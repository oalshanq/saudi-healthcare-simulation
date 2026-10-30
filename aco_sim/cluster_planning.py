"""Annual coded activity and capacity ledgers; no DRG grouper or codebook implied."""
from pathlib import Path
import numpy as np
import pandas as pd
from .model import catalogue, make_population, make_agents, simulate, PROFILES, SPECIALTY_IPU

ROOT = Path(__file__).resolve().parents[1]
DEMAND_COLUMNS = ['record_id', 'year', 'cluster_id', 'setting', 'code_system',
                  'edition', 'code', 'volume', 'series', 'source']
MAPPING_COLUMNS = ['code_system', 'edition', 'code', 'system', 'ipu', 'mapping_status', 'source']
SUPPLY_COLUMNS = ['year', 'cluster_id', 'asset_id', 'owner_type', 'owner_id', 'owner_name',
                  'resource', 'unit', 'physical_capacity', 'staffed_capacity',
                  'funded_capacity', 'availability_fraction', 'series', 'source']
ALLOCATION_COLUMNS = ['year', 'cluster_id', 'asset_id', 'ipu', 'allocated_fraction', 'source']
KEY = ['code_system', 'edition', 'code']
ASSET_KEY = ['year', 'cluster_id', 'asset_id']
UNITS = {'Beds': 'beds', 'Physicians': 'FTE', 'Nurses': 'FTE',
         'Outpatient_Clinics': 'rooms', 'Theatre_hours': 'hours/year',
         'Imaging_slots': 'slots/year', 'Laboratory_tests': 'tests/year'}
DEMAND_SERIES = ['Observed activity', 'Forecast demand', 'Synthetic forecast']
SUPPLY_SERIES = ['Observed capacity', 'Planned capacity', 'Synthetic capacity']


def clusters():
    return pd.read_csv(ROOT / 'data/clusters.csv', dtype=str)


def ipus():
    return catalogue()[['system', 'ipu']].drop_duplicates().reset_index(drop=True)


def _frame(df, columns, name):
    missing = set(columns) - set(df.columns)
    if missing:
        raise ValueError(f'{name}: missing columns: {", ".join(sorted(missing))}')
    result = df[columns].copy()
    for c in result:
        if result[c].isna().any():
            raise ValueError(f'{name}: {c} has missing values; missing capacity is not zero.')
        if result[c].dtype == object or pd.api.types.is_string_dtype(result[c]):
            result[c] = result[c].astype(str).str.strip()
            if result[c].eq('').any():
                raise ValueError(f'{name}: {c} has blank values.')
    return result


def _numeric(df, columns, name):
    for c in columns:
        df[c] = pd.to_numeric(df[c], errors='coerce')
        if not np.isfinite(df[c].to_numpy(dtype=float)).all() or (df[c] < 0).any():
            raise ValueError(f'{name}: {c} must be finite and nonnegative.')
    return df


def _years_and_clusters(df, name):
    _numeric(df, ['year'], name)
    if ((df.year % 1 != 0) | (df.year < 1900) | (df.year > 2200)).any():
        raise ValueError(f'{name}: year must be an integer between 1900 and 2200.')
    df['year'] = df.year.astype(int)
    unknown = set(df.cluster_id) - set(clusters().cluster_id)
    if unknown:
        raise ValueError(f'{name}: unknown cluster IDs: {", ".join(sorted(unknown))}')


def validate_demand(df):
    df = _frame(df, DEMAND_COLUMNS, 'Demand')
    _years_and_clusters(df, 'Demand')
    _numeric(df, ['volume'], 'Demand')
    if df.record_id.duplicated().any():
        raise ValueError('Demand: record_id must be unique.')
    if not set(df.series).issubset(DEMAND_SERIES):
        raise ValueError('Demand: series must be Observed activity, Forecast demand or Synthetic forecast.')
    expected = {'Inpatient': {'DRG', 'DEMO-DRG'},
                'Outpatient': {'ICD-10-AM', 'DEMO-ICD-10-AM'}}
    if any(s not in expected or c not in expected[s] for s, c in zip(df.setting, df.code_system)):
        raise ValueError('Demand: inpatient rows require DRG; outpatient rows require ICD-10-AM.')
    demo = df.code_system.str.startswith('DEMO-') | df.code.str.startswith('DEMO-')
    if (demo & df.series.ne('Synthetic forecast')).any():
        raise ValueError('Demand: DEMO codes cannot be labelled observed activity or actual forecast demand.')
    if (df.loc[df.series.eq('Observed activity'), 'volume'] % 1 != 0).any():
        raise ValueError('Demand: observed activity must count whole admissions or encounters.')
    grain = ['year', 'cluster_id', 'setting', *KEY, 'series']
    if df.duplicated(grain).any():
        raise ValueError('Demand: duplicate annual code aggregates. Submit one count per cluster/year/code/series.')
    return df


def validate_mappings(df):
    df = _frame(df, MAPPING_COLUMNS, 'Mappings')
    if df.duplicated(KEY).any():
        raise ValueError('Mappings: each code and edition must have one accountable IPU; ambiguous mappings are rejected.')
    if not set(df.code_system).issubset({'DRG', 'ICD-10-AM', 'DEMO-DRG', 'DEMO-ICD-10-AM'}):
        raise ValueError('Mappings: unsupported code_system.')
    if not set(df.mapping_status).issubset({'Approved', 'Proposed', 'Illustrative'}):
        raise ValueError('Mappings: mapping_status must be Approved, Proposed or Illustrative.')
    permitted = set(ipus().itertuples(index=False, name=None))
    if any(pair not in permitted for pair in df[['system', 'ipu']].itertuples(index=False, name=None)):
        raise ValueError('Mappings: System of Care and IPU must match the existing 26-IPU catalogue.')
    return df


def map_demand(demand, mappings):
    d, m = validate_demand(demand), validate_mappings(mappings)
    m = m.rename(columns={'source': 'mapping_source'})
    out = d.merge(m, on=KEY, how='left', validate='many_to_one', indicator=True)
    for column in ['system', 'ipu', 'mapping_status']:
        out[column] = out[column].fillna('Unmapped')
    out['mapping_source'] = out.mapping_source.fillna('No exact code / edition match')
    return out.drop(columns='_merge').merge(clusters()[['cluster_id', 'cluster_name']], on='cluster_id', validate='many_to_one')


def validate_supply(df):
    df = _frame(df, SUPPLY_COLUMNS, 'Supply')
    _years_and_clusters(df, 'Supply')
    _numeric(df, ['physical_capacity', 'staffed_capacity', 'funded_capacity', 'availability_fraction'], 'Supply')
    if df.duplicated(ASSET_KEY).any():
        raise ValueError('Supply: an asset must occur once per cluster/year, with one owner and one resource/unit.')
    if not set(df.owner_type).issubset({'IPU', 'Network', 'Platform'}):
        raise ValueError('Supply: owner_type must be IPU, Network or Platform.')
    if not set(df.series).issubset(SUPPLY_SERIES):
        raise ValueError('Supply: unsupported capacity series.')
    if any(UNITS.get(r) != u for r, u in zip(df.resource, df.unit)):
        raise ValueError('Supply: invalid resource/unit pair; use the documented template units.')
    if ((df.staffed_capacity > df.physical_capacity) | (df.funded_capacity > df.physical_capacity)).any():
        raise ValueError('Supply: staffed and funded capacity cannot exceed physical/established capacity.')
    if (df.availability_fraction > 1).any():
        raise ValueError('Supply: availability_fraction must be between 0 and 1.')
    own = df[df.owner_type.eq('IPU')]
    if not set(own.owner_name).issubset(set(ipus().ipu)):
        raise ValueError('Supply: IPU owner_name must match a reference IPU.')
    df['effective_capacity'] = df[['physical_capacity', 'staffed_capacity', 'funded_capacity']].min(axis=1) * df.availability_fraction
    return df


def allocate_supply(supply, allocations):
    s = validate_supply(supply)
    a = _frame(allocations, ALLOCATION_COLUMNS, 'Allocations')
    _years_and_clusters(a, 'Allocations')
    _numeric(a, ['allocated_fraction'], 'Allocations')
    if a.duplicated([*ASSET_KEY, 'ipu']).any():
        raise ValueError('Allocations: duplicate asset/IPU agreement.')
    if not set(a.ipu).issubset(set(ipus().ipu)):
        raise ValueError('Allocations: unknown IPU.')
    amounts = a.groupby(ASSET_KEY, as_index=False).allocated_fraction.sum()
    if (amounts.allocated_fraction > 1 + 1e-9).any():
        raise ValueError('Allocations: fractions for one asset exceed 100%; shared capacity would be double counted.')
    orphan = a.merge(s[ASSET_KEY], on=ASSET_KEY, how='left', indicator=True)
    if orphan._merge.eq('left_only').any():
        raise ValueError('Allocations: an agreement refers to a missing asset/year/cluster.')
    out = a.rename(columns={'source': 'allocation_source'}).merge(s, on=ASSET_KEY, how='left', validate='many_to_one')
    out = out.merge(ipus(), on='ipu', validate='many_to_one')
    for col in ['physical_capacity', 'staffed_capacity', 'funded_capacity', 'effective_capacity']:
        out[col] = out[col] * out.allocated_fraction
    remainder = s.merge(amounts, on=ASSET_KEY, how='left')
    remainder['allocated_fraction'] = 1 - remainder.allocated_fraction.fillna(0).clip(0, 1)
    remainder = remainder[remainder.allocated_fraction > 1e-9].copy()
    remainder['ipu'] = 'Unallocated'
    remainder['system'] = 'Unallocated'
    remainder['allocation_source'] = 'No IPU allocation provided for this share'
    for col in ['physical_capacity', 'staffed_capacity', 'funded_capacity', 'effective_capacity']:
        remainder[col] = remainder[col] * remainder.allocated_fraction
    return s, pd.concat([out, remainder], ignore_index=True)


def annual_matrix(df, value, cluster_ids, years):
    """Absent cluster-years stay missing, including entirely unreported years."""
    registry = clusters().set_index('cluster_id')
    if df.empty:
        result = pd.DataFrame(index=cluster_ids, columns=years, dtype=float)
    else:
        result = df.groupby(['cluster_id', 'year'])[value].sum().unstack('year')
        result = result.reindex(index=cluster_ids, columns=years)
    result.index = [registry.loc[c, 'cluster_name'] for c in result.index]
    result.index.name = 'Cluster'
    return result


def demo_data(seed=42, integrated=True, start=2025, end=2054):
    """Reuse v0.1 populations/profiles; all splits and code tokens are illustrative.

    Supply freezes the existing model's 2025 status-quo synthetic baseline and
    projects it at 0.8%/year. It does not recalculate supply from current demand.
    """
    reg = clusters()
    pop = make_population(seed).rename(columns={'Region': 'region'})
    pop = reg.merge(pop, on='region', validate='many_to_one')
    pop['Population'] = pop.Population / pop.groupby('region').cluster_id.transform('count')
    agents = make_agents(pop.rename(columns={'cluster_id': 'Region'}), seed=seed)
    systems = ipus().set_index('ipu').system.to_dict()
    maps, demand = [], []
    for i, specialty in enumerate(PROFILES):
        ipu = SPECIALTY_IPU[specialty]
        for setting, cs in [('Inpatient', 'DEMO-DRG'), ('Outpatient', 'DEMO-ICD-10-AM')]:
            maps.append([cs, 'DEMO-v0.1', f'DEMO-{setting[:2].upper()}-{i+1:02}',
                         systems[ipu], ipu, 'Illustrative', f'Existing v0.1 specialty-IPU crosswalk: {specialty}; not a clinical code map'])
    prepared = []
    for cid, g in agents.groupby('Region'):
        weights, risks = g.Weight.to_numpy(), g.Risk.to_numpy()
        prepared.append((cid, weights, risks, np.average(risks, weights=weights)))
    for year in range(start, end + 1):
        rng = np.random.default_rng(seed + year)
        for cid, weights, risks, risk in prepared:
            for i, (specialty, (rate, admit, los, doc, nurse, visits)) in enumerate(PROFILES.items()):
                ep_rate = rate * risk * (1 + .006 * (year - 2025)) * (.88 if integrated else 1.)
                episodes = float(np.dot(rng.poisson(np.maximum(0, ep_rate * risks / risk)), weights))
                for setting, cs, volume in [('Inpatient', 'DEMO-DRG', episodes * admit),
                                             ('Outpatient', 'DEMO-ICD-10-AM', episodes * visits)]:
                    code = f'DEMO-{setting[:2].upper()}-{i+1:02}'
                    demand.append([f'{cid}-{year}-{code}', year, cid, setting, cs,
                                   'DEMO-v0.1', code, volume, 'Synthetic forecast',
                                   f'v0.1 agents and {specialty} coefficients; equal regional cluster split; not coded activity'])
    baseline = simulate(agents, 2025, integrated=False, seed=seed).groupby(['Region', 'IPU', 'Resource'], as_index=False).Supply.sum()
    base_assets, base_alloc = [], []

    def add_asset(cid, asset, owner_type, owner_id, owner_name, resource, capacity, shares):
        base_assets.append([cid, asset, owner_type, owner_id, owner_name, resource, UNITS[resource], capacity])
        for ipu, share in shares:
            base_alloc.append([cid, asset, ipu, share])

    for cid, group in baseline.groupby('Region'):
        for res, resource_rows in group.groupby('Resource'):
            total = resource_rows.Supply.sum()
            shares = [(r.IPU, r.Supply / total) for r in resource_rows.itertuples() if total > 0]
            if res in ['Beds', 'Outpatient_Clinics']:
                for network in [1, 2]:
                    add_asset(cid, f'{cid}-N{network}-{res}', 'Network', f'{cid}-N{network}',
                              f'Illustrative Network {network}', res, total / 2, shares)
            else:
                # Transfer a 10% share of the baseline workforce to one shared
                # platform; do not add the same people to two inventories.
                for j, row in enumerate(resource_rows.itertuples()):
                    add_asset(cid, f'{cid}-IPU{j:02}-{res}', 'IPU', f'{cid}-IPU{j:02}',
                              row.IPU, res, row.Supply * .9, [(row.IPU, 1.)])
                add_asset(cid, f'{cid}-PL1-{res}', 'Platform', f'{cid}-PL1',
                          'Illustrative shared clinical platform', res, total * .1, shares)
    assets = pd.DataFrame(base_assets, columns=['cluster_id', 'asset_id', 'owner_type', 'owner_id', 'owner_name', 'resource', 'unit', 'baseline_capacity'])
    years = pd.DataFrame({'year': range(start, end + 1)})
    assets = assets.merge(years, how='cross')
    cap = assets.baseline_capacity * (1.008 ** (assets.year - 2025))
    assets['physical_capacity'] = cap / .85
    assets['staffed_capacity'] = cap
    assets['funded_capacity'] = cap
    assets['availability_fraction'] = 1.
    assets['series'] = 'Synthetic capacity'
    assets['source'] = 'Frozen v0.1 2025 synthetic supply; 0.8% annual growth; illustrative ownership and staffing assumptions'
    allocations = pd.DataFrame(base_alloc, columns=['cluster_id', 'asset_id', 'ipu', 'allocated_fraction']).merge(years, how='cross')
    allocations['source'] = 'Illustrative allocation only; no actual capacity agreement or operational attribution'
    return (pd.DataFrame(demand, columns=DEMAND_COLUMNS),
            pd.DataFrame(maps, columns=MAPPING_COLUMNS),
            assets[SUPPLY_COLUMNS], allocations[ALLOCATION_COLUMNS])
