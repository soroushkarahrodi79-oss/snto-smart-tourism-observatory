"""Unit tests for palettes + static PNG rendering (ADR-015). Offline / mocked ee."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.integrations.earth_engine.errors import (
    EarthEngineAuthError,
    EarthEngineQuotaError,
)
from src.integrations.earth_engine.palettes import DNDVI, NDVI, TRUE_COLOUR
from src.integrations.earth_engine.render import (
    build_thumbnail_params,
    get_thumbnail_url,
)

# ── Palettes ──────────────────────────────────────────────────────────────────

class TestPalettes:
    def test_true_colour_params(self):
        p = TRUE_COLOUR.to_ee_params()
        assert p["bands"] == ["B4", "B3", "B2"]
        assert p["min"] == 0.0
        assert p["max"] == 3000.0
        assert "palette" not in p  # multi-band true colour has no palette

    def test_ndvi_params_have_stable_range_and_palette(self):
        p = NDVI.to_ee_params()
        assert p["bands"] == ["NDVI"]
        assert p["min"] == 0.0 and p["max"] == 0.9
        assert isinstance(p["palette"], list) and len(p["palette"]) >= 2

    def test_dndvi_is_symmetric_diverging(self):
        p = DNDVI.to_ee_params()
        assert p["bands"] == ["dNDVI"]
        assert p["min"] == -0.4 and p["max"] == 0.4  # symmetric about zero
        assert len(p["palette"]) >= 3  # negative / neutral / positive
        assert DNDVI.legend  # documented


# ── build_thumbnail_params ────────────────────────────────────────────────────

class TestThumbnailParams:
    def test_merges_region_dimensions_format(self):
        region = MagicMock()
        params = build_thumbnail_params(
            region=region, visualization=NDVI.to_ee_params(), dimensions=512
        )
        assert params["region"] is region
        assert params["dimensions"] == 512
        assert params["format"] == "png"
        assert params["bands"] == ["NDVI"]

    def test_dimensions_lower_bound(self):
        with pytest.raises(ValueError):
            build_thumbnail_params(
                region=MagicMock(), visualization={}, dimensions=8
            )

    def test_dimensions_upper_bound(self):
        with pytest.raises(ValueError):
            build_thumbnail_params(
                region=MagicMock(), visualization={}, dimensions=9999
            )

    def test_bool_dimensions_rejected(self):
        with pytest.raises(ValueError):
            build_thumbnail_params(
                region=MagicMock(), visualization={}, dimensions=True
            )

    def test_unsupported_format_rejected(self):
        with pytest.raises(ValueError):
            build_thumbnail_params(
                region=MagicMock(),
                visualization={},
                dimensions=256,
                image_format="gif",
            )


# ── Alignment guarantee ───────────────────────────────────────────────────────

class TestAlignment:
    def test_before_after_params_identical_for_identical_inputs(self):
        region = MagicMock()
        vis = NDVI.to_ee_params()
        before = build_thumbnail_params(
            region=region, visualization=vis, dimensions=512
        )
        after = build_thumbnail_params(
            region=region, visualization=vis, dimensions=512
        )
        # Same region, dimensions, format and value stretch -> aligned panels.
        assert before == after
        assert before["region"] is after["region"]
        assert before["min"] == after["min"] and before["max"] == after["max"]

    def test_params_independent_of_image(self):
        # Params depend only on alignment inputs, never on the image, so two
        # different before/after images still render aligned.
        region = MagicMock()
        vis = TRUE_COLOUR.to_ee_params()
        p = build_thumbnail_params(region=region, visualization=vis, dimensions=384)
        assert "image" not in p


# ── get_thumbnail_url ─────────────────────────────────────────────────────────

class TestGetThumbnailUrl:
    def test_calls_get_thumb_url_with_params(self):
        image = MagicMock()
        image.getThumbURL.return_value = "https://ee.example/thumb/abc"
        region = MagicMock()
        url = get_thumbnail_url(
            image=image,
            region=region,
            visualization=NDVI.to_ee_params(),
            dimensions=256,
        )
        image.getThumbURL.assert_called_once()
        params = image.getThumbURL.call_args.args[0]
        assert params["region"] is region
        assert params["dimensions"] == 256
        assert params["format"] == "png"
        assert url == "https://ee.example/thumb/abc"

    def test_quota_error_mapped(self):
        image = MagicMock()
        image.getThumbURL.side_effect = RuntimeError("Quota exceeded")
        with pytest.raises(EarthEngineQuotaError):
            get_thumbnail_url(
                image=image,
                region=MagicMock(),
                visualization=NDVI.to_ee_params(),
                dimensions=256,
            )

    def test_auth_error_mapped(self):
        image = MagicMock()
        image.getThumbURL.side_effect = RuntimeError("403 permission denied")
        with pytest.raises(EarthEngineAuthError):
            get_thumbnail_url(
                image=image,
                region=MagicMock(),
                visualization=NDVI.to_ee_params(),
                dimensions=256,
            )

    def test_signed_url_never_logged(self):
        image = MagicMock()
        secret = "https://ee.example/thumb/SUPER-SECRET-TOKEN"
        image.getThumbURL.return_value = secret
        with patch("src.integrations.earth_engine.render.logger") as log:
            get_thumbnail_url(
                image=image,
                region=MagicMock(),
                visualization=NDVI.to_ee_params(),
                dimensions=256,
            )
        for call in log.mock_calls:
            assert "SUPER-SECRET-TOKEN" not in str(call)
