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
