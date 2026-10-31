"""Annual, evidence-labelled demand/supply gap and scenario workspace."""
import json
from dataclasses import asdict
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from .cluster_planning import (ipus, UNITS, DEMAND_COLUMNS, MAPPING_COLUMNS, SUPPLY_COLUMNS, ALLOCATION_COLUMNS)
from .gap_planning import Scenario, COEFFICIENT_COLUMNS, demo_coefficients, make_gap_ledger, summarize, apply_scenario
from .presentation import base, TEAL, AMBER, short


@st.cache_data(show_spinner='Preparing comparable annual requirements and allocations…', max_entries=4)
def _prepared(*args, **kwargs):
    return make_gap_ledger(*args, **kwargs)


def _chart(frame, field, label):
    valid = frame[frame.scenario_gap.notna()].sort_values('scenario_gap')
    fig = go.Figure()
    for col, name, color in [('baseline_gap','Baseline gap','#ABBBC0'), ('scenario_gap','Scenario gap',AMBER)]:
        fig.add_trace(go.Bar(x=valid[col].tolist(), y=valid[field].tolist(), orientation='h', name=name,
            marker_color=color, customdata=valid[['comparable_pairs','expected_pairs','coverage']].to_numpy(),
            hovertemplate='%{y}<br>%{x:,.1f} '+label+'<br>%{customdata[0]}/%{customdata[1]} comparable pairs'
                          '<br>%{customdata[2]}<extra>'+name+'</extra>'))
    base(fig, max(310,len(valid)*35+100))
    fig.update_layout(barmode='group')
    fig.add_vline(x=0,line_color='#213D44',line_width=1)
    fig.update_xaxes(title_text='Gap = required − available · '+label)
    fig.update_yaxes(showgrid=False)
    return fig


def _scenario(public):
    with st.expander('Scenario controls', expanded=not public):
        st.caption('Adjustments apply to the selected annual input path. Growth compounds from 2025, '
                   'regardless of the displayed year range. Zero adjustments reproduce the baseline. '
                   'Missing years stay missing; no observations are carried forward.')
        a,b = st.columns(2)
        with a:
            d = st.slider('Demand adjustment (%)', -50, 100, 0, 5, disabled=public, key='gap_demand_change')
            dg = st.slider('Additional annual demand growth (%)', -5.0, 10.0, 0.0, .5, disabled=public, key='gap_demand_growth')
        with b:
            s = st.slider('Capacity adjustment (%)', -50, 100, 0, 5, disabled=public, key='gap_supply_change')
            sg = st.slider('Additional annual capacity growth (%)', -5.0, 10.0, 0.0, .5, disabled=public, key='gap_supply_growth')
        st.caption('Controls are sensitivity assumptions, not approved investment plans or statistical confidence intervals. '
                   'Changes apply uniformly to the selected clusters and IPUs. Existing growth in the source path is retained.')
    return Scenario() if public else Scenario(d,dg,s,sg)


def render_gap(mode, cluster_ids, years, focus, inputs=None, integrated=True, seed=42):
    from .cluster_dashboard import LABELS, _read, _download
    st.header('Yearly demand–supply gap')
    st.caption('Positive gap = shortage. Negative gap = surplus. All comparisons use the same resource and unit. '
               'A capacity gap is a planning estimate, not a count of unserved patients.')
    public = mode == 'Published cluster evidence'
    synthetic = mode == 'Existing project simulation'
    a,b,c = st.columns(3)
    with a:
        resource = st.selectbox('Gap resource', list(UNITS), format_func=LABELS.get, key='gap_resource')
    with b:
        system = st.selectbox('System of Care', ['All Systems of Care', *ipus().system.unique()], key='gap_system')
    allowed = ipus() if system == 'All Systems of Care' else ipus()[ipus().system.eq(system)]
    with c:
        ipu = st.selectbox('IPU', ['All IPUs', *allowed.ipu], key='gap_ipu')
    unit = UNITS[resource]
    scenario = _scenario(public)
    if inputs is None:
        inputs = tuple(pd.DataFrame(columns=cols) for cols in [DEMAND_COLUMNS,MAPPING_COLUMNS,SUPPLY_COLUMNS,ALLOCATION_COLUMNS])
    demand, mapping, supply, allocation = inputs
    coefficients = pd.DataFrame(columns=COEFFICIENT_COLUMNS)
    setting = 'Inpatient' if resource == 'Beds' else 'Outpatient'
    demand_series, supply_series, edition = 'Unavailable', 'Unavailable', 'Unavailable'
    confirmed = True
    if public:
        st.warning('UNRESOLVED · Published totals cannot establish an IPU demand–supply gap. '
                   'The bundled evidence has no 2025–2054 coded activity, IPU allocations or calibrated resource coefficients. '
                   'Choose Existing project simulation for estimates, or Import annual CSVs for your own evidence.')
        with st.expander('Actual published baseline · 2024 · cluster totals only'):
            from .published_data import observations
            obs = observations()
            obs = obs[obs.cluster_id.isin(cluster_ids) & obs.metric.isin(['Hospital admissions','Hospital beds','Hospital outpatient encounters'])]
            st.caption('These are actual published aggregates, not IPU allocations or unmet demand. Admissions and beds '
                       'are different units and are not subtracted. System/IPU filters do not allocate these cluster totals.')
            st.dataframe(obs[['year','cluster_name','metric','value','unit','source_url']],hide_index=True,use_container_width=True)
    elif synthetic:
        coefficients = demo_coefficients(resource)
        demand_series, supply_series, edition = 'Synthetic forecast','Synthetic capacity','DEMO-v0.1'
        st.info('ESTIMATES · Synthetic activity and allocated capacity from the existing project. '
                '16 of 26 IPUs have original model profiles; the remaining IPUs retain unresolved values. '
                'No synthetic result is labelled actual or clinically calibrated.')
    else:
        a,b,c = st.columns(3)
        with a:
            setting = st.selectbox('Gap workload setting', ['Inpatient','Outpatient'], key='gap_setting')
            demand_series = st.selectbox('Gap demand series', sorted(demand.series.unique()) or ['Unavailable'])
        with b:
            supply_series = st.selectbox('Gap capacity series', sorted(supply.series.unique()) or ['Unavailable'])
        with c:
            editions = sorted(demand.loc[demand.setting.eq(setting) & demand.series.eq(demand_series),'edition'].unique())
            edition = st.selectbox('Gap coding edition', editions or ['Unavailable'])
        with st.expander('Resource conversion and scope', expanded=True):
            st.caption('Upload one requirement_per_activity per exact code, edition and resource, in the selected supply unit '
                       'per admission/encounter. For example, beds/admission = LOS ÷ (365 × target occupancy). '
                       'Use an explicit zero coefficient when a code needs none of that resource; omitted coefficients remain unresolved. '
                       'A diagnosis alone does not establish resource need.')
            file = st.file_uploader('Resource coefficients CSV', type=['csv'], key='gap_coefficients')
            coefficients = _read(file, COEFFICIENT_COLUMNS)
            _download('Download resource coefficient template', pd.DataFrame(columns=COEFFICIENT_COLUMNS), 'resource_coefficients_template.csv')
            confirmed = st.checkbox('I confirm the activity, coefficients and IPU allocations cover the same workload', key='gap_scope_confirmed')
            st.caption('For a setting-specific gap, allocate only that setting’s share of shared beds, rooms or workforce. '
                       'Imported Observed labels, mappings and scope confirmations are user-supplied, not independently verified. '
                       'Converted requirements and scenario outputs are always estimates. Recorded activity does not include all unmet need.')
    ledger, unallocated, owned = _prepared(*inputs, coefficients, cluster_ids, years, resource, setting,
        demand_series, supply_series, edition, scope_confirmed=confirmed)
    ledger = apply_scenario(ledger, scenario)
    all_ledger = ledger
    if system != 'All Systems of Care': ledger = ledger[ledger.system.eq(system)]
    if ipu != 'All IPUs': ledger = ledger[ledger.ipu.eq(ipu)]
    year = st.select_slider('Gap detail year', options=years, value=focus) if len(years)>1 else years[0]
    current = ledger[ledger.year.eq(year)]
    summary = summarize(current, ['year']).iloc[0]
    valid = current[current.comparable]
    a,b,c,d = st.columns(4)
    a.metric('Comparable IPU pairs', f'{len(valid)} / {len(current)}')
    b.metric('Required · comparable', f'{summary.scenario_demand:,.1f}' if len(valid) else 'Unavailable')
    c.metric('Available · comparable', f'{summary.scenario_supply:,.1f}' if len(valid) else 'Unavailable')
    d.metric('Net gap · comparable', f'{summary.scenario_gap:+,.1f}' if len(valid) else 'Unresolved')
    st.caption(f'{year} · {unit} · {summary.coverage}. Totals use only IPUs with both usable requirements and allocated capacity. '
               'They do not represent a complete cluster or System of Care when coverage is partial. '
               'Beds, rooms and FTE are annual snapshots and must not be added across years.')
    if len(valid):
        st.caption(f'Local shortages: {summary.shortage:,.1f} {unit} · Local surpluses: {summary.surplus:,.1f} {unit}. '
                   'Netting across IPUs does not mean capacity can be transferred between them.')
    if all_ledger.ipu.eq('Unmapped').any():
        st.warning('Some activity has no exact IPU crosswalk. It remains Unmapped in the full ledger and prevents a complete all-IPU comparison.')
    if len(unallocated):
        st.caption('Unallocated capacity is retained in the evidence tab; it is not assigned to IPUs or added to comparable totals.')
    tabs = st.tabs(['Gap comparison','Annual trends & heatmap','Evidence & unresolved gaps'])
    with tabs[0]:
        dimension = st.radio('Compare by', ['Cluster','System of Care','IPU'], horizontal=True)
        field = {'Cluster':'cluster_name','System of Care':'system','IPU':'ipu'}[dimension]
        grouped = summarize(current, [field])
        if grouped.scenario_gap.notna().any():
            if field == 'cluster_name': grouped[field] = grouped[field].map(short)
            st.plotly_chart(_chart(grouped,field,unit),use_container_width=True,config={'displaylogo':False})
        else:
            st.info('No comparable gap can be calculated for this selection. See the evidence table for the missing inputs.')
        st.dataframe(grouped,hide_index=True,use_container_width=True)
    with tabs[1]:
        annual = summarize(ledger,['year'])
        if annual.scenario_gap.notna().any():
            fig = go.Figure()
            for field,label,color,dash in [('baseline_gap','Baseline gap','#82959B','dash'),('scenario_gap','Scenario gap',AMBER,'solid')]:
                fig.add_trace(go.Scatter(x=annual.year.tolist(),y=annual[field].where(annual[field].notna(),None).tolist(),
                    name=label,mode='lines',line=dict(color=color,dash=dash),connectgaps=False,
                    customdata=annual[['comparable_pairs','expected_pairs']].to_numpy(),
                    hovertemplate='%{x}: %{y:,.1f}<br>%{customdata[0]}/%{customdata[1]} comparable pairs<extra>'+label+'</extra>'))
            base(fig,350); fig.add_hline(y=0,line_color='#213D44'); fig.update_yaxes(title_text=unit)
            fig.update_xaxes(tickformat='d',title_text='Year')
            st.plotly_chart(fig,use_container_width=True,config={'displaylogo':False})
            grouped = summarize(ledger,['year','cluster_name'])
            matrix = grouped.pivot(index='cluster_name',columns='year',values='scenario_gap')
            z = matrix.to_numpy(dtype=float)
            bound = max(float(np.nanmax(np.abs(z))),1.)
            fig = go.Figure(go.Heatmap(z=z.tolist(),x=matrix.columns.tolist(),y=matrix.index.map(short).tolist(),
                colorscale=[[0,TEAL],[.5,'#F5F7F7'],[1,'#B96A29']],zmin=-bound,zmax=bound,
                colorbar=dict(title=unit),hoverongaps=False,
                hovertemplate='%{y} · %{x}<br>Scenario net gap: %{z:,.1f}<extra></extra>'))
            base(fig,max(300,len(matrix)*26+100)); fig.update_xaxes(title_text='Year',tickformat='d')
            st.plotly_chart(fig,use_container_width=True,config={'displaylogo':False})
            st.caption('Amber: shortage · Teal: surplus · Blank: unresolved. These are comparable subtotals; coverage can change by year.')
        else:
            st.info('Annual comparisons remain unresolved until both sides and resource conversions are available.')
        st.dataframe(annual,hide_index=True,use_container_width=True)
        exported = annual.assign(resource=resource, unit=unit, data_source=mode, system_filter=system, ipu_filter=ipu,
                                 cluster_ids=';'.join(cluster_ids), scenario_anchor_year=2025, **asdict(scenario))
        _download('Download annual scenario summary',exported,'annual_gap_summary.csv')
    with tabs[2]:
        st.markdown('**Actual inputs → estimated requirements → estimated scenario → unresolved evidence**')
        st.caption('Published actuals are shown only in their recorded period and grain. Imported observations retain '
                   'their user-supplied status. Missing activity, coefficients, crosswalks and allocations are separate reasons. '
                   'No record is interpreted as zero. Mental Health as a seventh System remains proposed in the project.')
        columns = ['year','cluster_name','system','ipu','activity_status','capacity_status','result_status',
                   'activity','baseline_demand','baseline_supply','scenario_demand','scenario_supply','scenario_gap','data_gap']
        st.dataframe(current[columns],hide_index=True,use_container_width=True,height=480)
        with st.expander('Assumptions, source paths and workload conversion'):
            settings = {**asdict(scenario),'anchor_year':2025,'resource':resource,'unit':unit,
                     'workload_setting':setting,'demand_series':demand_series,'capacity_series':supply_series,
                     'edition':edition,'integrated_care':integrated if synthetic else None,'seed':seed if synthetic else None}
            st.dataframe(pd.DataFrame([(k,str(v)) for k,v in settings.items()],columns=['Setting','Value']),hide_index=True,use_container_width=True)
            st.dataframe(coefficients,hide_index=True,use_container_width=True)
            if synthetic:
                st.caption('Beds = synthetic admissions × LOS ÷ (365 × 0.82 occupancy). Rooms = encounters ÷ (240 × 8 × 2.2). '
                           'Workforce uses encounters ÷ visits per episode to reconstruct synthetic episodes; physician hours and '
                           'nursing hours (including inpatient bed-day nursing) are divided by 1,550 hours/FTE. '
                           'This workforce requirement covers the whole synthetic episode, not outpatient care alone. '
                           'Coefficients are preserved from the original model, not validated standards.')
            st.dataframe(current[['cluster_name','ipu','activity_source','mapping_source','mapping_status',
                                  'coefficient_source','capacity_source','allocation_source']],hide_index=True,use_container_width=True)
        with st.expander('Owned inventory and unallocated capacity · all IPUs in selected clusters'):
            st.caption('Inventory is shown for reconciliation, not added to IPU allocations. System/IPU filters do not allocate unassigned resources.')
            st.dataframe(owned[owned.year.eq(year)],hide_index=True,use_container_width=True)
            st.dataframe(unallocated[unallocated.year.eq(year)],hide_index=True,use_container_width=True)
        _download('Download unresolved annual rows',ledger[~ledger.comparable],'unresolved_annual_gaps.csv')
    ledger = ledger.copy()
    ledger['data_source'] = mode
    ledger['integrated_care'] = integrated if synthetic else ''
    ledger['simulation_seed'] = seed if synthetic else ''
    _download('Download annual cluster–System–IPU gap ledger',ledger,'annual_cluster_system_ipu_gaps.csv')
    st.download_button('Download scenario settings',json.dumps({'data_source':mode,'years':years,'clusters':cluster_ids,
        'system':system,'ipu':ipu,'resource':resource,'setting':setting,'edition':edition,'demand_series':demand_series,
        'supply_series':supply_series,'anchor_year':2025,'scope_confirmed':confirmed,
        'integrated_care':integrated if synthetic else None,'seed':seed if synthetic else None,
        'adjustments':asdict(scenario)},indent=2),file_name='gap_scenario.json',mime='application/json')
