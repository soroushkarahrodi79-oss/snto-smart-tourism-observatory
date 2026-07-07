from __future__ import annotations

from fastapi import FastAPI

from src._version import __version__
from src.api.routers import alerts, evaluate, ranking


def create_app() -> FastAPI:
    app = FastAPI(
        title="SNTO — Smart Natural Tourism Observatory",
        description=(
            "Decision-support system for evaluating natural tourism assets "
            "using satellite-derived environmental indicators."
        ),
        version=__version__,
    )

    app.include_router(evaluate.router, prefix="/evaluate_asset")
    app.include_router(ranking.router, prefix="/ranking")
    app.include_router(alerts.router, prefix="/alerts")

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "version": __version__}

    return app


app = create_app()
