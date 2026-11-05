import streamlit as st

# Creating the title and description for the whole Streamlit app, including buttons for navigation to different pages.
def home():
    st.title("Energy and Weather in Norway")
    st.write("""Explore Norwegian reservoir levels, cross-border electricity flows and
    weather data. Choose an area in the sidebar, and the analysis pages update to match.""")
    
    st.write("""You can navigate to the different pages using the buttons below, 
    or by using the top navigation bar.""")

    # Three equal columns with a bordered card for each topic
    col1, col2, col3 = st.columns(3)
    card_height = 220

    with col1.container(border=True, height=card_height):
        st.subheader("Reservoirs")
        st.write("Reservoir filling over time from NVE.")
        st.page_link("pages/plots.py", label="Reservoir plots",  icon=":material/arrow_forward:")
        st.page_link("pages/tables.py", label="Data tables",  icon=":material/arrow_forward:")

    with col2.container(border=True, height=card_height):
        st.subheader("Electricity")
        st.write("Flows to and from Norway from ENTSO-E.")
        st.page_link("pages/flows.py", label="Connection flows",  icon=":material/arrow_forward:")

    with col3.container(border=True, height=card_height):
        st.subheader("Analysis")
        st.write("Seasonal patterns, outliers and anomalies.")
        st.page_link("pages/stl_analysis.py", label="STL and spectrogram",  icon=":material/arrow_forward:")
        st.page_link("pages/outlier_and_anomaly.py", label="Outliers and anomalies",  icon=":material/arrow_forward:")

    # Names the data sources, so users know where the results come from
    st.caption("Data: NVE Magasinstatistikk, ENTSO-E Transparency Platform and Open-Meteo (ERA5).")

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
    "**Overview**": [st.Page(home, title="Home Page", default=True)],
    "**Reservoirs**": [
        st.Page("pages/plots.py", title="Reservoir Plots"),
        st.Page("pages/tables.py", title="Tables"),
    ],
    "**Electricity**": [st.Page("pages/flows.py", title="Connection Flows")],
    "**Analysis**": [
        st.Page("pages/stl_analysis.py", title="STL and Spectrogram"),
        st.Page("pages/outlier_and_anomaly.py", title="Outliers and Anomalies"),
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

# Running the selected page based on user navigation.
page = st.navigation(pages, position="top")
page.run()