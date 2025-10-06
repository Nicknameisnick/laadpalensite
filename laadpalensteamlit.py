import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Laadpalen en Elektrisch vervoer", layout="wide")

# -------------------------------
# Sidebar Controls
# -------------------------------
st.sidebar.title("Controls")
year_range = st.sidebar.slider("Select Year Range", 2010, 2025, (2010, 2025))
show_lines = st.sidebar.checkbox("Show Lines", value=True)
show_points = st.sidebar.checkbox("Show Points", value=True)

# -------------------------------
# Functions
# -------------------------------
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
        return 'benzine'

def auto_per_maand(data_cars):
    # Datum omzetten naar datetime
    data_cars['datum_eerste_toelating'] = pd.to_datetime(
        data_cars['datum_eerste_toelating'], format='%Y%m%d', errors='coerce'
    )

    # Groeperen en cumulatief aantal bepalen
    grouped_data = data_cars.groupby(['datum_eerste_toelating', 'brandstof']).size().unstack(fill_value=0)
    grouped_data = grouped_data.reset_index()

    if 'elektrisch' in grouped_data and 'benzine' in grouped_data:
        grouped_data[['elektrisch', 'benzine']] = grouped_data[['elektrisch', 'benzine']].cumsum()

    melted_data = grouped_data.melt(id_vars='datum_eerste_toelating', var_name='brandstof', value_name='aantal_autos')

    # Slider voor periode
    min_date = melted_data['datum_eerste_toelating'].min().to_pydatetime()
    max_date = melted_data['datum_eerste_toelating'].max().to_pydatetime()

    selected_date = st.slider(
        "Selecteer een periode",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="YYYY-MM"
    )

    # Filteren op slider
    filtered_data = melted_data[(melted_data['datum_eerste_toelating'] >= selected_date[0]) &
                                (melted_data['datum_eerste_toelating'] <= selected_date[1])]

    # Lijngrafiek
    fig_line = px.line(
        filtered_data,
        x='datum_eerste_toelating',
        y='aantal_autos',
        color='brandstof',
        color_discrete_map={'benzine': 'blue', 'elektrisch': 'red'},
        labels={'aantal_autos': 'Aantal auto\'s', 'datum_eerste_toelating': 'Datum eerste toelating'},
        title=f'Cumulatief aantal auto\'s per brandstofsoort van {selected_date[0].strftime("%Y-%m")} tot {selected_date[1].strftime("%Y-%m")}'
    )

    # Histogram
    color_map = {'benzine': 'blue', 'elektrisch': 'red'}
    filtered_hist_data = data_cars[(data_cars['brandstof'].isin(color_map.keys())) &
                                   (data_cars['datum_eerste_toelating'] >= selected_date[0]) &
                                   (data_cars['datum_eerste_toelating'] <= selected_date[1])]

    fig_hist = px.histogram(
        filtered_hist_data,
        x="brandstof",
        title="Histogram brandstofsoorten",
        color='brandstof',
        color_discrete_map=color_map,
        category_orders={'brandstof': list(color_map.keys())},
        text_auto=True
    )

    fig_hist.update_layout(bargap=0.2)
    max_count = data_cars['brandstof'].value_counts().max()
    fig_hist.update_yaxes(range=[0, max_count])

    # Twee kolommen met de grafieken
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig_line, use_container_width=True)
    with col2:
        st.plotly_chart(fig_hist, use_container_width=True)

# -------------------------------
# Tabs
# -------------------------------
tab1, tab2 = st.tabs([ 
   "Voertuigverdeling over de tijd", 
   "Oplaad data"
])

# Tab 1: Voertuigverdeling
with tab1:
    data_cars = pd.read_pickle('cars.pkl')
    data_cars['brandstof'] = data_cars['handelsbenaming'].apply(bepaal_brandstof)
    auto_per_maand(data_cars)

# Tab 2: placeholder
with tab2:
    st.write("Hier komt later oplaad data 📊")
