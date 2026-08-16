# Administrative boundary reference for the Madrid-side trail filter (B-01)

## ✅ `madrid_boundary_osm.geojson` — the boundary now in use

Supplied by the owner (2026-08-15) from **OpenStreetMap**, relation
[`349055`](https://www.openstreetmap.org/relation/349055) (Comunidad de
Madrid), fetched via polygons.openstreetmap.fr and confirmed to be the correct
administrative area before saving. **6 294 vertices** across 3 polygons (the
mainland community + 2 small exclaves) — dramatically finer than the earlier
placeholders (Natural Earth 425 vertices, click_that_hood 155).

**Repaired on ingest**: the raw geometry had a topology defect (`Nested
shells`, one polygon fully inside another rather than expressed as a hole) —
fixed with `geometry.buffer(0)`, the standard Shapely repair. Area changed by
**0.015%**, localised far from PNSG (near an exclave around 40.63°N, −3.38°E),
so the fix does not affect the trail-filtering result.

**Validated against known landmarks** before use:
- La Pedriza (−3.87, 40.74), unambiguously Madrid-side → **within** ✓
- Valsaín (−4.013, 40.817), unambiguously Segovia/Castilla y León-side → **outside** ✓

Trail-network check: **41/218** PNSG trails fall within this boundary at a
1000 m inward safety margin (vs. the old Natural Earth placeholder's ~55-58,
which — per the landmark test — was misclassifying the crest region).

**Provenance note:** this is an OpenStreetMap community-maintained boundary,
not a literal export of the IGN *Líneas Límite jurisdiccionales* file. It is
used as `--boundary-authoritative` because it passed the landmark validation
above and its resolution is adequate for this filtering task (excluding trails
near the boundary via the inward margin already absorbs residual small-scale
uncertainty). If the owner later obtains the literal IGN *Líneas Límite* layer,
swap it in the same way (see below) and re-run.

## Why not fetched directly from IGN

`ign.es` / the INSPIRE Administrative Units WFS — along with Eurostat GISCO,
GADM, the Overpass API, and every npm CDN (unpkg, jsDelivr) — is blocked by
this environment's outbound proxy, which only reaches
`raw.githubusercontent.com`. The owner fetched the OSM boundary from their own
network and uploaded it directly.

## Superseded placeholder

`madrid_boundary_naturalearth10m.geojson` (Natural Earth 10m admin-1, ~1:10M,
425 vertices) is kept for historical reference only. It is **not** used by
default any more — it materially misclassified sierra trails at the crest
(verified: it placed unambiguously-Madrid trails as "outside").

---

## DEM (A-4 ecological strata) — real Copernicus GLO-30, owner-supplied 2026-08-16

`pnsg_dem.tif` (elevation, EPSG:25830, 30 m) is **not committed to this repository** —
per the repo-wide policy at the top of `.gitignore` ("Datos geoespaciales pesados —
NUNCA subir a GitHub", `*.tif` excluded everywhere), the same treatment every
Sentinel-2 raster in this project already receives. What **is** committed is the
small derived product, `pnsg_trail_strata.csv` (218 rows, ~8 KB) plus its
`.provenance.json` sidecar — the sidecar records the DEM's SHA-256 so the
derivation is verifiable and reproducible without the raw file ever entering git
history.

### Source and processing

| Field | Value |
|---|---|
| Source | Copernicus GLO-30 DEM, via OpenTopography |
| Retrieved by | Owner, 2026-08-16 |
| BBox requested | (−4.28, 40.70) to (−3.70, 41.08) — tight around the PNSG trail network |
| Original file | `output_hh.tif`, EPSG:4326, 2088×1368 px (~0.028°/px ≈ 30.9 m), SHA-256 `e17b8a67…` |
| Elevation range (raw) | 837.8–2424.2 m — **sanity-checked**: max is within 4 m of Peñalara's real summit (2428 m), confirming correct geolocation |
| Reprojection | EPSG:4326 → **EPSG:25830** (UTM 30N, the CRS every other spatial component in this pipeline uses), 30 m, bilinear resampling |
| Nodata handling | Reprojecting a geographic rectangle into UTM rotates its footprint, leaving triangular gaps at the corners (2.29% of pixels here) — these are set to explicit `NaN`, never silently `0`, so `build_ecological_strata.py`'s `isfinite()` check correctly treats them as missing rather than as a spurious sea-level reading |
| Final file | `pnsg_dem.tif`, EPSG:25830, 1645×1425 px, 30 m, SHA-256 `16fff032…` |
| Coverage | Confirmed to fully contain the 218-trail network's bounding box |

### Why reprojection mattered here

The raw DEM ships in geographic coordinates (degrees). `compute_slope_aspect()`
(`src/geospatial/geometry.py`) derives aspect from the ratio of east-west to
north-south elevation gradients, assuming both pixel axes are in the same real
distance unit. At 40.8°N, one degree of longitude is only ~84 300 m while one
degree of latitude is ~111 100 m — using the DEM in EPSG:4326 directly would have
skewed every computed aspect angle by roughly that ratio, silently mis-assigning
the S1 (north-facing) / S2 (south-facing) forest split. Reprojecting to the metric
EPSG:25830 grid first removes that anisotropy.

### Result

`scripts/paper1/build_ecological_strata.py --dem clean_assets/field_validation/reference/pnsg_dem.tif --dem-authoritative`
classified all 218 trails (0 unresolved): 161 S2 (forest, south-facing), 38 S1
(forest, north-facing), 17 S3 (shrubland), 2 S4 (alpine grassland — both >2100 m,
north-facing, consistent with a high cirque near Peñalara). `scripts/paper1/generate_plot_plan.py --strata clean_assets/field_validation/reference/pnsg_trail_strata.csv`
now stratifies the plot plan by these real ecological bands instead of the interim
satellite-stress tercile.

### Reproducing this DEM

1. OpenTopography → Copernicus GLO-30 → same bbox as above → GeoTiff.
2. `python scripts/paper1/reproject_dem_to_utm.py --src <downloaded>.tif --dst pnsg_dem.tif`
   — reprojects to EPSG:25830 at 30 m, bilinear, explicit NaN nodata. Verified
   deterministic: re-running it against the original source file reproduces the
   exact SHA-256 below, byte for byte.
3. Verify the resulting SHA-256 matches `16fff032…` above, or — if it legitimately
   differs (e.g. a newer Copernicus release) — re-run `build_ecological_strata.py`
   and update this section.

## How to swap in a different boundary later

`scripts/paper1/generate_plot_plan.py` takes the boundary as a parameter and
treats the plan as **PROVISIONAL** unless `--boundary-authoritative` is passed:
```
python scripts/paper1/generate_plot_plan.py \
    --boundary clean_assets/field_validation/reference/<file>.geojson \
    --boundary-authoritative
```

## Provenance

| Field | Value |
|---|---|
| Layer | Comunidad de Madrid (admin-1), OSM relation 349055 |
| Source | OpenStreetMap, via polygons.openstreetmap.fr |
| Licence | ODbL (OpenStreetMap contributors) |
| Vertices | 6 294 (3 polygons: mainland + 2 exclaves) |
| Retrieved | 2026-08-15, supplied by the owner |
| Repair | `buffer(0)` on ingest — fixed a nested-shells topology defect; area Δ 0.015%, far from PNSG |
| Validated | Landmark spot-check (La Pedriza in / Valsaín out) — passed |
| Authoritative? | **Yes**, for the purposes of this filter (see provenance note above) |
