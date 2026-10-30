"""Public evidence views, with explicit classification and attribution gaps."""
import pandas as pd
import streamlit as st
from .cluster_planning import clusters, ipus, ROOT
from .published_data import (observations, snapshots, source_comparison, portfolio,
                             complete_ipu_demand, annual_observations, gap_register, CONTEXT)
from .presentation import ranking, source_figure, coverage_figure, TEAL, BLUE

NAMES = {'cluster_name':'Cluster', 'cluster_id':'Cluster ID', 'year':'Year', 'period':'Reporting period',
         'metric':'Measure', 'value':'Published value', 'unit':'Unit', 'status':'Status',
         'source_url':'Source', 'source_table':'Table', 'source_cell':'Cell', 'limitation':'Limits',
         'scope':'Reporting scope', 'system':'System of Care', 'ipu':'IPU', 'pathways':'Pathways',
         'module_status':'Module', 'legacy_model':'Simulation coverage', 'coded_activity':'Coded activity',
         'capacity_allocation':'Allocated capacity', 'related_indicators':'Related published evidence',
         'data_needed':'Required records', 'calibration_needed':'Calibration gaps', 'designation':'Designation',
         'value_2024':'MoH 2024 beds', 'value_undated':'HHC beds — year unspecified', 'review_status':'Review',
         'retrieved_on':'Retrieved on', 'volume':'Volume', 'association_status':'Association status'}


def table(frame, height=None):
    st.dataframe(frame.rename(columns=NAMES), hide_index=True, use_container_width=True,
                 column_config={'Source':st.column_config.LinkColumn('Source')},
                 **({'height':height} if height else {}))


def download(label, frame, name):
    st.download_button(label, frame.to_csv(index=False).encode('utf-8'), name, 'text/csv')


def evidence_rows(data):
    return data[['cluster_name', 'period', 'metric', 'value', 'unit', 'status',
                 'source_table', 'source_cell', 'source_url', 'limitation']]


def annual_view(metric, cluster_ids, years):
    frame = annual_observations(metric, cluster_ids, [2024, *years])
    frame.index = [clusters().set_index('cluster_id').loc[c, 'cluster_name'] for c in frame.index]
    frame.index.name = 'Cluster'
    data=observations()
    selected=data[data.metric.eq(metric)&data.cluster_id.isin(cluster_ids)]
    panels=st.tabs(['Compare clusters','Annual table'])
    with panels[0]:
        st.subheader(metric+' · 2024')
        st.caption('Reported volumes, largest first. Hover for exact values. This compares scale, not performance or population-adjusted need.')
        ranking(selected,metric,selected.unit.iloc[0],key='rank_'+metric)
    with panels[1]:
        st.caption('2024 is historical. Blank 2025–2054 planning cells are unavailable, not zero; no actuals are projected forward.')
        st.dataframe(frame, use_container_width=True, height=550)
    download('Download observed and planning years', frame.reset_index(), 'published_annual_cluster.csv')


def portfolio_view(cluster_ids, years):
    st.header('All 26 IPUs: evidence and unresolved gaps')
    a,b,c=st.columns(3)
    a.metric('IPUs supported', '26 / 26')
    b.metric('Validated coded activity', '0 / 26')
    c.metric('Verified IPU allocations', '0 / 26')
    st.caption('All ten previously unmodelled IPUs now have explicit annual coverage, pathway references, '
               'evidence links and data requirements. Their rates remain unavailable. '
               'The original 16 synthetic profiles are preserved; they are not validated clinical models.')
    inventory=portfolio()
    system=st.selectbox('Portfolio System of Care', ['All Systems of Care', *ipus().system.unique()])
    if system != 'All Systems of Care':
        inventory=inventory[inventory.system.eq(system)]
    st.caption('Green: pathway defined · Amber: related context or unvalidated simulation · Grey: unavailable. '
               'Context and synthetic profiles do not establish coded activity or operational capacity.')
    st.plotly_chart(coverage_figure(inventory),use_container_width=True,config={'displaylogo':False})
    with st.expander('IPU inventory and evidence descriptions'):
        table(inventory[['system','ipu','legacy_model','related_indicators']], height=450)
    st.divider()
    st.subheader('Explore an IPU')
    selected=st.selectbox('IPU evidence detail', inventory.ipu.tolist())
    row=inventory[inventory.ipu.eq(selected)].iloc[0]
    st.write('**Pathways:** '+row.pathways)
    st.write('**Records needed:** '+row.data_needed)
    st.write('**Calibration needed:** '+row.calibration_needed)
    if row.system=='Mental Health':
        st.info('Mental Health as a seventh System of Care remains proposed in this project.')
    data=observations()
    related=data[data.metric.isin(CONTEXT[selected]) & data.cluster_id.isin(cluster_ids)]
    if related.empty:
        st.warning('No sufficiently specific public cluster indicator has been loaded for this IPU. '
                   'Broad all-cause totals have not been assigned to it.')
    else:
        st.info('Related service evidence only. These are published service/facility counts, not coded IPU demand '
                'or capacity allocated to the IPU. This association is proposed and indicators may overlap.')
        metric=st.selectbox('Related indicator', sorted(related.metric.unique()))
        subset=related[related.metric.eq(metric)]
        ranking(subset,metric,subset.unit.iloc[0],key='ipu_related')
        with st.expander('Related source records'):
            table(evidence_rows(subset),height=350)
    st.subheader('Annual IPU coverage')
    focus=st.selectbox('Coverage year', years)
    missing=complete_ipu_demand(pd.DataFrame(),cluster_ids,[focus],'Inpatient','Observed activity')
    missing=missing[missing.ipu.eq(selected)]
    table(missing[['year','cluster_name','ipu','volume','status']],height=350)
    st.caption('Inpatient DRG demand, outpatient ICD-10-AM demand and IPU capacity are all unresolved '
               'for these cluster-years in the bundled public evidence. Imported records can populate every IPU in the annual views.')
    download('Download all 26 IPU definitions and requirements',portfolio(),'ipu_portfolio.csv')
    download('Download annual cluster × IPU gap register',gap_register(cluster_ids,years),'annual_ipu_data_gaps.csv')


def demand_view(cluster_ids, years):
    st.header('Yearly cluster demand: published evidence')
    st.warning('No usable cluster-level DRG or ICD-10-AM activity extract was found in the searched sources. '
               'Published service totals below describe delivered care and retain their original classifications. '
               'They cannot determine unmet need or coded IPU demand.')
    tabs=st.tabs(['Published activity totals','DRG / ICD-10-AM gaps'])
    data=observations()
    data=data[data.category.eq('Activity') & data.cluster_id.isin(cluster_ids)]
    with tabs[0]:
        choices=['Hospital admissions','Hospital outpatient encounters',*sorted(set(data.metric)-{'Hospital admissions','Hospital outpatient encounters'})]
        metric=st.selectbox('Published activity measure',choices)
        selected=data[data.metric.eq(metric)]
        a,b,c=st.columns(3)
        total=selected.value.sum(min_count=1)
        a.metric('Published activity · 2024',f'{total:,.0f}' if pd.notna(total) else 'Unavailable')
        b.metric('Clusters reporting',f'{selected.value.notna().sum()} / {len(cluster_ids)}')
        c.metric('DRG / ICD-10-AM breakdown','Unavailable')
        st.caption(selected.limitation.iloc[0])
        annual_view(metric,cluster_ids,years)
        with st.expander('Source records and definitions'):
            table(evidence_rows(selected))
        download('Download source activity records',selected,'published_activity.csv')
    with tabs[1]:
        setting=st.radio('Coded service setting',['Inpatient','Outpatient'],horizontal=True)
        st.info(('DRG admission counts' if setting=='Inpatient' else 'ICD-10-AM primary-diagnosis encounters')+
                ' are unavailable. No diagnosis or DRG has been inferred from an aggregate service total.')
        focus=st.selectbox('Coded detail year',years)
        skeleton=complete_ipu_demand(pd.DataFrame(),cluster_ids,[focus],setting,'Observed activity')
        table(skeleton[['year','cluster_name','system','ipu','volume','status']],height=450)
        download('Download complete annual coded-demand coverage',
                 complete_ipu_demand(pd.DataFrame(),cluster_ids,years,setting,'Observed activity'),
                 'annual_coded_demand_gaps.csv')


def supply_view(cluster_ids,years):
    st.header('Yearly cluster supply: published evidence')
    st.info('Reported beds and facility counts are loaded. Staffed/funded capacity, availability, '
            'workforce FTE and allocation agreements are unavailable. Effective capacity cannot be calculated from these sources.')
    tabs=st.tabs(['Dated cluster inventory','HHC profiles — undated','IPUs, Networks & Platforms','Source differences'])
    data=observations()
    data=data[data.category.eq('Capacity') & data.cluster_id.isin(cluster_ids)]
    with tabs[0]:
        metric=st.selectbox('Published capacity measure',['Hospital beds',*sorted(set(data.metric)-{'Hospital beds'})])
        selected=data[data.metric.eq(metric)]
        a,b,c=st.columns(3)
        total=selected.value.sum(min_count=1)
        a.metric('Reported inventory · 2024',f'{total:,.0f}' if pd.notna(total) else 'Unavailable')
        b.metric('Clusters reporting',f'{selected.value.notna().sum()} / {len(cluster_ids)}')
        c.metric('Effective capacity','Unavailable')
        st.caption(selected.unit.iloc[0]+'. '+selected.limitation.iloc[0])
        annual_view(metric,cluster_ids,years)
        with st.expander('Source capacity records'):
            table(evidence_rows(selected))
        download('Download source capacity records',selected,'published_capacity.csv')
    with tabs[1]:
        st.warning('Health Holding does not specify a reporting year for these profiles. '
                   'They are kept outside the annual ledger. Retrieved 31 October 2026 does not mean 2026 capacity.')
        metric=st.selectbox('HHC profile measure',['Hospital beds','Hospitals','Primary healthcare centres','Specialized centres'])
        subset=snapshots()
        subset=subset[subset.metric.eq(metric)&subset.cluster_id.isin(cluster_ids)]
        ranking(subset,metric,subset.unit.iloc[0],key='hhc_rank',color='#A76516')
        with st.expander('HHC profile records'):
            table(evidence_rows(subset),height=550)
        download('Download undated HHC profile records',subset,'hhc_undated_capacity.csv')
    with tabs[2]:
        group=st.radio('Organisational evidence',['IPUs','Networks','Platforms'],horizontal=True)
        if group=='IPUs':
            st.warning('No actual IPU allocation agreements were found. Related evidence is available in IPU coverage & gaps. '
                       'Specialty beds are not automatically owned by or allocated to an IPU.')
        elif group=='Networks':
            st.warning('Cluster inventory is known, but the within-cluster Network ownership split is not. '
                       'The illustrative two-Network split remains confined to Existing project simulation.')
        else:
            st.warning('Some facility categories support shared services, but Platform ownership, staffing, '
                       'annual slots and IPU allocations are not published in these sources.')
            table(evidence_rows(data[data.metric.isin(['Central / regional laboratories','Rehabilitation centres'])]),height=450)
        gaps=clusters()[clusters().cluster_id.isin(cluster_ids)][['cluster_id','cluster_name']].copy()
        gaps['Grouping']=group
        gaps['Ownership / allocation']='Unavailable'
        gaps['Staffed / funded / effective capacity']='Unavailable'
        table(gaps)
        download('Download organisational capacity gaps',gaps,'organisational_capacity_gaps.csv')
    with tabs[3]:
        compare=source_comparison()
        subset=compare[compare.cluster_id.isin(cluster_ids)]
        st.caption('Values are shown side by side, not as a trend or net change. Scope, definitions and the HHC reporting date '
                   'need reconciliation. No source silently overwrites another.')
        st.plotly_chart(source_figure(subset),use_container_width=True,config={'displaylogo':False})
        with st.expander('Source comparison table'):
            table(subset,height=550)
        download('Download capacity source comparison',compare[compare.cluster_id.isin(cluster_ids)],'capacity_source_comparison.csv')


def sources_view():
    st.header('Published sources and unresolved data gaps')
    st.markdown('[MoH 2024 statistical workbook](https://www.moh.gov.sa/en/Ministry/Statistics/book/Documents/Statistical-Yearbook-2024.xlsx) '
                '· [Health Holding cluster profiles](https://www.health.sa/en/clusters/list)')
    st.write('780 source records cover 39 measures across all 20 clusters for 2024, including one missing source value. '
             'A further 80 undated HHC profile values are kept separate. Each record has a source, table/cell or profile, '
             'reporting period, retrieval date and scope note. Facility categories and activity measures can overlap and are not added together.')
    checks=pd.read_csv(ROOT/'data/published_reconciliation.csv')
    st.caption('Makkah, Aseer and Al-Jouf use their whole-cluster source totals. Multi-cluster subtotals and component rows '
               'are excluded. The PHC national total includes 16,783 unassigned encounters/consultations; these are not distributed to clusters.')
    with st.expander('Published national controls and reconciliation'):
        table(checks)
    st.subheader('Research outcome')
    st.markdown('''- **Found:** 2024 cluster activity totals, hospital/specialty/ICU/ER beds and selected facility counts; undated HHC cluster profiles.
- **Not found in searched sources:** usable cluster × year × DRG admission or ICD-10-AM outpatient extracts; approved code-to-IPU crosswalks; actual Network/Platform ownership and IPU capacity agreements.
- **Available but unsuitable for cluster coding:** yearbook ICD-10 disease-group tables 4-14, 4-18 and 4-30 lack cluster attribution and do not establish an ICD-10-AM edition. They were not distributed into clusters.
- **Still required:** staffing, funding, operating hours, service slots, cohort denominators and future capacity plans. No actual 2025–2054 time series was inferred from 2024 or undated records.
- **All 26 IPUs supported:** all have pathway references, annual import coverage, data requirements and visible missingness. Ten newly covered IPUs have no invented rates. Mental Health as a seventh System remains proposed.
- **Search limits:** official MoH yearbook/open-data library, HHC profiles, CHI coding/open-data searches, connected GitHub/Drive searches and local project sources were checked. This is not proof that the missing records do not exist. The CHI data-centre page could not be retrieved during this review.
- **Project source quality:** the Eastern ACO register identifies itself as simulated planning content; the legacy regional “real_supply_data” file has no verifiable source. Neither was promoted to actual cluster evidence.''')
    st.caption('Research checked 31 October 2026. Switch Data source to Import annual CSVs for templates and browser-local data imports. '
               'Select Existing project simulation to retain all prior scenarios.')
    download('Download all published annual observations',observations(),'published_cluster_observations.csv')
    download('Download source reconciliation',checks,'published_reconciliation.csv')


def render_published(view,cluster_ids,years):
    if view=='Overview':
        overview(cluster_ids,years)
    elif view=='Yearly cluster demand':
        demand_view(cluster_ids,years)
    elif view=='Yearly cluster supply':
        supply_view(cluster_ids,years)
    elif view=='IPU coverage & gaps':
        portfolio_view(cluster_ids,years)
    else:
        sources_view()


def overview(cluster_ids,years):
    st.header('Cluster overview')
    st.caption('MoH facilities · 2024 reported activity and inventory · Selected clusters only')
    data=observations()
    selected=data[data.cluster_id.isin(cluster_ids)]
    cards=st.columns(3)
    for card,metric,label in zip(cards,['Hospital admissions','Hospital outpatient encounters','Hospital beds'],
                                 ['Hospital admissions','Outpatient encounters','Reported hospital beds']):
        total=selected.loc[selected.metric.eq(metric),'value'].sum(min_count=1)
        card.metric(label,f'{total:,.0f}' if pd.notna(total) else 'Unavailable')
    st.info('Published totals are available for all 20 clusters. DRG / ICD-10-AM detail and effective, allocated capacity remain unavailable.')
    left,right=st.columns(2)
    with left:
        st.subheader('Activity by cluster')
        metric=st.selectbox('Overview activity',['Hospital admissions','Hospital outpatient encounters','PHC encounters and consultations'],label_visibility='collapsed')
        subset=selected[selected.metric.eq(metric)]
        st.caption(metric+' · 2024')
        ranking(subset,metric,subset.unit.iloc[0],key='overview_activity')
    with right:
        st.subheader('Capacity by cluster')
        metric=st.selectbox('Overview capacity',['Hospital beds','Primary healthcare centres','Emergency department beds'],label_visibility='collapsed')
        subset=selected[selected.metric.eq(metric)]
        st.caption(metric+' · 2024')
        ranking(subset,metric,subset.unit.iloc[0],key='overview_capacity',color=BLUE)
    st.caption('Charts show scale, not performance. Measures have different units and must not be added. '
               'Reported beds do not establish staffing or availability.')
    st.subheader('Evidence at a glance')
    status=pd.DataFrame([
        ['Cluster activity & inventory','2024 · 20 clusters','Published'],
        ['HHC capacity profiles','Reporting year unspecified','Separate snapshot'],
        ['Reference IPU portfolio','26 IPUs · 49 pathways','Defined'],
        ['Cluster DRG / ICD-10-AM activity','No usable extract found','Unavailable'],
        ['IPU / Network / Platform allocations','No verified register found','Unavailable'],
        [f'{years[0]}–{years[-1]} planning inputs','Future actuals and calibrated rates','Unavailable'],
    ],columns=['Evidence','Coverage','Status'])
    table(status)
    st.caption('Use the left navigation for annual demand, supply, IPU coverage, source details or the preserved simulation. '
               'Change the cluster selection to update every chart on this page.')
