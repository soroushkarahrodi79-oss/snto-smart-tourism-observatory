"""
SNTO — Mobility → visitor-pressure bridge (v2.2).

Turns the real MITMA inbound-trip snapshot into a per-municipality
visitor-pressure signal the rest of the platform can consume (SCM
de-circularisation, the forthcoming LAC/ROS capacity model). Two rules keep it
honest:

  1. **Fallback, never blur.** ``inbound_pressure_by_ine`` returns ``None`` when
     the real snapshot has not been ingested — callers keep using the labeled
     curated estimate. Real and curated are never silently mixed.
  2. **Downgrade on interpretation.** The raw inbound trips are ``REAL``; the
     moment they are *used as a pressure input* they carry an interpretive
     assumption (municipal trip ≈ tourism pressure), so the derived signal is
     labeled ``CALIBRATED``, not ``REAL`` (ADR-004 evidence separation).
"""
from __future__ import annotations

from dataclasses import dataclass

from src.mobility.loader import load_mobility
from src.mobility.models import PROXY_CAVEAT
from src.temporal.manifest import DataStatus


@dataclass(frozen=True)
class PressureSignal:
    """A real-data-backed visitor-pressure reading for one municipality."""

    ine_code: str
    name: str
    period: str
    inbound_trips: float          # real MITMA inbound trips (the observation)
    data_status: DataStatus       # CALIBRATED — a proxy interpretation, not raw
    caveat: str


def inbound_pressure_by_ine(
    year: str,
    snapshot=None,
) -> dict[str, PressureSignal] | None:
    """Real inbound-mobility pressure per municipality INE code for ``year``.

    Returns ``None`` when no real snapshot exists (caller falls back to the
    curated estimate). Zones without a datum for ``year`` are omitted rather
    than zero-filled — absence of evidence is never rendered as zero pressure.
    """
    snap = snapshot if snapshot is not None else load_mobility()
    if snap is None:
        return None

    out: dict[str, PressureSignal] = {}
    for ine_code, zone in snap.zones.items():
        trips = zone.annual(year)
        if trips is None:
            continue
        out[ine_code] = PressureSignal(
            ine_code=ine_code,
            name=zone.name,
            period=year,
            inbound_trips=trips,
            # REAL observation → CALIBRATED once read as a pressure proxy.
            data_status=DataStatus.CALIBRATED,
            caveat=PROXY_CAVEAT,
        )
    return out or None
