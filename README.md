# IND320 Project Work

Repository for assignments in IND320 Fall 2026, including Jupyter notebooks, Streamlit app, requirements.txt file and explanation videos.

**Streamlit app:** https://ind320-magnusfrantsen.streamlit.app/

## Data sources
- **NVE Magasinstatistikk API** – weekly reservoir levels for Norway (area types NO, EL and VASS)
- **ENTSO-E Transparency Platform API** – hourly physical cross-border electricity flows to and from Norway (16 Oct 2024 – 16 Oct 2026)
- **MongoDB Atlas** – stores the cross-border flow data (written from the notebook, read by the Streamlit app)
- **NVE Atlas** – shapefiles for the electricity and precipitation areas, used to sample locations for the weather data
- **Open-Meteo API** – hourly historical reanalysis weather data from the ERA5 model, including precipitation and temperature

## Folder Structure
- **IND320/**
  - **data/**
    - shapefiles/
    - weather_cache/
    - locations.csv
    - NO3_2024_hourly.csv
  - **Notebooks/**
    - Assignment 1.ipynb
    - Assignment 2.ipynb
    - Assignment 3.ipynb
  - **pages/**
    - flows.py
    - plots.py
    - tables.py
    - outlier_and_anomaly.py
    - stl_analysis.py
  - **Videos/**
    - IND320_Project_Work_Part_1.mp4
    - IND320_Project_Work_Part_2.mp4
    - IND320_Project_Work_Part_3.mp4
  - .gitignore
  - app.py
  - utils.py
  - README.md
  - requirements.txt

## Running the Streamlit app locally on your computer
1. Install the requirements: `pip install -r requirements.txt`
2. Create `.streamlit/secrets.toml` (not included in the repository) with the MongoDB connection string:
```toml
   [mongo]
   uri = "mongodb+srv://<user>:<password>@<cluster>/"
```
3. Run the app: `streamlit run app.py`

## Running the notebooks
Assignment 2 also requires:
- A local Cassandra instance running on `localhost:9042`
- Java 17 and Spark (via pyspark), plus Hadoop `winutils.exe` on Windows
- A folder `../no_sync/` (outside the repository) containing `entsoe_token.txt` (ENTSO-E security token) and `mongodb_uri.txt` (MongoDB connection string)