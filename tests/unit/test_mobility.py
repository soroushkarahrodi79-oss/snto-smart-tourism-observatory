"""
Tests for the v2.2 real mobility feed.

Two axes: the ETL parses the real MITMA pipe-delimited schema correctly (against
a small schema-faithful fixture — clearly synthetic, never presented as real
data), and the layer is evidence-honest (real raw trips; CALIBRATED once used as
a pressure proxy; honest fallback when no snapshot exists).
"""
from __future__ import annotations

import json

import etl_mobility
from src.mobility import (
    inbound_pressure_by_ine,
    load_mobility,
    load_pnsg_zones,
    mobility_snapshot_exists,
)
from src.mobility.models import MobilitySnapshot, MobilityZone
from src.temporal.manifest import DataStatus

# Real MITMA municipal schema (2022+): pipe-delimited, header-named columns.
_HEADER = "fecha|periodo|origen|destino|distancia|viajes|viajes_km"


def _write_viajes(dir_path, rows: list[str]) -> None:
    (dir_path / "viajes_20240701.csv").write_text(
        _HEADER + "\n" + "\n".join(rows) + "\n", encoding="utf-8"
    )


def test_reference_crosswalk_is_real_and_loads() -> None:
    zones = load_pnsg_zones()
    by_ine = {z.ine_code: z for z in zones}
    # Verified verbatim from the MITMA zoning file (2026-07-21).
    assert by_ine["28038"].mitma_zone_id == "28038"  # Cercedilla
    assert by_ine["28093"].mitma_zone_id == "28093"  # Navacerrada
    # Aggregated municipalities are declared unresolved, not guessed.
    assert by_ine["28120"].resolved is False  # Rascafría


def test_etl_aggregates_inbound_trips_excluding_internal(tmp_path) -> None:
    _write_viajes(tmp_path, [
        # inbound to Cercedilla (28038) from elsewhere → counted
        "20240701|0|28079|28038|10-50|120.0|3000",
        "20240701|0|28093|28038|2-10|80.0|400",
        # internal Cercedilla→Cercedilla → excluded (residents)
        "20240701|0|28038|28038|0.5-2|500.0|300",
        # inbound to a non-PNSG zone → ignored
        "20240701|0|28079|28006|10-50|999.0|9000",
    ])
    snap = etl_mobility.ingest(tmp_path, period="2024-07")
    cerce = snap["zones"]["28038"]
    # 120 + 80 = 200 inbound trips over 1 day → mean daily 200.0
    assert cerce["inbound_trips"]["2024-07"] == 200.0
    assert cerce["data_status"] == "real"
    assert cerce["caveats"]  # proxy caveat attached


def test_etl_output_roundtrips_through_loader(tmp_path) -> None:
    _write_viajes(tmp_path, ["20240701|0|28079|28093|10-50|55.0|1200"])
    snap_dict = etl_mobility.ingest(tmp_path, period="2024")
    out = tmp_path / "mobility.json"
    out.write_text(json.dumps(snap_dict, ensure_ascii=False), encoding="utf-8")

    assert mobility_snapshot_exists(out) is True
    load_mobility.cache_clear()
    snap = load_mobility(out)
    assert isinstance(snap, MobilitySnapshot)
    assert snap.by_ine("28093").annual("2024") == 55.0


def test_missing_snapshot_is_honest_none(tmp_path) -> None:
    load_mobility.cache_clear()
    assert mobility_snapshot_exists(tmp_path / "nope.json") is False
    assert load_mobility(tmp_path / "nope.json") is None


# ── Evidence discipline ────────────────────────────────────────────────────


def _snap_with(ine: str, year: str, trips: float) -> MobilitySnapshot:
    return MobilitySnapshot(
        schema_version="1.0", source_period=year, generated_at="",
        source={}, zones={
            ine: MobilityZone(mitma_zone_id=ine, ine_code=ine, name="X",
                              inbound_trips={year: trips})
        },
    )


def test_raw_trips_are_real_but_pressure_is_calibrated() -> None:
    snap = _snap_with("28038", "2024", 200.0)
    # Raw zone datum is a REAL observation.
    assert snap.by_ine("28038").data_status is DataStatus.REAL
    # Used as a pressure signal, it is downgraded to CALIBRATED (a proxy).
    signals = inbound_pressure_by_ine("2024", snapshot=snap)
    assert signals["28038"].data_status is DataStatus.CALIBRATED
    assert signals["28038"].inbound_trips == 200.0
    assert signals["28038"].caveat


def test_pressure_bridge_returns_none_without_snapshot() -> None:
    # None → callers keep the labeled curated estimate; never blurred.
    assert inbound_pressure_by_ine("2024", snapshot=None) is None


def test_absent_year_is_omitted_not_zeroed() -> None:
    snap = _snap_with("28038", "2024", 200.0)
    # A year with no datum yields no signal (absence != zero pressure).
    assert inbound_pressure_by_ine("2099", snapshot=snap) is None
