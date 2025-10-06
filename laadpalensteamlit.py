import requests
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

st.set_page_config(page_title="Laadpalen en Elektrisch vervoer", layout="wide")

# -------------------------------
# 🚀 Cached Functions
# -------------------------------

@st.cache_data(ttl=3600)  # cache for 1 hour
def load_data():
    url = "https://api.openchargemap.io/v3/poi/?output=json&countrycode=NL&maxresults=6000&compact=true&verbose=false&key=2960318e-86ae-49e0-82b1-3c8bc6790b41"
    response = requests.get(url)
    responsejson = response.json()
    laadpalen = pd.json_normalize(responsejson)

    # Flatten connections
    df4 = pd.json_normalize(laadpalen.Connections)
    df5 = pd.json_normalize(df4[0])
    laadpalen = pd.concat([laadpalen, df5], axis=1)

    # Drop unused columns
    columns_to_drop = [
        "Amps", "Voltage", "AddressInfo.StateOrProvince", "NumberOfPoints",
        "UsageCost", "UUID", "DataProviderID", "Reference", "Connections",
        "AddressInfo.DistanceUnit", "AddressInfo.AddressLine2",
        "AddressInfo.ContactTelephone1", "AddressInfo.RelatedURL",
        "DataProvidersReference", "IsRecentlyVerified", "DataQualityLevel",
        "AddressInfo.CountryID", "SubmissionStatusTypeID"
    ]
    laadpalen.drop(columns_to_drop, axis=1, inplace=True)

    # Add geometry
    geometry = [Point(a) for a in zip(laadpalen["AddressInfo.Longitude"], laadpalen["AddressInfo.Latitude"])]
    laadpalen_gdf = gpd.GeoDataFrame(laadpalen, geometry=geometry, crs="EPSG:4326")

    return laadpalen_gdf


def build_map(laadpalen_gdf):
    m = folium.Map(location=[52.1, 5.3], zoom_start=8)
    marker_cluster = MarkerCluster().add_to(m)

    for _, row in laadpalen_gdf.iterrows():
        folium.Marker(
            location=[row["AddressInfo.Latitude"], row["AddressInfo.Longitude"]],
            popup=row.get("AddressInfo.Title", "Charging Station")
        ).add_to(marker_cluster)

    return m


# -------------------------------
# 📊 Streamlit Layout
# -------------------------------

st.sidebar.title("Controls")

year_range = st.sidebar.slider("Select Year Range", 2010, 2025, (2010, 2025))  # placeholder for real daterange
show_lines = st.sidebar.checkbox("Show Lines", value=True)
show_points = st.sidebar.checkbox("Show Points", value=True)

tab1, tab2, tab3 = st.tabs([
    "Voertuigverdeling over de tijd",
    "Oplaad data",
    "Laadpalen map"
])

with tab3:
    # Load data once (cached)
    laadpalen_gdf = load_data()

    # Build map (not cached, so it always renders properly in Streamlit)
    m = build_map(laadpalen_gdf)

    # Render interactive map
    st_folium(m, width=800, height=600)
