import streamlit as st
from requests.exceptions import RequestException
from utils import load_weather, lof_anomalies, spc_outliers
import plotly.express as px

st.title("Outlier and Anomaly Detection")
st.write("This is a simple Outlier and Anomaly Detection page.")

area_type = st.session_state["area_type"]
area_nr = st.session_state["area_nr"]

# If the selected area type is "NO", display an info message and stop the execution of the page.
# Weather data needs a specific area, because a national mean would average away regional outliers.
# The page therefore stops here when all of Norway (NO) is selected.
if area_type == "NO":
    st.info("Weather analysis needs a specific area. Select EL or VASS.")
    st.stop()

try:
    with st.spinner("Loading weather data..."):
        weather = load_weather(area_type, area_nr, 2024)
except RequestException as error:
    st.error(f"Could not download weather data: {error}")
    st.stop()

# Creating two tabs for Outlier/SPC analysis and Anomaly/LOF analysis, 
# with an option to rerun the page when switching tabs.
tab1, tab2 = st.tabs(["Outlier/SPC analysis", "Anomaly/LOF Analysis"], on_change="rerun")

# Displaying the content for the first tab (Outlier/SPC analysis) if it is open.
if tab1.open:
    with tab1:
        with st.expander("Analysis settings"):
            cutoff_days = st.slider("DCT cutoff (days)", 7, 90, 30)
            n_std = st.slider("Number of standard deviations", 1.0, 6.0, 3.0, step=0.5)

        fig, summary = spc_outliers(weather["temperature_2m"], cutoff_days, n_std)
        st.pyplot(fig)

        col1, col2, col3 = st.columns(3)
        col1.metric("Outliers", summary["n_outliers"])
        col2.metric("High", summary["n_high"])
        col3.metric("Low", summary["n_low"])

# Displaying the content for the second tab (Anomaly/LOF analysis) if it is open.
if tab2.open:
    with tab2:
        proportion = st.slider("Proportion of anomalies", 0.001, 0.1, 0.01, step=0.001, format="%.3f")
        n_neighbors = st.slider("Number of neighbours", 5, 100, 20)

        fig, summary = lof_anomalies(weather["temperature_2m"], proportion, n_neighbors)
        st.pyplot(fig)

        col1, col2, col3 = st.columns(3)
        col1.metric("Anomalies", summary["n_anomalies"])
        col2.metric("Lowest value (°C)", f"{summary['value_min']:.1f}")
        col3.metric("Highest value (°C)", f"{summary['value_max']:.1f}")
        # Includes all 12 months, so months without anomalies show as zero
        months = (
            summary["anomalies_per_month"]
            .reindex(range(1, 13), fill_value=0)
            .rename_axis("month")
            .reset_index(name="anomalies")
        )

        # Plotly bar chart with one horizontal label per month
        fig_months = px.bar(
            months,
            x="month",
            y="anomalies",
            labels={"month": "Month", "anomalies": "Number of anomalies"},
        )
        fig_months.update_xaxes(tickangle=0, dtick=1)
        st.plotly_chart(fig_months)