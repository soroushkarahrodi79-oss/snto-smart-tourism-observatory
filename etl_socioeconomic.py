"""
SNTO — Socioeconomic ingestion ETL (F9)
========================================
Curates the municipal socioeconomic snapshot for the PNSG from the data package
under ``data/raw_assets/raster_data/PNSG/Datos complementarios/data``:

  - processed/tabla_correspondencia_municipios_pnsg.csv   (crosswalk, 34 munis)
  - raw/almudena/FichaMunicipal_*.md                      (15 Madrid fichas)
  - raw/ine_padron/2881.csv (Madrid) · 2894.csv (Segovia) (padrón 2007–2025)
  - raw/ine_eoatr/.../*.csv                               (turismo rural, zona PNSG)

Outputs (curated, versioned, offline-reproducible):
  - data/clean_assets/socioeconomic/municipalities.json
  - data/clean_assets/socioeconomic/pnsg_tourism_zone.json

Design choices:
  * Population & despoblación come from PADRÓN for ALL 34 municipalities (one
    consistent source spanning Madrid + Segovia).
  * Ageing, tourism employment, second homes, income, GDP, unemployment come
    from ALMUDENA — Madrid only. Segovia stays DEMOGRAPHIC_ONLY (declared).
  * EOATR is only published at the PNSG tourist-zone level, so it is stored as a
    territory-level context file, not per municipality.

Run:  python etl_socioeconomic.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.socioeconomic.mapping import CROSSWALK_PATH, load_crosswalk
from src.socioeconomic.models import DataCompleteness, Municipality

# ── Paths ──────────────────────────────────────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parent
SRC_DATA_ROOT = (
    _REPO_ROOT / "data" / "raw_assets" / "raster_data" / "PNSG"
    / "Datos complementarios" / "data"
)
ALMUDENA_DIR = SRC_DATA_ROOT / "raw" / "almudena"
PADRON_DIR = SRC_DATA_ROOT / "raw" / "ine_padron"
EOATR_DIR = SRC_DATA_ROOT / "raw" / "ine_eoatr"

# Curated snapshot lives INSIDE the package (source-controlled config, ~50 KB),
# not under data/ — data/ is git-ignored and docker-ignored (3.4 GB of rasters).
# Shipping it in src/ guarantees it reaches CI and the Azure image.
OUT_DIR = _REPO_ROOT / "src" / "socioeconomic" / "snapshot"
OUT_MUNICIPALITIES = OUT_DIR / "municipalities.json"
OUT_TOURISM_ZONE = OUT_DIR / "pnsg_tourism_zone.json"

SNAPSHOT_DATE = "2026-06"
ALMUDENA_PROV = f"ALMUDENA Ficha Municipal (descarga {SNAPSHOT_DATE})"


# ── Spanish number parsing ─────────────────────────────────────────────────────
def parse_es_number(token: str) -> Optional[float]:
    """EU format -> float. '1.026.696'->1026696.0; '18,90'->18.9; '****'->None."""
    if token is None:
        return None
    t = token.strip()
    if not t or "*" in t or set(t) <= {"-", " "}:
        return None
    t = t.replace(".", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


# ── ALMUDENA ficha parser (Madrid) ─────────────────────────────────────────────
_ALMUDENA_PATTERNS = {
    # field: (regex, caster)  -> first capture is the MUNICIPIO column value
    "pct_over_65": re.compile(r"Grado de envejecimie\w+\s+([\-\d.,]+)", re.I),
    "tourism_employment": re.compile(
        r"Servicios de distribuci[óo]n y hosteler[íi]a\s+([\-\d.,]+)", re.I
    ),
    "pct_second_homes": re.compile(r"No principales \(%\)\s+([\-\d.,]+)", re.I),
    "gdp_per_capita_eur": re.compile(r"Per c[áa]pita:\s*\(euros\)\s+([\-\d.,]+)", re.I),
    "income_per_capita_eur": re.compile(
        r"Renta Disponible Bruta Municipal\s*\.\s*Per\s+c[áa]pita\s+([\-\d.,]+)", re.I
    ),
    "unemployment_rate_pct": re.compile(r"\n\s*Por 100 hab\s+([\-\d.,]+)", re.I),
}


def parse_almudena_ficha(path: Path) -> dict[str, Optional[float]]:
    text = path.read_text(encoding="utf-8")
    out: dict[str, Optional[float]] = {}
    for field, pat in _ALMUDENA_PATTERNS.items():
        m = pat.search(text)              # first occurrence = municipio column
        out[field] = parse_es_number(m.group(1)) if m else None
    return out


def almudena_code_from_filename(path: Path) -> str:
    # FichaMunicipal_0382_Cercedilla.md -> "0382"
    return path.name.split("_")[1]


def load_almudena_by_code() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for md in sorted(ALMUDENA_DIR.glob("FichaMunicipal_*.md")):
        out[almudena_code_from_filename(md)] = parse_almudena_ficha(md)
    return out


# ── INE padrón parser ──────────────────────────────────────────────────────────
def _read_text_robust(path: Path) -> str:
    """INE CSVs ship in mixed encodings (utf-8-sig or cp1252). Try both."""
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace")


def load_padron(path: Path) -> dict[str, dict[int, int]]:
    """ine_code -> {year: population} from a padrón table (tab-separated)."""
    series: dict[str, dict[int, int]] = {}
    reader = csv.reader(_read_text_robust(path).splitlines(), delimiter="\t")
    next(reader, None)  # header
    for row in reader:
        if len(row) < 4:
            continue
        muni, sexo, periodo, total = row[0], row[1], row[2], row[3]
        if sexo.strip().lower() not in ("total", "ambos sexos"):
            continue  # skip Hombres/Mujeres splits; keep the Total row only
        code = muni.split()[0].strip()
        try:
            year = int(periodo.strip())
        except ValueError:
            continue
        pop = parse_es_number(total)
        if pop is None:
            continue
        series.setdefault(code, {})[year] = int(pop)
    return series


def padron_summary(
    year_pop: dict[int, int],
) -> tuple[Optional[int], Optional[int], Optional[float]]:
    """Return (population_latest, latest_year, pct_change_over_5y)."""
    if not year_pop:
        return None, None, None
    latest = max(year_pop)
    pop = year_pop[latest]
    base_year = latest - 5
    base = year_pop.get(base_year)
    if base:
        change = round((pop - base) / base * 100.0, 2)
    else:
        change = None
    return pop, latest, change


# ── INE EOATR (PNSG tourist zone) ──────────────────────────────────────────────
_PNSG_ZONE = "Parque Nacional Sierra de Guadarrama"
_MONTH_ORDER = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]


def load_eoatr_pnsg() -> dict:
    """Extract the PNSG-zone monthly series from every EOATR csv (oferta/demanda)."""
    out: dict[str, dict] = {}
    for csv_path in sorted(EOATR_DIR.rglob("*.csv")):
        kind = "demanda" if "DEMANDA" in str(csv_path).upper() else "oferta"
        months: dict[str, Optional[float]] = {}
        with open(csv_path, encoding="utf-8-sig", newline="") as fh:
            for row in csv.reader(fh, delimiter="\t"):
                if len(row) >= 3 and row[0].strip() == _PNSG_ZONE:
                    months[row[1].strip()] = parse_es_number(row[2])
        if months:
            ordered = [months.get(m) for m in _MONTH_ORDER]
            present = [v for v in ordered if v is not None]
            out[csv_path.stem] = {
                "kind": kind,
                "source_file": csv_path.name,
                "monthly": {m: months.get(m) for m in _MONTH_ORDER},
                "annual_mean": (
                    round(sum(present) / len(present), 1) if present else None
                ),
            }
    return out


# ── Orchestration ──────────────────────────────────────────────────────────────
def build_municipalities() -> list[Municipality]:
    crosswalk = load_crosswalk()
    almudena = load_almudena_by_code()
    padron_madrid = load_padron(PADRON_DIR / "2881.csv")
    padron_segovia = load_padron(PADRON_DIR / "2894.csv")

    municipalities: list[Municipality] = []
    for row in crosswalk:
        padron = padron_madrid if row.province == "Madrid" else padron_segovia
        pop, year, change = padron_summary(padron.get(row.ine_code, {}))
        year_lo = (year - 5) if year else None
        padron_prov = (
            f"INE Padrón (tabla {row.padron_table}, {year_lo}–{year})"
            if year else f"INE Padrón (tabla {row.padron_table})"
        )

        m = Municipality(
            ine_code=row.ine_code,
            name=row.name,
            province=row.province,
            pnsg_zone=row.pnsg_zone,
            almudena_code=row.almudena_code,
            population=pop,
            population_year=year,
            pop_change_5y_pct=change,
        )
        if pop is not None:
            m.provenance["population"] = padron_prov
            m.provenance["pop_change_5y_pct"] = padron_prov

        # ALMUDENA economic/tourism layer (Madrid only)
        alm = almudena.get(row.almudena_code) if row.almudena_code else None
        if alm:
            _emp = alm["tourism_employment"]
            m.pct_over_65 = alm["pct_over_65"]
            m.tourism_employment = int(_emp) if _emp is not None else None
            m.pct_second_homes = alm["pct_second_homes"]
            m.income_per_capita_eur = alm["income_per_capita_eur"]
            m.gdp_per_capita_eur = alm["gdp_per_capita_eur"]
            m.unemployment_rate_pct = alm["unemployment_rate_pct"]
            m.completeness = DataCompleteness.FULL
            for f in ("pct_over_65", "tourism_employment", "pct_second_homes",
                      "income_per_capita_eur", "gdp_per_capita_eur",
                      "unemployment_rate_pct"):
                if getattr(m, f) is not None:
                    m.provenance[f] = ALMUDENA_PROV
        else:
            m.completeness = DataCompleteness.DEMOGRAPHIC_ONLY
            m.caveats.append("Sin cobertura ALMUDENA: solo demografía (INE padrón).")

        # Quality caveats
        if pop is not None and pop < 1000:
            m.caveats.append(
                "Municipio pequeño (<1.000 hab): indicadores volátiles / "
                "posible secreto estadístico."
            )
        if m.gdp_per_capita_eur is not None and m.gdp_per_capita_eur > 60000:
            m.caveats.append(
                "PIB per cápita atípico: artefacto de municipio muy pequeño, "
                "no usar como señal económica."
            )

        municipalities.append(m)

    return municipalities


def main() -> int:
    if not CROSSWALK_PATH.exists():
        print(f"[ERROR] Crosswalk not found: {CROSSWALK_PATH}", file=sys.stderr)
        return 1

    municipalities = build_municipalities()
    tourism_zone = load_eoatr_pnsg()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    n_full = sum(1 for m in municipalities if m.completeness == DataCompleteness.FULL)
    payload = {
        "schema_version": "1.0",
        "source_snapshot_date": SNAPSHOT_DATE,
        "generated_at": generated_at,
        "n_municipalities": len(municipalities),
        "n_full": n_full,
        "n_demographic_only": len(municipalities) - n_full,
        "sources": {
            "crosswalk": "tabla_correspondencia_municipios_pnsg.csv",
            "demographics": "INE Padrón (tablas 2881 Madrid / 2894 Segovia)",
            "economy_tourism": "ALMUDENA Fichas Municipales (Comunidad de Madrid)",
        },
        "municipalities": {m.ine_code: m.to_dict() for m in municipalities},
    }
    OUT_MUNICIPALITIES.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    OUT_TOURISM_ZONE.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "zone": _PNSG_ZONE,
                "source": (
                    "INE Encuesta de Ocupación en Alojamientos de "
                    "Turismo Rural (EOATR)"
                ),
                "generated_at": generated_at,
                "series": tourism_zone,
            },
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )

    _mun_rel = OUT_MUNICIPALITIES.relative_to(_REPO_ROOT)
    _zone_rel = OUT_TOURISM_ZONE.relative_to(_REPO_ROOT)
    print(f"[OK] {len(municipalities)} municipios -> {_mun_rel}")
    print(f"     FULL={n_full}  DEMOGRAPHIC_ONLY={len(municipalities) - n_full}")
    print(f"[OK] EOATR PNSG zone series ({len(tourism_zone)} files) -> {_zone_rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
