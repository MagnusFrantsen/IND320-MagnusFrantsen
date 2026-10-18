import streamlit as st


def home():
    st.title("Home Page")
    st.write("This is the home page of the app.")
    st.write("In this app, you can perform various data analytics tasks and visualize the results.")

    col1 ,col2, col3 = st.columns(3)

    with col1:
        if st.button("Go to Plots Page"):
            st.switch_page("pages/plots.py")
    with col2:
        if st.button("Go to Imported Data Table"):
            st.switch_page("pages/plots.py")
    with col3:
        if st.button("Go to ENTSO-E data"):
            st.switch_page("pages/dummy_page.py")

pages = [
    st.Page(home, title="Home Page"),
    st.Page("pages/plots.py", title="Plots"),
    st.Page("pages/table_imported_data.py", title="Imported Data Table"),
    st.Page("pages/dummy_page.py",title = "ENTSO-E"),
]

page = st.navigation(pages)
page.run()