import streamlit as st
import pandas as pd
from utils import load_data

# Header and description of the page
st.title("Line Chart Columns")
st.write("""This page displays the imported data from the NVE Magasinstatistikk API in a table format using LineChartColumn().
Use the slider to select a date range and use the radio buttons to select an area type. 
The default date range is january 1995 and the default area type is EL. 
Columns such as week number, year, capacity and next publishdate is not included as it is considered metadata.""")

# All months being put in to a list for use in the slider
all_months = list(pd.period_range(start="1995-01", end=pd.Timestamp.today(), freq="M"))

# Creating a slider based on the all_months list with the default value as Jan 1995
start, end = st.select_slider(
    "Select Date Range:",
    options=all_months,
    value=(all_months[0], all_months[0])
)

# Loading the data using the load_data function from utils.py
df, columns_to_plot, column_mapping = load_data(start,end)

# Creating the select boxes for area_type
selected_area_type = st.radio("Area Type:", options=["EL","NO","VASS"])

# Filtering the dataframe based on the selected area_type
df_filtered_type = df[df['area_type'] == selected_area_type]

# Description of what shows below
st.write("Tables for the different area numbers:")

# Looping through the area_nr for the schosen area_type
for area_nr in sorted(df_filtered_type['area_nr'].unique()):

    # Filtering the dataframe down to the data for the given area number the loop is going through
    df_single_area = df_filtered_type[df_filtered_type['area_nr'] == area_nr]

    # Creating a summary dataframe for each area nr used to create the table
    summary_df = pd.DataFrame([
        {'Column': column_mapping.get(col, col),
         'Selected period': df_single_area[col].to_list()}
        for col in columns_to_plot
    ])

    # Putting the different plots inside each own expander for better user experience
    with st.expander(f"Area {area_nr}", expanded=True):

        # Showing the dataframe using LineChartColumn, not displaying the dataframe-index.
        st.dataframe(
            summary_df,
            column_config={'Selected period': st.column_config.LineChartColumn('Selected period')},
            hide_index=True
        )