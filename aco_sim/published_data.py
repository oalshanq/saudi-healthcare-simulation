"""Published cluster observations and complete IPU coverage, without invented attribution."""
import pandas as pd
from .cluster_planning import ROOT, clusters, ipus
from .model import SPECIALTY_IPU, catalogue

# Analyst-selected related service indicators. These are contextual associations,
# NOT clinical code crosswalks, exclusive IPU volumes, or capacity agreements.
CONTEXT = {
    'Population Health, Screening and Immunisation': ['PHC encounters and consultations', 'Primary healthcare centres'],
    'Oral and Dental Health': ['Dental centres', 'Faciodental interventions'],
    'Emergency and Acute Assessment': ['Medical emergency encounters', 'Surgical emergency encounters', 'Emergency department beds'],
    'Acute Medicine and Same-Day Emergency Care': ['Medicine beds'],
    'Acute Coronary Syndrome': ['Cardiology centres'],
    'Stroke': [],
    'Major Trauma': [],
    'Paediatric Medicine': ['Paediatric beds', 'Paediatric ICU beds'],
    'Joint Replacement': [],
    'Cancer': ['Oncology centres'],
    'Cardiac Intervention and Surgery': ['Cardiology centres', 'Cardiac / chest / vascular interventions'],
    'Spine': [],
    'Cataract and Ophthalmic Surgery': ['Ophthalmology interventions'],
    'General and Bariatric Surgery': ['General surgery interventions'],
    'Urology': ['Urology interventions'],
    'ENT and Head-and-Neck': ['ENT interventions'],
    'Cardiometabolic': ['Diabetes clinic encounters', 'Diabetes and endocrinology centres'],
    'Heart Failure': ['Cardiology centres'],
    'Respiratory': [],
    'Musculoskeletal and Rheumatology': [],
    'Frailty and Complex Multimorbidity': [],
    'Neurological Long-Term Conditions': [],
    'Renal and Dialysis': ['Dialysis centres / units'],
    'Maternity and Neonatal': ['Obstetric / gynaecology beds', 'Neonatal ICU beds', 'Obstetric / gynaecology interventions'],
    'Palliative and End of Life': [],
    'Mental Health': ['Psychiatry / neurology beds'],
}
REQUIREMENTS = {
    'Emergency and Acute Assessment': 'ED presentations, triage and disposition; linked admissions; avoid counting an ED visit as an admission.',
    'Acute Coronary Syndrome': 'Confirmed ACS cohorts, principal diagnoses, grouped admissions, interventions and transfer attribution.',
    'Stroke': 'Stroke subtype, admissions, episode boundaries, acute/rehabilitation handover and transfer attribution.',
    'Major Trauma': 'Injury cohorts, severity, grouped admissions and one accountable episode across transfers.',
    'Urology': 'Urology coded admissions and outpatient diagnoses; distinguish procedures from admissions.',
    'Cardiometabolic': 'Primary-diagnosis outpatient counts and grouped admissions; separate overlapping diabetes and cardiovascular cohorts.',
    'Respiratory': 'Respiratory coded admissions and primary-diagnosis encounters, disease cohorts and longitudinal follow-up.',
    'Musculoskeletal and Rheumatology': 'MSK/rheumatology coded encounters; separate chronic management from surgical episodes.',
    'Renal and Dialysis': 'Renal coded admissions, outpatient encounters, dialysis sessions, stations and staffing; sessions are not patients.',
    'Mental Health': 'Mental-health coded episodes, community contacts and dedicated capacity; separate neurology from psychiatry.',
}


def observations():
    result = pd.read_csv(ROOT / 'data/published_observations.csv', keep_default_na=False)
    result['value'] = pd.to_numeric(result.value, errors='coerce')
    result['year'] = result.year.astype(int)
    return result.merge(clusters()[['cluster_id', 'cluster_name']], on='cluster_id', validate='many_to_one')


def snapshots():
    # The source has no reporting year. Never use retrieval year as an observation year.
    result = pd.read_csv(ROOT / 'data/hhc_capacity_snapshots.csv', keep_default_na=False)
    result['value'] = pd.to_numeric(result.value)
    return result.merge(clusters()[['cluster_id', 'cluster_name']], on='cluster_id', validate='many_to_one')


def source_comparison():
    a = observations().query("metric == 'Hospital beds'")[['cluster_id', 'cluster_name', 'value']]
    b = snapshots().query("metric == 'Hospital beds'")[['cluster_id', 'value']]
    result = a.merge(b, on='cluster_id', suffixes=('_2024', '_undated'), validate='one_to_one')
    result['review_status'] = result.apply(lambda r: 'Different published values — period / scope unresolved'
        if r.value_2024 != r.value_undated else 'Same published value — dates still not comparable', axis=1)
    return result


def portfolio():
    frame = ipus()
    assert set(frame.ipu) == set(CONTEXT), 'Every IPU requires an explicit evidence definition.'
    paths = catalogue().groupby('ipu').pathway_id.agg(lambda s: '; '.join(s)).to_dict()
    frame['pathways'] = frame.ipu.map(paths)
    frame['module_status'] = 'Ready for annual coded imports; no validated clinical calibration'
    frame['legacy_model'] = frame.ipu.map(lambda i: 'Synthetic profile available' if i in SPECIALTY_IPU.values()
                                         else 'New coverage module — rate parameters unavailable')
    frame['coded_activity'] = 'Unavailable: no cluster DRG / ICD-10-AM extract found'
    frame['capacity_allocation'] = 'Unavailable: no IPU asset allocation agreement found'
    frame['related_indicators'] = frame.ipu.map(lambda i: '; '.join(CONTEXT[i]) or 'No sufficiently specific published indicator loaded')
    frame['data_needed'] = frame.ipu.map(lambda i: REQUIREMENTS.get(i,
        'Edition-specific coded admissions and outpatient primary diagnoses; accountable IPU crosswalk; staffed/funded assets and capacity agreements.'))
    frame['calibration_needed'] = 'Cohort denominator, annual rates, admission probability, LOS, staff time, visits and shared-resource shares'
    frame['designation'] = frame.system.map(lambda s: 'Seventh System proposed in project' if s == 'Mental Health' else 'Project reference portfolio')
    frame['association_status'] = 'Proposed service-context association only; not a clinical mapping or IPU allocation'
    return frame


def complete_ipu_demand(mapped, cluster_ids, years, setting, series):
    """Materialise every IPU for the chosen scope, retaining missing versus zero."""
    frame = pd.MultiIndex.from_product([years, cluster_ids, ipus().ipu],
                                       names=['year', 'cluster_id', 'ipu']).to_frame(index=False)
    frame = frame.merge(ipus(), on='ipu', validate='many_to_one')
    if not mapped.empty:
        subset = mapped[mapped.setting.eq(setting) & mapped.series.eq(series)]
        totals = subset.groupby(['year', 'cluster_id', 'ipu'], as_index=False).volume.sum(min_count=1)
        frame = frame.merge(totals, on=['year', 'cluster_id', 'ipu'], how='left', validate='one_to_one')
    else:
        frame['volume'] = float('nan')
    frame['status'] = frame.volume.map(lambda n: 'Unavailable — no record for this IPU / cluster / year'
                                      if pd.isna(n) else 'Reported in selected dataset')
    frame['setting'], frame['series'] = setting, series
    return frame.merge(clusters()[['cluster_id', 'cluster_name']], on='cluster_id', validate='many_to_one')


def annual_observations(metric, cluster_ids, years):
    data = observations()
    selected = data[data.metric.eq(metric) & data.cluster_id.isin(cluster_ids)]
    # min_count prevents explicit missing source cells from turning into zero.
    matrix = selected.groupby(['cluster_id', 'year']).value.sum(min_count=1).unstack('year')
    return matrix.reindex(index=cluster_ids, columns=years)


def gap_register(cluster_ids, years):
    frame = pd.MultiIndex.from_product([years, cluster_ids, ipus().ipu],
                                       names=['year', 'cluster_id', 'ipu']).to_frame(index=False)
    frame = frame.merge(ipus(), on='ipu', validate='many_to_one')
    frame['drg_admissions'] = 'Unavailable — cluster / code / edition extract not found'
    frame['icd10am_outpatient'] = 'Unavailable — primary-diagnosis encounter extract not found'
    frame['ipu_capacity'] = 'Unavailable — ownership and allocation register not found'
    frame['forecast'] = 'Uncalibrated — no validated rates or annual capacity plans'
    return frame
