import streamlit as st
import pandas as pd
import requests
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from scipy.fft import dct, idct
from scipy.stats import median_abs_deviation
from sklearn.neighbors import LocalOutlierFactor

# Loading the data from the Magasinstatistikk API
@st.cache_data(ttl=("1d"))
def load_data(start, end):

    URL_MAGASIN = "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk/HentOffentligData"

    response = requests.get(URL_MAGASIN, timeout = 15)

    df = pd.DataFrame(response.json())  

    df.columns = ['Date', 'area_type','area_nr', 'iso_year', 'iso_week', 
              'res_level', 'capacity_TWh', 'res_level_TWh', 
              'next_publish_date', 'prev_res_level', 'change_res_level']

    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values(by=['Date'], ascending=True)
    # Creating a new column in the dataframe with the monts
    df = df[df['Date'].dt.to_period('M').between(start,end)]

    # Choosing these as the relevant columns to plot from the csv file and returning a list for use in the other files
    columns_to_plot = ['res_level', 'res_level_TWh', 'prev_res_level', 'change_res_level']

    # Creating a dictionary to create nicer titles and labels for axis in the plots
    column_mapping = {
        'res_level': "Reservoir Level (%)",
        'res_level_TWh': "Reservoir Level (TWh)",
        'prev_res_level': "Previous Reservoir Level (%)",
        'change_res_level': "Change in Reservoir Level (%)"
    }

    return df, columns_to_plot, column_mapping

WEATHER_URL = "https://archive-api.open-meteo.com/v1/archive"

WEATHER_VARS = [
    "temperature_2m",
    "precipitation",
    "snowfall",
    "shortwave_radiation",
    "wind_speed_10m",
    "soil_moisture_0_to_7cm",
]

# NVE regions that make up each VASS area
VASS_AREAS = {1: ["RS", "RØ"], 2: ["RV"], 3: ["RM"], 4: ["RN"]}


def fetch_location(lat, lon, start_date, end_date):
    """Download hourly ERA5 data for one location."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(WEATHER_VARS),
        "models": "era5",
        "timezone": "UTC",
        "wind_speed_unit": "ms",
        "elevation": "nan",
    }
    response = requests.get(WEATHER_URL, params=params, timeout=60)
    response.raise_for_status()
    frame = pd.DataFrame(response.json()["hourly"])
    frame["time"] = pd.to_datetime(frame["time"], utc=True)
    return frame


def region_mean(weather):
    """Compute the hourly mean for the area, weighted by the number of points per cell."""
    values = weather[WEATHER_VARS]
    weighted_sum = values.mul(weather["n_points"], axis=0).groupby(weather["time"]).sum()
    weight_sum = values.notna().mul(weather["n_points"], axis=0).groupby(weather["time"]).sum()
    return weighted_sum / weight_sum


@st.cache_data(ttl="1d")
def load_weather(area_type, area_nr, year):
    """Return hourly weather for an area, using the full NO3 result where it exists."""
    stored_file = Path(f"data/NO3_{year}_hourly.csv")
    if area_type == "EL" and area_nr == 3 and stored_file.exists():
        return pd.read_csv(stored_file, index_col="time", parse_dates=True)

    # Finding the area names used in locations.csv
    areas = [f"NO {area_nr}"] if area_type == "EL" else VASS_AREAS[area_nr]

    locations = pd.read_csv("data/locations.csv")
    selected = locations[locations["area"].isin(areas)]

    frames = []
    for row in selected.itertuples():
        frame = fetch_location(row.lat, row.lon, f"{year}-01-01", f"{year}-12-31")
        frames.append(frame.assign(n_points=row.n_points))
    return region_mean(pd.concat(frames, ignore_index=True))

# Creating a function to remove slow variations from a time series using the Discrete Cosine Transform (DCT).
def dct_highpass(series, cutoff_days=30):
    """Remove variation slower than cutoff_days using the Discrete Cosine Transform."""
    if series.isna().any():
        raise ValueError("The DCT needs a series without missing values")

    # The length of the series is determined, and the DCT coefficients are computed using the 'ortho' normalization.
    n = len(series)
    coefficients = dct(series.to_numpy(), norm="ortho")

    # Coefficient k has a period of 2n / k hours, so slower waves have a lower k
    cutoff = round(2 * n / (cutoff_days * 24))
    coefficients[:cutoff] = 0

    # Returning the inverse DCT of the modified coefficients, which gives the
    # seasonally adjusted temperature variations (SATV).
    return pd.Series(idct(coefficients, norm="ortho"), index=series.index, name="satv")

# Creating a function to identify outliers in a time series using Statistical Process Control (SPC) 
# limits based on robust statistics of the seasonally adjusted temperature variations (SATV).
def spc_outliers(series, cutoff_days=30, n_std=3.0):
    """Find outliers with SPC limits based on robust statistics of the SATV.

    series: hourly values with a time index.
    cutoff_days: variation slower than this counts as seasonal.
    n_std: number of robust standard deviations from the median to the limits.
    Returns the figure and a dictionary with a summary and a table of the outliers.
    """

    # The seasonally adjusted temperature variations (SATV) are computed using the DCT highpass filter 
    # with the specified cutoff in days.
    satv = dct_highpass(series, cutoff_days)

    # The median and MAD are barely affected by the outliers we are looking for
    center = satv.median()
    robust_std = median_abs_deviation(satv, scale="normal")

    # Adding the seasonal part back gives limits that follow the original series
    seasonal = series - satv
    
    # The lower and upper SPC limits are calculated by adding and subtracting the product of the number 
    # of robust standard deviations (n_std) and the robust standard deviation (robust_std) from the seasonal component and 
    # the center (median) of the SATV.
    lower = seasonal + center - n_std * robust_std
    upper = seasonal + center + n_std * robust_std

    # Identifying outliers based on the SPC limits, where values outside the range defined by the center and robust standard 
    # deviation are considered outliers.
    is_outlier = (satv < center - n_std * robust_std) | (satv > center + n_std * robust_std)
    outliers = pd.DataFrame({"value": series[is_outlier], "satv": satv[is_outlier]})

    # Creating a plot to visualize the original series, SPC limits, and identified outliers.
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(series.index, series, color="#2a78d6", linewidth=0.7, label=series.name or "Value")
    ax.plot(series.index, upper, color="#52514e", linewidth=1, linestyle="--", label="SPC limits")
    ax.plot(series.index, lower, color="#52514e", linewidth=1, linestyle="--")
    ax.scatter(outliers.index, outliers["value"], color="#eb6834", s=12, zorder=3, label="Outliers")
    ax.set_title(f"{len(outliers)} outliers ({n_std:g} robust SD, {cutoff_days}-day cutoff)")
    ax.set_ylabel(series.name or "Value")
    ax.grid(axis="y", alpha=0.3)
    ax.legend(loc="upper right", frameon=False)
    fig.tight_layout()

    """Creating a summary dictionary containing information about the number of outliers, their share in the series,
    the number of high and low outliers, the median of the SATV, the robust standard deviation of the SATV, 
    and a DataFrame containing the identified outliers."""
    summary = {
        "n_outliers": len(outliers),
        "share_outliers": len(outliers) / len(series),
        "n_high": int((outliers["satv"] > center).sum()),
        "n_low": int((outliers["satv"] < center).sum()),
        "satv_median": center,
        "satv_robust_std": robust_std,
        "outliers": outliers,
    }
    return fig, summary

def lof_anomalies(series, proportion=0.01, n_neighbors=20):
    """Find anomalies in a time series with the Local Outlier Factor method.

    series: hourly values with a time index.
    proportion: share of the points to mark as anomalies.
    n_neighbors: number of neighbours each point is compared with.
    Returns the figure and a dictionary with a summary and a table of the anomalies.
    """
    if series.isna().any():
        raise ValueError("LOF needs a series without missing values")

    # Using time and value, so a point is compared with similar times of the year
    time_position = np.arange(len(series))
    features = np.column_stack([
        (time_position - time_position.mean()) / time_position.std(),
        (series - series.mean()) / series.std(),
    ])

    model = LocalOutlierFactor(n_neighbors=n_neighbors, contamination=proportion)
    is_anomaly = model.fit_predict(features) == -1  # -1 marks outliers

    # A score near 1 is normal, and a higher score is more unusual
    scores = pd.Series(-model.negative_outlier_factor_, index=series.index)
    anomalies = pd.DataFrame({"value": series[is_anomaly], "lof_score": scores[is_anomaly]})

    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(series.index, series, color="#2a78d6", linewidth=0.7, label=series.name or "Value")
    ax.scatter(anomalies.index, anomalies["value"], color="#eb6834", s=12, zorder=3, label="Anomalies")
    ax.set_title(f"{len(anomalies)} anomalies with LOF ({proportion:.1%} of points)")
    ax.set_ylabel(series.name or "Value")
    ax.grid(axis="y", alpha=0.3)
    ax.legend(loc="upper right", frameon=False)
    fig.tight_layout()

    summary = {
        "n_anomalies": len(anomalies),
        "share_anomalies": len(anomalies) / len(series),
        "value_min": anomalies["value"].min(),
        "value_max": anomalies["value"].max(),
        "anomalies_per_month": anomalies.groupby(anomalies.index.month).size(),
        "anomalies": anomalies.sort_values("lof_score", ascending=False),
    }
    return fig, summary