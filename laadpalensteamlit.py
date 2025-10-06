import requests
import pandas as pd
import streamlit as st
import plotly.express as px
import geopandas as gpd
from shapely.geometry import Point
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

st.set_page_config(page_title="Laadpalen en Elektrisch vervoer", layout="wide")

# -------------------------------
# API Reader - Laadpalen Data
# -------------------------------
response = requests.get("https://api.openchargemap.io/v3/poi/?output=json&countrycode=NL&maxresults=6000&compact=true&verbose=false&key=2960318e-86ae-49e0-82b1-3c8bc6790b41") 
responsejson = response.json() 
Laadpalen = pd.json_normalize(responsejson) 
df4 = pd.json_normalize(Laadpalen.Connections) 
df5 = pd.json_normalize(df4[0]) 
Laadpalen = pd.concat([Laadpalen, df5], axis=1)

columns_to_drop = [
    "Amps", "Voltage", "AddressInfo.StateOrProvince", "NumberOfPoints", "UsageCost", "UUID", 
    "DataProviderID", "Reference", "Connections", "AddressInfo.DistanceUnit", 
    "AddressInfo.AddressLine2", "AddressInfo.ContactTelephone1", "AddressInfo.RelatedURL", 
    "DataProvidersReference", "IsRecentlyVerified", "DataQualityLevel", "AddressInfo.CountryID", 
    "SubmissionStatusTypeID"
]
Laadpalen.drop(columns_to_drop, axis=1, inplace=True)

geometry = [Point(a) for a in zip(Laadpalen["AddressInfo.Longitude"], Laadpalen["AddressInfo.Latitude"])]
Laadpalen1 = gpd.GeoDataFrame(Laadpalen, geometry=geometry, crs="EPSG:4326")

def build_map():
    m = folium.Map(location=[52.1, 5.3], zoom_start=8)
    marker_cluster = MarkerCluster().add_to(m)
    for _, row in Laadpalen1.iterrows():
        folium.Marker(
            location=[row["AddressInfo.Latitude"], row["AddressInfo.Longitude"]],
            popup=row.get("AddressInfo.Title", "Charging Station")
        ).add_to(marker_cluster)
    return m

# -------------------------------
# Tabs
# -------------------------------
tab1, tab2, tab3 = st.tabs([ 
   "Voertuigverdeling over de tijd", 
   "Oplaad data",
   "Laadpalen map"
])

# Tab 1: Voertuigverdeling
with tab1:
    # -------------------------------
    # Nieuwe grafiek: ontwikkeling brandstof per jaar (2015–2025)
    # -------------------------------

    # Laad de data
    brandstof_per_year = pd.read_csv("brandstof_per_year.csv", index_col=0)

    # Zorg dat index numeriek is (jaren)
    brandstof_per_year.index = brandstof_per_year.index.astype(int)

    # Smelt de data voor Plotly
    df_long = brandstof_per_year.reset_index().melt(
        id_vars="index", var_name="Brandstof", value_name="Aantal"
    )
    df_long.rename(columns={"index": "Jaar"}, inplace=True)

    # Zet het type van Jaar naar int
    df_long["Jaar"] = df_long["Jaar"].astype(int)

    # Voeg een slider toe om jaarrange te kiezen
    min_year, max_year = int(df_long["Jaar"].min()), int(df_long["Jaar"].max())
    selected_years = st.slider(
        "Selecteer periode (jaar)",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year),
        step=1
    )

    # Filter data op geselecteerde jaren
    df_filtered = df_long[
        (df_long["Jaar"] >= selected_years[0]) &
        (df_long["Jaar"] <= selected_years[1])
    ]

    # Kleurenschema instellen
    color_map = {
        'elektrisch': 'yellow',
        'hybride': 'green',
        'benzine': 'darkblue',
        'diesel': 'saddlebrown',
        'waterstof': 'blue'
    }

    # Plotly line chart
    fig_trend = px.line(
        df_filtered,
        x="Jaar",
        y="Aantal",
        color="Brandstof",
        markers=True,
        color_discrete_map=color_map,
        title=f"Ontwikkeling aantal voertuigen per brandstofsoort ({selected_years[0]}–{selected_years[1]})"
    )

    fig_trend.update_layout(
        xaxis_title="Jaar",
        yaxis_title="Aantal voertuigen",
        hovermode="x unified",
        legend_title="Brandstof",
        template="plotly_white"
    )

    # Toon grafiek
    st.plotly_chart(fig_trend, use_container_width=True)
   

# Tab 3: Laadpalen map
with tab3:
    m = build_map()
    st_folium(m, width=800, height=600)


