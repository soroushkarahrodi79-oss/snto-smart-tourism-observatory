"""
Tab 2 — Diagnóstico Satelital y Mapa — for the SNTO dashboard shell (Fase 4, paso 10).

Extracted verbatim from app.py (issue #27, modularización). In app.py this tab was
authored as two non-contiguous ``with tab_diagnostic:`` blocks (the territorial
map first, the Pipeline-A real trails second, with tab_assets interleaved in
source order only). They are fused here into a single ``render_tab_diagnostic``
with no behavioural change — both blocks render into the same tab in the same
order. The block-2 ``_ehs_color`` local (a colour string) is now cleanly
function-scoped, so it no longer shadows the module-level formatter and this
module deliberately does not import that name.
"""
from __future__ import annotations

import streamlit as st

from src.platform.calibration import asset_trail_geometries
from src.platform.map_layers import (
    LEGEND_ITEMS,
    build_pydeck_deck,
    build_pydeck_deck_spectral,
    build_real_trails_deck,
)
from src.platform.provenance import (
    data_status_badge,
    load_timeseries_coverage,
    snapshot_provenance,
)
from src.platform.real_trails import (
    build_real_trails_geojson,
    get_park_boundary,
    get_real_trails,
)
from src.platform.views import ConfidenceDetail


def render_tab_diagnostic(selected_key, _terr_cfg, ranked_assets, _view) -> None:
    """Render the Diagnóstico Satelital y Mapa tab (issue #27; fuses 2 blocks)."""
    st.subheader("Diagnóstico Satelital y Mapa — Visión Espacial del Territorio")
    st.caption(
        "Corazón científico del observatorio: el mapa territorial (gestión / "
        "diagnóstico espectral) y, debajo, las **sendas reales** medidas por "
        "Sentinel-2 (Pipeline A) con su EHS y ΔEHS observados."
    )

    with st.expander("📐 Nota metodológica — índices espectrales, EHS y convención de signo",
                     expanded=_view.technical):
        st.markdown("**Índices espectrales (Sentinel-2 L2A, tile T30TVL):**")
        st.latex(r"NDVI = \frac{NIR - RED}{NIR + RED}\ \ (B08, B04) \qquad "
                 r"NDMI = \frac{NIR - SWIR}{NIR + SWIR}\ \ (B08, B11)")
        st.markdown(
            "- **NDVI** — vigor de la vegetación.\n"
            "- **NDMI** — contenido hídrico foliar; detecta estrés que el NDVI no ve "
            "cuando el dosel aún está verde.\n"
            "- En **dosel denso** (NDVI ≥ 0,80, p. ej. hayedos) el NDVI **satura**: el peso "
            "del EHS se desplaza hacia el NDMI (y se usa EVI para la línea base) para no "
            "perder sensibilidad."
        )
        st.markdown(
            "**EHS por senda (Δ estacional):** se ancla en percentiles de la *propia "
            "escena*, no en constantes arbitrarias:"
        )
        st.latex(r"D_x = \mathrm{clamp}\!\left(\frac{P_{90} - \bar{x}}{P_{90} - P_{10}}\right)"
                 r"\qquad EHS = 100\,(w_{NDVI}\,D_{NDVI} + w_{NDMI}\,D_{NDMI})")
        st.markdown(
            "donde **P90** (`EHS_P_BASE`) es la referencia sana y **P10** (`EHS_P_FLOOR`) el "
            "suelo degradado, calculados tras excluir píxeles enmascarados por SCL y el propio "
            "buffer de 50 m de la senda (para no medir el problema dentro de la referencia).\n\n"
            "**Convención de signo (clave para auditar):** el Pipeline A calcula *estrés* "
            "(0 = sano, 100 = degradado); el dashboard habla *salud* (0 = crítico, 100 = sano). "
            "La conversión es **única**, en `src/platform/real_trails.py` (`stress_to_health`), "
            "de modo que todo el dashboard usa **alto = sano**. El **ΔEHS = salud_primavera − "
            "salud_verano**: ΔEHS negativo = deterioro estival.\n\n"
            "**Override conservador (Fase 2):** cuando el EHS satelital de la senda es *más "
            "degradado* que el juicio experto, **sobreescribe** al curado y escala tier/alerta; "
            "cuando es *más verde*, se mantiene el curado (posible geología, no degradación)."
        )

    # ── Control de modo de visualización ─────────────────────────────────────
    map_mode = st.radio(
        "Modo de visualización",
        options=["🗂️ Vista de Gestión (Tiers)", "🛰️ Vista de Diagnóstico Espectral (NDVI/NDMI)"],
        index=0,
        horizontal=True,
        help=(
            "**Vista de Gestión:** activos coloreados por tier de prioridad de inversión "
            "(escala neutra índigo→pizarra, NO semafórica). "
            "**Vista Espectral:** gradiente continuo RdYlGn derivado del EHS real del activo — "
            "simula el contraste espacial de degradación difusa visible en imágenes Sentinel-2."
        ),
    )

    spectral_mode = "Espectral" in map_mode

    if spectral_mode:
        st.caption(
            "🛰️ Color = gradiente RdYlGn (ColorBrewer) anclado en el EHS real del activo. "
            "**Rojo intenso** → EHS < 30 (degradación crítica) · "
            "**Amarillo** → EHS ≈ 60 (zona de transición) · "
            "**Verde saturado** → EHS > 80 (salud óptima). "
            "Reproduce el contraste espectral NDVI/NDMI a lo largo del corredor del sendero."
        )
    else:
        st.caption(
            "Renderizado WebGL vía Deck.gl / PyDeck. "
            "La carga computacional es constante — todo el rendering ocurre en la GPU del cliente. "
            "Haz clic en cualquier activo para ver su ficha completa."
        )

    # Geometrías reales (Pipeline A) por activo, para dibujar sobre su traza real
    _real_geoms = asset_trail_geometries(selected_key, ranked_assets)
    _n_real = sum(1 for g in _real_geoms.values() if g)
    if _n_real:
        st.caption(
            f"📍 **{_n_real} de {len(ranked_assets)}** activos se dibujan sobre su **traza "
            f"cartográfica real** (senda del Pipeline A · Sentinel-2). El resto, sin senda "
            f"OSM/OAPN equivalente, se sitúa en el **centroide municipal aproximado** "
            f"(≈, indicado en el tooltip)."
        )

    col_map, col_info = st.columns([3, 1])

    with col_map:
        try:
            _mc = _terr_cfg["map_center"]
            if spectral_mode:
                deck = build_pydeck_deck_spectral(ranked_assets, map_lat=_mc[0], map_lon=_mc[1], map_zoom=_mc[2], real_geoms=_real_geoms)
            else:
                deck = build_pydeck_deck(ranked_assets, map_lat=_mc[0], map_lon=_mc[1], map_zoom=_mc[2], real_geoms=_real_geoms)
            st.pydeck_chart(deck, use_container_width=True, height=540)
        except ImportError:
            st.error(
                "**pydeck no instalado.** Ejecuta `pip install pydeck` y reinicia el servidor.",
                icon="⚠️",
            )

    with col_info:
        if spectral_mode:
            # ── Leyenda espectral continua ────────────────────────────────────
            st.markdown("#### Escala EHS Espectral")
            _spectral_legend = [
                ("#a50026", "EHS < 30 — Crítico"),
                ("#d73027", "EHS 30-45 — Degradado"),
                ("#fdae61", "EHS 45-60 — Alerta"),
                ("#ffffbf", "EHS 60-75 — Moderado"),
                ("#a6d96a", "EHS 75-85 — Bueno"),
                ("#1a9850", "EHS > 85 — Óptimo"),
            ]
            for hex_c, label in _spectral_legend:
                st.markdown(
                    f'<div style="margin-bottom:7px;">'
                    f'<span class="legend-chip" style="background:{hex_c};'
                    f'border:1px solid rgba(0,0,0,.15)"></span>'
                    f'<small style="color:#444">{label}</small>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            st.divider()
            # EHS estadísticas rápidas
            ehs_vals = [a.ehs for a in ranked_assets]
            st.caption(f"EHS medio: **{sum(ehs_vals)/len(ehs_vals):.1f}**")
            st.caption(f"EHS mín: **{min(ehs_vals):.0f}** · máx: **{max(ehs_vals):.0f}**")
            st.caption(
                f"Activos en zona crítica (EHS<45): "
                f"**{sum(1 for v in ehs_vals if v < 45)}**"
            )
        else:
            # ── Leyenda de tiers (prioridad de inversión, escala neutra) ─────
            st.markdown("#### Distribución por tier (inversión)")
            tier_counts = {1: 0, 2: 0, 3: 0, 4: 0}
            for a in ranked_assets:
                if a.tier in tier_counts:
                    tier_counts[a.tier] += 1
            for item in LEGEND_ITEMS:
                t     = item["tier"]
                count = tier_counts.get(t, 0)
                color = item["hex"]
                label = item["label"]
                st.markdown(
                    f'<div style="margin-bottom:8px;">'
                    f'<span class="legend-chip" style="background:{color};'
                    f'border:1px solid rgba(0,0,0,.12)"></span>'
                    f'<b style="color:#0d1b2a">{count}</b>'
                    f'<small style="color:#555;margin-left:6px">{label}</small>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        st.divider()
        st.markdown("#### Cobertura territorial")
        regions = sorted({a.region for a in ranked_assets})
        for r in regions:
            n = sum(1 for a in ranked_assets if a.region == r)
            st.caption(f"· {r} ({n})")

        st.divider()
        st.caption(
            f"📍 Geometría: {_n_real}/{len(ranked_assets)} activos sobre su **traza real** "
            "(senda Pipeline A · Sentinel-2); los demás en **centroide municipal aproximado** "
            "(≈, mapeo activo↔senda en `calibration._ASSET_TRAIL_MAP`)."
        )

    # ── (continúa) Sendas reales del Pipeline A, debajo del mapa ──────────────
    st.divider()
    st.subheader("Sendas Reales — Análisis Satelital del Pipeline A")
    st.caption(
        "Esta capa NO usa datos curados: muestra exactamente lo que la ciencia "
        "produce a partir de la **cartografía real de senderos × Sentinel-2** "
        "(NDVI/NDMI) aplicando las fórmulas EHS / ΔEHS / SCM del proyecto. "
        "Cada línea es el trazado cartográfico verdadero, coloreado por su Salud "
        "Ecológica (EHS) de verano."
    )

    _real = get_real_trails(selected_key)

    if not _real.available:
        st.info(
            "Aún no hay resultados del Pipeline A para este territorio.\n\n"
            "Genera la salida ejecutando en la raíz del proyecto:\n\n"
            "```\npython run_pipeline_a_filemode.py --territory all\n```\n\n"
            "Esto cruza la cartografía de senderos con el ráster Sentinel-2 y "
            "escribe `data/outputs/<territorio>/pipeline_a_results.geojson`.",
            icon="🛰",
        )
    else:
        s = _real.summary
        import pandas as pd

        # ── Calidad y trazabilidad del dato (F3) ──────────────────────────────
        _prov = snapshot_provenance(selected_key)
        _badge = data_status_badge(_prov.status)
        _scenes = (" · ".join(_prov.scene_dates)
                   if _prov.scene_dates else f"{_prov.n_scenes} escenas estacionales")
        st.markdown(
            f'<div style="padding:10px 14px;border-radius:8px;'
            f'background:#f3f8f6;border-left:4px solid {_badge.color};margin-bottom:6px;">'
            f'<span style="font-weight:700;color:{_badge.color}">'
            f'{_badge.emoji} {_badge.label}</span> '
            f'<span style="font-size:0.8rem;color:#5a6b7a">· {_badge.caveat}</span><br/>'
            f'<span style="font-size:0.8rem;color:#33485c">'
            f'<b>Escenas Sentinel-2:</b> {_scenes} &nbsp;·&nbsp; '
            f'<b>Composición:</b> percentiles de escena (P90/P10) &nbsp;·&nbsp; '
            f'<b>Tile:</b> T30TVL</span><br/>'
            f'<span style="font-size:0.8rem;color:#33485c">'
            f'<b>Profundidad temporal:</b> {_prov.inference_label}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        _cov = load_timeseries_coverage(selected_key)
        if _cov is not None:
            st.caption(
                f"📈 Serie multi-anual: cobertura **{_cov['fraction']*100:.0f}%** "
                f"({_cov['n_present']}/{_cov['n_expected']} periodos) · "
                f"estado dominante: **{_cov['dominant_status']}** · "
                f"huecos: {_cov['n_gaps']}."
            )
        # Confianza modulada por la vista/audiencia activa (F7).
        if _view.confidence_detail is ConfidenceDetail.FULL:
            st.warning(_prov.caveat, icon="⚠️")
            st.caption(
                f"🔎 Trazabilidad: {_prov.inference_label} "
                "Metodología y límites en docs/temporal_series_design.md y "
                "docs/baselines_uncertainty_design.md."
            )
        elif _view.confidence_detail is ConfidenceDetail.CONCISE:
            _ok = "usar como prioridad, no como orden de gasto"
            st.caption(f"⚠️ Confianza: señal de alerta temprana — {_ok}.")
        else:  # RAW (técnica): el dato crudo va en los KPIs y la tabla de abajo
            st.caption(f"⚠️ {_prov.caveat}")

        # ── Tira de KPIs reales ──
        k1, k2, k3, k4, k5 = st.columns(5)
        _ehs_mean = s.get("ehs_summer_mean")
        _ehs_color = ("#0F6E56" if (_ehs_mean or 0) >= 60
                      else "#EF9F27" if (_ehs_mean or 0) >= 45 else "#A32D2D")
        with k1:
            st.metric("Sendas analizadas", s.get("n_trails", len(_real.trails)))
        with k2:
            st.metric("Longitud total", f"{s.get('total_length_km', 0):.0f} km")
        with k3:
            st.markdown(
                f'<div style="font-size:0.78rem;color:#7a8899">EHS verano medio</div>'
                f'<div style="font-size:1.6rem;font-weight:700;color:{_ehs_color}">'
                f'{_ehs_mean if _ehs_mean is not None else "—"}'
                f'<span style="font-size:0.8rem;color:#9aa4af">/100</span></div>',
                unsafe_allow_html=True,
            )
        with k4:
            st.metric("Sendas en deterioro", s.get("n_degrading_positive_delta", 0),
                      help="Sendas cuya salud ecológica cae de primavera a verano "
                           "(ΔEHS de salud < 0, equivalente a un aumento del estrés).")
        with k5:
            st.metric("Presupuesto indicativo",
                      f"€{s.get('total_budget_eur', 0):,.0f}",
                      help="Σ longitud × coste/m × (EHS/100) × factor causal SCM.")

        st.divider()

        # ── Mapa real + leyenda EHS ──
        _mc = _terr_cfg["map_center"]
        _map_c, _leg_c = st.columns([4, 1], gap="medium")
        with _map_c:
            try:
                _geo = build_real_trails_geojson(_real)
                _boundary = get_park_boundary(selected_key)
                _deck = build_real_trails_deck(
                    _geo, map_lat=_mc[0], map_lon=_mc[1], map_zoom=_mc[2],
                    boundary_geojson=_boundary,
                )
                st.pydeck_chart(_deck, use_container_width=True, height=460)
            except ImportError:
                st.error("pydeck no instalado — `pip install pydeck`", icon="⚠️")
        with _leg_c:
            st.markdown("**EHS (Salud Ecológica)**")
            _legend = [
                ("#1a9850", "≥ 75 · Saludable"),
                ("#a6d96a", "60–75 · Estable"),
                ("#ffffbf", "45–60 · Alerta"),
                ("#fdae61", "30–45 · Estrés"),
                ("#d73027", "< 30 · Crítico"),
                ("#9e9e9e", "Sin dato"),
            ]
            for hexc, lbl in _legend:
                st.markdown(
                    f'<span class="legend-chip" style="background:{hexc};'
                    f'border:1px solid #ccc"></span><small>{lbl}</small>',
                    unsafe_allow_html=True,
                )
            st.caption(
                "Color = NDVI/NDMI real del píxel sobre el buffer de 50 m de cada senda."
            )

        # ── Zonificación PRUG (solo PNSG) ──
        if _real.has_prug:
            from collections import Counter
            _zc = Counter(t.prug_zone for t in _real.trails if t.prug_zone)
            _prot = sum(1 for t in _real.trails
                        if t.prug_zone in ("Zona de Reserva", "Zona de Uso Restringido"))
            st.markdown(
                f'<div style="margin-top:8px;padding:10px 12px;background:#fffdf5;'
                f'border-radius:6px;border-left:3px solid #d4a017;">'
                f'<span style="font-size:0.72rem;color:#8a6d1a;text-transform:uppercase;'
                f'letter-spacing:0.06em;font-weight:700">⛰ Zonificación PRUG oficial</span><br/>'
                f'<span style="font-size:0.80rem;color:#444">'
                f'{_prot} de {len(_real.trails)} sendas discurren por zonas de alta protección '
                f'(Reserva / Uso Restringido). La prioridad de intervención pondera la '
                f'degradación por el nivel de protección del PRUG.</span></div>',
                unsafe_allow_html=True,
            )

        st.divider()

        # ── Tabla priorizada ──
        _has_prug = _real.has_prug
        if _has_prug:
            st.markdown("**Ranking de intervención · degradación × protección PRUG (prioridad combinada)**")
            _ranked = _real.ranked_by_priority_index()
        else:
            st.markdown("**Ranking de intervención · peor salud ecológica primero**")
            _ranked = _real.ranked_by_priority()

        _rows = []
        for t in _ranked:
            row = {
                "Senda":          t.name,
                "Long. (km)":     t.length_km,
                "EHS primavera":  round(t.health_spring, 1) if t.health_spring is not None else None,
                "EHS verano":     round(t.health_summer, 1) if t.health_summer is not None else None,
                "ΔEHS":           round(t.delta_health, 1) if t.delta_health is not None else None,
                "Prioridad":      t.priority_label,
                "Causa (SCM)":    t.scm_label_es,
                "Presupuesto (€)": round(t.budget_eur, 0) if t.budget_eur is not None else None,
            }
            if _has_prug:
                row["Zona PRUG"] = (t.prug_zone or "—").replace("Zona de ", "")
                row["Prioridad PRUG"] = t.priority_index
            _rows.append(row)
        _df = pd.DataFrame(_rows)

        _colcfg = {
            "EHS verano": st.column_config.ProgressColumn(
                "EHS verano", min_value=0, max_value=100, format="%.0f"),
            "EHS primavera": st.column_config.NumberColumn(format="%.0f"),
            "ΔEHS": st.column_config.NumberColumn(
                "ΔEHS", format="%.1f",
                help="Negativo = empeora en verano (caída de NDVI estacional)."),
            "Presupuesto (€)": st.column_config.NumberColumn(format="€%d"),
        }
        if _has_prug:
            _colcfg["Prioridad PRUG"] = st.column_config.ProgressColumn(
                "Prioridad PRUG", min_value=0, max_value=100, format="%.0f",
                help="(100 − salud) × peso de protección PRUG. Mayor = más urgente.")
        st.dataframe(_df, use_container_width=True, hide_index=True, column_config=_colcfg)
        _terr_folder = "sierra_del_rincon" if selected_key == "snr" else "pnsg"
        _carto = ("Cartografía oficial OAPN (sendas homologadas + límite + zonificación PRUG)"
                  if selected_key == "pnsg" else "Cartografía OpenStreetMap")
        st.caption(
            f"Fuente: Pipeline A · Sentinel-2 tile T30TVL · {_carto} · "
            "Salida real, sin datos sintéticos. Provenance: "
            f"`data/outputs/{_terr_folder}/pipeline_a_results.geojson`"
        )
