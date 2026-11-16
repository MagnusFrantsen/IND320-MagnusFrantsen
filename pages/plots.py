import streamlit as st
import pandas as pd
import plotly.express as px
from utils import load_data, AREA_COLORS

# Title and short description of the page
st.title("Reservoirs")
st.write("""Reservoir filling from the NVE Magasinstatistikk API. Choose a period with the slider;
the area type is selected in the sidebar. The Plots tab shows the development over time,
and the Table tab shows each area as small line charts.""")

# Creating a list of all months available as options in the slider
all_months = list(pd.period_range(start="1995-01", end=pd.Timestamp.today(), freq="M"))

# Shared slider for both tabs: start and end determine the download interval in load_data()
start, end = st.select_slider(
    "Select Date Range:",
    options=all_months,
    value=(all_months[0], all_months[1])
)

# Loading the data and defining the variables returned from the load_data() function in utils.py
df, columns_to_plot, column_mapping = load_data(start, end)

# Using the global area type selected in the sidebar, and keeping only those rows
area = st.session_state["area_type"]
df = df[df["area_type"] == area]

def reservoir_chart(data, column, area):
    """Return a Plotly line chart of one reservoir column, with one line per area number."""
    # Area names as text, so each area number gets its own colour and legend entry
    plot_df = data.assign(Area="Area " + data["area_nr"].astype(str))
    fig = px.line(
        plot_df, x="Date", y=column, color="Area",
        color_discrete_sequence=AREA_COLORS,
        labels={column: column_mapping[column], "Date": "Time"},
        title=f"{column_mapping[column]} in area type {area}",
    )
    # One hover box listing all areas for the date under the cursor
    fig.update_layout(hovermode="x unified", legend_title_text="")
    return fig

# Two views of the same data: interactive charts and a compact table
tab_plots, tab_table = st.tabs(["Plots", "Table"])

with tab_plots:
    # Selectbox to choose which column to plot (only used in this tab)
    selected_column = st.selectbox(
        "Select Column to Plot:",
        options=list(column_mapping.keys()) + ["All"],
        format_func=lambda x: "All Columns" if x == "All" else column_mapping[x])

    # Plotting every column below each other when 'All' is chosen, otherwise only the chosen column
    columns = columns_to_plot if selected_column == "All" else [selected_column]
    for col in columns:
        # st.plotly_chart applies the app theme from config.toml to the chart
        st.plotly_chart(reservoir_chart(df, col, area))

with tab_table:
    st.write("""One table per area number. Week number, year, capacity and next publish date
    are left out, since they are metadata.""")

    # Looping through the area numbers for the chosen area type
    for area_nr in sorted(df["area_nr"].unique()):

        # Keeping only the rows for the area number the loop is going through
        df_single_area = df[df["area_nr"] == area_nr]

        # One row per column, holding all its values in the period, which LineChartColumn draws as a small chart
        summary_df = pd.DataFrame([
            {"Column": column_mapping.get(col, col),
             "Selected period": df_single_area[col].to_list()}
            for col in columns_to_plot
        ])

        # Each area in its own expander, without the dataframe index
        with st.expander(f"Area {area_nr}", expanded=True):
            st.dataframe(
                summary_df,
                column_config={"Selected period": st.column_config.LineChartColumn("Selected period")},
                hide_index=True
            )