"""
ManagedAsset — the central product object of v2.0 (Fase 5).

The managed asset (trail, viewpoint, zone) with an action-state lifecycle,
per ``docs/ux/ui-evolution-v2-spec.md`` §3:
``detected -> verified -> assigned -> funded -> resolved -> monitored``.
"""
from __future__ import annotations

from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.persistence.base import Base
from src.persistence.enums import ManagedAssetStatus


class ManagedAsset(Base):
    __tablename__ = "managed_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    territory_id: Mapped[int] = mapped_column(ForeignKey("territories.id"))
    # The id this asset already has in the analytical layer (src.territorial /
    # src.assets), so persisted records can be joined back to the in-memory
    # pipeline output without inventing a second identifier scheme.
    external_asset_id: Mapped[str] = mapped_column(String(128), index=True)
    name: Mapped[str] = mapped_column(String(200))
    asset_type: Mapped[str] = mapped_column(String(32))
    # Verbatim GeoJSON geometry (as src.assets.models.GeoJSONGeometry serializes
    # it). This stays the *canonical, portable* geometry: it round-trips
    # unchanged on both SQLite (dev/tests) and Postgres.
    geometry_geojson: Mapped[str] = mapped_column(Text)
    # Derived PostGIS mirror of ``geometry_geojson`` for in-DB spatial queries
    # (v3.0). The *base* type is ``Text`` with a Postgres-only ``Geometry``
    # variant: on Postgres the DDL is a real ``geometry(Geometry, 4326)`` column
    # (GIST-indexed + backfilled from the GeoJSON by the migration); everywhere
    # else it stays inert ``Text``. Keeping ``Text`` as the base (not the
    # Geometry) is deliberate — GeoAlchemy2's global DDL listeners only fire for
    # a base Geometry type, so this arrangement avoids the SpatiaLite calls that
    # would otherwise break plain-SQLite ``create_all`` in dev/tests. Nullable:
    # rows with absent/invalid GeoJSON (e.g. ``"{}"``) keep ``geom IS NULL`` —
    # geometry is never fabricated. Spatial reads live in ManagedAssetRepository
    # and only run on Postgres.
    geom: Mapped[str | None] = mapped_column(
        Text().with_variant(
            Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=False),
            "postgresql",
        ),
        nullable=True,
    )
    region: Mapped[str] = mapped_column(String(200))
    status: Mapped[ManagedAssetStatus] = mapped_column(
        default=ManagedAssetStatus.DETECTED
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    territory: Mapped["Territory"] = relationship()  # noqa: F821

    def __repr__(self) -> str:  # pragma: no cover - debug aid only
        return (
            f"ManagedAsset(id={self.id!r}, external_asset_id="
            f"{self.external_asset_id!r}, status={self.status!r})"
        )
