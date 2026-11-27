import streamlit as st
import pandas as pd
from requests.exceptions import RequestException
from utils import (load_data, load_weather_period, sliding_window_correlation, plot_swc,
                   area_name, WEATHER_VARS, WEATHER_LABELS, SUM_VARS)

st.title("Sliding Window Correlation")
st.write("""How strongly a weather property is related to the reservoir in the selected area, and how
that relation changes over time. Shift the weather back with the lag to look for delayed effects,
such as snow that melts into the reservoirs months later.""")

# The area chosen in the sidebar or on the map
area_type = st.session_state["area_type"]
area_nr = st.session_state["area_nr"]

# Weather needs a specific area: a national mean would hide the regional differences
if area_type == "NO":
    st.info("Weather analysis needs a specific area. Select EL or VASS.")
    st.stop()

# Controls: what to compare, and how
col1, col2 = st.columns(2)
prop = col1.selectbox(
    "Weather property", WEATHER_VARS,
    format_func=lambda v: f"{WEATHER_LABELS[v][0]} ({WEATHER_LABELS[v][1]})",
    key="corr_property", persist_state="session")

# Weekly change shows short-term effects (e.g. rain filling the reservoir). 
# The level shows the seasonal relation
reservoir_var = col2.radio(
    "Reservoir variable", ["change", "level"], horizontal=True,
    format_func=lambda v: "Weekly change in filling" if v == "change" else "Filling level")

# Years to compare; the default is the last five complete years
# Weather is downloaded one cached year at a time
this_year = pd.Timestamp.today().year
start_year, end_year = st.select_slider(
    "Years", options=list(range(2015, this_year + 1)), value=(this_year - 5, this_year - 1))
col3, col4 = st.columns(2)
lag = col3.slider("Lag (weeks the weather comes before the reservoir)", 0, 26, 0)
window = col4.slider("Window length (weeks)", 4, 104, 26, step=2)

# Weekly weather for the area and period
try:
    weather = load_weather_period(area_type, area_nr, start_year, end_year, prop)
except RequestException as error:
    st.error(f"Could not download weather data: {error}")
    st.stop()

# Weekly reservoir series for the same area, in percent (level) or percentage points (change),
# cut to the weeks that have weather, so both series cover the same period
df, _, _ = load_data(pd.Period("1995-01", "M"), pd.Timestamp.today().to_period("M"))
df = df[(df["area_type"] == area_type) & (df["area_nr"] == area_nr)].set_index("Date")
column = "change_res_level" if reservoir_var == "change" else "res_level"
reservoir = (df[column] * 100)[weather.index.min():weather.index.max()]
reservoir_label = "Weekly change in filling (pp)" if reservoir_var == "change" else "Filling (%)"

# The sliding window correlation
correlation = sliding_window_correlation(reservoir, weather, lag, window)
if correlation.notna().sum() == 0:
    st.warning("The window is longer than the chosen period. Choose more years or a shorter window.")
    st.stop()

# Plotting both series and the correlation
name, unit, _ = WEATHER_LABELS[prop]
weather_label = f"{name}, weekly {'total' if prop in SUM_VARS else 'mean'} ({unit})"
fig = plot_swc(reservoir, weather, correlation, reservoir_label, weather_label, lag, window,
               title=f"{name} and reservoir in {area_name(area_type, area_nr)}, {start_year}–{end_year}")
st.plotly_chart(fig)

# The average correlation over the period, as a single summary number
st.metric("Mean correlation over the period", f"{correlation.mean():.2f}")

with st.expander("About this page"):
    st.write("""The weather is shifted forward by the lag, so a lag of 4 compares each week's reservoir
    value with the weather four weeks earlier. The correlation is computed in a window of the chosen
    length that slides one week at a time, and each value is placed at the centre of its window.
    Data: NVE Magasinstatistikk and Open-Meteo (ERA5), aggregated to Monday–Sunday weeks in Norwegian time.""")