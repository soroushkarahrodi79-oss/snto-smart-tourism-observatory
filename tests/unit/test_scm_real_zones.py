"""
Tests for the v2.2 SCM real-zone path.

Pins the evidence gate: attribution from observed zones is REAL, from the
α-decay fallback is SIMULATED, and the two are never confused — plus the honest
loader gate and the analyse_asset factory's prefer-real-else-simulate rule.
"""
from __future__ import annotations

import json

from src.assets.models import AssetObservation
from src.platform.evidence import EvidenceClass
from src.spatial_causality import analyse_asset, load_real_zones, real_zones_exist
from src.spatial_causality.analyzer import evidence_class_for_source


def _obs(n: int = 24) -> list[AssetObservation]:
    """A single-buffer monthly series with a mild seasonal cycle."""
    import math

    out = []
    for i in range(n):
        ndvi = 0.55 + 0.12 * math.sin(2 * math.pi * i / 12)
        out.append(AssetObservation(
            asset_id="a1", year=2021 + i // 12, month=(i % 12) + 1,
            ndvi=round(ndvi, 4), ndmi=round(ndvi * 0.5, 4), data_source="gee",
        ))
    return out


def _write_zones(base, asset_id: str) -> None:
    def series(scale):
        return [
            {"year": 2021 + i // 12, "month": (i % 12) + 1,
             "ndvi": round(0.55 * scale, 4), "ndmi": round(0.28 * scale, 4)}
            for i in range(24)
        ]
    payload = {
        "asset_id": asset_id,
        "zones": {
            "core": series(0.90),       # core more degraded
            "near": series(0.96),
            "landscape": series(1.00),
        },
    }
    (base / f"{asset_id}.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


# ── Evidence gate ──────────────────────────────────────────────────────────


def test_evidence_class_maps_source() -> None:
    assert evidence_class_for_source("scm_simulated:core") is EvidenceClass.SIMULATED
    assert evidence_class_for_source("scm_real:core") is EvidenceClass.REAL
    assert evidence_class_for_source("gee") is EvidenceClass.REAL
    assert evidence_class_for_source("sentinel-2") is EvidenceClass.REAL
    # Unknown defaults to SIMULATED — never over-claims REAL.
    assert evidence_class_for_source("unknown") is EvidenceClass.SIMULATED


def test_simulated_fallback_is_labelled_simulated() -> None:
    result = analyse_asset("no-zones-asset", _obs())
    assert result.evidence_class is EvidenceClass.SIMULATED
    assert "simulated" in result.data_source


# ── Real-zone loader gate ──────────────────────────────────────────────────


def test_loader_returns_none_when_absent(tmp_path) -> None:
    assert real_zones_exist("x", base=tmp_path) is False
    load_real_zones.cache_clear()
    assert load_real_zones("x", base=tmp_path) is None


def test_loader_reads_all_three_zones(tmp_path) -> None:
    _write_zones(tmp_path, "a1")
    load_real_zones.cache_clear()
    zones = load_real_zones("a1", base=tmp_path)
    assert zones is not None
    assert set(zones) == {"core", "near", "landscape"}
    assert all(o.data_source == "scm_real:core" for o in zones["core"])


def test_loader_rejects_incomplete_export(tmp_path) -> None:
    (tmp_path / "bad.json").write_text(
        json.dumps({"asset_id": "bad", "zones": {"core": [{"year": 2021,
                    "month": 1, "ndvi": 0.5, "ndmi": 0.2}]}}),  # missing zones
        encoding="utf-8",
    )
    load_real_zones.cache_clear()
    assert load_real_zones("bad", base=tmp_path) is None


# ── Factory prefers real zones ─────────────────────────────────────────────


def test_analyse_asset_uses_real_zones_when_present(tmp_path, monkeypatch) -> None:
    import src.spatial_causality.zone_loader as zl

    monkeypatch.setattr(zl, "_ZONES_DIR", tmp_path)
    _write_zones(tmp_path, "a1")
    zl.load_real_zones.cache_clear()

    result = analyse_asset("a1", _obs())
    assert result.evidence_class is EvidenceClass.REAL
    assert "scm_real" in result.data_source
    zl.load_real_zones.cache_clear()
