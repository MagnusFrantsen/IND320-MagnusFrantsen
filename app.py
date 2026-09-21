import streamlit as st

def main():
    st.title("Home Page")
    st.write("This is the home page of the app. You can navigate to the analytics page using the sidebar menu.")

    # Enkel interaktiv komponent for å sjekke at alt reagerer
    wish = st.text_input("What do you want to do?")
    if wish:
        st.success(f"You want to do: {wish}")

    place = st.text_input("Where are you?")
    if place:
        st.success(f"You are in {place}!")

def analytics_page():
    st.title("Analytics page")
    st.write("This is the analytics page.")

pages = {
    "Home": [
        st.Page(main,title ="Home Page"),
    ],
    "Analytics": [
        st.Page(analytics_page, title="Analytics")
    ],
}

pg = st.navigation(pages)
pg.run()