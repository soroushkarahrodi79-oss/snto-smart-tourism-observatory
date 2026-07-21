"""
SNTO — Mobility data models (v2.2, real visitor/mobility feed).

The mobility layer ingests the **real** MITMA municipal-mobility open data
(INE + the three carriers) to replace the mock ``etl_tourist_traffic.py`` and
de-circularise the visitor-pressure signal that was, until now, either random
(mock) or a curated estimate (``visitor_capacity_annual`` in fixtures).

EVIDENCE DISCIPLINE (ADR-004 / CLAUDE.md)
-----------------------------------------
The inbound-trip counts are **real observations** (``DataStatus.REAL``): MITMA
publishes them officially. But a municipal inbound-trip count is a *proxy* for
tourism pressure, **not** trail footfall — a trip into Cercedilla is not a walk
on a specific senda. So the raw counts are stored as REAL with a standing
caveat, and any value *derived* from them as a pressure/capacity input is
downgraded to ``CALIBRATED`` by the bridge (it embeds an interpretive
assumption). Nothing here is ever presented as observed trail visitation.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.temporal.manifest import DataStatus


@dataclass(frozen=True)
class MobilityZone:
    """One MITMA municipal zone's real inbound mobility, joined to a municipality.

    ``inbound_trips`` maps a period key (``"2024"`` annual or ``"2024-07"``
    monthly) to the mean daily number of trips whose *destination* is this zone
    and whose origin is elsewhere (residents' internal trips excluded) — the
    real inbound-pressure proxy.
    """

    mitma_zone_id: str
    ine_code: str
    name: str
    inbound_trips: dict[str, float] = field(default_factory=dict)
    data_status: DataStatus = DataStatus.REAL
    caveats: list[str] = field(default_factory=list)

    def annual(self, year: str) -> float | None:
        return self.inbound_trips.get(year)

    def to_dict(self) -> dict:
        return {
            "mitma_zone_id": self.mitma_zone_id,
            "ine_code": self.ine_code,
            "name": self.name,
            "inbound_trips": self.inbound_trips,
            "data_status": self.data_status.value,
            "caveats": self.caveats,
        }

    @classmethod
    def from_dict(cls, d: dict) -> MobilityZone:
        return cls(
            mitma_zone_id=str(d["mitma_zone_id"]),
            ine_code=str(d["ine_code"]),
            name=str(d.get("name", "")),
            inbound_trips={
                str(k): float(v) for k, v in d.get("inbound_trips", {}).items()
            },
            data_status=DataStatus(d.get("data_status", "real")),
            caveats=list(d.get("caveats", [])),
        )


# Standing caveat attached to every mobility figure, so the proxy nature is
# never lost as the data flows downstream.
PROXY_CAVEAT = (
    "Viajes entrantes a la zona municipal (MITMA, posicionamiento móvil "
    "agregado): proxy REAL de presión turística municipal, NO aforo de senda. "
    "Un viaje al municipio no es una visita a un activo concreto."
)


@dataclass(frozen=True)
class MobilitySnapshot:
    """Curated snapshot of real inbound mobility for the territory's zones."""

    schema_version: str
    source_period: str                 # e.g. "2024" or "2024-01..2024-12"
    generated_at: str
    source: dict
    zones: dict[str, MobilityZone]     # ine_code -> MobilityZone

    def by_ine(self, ine_code: str | None) -> MobilityZone | None:
        return self.zones.get(ine_code) if ine_code else None

    @property
    def n_zones(self) -> int:
        return len(self.zones)
