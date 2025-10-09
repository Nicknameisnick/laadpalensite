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
    show_reg_diesel = st.toggle("Toon regressielijn Diesel", value=False)

    fig = px.line(
        filtered,
        x='datum',
        y='aantal',
        color='brandstof',
        color_discrete_map=color_map,
        title="Aantal verkochte personenauto’s per brandstofcategorie (per kwartaal)"
    )

    # Add regressions with future projection to 2030
    future_end = pd.Timestamp('2030-01-01')

    for brand in ['Benzine', 'elektrisch', 'hybride', 'Diesel']:
        show_toggle = (
            (brand == 'Benzine' and show_reg_benzine) or
            (brand == 'elektrisch' and show_reg_elektrisch) or
            (brand == 'hybride' and show_reg_hybride) or
            (brand == 'Diesel' and show_reg_diesel)
        )
        if show_toggle:
            data = filtered[filtered['brandstof'] == brand].sort_values('datum')
            if len(data) > 1:
                # Prepare regression input
                x = np.arange(len(data))
                y = data['aantal'].values
                slope, intercept, r_value, p_value, _ = stats.linregress(x, y)

                # Predict future values until 2030
                last_date = data['datum'].max()
                future_dates = pd.date_range(last_date, future_end, freq='QS')[1:]  # quarterly steps
                total_x = np.arange(len(data) + len(future_dates))
                predicted = intercept + slope * total_x
                full_dates = pd.concat([data['datum'], pd.Series(future_dates)], ignore_index=True)

                # Add regression line
                fig.add_scatter(
                    x=full_dates,
                    y=predicted,
                    mode='lines',
                    name=f"Regressie {brand} (p={p_value:.3e}, r={r_value:.3f})",
                    line=dict(color=color_map[brand], dash='dot')
                )

    fig.update_layout(
        plot_bgcolor='#1e222b',
        paper_bgcolor='#1e222b',
        font=dict(color='white', size=20),
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
        textposition='auto',
        offsetgroup=None,
        alignmentgroup=None
    )

    bar_fig.update_layout(
        width=800,
        plot_bgcolor='#1e222b',
        paper_bgcolor='#1e222b',
        font=dict(color='white', size=20),
        legend=dict(font=dict(color='white')),
        xaxis=dict(
            title_font=dict(color='white'),
            tickfont=dict(color='white'),
            type='category',
            categoryorder='array',
            categoryarray=totalen['brandstof'].tolist(),
        ),
        yaxis=dict(title_font=dict(color='white'), tickfont=dict(color='white')),
        bargap=0.2,
        height=350
    )

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
     font=dict(color='white', size=20),
     legend=dict(font=dict(color='white')),
     xaxis=dict(
         title_font=dict(color='white'),
         tickfont=dict(color='white'),
         type='category',
         categoryorder='array',
         categoryarray=totalen['brandstof'].tolist(),
     ),
     yaxis=dict(title_font=dict(color='white'), tickfont=dict(color='white')),
     bargap=0.2,
     height=350
 )



    # ---- Load and clean personenautos_huidig.csv ----
    df_huidig = pd.read_csv("personenautos_huidig.csv")

    # Drop index column if it exists
    if 'Unnamed: 0' in df_huidig.columns:
        df_huidig = df_huidig.drop(columns=['Unnamed: 0'])

    # Fix potential column name typo
    df_huidig.rename(columns={'Elekrticiteit': 'Elektriciteit'}, inplace=True)

    # Ensure 'Jaar' is a proper column, not index
    if 'Jaar' not in df_huidig.columns:
        df_huidig = df_huidig.reset_index().rename(columns={'index': 'Jaar'})

    # Convert to numeric
    df_huidig['Jaar'] = pd.to_numeric(df_huidig['Jaar'], errors='coerce')


    # Melt into long format for Plotly
    df_huidig_melted = df_huidig.melt(
        id_vars='Jaar',
        var_name='Brandstof',
        value_name='Aantal (miljoen)'
    )

    huidig_color_map = {
        'Benzine': 'dodgerblue',
        'Diesel': 'saddlebrown',
        'LPG': 'mediumpurple',
        'Elektriciteit': 'gold'
    }

   line_fig = px.line(
    df_huidig_melted,
    x='Jaar',
    y='Aantal (miljoen)',
    color='Brandstof',
    color_discrete_map=huidig_color_map,
    title="Aantal motorvoertuigen actief (2019–2025)",
    markers=True  # show data points
)

    line_fig.update_layout(
        plot_bgcolor='#1e222b',
        paper_bgcolor='#1e222b',
        font=dict(color='white', size=20),
        legend=dict(font=dict(color='white')),
        xaxis=dict(
            title_font=dict(color='white'),
            tickfont=dict(color='white'),
            dtick=1,
            showgrid=True,
            gridcolor='gray'
        ),
        yaxis=dict(
            title_font=dict(color='white'),
            tickfont=dict(color='white'),
            showgrid=True,
            gridcolor='gray'
        ),
        hovermode='x unified',
        width=800,
        height=350
    )




# ---- Place both graphs next to each other ----
col1, col2 = st.columns(2)

with col1:
    st.plotly_chart(bar_fig, use_container_width=True, key="bar_fig_chart")
     
    st.markdown(
        "Bron (verkoopdata): [CBS - Verkochte wegvoertuigen; nieuw en tweedehands, voertuigsoort, brandstof]"
        "(https://opendata.cbs.nl/#/CBS/nl/dataset/85898NED/table)"
    )

with col2:
    st.plotly_chart(line_fig, use_container_width=True, key="line_fig_chart")

    st.markdown('</div>', unsafe_allow_html=True)

    # ---- Sources ----
   

    st.markdown(
        "Bron (actieve voertuigen): "
        "[Compendium voor de Leefomgeving - Aantal motorvoertuigen actief, 2019–2025]"
        "(https://www.clo.nl/indicatoren/nl002627-aantal-motorvoertuigen-actief-2019-2025#:~:text=Het%20personenautopark%20is%20tussen%202019,9%20tot%207%2C2%20procent.)"
    )

with tab2:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)

    # ===========================
    # Load and clean data
    # ===========================
    df_lp = pd.read_csv('laadpaaldata_cleaned.csv')

    # Ensure datetime columns
    df_lp['Started'] = pd.to_datetime(df_lp['Started'], errors='coerce')
    df_lp['Ended'] = pd.to_datetime(df_lp['Ended'], errors='coerce')
    df_lp = df_lp.dropna(subset=['Started', 'Ended'])

    # ===========================
    # 1. MaxPower frequency (250W bins)
    # ===========================
    bin_width = 250
    max_power_bins = range(0, int(df_lp['MaxPower'].max()) + bin_width, bin_width)
    df_lp['MaxPower_bin'] = pd.cut(df_lp['MaxPower'], bins=max_power_bins)

    maxpower_freq = df_lp['MaxPower_bin'].value_counts().reset_index()
    maxpower_freq.columns = ['MaxPower_bin', 'Frequency']
    maxpower_freq = maxpower_freq.sort_values('MaxPower_bin')

    # ✅ FIX: Convert Interval objects to readable strings
    maxpower_freq['MaxPower_bin'] = maxpower_freq['MaxPower_bin'].astype(str)

    fig_maxpower = px.bar(
        maxpower_freq,
        x='MaxPower_bin',
        y='Frequency',
        text='Frequency',
        title='Frequentie van MaxPower bij laadpalen (in 1 kW-bins)',
        labels={'MaxPower_bin': 'Max Power (kW-bins)', 'Frequency': 'Aantal keren'},
        width=800
    )
    fig_maxpower.update_traces(textposition='auto')
    fig_maxpower.update_layout(
        plot_bgcolor='#1e222b',
        paper_bgcolor='#1e222b',
        font=dict(color='white', size=20),
        xaxis=dict(title_font=dict(color='white'), tickfont=dict(color='white')),
        yaxis=dict(title_font=dict(color='white'), tickfont=dict(color='white'))
    )
    st.plotly_chart(fig_maxpower, use_container_width=True)

    # ===========================
    # 2. Average occupancy per hour of day
    # ===========================
    hours = range(24)
    occupancy = []

    for hour in hours:
        active = df_lp[(df_lp['Started'].dt.hour <= hour) & (df_lp['Ended'].dt.hour > hour)]
        occupancy.append(len(active))

    occupancy_per_hour = pd.DataFrame({
        'Hour': hours,
        'AvgOccupancy': occupancy
    })

    days_in_data = (df_lp['Ended'].max() - df_lp['Started'].min()).days
    occupancy_per_hour['AvgOccupancy'] = occupancy_per_hour['AvgOccupancy'] / days_in_data
    occupancy_per_hour['AvgOccupancy'] = occupancy_per_hour['AvgOccupancy'].clip(lower=0)

    fig_occupancy = px.bar(
        occupancy_per_hour,
        x='Hour',
        y='AvgOccupancy',
        text='AvgOccupancy',
        title='Gemiddelde bezetting per uur van de dag',
        labels={'Hour': 'Uur van de dag', 'AvgOccupancy': 'Gemiddeld aantal laadpalen in gebruik'},
        width=800
    )
    fig_occupancy.update_traces(texttemplate='%{text:.2f}', textposition='auto')
    fig_occupancy.update_layout(
        plot_bgcolor='#1e222b',
        paper_bgcolor='#1e222b',
        font=dict(color='white', size=20),
        xaxis=dict(title_font=dict(color='white'), tickfont=dict(color='white')),
        yaxis=dict(title_font=dict(color='white'), tickfont=dict(color='white'))
    )
    st.plotly_chart(fig_occupancy, use_container_width=True)

    # ===========================
    # 3. ConnectedTime vs ChargeTime boxplot
    # ===========================
    df_compare = df_lp[['ConnectedTime', 'ChargeTime']].melt(var_name='Type', value_name='TimeHours')

    fig_compare = px.box(
        df_compare,
        x='Type',
        y='TimeHours',
        color='Type',
        title='Vergelijking tussen ConnectedTime en ChargeTime',
        labels={'TimeHours': 'Tijd (uur)'},
        width=800
    )
    fig_compare.update_layout(
        plot_bgcolor='#1e222b',
        paper_bgcolor='#1e222b',
        font=dict(color='white', size=20),
        xaxis=dict(title_font=dict(color='white'), tickfont=dict(color='white')),
        yaxis=dict(title_font=dict(color='white'), tickfont=dict(color='white')),
        showlegend=False
    )
    st.plotly_chart(fig_compare, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

# -----------------------
# Cache: laad laadpalen (OpenChargeMap)
# -----------------------
@st.cache_data(ttl=3600)
def laad_laadpalen():
    url = "https://api.openchargemap.io/v3/poi/?output=json&countrycode=NL&maxresults=10000&compact=true&verbose=false&key=2960318e-86ae-49e0-82b1-3c8bc6790b41"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()
    df = pd.json_normalize(data)

    # verwijder rijen zonder coördinaten
    df = df.dropna(subset=["AddressInfo.Latitude", "AddressInfo.Longitude"])
    # maak geometrie aan
    geometry = [Point(xy) for xy in zip(df["AddressInfo.Longitude"], df["AddressInfo.Latitude"])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
    return gdf

# -----------------------
# Cache: provincies laden uit GeoJSON
# -----------------------
@st.cache_data(ttl=86400)
def laad_provincies():
    url = "https://www.webuildinternet.com/articles/2015-07-19-geojson-data-of-the-netherlands/provinces.geojson"
    provincies = gpd.read_file(url)
    provincies = provincies.to_crs("EPSG:4326")
    return provincies

# -----------------------
# Hulpfunctie: kolomnaam zoeken
# -----------------------
def vind_naam_kolom(gdf):
    kandidaten = ["name", "naam", "provincie", "provincienaam", "NAME", "Name"]
    for c in kandidaten:
        if c in gdf.columns:
            return c
    for c in gdf.columns:
        if c != gdf.geometry.name:
            return c
    return None

# -----------------------
# Provincies koppelen aan laadpalen
# -----------------------
def koppel_provincies(laadpalen, provincies):
    punten = laadpalen.copy()
    provs = provincies.copy()

    if punten.crs != provs.crs:
        provs = provs.to_crs(punten.crs)

    kolom = vind_naam_kolom(provs)

    try:
        joined = gpd.sjoin(punten, provs[[kolom, provs.geometry.name]], how="left", predicate="within")
        joined = joined.rename(columns={kolom: "Provincie"})
        joined = joined.drop(columns=[c for c in ["index_right"] if c in joined.columns])
        return joined
    except Exception:
        st.warning("Snelle ruimtelijke join mislukt. Valt terug op tragere methode. Installeer 'rtree' voor betere prestaties.")
        punten["Provincie"] = None
        for _, prow in provs.iterrows():
            naam = prow.get(kolom) if kolom else None
            mask = punten.geometry.within(prow.geometry)
            punten.loc[mask, "Provincie"] = naam
        return punten

# -----------------------
# Kaart bouwen
# -----------------------
def bouw_kaart(gdf, locatie=[52.1, 5.3], zoom=8):
    m = folium.Map(location=locatie, zoom_start=zoom)
    cluster = MarkerCluster().add_to(m)
    for _, r in gdf.iterrows():
        folium.Marker(
            location=[r["AddressInfo.Latitude"], r["AddressInfo.Longitude"]],
            popup=r.get("AddressInfo.Title", "Laadpunt")
        ).add_to(cluster)
    return m

# -----------------------
# Streamlit UI
# -----------------------
with tab3:
    st.markdown('<div class="chart-container" style="text-align:center;">', unsafe_allow_html=True)

    st.title("🔌 Laadpalen in Nederland per Provincie")

    # laad data
    laadpalen = laad_laadpalen()
    provincies = laad_provincies()
    laadpalen_met_prov = koppel_provincies(laadpalen, provincies)

    # overzicht aantal laadpalen
    st.subheader("Aantal laadpalen per provincie")
    counts = laadpalen_met_prov["Provincie"].fillna("Onbekend").value_counts()
    st.dataframe(counts)

    # dropdown voor provincies
    opties = ["Alle provincies"] + sorted([p for p in laadpalen_met_prov["Provincie"].dropna().unique()])
    keuze = st.selectbox("Kies een provincie:", opties)

    # filter & kaart centreren
    if keuze != "Alle provincies":
        gefilterd = laadpalen_met_prov[laadpalen_met_prov["Provincie"] == keuze]
        if len(gefilterd) == 0:
            st.info("Geen laadpalen gevonden in deze provincie.")
            gefilterd = laadpalen_met_prov.iloc[0:0]
            center = [52.1, 5.3]
            zoom = 8
        else:
            center = [gefilterd["AddressInfo.Latitude"].mean(), gefilterd["AddressInfo.Longitude"].mean()]
            zoom = 10
    else:
        gefilterd = laadpalen_met_prov
        center = [52.1, 5.3]
        zoom = 8

    # kaart tonen
    m = bouw_kaart(gefilterd, locatie=center, zoom=zoom)
    st_folium(m, width=1750, height=750)

    st.markdown('</div>', unsafe_allow_html=True)

































