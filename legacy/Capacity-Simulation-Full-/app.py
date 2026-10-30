
import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import folium_static
from models import run_des_simulation, run_abm_simulation, load_real_supply_data, calculate_gap_map_data

st.set_page_config(page_title="Healthcare Simulation: DES + ABM", layout="wide")
st.title("Saudi Healthcare Simulation (DES + ABM) with Regional Gap Maps")

df_supply = load_real_supply_data()
regions = df_supply["Region"].unique().tolist()
specialties = ["Pediatrics", "Internal Medicine", "Cardiology", "Oncology", "Family Medicine"]

sim_type = st.sidebar.selectbox("Simulation Type", ["DES", "ABM"])
specialty = st.sidebar.selectbox("Select Specialty", specialties)

if st.sidebar.button("Run Simulation"):
    if sim_type == "DES":
        results = run_des_simulation(df_supply, specialty)
    else:
        results = run_abm_simulation(df_supply, specialty)

    st.success(f"{sim_type} simulation for {specialty} completed.")

    st.subheader("Gap Map by Region")
    gap_df = calculate_gap_map_data(results)

    sa_regions = gpd.read_file("https://raw.githubusercontent.com/datasets/geo-admin1-us/master/data/admin1-saudi.geojson")
    merged = sa_regions.merge(gap_df, left_on="name", right_on="Region", how="left")

    m = folium.Map(location=[23.8859, 45.0792], zoom_start=5)
    folium.Choropleth(
        geo_data=merged,
        data=merged,
        columns=["Region", "Gap"],
        key_on="feature.properties.name",
        fill_color="YlOrRd",
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name="Gap Index"
    ).add_to(m)

    folium_static(m)

