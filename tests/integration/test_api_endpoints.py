from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)

MASATRIGO_PAYLOAD = {
    "asset_id": "masatrigo-trail-001",
    "name": "Masatrigo Trail, Badajoz",
    "asset_type": "trail",
    "geometry": {
        "type": "LineString",
        "coordinates": [[-7.02, 38.88], [-7.00, 38.90]],
    },
    "region": "Extremadura",
    "country": "Spain",
    "elevation_m": 420.0,
    "year": 2024,
}


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_evaluate_asset_returns_200():
    resp = client.post("/evaluate_asset/", json=MASATRIGO_PAYLOAD)
    assert resp.status_code == 200


def test_evaluate_asset_risk_score_in_range():
    resp = client.post("/evaluate_asset/", json=MASATRIGO_PAYLOAD)
    data = resp.json()
    assert 0.0 <= data["risk_score"] <= 1.0


def test_evaluate_asset_has_alert_level():
    resp = client.post("/evaluate_asset/", json=MASATRIGO_PAYLOAD)
    data = resp.json()
    assert data["alert_level"] in [
        "CRITICAL_INTERVENTION",
        "URGENT_MONITORING",
        "PREVENTIVE_ACTION",
        "NORMAL",
    ]


def test_evaluate_asset_has_recommended_actions():
    resp = client.post("/evaluate_asset/", json=MASATRIGO_PAYLOAD)
    data = resp.json()
    assert len(data["recommended_actions"]) > 0


def test_evaluate_asset_has_computation_trace():
    resp = client.post("/evaluate_asset/", json=MASATRIGO_PAYLOAD)
    data = resp.json()
    assert "computation_trace" in data
    assert "final_score" in data["computation_trace"]


def test_evaluate_asset_invalid_geometry_type_returns_422():
    bad_payload = {**MASATRIGO_PAYLOAD, "geometry": {"type": "Point", "coordinates": [-7.0, 38.9]}}
    resp = client.post("/evaluate_asset/", json=bad_payload)
    assert resp.status_code == 422


def test_ranking_endpoint_returns_200():
    resp = client.get("/ranking/")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "assets" in data


def test_alerts_endpoint_returns_200():
    resp = client.get("/alerts/")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "alerts" in data
