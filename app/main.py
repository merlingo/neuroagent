from fastapi import FastAPI

from app.api import (
    routes_agents,
    routes_approvals,
    routes_autoresearch,
    routes_documents,
    routes_domains,
    routes_evaluate,
    routes_evals,
    routes_models,
    routes_obsidian,
    routes_runs,
    routes_storage,
    routes_tools,
    routes_use_cases,
)
from app.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.2.0", debug=settings.app_debug)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok", "app": settings.app_name, "environment": settings.app_env}

    app.include_router(routes_domains.router)
    app.include_router(routes_agents.router)
    app.include_router(routes_runs.router)
    app.include_router(routes_approvals.router)
    app.include_router(routes_autoresearch.router)
    app.include_router(routes_documents.router)
    app.include_router(routes_tools.router)
    app.include_router(routes_models.router)
    app.include_router(routes_obsidian.router)
    app.include_router(routes_evals.router)
    app.include_router(routes_evaluate.router)
    app.include_router(routes_use_cases.router)
    app.include_router(routes_storage.router)
    return app


app = create_app()
