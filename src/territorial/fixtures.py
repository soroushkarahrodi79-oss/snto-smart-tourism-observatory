"""
Territory data fixtures (Sierra del Rincón, PNSG) — Fase 4, paso 0.

Moved verbatim out of app.py (issue #27, modularización): these two builders
are pure calibration/demo data (hardcoded TerritorialAsset instances), zero
Streamlit coupling, so they are the safest and highest-leverage first cut of
the modularization — no behavior change, just a location change.

``build_territory`` seeds the Sierra del Rincón (SNR) pilot territory;
``build_pnsg_territory`` seeds the PNSG (Parque Nacional Sierra de
Guadarrama), the observatory's principal territory since v1.1.
"""
from __future__ import annotations

from src.territorial.models import AssetType, TerritorialAsset


def build_territory() -> list[TerritorialAsset]:
    """
    20 activos reales de la Reserva de la Biosfera Sierra del Rincón (Madrid).

    Distribución de tiers calibrada contra el motor TPI:
      Tier 1 (Atención Inmediata) — 5 activos: presión turística alta, EHS < 45
      Tier 2 (Acción Preventiva)  — 6 activos: señales de alerta, EHS 50-65
      Tier 3 (Monitorización)     — 5 activos: estables, TPI < 38
      Tier 4 (Promoción Activa)   — 4 activos: EHS ≥ 75, riesgo bajo, DCS ≥ 55
    """
    return [

        # ── TIER 1 · Atención Inmediata ───────────────────────────────────────
        # Activadores garantizados: alert CRITICAL/URGENT + EHS < 45 + TPI > 50
        # Para KPI-7 (Human Pressure Alerts 🔴): todos con LOCALIZED_IMPACT
        # ──────────────────────────────────────────────────────────────────────

        # TPI ≈ 95 | CU=40(CRITICAL) + ES=20.5 + SV=19.3 + CC=15
        TerritorialAsset(
            asset_id="snr-nat-001",
            name="Hayedo de Montejo — Zona Periférica",
            asset_type=AssetType.NATURAL_PARK, region="Montejo de la Sierra",
            ehs=38.0, risk_score=0.74, dcs=82.0,
            alert_level="CRITICAL_INTERVENTION",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="HIGH",
            trend_direction="decreasing", mk_p_value=0.008,
            visitor_capacity_annual=45_000, economic_importance=0.95,
            accessibility_score=0.92,
            elevation_m=1_220, area_ha=102.0,
            description=(
                "Zona de amortiguamiento del Hayedo. Desbordamiento de visitantes "
                "fuera del sistema de reserva gestionado: pisoteo de regenerado, "
                "compactación de suelo y alteración de la regeneración natural del haya."
            ),
        ),

        # TPI ≈ 89 | CU=40(CRITICAL) + ES=19.0 + SV=14.8 + CC=15
        TerritorialAsset(
            asset_id="snr-rec-001",
            name="Área Recreativa Vado de Montejo",
            asset_type=AssetType.RECREATIONAL_AREA, region="Montejo de la Sierra",
            ehs=33.0, risk_score=0.79, dcs=76.0,
            alert_level="CRITICAL_INTERVENTION",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="HIGH",
            trend_direction="decreasing", mk_p_value=0.004,
            visitor_capacity_annual=28_000, economic_importance=0.78,
            accessibility_score=0.88,
            elevation_m=950, area_ha=8.5,
            description=(
                "Punto de baño en el nacimiento del Jarama. Saturación extrema en "
                "verano: vertidos, compactación de ribera y deterioro de la vegetación "
                "helofítica. Sin control de aforo ni guardería ambiental."
            ),
        ),

        # TPI ≈ 86 | CU=40(URGENT+declining, EHS<40 → factor=1.0) + ES=19.75 + SV=11.7 + CC=15
        TerritorialAsset(
            asset_id="snr-trail-001",
            name="Cascada del Chorrón — La Hiruela",
            asset_type=AssetType.TRAIL, region="La Hiruela",
            ehs=36.0, risk_score=0.77, dcs=79.0,
            alert_level="URGENT_MONITORING",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="HIGH",
            trend_direction="decreasing", mk_p_value=0.011,
            visitor_capacity_annual=18_000, economic_importance=0.65,
            accessibility_score=0.78,
            elevation_m=1_380, length_km=2.4,
            description=(
                "Cascada descubierta por redes sociales (~2019). El sendero de acceso "
                "carece de balizamiento; erosión severa en las riberas por atajos "
                "improvisados y pisoteo directo del cauce."
            ),
        ),

        # TPI ≈ 86 | CU=40(URGENT+declining) + ES=18.25 + SV=13.1 + CC=15
        TerritorialAsset(
            asset_id="snr-view-001",
            name="Mirador del Cancho de la Cabra",
            asset_type=AssetType.VIEWPOINT, region="Puebla de la Sierra",
            ehs=41.0, risk_score=0.70, dcs=73.0,
            alert_level="URGENT_MONITORING",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="HIGH",
            trend_direction="decreasing", mk_p_value=0.019,
            visitor_capacity_annual=22_000, economic_importance=0.72,
            accessibility_score=0.82,
            elevation_m=1_450,
            description=(
                "Mirador rocoso en la divisoria de Puebla de la Sierra. Acceso ilegal "
                "de vehículos todoterreno que abre pistas en la ladera; erosión laminar "
                "activa en el área de aparcamiento informal."
            ),
        ),

        # TPI ≈ 92 | CU=40(URGENT+declining) + ES=20.25 + SV=16.3 + CC=15
        TerritorialAsset(
            asset_id="snr-trail-002",
            name="Senda de los Hayas — Acceso Norte Hayedo",
            asset_type=AssetType.TRAIL, region="Montejo de la Sierra",
            ehs=42.0, risk_score=0.68, dcs=81.0,
            alert_level="URGENT_MONITORING",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="HIGH",
            trend_direction="decreasing", mk_p_value=0.015,
            visitor_capacity_annual=32_000, economic_importance=0.88,
            accessibility_score=0.90,
            elevation_m=1_180, length_km=4.8,
            description=(
                "Principal corredor de acceso al Hayedo de Montejo por el norte. "
                "Afluencia masiva en otoño (foliación). Sendero multisendas por "
                "atajos; erosión remontante activa en al menos tres puntos críticos."
            ),
        ),

        # ── TIER 2 · Acción Preventiva ────────────────────────────────────────
        # EHS 50-65, alert PREVENTIVE_ACTION, TPI 42-62 (≥ 38, < 50 en muchos)
        # ──────────────────────────────────────────────────────────────────────

        # TPI ≈ 61 | CU=26.4(PREV+dec) + ES=17.0 + SV=7.8 + CC=10
        TerritorialAsset(
            asset_id="snr-trail-003",
            name="Senda de los Carboneros — Horcajuelo",
            asset_type=AssetType.TRAIL, region="Horcajuelo de la Sierra",
            ehs=58.0, risk_score=0.47, dcs=68.0,
            alert_level="PREVENTIVE_ACTION",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="MODERATE",
            trend_direction="decreasing", mk_p_value=0.038,
            visitor_capacity_annual=8_000, economic_importance=0.48,
            accessibility_score=0.60,
            elevation_m=1_080, length_km=6.2,
            description=(
                "Antigua ruta de arrieros y carboneros que conecta Horcajuelo con la "
                "sierra. Señales tempranas de erosión lineal y daño en el talud. "
                "Sin intervención, escalaría a Tier 1 en 2-3 años."
            ),
        ),

        # TPI ≈ 56 | CU=22.0(PREV+dec) + ES=18.0 + SV=7.8 + CC=8
        TerritorialAsset(
            asset_id="snr-nat-002",
            name="Hayedo de Robregordo",
            asset_type=AssetType.NATURAL_PARK, region="Robregordo",
            ehs=54.0, risk_score=0.52, dcs=72.0,
            alert_level="PREVENTIVE_ACTION",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="MODERATE",
            trend_direction="decreasing", mk_p_value=0.044,
            visitor_capacity_annual=6_500, economic_importance=0.55,
            accessibility_score=0.55,
            elevation_m=1_310, area_ha=38.0,
            description=(
                "Rodal de hayas secundario junto a Robregordo, sin régimen de reserva. "
                "Estrés térmico creciente (borde sur de distribución del haya) combinado "
                "con pisoteo difuso sin canalizar."
            ),
        ),

        # TPI ≈ 55 | CU=20.0(PREV) + ES=16.25 + SV=8.7 + CC=10
        TerritorialAsset(
            asset_id="snr-view-002",
            name="Mirador de La Hiruela — Cresta Norte",
            asset_type=AssetType.VIEWPOINT, region="La Hiruela",
            ehs=61.0, risk_score=0.44, dcs=65.0,
            alert_level="PREVENTIVE_ACTION",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="MODERATE",
            trend_direction="no_trend", mk_p_value=0.12,
            visitor_capacity_annual=9_500, economic_importance=0.52,
            accessibility_score=0.68,
            elevation_m=1_340,
            description=(
                "Mirador sobre el pueblo más alto de la reserva con vistas al "
                "macizo de Ayllón. Presión moderada; vegetación rupícola en la "
                "plataforma de observación con señales de pisoteo."
            ),
        ),

        # TPI ≈ 47 | CU=20.0(PREV) + ES=15.25 + SV=7.0 + CC=5
        TerritorialAsset(
            asset_id="snr-trail-004",
            name="Ruta del Vértice Cabeza Mediana",
            asset_type=AssetType.TRAIL, region="Prádena del Rincón",
            ehs=63.0, risk_score=0.42, dcs=61.0,
            alert_level="PREVENTIVE_ACTION",
            scm_classification="MIXED", scm_confidence="MODERATE",
            trend_direction="no_trend", mk_p_value=0.15,
            visitor_capacity_annual=7_200, economic_importance=0.44,
            accessibility_score=0.52,
            elevation_m=1_620, length_km=9.1,
            description=(
                "Ruta al punto más alto de la reserva (1 620 m). Terreno de pizarra "
                "frágil; primeras señales de apertura de caminos alternativos en la "
                "cumbre durante fines de semana con alta afluencia."
            ),
        ),

        # TPI ≈ 51 | CU=22.0(PREV+dec) + ES=14.5 + SV=10.4 + CC=4
        TerritorialAsset(
            asset_id="snr-rec-002",
            name="Fuente del Cura — Montejo de la Sierra",
            asset_type=AssetType.RECREATIONAL_AREA, region="Montejo de la Sierra",
            ehs=55.0, risk_score=0.50, dcs=58.0,
            alert_level="PREVENTIVE_ACTION",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="LOW",
            trend_direction="decreasing", mk_p_value=0.052,
            visitor_capacity_annual=12_000, economic_importance=0.60,
            accessibility_score=0.82,
            elevation_m=1_020, area_ha=2.5,
            description=(
                "Fuente etnográfica y área de descanso muy frecuentada como punto "
                "de salida al Hayedo. Residuos, compactación del suelo y deterioro "
                "de la cubierta herbácea en el entorno inmediato."
            ),
        ),

        # TPI ≈ 52 | CU=20.0(PREV) + ES=16.0 + SV=6.2 + CC=10
        TerritorialAsset(
            asset_id="snr-heritage-001",
            name="Castro de la Edad del Hierro — La Hiruela",
            asset_type=AssetType.NATURAL_PARK, region="La Hiruela",
            ehs=52.0, risk_score=0.55, dcs=64.0,
            alert_level="PREVENTIVE_ACTION",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="MODERATE",
            trend_direction="no_trend", mk_p_value=0.19,
            visitor_capacity_annual=4_800, economic_importance=0.42,
            accessibility_score=0.48,
            elevation_m=1_410, area_ha=4.2,
            description=(
                "Yacimiento castreño prerromano en cerro testigo con materiales "
                "en superficie. Sin protección perimetral ni señalización; visitantes "
                "entran libremente causando remoción involuntaria de piezas."
            ),
        ),

        # ── TIER 3 · Monitorización Rutinaria ────────────────────────────────
        # NORMAL alert, TPI < 38, condición moderada-buena
        # ──────────────────────────────────────────────────────────────────────

        # TPI ≈ 33 | CU=10.4(NORMAL,70) + ES=14.25 + SV=4.4 + CC=4
        TerritorialAsset(
            asset_id="snr-nat-003",
            name="Bosque de Quejigos — Horcajuelo de la Sierra",
            asset_type=AssetType.NATURAL_PARK, region="Horcajuelo de la Sierra",
            ehs=70.0, risk_score=0.34, dcs=57.0,
            alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="LOW",
            trend_direction="no_trend", mk_p_value=0.28,
            visitor_capacity_annual=2_200, economic_importance=0.30,
            accessibility_score=0.38,
            elevation_m=1_090, area_ha=55.0,
            description=(
                "Bosque mixto de quejigo y melojo en buen estado de conservación. "
                "Presión antrópica baja; monitorización anual de fenología y cobertura "
                "suficiente con recursos actuales."
            ),
        ),

        # TPI ≈ 33 | CU=9.6(NORMAL,68) + ES=15.0 + SV=4.5 + CC=4
        TerritorialAsset(
            asset_id="snr-heritage-002",
            name="Ermita de San Blas — Montejo de la Sierra",
            asset_type=AssetType.VIEWPOINT, region="Montejo de la Sierra",
            ehs=68.0, risk_score=0.36, dcs=60.0,
            alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="LOW",
            trend_direction="no_trend", mk_p_value=0.31,
            visitor_capacity_annual=1_800, economic_importance=0.28,
            accessibility_score=0.45,
            elevation_m=1_050,
            description=(
                "Ermita del s. XVI en alto con vistas a la sierra. Interés cultural "
                "y puntos de observación de flora rupícola. Afluencia baja y estacional; "
                "no requiere intervención activa."
            ),
        ),

        # TPI ≈ 37 | CU=10.6(NORMAL,73) + ES=14.5 + SV=3.5 + CC=8
        TerritorialAsset(
            asset_id="snr-stream-001",
            name="Arroyo de Horcajuelo — Tramo Alto",
            asset_type=AssetType.RECREATIONAL_AREA, region="Horcajuelo de la Sierra",
            ehs=73.0, risk_score=0.31, dcs=58.0,
            alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="MODERATE",
            trend_direction="increasing", mk_p_value=0.36,
            visitor_capacity_annual=1_500, economic_importance=0.25,
            accessibility_score=0.30,
            elevation_m=1_140, area_ha=5.0,
            description=(
                "Tramo fluvial de cabecera con macroinvertebrados indicadores de "
                "calidad alta. Tendencia al alza en los índices bióticos; requiere "
                "solo monitorización hidrológica anual."
            ),
        ),

        # TPI ≈ 32 | CU=10.2(NORMAL,71) + ES=13.75 + SV=4.8 + CC=3
        TerritorialAsset(
            asset_id="snr-view-003",
            name="Mirador de Somosierra — Acceso Reserva",
            asset_type=AssetType.VIEWPOINT, region="Prádena del Rincón",
            ehs=71.0, risk_score=0.33, dcs=55.0,
            alert_level="NORMAL",
            scm_classification="MIXED", scm_confidence="LOW",
            trend_direction="no_trend", mk_p_value=0.25,
            visitor_capacity_annual=2_800, economic_importance=0.32,
            accessibility_score=0.42,
            elevation_m=1_390,
            description=(
                "Punto panorámico en el límite norte de la reserva, junto al Puerto "
                "de Somosierra. Afluencia compartida con el paso de la A-1; sin señales "
                "de presión diferencial sobre la reserva."
            ),
        ),

        # TPI ≈ 32 | CU=9.2(NORMAL,66) + ES=14.5 + SV=3.9 + CC=4
        TerritorialAsset(
            asset_id="snr-heritage-003",
            name="Antigua Nevera — Puebla de la Sierra",
            asset_type=AssetType.VIEWPOINT, region="Puebla de la Sierra",
            ehs=66.0, risk_score=0.38, dcs=58.0,
            alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="LOW",
            trend_direction="no_trend", mk_p_value=0.34,
            visitor_capacity_annual=1_200, economic_importance=0.26,
            accessibility_score=0.38,
            elevation_m=1_240,
            description=(
                "Nevera etnográfica del s. XVIII rehabilitada. Patrimonio cultural "
                "menor, visitas espontáneas ocasionales. Estado constructivo estable; "
                "no requiere intervención prioritaria."
            ),
        ),

        # ── TIER 4 · Promoción Activa ─────────────────────────────────────────
        # Garantía: EHS ≥ 75 AND risk ≤ 0.35 AND DCS ≥ 55 AND trend ≠ decreasing
        # Objetivo: absorber visitantes del Hayedo y diversificar la oferta
        # ──────────────────────────────────────────────────────────────────────

        TerritorialAsset(
            asset_id="snr-trail-005",
            name="Senda del Castañar — La Hiruela",
            asset_type=AssetType.TRAIL, region="La Hiruela",
            ehs=88.0, risk_score=0.18, dcs=78.0,
            alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="HIGH",
            trend_direction="increasing", mk_p_value=0.42,
            visitor_capacity_annual=4_500, economic_importance=0.55,
            accessibility_score=0.70,
            elevation_m=1_280, length_km=5.3,
            description=(
                "Bosque de castaños centenarios poco conocido fuera del ámbito local. "
                "Excelente estado de conservación, senda bien trazada. Capacidad de "
                "absorción real de 4 500 visitantes/año sin impacto apreciable."
            ),
        ),

        TerritorialAsset(
            asset_id="snr-trail-006",
            name="Ruta de los Pueblos Negros — Prádena a Robregordo",
            asset_type=AssetType.TRAIL, region="Robregordo",
            ehs=85.0, risk_score=0.22, dcs=74.0,
            alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="HIGH",
            trend_direction="no_trend", mk_p_value=0.38,
            visitor_capacity_annual=6_800, economic_importance=0.60,
            accessibility_score=0.72,
            elevation_m=1_170, length_km=11.4,
            description=(
                "Itinerario cultural que conecta los pueblos de arquitectura negra "
                "en pizarra de la sierra. Combina patrimonio etnográfico y paisaje; "
                "infrautilizado respecto a su potencial turístico."
            ),
        ),

        TerritorialAsset(
            asset_id="snr-view-004",
            name="Mirador de la Hoya del Espino — Robregordo",
            asset_type=AssetType.VIEWPOINT, region="Robregordo",
            ehs=91.0, risk_score=0.14, dcs=82.0,
            alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="HIGH",
            trend_direction="increasing", mk_p_value=0.48,
            visitor_capacity_annual=3_200, economic_importance=0.50,
            accessibility_score=0.62,
            elevation_m=1_460,
            description=(
                "Balcón natural sobre el valle de la Hoya del Espino prácticamente "
                "desconocido. EHS excelente, paisaje vegetal en recuperación activa "
                "tras el abandono del pastoreo extensivo."
            ),
        ),

        TerritorialAsset(
            asset_id="snr-center-001",
            name="Centro de Interpretación de la Biosfera — Montejo",
            asset_type=AssetType.RECREATIONAL_AREA, region="Montejo de la Sierra",
            ehs=82.0, risk_score=0.24, dcs=88.0,
            alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="HIGH",
            trend_direction="no_trend", mk_p_value=0.44,
            visitor_capacity_annual=8_500, economic_importance=0.72,
            accessibility_score=0.88,
            elevation_m=980, area_ha=3.0,
            description=(
                "Centro de visitantes de la reserva con jardín botánico, exposición "
                "permanente sobre el haya y la biosfera, y punto de reserva para el "
                "Hayedo. Nodo estratégico para redistribuir flujos de visitantes."
            ),
        ),

    ]


def build_pnsg_territory() -> list[TerritorialAsset]:
    """
    8 activos representativos del Parque Nacional Sierra de Guadarrama (Madrid/Segovia).

    Distribución de tiers calibrada contra el motor TPI:
      Tier 1 (Atención Inmediata) — 2 activos: saturación crítica, EHS < 45
      Tier 2 (Acción Preventiva)  — 3 activos: señales de alerta, EHS 50-65
      Tier 3 (Monitorización)     — 2 activos: estables, EHS 65-74
      Tier 4 (Promoción Activa)   — 1 activo:  EHS ≥ 75, riesgo bajo
    """
    return [

        # ── TIER 1 · Atención Inmediata ───────────────────────────────────────

        # TPI ≈ 91 | Laguna más visitada del PNSG — saturación documentada
        TerritorialAsset(
            asset_id="pnsg-nat-001",
            name="Laguna de Peñalara — Zona de Reserva",
            asset_type=AssetType.NATURAL_PARK, region="Rascafría",
            ehs=35.0, risk_score=0.77, dcs=79.0,
            alert_level="CRITICAL_INTERVENTION",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="HIGH",
            trend_direction="decreasing", mk_p_value=0.006,
            visitor_capacity_annual=120_000, economic_importance=0.97,
            accessibility_score=0.88,
            elevation_m=2_020, area_ha=28.0,
            description=(
                "Laguna glaciar de alta montaña, hábitat prioritario de la rana patilarga "
                "(Rana iberica). Presión de visitantes 340% sobre la capacidad de carga "
                "en verano: pisoteo de orillas, eutrofización y alteración de anfibios. "
                "Régimen de acceso sin control efectivo en temporada alta."
            ),
        ),

        # TPI ≈ 87 | Cima masificada en fin de semana — erosión severa en crestas
        TerritorialAsset(
            asset_id="pnsg-view-001",
            name="Cumbre Siete Picos — Acceso Sur",
            asset_type=AssetType.VIEWPOINT, region="Cercedilla",
            ehs=39.0, risk_score=0.73, dcs=74.0,
            alert_level="CRITICAL_INTERVENTION",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="HIGH",
            trend_direction="decreasing", mk_p_value=0.009,
            visitor_capacity_annual=85_000, economic_importance=0.90,
            accessibility_score=0.92,
            elevation_m=2_138,
            description=(
                "El conjunto de las siete cumbres es destino icónico del PNSG. "
                "La combinación de fácil acceso desde Cercedilla y alta afluencia "
                "genera erosión severa en las crestas cuarcíticas: pisoteo de céspedes "
                "de alta montaña, apertura de sendas paralelas y arrastre de suelo. "
                "Degradación acelerada sin protocolo de control de afluencia."
            ),
        ),

        # ── TIER 2 · Acción Preventiva ────────────────────────────────────────

        # TPI ≈ 58 | Travesía de cresta masificada — señales de erosión lineal
        TerritorialAsset(
            asset_id="pnsg-trail-001",
            name="Cuerda Larga — Travesía Integral de Cresta",
            asset_type=AssetType.TRAIL, region="Navacerrada",
            ehs=57.0, risk_score=0.49, dcs=66.0,
            alert_level="PREVENTIVE_ACTION",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="MODERATE",
            trend_direction="decreasing", mk_p_value=0.035,
            visitor_capacity_annual=45_000, economic_importance=0.75,
            accessibility_score=0.82,
            elevation_m=2_230, length_km=14.2,
            description=(
                "La travesía de mayor longitud del parque conecta el Ventisquero de "
                "la Condesa con el Puerto de la Morcuera. Erosión lineal incipiente "
                "en sectores de pizarra friable; sendas alternativas en tramos de cresta "
                "con afluencia concentrada en otoño e invierno."
            ),
        ),

        # TPI ≈ 55 | Área recreativa histórica con presión creciente
        TerritorialAsset(
            asset_id="pnsg-rec-001",
            name="Valle de la Fuenfría — Sector Laguna",
            asset_type=AssetType.RECREATIONAL_AREA, region="Cercedilla",
            ehs=53.0, risk_score=0.53, dcs=61.0,
            alert_level="PREVENTIVE_ACTION",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="MODERATE",
            trend_direction="decreasing", mk_p_value=0.042,
            visitor_capacity_annual=35_000, economic_importance=0.68,
            accessibility_score=0.90,
            elevation_m=1_500, area_ha=42.0,
            description=(
                "Valle glaciar con pinar de pino silvestre y laguna artificial. "
                "Área de referencia para senderismo familiar desde Madrid. "
                "Compactación de suelo en orillas de la laguna y degradación del "
                "sotobosque en zonas de descanso no reguladas."
            ),
        ),

        # TPI ≈ 47 | Puerto de montaña con acceso rodado — conflicto vehículos/senderistas
        TerritorialAsset(
            asset_id="pnsg-view-002",
            name="Collado Ventoso — Puerto de Navacerrada",
            asset_type=AssetType.VIEWPOINT, region="Navacerrada",
            ehs=61.0, risk_score=0.45, dcs=63.0,
            alert_level="PREVENTIVE_ACTION",
            scm_classification="MIXED", scm_confidence="MODERATE",
            trend_direction="no_trend", mk_p_value=0.08,
            visitor_capacity_annual=55_000, economic_importance=0.72,
            accessibility_score=0.95,
            elevation_m=1_860,
            description=(
                "Puerto de carretera con acceso directo desde Madrid (A-6). Alta "
                "afluencia de visitantes sin objetivo de senderismo: congestión de "
                "aparcamiento, suciedad en bordes de carretera y pisoteo del cervunal "
                "en el entorno inmediato del aparcamiento. Sin gestión diferenciada "
                "respecto al parque de la estación de esquí."
            ),
        ),

        # ── TIER 3 · Monitorización Rutinaria ────────────────────────────────

        # TPI ≈ 32 | Hayedo maduro con buena cobertura de datos
        TerritorialAsset(
            asset_id="pnsg-nat-002",
            name="Hayedo del Valle de El Paular",
            asset_type=AssetType.NATURAL_PARK, region="Rascafría",
            ehs=70.0, risk_score=0.34, dcs=67.0,
            alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="MODERATE",
            trend_direction="no_trend", mk_p_value=0.24,
            visitor_capacity_annual=15_000, economic_importance=0.55,
            accessibility_score=0.65,
            elevation_m=1_140, area_ha=80.0,
            description=(
                "Hayedo relicto en el fondo del Valle del Lozoya, uno de los más "
                "meridionales de la Península Ibérica. Presión antrópica controlada; "
                "estado de conservación bueno. Monitorización fenológica anual y "
                "vigilancia de la regeneración natural en el margen sureste."
            ),
        ),

        # TPI ≈ 33 | Senda menos conocida — indicador de recuperación
        TerritorialAsset(
            asset_id="pnsg-trail-002",
            name="Senda Herreros — Collado del Hornillo",
            asset_type=AssetType.TRAIL, region="Manzanares El Real",
            ehs=68.0, risk_score=0.36, dcs=55.0,
            alert_level="NORMAL",
            scm_classification="MIXED", scm_confidence="LOW",
            trend_direction="increasing", mk_p_value=0.32,
            visitor_capacity_annual=12_000, economic_importance=0.44,
            accessibility_score=0.58,
            elevation_m=1_680, length_km=8.6,
            description=(
                "Ruta circular poco frecuentada que asciende desde Manzanares El Real "
                "por el cordal de La Pedriza sur. Tendencia NDVI al alza tras la "
                "reducción del pastoreo extensivo. Cobertura de datos satelitales "
                "parcial (zona de sombra topográfica estacional); DCS bajo."
            ),
        ),

        # ── TIER 4 · Promoción Activa ─────────────────────────────────────────

        TerritorialAsset(
            asset_id="pnsg-rec-002",
            name="Centro de Visitantes El Paular — Valle del Lozoya",
            asset_type=AssetType.RECREATIONAL_AREA, region="Rascafría",
            ehs=85.0, risk_score=0.18, dcs=84.0,
            alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="HIGH",
            trend_direction="no_trend", mk_p_value=0.46,
            visitor_capacity_annual=22_000, economic_importance=0.65,
            accessibility_score=0.85,
            elevation_m=1_120, area_ha=5.0,
            description=(
                "Centro de visitantes del PNSG en el valle del Lozoya. Excelente estado "
                "de conservación del entorno inmediato; jardín etnobotánico y sendas "
                "interpretativas accesibles. Capacidad de absorción real infrautilizada: "
                "nodo estratégico para redistribuir flujos desde Peñalara y Siete Picos."
            ),
        ),

    ]
