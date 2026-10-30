import pandas as pd
from aco_sim.published_data import (
    observations, snapshots, source_comparison, portfolio, complete_ipu_demand,
    annual_observations, gap_register,
)
from aco_sim.cluster_planning import ROOT, clusters, ipus


def test_public_source_controls_and_unique_grain():
    data = observations()
    assert len(data) == 780
    assert not data.duplicated(['year','cluster_id','metric']).any()
    checks = pd.read_csv(ROOT/'data/published_reconciliation.csv')
    sums = data.groupby('metric').value.sum(min_count=1)
    for row in checks.itertuples():
        assert sums[row.metric] == row.cluster_sum
        assert row.cluster_sum + row.source_unassigned == row.published_total
    assert sums['Hospital beds'] == 46905
    assert sums['Hospital admissions'] == 1876723
    assert sums['Hospital outpatient encounters'] == 16796225
    assert checks.set_index('metric').loc['PHC encounters and consultations','source_unassigned'] == 16783


def test_missing_source_cell_and_observed_zero_are_distinct():
    data = observations()
    lab = data.query("metric == 'Central / regional laboratories' and cluster_id == 'JED2'")
    assert lab.value.isna().all()
    zero = data.query("metric == 'General beds' and cluster_id == 'RYD1'")
    assert zero.value.iloc[0] == 0
    missing = annual_observations('Central / regional laboratories',['JED2'],[2024,2025,2054])
    assert missing.isna().all().all()


def test_no_future_actuals_or_undated_year_imputation():
    matrix = annual_observations('Hospital beds',clusters().cluster_id.tolist(),[2024,2025,2054])
    assert matrix[2024].sum() == 46905
    assert matrix[[2025,2054]].isna().all().all()
    snapshot = snapshots()
    assert len(snapshot) == 80 and snapshot.year.eq('').all()
    assert snapshot.query("cluster_id == 'RYD1' and metric == 'Hospital beds'").value.iloc[0] == 4000
    compare=source_comparison().set_index('cluster_id')
    assert compare.loc['TAB','value_2024'] == 1920
    assert compare.loc['TAB','value_undated'] == 1488
    assert compare.loc['TAB','review_status'].startswith('Different')


def test_26_modules_and_ten_uncalibrated_extensions():
    modules = portfolio()
    assert len(modules) == 26
    assert modules.legacy_model.str.startswith('New coverage').sum() == 10
    assert modules.pathways.str.split('; ').map(len).sum() == 49
    assert modules.coded_activity.str.startswith('Unavailable').all()
    assert modules.query("system == 'Mental Health'").designation.str.contains('proposed').all()
    assert len(gap_register(['RYD1'],[2025,2054])) == 52


def test_complete_grid_preserves_missing_zero_and_scope():
    ipu=ipus().ipu.iloc[0]
    rows=pd.DataFrame([dict(year=2025,cluster_id='RYD1',ipu=ipu,volume=0,setting='Inpatient',series='Observed activity'),
                       dict(year=2025,cluster_id='RYD1',ipu=ipu,volume=90,setting='Outpatient',series='Observed activity')])
    result=complete_ipu_demand(rows,['RYD1','RYD2'],[2025,2054],'Inpatient','Observed activity')
    assert len(result) == 104
    assert result.volume.notna().sum() == 1
    assert result.volume.dropna().iloc[0] == 0
    assert result.query('year == 2054').volume.isna().all()


def test_every_new_ipu_accepts_separate_coded_and_capacity_records():
    from aco_sim.cluster_planning import map_demand, allocate_supply
    # Test-only tokens exercise exact matching, not clinical coding validity.
    new = portfolio()[portfolio().legacy_model.str.startswith('New coverage')]
    demand, maps, assets, shares = [], [], [], []
    for n,row in enumerate(new.itertuples()):
        token=f'TEST-{n}'
        demand.append(dict(record_id=token,year=2025,cluster_id='RYD1',setting='Inpatient',
            code_system='DRG',edition='TEST-EDITION',code=token,volume=10,series='Observed activity',source='Unit-test fixture'))
        maps.append(dict(code_system='DRG',edition='TEST-EDITION',code=token,system=row.system,ipu=row.ipu,
            mapping_status='Proposed',source='Unit-test fixture'))
        assets.append(dict(year=2025,cluster_id='RYD1',asset_id=token,owner_type='Network',owner_id='TEST',
            owner_name='Test network',resource='Beds',unit='beds',physical_capacity=10,staffed_capacity=8,
            funded_capacity=7,availability_fraction=.5,series='Observed capacity',source='Unit-test fixture'))
        shares.append(dict(year=2025,cluster_id='RYD1',asset_id=token,ipu=row.ipu,allocated_fraction=1,source='Unit-test fixture'))
    mapped=map_demand(pd.DataFrame(demand),pd.DataFrame(maps))
    inventory, assigned=allocate_supply(pd.DataFrame(assets),pd.DataFrame(shares))
    assert mapped.ipu.nunique()==10 and mapped.volume.sum()==100
    assert assigned.ipu.nunique()==10 and assigned.effective_capacity.sum()==35
    assert assigned.effective_capacity.sum()==inventory.effective_capacity.sum()
