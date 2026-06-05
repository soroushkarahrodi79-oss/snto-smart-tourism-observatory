from __future__ import annotations

from abc import ABC, abstractmethod

from src.assets.models import AssetObservation, TourismAsset


class DataIngestionAdapter(ABC):
    @abstractmethod
    def fetch_time_series(
        self,
        asset: TourismAsset,
        year: int,
        months: int = 12,
    ) -> list[AssetObservation]:
        """Return chronologically ordered monthly observations for an asset."""
        ...
