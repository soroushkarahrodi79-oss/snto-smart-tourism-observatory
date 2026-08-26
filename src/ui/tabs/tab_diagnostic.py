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
    load_timeseries_coverage,
    snapshot_provenance,
    snapshot_status_badge,
)
from src.platform.ehs_presentation import CONDITION_COLOR, condition_legend_items
from src.platform.real_trails import (
    SCM_ATTRIBUTION_CAVEAT,
    SCM_ATTRIBUTION_LABEL,
    build_real_trails_geojson,
    get_park_boundary,
    get_real_trails,
)
from src.platform.views import ConfidenceDetail
from src.risk_engine.ehs import EHS_CONDITION_BANDS
from src.ui.kpi_sections import diagnostic_kpis
from src.ui.render_widgets import render_kpi_grid


def render_tab_diagnostic(
    selected_key,
    _terr_cfg,
    ranked_assets,
    _view,
    dashboard,
    base_comps,
) -> None:
    """Render the Diagnóstico Satelital y Mapa tab (issue #27; fuses 2 blocks)."""
    st.subheader("Diagnóstico Satelital y Mapa — Visión Espacial del Territorio")
    st.caption(
        "Corazón científico del observatorio: el mapa territorial (gestión / "
        "diagnóstico espectral) y, debajo, las **sendas reales** medidas por "
        "Sentinel-2 (Pipeline A) con su EHS y ΔEHS observados."
    )

    st.markdown("#### Salud del espacio protegido · indicadores de contexto")
    st.caption(
        "Los seis indicadores trasladados desde el panorama ejecutivo informan el "
        "diagnóstico sin competir con las decisiones urgentes. Su badge declara la "
        "clase de evidencia heredada por cada cifra."
    )
    _cost_by_id = {
        comparison.asset_id: comparison.scenarios[
            comparison.best_scenario_code
        ].cost_eur
        for comparison in base_comps
    }
    render_kpi_grid(
        diagnostic_kpis(dashboard.kpis),
        ranked_assets,
        _cost_by_id,
        columns=3,
        context=True,
    )
    st.divider()

    with st.expander("📐 Nota metodológica — índices espectrales, EHS y convención de signo",
                     expanded=_view.section(technical=True)):
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
            "**EHS por senda (Δ entre dos escenas):** se ancla en percentiles de la "
            "*propia escena*, no en constantes arbitrarias:"
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
            "de modo que todo el dashboard usa **alto = sano**. El **ΔEHS = diferencia "
            "de salud entre dos escenas fechadas** (`health_spring − health_summer`, "
            "nombres del código): un ΔEHS negativo indica menor salud en la escena "
            "más tardía. **No es una lectura estacional ni una tendencia** — las dos "
            "escenas están separadas ~8 meses, en años distintos y con dos sensores "
            "(S2A/S2B); sus fechas y sensores reales se muestran arriba (Q-03).\n\n"
            "**Override conservador (Fase 2):** cuando el EHS satelital de la senda es *más "
            "degradado* que el juicio experto, **sobreescribe** al curado y escala tier/alerta; "
            "cuando es *más verde*, se mantiene el curado (posible geología, no degradación)."
        )

    # ── Control de modo de visualización ─────────────────────────────────────
    # F10 Fase 3: el modo por defecto del mapa SIGUE A LA VISTA/AUDIENCIA, el mismo
    # eje "dato crudo vs. decisión" que el resto de la app. Técnica/Auditoría
    # (detalle técnico) abren en ESPECTRAL (NDVI/NDMI crudo); Gestor abre en
    # GESTIÓN (tiers de inversión). El toggle sigue siendo un override manual: la
    # `key` por vista hace que el default se aplique al cambiar de vista y que cada
    # audiencia recuerde su propia elección.
    _default_map_idx = 1 if _view.section(technical=True) else 0
    map_mode = st.radio(
        "Modo de visualización",
        options=["🗂️ Vista de Gestión (Tiers)", "🛰️ Vista de Diagnóstico Espectral (NDVI/NDMI)"],
        index=_default_map_idx,
        horizontal=True,
        key=f"map_mode_{_view.mode.value}",
        help=(
            "**Vista de Gestión:** activos coloreados por tier de prioridad de inversión "
            "(escala neutra índigo→pizarra, NO semafórica). "
            "**Vista Espectral:** gradiente continuo RdYlGn derivado del valor EHS del registro del activo — "
            "simula el contraste espacial de degradación difusa visible en imágenes Sentinel-2, "
            "no es una medición espectral directa sobre este activo."
        ),
    )
    st.caption(
        "🔁 El modo inicial sigue a la vista activa "
        f"(**{_view.label}** → {'Espectral' if _default_map_idx else 'Gestión'}); "
        "puedes cambiarlo libremente aquí."
    )

    spectral_mode = "Espectral" in map_mode

    if spectral_mode:
        _poor_low = EHS_CONDITION_BANDS[1][0]
        _moderate_low = EHS_CONDITION_BANDS[2][0]
        _excellent_low = EHS_CONDITION_BANDS[4][0]
        st.caption(
            "🛰️ Color = gradiente RdYlGn (ColorBrewer) anclado en el valor EHS del registro del activo. "
            f"**Rojo intenso** → EHS < {_poor_low:.0f} (degradación crítica) · "
            f"**Amarillo** → EHS ≈ {_moderate_low:.0f} (zona de transición) · "
            f"**Verde saturado** → EHS > {_excellent_low:.0f} (salud óptima). "
            "Simula el contraste espectral NDVI/NDMI a lo largo del corredor del sendero; "
            "no es una medición espectral directa sobre este activo."
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
            # K-24: deriva de la partición canónica de condición EHS
            # (src.risk_engine.ehs.EHS_CONDITION_BANDS) en vez de una tabla
            # de cortes literal propia de este widget.
            st.markdown("#### Escala EHS Espectral")
            for hex_c, label in condition_legend_items():
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
            _critical_ceiling = EHS_CONDITION_BANDS[1][0]  # POOR band lower bound
            st.caption(
                f"Activos en zona crítica (EHS<{_critical_ceiling:.0f}): "
                f"**{sum(1 for v in ehs_vals if v < _critical_ceiling)}**"
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
        "Ecológica (EHS) de la escena analizada."
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
        _badge = snapshot_status_badge(_prov)
        if _prov.scene_refs:
            _scenes = " · ".join(
                f"{r.sensor_id} · {r.acquisition_date}" for r in _prov.scene_refs
            )
        elif _prov.derived_output_available and not _prov.raw_scenes_available:
            # State B: derived artifact real, but source scenes absent here — do
            # not invent a count. Say plainly it cannot be verified locally.
            _scenes = ("no verificables en este entorno "
                       "(escenas fuente .SAFE ausentes)")
        else:
            _scenes = "—"
        st.markdown(
            f'<div class="snto-evidence-card">'
            f'<span class="snto-evidence-badge" '
            f'style="color:{_badge.color};border-color:{_badge.color}">'
            f'{_badge.emoji} {_badge.label}</span> '
            f'<span class="snto-body-copy">· {_badge.caveat}</span><br/>'
            f'<span class="snto-body-copy">'
            f'<b>Escenas Sentinel-2:</b> {_scenes} &nbsp;·&nbsp; '
            f'<b>Composición:</b> percentiles de escena (P90/P10) &nbsp;·&nbsp; '
            f'<b>Tile:</b> T30TVL</span><br/>'
            f'<span class="snto-body-copy">'
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
                f'<div style="font-size:0.78rem;color:#7a8899">EHS medio (escena)</div>'
                f'<div style="font-size:1.6rem;font-weight:700;color:{_ehs_color}">'
                f'{_ehs_mean if _ehs_mean is not None else "—"}'
                f'<span style="font-size:0.8rem;color:#9aa4af">/100</span></div>',
                unsafe_allow_html=True,
            )
        with k4:
            st.metric("Sendas con ΔEHS < 0 (2 escenas)",
                      s.get("n_degrading_positive_delta", 0),
                      help="Sendas con menor salud en la escena más tardía "
                           "(ΔEHS < 0). Diferencia entre dos escenas fechadas, "
                           "NO un deterioro estacional ni una tendencia (Q-03).")
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
            # K-24: deriva de la partición canónica de condición EHS en vez de
            # una tabla de cortes literal propia de este widget.
            _excellent_low, _good_low, _moderate_low, _poor_low = (
                EHS_CONDITION_BANDS[4][0], EHS_CONDITION_BANDS[3][0],
                EHS_CONDITION_BANDS[2][0], EHS_CONDITION_BANDS[1][0],
            )
            _legend = [
                (CONDITION_COLOR[EHS_CONDITION_BANDS[4][1]], f"≥ {_excellent_low:.0f} · Saludable"),
                (CONDITION_COLOR[EHS_CONDITION_BANDS[3][1]], f"{_good_low:.0f}–{_excellent_low:.0f} · Estable"),
                (CONDITION_COLOR[EHS_CONDITION_BANDS[2][1]], f"{_moderate_low:.0f}–{_good_low:.0f} · Alerta"),
                (CONDITION_COLOR[EHS_CONDITION_BANDS[1][1]], f"{_poor_low:.0f}–{_moderate_low:.0f} · Estrés"),
                (CONDITION_COLOR[EHS_CONDITION_BANDS[0][1]], f"< {_poor_low:.0f} · Crítico"),
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
                f'<div class="snto-evidence-card" style="margin-top:8px">'
                f'<span class="snto-micro-label">⛰ Zonificación PRUG oficial</span><br/>'
                f'<span class="snto-body-copy">'
                f'{_prot} de {len(_real.trails)} sendas discurren por zonas de alta protección '
                f'(Reserva / Uso Restringido). La prioridad de intervención pondera la '
                f'degradación por el nivel de protección del PRUG.</span></div>',
                unsafe_allow_html=True,
            )

        st.divider()

        # ── I-4 (Phase 0.5H): visible evidence legend — separates the REAL
        # environmental indicators from the model-derived SCM attribution
        # *before* the reader reaches the table/tooltip below. ─────────────
        st.markdown(
            '<div class="snto-evidence-card">'
            '<span class="snto-evidence-badge" '
            'style="color:#0F6E56;border-color:#0F6E56">'
            'SENTINEL-2 · DERIVADO</span> '
            '<span class="snto-body-copy">EHS y ΔEHS se derivan de '
            'observaciones Sentinel-2 reales.</span><br/>'
            f'<span class="snto-evidence-badge" '
            f'style="color:#8A5A00;border-color:#8A5A00">'
            f'{SCM_ATTRIBUTION_LABEL}</span> '
            f'<span class="snto-body-copy">{SCM_ATTRIBUTION_CAVEAT}</span>'
            '</div>',
            unsafe_allow_html=True,
        )

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
                "EHS escena temprana": round(t.health_summer, 1) if t.health_summer is not None else None,
                "EHS escena tardía":   round(t.health_spring, 1) if t.health_spring is not None else None,
                "ΔEHS":                round(t.delta_health, 1) if t.delta_health is not None else None,
                "Prioridad":      t.priority_label,
                "Atribución SCM": (
                    f"🧭 {t.scm_label_es}" if t.scm_class else t.scm_label_es
                ),
                "Presupuesto (€)": round(t.budget_eur, 0) if t.budget_eur is not None else None,
            }
            if _has_prug:
                row["Zona PRUG"] = (t.prug_zone or "—").replace("Zona de ", "")
                row["Prioridad PRUG"] = t.priority_index
            _rows.append(row)
        _df = pd.DataFrame(_rows)

        _colcfg = {
            "EHS escena temprana": st.column_config.ProgressColumn(
                "EHS escena temprana", min_value=0, max_value=100, format="%.0f"),
            "EHS escena tardía": st.column_config.NumberColumn(format="%.0f"),
            "ΔEHS": st.column_config.NumberColumn(
                "ΔEHS", format="%.1f",
                help="Negativo = menor salud en la escena más tardía; diferencia "
                     "entre dos escenas fechadas, no estacional (Q-03)."),
            "Atribución SCM": st.column_config.TextColumn(
                "Atribución SCM",
                help=(
                    "Clasificación del modelo SIG sobre observaciones Sentinel-2 "
                    "reales. Es una hipótesis de atribución espacial, no una "
                    "medición causal ni una causa confirmada."
                ),
            ),
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
            "EHS/ΔEHS son indicadores derivados de observaciones Sentinel-2 "
            "reales. La **Atribución SCM** es una clasificación del modelo SIG "
            "calculada sobre esas observaciones; no constituye medición causal "
            "ni causa confirmada. Provenance: "
            f"`data/outputs/{_terr_folder}/pipeline_a_results.geojson`"
        )
