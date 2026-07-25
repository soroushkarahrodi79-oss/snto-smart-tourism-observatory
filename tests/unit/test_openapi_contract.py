"""Contracts for the published OpenAPI document (v3.0, ADR-008).

The non-negotiables under test:

* The committed ``docs/api/openapi.json`` matches the live app — a partner
  evaluating integration must not read a contract the code no longer honours.
* Serialisation is stable (sorted keys), so a diff shows real API changes rather
  than dict-ordering noise.
* Publishing the contract does **not** imply the API is deployed: ADR-012 still
  governs that, and the accompanying doc must say so.
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.export_openapi import CONTRACT, build_contract, serialise

_ROOT = Path(__file__).resolve().parents[2]


def _committed() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


# ── Freshness ────────────────────────────────────────────────────────────────

def test_committed_contract_matches_the_live_app() -> None:
    """Mirrors `scripts/export_openapi.py --check`, enforced in the suite."""
    assert CONTRACT.read_text(encoding="utf-8") == serialise(build_contract()), (
        "El contrato OpenAPI está desactualizado. "
        "Ejecuta: python scripts/export_openapi.py"
    )


def test_serialisation_is_stable_and_sorted() -> None:
    rendered = serialise(build_contract())
    assert rendered.endswith("\n")
    # Re-serialising a parsed copy must be byte-identical (no ordering drift).
    assert serialise(json.loads(rendered)) == rendered


def test_contract_declares_the_package_version() -> None:
    from src._version import __version__

    assert _committed()["info"]["version"] == __version__


# ── The surface partners actually integrate against ──────────────────────────

def test_every_v2_router_is_represented() -> None:
    paths = _committed()["paths"]
    for prefix in (
        "/api/v2/territories/",
        "/api/v2/managed-assets/",
        "/api/v2/alerts/",
        "/api/v2/audit-log/",
    ):
        assert any(p.startswith(prefix) for p in paths), f"falta {prefix}"


def test_health_endpoint_is_published() -> None:
    """Deployment runbooks probe /health; it must be in the contract."""
    assert "/health" in _committed()["paths"]


def test_contract_carries_schema_components() -> None:
    schemas = _committed()["components"]["schemas"]
    assert "ManagedAssetOut" in schemas
    assert "TerritorySummaryOut" in schemas


def test_managed_asset_out_exposes_the_mobile_enrichment() -> None:
    """The Fase 2 (ADR-014) fields a client maps must be in the contract."""
    props = _committed()["components"]["schemas"]["ManagedAssetOut"]["properties"]
    for field in (
        "latitude",
        "longitude",
        "latest_observed_at",
        "latest_evidence_class",
    ):
        assert field in props


# ── Publishing ≠ deploying ───────────────────────────────────────────────────

def test_api_doc_states_the_service_is_not_deployed() -> None:
    """ADR-012 is unchanged by publishing a contract; the doc must not imply it."""
    doc = (_ROOT / "docs" / "api" / "README.md").read_text(encoding="utf-8")
    assert "ADR-012" in doc
    assert "no está desplegada" in doc
