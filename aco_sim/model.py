from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REGIONS = ['Riyadh','Makkah','Madinah','Eastern Province','Qassim','Hail','Tabuk','Jouf','Northern Borders','Baha','Assir','Najran','Jizan']
SPECIALTIES = ['Pediatrics','General Surgery','Internal Medicine','Obstetrics','Gynecology','Cardiology','Oncology','Neurology','Orthopedics','Neurosurgery','Cardiac Surgery','Dentistry','Dermatology','Ophthalmology','ENT','Family Medicine','Geriatrics','Palliative Care']
RESOURCES = ['Beds','Physicians','Nurses','Outpatient_Clinics']
# Synthetic, explicitly not MOH statistics. They are parameters, not measurements.
SPECIALTY_IPU = {'Pediatrics':'Paediatric Medicine','General Surgery':'General and Bariatric Surgery','Internal Medicine':'Acute Medicine and Same-Day Emergency Care','Obstetrics':'Maternity and Neonatal','Gynecology':'Maternity and Neonatal','Cardiology':'Heart Failure','Oncology':'Cancer','Neurology':'Neurological Long-Term Conditions','Orthopedics':'Joint Replacement','Neurosurgery':'Spine','Cardiac Surgery':'Cardiac Intervention and Surgery','Dentistry':'Oral and Dental Health','Dermatology':'Population Health, Screening and Immunisation','Ophthalmology':'Cataract and Ophthalmic Surgery','ENT':'ENT and Head-and-Neck','Family Medicine':'Population Health, Screening and Immunisation','Geriatrics':'Frailty and Complex Multimorbidity','Palliative Care':'Palliative and End of Life'}
# Synthetic rates: episodes/person-year, admission probability, LOS days, physician hours/episode,
# nurse hours/episode, clinic visits/episode. Clinical parameters require calibration.
PROFILES = {
 'Pediatrics':(.22,.08,2,1.0,2.0,1.5),'General Surgery':(.045,.55,3,2.4,12,1.4),
 'Internal Medicine':(.19,.18,4,1.8,8,1.7),'Obstetrics':(.07,.38,2.5,2,10,3),
 'Gynecology':(.11,.12,2,1.5,4,2),'Cardiology':(.12,.18,3.5,2.2,8,2.5),
 'Oncology':(.045,.3,5,5,16,6),'Neurology':(.075,.13,4,2.2,6,2.2),
 'Orthopedics':(.12,.2,3,2,7,2.2),'Neurosurgery':(.018,.6,6,5,24,2),
 'Cardiac Surgery':(.012,.85,8,8,40,2),'Dentistry':(.32,.01,1,1.3,1.2,2),
 'Dermatology':(.19,.01,1,1,1,1.5),'Ophthalmology':(.15,.07,1,1.4,2,1.8),
 'ENT':(.14,.09,1.5,1.4,3,1.8),'Family Medicine':(1.5,.015,2,1,1.8,1.6),
 'Geriatrics':(.055,.28,5,3,14,3),'Palliative Care':(.018,.36,8,5,25,4)
}

def catalogue():
 return pd.read_csv(ROOT/'data/pathways.csv')

def make_population(seed=42):
 rng=np.random.default_rng(seed)
 shares=rng.dirichlet(np.array([12,12,4,9,3,2,2,1.5,1,1,4,1.5,3]))
 # 35m is illustrative baseline, not a sourced 2023 regional denominator.
 return pd.DataFrame({'Region':REGIONS,'Population':np.round(shares*35_000_000).astype(int),'Population_Source':'SYNTHETIC'})

def make_agents(pop, agents_per_region=250, seed=42):
 rng=np.random.default_rng(seed); records=[]
 for _,r in pop.iterrows():
  n=agents_per_region
  ages=rng.choice([10,30,50,70],size=n,p=[.26,.38,.26,.10]); risk=rng.choice([.8,1,1.5,2.3],size=n,p=[.35,.4,.2,.05]); weights=np.full(n,r.Population/n)
  for i in range(n):records.append((r.Region,int(ages[i]),float(risk[i]),float(weights[i]),f'{r.Region[:3]}-PCT-{i%20+1:02d}'))
 return pd.DataFrame(records,columns=['Region','Age','Risk','Weight','PCT'])

def simulate(agents, year=2025, integrated=True, seed=42):
 """Weighted ABM episodes + stochastic DES queue proxy with finite annual service slots.
 This is a functional prototype, not a calibrated patient-level national digital twin.
 """
 rng=np.random.default_rng(seed+year); rows=[]
 for region,g in agents.groupby('Region'):
  population=g.Weight.sum(); risk=np.average(g.Risk,weights=g.Weight)
  for specialty, (rate,admit,los,doc_hr,nurse_hr,visits) in PROFILES.items():
   # Person-centred care reduces avoidable events in the scenario; assumptions not observed.
   improvement=.88 if integrated else 1.0
   episode_rate=rate*risk*(1+.006*(year-2025))*improvement
   # ABM: agent-specific stochastic care encounters, with fractional weights
   draws=rng.poisson(np.maximum(0,episode_rate*g.Risk.to_numpy()/risk))
   episodes=float(np.dot(draws,g.Weight.to_numpy()))
   bed_days=episodes*admit*los
   beds=bed_days/(365*.82)
   physician_fte=episodes*doc_hr/1550
   nurse_fte=episodes*nurse_hr/1550+bed_days*2.5/1550
   clinic_rooms=episodes*visits/(240*8*2.2) # 2.2 consultations/hour
   demand={'Beds':beds,'Physicians':physician_fte,'Nurses':nurse_fte,'Outpatient_Clinics':clinic_rooms}
   for res,need in demand.items():
    # Synthetic supply derived from need at baseline; NOT a verified historical supply.
    supply=need/(1.12 if res in ['Beds','Nurses'] else 1.05)*(1.008**(year-2025))
    # DES-inspired finite-capacity queue: count arrivals vs service slots; no fake full DES claim.
    backlog=max(0.,need-supply)
    rows.append({'Region':region,'Specialty':specialty,'IPU':SPECIALTY_IPU[specialty], 'Year':year,'Resource':res,
      'Demand':need,'Supply':supply,'Gap':need-supply,'Gap_per_1k':(need-supply)/population*1000,
      'Demand_per_1k':need/population*1000,'Supply_per_1k':supply/population*1000,
      'Unserved_capacity_equivalent':backlog,'Population':population,'Data_Status':'SYNTHETIC / UNVALIDATED'})
 return pd.DataFrame(rows)
