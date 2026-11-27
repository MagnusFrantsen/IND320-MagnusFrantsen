# IND320 Project Work

Repository for assignments in IND320 Fall 2026, including Jupyter notebooks, the Streamlit app, requirements files and explanation videos.

**Streamlit app:** https://ind320-magnusfrantsen.streamlit.app/

## Data sources
- **NVE Magasinstatistikk API** – weekly reservoir levels for Norway (area types NO, EL and VASS)
- **ENTSO-E Transparency Platform API** – hourly physical cross-border electricity flows to and from Norway (16 Oct 2024 – 16 Oct 2026)
- **MongoDB Atlas** – stores the cross-border flow data (written from the notebook, read by the Streamlit app)
- **NVE Atlas** – shapefiles for the price areas and water areas, used to sample weather locations and to draw the map
- **Open-Meteo API** – hourly historical reanalysis weather data from the ERA5 model
- **Norges Bank API** – daily EUR and USD exchange rates in NOK, used in the reservoir forecast

## App pages
- **Home** – interactive map of the areas; clicking an area selects it for every page
- **Explore** – reservoir filling (plots and tables) and cross-border electricity flows
- **Analyze** – STL and spectrogram, weather outliers and anomalies (SPC and LOF), and sliding window correlation
- **Forecast** – reservoir filling forecast with River's SNARIMAX, shown as a Plotly animation

## Folder structure
- **IND320/**
  - **.streamlit/**
    - config.toml
  - **data/**
    - shapefiles/
    - locations.csv
    - map_price_areas.geojson
    - map_vass_areas.geojson
    - map_norway_areas.geojson
    - NO3_2024_hourly.csv
  - **images/**
    - Streamlit_app_sketch.png
  - **Notebooks/**
    - Assignment 1.ipynb
    - Assignment 2.ipynb
    - Assignment 3.ipynb
    - Assignment 4.ipynb
  - **pages/**
    - plots.py
    - flows.py
    - stl_analysis.py
    - outlier_and_anomaly.py
    - correlation.py
    - reservoir_forecast.py
  - **Videos/**
    - IND320_Project_Work_Part_1.mp4
    - IND320_Project_Work_Part_2.mp4
    - IND320_Project_Work_Part_3.mp4
    - IND320_Project_Work_Part_4.mp4
  - .gitignore
  - app.py
  - utils.py
  - README.md
  - requirements.txt
  - requirements-notebooks.txt

## Running the Streamlit app locally on your computer
1. Install the app requirements: `pip install -r requirements.txt`
2. Create `.streamlit/secrets.toml` (not included in the repository) with the MongoDB connection string:
```toml
   [mongo]
   uri = "mongodb+srv://<user>:<password>@<cluster>/"
```
3. Run the app: `streamlit run app.py`

## Running the notebooks
1. Install the notebook requirements, which include the app requirements: `pip install -r requirements-notebooks.txt`
2. Assignment 2 also requires:
   - A local Cassandra instance running on `localhost:9042`
   - Java 17 and Spark (via pyspark), plus Hadoop `winutils.exe` on Windows
   - A folder `no_sync/` in the project folder, ignored by Git, containing `entsoe_token.txt` (ENTSO-E security token) and `mongodb_uri.txt` (MongoDB connection string)