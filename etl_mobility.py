"""
SNTO ETL — Real visitor/mobility feed (v2.2)
============================================
Ingests the **real** MITMA municipal-mobility open data (INE + Orange /
Telefónica / Vodafone) into the curated snapshot the dashboard consumes,
replacing the mock ``etl_tourist_traffic.py``.

Why an owner-run ETL (not a bundled dataset)
--------------------------------------------
The MITMA daily files (``viajes_YYYYMMDD.csv.gz``, pipe-delimited) are multi-GB;
they cannot live in git/the Docker image (same reason the socioeconomic layer
ships a curated JSON snapshot, not its ALMUDENA/INE source). Download the days
you want from https://opendata-movilidad.mitma.es/ (estudios básicos, zoning
"municipios") into ``--src-dir`` and run this script; it writes
``src/mobility/snapshot/mobility.json``. Until then the dashboard falls back to
the labeled curated estimate (``mobility_snapshot_exists()`` is False).

Real schema (2022+ "estudios básicos", municipal zoning)
--------------------------------------------------------
Pipe-delimited (``|``) gzipped CSV. Columns are read **by header name** (robust
to the minor schema drift between MITMA releases); the ones used are:
  ``fecha`` (YYYYMMDD), ``origen`` (zone id), ``destino`` (zone id),
  ``viajes`` (trip count).
Inbound pressure = sum of ``viajes`` where ``destino`` is a PNSG zone and
``origen`` != ``destino`` (residents' internal trips excluded), averaged to
mean **daily** trips over the ingested days, per period key.

Usage
-----
    python etl_mobility.py --src-dir data/mitma/2024 --period 2024
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from src.mobility.loader import PNSG_ZONES_PATH, SNAPSHOT_PATH, load_pnsg_zones
from src.mobility.models import PROXY_CAVEAT

_DELIM = "|"


def _open_maybe_gz(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", newline="")
    return open(path, "rt", encoding="utf-8", newline="")


def _target_zone_ids() -> dict[str, str]:
    """Resolved MITMA zone id -> INE code for the PNSG municipalities.

    Only ``resolved`` zones are used; unresolved (aggregated) municipalities are
    skipped honestly rather than guessed. Extend the reference file's
    ``mitma_zone_id`` from MITMA's ``relacion_ine_zonificacion`` to include them.
    """
    return {
        z.mitma_zone_id: z.ine_code
        for z in load_pnsg_zones()
        if z.resolved and z.mitma_zone_id
    }


def ingest(src_dir: Path, period: str) -> dict:
    """Aggregate inbound trips for the PNSG zones across all files in src_dir."""
    zone_to_ine = _target_zone_ids()
    if not zone_to_ine:
        raise SystemExit(
            "No resolved MITMA zones in the reference crosswalk; nothing to ingest."
        )
    targets = set(zone_to_ine)

    inbound: dict[str, float] = defaultdict(float)  # ine_code -> total inbound trips
    files = sorted(
        p for p in src_dir.iterdir()
        if p.name.startswith("viajes") and (p.suffix in {".gz", ".csv"})
    )
    if not files:
        raise SystemExit(f"No 'viajes*' files found in {src_dir}")

    days: set[str] = set()
    for fp in files:
        with _open_maybe_gz(fp) as fh:
            reader = csv.DictReader(fh, delimiter=_DELIM)
            for row in reader:
                dest = row.get("destino")
                origin = row.get("origen")
                if dest not in targets or origin == dest:
                    continue
                try:
                    trips = float(row.get("viajes", "0") or 0)
                except ValueError:
                    continue
                inbound[zone_to_ine[dest]] += trips
                if row.get("fecha"):
                    days.add(row["fecha"])

    n_days = max(len(days), 1)
    # Mean daily inbound trips over the ingested period (comparable across
    # months of different length).
    names = {z.ine_code: z.name for z in load_pnsg_zones()}
    zones = {
        ine: {
            "mitma_zone_id": next(
                (zid for zid, code in zone_to_ine.items() if code == ine), ine
            ),
            "ine_code": ine,
            "name": names.get(ine, ""),
            "inbound_trips": {period: round(total / n_days, 1)},
            "data_status": "real",
            "caveats": [PROXY_CAVEAT],
        }
        for ine, total in sorted(inbound.items())
    }

    return {
        "schema_version": "1.0",
        "source_period": period,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {
            "name": "MITMA — Estudios de movilidad con Big Data (Open Data)",
            "url": "https://opendata-movilidad.mitma.es/",
            "reference": str(PNSG_ZONES_PATH.name),
            "n_days_ingested": n_days,
        },
        "zones": zones,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Ingest real MITMA municipal mobility.")
    ap.add_argument("--src-dir", required=True, type=Path,
                    help="Directory of downloaded MITMA 'viajes*' municipal files.")
    ap.add_argument("--period", required=True,
                    help="Period key for the aggregate, e.g. '2024' or '2024-07'.")
    ap.add_argument("--out", type=Path, default=SNAPSHOT_PATH)
    args = ap.parse_args()

    snapshot = ingest(args.src_dir, args.period)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"[etl_mobility] wrote {args.out} — {len(snapshot['zones'])} zones, "
        f"period {args.period}, {snapshot['source']['n_days_ingested']} days."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
