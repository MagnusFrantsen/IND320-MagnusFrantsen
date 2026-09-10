import streamlit as st

st.title("Min første Streamlit-app 🚀")
st.write("Hei! Hvis du ser dette, fungerer alt som det skal.")

# Enkel interaktiv komponent for å sjekke at alt reagerer
navn = st.text_input("Hva heter du?")
if navn:
    st.success(f"Velkommen til appen, {navn}!")

sted = st.text.input("Hvor er du?")
if sted:
    st.success(f"Du er i {sted}!")