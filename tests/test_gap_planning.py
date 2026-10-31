import numpy as np
import pandas as pd
import pytest
from aco_sim.cluster_planning import demo_data, clusters, ipus, DEMAND_COLUMNS, MAPPING_COLUMNS, SUPPLY_COLUMNS, ALLOCATION_COLUMNS
from aco_sim.gap_planning import (Scenario, demo_coefficients, make_gap_ledger, summarize, COEFFICIENT_COLUMNS, validate_coefficients)
from aco_sim.model import make_population, make_agents, simulate

@pytest.fixture(scope='module')
def demo():
    return demo_data(start=2025,end=2026)


def ledger(demo, resource='Beds', scenario=Scenario(), coefficients=None, years=(2025,2026), confirmed=True):
    return make_gap_ledger(*demo, demo_coefficients(resource) if coefficients is None else coefficients,
        ['RYD1'],list(years),resource,'Inpatient' if resource=='Beds' else 'Outpatient',
        'Synthetic forecast','Synthetic capacity','DEMO-v0.1',scenario,scope_confirmed=confirmed)[0]


def test_original_resource_equations_match(demo):
    # Independent original engine comparison, using the same regional split/agents.
    pop=clusters().merge(make_population().rename(columns={'Region':'region'}),on='region')
    pop['Population']=pop.Population / pop.groupby('region').cluster_id.transform('count')
    agents=make_agents(pop.rename(columns={'cluster_id':'Region'}))
    original=simulate(agents,2025,integrated=True)
    for resource in ['Beds','Outpatient_Clinics','Physicians','Nurses']:
        actual=ledger(demo,resource).query('year == 2025').set_index('ipu').baseline_demand.dropna().sort_index()
        expected=original.query('Region == "RYD1" and Resource == @resource').groupby('IPU').Demand.sum().sort_index()
        assert np.allclose(actual,expected,rtol=1e-12)


def test_missing_ipus_remain_missing_and_totals_are_partial(demo):
    result=ledger(demo)
    assert len(result)==52 and result.comparable.sum()==32
    assert result.loc[~result.comparable,'scenario_gap'].isna().all()
    assert set(result.loc[result.comparable,'result_status'])=={'Synthetic estimate — unvalidated'}
    summary=summarize(result,['year'])
    assert (summary.comparable_pairs==16).all() and (summary.expected_pairs==26).all()
    assert (summary.coverage=='Partial comparable subtotal').all()
    assert np.allclose(summary.shortage-summary.surplus,summary.scenario_gap)


def test_scenario_is_identity_and_fixed_2025_anchor(demo):
    base=ledger(demo)
    assert np.allclose(base.baseline_gap,base.scenario_gap,equal_nan=True)
    adjusted=ledger(demo,scenario=Scenario(20,10,-10,5),years=(2026,))
    assert np.allclose(adjusted.demand_factor,1.2*1.1)
    assert np.allclose(adjusted.supply_factor,.9*1.05)
    assert np.allclose(adjusted.scenario_demand,adjusted.baseline_demand*1.32,equal_nan=True)
    assert np.allclose(adjusted.scenario_supply,adjusted.baseline_supply*.945,equal_nan=True)
    year2054=ledger(demo,scenario=Scenario(0,10,0,5),years=(2054,))
    assert np.allclose(year2054.demand_factor,1.1**29)
    assert year2054.scenario_gap.isna().all()  # No extrapolation of absent records.


def test_partial_coefficients_invalidate_whole_ipu_not_zero(demo):
    co=demo_coefficients('Beds')
    # Maternity has Obstetrics and Gynecology; dropping one must invalidate entire IPU.
    result=ledger(demo,coefficients=co[co.code.ne('DEMO-IN-04')])
    maternity=result[result.ipu.eq('Maternity and Neonatal')]
    assert maternity.activity.notna().all()
    assert maternity.baseline_demand.isna().all() and maternity.scenario_gap.isna().all()
    assert maternity.data_gap.str.contains('Missing resource coefficient').all()
    zero=ledger(demo,coefficients=co.assign(requirement_per_activity=0))
    assert (zero.loc[zero.comparable,'baseline_demand']==0).all()
    assert zero.gap_pct_required.isna().all()


def test_missing_supply_and_unconfirmed_scope_never_report_gap(demo):
    d,m,s,a=demo
    no_alloc=(d,m,s,pd.DataFrame(columns=ALLOCATION_COLUMNS))
    result=ledger(no_alloc)
    assert result.baseline_supply.isna().all() and result.scenario_gap.isna().all()
    assert ledger(demo,confirmed=False).scenario_gap.isna().all()


def test_empty_actuals_are_unresolved():
    inputs=tuple(pd.DataFrame(columns=c) for c in [DEMAND_COLUMNS,MAPPING_COLUMNS,SUPPLY_COLUMNS,ALLOCATION_COLUMNS])
    result,_,_=make_gap_ledger(*inputs,pd.DataFrame(columns=COEFFICIENT_COLUMNS),['RYD1'],[2025,2054],
       'Beds','Inpatient','Unavailable','Unavailable','Unavailable')
    assert len(result)==52 and result.scenario_gap.isna().all()
    assert summarize(result,['year']).scenario_gap.isna().all()


def test_coefficients_reject_duplicates_units_and_infinity():
    co=demo_coefficients('Beds').iloc[:1]
    with pytest.raises(ValueError,match='duplicate'):
        validate_coefficients(pd.concat([co,co]))
    with pytest.raises(ValueError,match='incompatible'):
        validate_coefficients(co.assign(unit='FTE'))
    with pytest.raises(ValueError,match='finite'):
        validate_coefficients(co.assign(requirement_per_activity=np.inf))


def test_unmapped_activity_retained_and_wrong_edition_is_missing(demo):
    d,m,s,a=demo
    result=ledger((d,m[m.code.ne('DEMO-IN-01')],s,a))
    assert result.ipu.eq('Unmapped').sum()==2
    assert result[result.ipu.eq('Unmapped')].scenario_gap.isna().all()
    wrong=demo_coefficients('Beds').assign(edition='wrong')
    assert ledger(demo,coefficients=wrong).scenario_gap.isna().all()


def test_imported_actual_inputs_never_make_estimates_actual():
    ipu=ipus().iloc[0]
    d=pd.DataFrame([['r',2025,'RYD1','Inpatient','DRG','v1','A',100,'Observed activity','Activity source']],columns=DEMAND_COLUMNS)
    m=pd.DataFrame([['DRG','v1','A',ipu.system,ipu.ipu,'Approved','Mapping source']],columns=MAPPING_COLUMNS)
    s=pd.DataFrame([[2025,'RYD1','a','Network','n','Network','Beds','beds',10,10,10,1,'Observed capacity','Register']],columns=SUPPLY_COLUMNS)
    a=pd.DataFrame([[2025,'RYD1','a',ipu.ipu,1,'Agreement']],columns=ALLOCATION_COLUMNS)
    c=pd.DataFrame([['DRG','v1','A','Beds','beds',.2,'Assumed coefficient']],columns=COEFFICIENT_COLUMNS)
    out,_,_=make_gap_ledger(d,m,s,a,c,['RYD1'],[2025], 'Beds','Inpatient','Observed activity','Observed capacity','v1',Scenario(10,0,0,0))
    row=out[out.ipu.eq(ipu.ipu)].iloc[0]
    assert row.baseline_demand==20 and row.baseline_gap==10 and row.scenario_gap==12
    assert row.activity_status=='Observed activity' and row.capacity_status=='Observed capacity'
    assert row.result_status=='Calculated estimate — imported assumptions'
    assert row.coefficient_source=='Assumed coefficient' and row.allocation_source=='Agreement'
