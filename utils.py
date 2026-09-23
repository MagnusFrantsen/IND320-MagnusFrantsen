import streamlit as st
import pandas as pd

@st.cache_data
def load_data():

    df = pd.read_csv("D2Dbook/data/reservoirs.csv")
    df.columns = ['Date', 'area_type','area_nr', 'iso_year', 'iso_week', 
              'res_level', 'capacity_TWh', 'res_level_TWh', 
              'next_publish_date', 'last_res_level', 'change_res_level']

    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values(by=['Date'], ascending=True)
    df.round(3)

    return df


