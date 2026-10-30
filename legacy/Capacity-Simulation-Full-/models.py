
import pandas as pd
import numpy as np

def load_real_supply_data():
    return pd.read_csv("real_supply_data.csv")

def run_des_simulation(df_supply, specialty):
    df = []
    for _, row in df_supply.iterrows():
        modifier = hash(specialty) % 5 * 0.05 + 0.95
        demand = {
            "Beds": 2.5 * modifier,
            "Nurses": 6.0 * modifier,
            "Clinics": 1.2 * modifier,
            "Physicians": 3.3 * modifier
        }
        gap = (demand["Beds"] - row["Beds_per_1k"]) + (demand["Nurses"] - row["Nurses_per_1k"]) +               (demand["Clinics"] - row["Clinics_per_1k"]) + (demand["Physicians"] - row["Physicians_per_1k"])
        df.append({
            "Region": row["Region"],
            "Gap": round(gap, 2)
        })
    return pd.DataFrame(df)

def run_abm_simulation(df_supply, specialty):
    df = []
    for _, row in df_supply.iterrows():
        np.random.seed(42)
        modifier = hash(specialty) % 7 * 0.05 + 0.90
        multiplier = np.random.uniform(0.98, 1.03)
        demand = {
            "Beds": 2.5 * modifier * multiplier,
            "Nurses": 6.0 * modifier * multiplier,
            "Clinics": 1.2 * modifier * multiplier,
            "Physicians": 3.3 * modifier * multiplier
        }
        gap = (demand["Beds"] - row["Beds_per_1k"]) + (demand["Nurses"] - row["Nurses_per_1k"]) +               (demand["Clinics"] - row["Clinics_per_1k"]) + (demand["Physicians"] - row["Physicians_per_1k"])
        df.append({
            "Region": row["Region"],
            "Gap": round(gap, 2)
        })
    return pd.DataFrame(df)

def calculate_gap_map_data(df_results):
    return df_results

