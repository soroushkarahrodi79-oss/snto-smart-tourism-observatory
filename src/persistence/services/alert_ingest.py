"""
Bridge: in-memory AlertEngine output -> persisted Alert + Recommendations
(Fase 5, step 5.4).

``src.alerts.engine.AlertEngine`` already computes an ``Alert`` (level, score,
triggered rules, recommended action labels) in memory per evaluation. This
service takes that domain object and writes it to the persistence layer as an
``Alert`` row plus one ``Recommendation`` row per recommended action.

Deliberate boundaries:
- The bridge does **not** invent assets. The target ``ManagedAsset`` must
  already exist (matched by its ``external_asset_id``, which is exactly the
  ``asset_id`` the engine's ``Alert`` carries); an unknown asset raises
  ``AssetNotRegisteredError`` rather than silently creating one.
- Recommendations are persisted with only the fields the engine actually
  produces — an ``action_label``. Cost range, owner, deadline and confidence
  are left ``None`` because the engine does not compute them; they are filled
  in later by a human (or a costing step), never fabricated here.
- No audit-log entry is written here yet — that trail is retrofitted across
  every 5.3–5.6 write in step 5.7, per the Fase 5 plan.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.alerts.engine import Alert as EngineAlert
from src.persistence.models.alert import Alert
from src.persistence.models.recommendation import Recommendation
from src.persistence.repositories import (
    AlertRepository,
    ManagedAssetRepository,
    RecommendationRepository,
)


class AssetNotRegisteredError(LookupError):
    """Raised when an engine Alert references an unpersisted ManagedAsset."""

    def __init__(self, external_asset_id: str) -> None:
        super().__init__(
            f"No ManagedAsset with external_asset_id={external_asset_id!r}; "
            "register the asset before persisting its alerts."
        )
        self.external_asset_id = external_asset_id


def persist_engine_alert(session: Session, engine_alert: EngineAlert) -> Alert:
    """
    Persist one engine Alert (and its recommended actions) for an existing
    ManagedAsset, returning the created persistent ``Alert``.
    """
    asset = ManagedAssetRepository(session).get_by_external_id(
        engine_alert.asset_id
    )
    if asset is None:
        raise AssetNotRegisteredError(engine_alert.asset_id)

    alert = AlertRepository(session).add(
        Alert(
            asset_id=asset.id,
            level=engine_alert.level.value,
            risk_score=engine_alert.score,
            triggered_rules=list(engine_alert.triggered_rules),
        )
    )

    rec_repo = RecommendationRepository(session)
    for action in engine_alert.recommended_actions:
        rec_repo.add(Recommendation(alert_id=alert.id, action_label=action))

    return alert
