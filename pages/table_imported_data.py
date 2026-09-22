import streamlit as st
import pandas as pd
from utils import load_data

st.title("Imported Data Table")
st.write("This page displays the imported data in a table format.")

# Loading the data using the load_data function from utils.py
df = load_data()

# 
df['Date'] = pd.to_datetime(df['Date'])

# Creating to columns for the select boxes
col1, col2 = st.columns(2)

# Creating the select boxes for area_type
with col1:
    selected_area_type = st.selectbox("Select Area Type:", df['area_type'].unique())

# Filtering the dataframe based on the selected area_type
df_filtered_type = df[df['area_type'] == selected_area_type]

# Creating the select box for area_nr based on the filtered dataframe
with col2:
    selected_area_nr = st.selectbox("Select Area Number:", sorted(df_filtered_type['area_nr'].unique()))

# Filtering the dataframe based on the selected area_nr
df_single_area = df_filtered_type[df_filtered_type['area_nr'] == selected_area_nr]

# Finding the minimum date in the filtered dataframe
min_date = df_single_area['Date'].min()

# Selecting the first month of data (january 1995)
first_month = df_single_area[
    (df_single_area['Date'] >= min_date) & 
    (df_single_area['Date'] < min_date + pd.DateOffset(months=1))
]

# Creating a summary list to hold data of the first month
summary_data = []

# Looping through the columns of the filtered dataframe to find the values for a given area
for col in df_single_area.columns:
    if pd.api.types.is_numeric_dtype(df_single_area[col]):
        summary_data.append({
            'Column': col,
            'first_month_trend': first_month[col].to_list()
        })

# Creating a summary dataframe
summary_df = pd.DataFrame(summary_data)

# Displaying the summary dataframe using LineChartColumn hiding the index from the csv file
st.dataframe(summary_df,
             column_config={'first_month_trend': st.column_config.LineChartColumn('First month')},
             hide_index=True)

