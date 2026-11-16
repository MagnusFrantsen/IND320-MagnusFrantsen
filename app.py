import streamlit as st
import pandas as pd
from requests.exceptions import RequestException
from utils import (area_map, area_name, area_from_name, filling_for_month, weather_for_month,
                   WEATHER_VARS, WEATHER_LABELS, SUM_VARS)

def on_map_click():
    """Store the clicked area as the selected area, so the sidebar and all pages use it.

    Runs before the page is redrawn, which is what allows it to change the sidebar's selection.
    """
    points = st.session_state["map"]["selection"]["points"]
    if points:
        st.session_state["area_type"], st.session_state["area_nr"] = area_from_name(points[0]["location"])

# Creating the title and description for the whole Streamlit app, including buttons for navigation to different pages.
def home():
    st.title("Energy and Weather in Norway")
    st.write("""Explore Norwegian reservoir levels, cross-border electricity flows and
    weather data. Choose an area in the sidebar, and the analysis pages update to match.""")
    
    st.write("""You can navigate to the different pages using the buttons below, 
    or by using the top navigation bar.""")

        # The area type and area chosen in the sidebar (or by clicking the map)
    area_type = st.session_state["area_type"]
    area_nr = st.session_state["area_nr"]

    # What to colour the areas by, and which month; both are kept when visiting other pages
    col_colour, col_month = st.columns(2)
    colour_by = col_colour.selectbox(
        "Colour areas by", ["filling"] + WEATHER_VARS,
        format_func=lambda v: "Reservoir filling" if v == "filling" else WEATHER_LABELS[v][0],
        key="map_colour", persist_state="session")
    months = list(pd.period_range("1995-01", pd.Timestamp.today().to_period("M") - 1, freq="M"))
    month = col_month.select_slider("Month", options=months, value=months[-1],
                                    key="map_month", persist_state="session")

    # The value per area: reservoir filling in the last week of the month, or the month's weather
    values, range_color = pd.Series(dtype=float), None
    if colour_by == "filling":
        values, label, range_color = filling_for_month(area_type, month), "Reservoir filling (%)", (0, 100)
    else:
        name, unit, _ = WEATHER_LABELS[colour_by]
        label = f"{name}, monthly {'total' if colour_by in SUM_VARS else 'mean'} ({unit})"
        try:
            values = weather_for_month(area_type, month)[colour_by]
        except RequestException as error:
            st.warning(f"Could not download weather data, so the areas are not coloured: {error}")

    # The map; clicking an area calls on_map_click, which selects that area for all pages
    fig = area_map(area_type, values, area_name(area_type, area_nr), label, range_color)
    st.plotly_chart(fig, key="map", on_select=on_map_click, selection_mode="points")
    st.caption(f"Selected area: {area_name(area_type, area_nr)}. Click another area to change it; "
               "the area type is chosen in the sidebar.")

    # Three equal columns with a bordered card for each topic
    col1, col2, col3 = st.columns(3)
    card_height = 310

    with col1.container(border=True, height=card_height):
        st.subheader("Explore")
        st.write("Reservoir filling from NVE and electricity flows from ENTSO-E.")
        st.page_link("pages/plots.py", label="Reservoirs", icon=":material/arrow_forward:")
        st.page_link("pages/flows.py", label="Connection flows", icon=":material/arrow_forward:")

    with col2.container(border=True, height=card_height):
        st.subheader("Analyze")
        st.write("Seasonal patterns, weather outliers and anomalies, and how weather relates to reservoir filling.")
        st.page_link("pages/stl_analysis.py", label="STL and spectrogram", icon=":material/arrow_forward:")
        st.page_link("pages/outlier_and_anomaly.py", label="Outliers and anomalies", icon=":material/arrow_forward:")
        st.page_link("pages/correlation.py", label="Correlation", icon=":material/arrow_forward:")

    with col3.container(border=True, height=card_height):
        st.subheader("Forecast")
        st.write("Forecast of reservoir filling for the coming months.")
        st.page_link("pages/reservoir_forecast.py", label="Reservoir forecast", icon=":material/arrow_forward:")

    # Names the data sources, so users know where the results come from
    st.caption("Data: NVE Magasinstatistikk, ENTSO-E Transparency Platform, Open-Meteo (ERA5) and Norges Bank.")

# Adds a thin line under the top navigation bar
st.markdown(
    """
    <style>
    [data-testid="stHeader"] {
        border-bottom: 1px solid #d9d9d9;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
pages = {
    "": [st.Page(home, title="Home", default=True)],
    "**Explore**": [
        st.Page("pages/plots.py", title="Reservoirs"),
        st.Page("pages/flows.py", title="Connection Flows")
    ],
    "**Analyze**": [
        st.Page("pages/stl_analysis.py", title="STL and Spectrogram"),
        st.Page("pages/outlier_and_anomaly.py", title="Outliers and Anomalies"),
        st.Page("pages/correlation.py", title="Correlation")
    ],
    "**Forecast**": [
        st.Page("pages/reservoir_forecast.py", title = "Reservoir Forecast")
    ],
}

# Formatting the navigation section header with custom CSS to increase font size and weight.
st.markdown(
    """
    <style>
    [data-testid="stNavSectionHeader"] {
        font-size: 1.25rem;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

area_numbers = {
    "NO": [0],
    "EL": [1, 2, 3, 4, 5],
    "VASS": [1, 2, 3]
}
# Creating a sidebar radio button for selecting the area type (NO, EL, VASS) with a unique key for state management.
with st.sidebar.expander("Select area", expanded=True):
    area_type = st.radio("Area Type", list(area_numbers), index=1, key="area_type")
    area_nr = st.selectbox("Area Number", area_numbers[area_type], key="area_nr")

# Running the selected page, with a spinner shown until the page has finished loading
page = st.navigation(pages, position="top")
with st.spinner("Loading page..."):
    page.run()
