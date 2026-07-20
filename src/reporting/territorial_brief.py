"""
Executive brief over the *territorial* decision portfolio (Fase 6.7e).

WHY
===
The Gobernar layer's "Informes y exportaciones" module (spec §6, "Reports /
exports") needs a light, shareable document a director can take out of the
dashboard. SNTO already computes a director-grade brief in
``src/reporting/risk_brief.py`` — but that one consumes the Phase-1
``risk_engine`` pipeline (``RiskScore``/``RiskComponents``/``Alert``), whose
three-part decomposition (ecological / pressure / vulnerability) the running
dashboard's ``TerritorialAsset`` model **does not carry**. Feeding the
territorial data through it would mean fabricating those components — a project
non-negotiable ("do not blur real, calibrated, synthetic evidence").

So this module is deliberately *thin*: it rolls up **exactly the figures the
dashboard already shows** for the real curated decision portfolio (EHS, risk
score, intervention tier, alert level, satellite trend, recommended action,
indicative budget) into a Markdown/JSON artifact. It invents nothing: any
field that is absent (action, budget, tier) degrades to an explicit
"pendiente"/"sin asignar" placeholder, never a made-up value. It also does
**not** claim field validation (#26 pending) and does not import the
component-based cause attribution, keeping the two evidence pipelines separate.

The output is a JSON-serialisable dict plus a Markdown renderer, mirroring the
shape of ``risk_brief`` so the reporting surface stays consistent.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from src._version import __version__

if TYPE_CHECKING:  # avoid heavy imports at module load
    from src.territorial.models import TerritorialAsset


# Human-readable Spanish labels for the raw enum-ish strings the territorial
# model stores. Unknown values fall back to the raw string, never a guess.
_ALERT_LABELS: dict[str, str] = {
    "CRITICAL_INTERVENTION": "🔴 Intervención crítica",
    "URGENT_MONITORING": "🟡 Vigilancia urgente",
    "PREVENTIVE_ACTION": "🔵 Acción preventiva",
    "NORMAL": "🟢 Normal",
}
_TREND_LABELS: dict[str, str] = {
    "decreasing": "descendente",
    "increasing": "ascendente",
    "stable": "estable",
    "no trend": "sin tendencia",
}


def _alert_label(raw: str | None) -> str:
    if not raw:
        return "sin clasificar"
    return _ALERT_LABELS.get(raw, raw)


def _trend_label(raw: str | None) -> str:
    if not raw:
        return "sin dato"
    return _TREND_LABELS.get(raw, raw)


@dataclass(frozen=True)
class BriefRow:
    """One portfolio asset as it already appears on the dashboard."""

    rank: int
    asset_id: str
    name: str
    ehs: float | None
    risk_score: float | None
    tier: int | None
    tier_label: str
    alert_label: str
    trend_label: str
    recommended_action: str
    budget_eur: float | None


def _priority_key(asset: TerritorialAsset) -> tuple:
    """Order the portfolio worst-first, tolerating missing tier/risk."""
    tier = asset.tier if asset.tier is not None else 99
    risk = asset.risk_score if asset.risk_score is not None else 0.0
    ehs = asset.ehs if asset.ehs is not None else 100.0
    return (tier, -risk, ehs)


def build_territorial_brief(
    assets: list[TerritorialAsset],
    *,
    territory_name: str,
    report_date: str | None = None,
) -> dict:
    """Assemble the dashboard portfolio into a JSON-serialisable brief.

    Rolls up only fields the ``TerritorialAsset`` model actually holds; missing
    action/budget/tier degrade to explicit placeholders, never fabricated.
    """
    if report_date is None:
        report_date = date.today().isoformat()

    ordered = sorted(assets, key=_priority_key)
    rows: list[BriefRow] = []
    for i, a in enumerate(ordered, start=1):
        rows.append(
            BriefRow(
                rank=i,
                asset_id=a.asset_id,
                name=a.name,
                ehs=round(a.ehs, 1) if a.ehs is not None else None,
                risk_score=round(a.risk_score, 3) if a.risk_score is not None else None,
                tier=a.tier,
                tier_label=a.tier_label or "sin clasificar",
                alert_label=_alert_label(a.alert_level),
                trend_label=_trend_label(a.trend_direction),
                recommended_action=a.recommended_action_label or "pendiente de definir",
                budget_eur=a.budget_estimate_eur,
            )
        )

    total_budget = sum(r.budget_eur for r in rows if r.budget_eur is not None)
    return {
        "metadata": {
            "report_date": report_date,
            "system": "Smart Natural Tourism Observatory (SNTO)",
            "version": __version__,
            "territory": territory_name,
            "assets_in_portfolio": len(rows),
        },
        "evidence_note": (
            "EHS y riesgo son las señales calibradas del panel (EHS curado con "
            "inyección Sentinel-2 real donde el satélite observa más degradación); "
            "el tier y la alerta derivan de ellas. La acción recomendada y el "
            "presupuesto son orientativos y requieren calibración local. Ningún "
            "activo está validado en campo (campaña #26 pendiente): «tendencia "
            "satelital real» no equivale a «validado en campo»."
        ),
        "total_indicative_budget_eur": round(total_budget, 2) if total_budget else None,
        "entries": [r.__dict__ for r in rows],
    }


def render_territorial_brief_markdown(brief: dict) -> str:
    """Render the territorial brief dict as a light, exportable Markdown doc."""
    m = brief["metadata"]
    lines = [
        f"# Resumen ejecutivo del panel — {m['territory']}",
        "",
        f"**Fecha de informe:** {m['report_date']}  ·  **SNTO** v{m['version']}  ·  "
        f"**Activos en cartera:** {m['assets_in_portfolio']}",
        "",
        f"> {brief['evidence_note']}",
        "",
        "## Cartera de decisión (peor primero)",
        "",
    ]
    cols = [
        "#", "Activo", "EHS", "Riesgo", "Tier", "Alerta", "Tendencia",
        "Acción recomendada", "Coste orientativo (€)",
    ]
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("|" + "|".join("---" for _ in cols) + "|")
    for e in brief["entries"]:
        ehs = f"{e['ehs']:.0f}/100" if e["ehs"] is not None else "sin dato"
        risk = f"{e['risk_score']:.2f}" if e["risk_score"] is not None else "sin dato"
        tier = (
            f"T{e['tier']} · {e['tier_label']}"
            if e["tier"] is not None
            else "sin clasificar"
        )
        budget = (
            f"{e['budget_eur']:,.0f}" if e["budget_eur"] is not None else "pendiente"
        )
        lines.append(
            f"| {e['rank']} | {e['name']} | {ehs} | {risk} | {tier} | "
            f"{e['alert_label']} | {e['trend_label']} | {e['recommended_action']} | "
            f"{budget} |"
        )
    lines.append("")
    if brief["total_indicative_budget_eur"]:
        lines.append(
            f"**Presupuesto orientativo total:** "
            f"{brief['total_indicative_budget_eur']:,.0f} €"
        )
        lines.append("")
    lines.append(
        "_Informe orientativo generado por SNTO. No sustituye la inspección de "
        "campo ni la validación técnica local._"
    )
    lines.append("")
    return "\n".join(lines)
