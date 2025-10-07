
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
# Custom dark theme & styling (background + rounded containers)
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
# Laadpalen Data en Map (short file)
# ===============================
Laadpalen = pd.read_csv('laadpalen_kort.csv')
geometry = [Point(a) for a in zip(Laadpalen["AddressInfo.Longitude"], Laadpalen["AddressInfo.Latitude"])]
Laadpalen1 = gpd.GeoDataFrame(Laadpalen, geometry=geometry, crs="EPSG:4326")

def build_map():
    # dark tiles for map
    m = folium.Map(location=[52.1, 5.3], zoom_start=8, tiles="CartoDB dark_matter")
    marker_cluster = MarkerCluster().add_to(m)
    for _, row in Laadpalen1.iterrows():
        folium.Marker(
            location=[row["AddressInfo.Latitude"], row["AddressInfo.Longitude"]],
            popup=row.get("AddressInfo.Title", "Charging Station")
        ).add_to(marker_cluster)
    return m

# -------------------------------
# Helper: format p-value robustly
# -------------------------------
def format_pvalue(pval_from_linreg, t_stat, df):
    """
    Return a human-readable p-value string.
    If linregress p is usable (>0) we format it.
    Otherwise try t-dist; if that underflows produce a safe '<1eXXX' bound.
    """
    # Prefer direct p from linregress if >0
    if pval_from_linreg is not None and pval_from_linreg > 0:
        if pval_from_linreg >= 1e-4:
            return f"{pval_from_linreg:.4f}"
        else:
            return f"{pval_from_linreg:.2e}"

    # Next try t-distribution using t_stat and df
    if np.isfinite(t_stat) and df > 0:
        p_t = 2.0 * stats.t.sf(abs(t_stat), df)
        if p_t > 0:
            if p_t >= 1e-4:
                return f"{p_t:.4f}"
            else:
                return f"{p_t:.2e}"

        # else p_t underflowed to zero; fall through to asymptotic approx

    # Asymptotic normal tail approximation for extreme z = |t_stat|
    if (np.isfinite(t_stat)):
        z = abs(t_stat)
        # if z is tiny/zero -> bail out
        if z < 1e-8:
            return "p=nan"
        # log p approx: ln p ≈ -z^2/2 - ln(z) - 0.5 ln(2π)
        ln_p = - (z**2) / 2.0 - np.log(z) - 0.5 * np.log(2.0 * np.pi)
        log10_p = ln_p / np.log(10.0)
        expo = int(np.floor(log10_p))
        return f"<1e{expo}"
    return "p=nan"

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

    # read file and fix header-in-data
    df_raw = pd.read_csv("personenautos_csb.csv")
    df = df_raw.copy()
    new_cols = df.iloc[0].tolist()
    df.columns = new_cols
    df = df.drop(index=0).reset_index(drop=True)

    # keep relevant cols and rename
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

    # color map (bright on dark)
    color_map = {
        'Benzine': 'dodgerblue',
        'Diesel': 'saddlebrown',
        'elektrisch': 'gold',
        'hybride': 'limegreen'
    }

    # date slider & filtering
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
    filtered = filtered[filtered['brandst]()]()
