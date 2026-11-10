import pandas as pd
import streamlit as st
from utils import filling_series, load_data, plot_spectrogram, plot_stl

# Naming the page
st.title("STL and Spectrogram Analysis")

# Filling data exists for all area types, so this page needs no NO guard
area_type = st.session_state["area_type"]
area_nr = st.session_state["area_nr"]

# Writing which area type and number is shown
st.write(f"Showing reservoir filling for {area_type} {area_nr}.")

# Calling the load_data function from utils.py
data, _, _ = load_data(pd.Period("1995-01", "M"), pd.Period.now("M"))
# Calling the filling_series_function from data for the given area type and number
filling = filling_series(data, area_type, area_nr)

# Defining the two tabs of the page, rerunning the page when clicked
tab1, tab2 = st.tabs(["STL Analysis", "Spectrogram Analysis"], on_change="rerun")

# Defining what happens in tab 1 (STL Analysis)
if tab1.open:
    with tab1:
        seasonal = st.slider("Seasonal smoother (weeks)", 7, 53, 13, step=2)
        robust = st.toggle("Robust fitting", value=True)
        trend = st.slider("Trend smoother (weeks)", 53, 261, 89, step=2)
        st.pyplot(plot_stl(filling, seasonal=seasonal, trend=trend, robust=robust))   

# Defining what happens in tab 2 (Spectrogram analysis)
if tab2.open:
    with tab2:
        # User can choose the window length
        window_length = st.slider("Window length (weeks)", 26, 208, 104, step=26)
        # User can define the overlap
        window_overlap = st.slider("Window overlap (weeks)", 0, window_length - 1, window_length * 3 // 4,
                                   help="Default is 75% of the window, so a new window starts every quarter window length.")
        # Displaying the plot using the plot_spectrogram function from utils.py
        st.pyplot(plot_spectrogram(filling, window_length, window_overlap))