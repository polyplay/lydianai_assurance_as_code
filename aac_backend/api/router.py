from fastapi import APIRouter

from aac_backend.api import (
    artefacts,
    auth,
    baselines,
    imports,
    jobs,
    projects,
    repositories,
    relationships,
    reports,
    traceability,
    validation,
    workspace,
)

api_router = APIRouter()


@api_router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


api_router.include_router(auth.router)
api_router.include_router(projects.router)
api_router.include_router(repositories.router)
api_router.include_router(artefacts.router)
api_router.include_router(relationships.router)
api_router.include_router(imports.router)
api_router.include_router(validation.router)
api_router.include_router(traceability.router)
api_router.include_router(baselines.router)
api_router.include_router(reports.router)
api_router.include_router(jobs.router)
api_router.include_router(workspace.router)
