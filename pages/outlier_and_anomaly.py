import streamlit as st
from requests.exceptions import RequestException
from utils import load_weather, lof_anomalies, spc_outliers, WEATHER_VARS, WEATHER_LABELS
import plotly.express as px

# Naming the page
st.title("Outlier and Anomaly Detection")

# Fetching the area type and area number chosen in the sidebar
area_type = st.session_state["area_type"]
area_nr = st.session_state["area_nr"]

# Selector for the weather property, used by both tabs. Temperature is first in the list, so it is the default.
# The key keeps the choice in session state when the user leaves the page and comes back.
prop = st.selectbox(
    "Weather property",
    options=WEATHER_VARS,
    format_func=lambda var: f"{WEATHER_LABELS[var][0]} ({WEATHER_LABELS[var][1]})",
    key="outlier_property",
    persist_state="session"
)
name, unit, decimals = WEATHER_LABELS[prop]
label = f"{name} ({unit})"

st.write(f"Hourly {name.lower()} in {area_type} {area_nr}, 2024. Points far from the normal seasonal pattern are marked.")

# If the selected area type is "NO", display an info message and stop the execution of the page.
# Weather data needs a specific area, because a national mean would average away regional outliers.
# The page therefore stops here when all of Norway (NO) is selected.
if area_type == "NO":
    st.info("Weather analysis needs a specific area. Select EL or VASS.")
    st.stop()

try:
    # Creating a spinner that is shown when load_weather is running
    with st.spinner("Loading weather data..."):
        weather = load_weather(area_type, area_nr, 2024)

# Creating an error message if the data cannot be downloaded
except RequestException as error:
    st.error(f"Could not download weather data: {error}")
    st.stop()

# Creating two tabs for Outlier/SPC analysis and Anomaly/LOF analysis, 
# with an option to rerun the page when switching tabs.
tab1, tab2 = st.tabs(["Outliers (SPC)", "Anomalies (LOF)"], on_change="rerun")

# Displaying the content for the first tab (Outlier/SPC analysis) if it is open.
if tab1.open:
    with tab1:
        with st.expander("Analysis settings"):
            cutoff_days = st.slider("Seasonal cutoff (days)", 7, 90, 30,
                        help="Variation slower than this counts as seasonal (DCT high-pass filter).")
            n_std = st.slider("Limit width (standard deviations)", 1.0, 6.0, 3.0, step=0.5)

        # Defining the figure and the summary by calling spc_outliers on the chosen property
        fig, summary = spc_outliers(weather[prop], cutoff_days, n_std, label=label,
                                    title=f"{name} outliers in {area_type} {area_nr}, 2024")

        # Displaying the interactive Plotly chart, themed by the app's config.toml
        st.plotly_chart(fig)

        # Creating the different columns
        col1, col2, col3 = st.columns(3)
        # Showing three key numbers side by side in the defined columns
        col1.metric("Outliers", summary["n_outliers"])
        col2.metric("High outliers", summary["n_high"])
        col3.metric("Low outliers", summary["n_low"])

# Displaying the content for the second tab (Anomaly/LOF analysis) if it is open.
if tab2.open:
    with tab2:
        # Slider for the share of points LOF should mark as anomalies: from 0.1 % to 10 %,
        proportion = st.slider("Proportion of anomalies", 0.001, 0.1, 0.01, step=0.001, format="%.3f")
        # Slider for how many nearby points each point is compared with (From 5 to 100, 20 as default).
        n_neighbors = st.slider("Number of neighbours", 5, 100, 20)

        # Defining the figure and summary by calling lof_anomalies on the chosen property
        fig, summary = lof_anomalies(weather[prop], proportion, n_neighbors, label=label,
                                     title=f"{name} anomalies in {area_type} {area_nr}, 2024 (Local Outlier Factor)")
        
        # Displaying the interactive Plotly chart, themed by the app's config.toml
        st.plotly_chart(fig)

        # Defining the columns
        col1, col2, col3 = st.columns(3)
        col1.metric("Anomalies", summary["n_anomalies"])
        # Lowest and highest anomaly, with the unit and decimals of the chosen property
        col2.metric(f"Lowest value ({unit})", f"{summary['value_min']:.{decimals}f}")
        col3.metric(f"Highest value ({unit})", f"{summary['value_max']:.{decimals}f}")

        # Making a table with one row per month (1–12) and the number of anomalies in each.
        # Months with no anomalies get 0, so all 12 months show in the bar chart.
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
        # Formatting the x-axis of the bar chart
        fig_months.update_xaxes(tickangle=0, dtick=1)
        
        # Displaying the bar chart of anomalies per month
        st.plotly_chart(fig_months)