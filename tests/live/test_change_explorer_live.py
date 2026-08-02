"""
Optional LIVE Earth Engine test for the Visual Change Explorer (ADR-015).

Marked ``live_ee`` and **skipped by default**. It runs only when ALL of these are
set, so it never executes in normal/blocking CI:

* ``SNTO_LIVE_EE_TEST=1``            (explicit opt-in),
* ``SNTO_ENABLE_CHANGE_EXPLORER=true`` (feature flag),
* ``GEE_PROJECT_ID``                 (an EE-registered project; plus working
  personal auth or a service-account key configured out-of-band).

It reuses the production service, hits a small conservative AOI inside PNSG, and
asserts only safe invariants. It **never** prints thumbnail URLs, takes no
screenshots, and creates no exports/assets.
"""
from __future__ import annotations

import dataclasses
import os
from datetime import date

import pytest

_OPT_IN = os.environ.get("SNTO_LIVE_EE_TEST") == "1"
_FLAG = os.environ.get("SNTO_ENABLE_CHANGE_EXPLORER", "").lower() == "true"
_PROJECT = bool(os.environ.get("GEE_PROJECT_ID"))

pytestmark = [
    pytest.mark.live_ee,
    pytest.mark.skipif(
        not (_OPT_IN and _FLAG and _PROJECT),
        reason=(
            "live_ee: set SNTO_LIVE_EE_TEST=1 + SNTO_ENABLE_CHANGE_EXPLORER=true "
            "+ GEE_PROJECT_ID (with working EE credentials) to run."
        ),
    ),
]

# Conservative AOI inside PNSG (matches the manual smoke script). Override lives
# only in the test — never in the production territory registry.
_SMOKE_BBOX = (-3.95, 40.85, -3.85, 40.92)  # (W, S, E, N)


def test_change_explorer_live_round_trip() -> None:
    from src.analysis.change_detection.models import CompositeKind, DateWindow
    from src.config import territories
    from src.config.settings import Settings
    from src.services.change_explorer_service import (
        ChangeExplorerRequest,
        ResultStatus,
        run_change_explorer,
    )

    cfg = dataclasses.replace(territories.get("pnsg"), bbox_wgs84=_SMOKE_BBOX)
    request = ChangeExplorerRequest(
        territory_id="pnsg",
        product=CompositeKind.NDVI,
        before=DateWindow(date(2023, 7, 1), date(2023, 8, 31)),
        after=DateWindow(date(2024, 7, 1), date(2024, 8, 31)),
        max_cloud_pct=20.0,
        dimensions=256,
    )

    # A successful return implies ee.Initialize + the whole pipeline ran.
    result = run_change_explorer(
        request, app_settings=Settings(), territory_resolver=lambda _t: cfg
    )

    for q in (result.before_quality, result.after_quality):
        assert q.scene_count is None or q.scene_count >= 0
        if q.valid_pixel_fraction is not None:
            assert 0.0 <= q.valid_pixel_fraction <= 1.0
        if q.mean_scene_cloud_pct is not None:
            assert 0.0 <= q.mean_scene_cloud_pct <= 100.0

    if result.status is ResultStatus.OK:
        for artifact in (
            result.before_artifact,
            result.after_artifact,
            result.dndvi_artifact,
        ):
            assert artifact is not None
            # Non-empty URL required, but it must NEVER be printed/asserted-on
            # by value.
            assert isinstance(artifact.url, str) and artifact.url
