"""ManagedAssetRepository — CRUD + lifecycle/territory lookups (Fase 5, 5.2).

The spatial lookups (``list_within_distance`` / ``list_intersecting``, v3.0)
run in-DB against the PostGIS ``geom`` column and therefore only work on a
PostgreSQL/PostGIS backend; on SQLite (dev/tests) they raise
``PostGISUnavailable`` rather than silently returning wrong answers.
"""
from __future__ import annotations

from geoalchemy2 import Geography
from sqlalchemy import cast, func, select

from src.persistence.enums import ManagedAssetStatus
from src.persistence.models.managed_asset import ManagedAsset
from src.persistence.repositories.base import Repository


class PostGISUnavailable(RuntimeError):
    """Raised when a spatial query is attempted on a non-PostGIS backend."""


class ManagedAssetRepository(Repository[ManagedAsset]):
    model = ManagedAsset

    def _require_postgis(self) -> None:
        """Guard: spatial SQL is only valid on PostgreSQL/PostGIS."""
        if self.session.get_bind().dialect.name != "postgresql":
            raise PostGISUnavailable(
                "spatial queries require a PostgreSQL/PostGIS backend; the "
                "active engine is "
                f"{self.session.get_bind().dialect.name!r}"
            )

    def get_by_external_id(self, external_asset_id: str) -> ManagedAsset | None:
        return self.session.scalars(
            select(ManagedAsset).where(
                ManagedAsset.external_asset_id == external_asset_id
            )
        ).first()

    def list_by_territory(self, territory_id: int) -> list[ManagedAsset]:
        return list(
            self.session.scalars(
                select(ManagedAsset).where(ManagedAsset.territory_id == territory_id)
            )
        )

    def list_by_status(self, status: ManagedAssetStatus) -> list[ManagedAsset]:
        return list(
            self.session.scalars(
                select(ManagedAsset).where(ManagedAsset.status == status)
            )
        )

    def list_within_distance(
        self, lon: float, lat: float, meters: float
    ) -> list[ManagedAsset]:
        """Assets whose geometry lies within ``meters`` of ``(lon, lat)``.

        Distance is measured on the spheroid (``geography`` cast), so ``meters``
        is true ground distance regardless of latitude. Rows with ``geom IS
        NULL`` (absent/invalid GeoJSON) are excluded. PostGIS-only.
        """
        self._require_postgis()
        point = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
        stmt = select(ManagedAsset).where(
            ManagedAsset.geom.isnot(None),
            func.ST_DWithin(
                cast(ManagedAsset.geom, Geography),
                cast(point, Geography),
                meters,
            ),
        )
        return list(self.session.scalars(stmt))

    def list_intersecting(self, geojson: str) -> list[ManagedAsset]:
        """Assets whose geometry intersects the given GeoJSON geometry.

        ``geojson`` is a verbatim GeoJSON geometry string (same shape as
        ``geometry_geojson``). Rows with ``geom IS NULL`` are excluded.
        PostGIS-only.
        """
        self._require_postgis()
        other = func.ST_SetSRID(func.ST_GeomFromGeoJSON(geojson), 4326)
        stmt = select(ManagedAsset).where(
            ManagedAsset.geom.isnot(None),
            func.ST_Intersects(ManagedAsset.geom, other),
        )
        return list(self.session.scalars(stmt))
