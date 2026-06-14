"""
SNTO — Municipality name/code mapping (F9)
===========================================
The socioeconomic sources use three different identifiers for the same place:

  - INE padrón / boundaries / crosswalk : INE municipal code (e.g. "28038")
  - ALMUDENA fichas                     : codMunZona      (e.g. "0382")
  - TerritorialAsset.region             : a free-text name ("Manzanares El Real")

This module loads the authoritative crosswalk and exposes name normalisation so
any of the three can be resolved to the canonical **INE code**.

The crosswalk file ships with the curated PNSG data package:
    data/raw_assets/raster_data/PNSG/Datos complementarios/data/processed/
    tabla_correspondencia_municipios_pnsg.csv
"""
from __future__ import annotations

import csv
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Repo root = three parents up from src/socioeconomic/mapping.py
_REPO_ROOT = Path(__file__).resolve().parents[2]
CROSSWALK_PATH = (
    _REPO_ROOT
    / "data" / "raw_assets" / "raster_data" / "PNSG"
    / "Datos complementarios" / "data" / "processed"
    / "tabla_correspondencia_municipios_pnsg.csv"
)


@dataclass(frozen=True)
class CrosswalkRow:
    ine_code: str
    name: str
    province: str
    pnsg_zone: str               # "PN" | "ZPP"
    almudena_code: Optional[str]  # None for Segovia / special entities
    padron_table: Optional[str]   # INE table id: "2881" (Madrid) | "2894" (Segovia)
    notes: str = ""


def normalize_name(name: str) -> str:
    """
    Canonical comparison key for a municipality name.

    Strips accents/case/punctuation and rewrites the INE "trailing article"
    convention so the same place matches across sources:
        "Molinos, Los"  / "Molinos (Los)"  / "Los Molinos"   -> "los molinos"
        "Boalo, El"     / "Boalo (El)"     / "El Boalo"       -> "el boalo"
        "Acebeda, La"   / "La Acebeda"                        -> "la acebeda"
    """
    s = name.strip()

    # "Name, Article" or "Name (Article)" -> "Article Name"
    for sep in (", ", " ("):
        if sep in s:
            head, _, tail = s.partition(sep)
            tail = tail.rstrip(")").strip()
            if tail.lower() in {"el", "la", "los", "las"}:
                s = f"{tail} {head}"
            break

    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = "".join(c if c.isalnum() or c.isspace() else " " for c in s)
    return " ".join(s.split())


def load_crosswalk(path: Path | None = None) -> list[CrosswalkRow]:
    """Load the 34-municipality PNSG crosswalk (skips the non-municipal entity)."""
    path = path or CROSSWALK_PATH
    rows: list[CrosswalkRow] = []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            ine = (r.get("ine_code") or "").strip()
            if not ine or ine.lower() == "s/c":   # skip Los Baldíos (no INE code)
                continue
            almudena = (r.get("codigo_almudena") or "").strip() or None
            padron = (r.get("padron_tabla_ine") or "").strip() or None
            rows.append(
                CrosswalkRow(
                    ine_code=ine,
                    name=(r.get("municipio") or "").strip(),
                    province=(r.get("provincia") or "").strip(),
                    pnsg_zone=(r.get("zona_pnsg") or "").strip(),
                    almudena_code=almudena,
                    padron_table=padron,
                    notes=(r.get("notas") or "").strip(),
                )
            )
    return rows


def build_name_index(rows: list[CrosswalkRow]) -> dict[str, str]:
    """normalised name -> ine_code (for resolving asset.region)."""
    return {normalize_name(r.name): r.ine_code for r in rows}


def region_to_ine(region: str, rows: list[CrosswalkRow] | None = None) -> Optional[str]:
    """Resolve a TerritorialAsset.region free-text name to its INE code, or None."""
    rows = rows if rows is not None else load_crosswalk()
    return build_name_index(rows).get(normalize_name(region))
