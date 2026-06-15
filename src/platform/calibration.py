"""
SNTO — Validación cruzada: EHS curado × EHS satelital
======================================================
Triangula el EHS curado (juicio experto de salud ecológica bajo presión
turística) con el EHS satelital REAL del Pipeline A (verdor NDVI/NDMI de la
senda concreta correspondiente). NO sustituye el valor curado: lo VALIDA.

Por qué triangular y no sustituir
---------------------------------
Ambos índices se llaman "EHS" pero miden constructos distintos:
  · Curado    → salud ecológica bajo presión antrópica (juicio experto).
  · Satelital → verdor de la vegetación relativo al paisaje (NDVI/NDMI).

En alta montaña divergen de forma esperable: cumbres cuarcíticas (Siete Picos),
crestas y canchales graníticos (La Pedriza) o accesos a refugios sobre roca
(Peñalara) tienen poco NDVI por GEOLOGÍA, no por degradación turística. Por eso
el satélite NO es una "verdad" que reemplace al juicio experto, sino una segunda
medición independiente. La concordancia (o la divergencia explicada) es el
resultado científico defendible.

Mapeo activo→senda
------------------
_ASSET_TRAIL_MAP asocia cada asset_id curado con subcadenas de nombre que
identifican su(s) senda(s) real(es) concreta(s) en la salida del pipeline.
Solo se mapea donde existe correspondencia toponímica clara; los activos sin
senda pública equivalente (p. ej. núcleos de reserva estricta) quedan SIN_DATO.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.platform.real_trails import get_real_trails, RealTrail

# Banda de concordancia: |EHS_curado − EHS_satélite| ≤ 12 → se consideran de acuerdo.
# 12 ≈ anchura de medio tier; tolera ruido de medición sin enmascarar divergencias.
CONCORDANCE_BAND: float = 12.0


@dataclass(frozen=True)
class CalibrationResult:
    asset_id: str
    curated_ehs: float
    satellite_ehs: Optional[float]      # media de salud de las sendas mapeadas
    matched_trails: list[str]           # nombres de sendas de referencia
    n_trails: int
    delta: Optional[float]              # satélite − curado
    flag: str                          # "confirma" | "mas_sano" | "mas_degradado" | "sin_dato"

    @property
    def badge(self) -> tuple[str, str, str]:
        """(emoji, etiqueta, color_hex) para la UI."""
        return _FLAG_BADGE[self.flag]


_FLAG_BADGE: dict[str, tuple[str, str, str]] = {
    "confirma":       ("✓", "Satélite confirma",        "#2e7d32"),
    "mas_sano":       ("⚠", "Satélite más verde",       "#e68214"),
    "mas_degradado":  ("⚠", "Satélite más degradado",   "#c62828"),
    "sin_dato":       ("—", "Sin senda equivalente",     "#9e9e9e"),
}


# asset_id → subcadenas de nombre de senda (match si el nombre CONTIENE alguna).
# Conservador: solo correspondencias toponímicas defendibles.
_ASSET_TRAIL_MAP: dict[str, list[str]] = {

    # ── PN Sierra de Guadarrama (correspondencias claras con sendas del parque) ──
    "pnsg-nat-001":  ["Peñalara", "Lagunazo"],            # Laguna de Peñalara y su entorno
    "pnsg-view-001": ["Siete Picos"],                     # Cumbre Siete Picos
    "pnsg-trail-001": ["Cuerda Larga"],                   # Travesía Cuerda Larga
    "pnsg-rec-001":  ["Fuenfría"],                         # Valle de la Fuenfría
    "pnsg-view-002": ["Collado Ventoso",
                      "Guardas - Puerto Navacerrada"],     # Puerto de Navacerrada
    "pnsg-nat-002":  ["Monasterio del Paular",
                      "Batanes", "Hayedos - Lozoya"],       # Hayedo del Valle de El Paular
    "pnsg-trail-002": ["Pedriza", "Yelmo"],               # Senda Herreros / La Pedriza
    "pnsg-rec-002":  ["Monasterio del Paular", "Batanes"], # Centro de Visitantes El Paular

    # ── Sierra del Rincón (cobertura PARCIAL: solo topónimos inequívocos) ────────
    # Los núcleos de reserva estricta (Hayedo de Montejo) y el patrimonio puntual
    # (ermitas, castro, neveras) NO tienen senda pública OSM equivalente → SIN_DATO.
    "snr-trail-001": ["Camino de la Hiruela"],            # Cascada del Chorrón — La Hiruela
    "snr-trail-005": ["Camino de la Hiruela"],            # Senda del Castañar — La Hiruela
    "snr-view-002":  ["Camino de la Hiruela"],            # Mirador de La Hiruela
    "snr-nat-003":   ["Camino de Horcajuelo"],            # Bosque de Quejigos — Horcajuelo
    "snr-trail-003": ["Camino de Horcajuelo"],            # Senda de los Carboneros — Horcajuelo
    "snr-trail-006": ["Camino de Riaza"],                 # Pueblos Negros — Prádena a Robregordo
}


def _classify(curated: float, satellite: Optional[float]) -> str:
    if satellite is None:
        return "sin_dato"
    delta = satellite - curated
    if abs(delta) <= CONCORDANCE_BAND:
        return "confirma"
    return "mas_sano" if delta > 0 else "mas_degradado"


def calibrate_asset(asset_id: str, curated_ehs: float, trails: list[RealTrail]) -> CalibrationResult:
    """Triangula un activo curado con las sendas reales mapeadas."""
    subs = _ASSET_TRAIL_MAP.get(asset_id, [])
    matched = [
        t for t in trails
        if t.health_summer is not None and any(s.lower() in t.name.lower() for s in subs)
    ]
    if not matched:
        return CalibrationResult(
            asset_id=asset_id, curated_ehs=curated_ehs, satellite_ehs=None,
            matched_trails=[], n_trails=0, delta=None, flag="sin_dato",
        )
    sat = round(sum(t.health_summer for t in matched) / len(matched), 1)
    return CalibrationResult(
        asset_id=asset_id,
        curated_ehs=curated_ehs,
        satellite_ehs=sat,
        matched_trails=[t.name for t in matched],
        n_trails=len(matched),
        delta=round(sat - curated_ehs, 1),
        flag=_classify(curated_ehs, sat),
    )


def calibrate_territory(dashboard_key: str, assets: list) -> dict[str, CalibrationResult]:
    """Calibra todos los activos curados de un territorio contra su salida real.

    Args:
        dashboard_key: "snr" | "pnsg".
        assets: lista de TerritorialAsset (deben tener .asset_id y .ehs).

    Returns:
        dict asset_id → CalibrationResult. Si el pipeline no se ha ejecutado,
        todos salen con flag "sin_dato".
    """
    ds = get_real_trails(dashboard_key)
    trails = ds.trails if ds.available else []
    return {
        a.asset_id: calibrate_asset(a.asset_id, a.ehs, trails)
        for a in assets
    }


def asset_trail_geometries(dashboard_key: str, assets: list) -> dict[str, list[dict]]:
    """Geometrías reales (GeoJSON WGS84) de las sendas del Pipeline A asociadas a
    cada activo curado, vía el mismo ``_ASSET_TRAIL_MAP`` que usa la calibración.

    Permite dibujar el activo curado sobre su **traza cartográfica real** en lugar
    del centroide municipal aproximado. A diferencia de ``calibrate_asset`` (que
    exige ``health_summer`` para promediar salud), aquí solo se requiere geometría.

    Returns:
        dict ``asset_id → [geometry, ...]``. Lista vacía si el activo no tiene
        senda equivalente o si el Pipeline A no se ha ejecutado.
    """
    ds = get_real_trails(dashboard_key)
    trails = ds.trails if ds.available else []
    out: dict[str, list[dict]] = {}
    for a in assets:
        subs = _ASSET_TRAIL_MAP.get(a.asset_id, [])
        out[a.asset_id] = [
            t.geometry for t in trails
            if t.geometry and any(s.lower() in t.name.lower() for s in subs)
        ]
    return out


def coverage_summary(results: dict[str, CalibrationResult]) -> dict[str, int]:
    """Recuento por categoría de concordancia, para cabeceras de la UI."""
    out = {"confirma": 0, "mas_sano": 0, "mas_degradado": 0, "sin_dato": 0}
    for r in results.values():
        out[r.flag] += 1
    return out
