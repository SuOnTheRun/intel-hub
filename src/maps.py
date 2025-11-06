import pydeck as pdk
import pandas as pd
import streamlit as st

def render_global_air_map(df: pd.DataFrame, center=None, zoom=4):
    if df is None or df.empty:
        st.info("No live aircraft in the selected region right now.")
        return
    lat = float(df["latitude"].mean()); lon = float(df["longitude"].mean())
    if center: lat, lon = center
    view_state = pdk.ViewState(latitude=lat, longitude=lon, zoom=zoom, pitch=30)
    pts = df.rename(columns={"latitude":"lat","longitude":"lon"})

    heat = pdk.Layer(
        "HeatmapLayer",
        data=pts,
        get_position='[lon, lat]',
        aggregation='"SUM"',
        get_weight="velocity",
        radiusPixels=40,
    )
    scatter = pdk.Layer(
        "ScatterplotLayer",
        data=pts,
        get_position='[lon, lat]',
        get_radius=20000,
        pickable=True,
        auto_highlight=True,
    )
    r = pdk.Deck(layers=[heat, scatter], initial_view_state=view_state, map_style="mapbox://styles/mapbox/dark-v11")
    st.pydeck_chart(r, use_container_width=True)

def render_tracks_map(track_df: pd.DataFrame):
    if track_df is None or track_df.empty:
        st.info("No track available (requires authenticated OpenSky and a recent flight).")
        return
    track_df = track_df.dropna(subset=["lat","lon"])
    view_state = pdk.ViewState(latitude=float(track_df["lat"].mean()), longitude=float(track_df["lon"].mean()), zoom=5, pitch=30)
    line = pdk.Layer(
        "PathLayer",
        data=[{"path": track_df[["lon","lat"]].values.tolist(), "name": "track"}],
        get_path="path",
        width_scale=20, width_min_pixels=2,
    )
    r = pdk.Deck(layers=[line], initial_view_state=view_state, map_style="mapbox://styles/mapbox/dark-v11")
    st.pydeck_chart(r, use_container_width=True)

import plotly.express as px
import streamlit as st

def render_global_gdelt_map(gdelt_df, center=(20, 78), zoom=3):
    if gdelt_df is None or gdelt_df.empty:
        return
    if not {"lat","lon"}.issubset(set(gdelt_df.columns)):
        return
    fig = px.density_mapbox(
        gdelt_df.dropna(subset=["lat","lon"]),
        lat="lat", lon="lon", z="risk_score" if "risk_score" in gdelt_df.columns else None,
        radius=12, center={"lat": center[0], "lon": center[1]},
        zoom=zoom, height=520
    )
    fig.update_layout(mapbox_style="carto-darkmatter", margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

def render_risk_or_map(gdelt_df, air_df, region_center_tuple, events_df_for_tiles):
    try:
        if gdelt_df is not None and not gdelt_df.empty and {"lat","lon"}.issubset(set(gdelt_df.columns)):
            from .maps import render_global_gdelt_map
            render_global_gdelt_map(gdelt_df, center=region_center_tuple, zoom=4)
            return
        if air_df is not None and not air_df.empty:
            from .maps import render_global_air_map
            render_global_air_map(air_df, center=region_center_tuple, zoom=4)
            return
    except Exception:
        pass
    # fallback to region tiles
    from .analytics import region_risk_table
    from .ui import render_region_risk_tiles
    rr = region_risk_table(events_df_for_tiles)
    render_region_risk_tiles(rr)
# src/maps.py
import pandas as pd

def kepler_us_incidents_layer(df: pd.DataFrame) -> dict:
    """
    Returns a basic Kepler layer config; you can replace with your full config later.
    """
    if df is None or df.empty:
        return {"data": {"fields": [], "rows": []}, "config": {}}

    table = {
        "data": {
            "fields": [{"name": c, "type": "string"} for c in df.columns],
            "rows": df.astype(str).values.tolist()
        },
        "config": {"version": "v1"}
    }
    return table
