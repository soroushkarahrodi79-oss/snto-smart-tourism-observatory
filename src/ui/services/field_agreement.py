"""
Satellite↔field agreement runner service (v2.5 enablement).

The validation gate (#26 / plan_v3_roadmap.md v2.5) asks: does the satellite EHS
actually track ground-truth degradation? The statistics to answer it already
exist (:func:`src.validation.agreement.validate_satellite_vs_field` — Spearman ρ
+ direction, and ``control_impact_contrast`` — Cliff's δ). What was missing is
the wiring that pairs the **real persisted field plots** (``FieldVerification``
rows, written by the campaign) with each asset's **satellite stress** and runs
it end-to-end.

This module is that wiring — pure data access, no Streamlit, so it is
unit-testable against an in-memory session and reused by both a UI surface and,
later, an ``/api/v2`` endpoint. It is honest by construction: with fewer than 3
co-located plots the built analysis already returns an "insuficiente" verdict,
so until the owner's field campaign produces real rows this reports
"campaña pendiente" rather than a fabricated agreement.

Convention: both axes use the **stress** convention (high = degraded). A
``FieldVerification.result`` holds the field ``degradation_index`` (0=pristine,
100=degraded); the satellite stress is ``100 − EHS``. A positive Spearman ρ
means the satellite follows the observed degradation — the thing we must prove
before claiming validation.
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from src.persistence.repositories import ManagedAssetRepository
from src.persistence.repositories.field_verification import (
    FieldVerificationRepository,
)
from src.persistence.session import session_scope
from src.validation.agreement import AgreementReport, validate_satellite_vs_field


@dataclass(frozen=True)
class PairedPlot:
    """One field plot paired with its asset's satellite stress."""

    asset_external_id: str
    asset_name: str
    field_degradation: float     # persisted FieldVerification.result (0..100)
    satellite_stress: float      # 100 − EHS (0..100)
    verified_at: str


@dataclass(frozen=True)
class FieldAgreementSummary:
    """The validation verdict plus the plots it was computed from."""

    n_verifications: int         # persisted field rows seen
    n_paired: int                # rows with a numeric result AND a known EHS
    report: AgreementReport | None
    plots: list[PairedPlot] = field(default_factory=list)

    @property
    def gate_passed(self) -> bool:
        """True only for a real, direction-correct, >=3-plot agreement (ρ>=0.3)."""
        r = self.report
        return bool(r and r.n >= 3 and r.direction_ok and r.spearman >= 0.3)


@contextmanager
def _open_session() -> Iterator[Session]:
    """Session seam — real ``session_scope`` in the app, patched in tests."""
    with session_scope() as session:
        yield session


def _as_float(result: str | None) -> float | None:
    """Parse a FieldVerification.result to a degradation index, or None.

    The bridge stores ``"no measured components"`` when a plot has no measured
    component — that is honestly un-pairable, not zero, so it returns None.
    """
    if result is None:
        return None
    try:
        return float(result)
    except (TypeError, ValueError):
        return None


def compute_field_agreement(
    ehs_by_external_id: dict[str, float],
    *,
    session: Session | None = None,
) -> FieldAgreementSummary:
    """Run the satellite↔field agreement over all persisted field plots.

    Args:
        ehs_by_external_id: satellite EHS (0..100) per asset external id, from the
            analytical layer (the persisted ``ManagedAsset`` does not store EHS).
        session: optional session (tests inject an in-memory one); otherwise the
            process session scope is opened.

    Returns a :class:`FieldAgreementSummary`; ``report`` is ``None`` only when no
    field plots are paired at all, else the built (possibly "insuficiente")
    verdict.
    """
    if session is not None:
        return _compute(session, ehs_by_external_id)
    with _open_session() as own:
        return _compute(own, ehs_by_external_id)


def _compute(
    session: Session, ehs_by_external_id: dict[str, float]
) -> FieldAgreementSummary:
    asset_repo = ManagedAssetRepository(session)
    fv_repo = FieldVerificationRepository(session)

    # Only assets we hold a satellite EHS for can be paired, so iterate those.
    n_verifications = 0
    plots: list[PairedPlot] = []
    for external_id, ehs in ehs_by_external_id.items():
        asset = asset_repo.get_by_external_id(external_id)
        if asset is None:
            continue
        for fv in fv_repo.list_by_asset(asset.id):
            n_verifications += 1
            field_val = _as_float(fv.result)
            if field_val is None:
                continue
            plots.append(
                PairedPlot(
                    asset_external_id=asset.external_asset_id,
                    asset_name=asset.name,
                    field_degradation=field_val,
                    satellite_stress=round(100.0 - ehs, 2),
                    verified_at=fv.verified_at.isoformat()
                    if fv.verified_at else "",
                )
            )

    report: AgreementReport | None = None
    if plots:
        pairs = [(p.satellite_stress, p.field_degradation) for p in plots]
        report = validate_satellite_vs_field(pairs)

    return FieldAgreementSummary(
        n_verifications=n_verifications,
        n_paired=len(plots),
        report=report,
        plots=plots,
    )
