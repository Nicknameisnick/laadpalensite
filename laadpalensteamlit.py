import requests
import pandas as pd
import streamlit as st
import plotly.express as px
import geopandas as gpd
from shapely.geometry import Point
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

# -----------------------------
# Page config MUST be first
# -----------------------------
st.set_page_config(page_title="Laadpalen en Elektrisch vervoer", layout="wide")

# -----------------------------
# Custom background and logo
# -----------------------------
st.markdown(
    """
    <style>
    /* Background image */
    .stApp {
        background-image: url('https://i.pinimg.com/originals/2e/48/45/2e48453eb6bed89d50a954cd1de7aa07.jpg');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        color: black; /* make text black */
    }

    /* Top-right logo */
    .logo-container {
        position: fixed;
        top: 10px;
        right: 10px;
        z-index: 9999;
    }

    .logo-container img {
        width: 120px;
        height: auto;
    }
    </style>
    <div class="logo-container">
        <img src="https://zakelijkschrijven.nl/wp-content/uploads/2021/01/HvA-logo.png">
    </div>
    """,
    unsafe_allow_html=True
)

# ===============================
# Laadpalen Data en Map
# ===============================
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

# ===============================
# Tabs
# ===============================
tab1, tab2, tab3 = st.tabs([ 
   "Voertuigverdeling over de tijd", 
   "Oplaad data",
   "Laadpalen map"
])

# ===============================
# TAB 1: Personenauto’s per kwartaal
# ===============================
with tab1:
    # Lees CSV in
    df_raw = pd.read_csv("personenautos_csb.csv")

    # De echte kolomnamen staan in de tweede rij
    df = df_raw.copy()
    new_cols = df.iloc[0].tolist()
    df.columns = new_cols
    df = df.drop(index=0).reset_index(drop=True)

    # Hou alleen relevante kolommen
    df = df[['Brandstofsoort voertuig', 'Benzine', 'Diesel', 'Full elektric (BEV)', 'Totaal hybrides']]

    # Hernoem kolommen
    df.rename(columns={
        'Brandstofsoort voertuig': 'kwartaal',
        'Full elektric (BEV)': 'elektrisch',
        'Totaal hybrides': 'hybride'
    }, inplace=True)

    # Zet getallen om naar numeriek
    for col in ['Benzine', 'Diesel', 'elektrisch', 'hybride']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Converteer kwartaal naar datum
    def parse_quarter(q):
        try:
            year_part, q_part = q.split()[:2]
            year = int(year_part)
            q_num = int(q_part[0])
            month = (q_num - 1) * 3 + 1
            return pd.Timestamp(year=year, month=month, day=1)
        except Exception:
            return pd.NaT

    df['datum'] = df['kwartaal'].apply(parse_quarter)
    df = df.dropna(subset=['datum'])

    # Data smelten
    melted = df.melt(
        id_vars='datum',
        value_vars=['Benzine', 'Diesel', 'elektrisch', 'hybride'],
        var_name='brandstof',
        value_name='aantal'
    )

    melted = melted.sort_values('datum')

    # Kleuren
    color_map = {
        'Benzine': 'darkblue',
        'Diesel': 'saddlebrown',
        'elektrisch': 'yellow',
        'hybride': 'green'
    }

    # Slider
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

    # 🔹 Multi-select dropdown voor brandstofcategorieën
    brandstof_opties = filtered['brandstof'].unique().tolist()
    selected_brandstoffen = st.multiselect(
        "Selecteer brandstoftypes om te tonen",
        options=brandstof_opties,
        default=brandstof_opties
    )

    filtered = filtered[filtered['brandstof'].isin(selected_brandstoffen)]

    # Lijnplot
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
        hovermode="x unified",
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(color="black"),          # alle tekst zwart
        legend=dict(
            font=dict(color="black")
        )
    )

    st.plotly_chart(fig, use_container_width=True)

    # 🔹 Bar chart
    totalen = filtered.groupby('brandstof', as_index=False)['aantal'].sum()

    bar_fig = px.bar(
        totalen,
        x='brandstof',
        y='aantal',
        color='brandstof',
        color_discrete_map=color_map,
        title="Totaal aantal verkochte auto's per brandstofcategorie (geselecteerde periode)"
    )

    bar_fig.update_traces(
        width=0.5  # bredere bars
    )

    bar_fig.update_layout(
        xaxis_title="Brandstofcategorie",
        yaxis_title="Totaal aantal auto's",
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(color="black"),  # alles zwart
        legend=dict(font=dict(color="black")),
        bargap=0.3,
        barmode='group',
        xaxis=dict(tickmode='array', tickvals=list(range(len(totalen))), ticktext=totalen['brandstof'])
    )

    st.plotly_chart(bar_fig, use_container_width=False)

    # Bron
    st.markdown(
        "Bron: [CBS - Verkochte wegvoertuigen; nieuw en tweedehands, voertuigsoort, brandstof]"
        "(https://opendata.cbs.nl/#/CBS/nl/dataset/85898NED/table)"
    )

# ===============================
# TAB 3: Laadpalen map
# ===============================
with tab3:
    m = build_map()
    st_folium(m, width=800, height=600)
