"""
SNTO Smart Natural Tourism Observatory -- Interactive Dashboard
Streamlit + Folium dashboard for the Sierra del Rincón Biosphere Reserve pilot.

Run with:
    streamlit run app.py
"""
from __future__ import annotations

import os

import folium
import geopandas as gpd
import streamlit as st
from sqlalchemy import create_engine
from streamlit_folium import st_folium

# ── Page config (must be the first Streamlit call) ────────────────────────────
st.set_page_config(
    page_title="SNTO — Sierra del Rincón Destination Dashboard",
    layout="wide",
)

# ── DB credentials (override via env vars) ────────────────────────────────────
_DB_HOST = os.getenv("SNTO_DB_HOST", "localhost")
_DB_PORT = int(os.getenv("SNTO_DB_PORT", "5432"))
_DB_NAME = os.getenv("SNTO_DB_NAME", "snto")
_DB_USER = os.getenv("SNTO_DB_USER", "postgres")
_DB_PASS = os.getenv("SNTO_DB_PASS", "Navidesalehin_1379")

# Sierra del Rincón Biosphere Reserve, northeast Madrid province
_MAP_CENTER = [41.14, -3.52]
_MAP_ZOOM   = 12


# ── Data loader ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner="Loading trail data from PostGIS...")
def load_trails() -> gpd.GeoDataFrame:
    """Read production_hiking_trails from PostGIS into a WGS-84 GeoDataFrame."""
    engine = create_engine(
        f"postgresql+psycopg2://{_DB_USER}:{_DB_PASS}"
        f"@{_DB_HOST}:{_DB_PORT}/{_DB_NAME}"
    )
    # SELECT * includes the primary key `id`, required for fallback name generation
    gdf = gpd.read_postgis(
        "SELECT * FROM production_hiking_trails ORDER BY id",
        engine,
        geom_col="geometry",
    )

    # Ensure CRS is EPSG:4326 (Folium requires WGS-84)
    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=4326)
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    # Smart fallback: replace null/empty names with a location-aware descriptor
    if "name" not in gdf.columns:
        gdf["name"] = None

    unnamed_mask = gdf["name"].isna() | (gdf["name"].astype(str).str.strip().isin(["", "None"]))
    if unnamed_mask.any():
        def _fallback_name(row: gpd.GeoSeries) -> str:
            centroid = row.geometry.centroid
            lat = round(centroid.y, 4)
            lon = round(centroid.x, 4)
            return f"Unnamed Trail (ID: {row['id']}) [Lat: {lat}, Lon: {lon}]"

        gdf.loc[unnamed_mask, "name"] = gdf.loc[unnamed_mask].apply(_fallback_name, axis=1)

    # Graceful fallback when TIS engine has not yet been run
    for col, default in [
        ("avg_ndvi",           None),
        ("avg_ndmi",           None),
        ("ehs_index",          None),
        ("delta_ehs",          None),
        ("needs_intervention", False),
        ("tis_budget_eur",     0.0),
        ("annual_visitors",    0),
        ("priority_score",     0.0),
    ]:
        if col not in gdf.columns:
            gdf[col] = default

    gdf["needs_intervention"] = gdf["needs_intervention"].fillna(False)
    gdf["tis_budget_eur"]     = gdf["tis_budget_eur"].fillna(0.0)
    gdf["annual_visitors"]    = gdf["annual_visitors"].fillna(0).astype(int)
    gdf["priority_score"]     = gdf["priority_score"].fillna(0.0)
    return gdf


def _fmt_eur(value: float) -> str:
    return f"€ {value:,.0f}"


# ── Load data ─────────────────────────────────────────────────────────────────
try:
    gdf = load_trails()
    _load_error: str | None = None
except Exception as exc:
    gdf = None
    _load_error = str(exc)


# ── Header ────────────────────────────────────────────────────────────────────
st.title("Smart Natural Tourism Observatory")
st.markdown(
    "**Destination Management Dashboard** &nbsp;·&nbsp; "
    "Sierra del Rincón Biosphere Reserve, Madrid, Spain"
)
st.divider()

if _load_error:
    st.error(f"Database connection failed: {_load_error}")
    st.info(
        "Ensure PostgreSQL is running and the three ETL scripts have been executed in order:  \n"
        "`db_production_seeder.py` → `etl_raster_intersection.py` → `tis_engine.py`"
    )
    st.stop()


# ── Section 1: KPIs ───────────────────────────────────────────────────────────
critical_mask  = gdf["needs_intervention"] == True
total_trails   = len(gdf)
critical_count = int(critical_mask.sum())
total_budget   = float(gdf["tis_budget_eur"].sum())
max_visitors   = int(gdf["annual_visitors"].max()) if total_trails else 0
avg_visitors   = int(gdf["annual_visitors"].mean()) if total_trails else 0

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

kpi1.metric(
    label="Total Trails Analysed",
    value=total_trails,
)
kpi2.metric(
    label="Critical Trails",
    value=f"{critical_count} / {total_trails}",
    delta=f"{critical_count / total_trails * 100:.0f}% require intervention" if total_trails else None,
    delta_color="inverse",
    help="Trails where Priority Score > 60 (needs_intervention = True)",
)
kpi3.metric(
    label="Total Restoration Budget",
    value=_fmt_eur(total_budget),
    help="Sum of TIS budget across all critical trails  "
         "(formula: trail length × €15.50/m × EHS/100)",
)
kpi4.metric(
    label="Max Tourist Volume",
    value=f"{max_visitors:,}",
    delta=f"Avg {avg_visitors:,} visitors / trail",
    delta_color="off",
    help="Peak annual visitor count across all analysed trails",
)

st.divider()


# ── Section 2: Interactive map ────────────────────────────────────────────────
st.subheader("Trail Health Map")
st.caption(
    "Green = healthy (EHS ≤ 60)  |  Red = critical (EHS > 60)  |  "
    "Hover a trail for details."
)

m = folium.Map(
    location=_MAP_CENTER,
    zoom_start=_MAP_ZOOM,
    tiles="CartoDB positron",
)

for _, row in gdf.iterrows():
    geom = row.geometry
    if geom is None or geom.is_empty:
        continue

    needs_action: bool = bool(row["needs_intervention"])
    color    = "red" if needs_action else "green"
    name     = row["name"]  # fallback name already generated in load_trails()
    ehs      = row.get("ehs_index")
    budget   = float(row.get("tis_budget_eur") or 0.0)
    visitors = int(row.get("annual_visitors") or 0)
    priority = row.get("priority_score")

    ehs_display      = f"{ehs:.1f}" if ehs is not None else "N/A"
    priority_display = f"{priority:.1f}" if priority is not None else "N/A"
    visitors_display = f"{visitors:,}"
    budget_display   = _fmt_eur(budget) if needs_action else "No budget required"
    status_label     = "CRITICAL — intervention required" if needs_action else "Healthy"

    tooltip = folium.Tooltip(
        f"<b>{name}</b><br>"
        f"Status: <span style='color:{color};font-weight:bold'>{status_label}</span><br>"
        f"EHS (Eco Stress): {ehs_display}<br>"
        f"Annual Visitors: {visitors_display}<br>"
        f"Priority Score: {priority_display}<br>"
        f"Estimated Budget: {budget_display}",
        sticky=True,
    )

    folium.GeoJson(
        geom.__geo_interface__,
        style_function=lambda _feat, c=color: {
            "color":   c,
            "weight":  3,
            "opacity": 0.85,
        },
        tooltip=tooltip,
    ).add_to(m)

# Floating legend
legend_html = """
<div style="
    position: fixed; bottom: 36px; left: 36px; z-index: 1000;
    background: white; padding: 10px 16px; border: 1px solid #bbb;
    border-radius: 6px; font-size: 13px; font-family: sans-serif; line-height: 1.8;
    box-shadow: 2px 2px 6px rgba(0,0,0,.15);">
  <b>Trail Status</b><br>
  <span style="color:green;font-size:18px;">&#9644;</span>&nbsp; Healthy &nbsp;(EHS &le; 60)<br>
  <span style="color:red;font-size:18px;">&#9644;</span>&nbsp; Critical &nbsp;(EHS &gt; 60)
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

st_folium(m, use_container_width=True, height=520)

st.divider()


# ── Section 3: Priority data table ───────────────────────────────────────────
st.subheader("Top 10 Priority Trails — Action Required")
st.caption("Sorted by Priority Score (descending). Higher score = more urgent intervention.")

priority_cols = {
    "name":            "Trail Name",
    "ehs_index":       "EHS Index",
    "priority_score":  "Priority Score",
    "annual_visitors": "Annual Visitors",
    "tis_budget_eur":  "Budget (EUR)",
}

available_cols = [c for c in priority_cols if c in gdf.columns]

priority_df = (
    gdf[critical_mask][available_cols]
    .copy()
    .sort_values("priority_score", ascending=False)
    .head(10)
    .reset_index(drop=True)
    .rename(columns=priority_cols)
)
priority_df.index = priority_df.index + 1  # 1-based rank

fmt_map: dict[str, str] = {}
if "EHS Index"       in priority_df.columns:  fmt_map["EHS Index"]       = "{:.1f}"
if "Priority Score"  in priority_df.columns:  fmt_map["Priority Score"]  = "{:.1f}"
if "Annual Visitors" in priority_df.columns:  fmt_map["Annual Visitors"] = "{:,.0f}"
if "Budget (EUR)"    in priority_df.columns:  fmt_map["Budget (EUR)"]    = "€ {:,.0f}"

styled = priority_df.style.format(fmt_map, na_rep="N/A")
if "Priority Score" in priority_df.columns:
    styled = styled.background_gradient(subset=["Priority Score"], cmap="RdYlGn_r")

st.dataframe(styled, use_container_width=True)

st.caption(
    "EHS (Environmental Health Stress) 0–100: higher = more degraded vegetation. "
    "Priority Score combines EHS and tourist pressure. Critical threshold: Priority > 60. "
    "Budget formula: trail length (m) × €15.50/m × (EHS / 100)."
)

st.divider()


# ── Section 4: Temporal Degradation Analysis ─────────────────────────────────
st.subheader("Temporal Degradation Analysis")
st.caption(
    "Positive Delta EHS values represent an accelerated increase in environmental stress "
    "between Spring and Summer, identifying trails at higher risk of seasonal degradation."
)

if "delta_ehs" in gdf.columns and gdf["delta_ehs"].notna().any():
    delta_df = (
        gdf[["name", "delta_ehs"]]
        .dropna(subset=["delta_ehs"])
        .sort_values("delta_ehs", ascending=False)
        .head(10)
        .set_index("name")
        .rename(columns={"delta_ehs": "Delta EHS (Summer − Spring)"})
    )
    st.bar_chart(delta_df)
else:
    st.info(
        "Delta EHS data is not yet available. "
        "Run `calculate_delta_ehs.py` to populate the `delta_ehs` column."
    )
