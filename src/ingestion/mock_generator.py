from __future__ import annotations

import hashlib
import math

from src.assets.models import AssetObservation, TourismAsset
from src.config.constants import MOCK_MONTHS, MOCK_SPRING_PEAK_MONTH
from src.ingestion.base import DataIngestionAdapter


class MockDataGenerator(DataIngestionAdapter):
    """
    Produces deterministic, reproducible NDVI/NDMI time series.

    Uses hashlib.md5 (not Python's hash()) so outputs are stable across
    interpreter restarts regardless of PYTHONHASHSEED.

    Model:
        NDVI(t) = clamp(baseline + amplitude * sin(2π*(t - peak)/12) - degradation, 0, 1)
        NDMI(t) = NDVI(t) * 0.65 - 0.05 * cos(2π*t/12)

    All parameters are pure functions of asset_id — no stochastic component.
    """

    def fetch_time_series(
        self,
        asset: TourismAsset,
        year: int,
        months: int = MOCK_MONTHS,
    ) -> list[AssetObservation]:
        observations: list[AssetObservation] = []
        for i in range(months):
            month = (i % 12) + 1
            ndvi = self._ndvi_for_month(asset.asset_id, month)
            ndmi = self._ndmi_for_month(ndvi, month)
            observations.append(
                AssetObservation(
                    asset_id=asset.asset_id,
                    year=year,
                    month=month,
                    ndvi=ndvi,
                    ndmi=ndmi,
                    cloud_cover_pct=0.0,
                    data_source="mock",
                )
            )
        return observations

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _seed_offset(self, asset_id: str) -> float:
        """Deterministic float in [0, 1) from asset_id via MD5."""
        digest = hashlib.md5(asset_id.encode()).hexdigest()
        return (int(digest, 16) % 10_000) / 10_000

    def _ndvi_for_month(self, asset_id: str, month: int) -> float:
        offset = self._seed_offset(asset_id)
        baseline = 0.40 + 0.25 * offset
        amplitude = 0.10 + 0.15 * offset
        # Degradation: one of three levels (0.0, 0.1, 0.2) keyed to asset hash
        deg_level = int(hashlib.md5(asset_id.encode()).hexdigest(), 16) % 3
        degradation = deg_level * 0.10

        seasonal = amplitude * math.sin(
            2 * math.pi * (month - MOCK_SPRING_PEAK_MONTH) / 12
        )
        raw = baseline + seasonal - degradation
        return max(0.0, min(1.0, raw))

    def _ndmi_for_month(self, ndvi: float, month: int) -> float:
        moisture_lag = -0.05 * math.cos(2 * math.pi * month / 12)
        raw = ndvi * 0.65 + moisture_lag
        return max(-1.0, min(1.0, raw))
