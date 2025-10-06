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

#Api Reader 

response = requests.get("https://api.openchargemap.io/v3/poi/?output=json&countrycode=NL&maxresults=6000&compact=true&verbose=false&key=2960318e-86ae-49e0-82b1-3c8bc6790b41") 
responsejson = response.json() 
Laadpalen = pd.json_normalize(responsejson) 
df4 = pd.json_normalize(Laadpalen.Connections) 
df5 = pd.json_normalize(df4[0]) 
Laadpalen = pd.concat([Laadpalen, df5], axis=1)
columns_to_drop = ["Amps", "Voltage", "AddressInfo.StateOrProvince", "NumberOfPoints", "UsageCost", "UUID", "DataProviderID", "Reference", "Connections", "AddressInfo.DistanceUnit", "AddressInfo.AddressLine2", "AddressInfo.ContactTelephone1", "AddressInfo.RelatedURL", "DataProvidersReference", "IsRecentlyVerified", "DataQualityLevel", "AddressInfo.CountryID", "SubmissionStatusTypeID"]
Laadpalen1 = Laadpalen.drop(columns_to_drop, axis=1, inplace=True) 
geometry = [Point(a) for a in zip(Laadpalen["AddressInfo.Longitude"], Laadpalen["AddressInfo.Latitude"])]
Laadpalen1 = gpd.GeoDataFrame(Laadpalen, geometry=geometry, crs="EPSG:4326")


#streamlit
st.sidebar.title("Controls")

year_range = st.sidebar.slider("Select Year Range", 2010, 2025, (2010, 2025)) #moet nog de juiste daterange worden

show_lines = st.sidebar.checkbox("Show Lines", value=True)
show_points = st.sidebar.checkbox("Show Points", value=True)

tab1, tab2, tab3 = st.tabs([ 
   "Voertuigverdeling over de tijd", 
   "Oplaad data",
   "Laadpalen map"
])
with tab1:
    data_cars = pd.read_pickle('cars.pkl')

    # Functie om brandstofsoort te bepalen
    def bepaal_brandstof(naam):
        naam = naam.lower()
        if any(keyword in naam for keyword in ['edrive', 'id', 'ev', 'electric', 'atto', 'pro', 'ex', 'model', 'e-tron', 'mach-e', 'kw']):
            return 'elektrisch'
        elif any(keyword in naam for keyword in ['hybrid', 'phev', 'plugin']):
            return 'hybride'
        elif 'diesel' in naam:
            return 'diesel'
        elif 'waterstof' in naam or 'fuel cell' in naam:
            return 'waterstof'
        else:
            return 'benzine'  # Default

    # Voeg kolom brandstof toe
    data_cars['brandstof'] = data_cars['handelsbenaming'].apply(bepaal_brandstof)

    # Functie voor grafieken
    def auto_per_maand():
        import plotly.express as px

        # Datum naar datetime
        data_cars['datum_eerste_toelating'] = pd.to_datetime(
            data_cars['datum_eerste_toelating'], format='%Y%m%d', errors='coerce'
        )

        grouped_data = data_cars.groupby(['datum_eerste_toelating', 'brandstof']).size().unstack(fill_value=0)
        grouped_data = grouped_data.reset_index()
        grouped_data[['elektrisch', 'benzine']] = grouped_data[['elektrisch', 'benzine']].cumsum()
        melted_data = grouped_data.melt(id_vars='datum_eerste_toelating', var_name='brandstof', value_name='aantal_autos')

        min_date = melted_data['datum_eerste_toelating'].min().to_pydatetime()
        max_date = melted_data['datum_eerste_toelating'].max().to_pydatetime()

        selected_date = st.slider(
            "Selecteer een maand",
            min_value=min_date,
            max_value=max_date,
            value=(min_date, max_date),
            format="YYYY-MM"
        )

        filtered_data = melted_data[(melted_data['datum_eerste_toelating'] >= selected_date[0]) &
                                    (melted_data['datum_eerste_toelating'] <= selected_date[1])]

        fig_line = px.line(
            filtered_data,
            x='datum_eerste_toelating',
            y='aantal_autos',
            color='brandstof',
            color_discrete_map={'benzine': 'blue', 'elektrisch': 'red'},
            labels={'aantal_autos': 'Aantal auto\'s', 'datum_eerste_toelating': 'Datum eerste toelating'},
            title=f'Cumulatief aantal auto\'s per brandstofsoort van {selected_date[0].strftime("%Y-%m")} tot {selected_date[1].strftime("%Y-%m")}'
        )

        color_map = {'benzine': 'blue', 'elektrisch': 'red'}
        filtered_hist_data = data_cars[(data_cars['brandstof'].isin(color_map.keys())) &
                                       (data_cars['datum_eerste_toelating'] >= selected_date[0]) &
                                       (data_cars['datum_eerste_toelating'] <= selected_date[1])]

        fig_hist = px.histogram(
            filtered_hist_data,
            x="brandstof",
            title="Histogram of Fueltypes in Cars",
            color='brandstof',
            color_discrete_map=color_map,
            category_orders={'brandstof': list(color_map.keys())},
            text_auto=True
        )

        fig_hist.update_layout(bargap=0.2)
        max_count = data_cars['brandstof'].value_counts().max()
        fig_hist.update_yaxes(range=[0, max_count])

        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(fig_line)
        with col2:
            st.plotly_chart(fig_hist)

    # 🔹 Call function so graphs show in tab1
    auto_per_maand()

with tab3:
    m = folium.Map(location=[52.1, 5.3], zoom_start=8)
    marker_cluster = MarkerCluster().add_to(m)
    for _, row in Laadpalen1.iterrows():
        folium.Marker(
            location=[row["AddressInfo.Latitude"], row["AddressInfo.Longitude"]],
            popup=row["AddressInfo.Title"] if "AddressInfo.Title" in row else "Charging Station"
        ).add_to(marker_cluster)

    # render map
    st_folium(m, width=800, height=600)

















