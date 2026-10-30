
import streamlit as st
import pandas as pd
import plotly.express as px
from models import run_simulation

st.set_page_config(page_title="Saudi Healthcare Simulation", layout="wide")
st.title("Saudi Arabia Healthcare Simulation Dashboard")

st.sidebar.header("Select Simulation Parameters")
region = st.sidebar.selectbox("Region", ["Riyadh", "Makkah", "Jeddah", "Dammam"])
specialty = st.sidebar.selectbox("Specialty", [
    "Cardiology", "Pediatrics", "Oncology", "Neurology", "General Surgery"
])
years = list(range(2025, 2055))

if st.sidebar.button("Run Simulation"):
    df = run_simulation(region=region, specialty=specialty)
    st.success("Simulation complete.")

    st.subheader(f"Forecast Results for {specialty} in {region}")
    fig = px.line(df, x="Year", y=["Demand", "Beds", "Physicians", "Nurses"], markers=True)
    st.plotly_chart(fig, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv, f"{region}_{specialty}_forecast.csv", "text/csv")
else:
    st.info("Click 'Run Simulation' to generate forecast.")

