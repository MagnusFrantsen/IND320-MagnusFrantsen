import streamlit as st
from utils import load_data
import pandas as pd
import matplotlib.pyplot as plt

# Title and short description of the page
st.title("Plots Page")
st.write("This page has a plot of the imported data, a drop-down menu and a slider for user input.")

# Loading the data using the load_data function from utils.py
df = load_data()

area = 'NO'
# Caching the filtering and choosing NO as area type to make the plotting make sense
@st.cache_data
def filter_by_area(df, area_type):
    return df[df['area_type'] == area_type]

df = filter_by_area(df,area)

df['Month'] = df['Date'].dt.to_period('M')

columns_to_plot = ['res_level', 'res_level_TWh', 'last_res_level', 'change_res_level']

# Used this during development to check that the data was loaded correctly, and to see the first 5 rows of the dataframe
# st.write(df.head())

months = sorted(df['Month'].unique())

column_mapping = {
    'res_level': "Reservoir Level (%)",
    'res_level_TWh': "Reservoir Level (TWh)",
    'last_res_level': "Last Reservoir Level (%)",
    'change_res_level': "Change in Reservoir Level (%)"
}

col1, col2 = st.columns(2)

with col1:
    selected_column = st.selectbox(
        "Select Column to Plot:", 
        options=list(column_mapping.keys()),
        format_func=lambda x: column_mapping[x])
    
with col2:
    selected_date_range = st.select_slider(
        "Select Date Range:", 
        options= sorted(df['Month'].unique()),
        value = (months[0], months[0])
    )

# Defining the start and end of 
start, end = selected_date_range

@st.cache_data
def filter_by_month(df, start, end):
    interval = df['Month'].between(start, end)
    return df[interval]

df_filtered = filter_by_month(df, start, end)
nice_title = column_mapping[selected_column]

fig,ax = plt.subplots()
ax.plot(df_filtered['Date'], df_filtered[selected_column])
ax.set_title(f"{nice_title} in Area Type {area}")
ax.grid(True)

st.pyplot(fig)