import streamlit as st

st.title("Reservoir Forecasting")
st.write("Here you can perform forecasting on for instance reservoir filling.")

# Temporary test: does clicking an area on a Plotly map return a selection in Streamlit?
import json
import plotly.graph_objects as go
import streamlit as st

# Reading the VASS areas, the smallest of the GeoJSON files
with open("data/vass_areas.geojson", encoding="utf-8") as f:
    geojson = json.load(f)
areas = [feature["properties"]["area"] for feature in geojson["features"]]

# One coloured area per VASS area, matched to the GeoJSON by its "area" property
fig = go.Figure(go.Choroplethmap(
    geojson=geojson, featureidkey="properties.area",
    locations=areas, z=list(range(len(areas))),
    customdata=areas, colorscale="Blues", marker_opacity=0.5,
    hovertemplate="%{customdata}<extra></extra>",
))
fig.update_layout(map_style="carto-darkmatter", map_center={"lat": 65, "lon": 15}, map_zoom=3.3,
                  height=600, margin=dict(l=0, r=0, t=0, b=0))

# on_select="rerun" makes Streamlit rerun the script and return what was clicked
event = st.plotly_chart(fig, on_select="rerun", selection_mode="points")
st.write(event)