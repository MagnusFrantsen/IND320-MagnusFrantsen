import streamlit as st
from utils import load_data
import pandas as pd
import matplotlib.pyplot as plt

# Title and short description of the page
st.title("Plots Page")
st.write("This page has a plot of the imported data from NVE Magasinstatistikk API, a drop-down menu, radio buttons and a slider for user input.")

# Creating a list of all months available as options in the slider
all_months = list(pd.period_range(start="1995-01", end=pd.Timestamp.today(), freq="M"))

# Returning start, end variables used as input to determine the download interval in load_data()
start, end = st.select_slider(
    "Select Date Range:",
    options=all_months,
    value=(all_months[0], all_months[1])
)

# Loading the data and defining the variables returned from the load_data() function in utils.py
df, columns_to_plot, column_mapping = load_data(start, end)

# Selectbox to choose which column to plot
selected_column = st.selectbox(
    "Select Column to Plot:", 
    options=list(column_mapping.keys()) + ['All'],
    format_func=lambda x: "All Columns" if x == 'All' else column_mapping[x])

# Radio buttons to select area type
area = st.radio("Select area type:",
    options = ["EL", "NO", "VASS"])

# Caching the filtering and choosing NO as area type to make the plotting make sense
df = df[df['area_type'] == area]

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

        fig, ax = plt.subplots(figsize=(16, 8))

        # Looping through the area numbers for the chosen area type
        for area_nr, group in df.groupby('area_nr'):
            ax.plot(group['Date'], group[col], label=f"Area {area_nr}")

        # Defining the name of the plot
        ax.set_title(f"{column_mapping[col]} in area type {area}")

        # Naming the axes
        ax.set_xlabel('Time')
        ax.set_ylabel(column_mapping[col])

        # Turning on a grid
        ax.grid(True)

        # Setting the location of the legends to the upper right section
        ax.legend(loc='upper right')

        # Displaying the plot in the Streamlit APp
        st.pyplot(fig)

# Plotting the selected column when one column is chosen
else:
    # Looping through each area number for the chosen area type
    for area_nr, group in df.groupby('area_nr'):

        # Creating the plot for the given area number
        ax1.plot(group['Date'], group[selected_column], label=f"Area {area_nr}")

        # Defining the title of the plot 
        ax1.set_title(f"{nice_title} in Area Type {area}")

        # Creating a legend
        ax1.legend()
        # Turning on a grid in the plot
        ax1.grid(True)

    # Creating labels for the x- and y-axes
    ax1.set_xlabel('Time')
    ax1.set_ylabel(column_mapping[selected_column])

    # Displaying the figure in the Streamlit App
    st.pyplot(fig)