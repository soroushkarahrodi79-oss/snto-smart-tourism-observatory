"""
SNTO — Puente Pipeline A → Observatorio en vivo
================================================
Carga la salida REAL del Pipeline A (EHS / ΔEHS / SCM / presupuesto por senda,
con geometría WGS84 verdadera) y la expone al dashboard de Streamlit.

A diferencia de la vista ejecutiva curada (activos narrativos escritos a mano),
esta capa muestra exactamente lo que la ciencia produce a partir de:
    cartografía de senderos  ×  Sentinel-2 (NDVI/NDMI)  →  fórmulas EHS/ΔEHS/SCM

Entrada (generada por run_pipeline_a_filemode.py):
    data/outputs/<territorio>/pipeline_a_results.geojson
    data/outputs/<territorio>/pipeline_a_summary.json

El dashboard llama get_real_trails(dashboard_key) con "snr" | "pnsg".

CONVENIO DE SCORE — IMPORTANTE
------------------------------
El Pipeline A (calculate_delta_ehs._trail_stress_score) calcula un score de
ESTRÉS/DEGRADACIÓN: stress = 100 × déficit, donde 0 = vegetación sana (sin
estrés) y 100 = máximamente degradada. Las columnas legacy del GeoJSON de
entrada (ehs_spring, ehs_summer, delta_ehs) almacenan ese convenio de estrés.

El observatorio (app.py) habla en convenio de SALUD: alto = sano (Tier 4
promoción = salud ≥ 75), bajo = crítico.

Para que todo el dashboard hable un único idioma, este puente CONVIERTE la
salida del pipeline a salud al cargar, usando la conversión canónica de
src.metrics.semantics (salud = 100 − estrés). Por eso los campos de RealTrail
se llaman health_* y delta_health: contienen SALUD, no estrés. La etiqueta
de marca "EHS" se conserva solo en la UI.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from src.metrics.semantics import delta_stress_to_delta_health, stress_to_health

# Raíz del proyecto: .../src/platform/real_trails.py → subir 3 niveles
_ROOT = Path(__file__).resolve().parents[2]
_OUTPUTS = _ROOT / "data" / "outputs"

# Mapeo clave-de-dashboard → carpeta-de-territorio del pipeline.
# (app.py usa claves cortas "snr"/"pnsg"; el pipeline escribe carpetas largas.)
_DASHBOARD_TO_TERRITORY: dict[str, str] = {
    "snr":  "sierra_del_rincon",
    "pnsg": "pnsg",
}

# ── Clasificación de prioridad por SALUD de verano ────────────────────────────
# Coherente con las bandas ecológicas del proyecto (constants.py: degradado<30,
# sano≥55). Salud baja = vegetación estresada = prioridad alta de intervención.
PRIORITY_BANDS: list[tuple[float, str, str]] = [
    # (umbral_inferior_salud, etiqueta, color_hex)
    (0.0,  "Crítica",     "#c62828"),   # EHS < 30  — degradación severa
    (30.0, "Alta",        "#e65100"),   # 30–45     — estrés marcado
    (45.0, "Media",       "#f9a825"),   # 45–60     — señales de alerta
    (60.0, "Baja",        "#558b2f"),   # 60–75     — estable
    (75.0, "Mínima",      "#2e7d32"),   # ≥ 75      — saludable
]

_SCM_LABEL_ES: dict[str, str] = {
    "LOCALIZED_IMPACT": "Impacto localizado (uso del sendero)",
    "MIXED":            "Causa mixta",
    "LANDSCAPE_DRIVEN": "Forzamiento de paisaje (clima)",
}


@dataclass(frozen=True)
class RealTrail:
    """Una senda real analizada por el Pipeline A.

    Convenio de score: los campos health_* y delta_health están en SALUD
    (0 = crítico, 100 = sano), ya convertidos desde el estrés del pipeline
    vía src.metrics.semantics. delta_health > 0 ⇒ la salud MEJORA en verano.
    """
    trail_id: int
    name: str
    length_km: float
    health_spring: Optional[float]
    health_summer: Optional[float]
    delta_health: Optional[float]
    scm_class: Optional[str]
    budget_eur: Optional[float]
    geometry: dict[str, Any]   # GeoJSON geometry (LineString/MultiLineString) WGS84
    # Enriquecimiento PRUG (solo PNSG; None en territorios sin zonificación)
    prug_zone: Optional[str] = None
    prug_protection_weight: Optional[float] = None
    priority_index: Optional[float] = None   # (100−salud) × peso_protección

    # ── Derivados ──
    @property
    def priority_label(self) -> str:
        return _priority_for_health(self.health_summer)[0]

    @property
    def priority_color(self) -> str:
        return _priority_for_health(self.health_summer)[1]

    @property
    def scm_label_es(self) -> str:
        return _SCM_LABEL_ES.get(self.scm_class or "", "Sin clasificar")

    @property
    def is_degrading(self) -> bool:
        """En convenio de salud, delta_health < 0 ⇒ la salud cae de primavera a verano."""
        return self.delta_health is not None and self.delta_health < 0


def _priority_for_health(health: Optional[float]) -> tuple[str, str]:
    """Devuelve (etiqueta, color) de prioridad para una salud de verano."""
    if health is None:
        return ("Sin dato", "#9e9e9e")
    label, color = PRIORITY_BANDS[0][1], PRIORITY_BANDS[0][2]
    for low, lbl, col in PRIORITY_BANDS:
        if health >= low:
            label, color = lbl, col
    return (label, color)


@dataclass(frozen=True)
class RealTrailDataset:
    """Conjunto de sendas reales de un territorio + su resumen agregado."""
    territory_key: str
    available: bool
    trails: list[RealTrail]
    summary: dict[str, Any]

    def ranked_by_priority(self) -> list[RealTrail]:
        """Sendas ordenadas por urgencia: salud de verano ascendente (peor primero).

        Las sendas sin salud van al final.
        """
        return sorted(
            self.trails,
            key=lambda t: (t.health_summer is None, t.health_summer if t.health_summer is not None else 999),
        )

    def top_degrading(self, n: int = 5) -> list[RealTrail]:
        """Top-N sendas con mayor deterioro estacional (delta_health más negativo)."""
        degrading = [t for t in self.trails if t.delta_health is not None]
        return sorted(degrading, key=lambda t: t.delta_health)[:n]

    @property
    def has_prug(self) -> bool:
        """True si las sendas llevan zonificación PRUG (solo PNSG)."""
        return any(t.priority_index is not None for t in self.trails)

    def ranked_by_priority_index(self) -> list[RealTrail]:
        """Sendas por índice de prioridad combinado (degradación × protección PRUG).

        Mayor índice primero. Si no hay PRUG (p. ej. SNR), cae a salud ascendente.
        """
        if self.has_prug:
            return sorted(
                self.trails,
                key=lambda t: (t.priority_index is None,
                               -(t.priority_index if t.priority_index is not None else -1)),
            )
        return self.ranked_by_priority()


def _output_dir(dashboard_key: str) -> Optional[Path]:
    territory = _DASHBOARD_TO_TERRITORY.get(dashboard_key)
    if territory is None:
        return None
    return _OUTPUTS / territory


def get_real_trails(dashboard_key: str) -> RealTrailDataset:
    """Carga las sendas reales del Pipeline A para una clave de dashboard.

    Args:
        dashboard_key: "snr" o "pnsg".

    Returns:
        RealTrailDataset. Si el pipeline aún no se ha ejecutado para este
        territorio, available=False y trails=[] (el dashboard muestra un aviso).
    """
    outdir = _output_dir(dashboard_key)
    if outdir is None:
        return RealTrailDataset(dashboard_key, False, [], {})

    geojson_path = outdir / "pipeline_a_results.geojson"
    summary_path = outdir / "pipeline_a_summary.json"

    if not geojson_path.exists():
        return RealTrailDataset(dashboard_key, False, [], {})

    fc = json.loads(geojson_path.read_text(encoding="utf-8"))
    summary = (
        json.loads(summary_path.read_text(encoding="utf-8"))
        if summary_path.exists() else {}
    )

    trails: list[RealTrail] = []
    for feat in fc.get("features", []):
        p = feat.get("properties", {})
        # Convenio de SALUD (alto=sano), coherente con el resto del dashboard.
        health_spring = stress_to_health(p.get("ehs_spring"))
        health_summer = stress_to_health(p.get("ehs_summer"))
        # ΔEHS de salud: positivo = mejora, negativo = deterioro de verano.
        delta_health = delta_stress_to_delta_health(p.get("delta_ehs"))
        trails.append(RealTrail(
            trail_id=int(p.get("id", 0)),
            name=p.get("name") or "(sin nombre)",
            length_km=float(p.get("length_km") or 0.0),
            health_spring=health_spring,
            health_summer=health_summer,
            delta_health=delta_health,
            scm_class=p.get("scm_class"),
            budget_eur=p.get("budget_eur"),
            geometry=feat.get("geometry") or {},
            prug_zone=p.get("prug_zone"),
            prug_protection_weight=p.get("prug_protection_weight"),
            priority_index=p.get("priority_index"),
        ))

    # El resumen del pipeline está en convenio de degradación; lo convertimos a
    # salud para que las KPIs del observatorio sean coherentes.
    summary = _summary_to_health(summary)

    return RealTrailDataset(dashboard_key, True, trails, summary)


def _summary_to_health(summary: dict[str, Any]) -> dict[str, Any]:
    """Convierte las métricas EHS del resumen de degradación a salud.

    ehs_summer_mean/min/max: salud = 100 − degradación (y min↔max se intercambian).
    delta_ehs_mean: cambia de signo (salud Δ = −degradación Δ).
    n_degrading_positive_delta: en salud, el deterioro es Δ < 0; lo recalcula
    el dataset desde las sendas, así que aquí lo dejamos como cuenta de deterioro.
    """
    out = dict(summary)
    mean = summary.get("ehs_summer_mean")
    lo = summary.get("ehs_summer_min")
    hi = summary.get("ehs_summer_max")
    if mean is not None:
        out["ehs_summer_mean"] = round(100.0 - mean, 2)
    # min de salud proviene del max de degradación y viceversa
    if hi is not None:
        out["ehs_summer_min"] = round(100.0 - hi, 2)
    if lo is not None:
        out["ehs_summer_max"] = round(100.0 - lo, 2)
    dmean = summary.get("delta_ehs_mean")
    if dmean is not None:
        out["delta_ehs_mean"] = round(-dmean, 2)
    return out


# ── Construcción del GeoJSON coloreado por EHS para el mapa ────────────────────

def _health_to_rgba(health: Optional[float], alpha: int = 230) -> list[int]:
    """Color RdYlGn por salud (rojo=degradado, verde=sano). Gris si no hay dato."""
    if health is None:
        return [158, 158, 158, alpha]
    # Rampa diverging de 5 clases anclada a las bandas ecológicas.
    ramp = [
        (0.0,   [165,  0,  38]),
        (30.0,  [215, 48,  39]),
        (45.0,  [253, 174, 97]),
        (60.0,  [255, 255, 191]),
        (75.0,  [166, 217, 106]),
        (100.0, [ 26, 152,  80]),
    ]
    e = max(0.0, min(100.0, health))
    for i in range(len(ramp) - 1):
        lo_v, lo_c = ramp[i]
        hi_v, hi_c = ramp[i + 1]
        if lo_v <= e <= hi_v:
            t = (e - lo_v) / (hi_v - lo_v) if hi_v != lo_v else 0.0
            return [int(lo_c[j] + t * (hi_c[j] - lo_c[j])) for j in range(3)] + [alpha]
    return [128, 128, 128, alpha]


_OAPN_DIR = _ROOT / "data" / "raw_assets" / "vector_data" / "oapn"

# Límite oficial del parque por clave de dashboard (solo PNSG tiene capa OAPN).
_BOUNDARY_FILE: dict[str, str] = {
    "pnsg": "oapn_limite_pn.geojson",
}


def get_park_boundary(dashboard_key: str) -> Optional[dict[str, Any]]:
    """Devuelve el FeatureCollection del límite oficial del parque, o None.

    Fuente: capa oficial OAPN descargada por etl_oapn_wfs.py. Solo disponible
    para territorios con límite publicado (PNSG). Se usa como contorno en el mapa.
    """
    fname = _BOUNDARY_FILE.get(dashboard_key)
    if not fname:
        return None
    path = _OAPN_DIR / fname
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def build_real_trails_geojson(dataset: RealTrailDataset) -> dict[str, Any]:
    """FeatureCollection con geometría real coloreada por salud, lista para PyDeck."""
    features = []
    for t in dataset.trails:
        if not t.geometry:
            continue
        color = _health_to_rgba(t.health_summer)
        features.append({
            "type": "Feature",
            "geometry": t.geometry,
            "properties": {
                "name": t.name,
                "length_km": t.length_km,
                "health_summer": round(t.health_summer, 1) if t.health_summer is not None else "—",
                "delta_health": round(t.delta_health, 1) if t.delta_health is not None else "—",
                "scm": t.scm_label_es,
                "priority": t.priority_label,
                "budget": f"€{t.budget_eur:,.0f}" if t.budget_eur is not None else "—",
                "prug": t.prug_zone or "—",
                "line_color": color,
            },
        })
    return {"type": "FeatureCollection", "features": features}
