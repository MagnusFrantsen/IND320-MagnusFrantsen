import streamlit as st

# Creating the title and description for the whole Streamlit app, including buttons for navigation to different pages.
def home():
    st.title("IND320 Streamlit app")
    st.write("""In this Streamlit-app, you can visualize water reservoir data from NVE Magasinstatistikk API 
    and Cross-border electricity flow data from ENTSO-E Transparency Platform API.""")

    col1 ,col2, col3, col4, col5 = st.columns(5)

    with col1:
        if st.button("Go to Plots Page"):
            st.switch_page("pages/plots.py")
    with col2:
        if st.button("Go to Imported Data Table"):
            st.switch_page("pages/tables.py")
    with col3:
        if st.button("Flows"):
            st.switch_page("pages/flows.py")
    with col4:
        if st.button("STL Analysis"):
            st.switch_page("pages/stl_analysis.py")
    with col5:
        if st.button("Outlier and Anomaly Detection"):
            st.switch_page("pages/outlier_and_anomaly.py")

# Creating the navigation section with link to different pages in the Streamlit app.
pages = {"**Navigate to a page here:**":[
    st.Page(home, title="Home Page",default=True),
    st.Page("pages/plots.py", title="Reservoir Plots"),
    st.Page("pages/tables.py", title="Tables"),
    st.Page("pages/flows.py",title = "Connection Flows"),
    st.Page("pages/stl_analysis.py", title="STL Analysis"),
    st.Page("pages/outlier_and_anomaly.py", title="Outlier and Anomaly Detection"),
]
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
area_type =st.sidebar.radio("Area Type", ["NO", "EL", "VASS"], key="area_type")
area_nr = st.sidebar.selectbox("Area Number", area_numbers[area_type], key="area_nr")

# Creating a sidebar radio button for selecting the temperature unit (Celsius or Fahrenheit) 
# with a unique key for state management.
st.sidebar.radio("Temperature unit", ["Celsius", "Fahrenheit"], key="unit")

# Running the selected page based on user navigation.
page = st.navigation(pages)
page.run()