"Laadpalen map"
])
with tab1:
   data_cars = pd.read_pickle('cars.pkl')
data_cars.head()


# In[66]:


data_cars.isna().sum()


# In[67]:


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
        return 'benzine'  # Default voor auto's die geen andere trefwoorden bevatten

# Pas de functie toe om de brandstofsoort te bepalen
data_cars['brandstof'] = data_cars['handelsbenaming'].apply(bepaal_brandstof)

# Bekijk de eerste paar rijen met de nieuwe 'brandstof' kolom
data_cars[['handelsbenaming', 'brandstof']].head()


# In[68]:


def auto_per_maand():
    # Ensure the 'datum_eerste_toelating' column is in datetime format
    data_cars['datum_eerste_toelating'] = pd.to_datetime(data_cars['datum_eerste_toelating'], format='%Y%m%d', errors='coerce')

    # Group the data by 'datum_eerste_toelating' and 'brandstof', and count the number of cars per group
    grouped_data = data_cars.groupby(['datum_eerste_toelating', 'brandstof']).size().unstack(fill_value=0)

    # Reset the index to use the data for Plotly
    grouped_data = grouped_data.reset_index()

    # Calculate the cumulative sum for each fuel type
    grouped_data[['elektrisch', 'benzine']] = grouped_data[['elektrisch', 'benzine']].cumsum()

    # Melt the data to long-form format suitable for Plotly
    melted_data = grouped_data.melt(id_vars='datum_eerste_toelating', var_name='brandstof', value_name='aantal_autos')

    # Add a slider to select the month
    min_date = melted_data['datum_eerste_toelating'].min().to_pydatetime()  # Convert to datetime
    max_date = melted_data['datum_eerste_toelating'].max().to_pydatetime()  # Convert to datetime

    # Slider for month selection
    selected_date = st.slider(
        "Selecteer een maand",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="YYYY-MM"
    )

    # Filter the data based on the selected month
    filtered_data = melted_data[(melted_data['datum_eerste_toelating'] >= selected_date[0]) & 
                                (melted_data['datum_eerste_toelating'] <= selected_date[1])]

    # Create a line plot with separate lines for 'elektrisch' and 'benzine'
    fig_line = px.line(filtered_data, 
                        x='datum_eerste_toelating', 
                        y='aantal_autos', 
                        color='brandstof',
                        color_discrete_map={'benzine': 'blue', 'elektrisch': 'red'},
                        labels={'aantal_autos': 'Aantal auto\'s', 'datum_eerste_toelating': 'Datum eerste toelating'}, 
                        title=f'Cumulatief aantal auto\'s per brandstofsoort van {selected_date[0].strftime("%Y-%m")} tot {selected_date[1].strftime("%Y-%m")}'
    )

    # Create a histogram of fuel types
    color_map = {
        'benzine': 'blue',
        'elektrisch': 'red'
    }

    # Update filtered_data for histogram to only include relevant fuel types
    filtered_hist_data = data_cars[(data_cars['brandstof'].isin(color_map.keys())) & 
                                    (data_cars['datum_eerste_toelating'] >= selected_date[0]) & 
                                    (data_cars['datum_eerste_toelating'] <= selected_date[1])]

    # Create the histogram
    fig_hist = px.histogram(filtered_hist_data, 
                             x="brandstof", 
                             title="Histogram of Fueltypes in Cars", 
                             color='brandstof',  # Set color based on fuel type
                             color_discrete_map=color_map,
                             category_orders={'brandstof': list(color_map.keys())},  # Ensure specific order
                             text_auto=True)  # Optional: to display counts on bars

    # Update layout for better appearance
    fig_hist.update_layout(bargap=0.2)  # Optional: Adjust gap between bars

    # You can set a specific range or derive it from the original data
    max_count = data_cars['brandstof'].value_counts().max()  # Get the max count for y-axis scaling
    fig_hist.update_yaxes(range=[0, max_count])  # Set y-axis limits

    # Create two columns to display plots side by side
    col1, col2 = st.columns(2)

    # Display the line plot in the first column
    with col1:
        st.plotly_chart(fig_line)  # Show the Plotly line chart in Streamlit

    # Display the histogram in the second column
    with col2:
        st.plotly_chart(fig_hist)  # Show the histogram in Streamlit



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
@@ -188,3 +152,4 @@ def auto_per_maand():



