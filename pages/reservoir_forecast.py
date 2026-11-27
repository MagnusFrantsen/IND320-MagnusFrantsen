import streamlit as st
import numpy as np
import pandas as pd
from requests.exceptions import RequestException
from utils import (forecast_table, forecast_ahead, forecast_animation, month_slider, area_name,
                   WEATHER_VARS, WEATHER_LABELS)

# Best setting from the forecast tests in the Assignment 4 notebook, used as defaults on this page
BEST_SETTING = {"p": 2, "d": 0, "q": 0, "sp": 1, "sd": 1, "sq": 0, "lr": 0.001, "years": 10, "horizon": 26}

st.title("Reservoir Forecast")
st.write("""Forecast of the reservoir filling for the selected area, with a SNARIMAX model from River.
The model learns from the chosen years of weekly data and forecasts the following weeks, each week
built on its own earlier predictions. Press Play to watch the forecast unfold.""")

# The area chosen in the sidebar or on the map
area_type = st.session_state["area_type"]
area_nr = st.session_state["area_nr"]

# Training period: ends in the month shared with the map, and goes back the chosen number of years
months = list(pd.period_range("1995-01", pd.Timestamp.today().to_period("M") - 1, freq="M"))
col1, col2 = st.columns(2)
month = month_slider(col1, "Training data ends in (same month as the map)", months, key="forecast_month")
years = col2.slider("Years of training data", 2, 25, BEST_SETTING["years"],
                    help="The notebook tests found about ten years best; two years made the model unstable.")
horizon = st.slider("Forecast horizon (weeks)", 4, 52, BEST_SETTING["horizon"])

# Exogenous variables; weather needs a specific area, so it is not offered for the whole country
options = (WEATHER_VARS if area_type != "NO" else []) + ["EUR", "USD"]
sources = st.multiselect(
    "Exogenous variables", options, default=[],
    format_func=lambda v: WEATHER_LABELS[v][0] if v in WEATHER_LABELS else f"{v}/NOK exchange rate",
    help="None by default: in the notebook tests, no source improved the forecast.")
if area_type == "NO":
    st.caption("Weather is only offered for a price area or a water area.")

# Model parameters, with the best setting from the notebook as defaults
with st.expander("Model parameters (SNARIMAX)"):
    c1, c2, c3 = st.columns(3)
    p = c1.number_input("p: recent weeks used", 0, 6, BEST_SETTING["p"])
    d = c2.number_input("d: differencing", 0, 1, BEST_SETTING["d"])
    q = c3.number_input("q: recent errors used", 0, 3, BEST_SETTING["q"])
    c4, c5, c6 = st.columns(3)
    sp = c4.number_input("sp: earlier years used", 0, 2, BEST_SETTING["sp"])
    sd = c5.number_input("sd: seasonal differencing", 0, 1, BEST_SETTING["sd"])
    sq = c6.number_input("sq: earlier years' errors used", 0, 2, BEST_SETTING["sq"])
        # Smaller learning rates learn more slowly but stop the dynamic forecast from snowballing
    lr = st.select_slider("Learning rate (SGD)", options=[0.0005, 0.001, 0.005, 0.01], value=BEST_SETTING["lr"],
                          help="0.01 made the forecast unstable in up to a quarter of the notebook tests; 0.001 almost never.")
    st.caption("The season is fixed at 52 weeks, since the data are weekly.")

# Weekly table of the filling and the chosen variables. The weather and exchange rates are downloaded
# from the first year of the training period, so the downloads are no longer than needed
start_year = (month.start_time - pd.DateOffset(years=years)).year
try:
    table = forecast_table(area_type, area_nr, start_year, month.year, sources)
except RequestException as error:
    st.error(f"Could not download the data: {error}")
    st.stop()

# At least two years of complete training weeks are needed for a yearly season
if len(table[:month.end_time].dropna()) < 104:
    st.warning("Too little training data for this period. Choose a later month or more years.")
    st.stop()

# Training the model and forecasting; cached, so it only reruns when a setting changes
history, forecast, actual = forecast_ahead(table, month.end_time, years, horizon, tuple(sources),
                                           p, d, q, sp, sd, sq, lr)

# The filling must stay between 0 and 100 %; a forecast clearly outside that means the model has become unstable
if not np.isfinite(forecast).all() or forecast.min() < -5 or forecast.max() > 105:
    st.warning("""The model became unstable with these settings: the forecast leaves the 0-100 % range.
    Try more years of training data, a smaller learning rate, or fewer exogenous variables.""")
    st.stop()

name = area_name(area_type, area_nr)
st.plotly_chart(forecast_animation(history, forecast, actual,
                                   f"Forecast of reservoir filling in {name}, {horizon} weeks from {month}"))

# Key numbers: last known value, forecast end value, and the actual value when it is published for the last forecast week
complete = forecast.index[-1] in actual.index
if complete:
    m1, m2, m3, m4 = st.columns(4)
else:
    m1, m2, m4 = st.columns(3)
m1.metric("Last filling in training data", f"{history.iloc[-1]:.1f} %")
m2.metric(f"Forecast in {horizon} weeks", f"{forecast.iloc[-1]:.1f} %")

# Actual filling for the same week as the forecast, only when it is published
if complete:
    m3.metric(f"Actual in {horizon} weeks", f"{actual.iloc[-1]:.1f} %",
              delta=f"{actual.iloc[-1] - forecast.iloc[-1]:+.1f} pp vs forecast", delta_color="off")

# Mean error over the forecast weeks that already have a published filling
if len(actual):
    error = (forecast.reindex(actual.index) - actual).abs().mean()
    m4.metric(f"Mean error ({len(actual)} weeks)", f"{error:.1f} pp")
else:
    m4.metric("Mean error", "Not known yet")    

with st.expander("About this forecast"):
    st.write("""The model is River's SNARIMAX, trained one week at a time. Future values of exogenous
    variables are not known in advance, so weather uses the average for that week of the year in the
    training data, and exchange rates keep their last known value. When the training data ends in the
    past, the real filling is shown for comparison, and the mean error is computed from those weeks.
    Data: NVE Magasinstatistikk, Open-Meteo (ERA5) and Norges Bank.""")