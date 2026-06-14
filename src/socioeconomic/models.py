"""
SNTO — Socioeconomic data models (F9)
======================================
A ``Municipality`` is the convergence point of the socioeconomic snapshot:
demographics (INE padrón), tourism/economy (ALMUDENA, Madrid only) and, when
joined downstream, the aggregated environmental risk of its assets.

NORMALISATION
-------------
All raw figures are stored in their natural units (people, euros, %, beds).
Normalisation to [0, 1] for the SVI happens in ``indicators.py`` against the
PNSG cohort, never here — so the snapshot stays a faithful record of the source.

DATA COMPLETENESS
-----------------
ALMUDENA only covers Comunidad de Madrid. The Segovia side of the PNSG therefore
has demographics (padrón) but no municipal tourism/economy figures. Each
municipality declares its completeness so the SVI and the dashboard can be
honest about which index is full and which is demographic-only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DataCompleteness(str, Enum):
    FULL = "FULL"                          # demographics + ALMUDENA economy/tourism
    DEMOGRAPHIC_ONLY = "DEMOGRAPHIC_ONLY"  # padrón only (Segovia side)


@dataclass
class Municipality:
    """One PNSG municipality with its socioeconomic indicators and provenance."""

    # ── Identity (from the crosswalk) ─────────────────────────────────────
    ine_code: str                       # canonical join key (e.g. "28038")
    name: str
    province: str                       # "Madrid" | "Segovia"
    pnsg_zone: str                      # "PN" (parque) | "ZPP" (periférica)
    almudena_code: Optional[str] = None  # codMunZona, Madrid only

    # ── Demographics (INE padrón — available for all municipalities) ───────
    population: Optional[int] = None
    population_year: Optional[int] = None
    pop_change_5y_pct: Optional[float] = None   # despoblación (− = pierde población)

    # ── Demographics (ALMUDENA — Madrid only) ─────────────────────────────
    pct_over_65: Optional[float] = None         # grado de envejecimiento

    # ── Tourism & economy (ALMUDENA — Madrid only) ────────────────────────
    tourism_employment: Optional[int] = None    # afiliados SS hostelería/distribución
    pct_second_homes: Optional[float] = None     # viviendas no principales (%)
    income_per_capita_eur: Optional[float] = None  # renta disponible bruta pc
    gdp_per_capita_eur: Optional[float] = None      # PIB municipal pc
    unemployment_rate_pct: Optional[float] = None   # paro registrado por 100 hab

    # ── Quality & traceability ────────────────────────────────────────────
    completeness: DataCompleteness = DataCompleteness.DEMOGRAPHIC_ONLY
    provenance: dict[str, str] = field(default_factory=dict)  # field -> "source year"
    caveats: list[str] = field(default_factory=list)

    # ── Serialisation ─────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "ine_code": self.ine_code,
            "name": self.name,
            "province": self.province,
            "pnsg_zone": self.pnsg_zone,
            "almudena_code": self.almudena_code,
            "population": self.population,
            "population_year": self.population_year,
            "pop_change_5y_pct": self.pop_change_5y_pct,
            "pct_over_65": self.pct_over_65,
            "tourism_employment": self.tourism_employment,
            "pct_second_homes": self.pct_second_homes,
            "income_per_capita_eur": self.income_per_capita_eur,
            "gdp_per_capita_eur": self.gdp_per_capita_eur,
            "unemployment_rate_pct": self.unemployment_rate_pct,
            "completeness": self.completeness.value,
            "provenance": self.provenance,
            "caveats": self.caveats,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Municipality":
        return cls(
            ine_code=d["ine_code"],
            name=d["name"],
            province=d["province"],
            pnsg_zone=d["pnsg_zone"],
            almudena_code=d.get("almudena_code"),
            population=d.get("population"),
            population_year=d.get("population_year"),
            pop_change_5y_pct=d.get("pop_change_5y_pct"),
            pct_over_65=d.get("pct_over_65"),
            tourism_employment=d.get("tourism_employment"),
            pct_second_homes=d.get("pct_second_homes"),
            income_per_capita_eur=d.get("income_per_capita_eur"),
            gdp_per_capita_eur=d.get("gdp_per_capita_eur"),
            unemployment_rate_pct=d.get("unemployment_rate_pct"),
            completeness=DataCompleteness(d.get("completeness", "DEMOGRAPHIC_ONLY")),
            provenance=d.get("provenance", {}),
            caveats=d.get("caveats", []),
        )
