import streamlit as st
from utils import load_data

st.title("Analytics Page")
st.write("This page has a plot of the imported data, a drop-down menu and a slider for user input.")

df = load_data()
number_input = st.number_input("Enter a number:", key="number_input")
st.write(f"You entered: {number_input}")