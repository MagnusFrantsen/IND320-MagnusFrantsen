import streamlit as st

def main():
    st.title("Front page")
    st.wrote("This is the front page of the app.")

def analytics_page():
    st.title("Analytics page")
    st.write("This is the analytics page.")

pages = {
    "Home": [
        st.Page(main,title ="Front page"),
    ],
    "Analytics": [
        st.Page(analytics_page, title="Analytics")
    ],
}

st.title("Min første Streamlit-app 🚀")
st.write("Hei! Hvis du ser dette, fungerer alt som det skal.")

# Enkel interaktiv komponent for å sjekke at alt reagerer
navn = st.text_input("Hva heter du egentlig da?")
if navn:
    st.success(f"Velkommen til appen, {navn}!")

sted = st.text_input("Where are you?")
if sted:
    st.success(f"Du er i {sted}!")