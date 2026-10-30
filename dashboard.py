"""Current dashboard; the original v0.1 app remains available unchanged."""
import runpy
import streamlit as st

st.set_page_config(page_title='Saudi ACO Annual Cluster Planning', layout='wide')
view = st.sidebar.radio('View', ['Yearly cluster demand', 'Yearly cluster supply',
                                 'IPU coverage & gaps', 'Data & mappings', 'Regional prototype'])
if view == 'Regional prototype':
    runpy.run_path('app.py', run_name='__main__')
else:
    from aco_sim.cluster_dashboard import render
    render(view)
