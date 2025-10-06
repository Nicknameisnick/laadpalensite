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

# Load the dataset (skip the fake header row)
df = pd.read_csv("personenautos_csb.csv", sep=";", header=None, skiprows=[0])

# The first valid data row contains the column names, so we extract them:
columns = df.iloc[0].tolist()
df.columns = columns
df = df[1:]  # Remove the row with the column names

# Keep only relevant columns
df = df[['Wegvoertuigen', 'Benzine', 'Diesel', 'Full elektric (BEV)', 'Totaal hybrides']]

# Rename columns for clarity
df.rename(columns={
    'Wegvoertuigen': 'kwartaal',
    'Full elektric (BEV)': 'elektrisch',
    'Totaal hybrides': 'hybride'
}, inplace=True)

# Convert numeric columns to numbers
for col in ['Benzine', 'Diesel', 'elektrisch', 'hybride']:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Convert 'kwartaal' like "2007 1e kwartaal" → datetime (using first month of quarter)
def parse_quarter(q):
    try:
        year, quarter = q.split()
        q_num = int(quarter[0])  # e.g., '1e' → 1
        month = (q_num - 1) * 3 + 1
        return pd.Timestamp(year=int(year), month=month, day=1)
    except:
        return pd.NaT

df['datum'] = df['kwartaal'].apply(parse_quarter)
df = df.dropna(subset=['datum'])

# Melt the DataFrame for Plotly
melted = df.melt(id_vars='datum', value_vars=['Benzine', 'Diesel', 'elektrisch', 'hybride'],
                 var_name='brandstof', value_name='aantal')

# Sort by date
melted = melted.sort_values('datum')

# Define color map
color_map = {
    'elektrisch': 'yellow',
    'hybride': 'green',
    'Benzine': 'darkblue',
    'Diesel': 'saddlebrown'
}

# Slider limits
min_date = melted['datum'].min().to_pydatetime()
max_date = melted['datum'].max().to_pydatetime()

selected_date = st.slider(
    "Selecteer periode (kwartaal)",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date),
    format="YYYY-MM"
)

# Filter data
filtered = melted[(melted['datum'] >= selected_date[0]) & (melted['datum'] <= selected_date[1])]

# Plot
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

# Tab 3: Laadpalen map
with tab3:
    m = build_map()
    st_folium(m, width=800, height=600)



