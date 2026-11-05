import pandas as pd
import streamlit as st
from utils import filling_series, load_data, plot_spectrogram, plot_stl

st.title("STL and Spectrogram Analysis")

# Filling data exists for all area types, so this page needs no NO guard
area_type = st.session_state["area_type"]
area_nr = st.session_state["area_nr"]

st.write(f"Showing reservoir filling for {area_type} {area_nr}.")

data, _, _ = load_data(pd.Period("1995-01", "M"), pd.Period.now("M"))
filling = filling_series(data, area_type, area_nr)

tab1, tab2 = st.tabs(["STL Analysis", "Spectrogram Analysis"], on_change="rerun")

if tab1.open:
    with tab1:
        seasonal = st.slider("Seasonal smoother (weeks)", 7, 53, 13, step=2)
        robust = st.toggle("Robust fitting", value=True)
        trend = st.slider("Trend smoother (weeks)", 53, 261, 89, step=2)
        st.pyplot(plot_stl(filling, seasonal=seasonal, trend=trend, robust=robust))   

if tab2.open:
    with tab2:
        window_length = st.slider("Window length (weeks)", 26, 208, 104, step=26)
        window_overlap = st.slider("Window overlap (weeks)", 0, window_length - 1, window_length * 3 // 4)
        st.pyplot(plot_spectrogram(filling, window_length, window_overlap))