import streamlit as st
import pandas as pd
import plotly.express as px # Suggested library by AI model Claude Opus 5.5
from pymongo import MongoClient

# Cache the client so it's created once, not on every rerun
@st.cache_resource
def get_client():
    return MongoClient(st.secrets["mongo"]["uri"])

# Cache query results for 1 day to avoid hitting the DB limit
@st.cache_data(ttl="1d")
def load_data(db_name, coll_name, query=None):
    coll = get_client()[db_name][coll_name]
    docs = list(coll.find(query or {}, {"_id": 0}))  # drop _id (ObjectId breaks st.dataframe)
    return pd.DataFrame(docs)

# Creating a title/header for the page
st.title("ENTSO-E Data")

# Creating a pandas dataframe named df from load_data()
df = load_data("ind320","crossborder_flow")

# Converting the time column to datetime using to_datetime and extracting the year and month into separate columns.
# Used later for filtering on the selected year and months
df["time"] = pd.to_datetime(df["time"])
df["year"] = df["time"].dt.year
df["month"] = df["time"].dt.month

# Checking if the data was loaded during development of the page
# st.write(df.head())

# Creating the two columns in the page for the different plots
left, right = st.columns(2)

# Creating a list of months throughout the year used in the pills-filtering
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Creating the content inside the left column
with left:

    # Creating a header for the left column
    st.header("Piechart of Total Flow")
    
    # Putting the radio buttons inside an expander for better user experience
    with st.expander("Choose connection here"):
        
        # Creating radio buttons to select a connection. 
        connection = st.radio("Connection", sorted(df["connection"].unique()))

    st.write(f"Selected connection: {connection}")
    # Creating a selectbox to choose which year the piechart is showing for
    year = st.selectbox("Year", sorted(df["year"].unique()))

    # Rows for the chosen connection and year
    sub = df[(df["connection"] == connection) & (df["year"] == year)]

    # Sum MW per direction for the whole year
    totals = sub.groupby("direction")["mw"].sum().reset_index()

    # Creating the piechart
    fig_pie = px.pie(totals, names="direction", values="mw",
                     title=f"{connection} – total flow {year}")

    # Making sure the piechart is shown in the Streamlit app
    st.plotly_chart(fig_pie)

# Creating the content inside the right column
with right:

    # Creating a header for the right column
    st.header("Line Chart of Flow")

    # Because of the width of the column the pills are divided into two rows to 
    # make every month showing at the same time

    # Creating the first line of the options available
    first_half = st.pills("Months", months[:6], selection_mode="multi",
                      default=["Jan"], key="months_h1")

    # Creating the second line of the options available
    second_half = st.pills("Months (Jul–Dec)", months[6:], selection_mode="multi",
                       key="months_h2", label_visibility="collapsed")

    # Adding them together to make it work as options
    chosen = first_half + second_half

    # Converting the chosen month names from st.pills (e.g. "Jan", "Mar") to month numbers (1-12),
    # using each name's position in the months list (index 0 = "Jan" -> 1)
    month_nums = [months.index(m) + 1 for m in chosen]
     
    # Only keeping the rows in the subset where the month number matches one of the chosen months
    month_df = sub[sub["month"].isin(month_nums)]

    # Finding which of the selected months have no rows for this connection and year

    # Collecting the month numbers that actually have data in the filtered dataframe
    found = set(month_df["month"].unique())

    # Going through the chosen month numbers and keeping those without data,
    # converting each back to its name (e.g. 3 -> "Mar") using its position in the months list
    missing = [months[m - 1] for m in month_nums if m not in found]

    # Creating feedback based on selections made in the pills for better user experience

    # Feedback if no month is chosen
    if not chosen:
        st.info("Select one or more months to show the plot.")

    # Feedback if month chosen has no data if there is only missing data
    elif month_df.empty:
        st.info(f"No data for {', '.join(missing)} {year}.")

    # What happens if the months chosen have data
    else:
        if missing:
            # Feedback if the months chosen are both with and without data
            st.warning(f"No data for {', '.join(missing)} {year}. "
                       "Showing the other selected month(s).")
        # Collecting the data piece by piece, so a gap can be inserted between each month
        # to avoid having lines shown between months apart if the months between them are not chosen
        # This means there will only be a gap in the plot if there are months chosen with one or more
        # months that are not selected from st.pills
        parts = []

        # Sorting by time and grouping by direction and month, so each group is one continuous line segment
        for (direction, month), g in month_df.sort_values("time").groupby(["direction", "month"]):

            # Adding the actual hourly data for this direction and month
            parts.append(g)
            # Adding an empty row one hour after the month ends, so Plotly breaks the line here
            # instead of drawing a straight line across the gap to the next selected month
            parts.append(pd.DataFrame({
                "time": [g["time"].max() + pd.Timedelta(hours=1)],
                "mw": [None],
                "direction": [direction],
            }))
        # Combining all the month segments and gap rows into one dataframe for plotting (method suggested by AI)
        plot_df = pd.concat(parts)

        # Creating a line plot of the hourly flow, with one line (colour) per direction 
        fig_line = px.line(plot_df, x="time", y="mw", color="direction",
                        title=f"{connection} – hourly flow")

        # Displaying the Plotly figure in the Streamlit app
        st.plotly_chart(fig_line)

# Documentation of the data source
with st.expander("Read more about this page"):
    st.write(
        """This page plots cross-border electricity flow to and from Norway. 
        The data comes from the ENTSO-E Transparency Platform API, was stored 
        in Cassandra, filtered with Spark, and saved to MongoDB, which this app reads from.
        The data downloaded is for the period 16. October 2024 to 16. October 2026 
        (last two years from when the download was done)."""
    )