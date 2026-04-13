from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from aac_backend.api.router import api_router
from aac_backend.services.startup_service import initialize_application_state


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await initialize_application_state()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Assurance-as-Code API",
        version="0.1.0",
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/v1/docs",
        lifespan=lifespan,
    )
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
