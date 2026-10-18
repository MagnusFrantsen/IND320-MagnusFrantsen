import streamlit as st
from utils import load_data
import pandas as pd
import matplotlib.pyplot as plt

# Title and short description of the page
st.title("Plots Page")
st.write("This page has a plot of the imported data, a drop-down menu and a slider for user input.")

st.set_page_config(layout="wide")
# Loading the data using the load_data function from utils.py
df, columns_to_plot, column_mapping = load_data()

# Chossing the area plotted as 'NO' for this case, it would not make sense to plot everything on
# top of each other as it seems like a total mess

area = st.radio("Select area type:",
    options = ["EL", "NO", "VASS"])

# Caching the filtering and choosing NO as area type to make the plotting make sense
@st.cache_data
def filter_by_area(df, area_type):
    return df[df['area_type'] == area_type]

df= filter_by_area(df,area)

# Creating a new column in the dataframe with the monts
df['Month'] = df['Date'].dt.to_period('M')

# Used this during development to check that the data was loaded correctly, and to see the first 5 rows of the dataframe
# st.write(df.head())

# Sorting months and making sure the values are unique as I do not want duplicated in the slider
months = sorted(df['Month'].unique())

# The first column contains a selectbox to choose desired columns to plot


selected_column = st.selectbox(
    "Select Column to Plot:", 
    options=list(column_mapping.keys()) + ['All'],
    format_func=lambda x: "All Columns" if x == 'All' else column_mapping[x])

    # The second column is a slider to choose the desired time interval for plotting 

selected_date_range = st.select_slider(
    "Select Date Range:", 
    options= sorted(df['Month'].unique()),
    value = (months[0], months[0])
)

# Defining the start and end of interval that should be plotted
start, end = selected_date_range

#Caching the data and filtering the dataframe by the months defined by the interval from the slider
@st.cache_data
def filter_by_month(df, start, end):
    interval = df['Month'].between(start, end)
    return df[interval]

# Creating a dataframe filtered by the interval defined earlier by calling for the filter_by_month function
df_filtered = filter_by_month(df, start, end)

# If 'All' is selected it should say "All columns" in the menu in the select box
if selected_column == 'All':
    nice_title = "All Columns"

# If something else than all is selected, the value from the given column-key is what should be the title of the plot
else:    
    nice_title = column_mapping[selected_column]

# Creating a figure with a subplot and defining the size
fig, ax1 = plt.subplots(figsize=(16,8))

# Plotting all columns if 'All is chosen
if selected_column == 'All':    

    # Loop going through every column
    for col in columns_to_plot:
        
        # PLotting every column except change, as it would not make sense to normalize this value and it should have a different scale on its axis
        if col != 'change_res_level':
            fig, ax = plt.subplots(figsize=(16,8))

            for area_nr, group in df_filtered.groupby('area_nr'):
                ax.plot(group['Date'], group[col], label=f"Area {area_nr}")
                ax.set_title(f"{nice_title} in Area Type {area}")

            # Creating the title of the plot
            ax.set_title(f"{column_mapping[col]} in area type {area}")
            ax.grid(True)
            ax.legend(loc='upper right')
            # Creating labels for the x- and y-axis
            ax.set_xlabel('Time')
            ax.set_ylabel(f"{column_mapping[col]}")
            st.pyplot(fig)

        # If the columns name is 'change_res_level' it is plotted with a different axis to make sure the variation in the values are actually shown
        if col == 'change_res_level':
            fig, ax = plt.subplots(figsize=(16,8))

            for area_nr, group in df_filtered.groupby('area_nr'):
                ax.plot(group['Date'], group['change_res_level'], label=f"Area {area_nr}")

            ax.legend(loc='upper right')
            ax.grid(True)
            ax.set_title(f"{column_mapping[col]} in area type {area}")
            ax.set_ylabel(column_mapping['change_res_level'], color='tab:red')
            ax.tick_params(axis='y', labelcolor='tab:red')
            st.pyplot(fig)

# Plotting the selected column when something else than 'All' is chosen
else:
    for area_nr, group in df_filtered.groupby('area_nr'):
        ax1.plot(group['Date'], group[selected_column], label=f"Area {area_nr}")
        ax1.set_title(f"{nice_title} in Area Type {area}")
        ax1.legend()
        ax1.grid()
    ax1.set_xlabel('Time')
    ax1.set_ylabel(column_mapping[selected_column])
    st.pyplot(fig)