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
# Custom background + dark theme & styling
# -----------------------------
st.markdown(
    """
    <style>
    /* Background image + slight dark overlay */
    .stApp {
        background-image: url('https://www.power-technology.com/wp-content/uploads/sites/21/2021/09/shutterstock_1864450102-scaled.jpg');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        background-repeat: no-repeat;
    }

    /* Slight overlay so dark chart containers contrast */
    .stApp::before {
        content: "";
        position: fixed;
        inset: 0;
        background: rgba(6,10,15,0.55);
        pointer-events: none;
        z-index: 0;
    }

    /* Increase overall text size (approx 2x) */
    .stApp, .stApp * {
        font-size: 1.4rem !important;
    }

    /* Rounded container look for charts (cards) */
    .chart-container {
        background-color: #1e222b;
        padding: 22px;
        border-radius: 16px;
        margin-bottom: 26px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.45);
        z-index: 2;
    }

    /* Tabs styling */
    .stTabs [role="tab"] {
        color: white !important;
        font-size: 1.1rem !important;
    }
    .stTabs [role="tab"][aria-selected="true"] {
        color: #00c0ff !important;
        font-weight: 700;
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

# ===============================
# Tabs
# ===============================
tab1, tab2, tab3 = st.tabs([
   "Voertuigverdeling over de tijd",
   "Oplaad data",
   "Laadpalen map"
])

# -------------------------------
# Helper: format p-value robustly
# -------------------------------
def format_pvalue(pval_from_linreg, t_stat, df):
    """
    Return a human-readable p-value string.
    If pval_from_linreg > 0 -> format normally.
    If it is zero or underflowed, approximate using t or normal asymptotics and return '<1e-XXX'.
    """
    # if linreg gives a usable p
    if pval_from_linreg is not None and pval_from_linreg > 0:
        if pval_from_linreg >= 1e-4:
            return f"{pval_from_linreg:.4f}"
        else:
            return f"{pval_from_linreg:.2e}"

    # try computing from t and df via t-distribution survival; may underflow too
    if np.isfinite(t_stat) and df > 0:
        p_t = 2.0 * stats.t.sf(abs(t_stat), df)
        if p_t > 0:
            if p_t >= 1e-4:
                return f"{p_t:.4f}"
            else:
                return f"{p_t:.2e}"

        # if still zero, use normal-tail asymptotic approximation
        z = abs(t_stat)
    else:
        # fallback
        z = abs(t_stat) if np.isfinite(t_stat) else None

    if z is None or not np.isfinite(z) or z == 0:
        return "p=nan"

    # asymptotic normal tail: ln p approx = -z^2/2 - ln(z) - 0.5 ln(2π)
    ln_p = - (z**2) / 2.0 - np.log(z) - 0.5 * np.log(2.0 * np.pi)
    log10_p = ln_p / np.log(10.0)
    expo = int(np.floor(log10_p))
    # expo is negative, so show like "<1e-250"
    return f"<1e{expo}"

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
    filtered = filtered[filtered['brandstof'].isin(selected_brandstoffen)]

    # regression toggles (checkboxes)
    show_reg_benzine = st.checkbox("Toon regressielijn Benzine", value=False)
    show_reg_elektrisch = st.checkbox("Toon regressielijn Elektrisch", value=False)

    # line plot
    fig = px.line(
        filtered,
        x='datum',
        y='aantal',
        color='brandstof',
        color_discrete_map=color_map,
        title="Aantal verkochte personenauto’s per brandstofcategorie (per kwartaal)"
    )

    # add regression lines where requested
    for brand in ['Benzine', 'elektrisch']:
        if (brand == 'Benzine' and show_reg_benzine) or (brand == 'elektrisch' and show_reg_elektrisch):
            data = filtered[filtered['brandstof'] == brand].copy()
            if len(data) > 2:
                # use days-since-min for numeric x (better numerics than huge timestamps)
                x_days = (data['datum'] - data['datum'].min()).dt.days.values.astype(float)
                y = data['aantal'].values.astype(float)

                # run linear regression
                slope, intercept, r_value, p_value_lr, std_err = stats.linregress(x_days, y)

                # compute t-stat and p via t-dist (safer)
                if std_err and std_err > 0 and len(y) > 2:
                    t_stat = abs(slope / std_err)
                    dfree = len(y) - 2
                    p_from_t = 2.0 * stats.t.sf(t_stat, dfree)
                else:
                    t_stat = np.inf
                    p_from_t = 0.0

                # decide which p to display; prefer computed p_from_t if > 0
                p_to_format = p_from_t if (p_from_t and p_from_t > 0) else p_value_lr

                # format p robustly
                p_str = format_pvalue(p_to_format, t_stat, dfree if 'dfree' in locals() else 0)

                # add regression line (use same color, dashed)
                # compute fitted values for the plotted x (use original dates)
                fitted = intercept + slope * x_days
                fig.add_scatter(
                    x=data['datum'],
                    y=fitted,
                    mode='lines',
                    name=f"Regressie {brand} (p={p_str}, r={r_value:.3f})",
                    line=dict(color=color_map[brand], dash='dot'),
                    hoverinfo='skip'
                )

    # style the line chart to dark card
    fig.update_layout(
        plot_bgcolor='#1e222b',
        paper_bgcolor='#1e222b',
        font=dict(color='white', size=18),
        legend=dict(font=dict(color='white', size=16)),
        xaxis=dict(title_font=dict(color='white', size=18), tickfont=dict(color='white', size=14)),
        yaxis=dict(title_font=dict(color='white', size=18), tickfont=dict(color='white', size=14)),
        hovermode='x unified',
        margin=dict(l=40, r=20, t=70, b=40)
    )

    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ---- Bar chart (800 px wide) ----
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)

    totalen = filtered.groupby('brandstof', as_index=False)['aantal'].sum()
    # ensure consistent category order as in totalen
    categories = totalen['brandstof'].tolist()

    bar_fig = px.bar(
        totalen,
        x='brandstof',
        y='aantal',
        color='brandstof',
        color_discrete_map=color_map,
        title="Totaal aantal verkochte auto's per brandstofcategorie (geselecteerde periode)",
        text='aantal',
        category_orders={'brandstof': categories}
    )

    bar_fig.update_traces(width=0.6, textposition='auto')

    bar_fig.update_layout(
        width=800,                  # requested width
        plot_bgcolor='#1e222b',
        paper_bgcolor='#1e222b',
        font=dict(color='white', size=18),
        legend=dict(font=dict(color='white', size=16), orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        xaxis=dict(
            title_font=dict(color='white', size=18),
            tickfont=dict(color='white', size=14),
            type='category',
            categoryorder='array',
            categoryarray=categories,
            ticks='outside'
        ),
        yaxis=dict(title_font=dict(color='white', size=18), tickfont=dict(color='white', size=14)),
        bargap=0.20,
        height=360,
        margin=dict(l=40, r=20, t=70, b=40)
    )

    # draw the bar figure in fixed width mode so bars align over labels
    st.plotly_chart(bar_fig, use_container_width=False)

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(
        "Bron: [CBS - Verkochte wegvoertuigen; nieuw en tweedehands, voertuigsoort, brandstof] "
        "(https://opendata.cbs.nl/#/CBS/nl/dataset/85898NED/table)"
    )

# ===============================
# TAB 3: Laadpalen map (bigger)
# ===============================
with tab3:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    m = build_map()
    # bigger map display area
    st_folium(m, width=1200, height=900)
    st.markdown('</div>', unsafe_allow_html=True)
