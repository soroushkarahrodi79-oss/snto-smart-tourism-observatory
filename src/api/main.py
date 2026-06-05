from __future__ import annotations

from fastapi import FastAPI

from src.api.routers import alerts, evaluate, ranking


def create_app() -> FastAPI:
    app = FastAPI(
        title="SNTO — Smart Natural Tourism Observatory",
        description=(
            "Decision-support system for evaluating natural tourism assets "
            "using satellite-derived environmental indicators."
        ),
        version="1.0.0",
    )

    app.include_router(evaluate.router, prefix="/evaluate_asset")
    app.include_router(ranking.router, prefix="/ranking")
    app.include_router(alerts.router, prefix="/alerts")

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "version": "1.0.0"}

    return app


app = create_app()
