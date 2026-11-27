import streamlit as st
import pandas as pd
import requests
from pathlib import Path
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import plotly.express as px
import io

# The heavy libraries (scipy, scikit-learn, statsmodels, river) are imported inside the functions that use them.
# Importing them here added about 9 seconds before the home page could show anything when starting the app

# Colours used in every plot, chosen to stand out on the dark blue theme
PLOT_COLORS = {
    "series": "#5aa9e6",     # the main data series
    "highlight": "#f2a900",  # outliers, anomalies and other marked points (same as primaryColor)
    "limits": "#9fb3c8",     # control limits and reference lines
}
# One colour per area number, in order (area 1, 2, 3, ...)
AREA_COLORS = ["#5aa9e6", "#f2a900", "#7fc8a9", "#e07a5f", "#c9ada7"]

# Colour scale for the spectrogram: dark blue for weak, muted blue in between, amber for strong frequencies
SPECTROGRAM_SCALE = [[0.0, "#0d2240"], [0.6, "#2f6ea3"], [1.0, "#f2a900"]]

# Loading the data from the Magasinstatistikk API
@st.cache_data(ttl="1d", show_spinner="Downloading reservoir data from NVE...")
def load_data(start, end):

    """Download NVE's weekly reservoir statistics (Magasinstatistikk) for all areas.

    start, end: first and last month to keep, as pandas Periods (both included)
    Returns the data with English column names, the columns that can be plotted,
    and readable labels for those columns.
    Cached for a day, since NVE publishes new figures once a week; every page reuses the same download.
    """

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
    df = df[df['Date'].dt.to_period('M').between(start, end)]

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

# Readable name, unit and number of decimals for each weather variable, used in selectors, labels and metrics
WEATHER_LABELS = {
    "temperature_2m": ("Temperature", "°C", 1),
    "precipitation": ("Precipitation", "mm", 1),
    "snowfall": ("Snowfall", "cm", 1),
    "shortwave_radiation": ("Solar radiation", "W/m²", 0),
    "wind_speed_10m": ("Wind speed", "m/s", 1),
    "soil_moisture_0_to_7cm": ("Soil moisture", "m³/m³", 3),
}

# Defining the function fetch locations
def fetch_location(lat, lon, start_date, end_date):
    """Download hourly ERA5 data for one location (one request per location).

    Superseded by fetch_locations, which groups several locations in one request (part 3 feedback).
    Kept because the part 3 notebook uses it, and the part 4 notebook compares the two to show they give the same result.
    """

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

def fetch_locations(locations, start_date, end_date, variables=WEATHER_VARS):
    """Download hourly ERA5 data for several locations in one request.

    locations: table with the columns lat, lon and n_points
    Returns one table with all locations below each other, including n_points.
    """
    count = len(locations)

    # An empty table would send a request without coordinates and give a cryptic JSON error
    if count == 0:
        raise ValueError("No locations given: check the area name (e.g. 'NO 3', with a space)")

    # Defining the parameters for the download
    params = {
        # All coordinates in one request, separated by commas
        "latitude": ",".join(str(lat) for lat in locations["lat"]),
        "longitude": ",".join(str(lon) for lon in locations["lon"]),
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(variables),
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
    # Every column except time and the weight is a weather variable
    values = weather.drop(columns=["time", "n_points"])
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

# GeoJSON outline file for each area type on the map
MAP_FILES = {"EL": "data/map_price_areas.geojson",
             "VASS": "data/map_vass_areas.geojson",
             "NO": "data/map_norway_areas.geojson"}

# Weather variables that are summed over a period; the others are averaged
SUM_VARS = ["precipitation", "snowfall"]

@st.cache_data
def load_map_areas(area_type):
    """Return the GeoJSON outlines for one area type, read once and kept in the cache."""
    with open(MAP_FILES[area_type], encoding="utf-8") as f:
        return json.load(f)


def area_name(area_type, area_nr):
    """Name of an area on the map and in locations.csv, e.g. 'NO 3', 'VASS 1' or 'Norway'."""
    if area_type == "EL":
        return f"NO {area_nr}"
    if area_type == "VASS":
        return f"VASS {area_nr}"
    return "Norway"


def area_from_name(name):
    """The reverse of area_name: from a map name back to (area type, area number)."""
    if name == "Norway":
        return "NO", 0
    kind, nr = name.split(" ")
    return ("EL" if kind == "NO" else "VASS"), int(nr)


# Cached: the map recomputes this on every click and month change otherwise
@st.cache_data(ttl="1d", show_spinner="Preparing reservoir filling for the map...")
def filling_for_month(area_type, month):
    """Reservoir filling in percent for every area of a type, from the last published week in the month."""
    # Loading the whole period once, so the cached download is reused for every month
    df, _, _ = load_data(pd.Period("1995-01", "M"), pd.Timestamp.today().to_period("M"))
    df = df[(df["area_type"] == area_type) & (df["Date"].dt.to_period("M") == month)]

    # Keeping only the last week of the month, and converting the filling from a share to percent
    last_week = df[df["Date"] == df["Date"].max()]
    names = [area_name(area_type, nr) for nr in last_week["area_nr"]]
    return pd.Series(last_week["res_level"].to_numpy() * 100, index=names)


@st.cache_data(ttl="1d", show_spinner="Loading weather for the map...")
def weather_for_month(area_type, month):
    """Weather for every area of a type in one month: totals for precipitation and snowfall,
    means for the other variables. Returns one row per area and one column per variable."""
    # All grid cells for the area type, downloaded in one grouped request
    locations = pd.read_csv("data/locations.csv")
    prefix = "VASS " if area_type == "VASS" else "NO "
    selected = locations[locations["area"].str.startswith(prefix)].reset_index(drop=True)
    hourly = fetch_locations(selected, month.start_time.strftime("%Y-%m-%d"),
                             month.end_time.strftime("%Y-%m-%d"))

    # fetch_locations returns the locations below each other, in the order they were sent,
    # with the same number of hours each, so each block of rows gets its area's name
    hourly["area"] = np.repeat(selected["area"].to_numpy(), len(hourly) // len(selected))

    # For the whole country, every price-area grid cell counts towards one area
    if area_type == "NO":
        hourly["area"] = "Norway"

    # Weighted hourly mean per area, then the monthly total or mean of each variable
    result = {}
    for area, group in hourly.groupby("area"):
        area_hourly = region_mean(group.drop(columns="area"))
        result[area] = pd.concat([area_hourly.drop(columns=SUM_VARS).mean(), area_hourly[SUM_VARS].sum()])
    return pd.DataFrame(result).T

# Colour scale for the map, in the app's colours; the alpha value 0.6 makes the areas see-through
MAP_SCALE = [(0.0, "rgba(13,34,64,0.6)"), (0.5, "rgba(47,110,163,0.6)"), (1.0, "rgba(242,169,0,0.6)")]


def area_map(area_type, values, selected, label, range_color=None):
    """Return a Plotly map of one area type, coloured by a value per area, with the selected area outlined.

    area_type: "EL", "VASS" or "NO"
    values: Series with one value per area, indexed by area name (e.g. "NO 3")
    selected: name of the selected area, drawn with a thick outline
    label: name and unit of the value, shown on the colour bar and when hovering
    range_color: optional (min, max) for the colour scale; None uses the range of the values
    """
    geojson = load_map_areas(area_type)
    names = [feature["properties"]["area"] for feature in geojson["features"]]
    data = pd.DataFrame({"area": names, "value": [values.get(name) for name in names]})

    # Areas coloured by their value; transparency comes from the RGBA colour scale, as in the course
    fig = px.choropleth_map(
        data, geojson=geojson, featureidkey="properties.area", locations="area", color="value",
        color_continuous_scale=MAP_SCALE, range_color=range_color,
        map_style="carto-darkmatter", center={"lat": 65, "lon": 15}, zoom=3.3,
        labels={"value": label}, hover_name="area", hover_data={"area": False, "value": ":.1f"},
    )
    # Thin outlines on every area, and no fading of the other areas after a click
    fig.update_traces(marker_line=dict(width=0.8, color="#9fb3c8"), unselected=dict(marker=dict(opacity=1)))

    # The selected area drawn again on top, with no fill and a thick amber outline
    fig.add_trace(go.Choroplethmap(
        geojson=geojson, featureidkey="properties.area", locations=[selected], z=[0],
        colorscale=[(0, "rgba(0,0,0,0)"), (1, "rgba(0,0,0,0)")], showscale=False,
        marker_line=dict(width=4, color="#f2a900"), hoverinfo="skip",
    ))
    fig.update_layout(height=600, margin=dict(l=0, r=0, t=0, b=0))
    return fig


def to_nve_weeks(data, how="mean"):
    """Aggregate a time-indexed Series/DataFrame to NVE weeks.

    Weeks run Monday-Sunday in Norwegian time and are labelled with the Sunday date,
    matching the Magasinstatistikk measurement.
    """
    # Hourly UTC data is moved to Norwegian time, so weeks split at Norwegian midnight
    if data.index.tz is not None:
        data = data.tz_convert("Europe/Oslo")
    weekly = data.resample("W-SUN").agg(how)
    # Dropping the time zone, so all sources get plain dates that can be joined
    weekly.index = weekly.index.tz_localize(None)
    return weekly


@st.cache_data(ttl="1d", show_spinner=False)
def load_property_year(area_type, area_nr, year, prop):
    """Hourly values of one weather property for one area and one year, the weighted mean of its grid cells.
    Fetching only one property keeps the request small, well below Open-Meteo's rate limit."""
    locations = pd.read_csv("data/locations.csv")
    selected = locations[locations["area"] == area_name(area_type, area_nr)]
    end = min(pd.Timestamp(f"{year}-12-31"), pd.Timestamp.today().normalize() - pd.Timedelta(days=7))
    hourly = fetch_locations(selected, f"{year}-01-01", end.strftime("%Y-%m-%d"), variables=[prop])
    return region_mean(hourly)[prop]


def load_weather_period(area_type, area_nr, start_year, end_year, prop):
    """Weekly values of one weather property for one area over several years, one cached year at a time.
    Precipitation and snowfall are weekly totals, the other properties weekly means."""
    years = list(range(start_year, end_year + 1))
    progress = st.progress(0.0, text=f"Downloading weather for {len(years)} years...")
    parts = []
    for i, year in enumerate(years, start=1):
        parts.append(load_property_year(area_type, area_nr, year, prop))
        progress.progress(i / len(years), text=f"Downloaded {year} ({i} of {len(years)})")
    progress.empty()

    # Joining the years, then aggregating to Monday-Sunday weeks; partly covered weeks are dropped
    hourly = pd.concat(parts)
    weekly = to_nve_weeks(hourly, "sum" if prop in SUM_VARS else "mean")
    return weekly[to_nve_weeks(hourly, "count") >= 160]

def sliding_window_correlation(reservoir, weather, lag, window):
    """Correlation between a reservoir series and a weather series in a sliding window.

    lag: weeks the weather is shifted forward, so lag 4 compares each week with the weather 4 weeks earlier
    window: number of weeks in each window; each value is placed at the centre of its window
    """
    # Lining up the two series week by week, after shifting the weather by the lag
    data = pd.concat([reservoir.rename("reservoir"), weather.shift(lag).rename("weather")],
                     axis=1, join="inner").dropna()
    return data["reservoir"].rolling(window, center=True).corr(data["weather"])


def plot_swc(reservoir, weather, correlation, reservoir_label, weather_label, lag, window, title):
    """Two panels sharing the time axis: both series on the same scale on top, the sliding correlation below."""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                        subplot_titles=["Both series, standardised",
                                        f"Correlation in a {window}-week window, weather {lag} weeks earlier"])

    # Standardising both series (mean 0, standard deviation 1), so their shapes can be compared on one axis
    for series, name, color in [(reservoir, reservoir_label, PLOT_COLORS["series"]),
                                (weather.shift(lag), f"{weather_label}, {lag} weeks earlier", PLOT_COLORS["highlight"])]:
        z = (series - series.mean()) / series.std()
        fig.add_trace(go.Scatter(x=z.index, y=z, mode="lines", name=name, line=dict(color=color, width=1.5)),
                      row=1, col=1)

    # The sliding correlation, with a dashed zero line
    fig.add_trace(go.Scatter(x=correlation.index, y=correlation, mode="lines", name="Correlation",
                             line=dict(color=PLOT_COLORS["series"], width=2), showlegend=False), row=2, col=1)
    fig.add_hline(y=0, line=dict(color=PLOT_COLORS["limits"], width=1, dash="dash"), row=2, col=1)

    fig.update_yaxes(title_text="Standard deviations", row=1, col=1)
    fig.update_yaxes(title_text="Correlation", range=[-1, 1], row=2, col=1)
    fig.update_layout(title=title, height=650, hovermode="x unified",
                      legend=dict(orientation="h", yanchor="bottom", y=1.04, x=0))
    return fig

# Norges Bank's API for exchange rates
EXR_URL = "https://data.norges-bank.no/api/data/EXR/"


@st.cache_data(ttl="1d", show_spinner="Downloading exchange rates from Norges Bank...")
def load_exchange_rates(start, end):
    """Weekly mean EUR and USD exchange rates in NOK from Norges Bank, for start to end (YYYY-MM-DD)."""
    params = {"format": "csv", "startPeriod": start, "endPeriod": end, "locale": "en"}
    response = requests.get(EXR_URL + "B.USD+EUR.NOK.SP", params=params, timeout=30)
    response.raise_for_status()

    # The CSV is semicolon-separated, with one row per currency and business day
    rates = pd.read_csv(io.StringIO(response.text), sep=";")
    rates["TIME_PERIOD"] = pd.to_datetime(rates["TIME_PERIOD"])
    daily = rates.pivot(index="TIME_PERIOD", columns="BASE_CUR", values="OBS_VALUE")
    return to_nve_weeks(daily)


def forecast_table(area_type, area_nr, start_year, end_year, sources):
    """Weekly table for the forecast: the filling of one area plus the chosen exogenous variables.

    The sources are joined onto the filling, so the filling continues after the sources end
    and can be compared with the forecast.
    """
    df, _, _ = load_data(pd.Period("1995-01", "M"), pd.Timestamp.today().to_period("M"))
    table = filling_series(df, area_type, area_nr).rename("Filling").to_frame()

    # Weather: one property at a time, one year at a time, to stay below Open-Meteo's rate limit
    for prop in [s for s in sources if s in WEATHER_VARS]:
        table = table.join(load_weather_period(area_type, area_nr, start_year, end_year, prop).rename(prop))

    # Exchange rates, weekly means
    currencies = [s for s in sources if s in ("EUR", "USD")]
    if currencies:
        table = table.join(load_exchange_rates(f"{start_year}-01-01", f"{end_year}-12-31")[currencies])
    return table


def future_sources(train, future_dates, sources, hold_last=("EUR", "USD")):
    """Values of the sources for the weeks being forecast, using only what is known in advance.

    Weather: the average for that week of the year in the training data.
    Exchange rates (hold_last): the last known value.
    """
    # Week of the year for each date (week 53 is treated as week 52)
    week = lambda index: index.isocalendar().week.clip(upper=52).to_numpy()

    # Average per week of the year in the training data, looked up for the future dates
    seasonal = train[sources].groupby(week(train.index)).mean()
    future = seasonal.reindex(week(future_dates)).set_axis(future_dates).fillna(train[sources].mean())

    # Exchange rates have no yearly pattern, so the last known value is used instead
    for name in sources:
        if name in hold_last:
            future[name] = train[name].iloc[-1]
    return future


@st.cache_data(show_spinner="Training the forecast model...")
def forecast_ahead(table, train_end, years, horizon, sources=(), p=2, d=0, q=0, sp=1, sd=1, sq=0,
                   lr=0.001, target="Filling"):
    """Train a River SNARIMAX model on the weeks up to train_end and forecast the following weeks.

    App version of forecast_filling in the Assignment 4 notebook: that one tests against hidden weeks,
    while this one forecasts the weeks after a chosen month.
    The forecast is dynamic: each week ahead is built on the model's own earlier predictions.
    table: weekly table with the filling and any source columns, indexed by Sunday dates
    train_end: last date the model may learn from (the end of the chosen month)
    years: number of years of training data before train_end
    horizon: number of weeks to forecast
    sources: names of the columns used as exogenous variables
    p, d, q, sp, sd, sq: model settings; the season is fixed at 52 weeks
    lr: learning rate for the regression's SGD optimizer; 0.001 kept the forecast stable in the notebook tests
    Returns the training series, the forecast, and the actual filling for the forecast weeks where known.
    """
    # Imported here rather than at the top, so pages without forecasting load faster
    from river import time_series, linear_model, optim, preprocessing

    sources = list(sources)

    # Training data: the chosen number of years up to train_end, with no missing values
    train = table[:train_end].dropna()
    train = train[train.index > train.index[-1] - pd.DateOffset(years=years)]
    future_dates = pd.date_range(train.index[-1] + pd.Timedelta(weeks=1), periods=horizon, freq="W-SUN")

    model = time_series.SNARIMAX(
        p=p, d=d, q=q, m=52, sp=sp, sd=sd, sq=sq,
        regressor=preprocessing.StandardScaler() | linear_model.LinearRegression(optimizer=optim.SGD(lr)),
    )

    if sources:
        # Learning one week at a time, with that week's source values as extra inputs
        for y, x in zip(train[target], train[sources].to_dict("records")):
            model.learn_one(y, x)
        future = future_sources(train, future_dates, sources).to_dict("records")
    else:
        for y in train[target]:
            model.learn_one(y)
        future = None

    forecast = pd.Series(model.forecast(horizon=horizon, xs=future), index=future_dates)

    # The real filling for the forecast weeks, where it is already published
    actual = table[target].reindex(future_dates).dropna()
    return train[target], forecast, actual


def forecast_animation(history, forecast, actual, title):
    """Plotly animation: the last two years of history, then the forecast drawn one week at a time."""
    history = history[history.index > history.index[-1] - pd.DateOffset(years=2)]
    fig = go.Figure([
        go.Scatter(x=history.index, y=history, mode="lines", name="Filling (training data)",
                   line=dict(color=PLOT_COLORS["series"], width=2)),
        go.Scatter(x=actual.index, y=actual, mode="lines", name="Actual filling",
                   line=dict(color=PLOT_COLORS["limits"], width=2, dash="dot")),
        go.Scatter(x=forecast.index[:1], y=forecast.iloc[:1], mode="lines+markers", name="Forecast",
                   line=dict(color=PLOT_COLORS["highlight"], width=3), marker=dict(size=5)),
    ])

    # One frame per forecast week; each frame only updates the forecast line (trace 2)
    fig.frames = [go.Frame(data=[go.Scatter(x=forecast.index[:k], y=forecast.iloc[:k])], traces=[2], name=str(k))
                  for k in range(1, len(forecast) + 1)]

    # Fixed axes, so the chart doesn't jump while the animation plays
    all_y = pd.concat([history, forecast, actual])
    fig.update_layout(
        title=title, height=500, xaxis_title="Week", yaxis_title="Filling (%)",
        xaxis=dict(range=[history.index[0], forecast.index[-1] + pd.Timedelta(weeks=2)]),
        yaxis=dict(range=[max(0, all_y.min() - 5), min(100, all_y.max() + 5)]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        updatemenus=[dict(type="buttons", showactive=False, x=0, y=-0.15, xanchor="left", buttons=[
            dict(label="Play", method="animate",
                 args=[None, dict(frame=dict(duration=120, redraw=False), transition=dict(duration=0), fromcurrent=True)]),
            dict(label="Pause", method="animate",
                 args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")])])],
        sliders=[dict(x=0.12, y=-0.15, len=0.88, currentvalue=dict(prefix="Weeks ahead: "),
                      steps=[dict(label=str(k), method="animate",
                                  args=[[str(k)], dict(frame=dict(duration=0, redraw=False), mode="immediate")])
                             for k in range(1, len(forecast) + 1)])],
    )
    return fig


def month_slider(container, label, months, key):
    """Month slider whose value is shared between pages, so the map and the forecast use the same month."""
    def store():
        # Saving the chosen month where every page can read it
        st.session_state["shared_month"] = st.session_state[key]

    current = st.session_state.get("shared_month", months[-1])
    return container.select_slider(label, options=months, value=current if current in months else months[-1],
                                   key=key, on_change=store)

# Creating a function to remove slow variations from a time series using the Discrete Cosine Transform (DCT).
def dct_highpass(series, cutoff_days=30):
    """Remove variation slower than cutoff_days using the Discrete Cosine Transform."""

    # Imported here rather than at the top, so pages without the DCT load faster
    from scipy.fft import dct, idct

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
# Cached: the DCT filter on a year of hourly data only reruns when the data or a setting changes
@st.cache_data(show_spinner="Finding outliers with SPC...")
def spc_outliers(series, cutoff_days=30, n_std=3.0, label="Temperature (°C)", title="Temperature outliers"):
    """Find outliers with SPC limits based on robust statistics of the SATV.

    series: hourly values with a time index.
    cutoff_days: variation slower than this counts as seasonal.
    n_std: number of robust standard deviations from the median to the limits.
    Returns the figure and a dictionary with a summary and a table of the outliers.
    label: name and unit of the series, shown on the y-axis and in the legend.
    title: title of the plot.
    """

    # Imported here rather than at the top, so pages without SPC load faster
    from scipy.stats import median_abs_deviation    

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

# Cached: LOF on about 8,760 hourly points is the slowest analysis in the app
@st.cache_data(show_spinner="Detecting anomalies with LOF...")
def lof_anomalies(series, proportion=0.01, n_neighbors=20, label="Temperature (°C)", title="Temperature anomalies"):
    """Find anomalies in a time series with the Local Outlier Factor method.

    series: hourly values with a time index.
    proportion: share of the points to mark as anomalies.
    n_neighbors: number of neighbours each point is compared with.
    Returns the figure and a dictionary with a summary and a table of the anomalies.
    label: name and unit of the series, shown on the y-axis and in the legend.
    title: title of the plot.
    """

    # Imported here rather than at the top; scikit-learn is slow to import and only needed for LOF
    from sklearn.neighbors import LocalOutlierFactor

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

# Cached: the STL decomposition only reruns when the series or a setting changes
@st.cache_data(show_spinner="Running the STL decomposition...")
def plot_stl(series, period=52, seasonal=13, trend=None, robust=True, title ="STL decomposition of weekly reservoir filling"):
    """Plot an STL decomposition of a weekly series.

    series: weekly values with a time index and no gaps.
    period: number of samples per seasonal cycle.
    seasonal: seasonal smoother length in weeks, must be odd and at least 7.
    trend: trend smoother length, must be odd. None lets STL choose from the other settings.
    robust: reduces the influence of unusual weeks when True.
    Returns the figure.
    """

    # Imported here rather than at the top; statsmodels is slow to import and only needed for STL
    from statsmodels.tsa.seasonal import STL

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

# Cached: the spectrogram only reruns when the series or a window setting changes
@st.cache_data(show_spinner="Computing the spectrogram...")
def plot_spectrogram(series, window_length=104, window_overlap=78, title="Spectrogram of reservoir filling"):
    """Plot a spectrogram of a weekly series.

    series: weekly values with a time index and no gaps.
    window_length: number of weeks in each window.
    window_overlap: number of weeks shared by neighbouring windows.
    Returns the figure.
    """

    # Imported here rather than at the top, so pages without the spectrogram load faster
    from scipy.signal import spectrogram

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

    # Power in decibels; 1e-12 avoids taking the log of zero
    power_db = 10 * np.log10(power + 1e-12)

    # Colour range from the frequencies shown by default (0–6 cycles per year), so the colours
    # spread over what is visible. Plotly needs both zmin and zmax for a custom range.
    shown = frequencies <= 6
    zmin, zmax = np.percentile(power_db[shown], 5), power_db[shown].max()

    fig = go.Figure(go.Heatmap(
        x=window_centers, y=frequencies, z=power_db, zmin=zmin, zmax=zmax,
        colorscale=SPECTROGRAM_SCALE, colorbar=dict(title="Power (dB)"),
        hovertemplate="%{x|%Y-%m}<br>%{y:.2f} cycles per year<br>%{z:.1f} dB<extra></extra>",
    ))
    # Showing 0–6 cycles per year by default, where the seasonal signal is; zoom out to see the rest
    fig.update_layout(title=title, xaxis_title="Year", yaxis_title="Frequency (cycles per year)",
                      yaxis_range=[0, 6], height=450)

    # Returning the figure
    return fig