from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import logging
from time import perf_counter
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from aac_backend.api.router import api_router
from aac_backend.config import get_settings
from aac_backend.schemas.common import ApiErrorDetail, ApiErrorEnvelope
from aac_backend.services.request_context import (
    current_correlation_id,
    current_request_id,
    establish_request_context,
)
from aac_backend.services.observability import structured_log
from aac_backend.services.startup_service import initialize_application_state

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
LOGGER = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await initialize_application_state()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    _configure_logging()
    app = FastAPI(
        title="Assurance-as-Code API",
        version="0.1.0",
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/v1/docs",
        lifespan=lifespan,
    )
    if settings.allowed_cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.allowed_cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=[
                "Authorization",
                "Content-Type",
                "X-Request-ID",
                "X-Correlation-ID",
            ],
        )

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id, correlation_id = establish_request_context(
            request_id=request.headers.get("X-Request-ID"),
            correlation_id=request.headers.get("X-Correlation-ID"),
        )
        started = perf_counter()
        structured_log(
            LOGGER,
            logging.INFO,
            "http.request.started",
            method=request.method,
            path=request.url.path,
            client_host=request.client.host if request.client else None,
            path_params=dict(request.scope.get("path_params") or {}),
            query_string=request.url.query,
        )
        try:
            response = await call_next(request)
        except Exception:
            structured_log(
                LOGGER,
                logging.ERROR,
                "http.request.failed",
                message="Unhandled exception during request processing",
                method=request.method,
                path=request.url.path,
                client_host=request.client.host if request.client else None,
                path_params=dict(request.scope.get("path_params") or {}),
                query_string=request.url.query,
                duration_ms=(perf_counter() - started) * 1000,
            )
            raise
        duration_ms = (perf_counter() - started) * 1000
        structured_log(
            LOGGER,
            logging.INFO,
            "http.request.completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            client_host=request.client.host if request.client else None,
            path_params=dict(request.scope.get("path_params") or {}),
            query_string=request.url.query,
        )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id
        return response

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        message, details = _exception_content(exc.detail)
        structured_log(
            LOGGER,
            logging.WARNING if exc.status_code < 500 else logging.ERROR,
            "http.request.rejected",
            message=message,
            status_code=exc.status_code,
            details=details if isinstance(details, dict) else None,
        )
        return _error_response(
            status_code=exc.status_code,
            code=_error_code(exc.status_code),
            message=message,
            details=details,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        structured_log(
            LOGGER,
            logging.WARNING,
            "http.request.rejected",
            message="The request payload is invalid.",
            status_code=422,
            details=exc.errors(),
        )
        return _error_response(
            status_code=422,
            code="validation_error",
            message="The request payload is invalid.",
            details=exc.errors(),
        )

    @app.exception_handler(Exception)
    async def unexpected_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        LOGGER.exception(
            "Unhandled API exception | request_id=%s correlation_id=%s",
            current_request_id(),
            current_correlation_id(),
        )
        return _error_response(
            status_code=500,
            code="internal_error",
            message="An unexpected server error occurred.",
        )

    app.include_router(api_router, prefix="/api/v1")
    if WEB_DIR.exists():
        app.mount("/app", StaticFiles(directory=WEB_DIR, html=True), name="web")
    return app


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details=None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    envelope = ApiErrorEnvelope(
        error=ApiErrorDetail(code=code, message=message, details=details)
    )
    return JSONResponse(
        status_code=status_code,
        content=envelope.model_dump(mode="json"),
        headers=headers,
    )


def _exception_content(detail) -> tuple[str, object | None]:
    if isinstance(detail, str):
        return detail, None
    if isinstance(detail, dict):
        return str(detail.get("message") or "The request could not be completed."), detail
    return "The request could not be completed.", detail


def _error_code(status_code: int) -> str:
    return {
        400: "bad_request",
        401: "authentication_required",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        413: "payload_too_large",
        415: "unsupported_media_type",
        422: "validation_error",
        423: "resource_locked",
        429: "rate_limited",
    }.get(status_code, "request_failed")


def _configure_logging() -> None:
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
    root.setLevel(logging.INFO)


app = create_app()
