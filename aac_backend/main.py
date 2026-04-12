from fastapi import FastAPI

from aac_backend.api.router import api_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Assurance-as-Code API",
        version="0.1.0",
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/v1/docs",
    )
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
