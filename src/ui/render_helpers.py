"""
Presentation primitives for the SNTO dashboard — Fase 4, paso 1.

Stateless formatting layer extracted verbatim from app.py (issue #27,
modularización): the status/tier/alert palettes and the pure HTML-chip / colour
formatters. Zero Streamlit, zero session state, zero app-assembly coupling —
they only map a status/tier/EHS value to a colour or an HTML ``<span>``, so they
are safe to share across the dashboard shell and every tab module.

Names keep their original ``_`` prefix so the (still monolithic) app.py call
sites are unchanged; they can be promoted to public names once the tabs that use
them also move into src/ui/.
"""
from __future__ import annotations

# ── Paleta de estados ─────────────────────────────────────────────────────────
_COLOR = {"GREEN": "#2e7d32", "AMBER": "#e65100", "RED": "#c62828", "BLUE": "#1565c0"}
_BG    = {"GREEN": "#e8f5e9", "AMBER": "#fff3e0", "RED": "#ffebee", "BLUE": "#e3f2fd"}
_EMOJI = {"GREEN": "🟢",      "AMBER": "🟡",      "RED": "🔴",      "BLUE": "🔵"}

# ── TIER = estrategia / prioridad de inversión pública (NO es riesgo táctico) ──
# Paleta NEUTRA índigo→pizarra (oscuro = Tier I máxima prioridad → claro = Tier IV).
# Deliberadamente sin rojo/ámbar/verde: el semáforo se reserva para las ALERTAS.
_TIER_ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV"}
_TIER_BADGE_COLOR = {              # (texto, fondo)
    1: ("#ffffff", "#312e5c"),     # índigo profundo
    2: ("#ffffff", "#56548a"),     # índigo medio
    3: ("#2d2f4a", "#a9adcb"),     # pizarra media
    4: ("#3a3d57", "#d6d9e8"),     # pizarra clara
}
_TIER_INVEST_LABEL = {
    1: "Prioridad máxima de inversión",
    2: "Inversión preventiva",
    3: "Monitorización rutinaria",
    4: "Promoción / mínima inversión pública",
}
_ASSET_TYPE_EMOJI = {
    "TRAIL":             "🥾",
    "VIEWPOINT":         "🔭",
    "RECREATIONAL_AREA": "🌿",
    "NATURAL_PARK":      "🌲",
    "CYCLING_ROUTE":     "🚴",
}


_ALERT_META: dict[str, tuple[str, str, str, str]] = {
    # level: (icon, label, bg, border)
    "CRITICAL_INTERVENTION": ("🔴", "Intervención Crítica",  "#fff5f5", "#feb2b2"),
    "URGENT_MONITORING":     ("🟡", "Monitorización Urgente","#fffbeb", "#fde68a"),
    "PREVENTIVE_ACTION":     ("🔵", "Acción Preventiva",     "#eff6ff", "#bfdbfe"),
}
_ALERT_SEVERITY = {
    "CRITICAL_INTERVENTION": 0,
    "URGENT_MONITORING":     1,
    "PREVENTIVE_ACTION":     2,
}
_ALERT_ACCENT = {
    "CRITICAL_INTERVENTION": "#c62828",
    "URGENT_MONITORING": "#e65100",
    "PREVENTIVE_ACTION": "#1565c0",
    "NORMAL": "#2e7d32",
}

# ── FASE 3: helpers de chips — TIER (neutro) y ALERTA (semáforo) ──────────────
def _tier_chip(tier) -> str:
    """Chip estructural neutro [TIER N] (prioridad de inversión, no riesgo)."""
    t = int(tier) if tier else 3
    fg, bg = _TIER_BADGE_COLOR.get(t, ("#2d2f4a", "#a9adcb"))
    return (
        f'<span class="snto-tier-chip" style="background:{bg};color:{fg};" '
        f'title="{_TIER_INVEST_LABEL.get(t, "")}">TIER {_TIER_ROMAN.get(t, "III")}</span>'
    )


def _alert_chip(alert_level: str) -> str:
    """Chip semafórico táctico para el estado de alerta actual del activo."""
    meta = _ALERT_META.get(alert_level)
    if not meta:
        return (
            '<span class="snto-status-chip" style="background:#e8f5e9;color:#1b5e20;">'
            '🟢 Normal</span>'
        )
    icon, label, bg, border = meta
    return (
        f'<span class="snto-status-chip" style="background:{bg};'
        f'border:1px solid {border};color:#2b3440;">{icon} {label}</span>'
    )


def _alert_accent(alert_level: str) -> str:
    """Return the tactical severity accent used by asset cards.

    Fase 6.1 reserves asset-card accents for severity. Investment tier stays a
    neutral indigo/slate badge and must never drive the card border.
    """
    return _ALERT_ACCENT.get(alert_level, _ALERT_ACCENT["NORMAL"])


def _ehs_color(ehs: float) -> str:
    """Color de salud para el valor de EHS (gradiente continuo, independiente
    del tier). Verde=sano, ámbar=alerta, rojo=degradado. Es un dato medido, no
    una categoría de estrategia."""
    if ehs >= 75:
        return "#1a9850"
    if ehs >= 60:
        return "#66a61e"
    if ehs >= 45:
        return "#e6a700"
    if ehs >= 30:
        return "#e0701a"
    return "#c62828"
