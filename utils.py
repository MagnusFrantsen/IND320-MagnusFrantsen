import streamlit as st
import pandas as pd
import requests
from pathlib import Path
import numpy as np
from scipy.fft import dct, idct
from scipy.stats import median_abs_deviation
from sklearn.neighbors import LocalOutlierFactor
from scipy.signal import spectrogram
from statsmodels.tsa.seasonal import STL
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Colours used in every plot, chosen to stand out on the dark blue theme
PLOT_COLORS = {
    "series": "#5aa9e6",     # the main data series
    "highlight": "#f2a900",  # outliers, anomalies and other marked points (same as primaryColor)
    "limits": "#9fb3c8",     # control limits and reference lines
}
# One colour per area number, in order (area 1, 2, 3, ...)
AREA_COLORS = ["#5aa9e6", "#f2a900", "#7fc8a9", "#e07a5f", "#c9ada7"]

# Colour scale for the spectrogram: from a blue near the page background, through light blue, to the highlight colour
SPECTROGRAM_SCALE = [[0.0, "#14305a"], [0.5, "#5aa9e6"], [1.0, "#f2a900"]]

# Loading the data from the Magasinstatistikk API
@st.cache_data(ttl="1d", show_spinner="Downloading reservoir data from NVE...")
def load_data(start, end):

    # Address of NVE's public API for weekly reservoir statistics (Magasinstatistikk)
    URL_MAGASIN = "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk/HentOffentligData"

    # Downloading the data; timeout=15 stops the request if the API has not answered within 15 seconds
    response = requests.get(URL_MAGASIN, timeout = 15)

    # The API returns a list of JSON records, which becomes one row each in a DataFrame
    df = pd.DataFrame(response.json())  

    # Renaming the columns from the API's Norwegian names to short English names
    df.columns = ['Date', 'area_type','area_nr', 'iso_year', 'iso_week', 
              'res_level', 'capacity_TWh', 'res_level_TWh', 
              'next_publish_date', 'prev_res_level', 'change_res_level']

    # Converting the Date column from text to datetime, so it can be sorted and compared as dates
    df['Date'] = pd.to_datetime(df['Date'])
    # Sorting the rows by date, oldest first
    df = df.sort_values(by=['Date'], ascending=True)
    # Keeping only the rows with months between start and end including both
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

    # Returning relevant variables from load data
    return df, columns_to_plot, column_mapping

# The address for the Open-Meteo API 
WEATHER_URL = "https://archive-api.open-meteo.com/v1/archive"

# Defining the weather parameters wanting to be downloaded in a list for later use
WEATHER_VARS = [
    "temperature_2m",
    "precipitation",
    "snowfall",
    "shortwave_radiation",
    "wind_speed_10m",
    "soil_moisture_0_to_7cm",
]

# Defining the function fetch locations
def fetch_location(lat, lon, start_date, end_date):
    """Download hourly ERA5 data for one location."""

    # Defining the parameters for the download
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

    # Creating a get response from Open-Meteo
    response = requests.get(WEATHER_URL, params=params, timeout=60)
    response.raise_for_status()
    # Converting the JSON-response to a pandas DataFrame
    frame = pd.DataFrame(response.json()["hourly"])
    frame["time"] = pd.to_datetime(frame["time"], utc=True)
    # Returning frame
    return frame

def fetch_locations(locations, start_date, end_date):
    """Download hourly ERA5 data for several locations in one request.

    locations: table with the columns lat, lon and n_points
    Returns one table with all locations below each other, including n_points.
    """
    count = len(locations)

    # Defining the parameters for the download
    params = {
        # All coordinates in one request, separated by commas
        "latitude": ",".join(str(lat) for lat in locations["lat"]),
        "longitude": ",".join(str(lon) for lon in locations["lon"]),
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(WEATHER_VARS),
        "models": "era5",
        "timezone": "UTC",
        "wind_speed_unit": "ms",
        # One value per location: use each grid cell's own elevation
        "elevation": ",".join(["nan"] * count),
    }

    # Creating a get response from Open-Meteo (longer timeout, since the answer is larger)
    response = requests.get(WEATHER_URL, params=params, timeout=120)
    response.raise_for_status()

    # Several locations give a list with one structure per location,
    # while a single location gives one structure
    results = response.json()
    if isinstance(results, dict):
        results = [results]
    if len(results) != count:
        raise ValueError(f"Asked for {count} locations but received {len(results)}")

    # Converting each structure to a table and adding the weight of its location
    frames = []
    for result, n_points in zip(results, locations["n_points"]):
        frame = pd.DataFrame(result["hourly"])
        frame["time"] = pd.to_datetime(frame["time"], utc=True)
        frames.append(frame.assign(n_points=n_points))
    return pd.concat(frames, ignore_index=True)

# Creating a function to compute the mean of a region
def region_mean(weather):
    """Compute the hourly mean for the area, weighted by the number of points per cell."""
    values = weather[WEATHER_VARS]
    weighted_sum = values.mul(weather["n_points"], axis=0).groupby(weather["time"]).sum()
    weight_sum = values.notna().mul(weather["n_points"], axis=0).groupby(weather["time"]).sum()
    return weighted_sum / weight_sum

# Creating the load_weather function with 1d cache and a spinner showing when it is running
@st.cache_data(ttl="1d", show_spinner="Loading weather data...")
def load_weather(area_type, area_nr, year):
    """Return hourly weather for an area, using the full NO3 result where it exists."""

    # Using the NO3 data saved from the notebook if it exists, so the app does not have to call the API for NO3
    stored_file = Path(f"data/NO3_{year}_hourly.csv")
    if area_type == "EL" and area_nr == 3 and stored_file.exists():
        return pd.read_csv(stored_file, index_col="time", parse_dates=True)

    # Finding the area name used in locations.csv, for example "NO 3" or "VASS 1"
    area = f"NO {area_nr}" if area_type == "EL" else f"VASS {area_nr}"

    # Reading the saved locations and keeping only the ones in the selected area
    locations = pd.read_csv("data/locations.csv")
    selected = locations[locations["area"] == area]

    # Downloading hourly weather for all the selected locations in one request
    weather = fetch_locations(selected, f"{year}-01-01", f"{year}-12-31")

    # Returning the weighted hourly mean for the area
    return region_mean(weather)

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

def plot_series_with_points(series, points, label, points_name, title, limits=None):
    """Return a Plotly chart of an hourly series with marked points, and optional limit lines.

    series: the hourly values with a time index.
    points: the marked values (outliers or anomalies), with a time index.
    label: name and unit of the series, shown on the y-axis and in the legend.
    points_name: legend name of the marked points, including their count.
    limits: optional (lower, upper) series, drawn as dashed lines.
    """
    fig = go.Figure()

    # Scattergl draws with WebGL, which keeps zooming smooth for the ~8,800 hourly points in a year
    fig.add_trace(go.Scattergl(x=series.index, y=series, mode="lines", name=label,
                               line=dict(color=PLOT_COLORS["series"], width=1)))

    # The control limits follow the seasonal pattern; drawn dashed, with one legend entry for both
    if limits is not None:
        lower, upper = limits
        for name, values, show in [("Control limits", upper, True), ("Lower limit", lower, False)]:
            fig.add_trace(go.Scattergl(x=values.index, y=values, mode="lines", name=name,
                                       legendgroup="limits", showlegend=show,
                                       line=dict(color=PLOT_COLORS["limits"], width=1, dash="dash")))

    # The marked points on top, in the highlight colour
    fig.add_trace(go.Scattergl(x=points.index, y=points, mode="markers", name=points_name,
                               marker=dict(color=PLOT_COLORS["highlight"], size=6)))

    fig.update_layout(title=title, yaxis_title=label, height=450,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    return fig

# Creating a function to identify outliers in a time series using Statistical Process Control (SPC) 
# limits based on robust statistics of the seasonally adjusted temperature variations (SATV).
def spc_outliers(series, cutoff_days=30, n_std=3.0, label="Temperature (°C)", title="Temperature outliers"):
    """Find outliers with SPC limits based on robust statistics of the SATV.

    series: hourly values with a time index.
    cutoff_days: variation slower than this counts as seasonal.
    n_std: number of robust standard deviations from the median to the limits.
    Returns the figure and a dictionary with a summary and a table of the outliers.
    label: name and unit of the series, shown on the y-axis and in the legend.
    title: title of the plot.
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

     # Plotting the series, the control limits and the outliers, with the outlier count in the legend
    fig = plot_series_with_points(series, outliers["value"], label, f"Outliers ({len(outliers)})",
                                  title, limits=(lower, upper))

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

def lof_anomalies(series, proportion=0.01, n_neighbors=20, label="Temperature (°C)", title="Temperature anomalies"):
    """Find anomalies in a time series with the Local Outlier Factor method.

    series: hourly values with a time index.
    proportion: share of the points to mark as anomalies.
    n_neighbors: number of neighbours each point is compared with.
    Returns the figure and a dictionary with a summary and a table of the anomalies.
    label: name and unit of the series, shown on the y-axis and in the legend.
    title: title of the plot.
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

    # Plotting the series with the anomalies marked, with the anomaly count in the legend
    fig = plot_series_with_points(series, anomalies["value"], label, f"Anomalies ({len(anomalies)})", title)

    summary = {
        "n_anomalies": len(anomalies),
        "share_anomalies": len(anomalies) / len(series),
        "value_min": anomalies["value"].min(),
        "value_max": anomalies["value"].max(),
        "anomalies_per_month": anomalies.groupby(anomalies.index.month).size(),
        "anomalies": anomalies.sort_values("lof_score", ascending=False),
    }
    return fig, summary

def filling_series(data, omr_type="NO", omr_nr=0):
    """Return the weekly degree of filling in percent for one area."""

     # Keeping only the rows for the selected area
    selected = data[(data["area_type"] == omr_type) & (data["area_nr"] == omr_nr)]
    # Using the date as index, sorting by date, and converting the filling from a share (0–1) to percent
    series = selected.set_index(pd.to_datetime(selected["Date"]))["res_level"].sort_index() * 100
    # Setting a fixed weekly frequency, so STL and the spectrogram get evenly spaced data.
    # Any missing weeks get a value interpolated between the neighbouring weeks
    return series.asfreq("7D").interpolate()

def plot_stl(series, period=52, seasonal=13, trend=None, robust=True, title ="STL decomposition of weekly reservoir filling"):
    """Plot an STL decomposition of a weekly series.

    series: weekly values with a time index and no gaps.
    period: number of samples per seasonal cycle.
    seasonal: seasonal smoother length in weeks, must be odd and at least 7.
    trend: trend smoother length, must be odd. None lets STL choose from the other settings.
    robust: reduces the influence of unusual weeks when True.
    Returns the figure.
    """
    result = STL(series, period=period, seasonal=seasonal, trend=trend, robust=robust).fit()

    # One row per part of the decomposition, sharing the time axis so zooming moves all four together
    parts = [("Filling (%)", result.observed), ("Trend (%)", result.trend),
             ("Seasonal (%)", result.seasonal), ("Residual (%)", result.resid)]
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.04)

    for row, (name, values) in enumerate(parts, start=1):
        # The residual is drawn as points, the other parts as lines
        mode = "markers" if row == 4 else "lines"
        fig.add_trace(go.Scatter(x=values.index, y=values, mode=mode, name=name, showlegend=False,
                                 line=dict(color=PLOT_COLORS["series"], width=1.5),
                                 marker=dict(color=PLOT_COLORS["series"], size=3)),
                      row=row, col=1)
        fig.update_yaxes(title_text=name, row=row, col=1)

    # A zero line in the residual panel, so deviations above and below are easy to compare
    fig.add_hline(y=0, line=dict(color=PLOT_COLORS["limits"], width=1, dash="dash"), row=4, col=1)

    fig.update_layout(title=title, height=750, hovermode="x unified")
    return fig

def plot_spectrogram(series, window_length=104, window_overlap=78, title="Spectrogram of reservoir filling"):
    """Plot a spectrogram of a weekly series.

    series: weekly values with a time index and no gaps.
    window_length: number of weeks in each window.
    window_overlap: number of weeks shared by neighbouring windows.
    Returns the figure.
    """

    # The windows must move forward, so the overlap has to be smaller than the window
    if window_overlap >= window_length:
        raise ValueError("window_overlap must be smaller than window_length")

    # Computing how strong each frequency is in each window.
    # fs=52 gives frequencies in cycles per year, since there are 52 samples per year.
    frequencies, times, power = spectrogram(
        series.to_numpy(),
        fs=52,
        window="hann",
        nperseg=window_length,
        noverlap=window_overlap,
        detrend="linear",
    )
    # Converting the window centres (given in years from the start) into dates for the x-axis and
    # times * 52 is the position in weeks, so times * 52 * 7 gives the exact number of days from the start
    window_centers = series.index[0] + pd.to_timedelta(times * 52 * 7, unit="D")

        # Plotting the power in decibels as colours: time on the x-axis, frequency on the y-axis.
    # 1e-12 avoids taking the log of zero
    fig = go.Figure(go.Heatmap(
        x=window_centers, y=frequencies, z=10 * np.log10(power + 1e-12),
        colorscale=SPECTROGRAM_SCALE, colorbar=dict(title="Power (dB)"),
        # Hover text: month of the window, frequency and power
        hovertemplate="%{x|%Y-%m}<br>%{y:.2f} cycles per year<br>%{z:.1f} dB<extra></extra>",
    ))
    fig.update_layout(title=title, xaxis_title="Year", yaxis_title="Frequency (cycles per year)", height=450)

    # Returning the figure
    return fig