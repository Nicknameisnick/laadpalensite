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

Laadpalen = pd.read_csv('laadpalen_api_data.csv')

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
    # Existing auto_per_maand plot
    data_cars = pd.read_pickle('cars.pkl')
    data_cars['brandstof'] = data_cars['handelsbenaming'].apply(bepaal_brandstof)
    auto_per_maand(data_cars)

    # -------------------------------
    # Personenautos CSV plot
    # -------------------------------
    df = pd.read_csv("personenautos_csb.csv", sep=";", header=None, skiprows=[0])
    # rest of the code must also be indented under this 'with' block
    columns = df.iloc[0].tolist()
    df.columns = columns
    df = df[1:]
    df = df[['Wegvoertuigen', 'Benzine', 'Diesel', 'Full elektric (BEV)', 'Totaal hybrides']]
    df.rename(columns={
        'Wegvoertuigen': 'kwartaal',
        'Full elektric (BEV)': 'elektrisch',
        'Totaal hybrides': 'hybride'
    }, inplace=True)

    for col in ['Benzine', 'Diesel', 'elektrisch', 'hybride']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    def parse_quarter(q):
        try:
            year, quarter = q.split()
            q_num = int(quarter[0])
            month = (q_num - 1) * 3 + 1
            return pd.Timestamp(year=int(year), month=month, day=1)
        except:
            return pd.NaT

    df['datum'] = df['kwartaal'].apply(parse_quarter)
    df = df.dropna(subset=['datum'])

    melted = df.melt(id_vars='datum', value_vars=['Benzine', 'Diesel', 'elektrisch', 'hybride'],
                     var_name='brandstof', value_name='aantal')
    melted = melted.sort_values('datum')

    color_map = {
        'elektrisch': 'yellow',
        'hybride': 'green',
        'Benzine': 'darkblue',
        'Diesel': 'saddlebrown'
    }

    min_date = melted['datum'].min().to_pydatetime()
    max_date = melted['datum'].max().to_pydatetime()

    selected_date = st.slider(
        "Selecteer periode (kwartaal personenauto's)",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="YYYY-MM"
    )

    filtered = melted[(melted['datum'] >= selected_date[0]) & (melted['datum'] <= selected_date[1])]

    fig = px.line(
        filtered,
        x='datum',
        y='aantal',
        color='brandstof',
        color_discrete_map=color_map,
        title="Aantal verkochte personenauto’s per brandstofcategorie (per kwartaal)"
    )

    fig.update_layout(
        xaxis_title="Kwartaal",
        yaxis_title="Aantal auto's",
        hovermode="x unified"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        "Bron: [CBS - Verkochte wegvoertuigen; nieuw en tweedehands, voertuigsoort, brandstof](https://opendata.cbs.nl/#/CBS/nl/dataset/85898NED/table)"
    )


# Tab 3: Laadpalen map
with tab3:
    m = build_map()
    st_folium(m, width=800, height=600)









