"""Current dashboard; the original v0.1 app remains available unchanged."""
import runpy
import streamlit as st

st.set_page_config(page_title='Saudi ACO Annual Cluster Planning', layout='wide')
from aco_sim.presentation import style
style()
st.sidebar.markdown('<div class="brand"><small>SAUDI HEALTH SYSTEM</small><strong>ACO Planning</strong><span>Supply & demand observatory</span></div>', unsafe_allow_html=True)
view = st.sidebar.radio('View', ['Overview', 'Yearly cluster demand', 'Yearly cluster supply',
                                 'IPU coverage & gaps', 'Data & mappings', 'Regional prototype'])
if view == 'Regional prototype':
    runpy.run_path('app.py', run_name='__main__')
else:
    from aco_sim.cluster_dashboard import render
    render(view)
