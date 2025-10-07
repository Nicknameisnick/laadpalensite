import requests
import pandas as pd
import streamlit as st
import plotly.express as px
import geopandas as gpd
from shapely.geometry import Point
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from scipy import stats
import numpy as np

# -----------------------------
# Page config MUST be first
# -----------------------------
st.set_page_config(page_title="Laadpalen en Elektrisch vervoer", layout="wide")

# -----------------------------
# Custom dark theme & styling
# -----------------------------
st.markdown(
    """
    <style>
   .stApp {
        background-image: url('https://www.power-technology.com/wp-content/uploads/sites/21/2021/09/shutterstock_1864450102-scaled.jpg');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }

    /* Rounded container look for charts */
    .chart-container {
        background-color: #1e222b;
        padding: 20px;
        border-radius: 20px;
        margin-bottom: 25px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }

    /* Tabs text color */
    .stTabs [role="tab"] {
        color: white !important;
    }
    .stTabs [role="tab"][aria-selected="true"] {
        color: #00c0ff !important;
        font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ===============================
# Laadpalen Data en Map
# ===============================
Laadpalen = pd.read_csv('laadpalen_kort.csv')
geometry = [Point(a) for a in zip(Laadpalen["AddressInfo.Longitude"], Laadpalen["AddressInfo.Latitude"])]
Laadpalen1 = gpd.GeoDataFrame(Laadpalen, geometry=geometry, crs="EPSG:4326")

def build_map():
    m = folium.Map(location=[52.1, 5.3], zoom_start=8, tiles="CartoDB dark_matter")
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
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)

    # Lees CSV in
    df_raw = pd.read_csv("personenautos_csb.csv")
    df = df_raw.copy()
    new_cols = df.iloc[0].tolist()
    df.columns = new_cols
    df = df.drop(index=0).reset_index(drop=True)
    df = df[['Brandstofsoort voertuig', 'Benzine', 'Diesel', 'Full elektric (BEV)', 'Totaal hybrides']]

    df.rename(columns={
        'Brandstofsoort voertuig': 'kwartaal',
        'Full elektric (BEV)': 'elektrisch',
        'Totaal hybrides': 'hybride'
    }, inplace=True)

    for col in ['Benzine', 'Diesel', 'elektrisch', 'hybride']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

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

    melted = df.melt(
        id_vars='datum',
        value_vars=['Benzine', 'Diesel', 'elektrisch', 'hybride'],
        var_name='brandstof',
        value_name='aantal'
    )
    melted = melted.sort_values('datum')

    color_map = {
        'Benzine': 'dodgerblue',
        'Diesel': 'saddlebrown',
        'elektrisch': 'gold',
        'hybride': 'limegreen'
    }

    # Date filter
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

    brandstof_opties = filtered['brandstof'].unique().tolist()
    selected_brandstoffen = st.multiselect(
        "Selecteer brandstoftypes om te tonen",
        options=brandstof_opties,
        default=brandstof_opties
    )
    filtered = filtered[filtered['brandstof'].isin(selected_brandstoffen)]

    # Buttons for regression lines
    show_reg_benzine = st.toggle("Toon regressielijn Benzine", value=False)
    show_reg_elektrisch = st.toggle("Toon regressielijn Elektrisch", value=False)
    show_reg_hybride = st.toggle("Toon regressielijn Hybride", value=False)

    fig = px.line(
        filtered,
        x='datum',
        y='aantal',
        color='brandstof',
        color_discrete_map=color_map,
        title="Aantal verkochte personenauto’s per brandstofcategorie (per kwartaal)"
    )

    # Add regressions for Benzine, Elektrisch, Hybride
    for brand in ['Benzine', 'elektrisch', 'hybride']:
        show_toggle = (
            (brand == 'Benzine' and show_reg_benzine) or
            (brand == 'elektrisch' and show_reg_elektrisch) or
            (brand == 'hybride' and show_reg_hybride)
        )
        if show_toggle:
            data = filtered[filtered['brandstof'] == brand]
            if len(data) > 1:
                x = np.arange(len(data))
                y = data['aantal'].values
                slope, intercept, r_value, p_value, _ = stats.linregress(x, y)
                line = intercept + slope * x
                fig.add_scatter(
                    x=data['datum'],
                    y=line,
                    mode='lines',
                    name=f"Regressie {brand} (p={p_value:.3e}, r={r_value:.3f})",
                    line=dict(color=color_map[brand], dash='dot')
                )

    fig.update_layout(
        plot_bgcolor='#1e222b',
        paper_bgcolor='#1e222b',
        font=dict(color='white'),
        legend=dict(font=dict(color='white')),
        xaxis=dict(title_font=dict(color='white'), tickfont=dict(color='white')),
        yaxis=dict(title_font=dict(color='white'), tickfont=dict(color='white')),
        hovermode='x unified'
    )

    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ---- Bar chart ----
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)

    totalen = filtered.groupby('brandstof', as_index=False)['aantal'].sum()
    bar_fig = px.bar(
        totalen,
        x='brandstof',
        y='aantal',
        color='brandstof',
        color_discrete_map=color_map,
        title="Totaal aantal verkochte auto's per brandstofcategorie (geselecteerde periode)",
        text='aantal'
    )

    bar_fig.update_traces(
        width=0.6,
        textposition='auto'
    )

    bar_fig.update_layout(
        width=800,
        plot_bgcolor='#1e222b',
        paper_bgcolor='#1e222b',
        font=dict(color='white'),
        legend=dict(font=dict(color='white')),
        xaxis=dict(
            title_font=dict(color='white'),
            tickfont=dict(color='white'),
            type='category',
            categoryorder='array',
            categoryarray=totalen['brandstof'].tolist()
        ),
        yaxis=dict(title_font=dict(color='white'), tickfont=dict(color='white')),
        bargap=0.2,
        height=350
    )

    st.plotly_chart(bar_fig, use_container_width=False)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(
        "Bron: [CBS - Verkochte wegvoertuigen; nieuw en tweedehands, voertuigsoort, brandstof]"
        "(https://opendata.cbs.nl/#/CBS/nl/dataset/85898NED/table)"
    )

# ===============================
# TAB 3: Laadpalen map
# ===============================
with tab3:
    st.markdown('<div class="chart-container" style="text-align:center;">', unsafe_allow_html=True)
    m = build_map()
    st_folium(m, width=1700, height=750)
    st.markdown('</div>', unsafe_allow_html=True)
