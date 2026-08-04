"""
SNTO — Earth Engine integration foundation (ADR-015).

Shared, idempotent Earth Engine initialization plus a typed error hierarchy.
This package holds Earth Engine I/O only; SNTO domain logic (composites,
indices, change detection) lives elsewhere per ADR-015.
"""
from __future__ import annotations

from src.integrations.earth_engine.client import (
    EarthEngineClient,
    cached_earth_engine_client,
    get_change_explorer_client,
    initialize_earth_engine,
    reset_earth_engine_state,
)
from src.integrations.earth_engine.errors import (
    EarthEngineAuthError,
    EarthEngineConfigError,
    EarthEngineDisabledError,
    EarthEngineError,
    EarthEngineQuotaError,
    EarthEngineUnavailableError,
    map_ee_exception,
)

__all__ = [
    "EarthEngineClient",
    "cached_earth_engine_client",
    "get_change_explorer_client",
    "initialize_earth_engine",
    "reset_earth_engine_state",
    "EarthEngineError",
    "EarthEngineDisabledError",
    "EarthEngineConfigError",
    "EarthEngineAuthError",
    "EarthEngineUnavailableError",
    "EarthEngineQuotaError",
    "map_ee_exception",
]
