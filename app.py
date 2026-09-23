import streamlit as st


def home():
    st.title("Home Page")
    st.write("This is the home page of the app.")
    st.write("In this app, you can perform various data analytics tasks and visualize the results.")
    if st.button("Go to Analytics Page"):
        st.switch_page("pages/Analytics.py")

pages = [
    st.Page(home, title="Home Page"),
    st.Page("pages/plots.py", title="Plots"),
    st.Page("pages/table_imported_data.py", title="Imported Data Table"),
    st.Page("pages/dummy_page.py",title = "Dummy Page"),
]

page = st.navigation(pages)
page.run()