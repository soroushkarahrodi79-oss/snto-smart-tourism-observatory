"""
Real visitor/mobility feed (v2.2).

Ingests the real MITMA municipal-mobility open data (INE + carriers) as a
visitor-pressure proxy, replacing the mock ``etl_tourist_traffic.py``. Every
figure is evidence-labeled: raw inbound trips are ``REAL``; anything derived as
a pressure input is ``CALIBRATED`` (a municipal-trip proxy, never trail
footfall). See :mod:`src.mobility.models`.
"""
from src.mobility.bridge import (
    PressureSignal,
    inbound_pressure_by_ine,
    latest_period,
)
from src.mobility.loader import (
    ZoneRef,
    load_mobility,
    load_pnsg_zones,
    mobility_snapshot_exists,
)
from src.mobility.models import (
    PROXY_CAVEAT,
    MobilitySnapshot,
    MobilityZone,
)

__all__ = [
    "PROXY_CAVEAT",
    "MobilitySnapshot",
    "MobilityZone",
    "PressureSignal",
    "ZoneRef",
    "inbound_pressure_by_ine",
    "latest_period",
    "load_mobility",
    "load_pnsg_zones",
    "mobility_snapshot_exists",
]
