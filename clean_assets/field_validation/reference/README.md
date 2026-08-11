# Administrative boundary reference for the Madrid-side trail filter (B-01)

## ⚠️ The committed boundary is NON-AUTHORITATIVE

`madrid_boundary_naturalearth10m.geojson` is the **Comunidad de Madrid** polygon
from **Natural Earth 10m admin-1** (public domain / CC0), clipped to the PNSG
region. It is committed only because the authoritative source is unreachable
from this build environment (see below).

**It is cartographic-scale (~1:10 000 000, 425 vertices for the whole community)
and is NOT accurate at the mountain crest**, which is exactly where the
Comunidad de Madrid / Castilla y León (Segovia) border runs and exactly where
the PNSG trail network sits. Verified against the 218-trail network, this
boundary misclassifies a large fraction of sierra trails (it places ~160 of 218
"outside Madrid", including trails that are unambiguously Madrid). **Do not treat
a jurisdiction determination made with this layer as correct.**

## Why not IGN

The authoritative layer is the IGN *Líneas Límite jurisdiccionales* (≈1:25 000),
served from `ign.es` / the INSPIRE Administrative Units WFS. That host — along
with Eurostat GISCO, GADM, the Overpass API, and every npm CDN (unpkg,
jsDelivr) — is blocked by this environment's outbound proxy, which only reaches
`raw.githubusercontent.com`. The finest boundary obtainable there is this
Natural Earth polygon.

## How to finalise the Madrid filter

`scripts/paper1/generate_plot_plan.py` takes the boundary as a parameter and
treats the plan as **PROVISIONAL** unless `--boundary-authoritative` is passed.
To produce a defensible Madrid-side pool:

1. Obtain the IGN *Líneas Límite* Comunidad de Madrid polygon (IGN download
   centre, or the INSPIRE AU WFS) in any OGR-readable format.
2. Place it here, e.g. `madrid_boundary_ign.geojson`.
3. Re-run:
   ```
   python scripts/paper1/generate_plot_plan.py \
       --boundary clean_assets/field_validation/reference/madrid_boundary_ign.geojson \
       --boundary-authoritative
   ```
4. The output loses its `PROVISIONAL` marking only when an authoritative
   boundary is declared.

Until then, the plot plan the engine produces demonstrates correct plot
geometry (distinct, SM-1…SM-4-valid impact/control coordinates) but its
**jurisdiction filter is provisional** and every selected trail's distance to
the boundary is recorded in the plan's provenance sidecar so it can be vetted
by hand.

## Provenance

| Field | Value |
|---|---|
| Layer | Comunidad de Madrid (admin-1) |
| Source | Natural Earth 10m Admin 1 – States, Provinces (`nvkelso/natural-earth-vector`) |
| Licence | Public domain (CC0) |
| Scale | ~1:10 000 000 |
| Retrieved | 2026-08-10, via `raw.githubusercontent.com` |
| Clipped to | bbox (−4.6, 40.5, −3.5, 41.3) around PNSG |
| Authoritative? | **No** — placeholder pending IGN Líneas Límite |
