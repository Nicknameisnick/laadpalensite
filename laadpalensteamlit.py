import requests
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import numpy as np
import geopandas as gpd

st.set_page_config(page_title="Laadpalen en Elektrisch vervoer", layout="wide")

#Api Reader
response = requests.get("https://api.openchargemap.io/v3/poi/?output=json&countrycode=NL&maxresults=100&compact=true&verbose=false&key=2960318e-86ae-49e0-82b1-3c8bc6790b41")
responsejson  = response.json()
Laadpalen = pd.json_normalize(responsejson)
df4 = pd.json_normalize(Laadpalen.Connections)
df5 = pd.json_normalize(df4[0])
Laadpalen = pd.concat([Laadpalen, df5], axis=1)
columns_to_exclude=["Amps", "Voltage", "AddressInfo.StateOrProvince", "NumberOfPoints", "UsageCost", "UUID", "DataProviderID", "Reference", "Connections", "AddressInfo.DistanceUnit", "AddressInfo.AddressLine2", "AddressInfo.ContactTelephone1", "AddressInfo.RelatedURL", "DataProvidersReference", "IsRecentlyVerified", "DataQualityLevel", "AddressInfo.CountryID", "SubmissionStatusTypeID"]
Laadpalen1 = Laadpalen.drop(columns_to_exclude, axis=1)

st.sidebar.title("Controls")

year_range = st.sidebar.slider("Select Year Range", 2010, 2025, (2010, 2025)) #moet nog de juiste daterange worden

show_lines = st.sidebar.checkbox("Show Lines", value=True)
show_points = st.sidebar.checkbox("Show Points", value=True)

tab1, tab2, tab3 = st.tabs([ 
   "Voertuigverdeling over de tijd", 
   "Oplaad data",
   "Laadpalen map"
])












