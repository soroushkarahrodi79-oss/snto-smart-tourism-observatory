"""
Evidence-class guard for the curated territorial layer (v2.1).

The governing constraint (CLAUDE.md / ADR-004): never blur real, calibrated,
synthetic or simulated evidence. These tests pin, in code, that the curated
fixture layer is machine-tracked as CALIBRATED — and can never silently
promote itself to REAL.
"""
from __future__ import annotations

import json

from src.temporal.manifest import DataStatus, classify_source
from src.territorial.fixtures import build_pnsg_territory, build_territory
from src.territorial.manifest import (
    CURATED_FIELDS,
    TERRITORIAL_LAYER_SOURCE,
    build_territorial_manifest,
)


def test_curated_layer_is_calibrated_never_real() -> None:
    for key, assets in (
        ("pnsg", build_pnsg_territory()),
        ("sierra_rincon", build_territory()),
    ):
        manifest = build_territorial_manifest(key, assets)
        assert manifest.data_status is DataStatus.CALIBRATED
        assert manifest.data_status is not DataStatus.REAL


def test_status_agrees_with_satellite_classifier() -> None:
    # The layer's free-text source must map to the SAME tier through the
    # classifier the satellite SeriesManifest uses — one vocabulary, no drift.
    manifest = build_territorial_manifest("pnsg", build_pnsg_territory())
    assert classify_source(manifest.data_source) is manifest.data_status
    assert manifest.data_source == TERRITORIAL_LAYER_SOURCE


def test_curated_fields_exist_on_the_model() -> None:
    asset = build_pnsg_territory()[0]
    for field_name in CURATED_FIELDS:
        assert hasattr(asset, field_name)


def test_manifest_counts_and_serializes() -> None:
    assets = build_pnsg_territory()
    manifest = build_territorial_manifest("pnsg", assets)
    assert manifest.n_assets == len(assets)

    payload = json.loads(manifest.to_json())
    assert payload["territory_key"] == "pnsg"
    assert payload["data_status"] == "calibrated"
    assert payload["curated_fields"] == list(CURATED_FIELDS)
    assert payload["n_assets"] == len(assets)
    assert payload["caveat"]
