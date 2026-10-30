import streamlit as st
import plotly.express as px
import pandas as pd
from aco_sim.model import REGIONS,SPECIALTIES,RESOURCES,catalogue,make_population,make_agents,simulate
st.set_page_config(page_title='Saudi ACO Supply–Demand Prototype',layout='wide')
st.title('Saudi ACO population, pathway and capacity simulation')
st.warning('Research prototype. Population, resource supply and care-use coefficients are SYNTHETIC and NOT verified MOH/GASTAT figures. Do not use for investment or clinical decisions.')
with st.sidebar:
 specialty=st.selectbox('Specialty',SPECIALTIES)
 resource=st.selectbox('Resource',RESOURCES)
 year=st.slider('Forecast year',2025,2054,2025)
 integrated=st.checkbox('ACO integrated-care scenario',True)
 seed=st.number_input('Random seed',0,100000,42)
@st.cache_data(show_spinner=False)
def run(y,care,s):
 pop=make_population(s); agents=make_agents(pop,seed=s)
 return simulate(agents,y,care,s)
df=run(year,integrated,int(seed)); subset=df[(df.Specialty==specialty)&(df.Resource==resource)]
st.subheader(f'{specialty} — {resource} gap per 1,000 people, {year}')
# National geographic point map with region labels. Points are NOT administrative polygons.
coords={'Riyadh':(24.7,46.7),'Makkah':(21.4,39.9),'Madinah':(24.5,39.6),'Eastern Province':(26.4,50.1),'Qassim':(26.2,43.5),'Hail':(27.5,41.7),'Tabuk':(28.4,36.6),'Jouf':(30.0,40.9),'Northern Borders':(30.0,41.0),'Baha':(20.0,41.5),'Assir':(18.2,42.5),'Najran':(17.5,44.1),'Jizan':(16.9,42.6)}
subset=subset.copy();subset['lat']=subset.Region.map(lambda x:coords[x][0]);subset['lon']=subset.Region.map(lambda x:coords[x][1])
fig=px.scatter_map(subset,lat='lat',lon='lon',color='Gap_per_1k',size='Population',hover_name='Region',hover_data=['Demand_per_1k','Supply_per_1k','Gap_per_1k'],color_continuous_scale='RdYlGn_r',zoom=4,center={'lat':24,'lon':45},height=560)
fig.update_layout(map_style='open-street-map',margin=dict(l=0,r=0,t=0,b=0));st.plotly_chart(fig,use_container_width=True)
st.caption('Map markers show approximate regional reference points, not verified administrative boundaries.')
left,right=st.columns(2)
with left:
 st.plotly_chart(px.bar(subset,x='Region',y=['Demand_per_1k','Supply_per_1k'],barmode='group',title='Demand and supply per 1,000'),use_container_width=True)
with right:
 mat=df[df.Resource==resource].pivot(index='Region',columns='Specialty',values='Gap_per_1k')
 st.plotly_chart(px.imshow(mat,aspect='auto',color_continuous_scale='RdBu_r',color_continuous_midpoint=0,title='Gap by region and specialty'),use_container_width=True)
st.subheader('All simulated outputs');st.dataframe(df,use_container_width=True)
st.download_button('Download all results (CSV)',df.to_csv(index=False).encode(),file_name='aco_simulation_synthetic.csv')
with st.expander('Reference IPU and pathway catalogue (Annex K)'):
 st.dataframe(catalogue(),use_container_width=True)
with st.expander('Model limitations and assumptions'):
 st.write('This version implements weighted synthetic person agents and stochastic episode generation. The queue proxy is not yet a full SimPy event-calendar DES. Regional supply, actual ACO attribution, pathway rates, provider network and clinical outcomes require verified input data. Specialty-to-IPU mappings are illustrative, not exhaustive clinical crosswalks. No DALY or value-based outcome benefit is claimed.')
