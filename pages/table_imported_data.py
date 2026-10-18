import streamlit as st
import pandas as pd
from utils import load_data

st.title("Line Chart Columns")
st.write("This page displays the imported data in a table format using LineChartColumn().")

# Loading the data using the load_data function from utils.py
df, columns_to_plot, column_mapping = load_data()

# Creating the select boxes for area_type

selected_area_type = st.radio("Area Type:", options=["EL","NO","VASS"])

# Filtering the dataframe based on the selected area_type
df_filtered_type = df[df['area_type'] == selected_area_type]

# Creating a summary list to hold data of the first month
summary_data = []

# Looping through the columns of the filtered dataframe to find the values for a given area, 
# given that the columns contain numeric data types
for area_nr in sorted(df_filtered_type['area_nr'].unique()):
    df_single_area = df_filtered_type[df_filtered_type['area_nr'] == area_nr]

    # Finding the minimum date in the filtered dataframe
    min_date = df_single_area['Date'].min()

    first_month = df_single_area[
    (df_single_area['Date'] >= min_date) & 
    (df_single_area['Date'] < min_date + pd.DateOffset(months=1))
    ]
    
    row = {'Area_nr': area_nr, **{column_mapping.get(col, col): first_month[col].to_list() for col in columns_to_plot}}

    summary_data.append(row)

# Creating a summary dataframe
summary_df = pd.DataFrame(summary_data)

# Displaying the summary dataframe using LineChartColumn
st.dataframe(summary_df,
             column_config = {column_mapping.get(col, col): st.column_config.LineChartColumn(column_mapping.get(col, col)) for col in columns_to_plot},
             hide_index = True)