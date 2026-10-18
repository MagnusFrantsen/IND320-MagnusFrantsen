import streamlit as st
import pandas as pd
from pymongo import MongoClient

# Cache the client so it's created once, not on every rerun
@st.cache_resource
def get_client():
    return MongoClient(st.secrets["mongo"]["uri"])

# Cache query results for 1 day minutes to avoid hitting the DB limit
@st.cache_data(ttl="1d")
def load_data(db_name, coll_name, query=None):
    coll = get_client()[db_name][coll_name]
    docs = list(coll.find(query or {}, {"_id": 0}))  # drop _id (ObjectId breaks st.dataframe)
    return pd.DataFrame(docs)

st.title("ENTSO-E Data")

with st.expander("Read more about this page"):
    st.write("This page is plotting data of cross border flow from and to Norway. The data comes from the ENTSO-E API.")

