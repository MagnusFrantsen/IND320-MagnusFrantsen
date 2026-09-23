import streamlit as st
from utils import load_data
import pandas as pd
import matplotlib.pyplot as plt

# Title and short description of the page
st.title("Plots Page")
st.write("This page has a plot of the imported data, a drop-down menu and a slider for user input.")

# Loading the data using the load_data function from utils.py
df = load_data()

# Chossing the area plotted as 'NO' for this case, it would not make sense to plot everything on
# top of each other as it seems like a total mess
area = 'NO'

# Caching the filtering and choosing NO as area type to make the plotting make sense
@st.cache_data
def filter_by_area(df, area_type):
    return df[df['area_type'] == area_type]

df = filter_by_area(df,area)

df['Month'] = df['Date'].dt.to_period('M')

# Choosing these as the relevant columns to plot from the csv file
columns_to_plot = ['res_level', 'res_level_TWh', 'prev_res_level', 'change_res_level']

# Used this during development to check that the data was loaded correctly, and to see the first 5 rows of the dataframe
# st.write(df.head())

# Sorting months and making sure the values are unique as I do not want duplicated in the slider
months = sorted(df['Month'].unique())

# Creating a dictionary to create nicer titles and labels for axis in the plots
column_mapping = {
    'res_level': "Reservoir Level (%)",
    'res_level_TWh': "Reservoir Level (TWh)",
    'prev_res_level': "Previous Reservoir Level (%)",
    'change_res_level': "Change in Reservoir Level (%)"
}

# Creating to columns
col1, col2 = st.columns(2)

# The first column contains a selectbox to choose desired columns to plot
with col1:
    selected_column = st.selectbox(
        "Select Column to Plot:", 
        options=list(column_mapping.keys()) + ['All'],
        format_func=lambda x: "All Columns" if x == 'All' else column_mapping[x])

# The second column is a slider to choose the desired time interval for plotting 
with col2:
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
fig, ax1 = plt.subplots(figsize=(10,5))

# Plotting all columns if 'All is chosen
if selected_column == 'All':
    # Loop going through every column
    for col in columns_to_plot:
        # PLotting every column except change, as it would not make sense to normalize this value and it should have a different scale on its axis
        if col != 'change_res_level':

            # Normalizing the values of Reservoir levels (% and TWh) and change in reservoir levels
            normalized = (df_filtered[col] - df_filtered[col].min()) / (df_filtered[col].max() - df_filtered[col].min())

            # Plotting the desired x- and y-values with a label given by the dictionary defined earlier (used for legend)
            ax1.plot(df_filtered['Date'], normalized, label=column_mapping[col])

            # Creating the title of the plot
            ax1.set_title("Normalized Values (0-1) of Reservoir Levels (% and TWh) and Change in Reservoir Levels (%)")

            # Creating labels for the x- and y-axis
            ax1.set_xlabel('Time')
            ax1.set_ylabel('Normalized Values (0-1)')

        # If the columns name is 'change_res_level' it is plotted with a different axis to make sure the variation in the values are actually shown
        if col == 'change_res_level':
            ax2 = ax1.twinx()
            ax2.plot(df_filtered['Date'], df_filtered['change_res_level'], color='tab:red', label=column_mapping['change_res_level'])
            ax2.set_ylabel(column_mapping['change_res_level'], color='tab:red')
            ax2.tick_params(axis='y', labelcolor='tab:red')

    # Collecting the legends in a common box regardless of subplot
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2)

# Plotting the selected column when something else than 'All' is chosen
else:
    ax1.plot(df_filtered['Date'], df_filtered[selected_column], label = nice_title)
    ax1.set_title(f"{nice_title} in Area Type {area}")
    ax1.legend()
    ax1.set_xlabel('Time')
    ax1.set_ylabel(column_mapping[selected_column])

# Adding a grid system to the plot
ax1.grid(True)

# Displaying the figure in the Streamlit App
st.pyplot(fig)