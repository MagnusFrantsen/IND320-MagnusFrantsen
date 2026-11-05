import streamlit as st

# Creating the title and description for the STL analysis page.
st.title("STL Analysis")
st.write("This is a simple STL analysis page.")

tab1, tab2 = st.tabs(["STL Analysis", "Spectrogram Analysis"], on_change="rerun")

if tab1.open:
    with tab1:
        st.write("This is the STL analysis tab.")
        # Add your STL analysis code here

if tab2.open:
    with tab2:
        st.write("This is the Spectrogram analysis tab.")
        # Add your Spectrogram analysis code here