"""Streamlit views for annual demand and non-duplicated organisational supply."""
from io import StringIO
import pandas as pd
import plotly.express as px
import streamlit as st
from .cluster_planning import (
    clusters, ipus, demo_data, map_demand, allocate_supply, annual_matrix,
    DEMAND_COLUMNS, MAPPING_COLUMNS, SUPPLY_COLUMNS, ALLOCATION_COLUMNS, UNITS,
)

TEMPLATES = [('Demand', DEMAND_COLUMNS), ('Code mappings', MAPPING_COLUMNS),
             ('Supply assets', SUPPLY_COLUMNS), ('IPU allocations', ALLOCATION_COLUMNS)]
LABELS = {'Beds': 'Beds', 'Physicians': 'Physician FTE', 'Nurses': 'Nurse FTE',
          'Outpatient_Clinics': 'Outpatient clinic rooms', 'Theatre_hours': 'Theatre hours',
          'Imaging_slots': 'Imaging slots', 'Laboratory_tests': 'Laboratory tests'}
DISPLAY_NAMES = {'year': 'Year', 'cluster_id': 'Cluster ID', 'cluster_name': 'Cluster',
                 'system': 'System of Care', 'ipu': 'IPU', 'mapping_status': 'Mapping status',
                 'volume': 'Volume', 'series': 'Data series', 'setting': 'Service setting',
                 'code_system': 'Classification', 'edition': 'Edition', 'code': 'Code',
                 'source': 'Source', 'mapping_source': 'Mapping source', 'resource': 'Resource',
                 'unit': 'Unit', 'owner_id': 'Owner ID', 'owner_name': 'Owner', 'owner_type': 'Owner type',
                 'asset_id': 'Asset ID', 'physical_capacity': 'Physical / established',
                 'staffed_capacity': 'Staffed', 'funded_capacity': 'Funded',
                 'effective_capacity': 'Effective capacity', 'availability_fraction': 'Availability',
                 'owned_capacity': 'Owned capacity', 'allocated_plus_unallocated': 'Allocated + unallocated',
                 'difference': 'Difference', 'allocated_fraction': 'Allocation share',
                 'allocation_source': 'Allocation source', 'region': 'Region', 'registry_note': 'Registry note'}


def _table(df, height=None):
    config = {DISPLAY_NAMES.get(c, c): st.column_config.NumberColumn(format='%.1f')
              for c in df if pd.api.types.is_numeric_dtype(df[c]) and c != 'year'}
    st.dataframe(df.rename(columns=DISPLAY_NAMES), use_container_width=True, hide_index=True,
                 column_config=config, **({'height': height} if height else {}))


@st.cache_data(show_spinner='Preparing annual views from the existing prototype…')
def existing_data(seed, integrated):
    return demo_data(seed=seed, integrated=integrated)


@st.cache_data(show_spinner=False)
def allocated_data(supply, agreements):
    return allocate_supply(supply, agreements)


def _download(label, df, filename):
    st.download_button(label, df.to_csv(index=False).encode('utf-8'),
                       file_name=filename, mime='text/csv')


def _read(upload, columns):
    if upload is None:
        return pd.DataFrame(columns=columns)
    return pd.read_csv(StringIO(upload.getvalue().decode('utf-8-sig')), dtype=str, keep_default_na=False)


def _load(mode, seed, integrated):
    if mode == 'Existing project simulation':
        st.warning('SYNTHETIC DEMONSTRATION · Existing model with illustrative cluster splits, DEMO codes and capacity allocations. '
                   'Actual DRG/ICD-10-AM activity and operational capacity data are not loaded.')
        return existing_data(seed, integrated)
    st.info('Import annual aggregate records. In this deployed browser app, files are processed in your browser '
            'and are not saved to GitHub or Netlify. Imported labels and approvals are user-supplied, not independently verified.')
    with st.expander('Load annual CSVs', expanded=True):
        left, right = st.columns(2)
        with left:
            demand = st.file_uploader('Demand activity / forecast CSV', type=['csv'], key='demand_file')
            mapping = st.file_uploader('DRG / ICD-10-AM to System of Care / IPU CSV', type=['csv'], key='mapping_file')
        with right:
            supply = st.file_uploader('Supply asset register CSV', type=['csv'], key='supply_file')
            allocation = st.file_uploader('IPU capacity allocations CSV', type=['csv'], key='allocation_file')
        st.caption('Demand uses one annual count per primary code; do not submit multiple diagnoses or claims lines '
                   'for the same encounter. Supply records each asset once; allocations reference its asset_id.')
    return tuple(_read(f, cols) for f, (_, cols) in zip(
        [demand, mapping, supply, allocation], TEMPLATES))


def _scope(df, selected_clusters, years):
    if df.empty:
        return df
    return df[df.cluster_id.isin(selected_clusters) & df.year.between(years[0], years[-1])].copy()


def _matrix(df, value, cluster_ids, years, title, unit):
    matrix = annual_matrix(df, value, cluster_ids, years)
    st.subheader(title)
    st.caption(f'{unit}. Blank cells mean no records for that cluster/year in this selection; they do not mean zero.')
    if matrix.notna().any().any():
        from .presentation import base, trend_figure, short
        charts=st.tabs(['Cluster heatmap','Yearly trends','Values'])
        with charts[0]:
            visual=matrix.copy()
            visual.index=visual.index.map(short)
            fig = px.imshow(visual, aspect='auto', color_continuous_scale='Teal',
                            labels={'x': 'Year', 'y': 'Cluster', 'color': unit})
            base(fig,max(300,len(cluster_ids)*25+120))
            fig.update_xaxes(dtick=5 if len(years)>10 else 1)
            st.plotly_chart(fig, use_container_width=True,config={'displaylogo':False})
        with charts[1]:
            st.caption('Use the legend to isolate a cluster. Missing years are not connected. Capacity snapshots are not summed across years.')
            st.plotly_chart(trend_figure(matrix,unit),use_container_width=True,config={'displaylogo':False})
        with charts[2]:
            st.dataframe(matrix, use_container_width=True, height=min(750, len(cluster_ids) * 35 + 50))
    else:
        st.info('No records for this selection. Choose another resource, period or data source.')
        st.dataframe(matrix,use_container_width=True,height=250)
    _download('Download year-by-cluster table', matrix.reset_index(),
              'annual_cluster_' + ('demand' if value == 'volume' else 'supply') + '.csv')


def _ipu_filter(df, prefix, allow_unassigned=True):
    systems = ipus().system.drop_duplicates().tolist()
    extras = [s for s in ['Unmapped', 'Unallocated'] if s in set(df.get('system', []))]
    system = st.selectbox('System of Care', ['All Systems of Care', *systems, *extras], key=prefix + '_system')
    allowed = ipus() if system == 'All Systems of Care' else ipus()[ipus().system.eq(system)]
    ipu_names = allowed.ipu.tolist()
    if allow_unassigned:
        ipu_names += [x for x in extras if system in ['All Systems of Care', x]]
    ipu = st.selectbox('IPU', ['All IPUs', *ipu_names], key=prefix + '_ipu')
    if system != 'All Systems of Care':
        df = df[df.system.eq(system)]
    if ipu != 'All IPUs':
        df = df[df.ipu.eq(ipu)]
    return df


def _demand(raw, mapping, cluster_ids, years, focus):
    st.header('Yearly cluster demand')
    if raw.empty:
        st.info('Demand is unavailable. Load demand aggregates; load code mappings to group them by System of Care and IPU.')
        return
    full = map_demand(raw, mapping)
    selected = _scope(full, cluster_ids, years)
    a, b, c = st.columns(3)
    with a:
        setting = st.radio('Service setting', ['Inpatient', 'Outpatient'], horizontal=True)
    with b:
        series = st.selectbox('Demand series', sorted(full.series.unique()))
    selected = selected[selected.setting.eq(setting) & selected.series.eq(series)]
    editions = sorted(selected.edition.unique())
    with c:
        edition = st.selectbox('Coding edition', ['All editions — disjoint records only', *editions])
    if edition != 'All editions — disjoint records only':
        selected = selected[selected.edition.eq(edition)]
    coverage_data = selected.copy()
    with st.expander('Coding and count definitions'):
        st.caption('Inpatient admissions group by DRG; outpatient encounters group by primary ICD-10-AM diagnosis. '
                   'The volumes are separate. Observed activity records delivered care, not all unmet need. '
                   'No automatic DRG grouper or clinical coding validation is performed. '
                   'Annual totals require disjoint records; do not import alternate coding versions of the same admissions as additional activity.')
        if selected.code_system.str.startswith('DEMO-').any():
            st.caption('DEMO grouping tokens link the existing specialty profiles to reference IPUs. They are not clinical codes. '
                       'Upload classified records and an edition-specific crosswalk for DRG/ICD-10-AM reporting.')
    with st.expander('System of Care and IPU filters'):
        selected = _ipu_filter(selected, 'demand')
    current = selected[selected.year.eq(focus)]
    recorded = 'Recorded' if series == 'Observed activity' else 'Expected'
    unit = 'admissions' if setting == 'Inpatient' else 'outpatient encounters'
    one, two, three = st.columns(3)
    one.metric(f'{recorded} {unit} · {focus}', f'{current.volume.sum():,.0f}' if not current.empty else 'Unavailable')
    two.metric('Clusters with records · selected year', f'{current.cluster_id.nunique()} / {len(cluster_ids)}')
    mapped = current.loc[current.ipu.ne('Unmapped'), 'volume'].sum()
    total = current.volume.sum()
    three.metric('Volume assigned to an IPU', f'{mapped / total:.1%}' if total else 'Unavailable')
    tabs = st.tabs(['Year by cluster', 'Systems of Care & IPUs', 'DRG / ICD-10-AM detail'])
    with tabs[0]:
        _matrix(selected, 'volume', cluster_ids, years,
                f'Annual {unit} · {series}', unit)
    with tabs[1]:
        st.subheader(f'Cluster → System of Care → IPU · {focus}')
        grouped = current.groupby(['year', 'cluster_name', 'system', 'ipu', 'mapping_status'], as_index=False).volume.sum()
        _table(grouped, height=550)
        modeled = set(full.loc[full.ipu.ne('Unmapped'), 'ipu'])
        unmodeled = ipus()[~ipus().ipu.isin(modeled)]
        st.caption(f'{len(modeled)} of 26 reference IPUs have records in this dataset. '
                   'Missing IPUs are not assigned invented demand or zero demand. Mental Health as a seventh System remains proposed.')
        if not unmodeled.empty:
            with st.expander('Reference IPUs without records in this dataset'):
                _table(unmodeled)
        from .published_data import complete_ipu_demand
        complete = complete_ipu_demand(coverage_data, cluster_ids, years, setting, series)
        with st.expander('Complete 26-IPU annual coverage, including missing records'):
            st.caption('All reference IPUs in the selected clusters and years; independent of the System/IPU filter above. '
                       'Missing volumes remain blank. Unmapped codes remain in the coded-detail export.')
            _table(complete[complete.year.eq(focus)], height=500)
        _download('Download complete 26-IPU annual demand coverage', complete, 'complete_ipu_demand_coverage.csv')
        _download('Download annual demand by System of Care and IPU',
                  selected.groupby(['year', 'cluster_id', 'cluster_name', 'setting', 'series', 'system', 'ipu', 'mapping_status'], as_index=False).volume.sum(),
                  'annual_cluster_system_ipu_demand.csv')
    with tabs[2]:
        st.subheader(f'Code and edition detail · {focus}')
        cols = ['year', 'cluster_name', 'setting', 'code_system', 'edition', 'code',
                'system', 'ipu', 'volume', 'series', 'mapping_status', 'source', 'mapping_source']
        _table(current[cols], height=550)
        missing = selected[selected.ipu.eq('Unmapped')]
        if not missing.empty:
            st.warning(f'{len(missing):,} selected records have no exact code-and-edition mapping. '
                       'Their volume is retained in the Unmapped category.')
        _download('Download coded annual demand', selected[cols + ['cluster_id', 'record_id']], 'annual_cluster_coded_demand.csv')


def _supply(raw, allocations, cluster_ids, years, focus):
    st.header('Yearly cluster supply')
    st.caption('Physical/established, staffed, funded and effective capacity are separate. '
               'Effective capacity = min(physical, staffed, funded) × availability. '
               'Inventory has one owner per asset; IPU views show allocations of that same inventory.')
    if raw.empty:
        st.info('Supply is unavailable. Load an annual asset register; add capacity agreements for the IPU allocation view.')
        return
    inventory, assigned = allocated_data(raw, allocations)
    inventory = _scope(inventory, cluster_ids, years)
    assigned = _scope(assigned, cluster_ids, years)
    grouping = st.radio('Supply grouping', ['IPUs (allocated)', 'Networks (owned)', 'Platforms (owned)'], horizontal=True)
    owners = inventory if grouping.startswith('IPUs') else inventory[inventory.owner_type.eq('Network' if grouping.startswith('Networks') else 'Platform')]
    available = [r for r in UNITS if r in set(owners.resource)]
    default_resource = available[0] if available else 'Beds'
    a, b = st.columns(2)
    with a:
        resource = st.selectbox('Supply resource', list(UNITS), format_func=LABELS.get,
                                index=list(UNITS).index(default_resource), key='resource_' + grouping)
    with b:
        series = st.selectbox('Capacity series', sorted(raw.series.unique()))
    unit = UNITS[resource]
    inv = inventory[inventory.resource.eq(resource) & inventory.series.eq(series)]
    assigned = assigned[assigned.resource.eq(resource) & assigned.series.eq(series)]
    if grouping == 'IPUs (allocated)':
        data = assigned
        with st.expander('System of Care and IPU filters'):
            data = _ipu_filter(data, 'supply')
        group_cols = ['system', 'ipu']
    else:
        data = inv[inv.owner_type.eq('Network' if grouping.startswith('Networks') else 'Platform')]
        group_cols = ['owner_id', 'owner_name']
    data = data.merge(clusters()[['cluster_id', 'cluster_name']], on='cluster_id', validate='many_to_one')
    current, total_inv = data[data.year.eq(focus)], inv[inv.year.eq(focus)]
    unallocated = assigned[assigned.year.eq(focus) & assigned.ipu.eq('Unallocated')]
    a, b, c = st.columns(3)
    a.metric(f'Owned inventory, all owner types · {focus}',
             f'{total_inv.effective_capacity.sum():,.1f} {unit}' if not total_inv.empty else 'Unavailable')
    b.metric(f'Effective capacity in this view · {focus}',
             f'{current.effective_capacity.sum():,.1f} {unit}' if not current.empty else 'Unavailable')
    c.metric('Unallocated to IPUs · selected year',
             f'{unallocated.effective_capacity.sum():,.1f} {unit}' if not total_inv.empty else 'Unavailable')
    st.caption('Beds, rooms and FTE are annual capacity snapshots, not totals to add across years. '
               'Theatre hours, imaging slots and laboratory tests use annual throughput units. '
               'IPU allocations must not be added to Network/Platform inventory totals.')
    if current.empty:
        st.info('No capacity records for this resource/group/year. Missing data is not zero. '
                'The existing prototype supplies only beds, physician FTE, nurse FTE and clinic rooms; '
                'no theatre-hour, imaging-slot or laboratory-test capacity has been invented.')
    if grouping.startswith('IPUs'):
        reported_ipus = set(assigned.loc[assigned.ipu.ne('Unallocated'), 'ipu'])
        st.caption(f'{len(reported_ipus)} of 26 reference IPUs have allocation records for this resource in the selected period.')
        absent = ipus()[~ipus().ipu.isin(reported_ipus)]
        if not absent.empty:
            with st.expander('Reference IPUs without capacity allocation records'):
                _table(absent)
    tabs = st.tabs(['Year by cluster', 'Organisation detail', 'Capacity reconciliation'])
    with tabs[0]:
        _matrix(data, 'effective_capacity', cluster_ids, years,
                f'{LABELS[resource]} · {grouping} · {series}', unit)
    with tabs[1]:
        st.subheader(f'{grouping} · {focus}')
        fields = ['year', 'cluster_name', *group_cols, 'resource', 'unit', 'series']
        values = ['physical_capacity', 'staffed_capacity', 'funded_capacity', 'effective_capacity']
        grouped = current.groupby(fields, as_index=False)[values].sum()
        _table(grouped, height=550)
        _download('Download annual organisational supply', data.groupby(fields, as_index=False)[values].sum(),
                  'annual_cluster_organisational_supply.csv')
    with tabs[2]:
        own = inv.groupby(['year', 'cluster_id'], as_index=False).effective_capacity.sum().rename(columns={'effective_capacity': 'owned_capacity'})
        assigned_total = assigned.groupby(['year', 'cluster_id'], as_index=False).effective_capacity.sum().rename(columns={'effective_capacity': 'allocated_plus_unallocated'})
        check = own.merge(assigned_total, on=['year', 'cluster_id'], how='left')
        check['difference'] = check.owned_capacity - check.allocated_plus_unallocated
        _table(check)
        st.caption('Allocated IPU capacity plus unallocated capacity reconciles to the owned asset register. '
                   'Fractions above 100%, duplicate assets and orphan agreements are rejected on import.')
        with st.expander('Owned asset register for the selected year and resource'):
            _table(total_inv)
        _download('Download supply asset register', inv, 'annual_cluster_supply_assets.csv')
        _download('Download reconciled IPU allocations', assigned, 'annual_cluster_ipu_capacity_allocations.csv')


def _sources(raw, mappings, supply, allocations):
    st.header('Data, classifications and coverage')
    st.write('The existing 26-IPU / 49-pathway catalogue and v0.1 synthetic population, care-use and resource coefficients '
             'are retained. The 20 cluster names come from Health Holding; the application IDs are local identifiers. '
             'No actual cluster population shares, provider Networks, Platform register, code crosswalk or capacity agreements were present.')
    st.markdown('[Health Holding cluster list](https://www.health.sa/en/clusters/list) · '
                '[CHI public-provider coding guidance](https://www.chi.gov.sa/Rules/article11/Documents/5.pdf)')
    st.caption('Cluster names checked 30 October 2026. CHI guidance describes inpatient DRGs and diagnosis coding with ICD-10-AM. '
               'Outpatient procedure and resource requirements need additional service data; a diagnosis code alone is not a capacity requirement.')
    with st.expander('How existing project data are used', expanded=True):
        st.markdown('''- Existing synthetic regional populations are split equally among their clusters. This is an assumption, not official attribution.
- Demand retains the existing agent risks, episode rates, admission probabilities, clinic-visit coefficients and integrated-care scenario. DEMO grouping tokens are not clinical codes.
- Supply freezes the existing synthetic 2025 status-quo baseline and grows it 0.8% annually, independently of the selected demand scenario.
- Two illustrative Networks own beds/clinic rooms. Workforce is partitioned 90% to IPUs and 10% to an illustrative shared clinical Platform. These shares conserve the original baseline; they are not observed organisation records.
- Physical capacity is assumed to be staffed capacity divided by 0.85; funded capacity equals staffed capacity and availability is 100%. These assumptions are not evidence of operational readiness.
- Unmodelled IPUs and missing modalities are shown as unavailable. Proposed and approved labels are retained; imported approval labels are not independently verified.''')
    st.subheader('CSV templates and import rules')
    st.caption('Use the cluster IDs and exact IPU names below. Supply and allocations are separate ledgers. '
               'Blank templates contain headers only and do not imply zero activity or capacity.')
    for label, cols in TEMPLATES:
        with st.expander(label + ' schema'):
            st.code(','.join(cols), language=None)
            _download('Download ' + label.lower() + ' template', pd.DataFrame(columns=cols),
                      label.lower().replace(' ', '_') + '_template.csv')
    st.markdown('''Demand: `setting` is Inpatient or Outpatient; `code_system` is DRG or ICD-10-AM; `edition` must identify the actual version.
Each record is one annual aggregate per cluster, code, edition and series. Outpatient records use a single primary diagnosis per encounter.
Demand `series` is Observed activity, Forecast demand or Synthetic forecast; versions and series are never silently merged.
Mapping keys match exactly on code system, edition and code; one accountable IPU per key. Unknown codes remain Unmapped.
`mapping_status` is Approved, Proposed or Illustrative, with a source for the crosswalk.
Supply `series` is Observed capacity, Planned capacity or Synthetic capacity. `owner_type` is IPU, Network or Platform.
An asset ID represents one resource/unit within one cluster and year. All numeric capacities are required and nonnegative.
Allocation fractions range from 0 to 1; their sum per asset must not exceed 1. Missing shares remain Unallocated.''')
    _table(pd.DataFrame(UNITS.items(), columns=['resource', 'unit']))
    with st.expander('20-cluster reference register'):
        _table(clusters())
        _download('Download cluster register', clusters(), 'cluster_register.csv')
    with st.expander('26-IPU reference portfolio'):
        _table(ipus())
    with st.expander('Loaded code mappings'):
        _table(mappings)
        _download('Download loaded mappings', mappings, 'loaded_code_mappings.csv')
    st.caption(f'Loaded rows: demand {len(raw):,}; mappings {len(mappings):,}; '
               f'supply assets {len(supply):,}; allocation agreements {len(allocations):,}. '
               'Observed activity is not silently forecast into missing years. No full DRG or ICD-10-AM codebook is distributed.')


def render(view):
    st.title('Saudi ACO supply & demand')
    st.caption('Compare clusters. Explore service capacity. Track the evidence still needed.')
    if view in ['Overview','IPU coverage & gaps']:
        mode='Published cluster evidence'
        st.sidebar.caption('This view summarises published evidence. Open demand or supply to choose a simulation or import.')
    else:
        mode = st.sidebar.radio('Data source', ['Published cluster evidence', 'Existing project simulation', 'Import annual CSVs'])
    st.sidebar.divider()
    st.sidebar.markdown('**Planning scope**')
    start, end = st.sidebar.slider('Year range', 2025, 2054, (2025, 2054))
    years = list(range(start, end + 1))
    focus = (st.sidebar.select_slider('Detail year', options=years, value=years[0])
             if len(years) > 1 and mode != 'Published cluster evidence' and view != 'IPU coverage & gaps'
             else years[0])
    names = clusters().set_index('cluster_id').cluster_name.to_dict()
    cluster_ids = st.sidebar.multiselect('Clusters (empty = all 20)', list(names), format_func=names.get)
    cluster_ids = cluster_ids or list(names)
    from .presentation import context
    context(mode,len(cluster_ids),years)
    if mode == 'Published cluster evidence':
        from .published_dashboard import render_published
        if view == 'IPU coverage & gaps' and mode != 'Published cluster evidence':
            st.info('This coverage review describes the bundled public evidence. Imported/synthetic records are shown in the annual demand and supply views.')
        render_published(view, cluster_ids, years)
        return
    integrated, seed = True, 42
    if mode == 'Existing project simulation':
        integrated = st.sidebar.checkbox('ACO integrated-care demand scenario', value=True)
        seed = int(st.sidebar.number_input('Simulation seed', 0, 100000, 42))
    try:
        demand, mapping, supply, allocations = _load(mode, seed, integrated)
        if view == 'Yearly cluster demand':
            _demand(demand, mapping, cluster_ids, years, focus)
        elif view == 'Yearly cluster supply':
            _supply(supply, allocations, cluster_ids, years, focus)
        else:
            _sources(demand, mapping, supply, allocations)
    except (ValueError, KeyError, UnicodeDecodeError, pd.errors.ParserError) as error:
        st.error('Input data could not be used: ' + str(error))
        st.info('Correct the named file using the templates in Data & mappings. No demonstration values are substituted for an invalid import.')
