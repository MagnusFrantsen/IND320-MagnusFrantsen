import streamlit as st
from utils import load_data
import pandas as pd
import matplotlib.pyplot as plt

# Title and short description of the page
st.title("Plots Page")
st.write("This page has a plot of the imported data, a drop-down menu and a slider for user input.")

# Loading the data using the load_data function from utils.py
df = load_data()

col1, col2 = st.columns(2)

df = df[df['area_type'] == 'NO']
df = df.round(2)

df['Month'] = df['Date'].dt.to_period('M')

columns_to_plot = ['res_level', 'res_level_TWh', 'last_res_level', 'change_res_level']

# Used this during development to check that the data was loaded correctly, and to see the first 5 rows of the dataframe
# st.write(df.head())

months = sorted(df['Month'].unique())
with col1:
    selected_column = st.selectbox("Select Column to Plot:", columns_to_plot)

with col2:
    selected_date_range = st.select_slider(
        "Select Date Range:", 
        options= sorted(df['Month'].unique()),
        value = (months[0], months[0])
    )

start, end = selected_date_range

df_filtered_columns = df['Month'].between(start, end)
df_filtered = df[df_filtered_columns]

fig,ax = plt.subplots()
ax.plot(df_filtered['Date'], df_filtered[selected_column])

st.pyplot(fig)