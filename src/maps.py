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
    scatter = pdk.Layer(
        "ScatterplotLayer",
        data=df.rename(columns={"latitude":"lat","longitude":"lon"}),
        get_position='[lon, lat]',
        get_radius=20000,
        pickable=True,
        auto_highlight=True,
    )
    text = pdk.Layer(
        "TextLayer",
        data=df.rename(columns={"latitude":"lat","longitude":"lon"}),
        get_position='[lon, lat]',
        get_text="callsign",
        get_size=12,
        get_alignment_baseline="'top'",
    )
    r = pdk.Deck(layers=[scatter, text], initial_view_state=view_state, map_style="mapbox://styles/mapbox/dark-v11")
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
