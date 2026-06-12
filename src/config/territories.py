"""
SNTO — Territory Registry
=========================
Central definition of all observatory territories. Each entry carries the
study-area bounding box (WGS 84, W S E N), the Sentinel-2 tile code, and
human-readable metadata used by ETL scripts and pipeline reports.

Adding a new territory
----------------------
1. Add a TerritoryConfig entry to TERRITORIES.
2. Place raw Sentinel-2 .SAFE folders under
       data/raw_assets/raster_data/<folder_name>/
3. Run prepare_raster.py --territory <key> ... to populate
       data/clean_assets/<key>/
4. Register vector layers in etl_vector_cleaner.py if available.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class TerritoryConfig:
    key: str                              # unique slug used in CLI flags and paths
    display_name: str
    bbox_wgs84: tuple[float, float, float, float]  # (W, S, E, N)
    s2_tile: str                          # Sentinel-2 MGRS tile (e.g. "T30TVL")
    raw_raster_folder: str                # sub-folder under data/raw_assets/raster_data/
    protection_category: str             # e.g. "Biosphere Reserve", "National Park"
    region: str = "Comunidad de Madrid"
    country: str = "Spain"
    notes: str = ""
    # Optional external data sources available for this territory
    external_sources: list[str] = field(default_factory=list)


# ── Registered territories ─────────────────────────────────────────────────────

TERRITORIES: dict[str, TerritoryConfig] = {

    "sierra_del_rincon": TerritoryConfig(
        key="sierra_del_rincon",
        display_name="Reserva de la Biosfera Sierra del Rincón",
        bbox_wgs84=(-3.65, 41.05, -3.30, 41.20),
        s2_tile="T30TVL",
        raw_raster_folder="Sierra del Rincón",
        protection_category="Biosphere Reserve (UNESCO MAB)",
        notes="Pilot territory. Small municipalities: Montejo de la Sierra, "
              "Prádena del Rincón, La Hiruela, Horcajuelo de la Sierra, Madarcos.",
        external_sources=["INE — padrón municipal", "OSM — senderos"],
    ),

    "pnsg": TerritoryConfig(
        key="pnsg",
        display_name="Parque Nacional Sierra de Guadarrama",
        # Full park boundary (Madrid + Segovia sides). For Madrid-only analysis
        # tighten to (-3.98, 40.68, -3.58, 41.05).
        bbox_wgs84=(-4.21, 40.65, -3.58, 41.08),
        s2_tile="T30TVL",
        raw_raster_folder="PNSG",
        protection_category="National Park (Red de Parques Nacionales)",
        notes="Larger territory with diverse municipalities: Cercedilla, "
              "Navacerrada, Guadarrama, Los Molinos, Collado Mediano, "
              "Manzanares el Real, Rascafría, Lozoya. "
              "Straddles Madrid and Castilla y León (Segovia). "
              "Richer socioeconomic data available via ALMUDENA and INE.",
        external_sources=[
            "ALMUDENA (Comunidad de Madrid IDE) — parcelas, usos del suelo, "
            "red viaria, edificios: https://www.comunidad.madrid/servicios/mapas/descarga-datos",
            "INE — Censo 2021, padrón municipal, estadística de turismo rural: "
            "https://www.ine.es/dyngs/INEbase/es/categoria.htm?c=Estadistica_P&cid=1254734710984",
            "MITERD OAPN — límite administrativo PNSG, ZEC, senderos oficiales: "
            "https://www.miteco.gob.es/es/red-parques-nacionales/nuestros-parques/guadarrama/",
            "OSM — red de senderos, miradores, aparcamientos",
        ],
    ),
}


def get(key: str) -> TerritoryConfig:
    """Return a TerritoryConfig by key, raising KeyError with a helpful message."""
    if key not in TERRITORIES:
        available = ", ".join(sorted(TERRITORIES))
        raise KeyError(
            f"Unknown territory '{key}'. Available: {available}"
        )
    return TERRITORIES[key]


def list_keys() -> list[str]:
    return sorted(TERRITORIES)
