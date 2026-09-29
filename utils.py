import streamlit as st
import pandas as pd
from pathlib import Path

@st.cache_data
def load_data():
    file_path = Path("D2Dbook/data/reservoirs.csv")
    
    if not file_path.exists():
        # Prøv en alternativ sti hvis mappen ligger direkte i roten
        file_path = Path("data/reservoirs.csv")

    df = pd.read_csv(file_path)

    df.columns = ['Date', 'area_type','area_nr', 'iso_year', 'iso_week', 
              'res_level', 'capacity_TWh', 'res_level_TWh', 
              'next_publish_date', 'prev_res_level', 'change_res_level']

    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values(by=['Date'], ascending=True)
    df.round(3)

    # Choosing these as the relevant columns to plot from the csv file and returning a list for use in the other files
    columns_to_plot = ['res_level', 'res_level_TWh', 'prev_res_level', 'change_res_level']

    return df, columns_to_plot