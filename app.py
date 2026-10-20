import streamlit as st


def home():
    st.title("IND320 Streamlit app")
    st.write("""In this Streamlit-app, you can visualize water reservoir data from NVE Magasinstatistikk API 
    and Cross-border electricity flow data from ENTSO-E Transparency Platform API.""")

    col1 ,col2, col3 = st.columns(3)

    with col1:
        if st.button("Go to Plots Page"):
            st.switch_page("pages/plots.py")
    with col2:
        if st.button("Go to Imported Data Table"):
            st.switch_page("pages/plots.py")
    with col3:
        if st.button("Flows"):
            st.switch_page("pages/flows.py")

pages = [
    st.Page(home, title="Home Page"),
    st.Page("pages/plots.py", title="Plots"),
    st.Page("pages/tables.py", title="Tables"),
    st.Page("pages/flows.py",title = "Connection Flows"),
]

page = st.navigation(pages)
page.run()