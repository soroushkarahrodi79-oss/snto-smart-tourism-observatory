"""Offline tests for the manual live smoke script (ADR-015).

The smoke script itself makes real EE calls only when invoked with the opt-in
flag; these tests cover its *safe* behaviour (refusal + secret-free summary)
without any Earth Engine contact.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

import scripts.smoke_test_change_explorer_live as smoke
from src.analysis.change_detection.models import CompositeKind, DateWindow, WindowRole
from src.analysis.change_detection.quality import evaluate_quality
from src.services.change_explorer_service import (
    ChangeExplorerRequest,
    ChangeExplorerResult,
    RenderedArtifact,
    ResultStatus,
)

_URL = "https://ee.example/thumb/SECRET-TOKEN"


def _result():
    before = DateWindow(date(2023, 7, 1), date(2023, 8, 31))
    after = DateWindow(date(2024, 7, 1), date(2024, 8, 31))
    req = ChangeExplorerRequest(
        territory_id="pnsg", product=CompositeKind.NDVI, before=before, after=after,
        max_cloud_pct=20.0, dimensions=256,
    )

    def _art(role):
        return RenderedArtifact(
            product=CompositeKind.NDVI, role=role, dimensions=256, window=after,
            visualization_id="ndvi:vis-v1", url=_URL,
        )

    def _q(win):
        return evaluate_quality(
            window=win, requested_max_cloud_pct=20.0, scene_count=8,
            valid_pixel_count=800, aoi_pixel_count=1000, mean_scene_cloud_pct=10.0,
        )

    return ChangeExplorerResult(
        territory_id="pnsg", territory_name="PNSG", product=CompositeKind.NDVI,
        status=ResultStatus.OK, request=req,
        before_quality=_q(before), after_quality=_q(after), warnings=(),
        evidence_label="Observación real Sentinel-2 — no validada en campo.",
        generated_at=datetime(2024, 9, 1, tzinfo=timezone.utc),
        before_artifact=_art(WindowRole.BEFORE), after_artifact=_art(WindowRole.AFTER),
        dndvi_artifact=_art(WindowRole.DIFFERENCE),
    )


def test_refuses_without_opt_in(monkeypatch):
    monkeypatch.setattr(smoke.sys, "argv", ["smoke"])  # no --confirm-live-ee
    assert smoke.main() == smoke.EXIT_REFUSED


def test_safe_summary_has_no_urls_or_secrets():
    summary = smoke._safe_result_summary(_result())
    blob = json.dumps(summary)
    assert "SECRET-TOKEN" not in blob
    assert "url" not in blob.lower()
    assert summary["artifacts_present"] == {
        "before": True, "after": True, "dndvi": True,
    }
    assert summary["status"] == "ok"
    assert summary["before_quality"]["valid_pixel_fraction"] == 0.8


def test_conservative_bbox_is_inside_pnsg():
    from src.config import territories

    w, s, e, n = smoke._CONSERVATIVE_BBOX
    pw, ps, pe, pn = territories.get("pnsg").bbox_wgs84
    assert pw <= w < e <= pe and ps <= s < n <= pn  # strictly inside PNSG
