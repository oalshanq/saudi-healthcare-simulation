
import pandas as pd
import numpy as np

def run_simulation(region, specialty):
    years = list(range(2025, 2055))
    data = []
    for year in years:
        demand = np.random.randint(2000, 9000)
        beds = int(demand * 0.01)
        physicians = int(demand * 0.02)
        nurses = int(demand * 0.03)
        data.append({
            "Region": region,
            "Specialty": specialty,
            "Year": year,
            "Demand": demand,
            "Beds": beds,
            "Physicians": physicians,
            "Nurses": nurses
        })
    return pd.DataFrame(data)

