"""
Director-grade risk brief (issue #12).

WHY
===
A national-park director does not consume risk scores or Mann-Kendall τ; they
consume a decision: *which asset, how sure are we, what to do, what it costs,
who owns it*. The protected-area director review (docs/reviews/2026/
02-national-park-director.md) asked explicitly for a "decision brief: priority
assets, confidence, action, cost, owner, status".

This module turns the pieces SNTO already computes — risk scores
(``src/risk_engine``), operational alerts (``src/alerts``), the portfolio
ranking (``src/ranking``) and the real satellite trend with its v1.3.0
confidence layer (``src/platform/satellite_trends``) — into that brief. It
chains, per priority asset:

    ecological state → probable cause → confidence → priority → budget

The **confidence** column is the v1.3.0 contribution: it is derived from the
statistical evidence (trend significance + Sen's-slope 95% CI), not asserted.
Attribution of cause is explicitly qualitative and preliminary — this module
never overclaims (a non-negotiable): every probable cause carries a caveat and
the brief states its own evidence limits.

The output is a plain structured dict (JSON-serialisable) plus a Markdown
renderer, so the brief is a *light, exportable* artifact — no dashboard
surface is required, honouring the "no major UI evolution before modularising
app.py" constraint.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import TYPE_CHECKING

from src._version import __version__

if TYPE_CHECKING:  # avoid import cycles / heavy deps at import time
    from src.alerts.engine import Alert
    from src.platform.satellite_trends import AssetTrend
    from src.ranking.ranker import RankedAsset
    from src.risk_engine.scorer import RiskScore


class Confidence(str, Enum):
    """How much statistical support the trend evidence gives an asset's story."""

    HIGH = "alta"
    MEDIUM = "media"
    LOW = "baja"
    NO_DATA = "sin datos"


class ProbableCause(str, Enum):
    """Preliminary, qualitative attribution of the ecological degradation."""

    TOURISM = "uso turístico"
    CLIMATE = "climática"
    MIXED = "mixta / requiere inspección"
    NONE = "sin degradación relevante"


# Degradation / pressure are on [0, 1]. These thresholds mirror the alert
# engine's "meaningful" band; kept local so the brief's wording is auditable.
_DEGRADATION_HIGH = 0.5
_PRESSURE_HIGH = 0.5
_PRESSURE_LOW = 0.35


@dataclass(frozen=True)
class BriefEntry:
    """One priority asset as a director reads it."""

    rank: int
    asset_id: str
    risk_score: float
    percentile: float
    priority_level: str          # AlertLevel value
    ecological_state: str        # human-readable band
    probable_cause: ProbableCause
    cause_caveat: str
    confidence: Confidence
    confidence_basis: str        # one line explaining the confidence verdict
    recommended_action: str
    budget_eur: float | None
    owner: str | None


def assess_confidence(trend: AssetTrend | None) -> tuple[Confidence, str]:
    """Confidence in the asset's trend story, from the v1.3.0 statistics.

    HIGH   — significant trend *and* Sen's-slope 95% CI excludes zero.
    MEDIUM — one of the two holds (significant, or CI excludes zero).
    LOW    — neither holds (no statistical support for a monotonic trend).
    NO_DATA — no real satellite trend available for the asset.
    """
    if trend is None:
        return Confidence.NO_DATA, "Sin serie satelital real para el activo."

    ci = trend.sens_slope_ci
    ci_excludes_zero = ci is not None and (ci[0] > 0 or ci[1] < 0)
    significant = trend.significant

    ci_txt = (
        f"IC 95% de Sen [{ci[0]:.2e}, {ci[1]:.2e}]" if ci is not None else "sin IC"
    )
    sig_txt = f"p={trend.p_value:.3f}"

    if significant and ci_excludes_zero:
        return Confidence.HIGH, (
            f"Tendencia significativa ({sig_txt}) y {ci_txt} excluye 0."
        )
    if significant or ci_excludes_zero:
        return Confidence.MEDIUM, f"Evidencia parcial: {sig_txt}; {ci_txt}."
    return Confidence.LOW, f"Sin soporte estadístico de tendencia: {sig_txt}; {ci_txt}."


def infer_probable_cause(
    ecological_degradation: float,
    human_pressure_proxy: float,
    trend: AssetTrend | None,
    portfolio_worst_year: str | None,
) -> tuple[ProbableCause, str]:
    """Qualitative, preliminary attribution of the degradation.

    Heuristic, never asserted as validated:
      * high pressure + high degradation → tourism use is the plausible driver;
      * high degradation + low pressure, coinciding with the portfolio-wide
        worst NDVI year → climate signal (a shared bad year points to weather,
        not localised footfall);
      * otherwise mixed / needs inspection, or no relevant degradation.
    """
    caveat = (
        "Atribución preliminar (no validada en campo); "
        "requiere inspección para confirmar el driver."
    )

    if ecological_degradation < _DEGRADATION_HIGH:
        return ProbableCause.NONE, "Sin degradación relevante que atribuir."

    if human_pressure_proxy >= _PRESSURE_HIGH:
        return ProbableCause.TOURISM, caveat

    shares_drought = (
        trend is not None
        and portfolio_worst_year is not None
        and trend.worst_year == portfolio_worst_year
    )
    if human_pressure_proxy < _PRESSURE_LOW and shares_drought:
        return ProbableCause.CLIMATE, (
            caveat
            + f" Coincide con el peor año NDVI de la cartera ({portfolio_worst_year})."
        )

    return ProbableCause.MIXED, caveat


def _ecological_band(degradation: float) -> str:
    if degradation >= 0.7:
        return f"crítico (degradación ecológica {degradation:.2f})"
    if degradation >= _DEGRADATION_HIGH:
        return f"deteriorado (degradación ecológica {degradation:.2f})"
    if degradation >= 0.3:
        return f"vigilancia (degradación ecológica {degradation:.2f})"
    return f"estable (degradación ecológica {degradation:.2f})"


def build_risk_brief(
    scores: list[RiskScore],
    alerts: list[Alert],
    ranked: list[RankedAsset],
    trends: list[AssetTrend] | None = None,
    budgets: dict[str, float] | None = None,
    owners: dict[str, str] | None = None,
    *,
    park_label: str = "PNSG",
    min_percentile: float = 50.0,
    report_date: str | None = None,
) -> dict:
    """Assemble the director brief as a JSON-serialisable dict.

    Only assets at or above ``min_percentile`` (worst half by default) become
    brief entries — a director wants the short list, not the portfolio dump.
    ``trends``/``budgets``/``owners`` are optional; missing data degrades to an
    explicit "sin datos"/"pendiente" rather than a fabricated value.
    """
    if report_date is None:
        report_date = date.today().isoformat()
    budgets = budgets or {}
    owners = owners or {}

    scores_by_id = {s.asset_id: s for s in scores}
    alerts_by_id = {a.asset_id: a for a in alerts}
    trends_by_id = {t.asset_id: t for t in (trends or [])}

    # Portfolio-wide worst NDVI year: a shared bad year is the climate fingerprint.
    worst_years = [t.worst_year for t in (trends or []) if t.worst_year]
    portfolio_worst_year = (
        max(set(worst_years), key=worst_years.count) if worst_years else None
    )

    entries: list[BriefEntry] = []
    for r in sorted(ranked, key=lambda x: x.rank):
        if r.percentile < min_percentile:
            continue
        score = scores_by_id.get(r.asset_id)
        if score is None:
            continue
        comp = score.components
        trend = trends_by_id.get(r.asset_id)
        alert = alerts_by_id.get(r.asset_id)

        confidence, confidence_basis = assess_confidence(trend)
        cause, cause_caveat = infer_probable_cause(
            comp.ecological_degradation, comp.human_pressure_proxy,
            trend, portfolio_worst_year,
        )
        action = (
            alert.recommended_actions[0]
            if alert and alert.recommended_actions
            else "Revisar en el ciclo de monitorización."
        )
        entries.append(
            BriefEntry(
                rank=r.rank,
                asset_id=r.asset_id,
                risk_score=round(r.risk_score, 4),
                percentile=round(r.percentile, 1),
                priority_level=alert.level.value if alert else "NORMAL",
                ecological_state=_ecological_band(comp.ecological_degradation),
                probable_cause=cause,
                cause_caveat=cause_caveat,
                confidence=confidence,
                confidence_basis=confidence_basis,
                recommended_action=action,
                budget_eur=budgets.get(r.asset_id),
                owner=owners.get(r.asset_id),
            )
        )

    total_budget = sum(e.budget_eur for e in entries if e.budget_eur is not None)
    return {
        "metadata": {
            "report_date": report_date,
            "system": "Smart Natural Tourism Observatory (SNTO)",
            "version": __version__,
            "park": park_label,
            "assets_in_brief": len(entries),
            "assets_evaluated": len(scores),
        },
        "evidence_note": (
            "Estado ecológico y prioridad derivan del EHS y del ranking de riesgo. "
            "La confianza se calcula sobre la evidencia estadística de la tendencia "
            "satelital real (significancia + IC 95% de Sen, v1.3.0). La causa probable "
            "es una atribución preliminar no validada en campo. El presupuesto es "
            "orientativo y requiere calibración local."
        ),
        "portfolio_worst_ndvi_year": portfolio_worst_year,
        "total_indicative_budget_eur": round(total_budget, 2) if total_budget else None,
        "entries": [e.__dict__ | {
            "probable_cause": e.probable_cause.value,
            "confidence": e.confidence.value,
        } for e in entries],
    }


def render_risk_brief_markdown(brief: dict) -> str:
    """Render the brief dict as a light, exportable Markdown document."""
    m = brief["metadata"]
    lines = [
        f"# Informe de riesgo para dirección — {m['park']}",
        "",
        f"**Fecha:** {m['report_date']}  ·  **SNTO** v{m['version']}  ·  "
        f"**Activos priorizados:** {m['assets_in_brief']} de {m['assets_evaluated']}",
        "",
        f"> {brief['evidence_note']}",
        "",
        "## Activos prioritarios",
        "",
    ]
    _cols = [
        "#", "Activo", "Estado ecológico", "Causa probable", "Confianza",
        "Prioridad", "Acción", "Coste (€)", "Responsable",
    ]
    lines.append("| " + " | ".join(_cols) + " |")
    lines.append("|" + "|".join("---" for _ in _cols) + "|")
    for e in brief["entries"]:
        budget = (
            f"{e['budget_eur']:,.0f}" if e["budget_eur"] is not None else "pendiente"
        )
        owner = e["owner"] or "sin asignar"
        lines.append(
            f"| {e['rank']} | {e['asset_id']} | {e['ecological_state']} | "
            f"{e['probable_cause']} | {e['confidence']} | {e['priority_level']} | "
            f"{e['recommended_action']} | {budget} | {owner} |"
        )
    lines.append("")
    if brief["total_indicative_budget_eur"]:
        lines.append(
            f"**Presupuesto orientativo total:** "
            f"{brief['total_indicative_budget_eur']:,.0f} €"
        )
        lines.append("")
    lines.append("### Notas de confianza y causa (por activo)")
    lines.append("")
    for e in brief["entries"]:
        lines.append(
            f"- **{e['asset_id']}** — confianza *{e['confidence']}*: "
            f"{e['confidence_basis']} Causa *{e['probable_cause']}*: "
            f"{e['cause_caveat']}"
        )
    lines.append("")
    return "\n".join(lines)
