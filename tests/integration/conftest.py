"""
Integration-test conftest.

On Windows, PostgreSQL/PostGIS installs its own proj.db (often schema version
2 or 4) and places it earlier in the PROJ search path than the rasterio-
bundled database (schema version 6+). rasterio ships PROJ 9.x with its own
proj_data/ directory; pyproj ships an older PROJ with a different (also older)
proj.db. Pointing PROJ_DATA to rasterio's bundled proj_data/ directory routes
every GDAL/PROJ database lookup to the correct schema version.

This is an environment-level fix: harmless where the conflict does not exist;
required on Windows systems with multiple PROJ installations.
"""
from __future__ import annotations

import os
from pathlib import Path

import rasterio as _rasterio

_RASTERIO_PROJ_DATA = str(Path(_rasterio.__file__).parent / "proj_data")
os.environ["PROJ_DATA"] = _RASTERIO_PROJ_DATA
