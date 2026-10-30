import numpy as np
import pandas as pd
import pytest
from aco_sim.cluster_planning import (
    demo_data, clusters, ipus, map_demand, validate_demand, validate_mappings,
    validate_supply, allocate_supply, annual_matrix, SUPPLY_COLUMNS, ALLOCATION_COLUMNS,
)


@pytest.fixture(scope='module')
def demo():
    return demo_data(start=2025, end=2026)


def test_portfolio_and_year_cluster_coverage(demo):
    d, m, s, a = demo
    mapped = map_demand(d, m)
    assert clusters().cluster_id.nunique() == 20
    assert len(ipus()) == 26
    assert len(mapped.groupby(['year', 'cluster_id', 'setting'])) == 2 * 20 * 2
    assert set(mapped.mapping_status) == {'Illustrative'}
    assert mapped.ipu.ne('Unmapped').all()
    # Do not fabricate activity for the reference IPUs without a v0.1 profile.
    assert mapped.ipu.nunique() < 26


def test_exact_edition_mapping_and_unmapped_conservation(demo):
    d, m, *_ = demo
    changed = d.iloc[:3].copy()
    changed.loc[changed.index[0], 'edition'] = 'different-edition'
    result = map_demand(changed, m)
    assert len(result) == 3
    assert result.iloc[0].ipu == 'Unmapped'
    assert result.volume.sum() == changed.volume.sum()
    assert result.iloc[1].ipu != 'Unmapped'


def test_ambiguous_mapping_is_rejected(demo):
    with pytest.raises(ValueError, match='one accountable IPU'):
        validate_mappings(pd.concat([demo[1], demo[1].iloc[:1]]))


@pytest.mark.parametrize('bad_value', [-1, np.inf, 'invalid'])
def test_bad_volumes_are_rejected(demo, bad_value):
    d = demo[0].iloc[:1].copy().astype({'volume': object})
    d.loc[d.index[0], 'volume'] = bad_value
    with pytest.raises(ValueError, match='finite and nonnegative'):
        validate_demand(d)


def test_duplicate_counts_and_mislabelled_demo_are_rejected(demo):
    d = demo[0].iloc[:1].copy()
    dup = d.copy(); dup['record_id'] = 'different-record-id'
    with pytest.raises(ValueError, match='duplicate annual code'):
        validate_demand(pd.concat([d, dup]))
    d['series'] = 'Observed activity'
    with pytest.raises(ValueError, match='DEMO codes cannot'):
        validate_demand(d)


def test_supply_is_independent_of_demand_scenario(demo):
    other = demo_data(integrated=False, start=2025, end=2026)
    assert not np.allclose(demo[0].volume, other[0].volume)
    pd.testing.assert_frame_equal(demo[2], other[2])
    pd.testing.assert_frame_equal(demo[3], other[3])


def test_owned_assets_and_ipu_allocations_conserve_all_resources(demo):
    s, assigned = allocate_supply(demo[2], demo[3])
    assert set(s.owner_type) == {'IPU', 'Network', 'Platform'}
    keys = ['year', 'cluster_id', 'resource', 'unit']
    for col in ['physical_capacity', 'staffed_capacity', 'funded_capacity', 'effective_capacity']:
        own = s.groupby(keys)[col].sum().sort_index()
        shared = assigned.groupby(keys)[col].sum().sort_index()
        assert np.allclose(own, shared, rtol=1e-12, atol=1e-10)


def test_overallocation_orphans_and_duplicate_assets_rejected(demo):
    s, a = demo[2], demo[3]
    a = a.copy(); a.loc[a.index[0], 'allocated_fraction'] = 2
    with pytest.raises(ValueError, match='exceed 100%'):
        allocate_supply(s, a)
    a = demo[3].iloc[:1].copy(); a['asset_id'] = 'does-not-exist'
    with pytest.raises(ValueError, match='missing asset'):
        allocate_supply(s, a)
    with pytest.raises(ValueError, match='once per cluster/year'):
        validate_supply(pd.concat([s, s.iloc[:1]]))


def test_unallocated_capacity_is_retained_and_missing_is_not_zero(demo):
    raw = demo[2].iloc[:1].copy()
    s, a = allocate_supply(raw, pd.DataFrame(columns=ALLOCATION_COLUMNS))
    assert set(a.ipu) == {'Unallocated'}
    assert np.allclose(a.effective_capacity, s.effective_capacity)
    matrix = annual_matrix(s, 'effective_capacity', [raw.iloc[0].cluster_id, 'RYD1'], [2025, 2030])
    assert matrix[2030].isna().all()


def test_imported_versions_and_series_do_not_silently_merge(demo):
    d = demo[0].iloc[:1].copy()
    d['code_system'] = 'DRG'; d['code'] = 'IMPORT-CODE'; d['edition'] = 'Provider edition A'
    d['series'] = 'Observed activity'; d['volume'] = 10
    second = d.copy(); second['edition'] = 'Provider edition B'; second['record_id'] = 'edition-b'
    validated = validate_demand(pd.concat([d, second]))
    assert len(validated) == 2
    with pytest.raises(ValueError, match='require DRG'):
        validate_demand(d.assign(code_system='ICD-10-AM'))
