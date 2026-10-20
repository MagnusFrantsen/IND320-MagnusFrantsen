import streamlit as st
import pandas as pd
import requests

# Loading the data from the Magasinstatistikk API
@st.cache_data(ttl=("1d"))
def load_data(start, end):

    URL_MAGASIN = "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk/HentOffentligData"

    response = requests.get(URL_MAGASIN, timeout = 15)

    df = pd.DataFrame(response.json())  

    df.columns = ['Date', 'area_type','area_nr', 'iso_year', 'iso_week', 
              'res_level', 'capacity_TWh', 'res_level_TWh', 
              'next_publish_date', 'prev_res_level', 'change_res_level']

    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values(by=['Date'], ascending=True)
    # Creating a new column in the dataframe with the monts
    df = df[df['Date'].dt.to_period('M').between(start,end)]

    # Choosing these as the relevant columns to plot from the csv file and returning a list for use in the other files
    columns_to_plot = ['res_level', 'res_level_TWh', 'prev_res_level', 'change_res_level']

    # Creating a dictionary to create nicer titles and labels for axis in the plots
    column_mapping = {
        'res_level': "Reservoir Level (%)",
        'res_level_TWh': "Reservoir Level (TWh)",
        'prev_res_level': "Previous Reservoir Level (%)",
        'change_res_level': "Change in Reservoir Level (%)"
    }

    return df, columns_to_plot, column_mapping