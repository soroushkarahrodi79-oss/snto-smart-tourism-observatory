"""
Tab 7 — Catálogo de Activos y Auditoría — for the SNTO dashboard shell (Fase 4, paso 7).

Extracted verbatim from app.py (issue #27, modularización). ``render_tab_assets``
takes the calibration record, the ranked assets and the active view, and paints
the per-asset catalogue cards with their tier/alert chips, EHS health bar and
data-provenance badges.
"""
from __future__ import annotations

import streamlit as st

from src.platform.calibration import coverage_summary
from src.platform.provenance import data_status_badge
from src.temporal import DataStatus
from src.ui.render_helpers import (
    _ASSET_TYPE_EMOJI,
    _TIER_BADGE_COLOR,
    _TIER_INVEST_LABEL,
    _TIER_ROMAN,
    _alert_chip,
    _ehs_color,
    _tier_chip,
)


def render_tab_assets(calibration, ranked_assets, _view) -> None:
    """Render the Catálogo de Activos y Auditoría tab (issue #27 extraction)."""
    st.subheader("Catálogo de Activos — Ranking por Índice de Prioridad Territorial (TPI)")
    st.caption(
        f"{len(ranked_assets)} activos monitorizados · "
        "Ordenados por TPI descendente (mayor urgencia primero)"
    )
    _cur_badge = data_status_badge(DataStatus.CALIBRATED)
    st.markdown(
        f'<div style="font-size:0.8rem;color:{_cur_badge.color};margin:-4px 0 8px">'
        f'{_cur_badge.emoji} <b>{_cur_badge.label}</b> · estos activos son una capa '
        f'narrativa de juicio experto, contrastada (no sustituida) por el satélite '
        f'en la pestaña <i>Diagnóstico Satelital y Mapa</i>. No usar para intervención formal sin '
        f'el dato satelital de su senda.</div>',
        unsafe_allow_html=True,
    )

    # ── Validación cruzada con el satélite (Pipeline A) ───────────────────────
    # Se reutiliza la calibración calculada en load_dashboard (contra el EHS
    # curado ORIGINAL, antes del override) para no falsear la concordancia.
    # Modulada por vista: GESTOR ve solo el titular; TÉCNICA/AUDITORÍA, el detalle.
    _calib = calibration
    _cov = coverage_summary(_calib)
    if _view.simplified:
        st.caption(
            f"🛰️ Validación satelital: **{_cov['mas_degradado']}** activo(s) con override "
            f"(satélite más degradado), **{_cov['confirma']}** confirmados, "
            f"**{_cov['sin_dato']}** sin senda equivalente. Detalle metodológico en la vista "
            f"de Auditoría científica."
        )
    else:
        with st.container():
            cc1, cc2, cc3, cc4 = st.columns(4)
            cc1.metric("✓ Satélite confirma", _cov["confirma"])
            cc2.metric("⚠ Satélite más verde", _cov["mas_sano"])
            cc3.metric("⚠ Satélite más degradado (override)", _cov["mas_degradado"])
            cc4.metric("— Sin senda equivalente", _cov["sin_dato"])
        st.caption(
            "**Validación cruzada + override conservador:** cada activo curado se contrasta "
            "con el EHS satelital real de su senda concreta (Pipeline A · Sentinel-2). "
            "El EHS curado mide *salud bajo presión turística* (juicio experto); el "
            "satelital mide *verdor de la vegetación* (NDVI/NDMI). Política aplicada: cuando "
            "el satélite ve **más degradación** que el experto (*más degradado*), el dato "
            "satelital **sobreescribe** el EHS curado y escala tier/alerta en todo el "
            "dashboard. Cuando el satélite es **más verde** (*más verde*) se mantiene el "
            "juicio curado, porque en alta montaña la roca/canchal alpino tiene poco NDVI "
            "por geología, no por turismo. Así el satélite **escala**, nunca relaja, el "
            "diagnóstico experto."
        )
        if _view.audit:
            with st.expander("⚖️ Procedencia y límites declarados (vista auditoría)", expanded=False):
                _real_badge = data_status_badge(DataStatus.REAL)
                _syn_badge = data_status_badge(DataStatus.SYNTHETIC)
                st.markdown(
                    f"- {_real_badge.emoji} **EHS satelital:** {_real_badge.caveat} "
                    f"Fuente Sentinel-2 L2A, tile T30TVL (Pipeline A).\n"
                    f"- {_syn_badge.emoji} **EHS curado:** juicio experto de salud bajo presión "
                    f"turística; capa narrativa contrastada (no sustituida al alza) por el satélite.\n"
                    f"- **Override conservador:** solo escala cuando el satélite ve más "
                    f"degradación (`mas_degradado`); nunca relaja el diagnóstico experto.\n"
                    f"- **Mapeo activo↔senda:** `calibration._ASSET_TRAIL_MAP` "
                    f"(solo correspondencias toponímicas defendibles; el resto, SIN_DATO).\n"
                    f"- **Límites:** resolución ~10–30 m; sendas sin equivalente OSM/OAPN no "
                    f"calibran; concordancia con banda ±12 EHS."
                )
    st.divider()

    # Filtros
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        tier_filter = st.multiselect(
            "Filtrar por Tier (prioridad de inversión)", options=[1, 2, 3, 4],
            default=[1, 2, 3, 4],
            format_func=lambda t: f"TIER {_TIER_ROMAN[t]} — {_TIER_INVEST_LABEL[t]}",
        )
    with f_col2:
        type_options = sorted({a.asset_type for a in ranked_assets})
        type_filter = st.multiselect(
            "Filtrar por tipo", options=type_options,
            default=type_options,
            format_func=lambda t: f"{_ASSET_TYPE_EMOJI.get(t,'📍')} {t.replace('_',' ').title()}",
        )
    with f_col3:
        region_options = sorted({a.region for a in ranked_assets})
        region_filter = st.multiselect(
            "Filtrar por municipio", options=region_options,
            default=region_options,
        )

    filtered = [
        a for a in ranked_assets
        if (a.tier in tier_filter)
        and (a.asset_type in type_filter)
        and (a.region in region_filter)
    ]

    st.caption(f"Mostrando {len(filtered)} de {len(ranked_assets)} activos")
    st.write("")

    # Render each asset as a styled card
    for asset in filtered:
        tier   = asset.tier or 0
        tpi    = asset.tpi or 0.0
        tier_fg, tier_bg = _TIER_BADGE_COLOR.get(tier, ("#2d2f4a", "#a9adcb"))
        ehs_c  = _ehs_color(asset.ehs)
        emoji  = _ASSET_TYPE_EMOJI.get(asset.asset_type, "📍")
        rank   = asset.priority_rank or "—"
        physical = ""
        if asset.length_km:
            physical = f"&nbsp;·&nbsp; {asset.length_km:.1f} km"
        elif asset.area_ha:
            physical = f"&nbsp;·&nbsp; {asset.area_ha:.0f} ha"
        if asset.elevation_m:
            physical += f"&nbsp;·&nbsp; {asset.elevation_m:.0f} m"

        # ── Sello de validación satelital ─────────────────────────────────────
        _cal = _calib.get(asset.asset_id)
        if _cal is not None:
            _vemoji, _vlabel, _vcolor = _cal.badge
            if _cal.satellite_ehs is not None:
                _refs = "; ".join(_cal.matched_trails[:2])
                if len(_cal.matched_trails) > 2:
                    _refs += f" (+{len(_cal.matched_trails) - 2})"
                _val_html = (
                    f'<div style="margin-top:6px;font-size:0.72rem;color:{_vcolor}">'
                    f'<b>{_vemoji} {_vlabel}</b> · EHS satélite '
                    f'<b>{_cal.satellite_ehs:.0f}</b>/100 '
                    f'(Δ {_cal.delta:+.0f} vs curado) '
                    f'<span style="color:#9aa4af">← {_refs}</span></div>'
                )
            else:
                _val_html = (
                    f'<div style="margin-top:6px;font-size:0.72rem;color:{_vcolor}">'
                    f'{_vemoji} {_vlabel} · sin senda satelital comparable</div>'
                )
        else:
            _val_html = ""

        st.markdown(
            f"""<div class="kpi-card" style="border-left:5px solid {tier_bg};margin-bottom:0.5rem;">
  <div style="display:flex;align-items:center;gap:12px;">
    <div style="font-size:1.8rem;line-height:1">{emoji}</div>
    <div style="flex:1">
      <div style="font-size:0.95rem;font-weight:700;color:#0d1b2a">
        #{rank}&ensp;{asset.name}
      </div>
      <div style="font-size:0.75rem;color:#7a8899;margin-top:2px">
        {asset.region}{physical}
      </div>
      <div style="margin-top:5px">{_tier_chip(tier)}{_alert_chip(asset.alert_level)}</div>
    </div>
    <div style="text-align:right;min-width:120px">
      <span style="font-size:1.1rem;font-weight:700;color:{ehs_c}">
        EHS&thinsp;{asset.ehs:.0f}
      </span>
      <span style="font-size:0.75rem;color:#9aa4af">/100</span>
    </div>
    <div style="text-align:right;min-width:80px">
      <div style="font-size:0.65rem;color:#9aa4af;text-transform:uppercase">TPI</div>
      <div style="font-size:1.3rem;font-weight:700;color:#0d1b2a">{tpi:.0f}</div>
    </div>
  </div>
  <div style="font-size:0.75rem;color:#555;margin-top:8px;padding-top:6px;
              border-top:1px solid #e8ecf0">
    {asset.description[:160]}{'…' if len(asset.description) > 160 else ''}
  </div>
  {_val_html}
</div>""",
            unsafe_allow_html=True,
        )
