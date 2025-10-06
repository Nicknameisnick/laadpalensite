import requests
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import numpy as np

st.set_page_config(page_title="Laadpalen en Elektrisch vervoer", layout="wide")

response = requests.get("https://api.openchargemap.io/v3/poi/?output=json&countrycode=NL&maxresults=100&compact=true&verbose=false&key=2960318e-86ae-49e0-82b1-3c8bc6790b41")
responsejson  = response.json()

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


with tab2:


with tab3:






