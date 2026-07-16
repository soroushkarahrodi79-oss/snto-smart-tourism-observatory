from __future__ import annotations

from fastapi import FastAPI

from src._version import __version__
from src.api.routers import alerts, evaluate, ranking
from src.api.v2 import alerts as v2_alerts
from src.api.v2 import field_verifications as v2_field_verifications
from src.api.v2 import interventions as v2_interventions
from src.api.v2 import managed_assets as v2_managed_assets


def create_app() -> FastAPI:
    app = FastAPI(
        title="SNTO — Smart Natural Tourism Observatory",
        description=(
            "Decision-support system for evaluating natural tourism assets "
            "using satellite-derived environmental indicators."
        ),
        version=__version__,
    )

    # Existing stateless routers — behavior unchanged (Fase 5 keeps these intact).
    app.include_router(evaluate.router, prefix="/evaluate_asset")
    app.include_router(ranking.router, prefix="/ranking")
    app.include_router(alerts.router, prefix="/alerts")

    # /api/v2 — persistence-backed, read-only in this step (Fase 5, ADR-011).
    app.include_router(
        v2_managed_assets.router, prefix="/api/v2/managed-assets"
    )
    app.include_router(v2_alerts.router, prefix="/api/v2/alerts")
    # Intervention lifecycle (5.5): routes span /managed-assets/.../interventions
    # and /interventions/..., so this router mounts at the /api/v2 root.
    app.include_router(v2_interventions.router, prefix="/api/v2")
    # Field verifications (5.6): /managed-assets/.../field-verifications.
    app.include_router(v2_field_verifications.router, prefix="/api/v2")

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "version": __version__}

    return app


app = create_app()
