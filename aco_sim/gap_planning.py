"""Unit-compatible scenario comparisons; missing evidence is never zero capacity."""
from dataclasses import dataclass, asdict
import numpy as np
import pandas as pd
from .cluster_planning import (
    KEY, UNITS, clusters, ipus, map_demand, allocate_supply, _frame, _numeric,
)
from .model import PROFILES

COEFFICIENT_COLUMNS = [*KEY, 'resource', 'unit', 'requirement_per_activity', 'source']
GRAIN = ['year', 'cluster_id', 'ipu']


@dataclass(frozen=True)
class Scenario:
    demand_change_pct: float = 0
    demand_growth_pct: float = 0
    supply_change_pct: float = 0
    supply_growth_pct: float = 0

    def factors(self, years):
        values = np.array(list(asdict(self).values()), dtype=float)
        if not np.isfinite(values).all() or (values < -100).any():
            raise ValueError('Scenario percentages must be finite and at least -100%.')
        if ((years < 2025) | (years > 2054)).any():
            raise ValueError('Scenario years must be within 2025–2054.')
        elapsed = years - 2025
        return ((1 + self.demand_change_pct / 100) * (1 + self.demand_growth_pct / 100) ** elapsed,
                (1 + self.supply_change_pct / 100) * (1 + self.supply_growth_pct / 100) ** elapsed)


def validate_coefficients(frame):
    result = _frame(frame, COEFFICIENT_COLUMNS, 'Resource coefficients')
    _numeric(result, ['requirement_per_activity'], 'Resource coefficients')
    if result.duplicated([*KEY, 'resource']).any():
        raise ValueError('Resource coefficients: duplicate code / edition / resource.')
    if any(UNITS.get(r) != u for r, u in zip(result.resource, result.unit)):
        raise ValueError('Resource coefficients: incompatible resource / unit.')
    if not set(result.code_system).issubset({'DRG', 'ICD-10-AM', 'DEMO-DRG', 'DEMO-ICD-10-AM'}):
        raise ValueError('Resource coefficients: unsupported code system.')
    return result


def demo_coefficients(resource):
    """Re-express existing v0.1 equations against the very same annual activity.

    Workforce uses outpatient volume / visits to recover synthetic episodes,
    including the inpatient nursing workload. It is not outpatient-only staffing.
    """
    rows = []
    for i, (_, admit, los, doc, nurse, visits) in enumerate(PROFILES.values()):
        if resource == 'Beds':
            cs, code, factor = 'DEMO-DRG', f'DEMO-IN-{i+1:02}', los / (365 * .82)
        else:
            cs, code = 'DEMO-ICD-10-AM', f'DEMO-OU-{i+1:02}'
            factor = {'Outpatient_Clinics': 1 / (240 * 8 * 2.2),
                      'Physicians': doc / (visits * 1550),
                      'Nurses': (nurse + admit * los * 2.5) / (visits * 1550)}.get(resource)
        if factor is not None:
            rows.append([cs, 'DEMO-v0.1', code, resource, UNITS[resource], factor,
                         'Existing v0.1 synthetic resource equation; uncalibrated'])
    return pd.DataFrame(rows, columns=COEFFICIENT_COLUMNS)


def _sources(values):
    return '; '.join(sorted(set(values.dropna().astype(str))))


def make_gap_ledger(demand, mappings, supply, allocations, coefficients, cluster_ids, years,
                    resource, setting, demand_series, supply_series, edition,
                    scenario=Scenario(), scope_confirmed=True):
    """One annual row per cluster/reference IPU, plus any unmapped activity.

    Caller explicitly selects one coding edition and one demand/capacity series.
    No automatic forecasts, observation carry-forward, or invented allocations.
    """
    if resource not in UNITS:
        raise ValueError('Unknown resource.')
    if setting not in ['Inpatient', 'Outpatient']:
        raise ValueError('Select one service setting.')
    mapped = map_demand(demand, mappings)
    inventory, assigned = allocate_supply(supply, allocations)
    coefficients = validate_coefficients(coefficients)
    d = mapped[mapped.cluster_id.isin(cluster_ids) & mapped.year.isin(years)
               & mapped.setting.eq(setting) & mapped.series.eq(demand_series) & mapped.edition.eq(edition)].copy()
    c = coefficients[coefficients.resource.eq(resource)].rename(columns={'source': 'coefficient_source'})
    d = d.merge(c, on=KEY, how='left', validate='many_to_one')
    d['required'] = d.volume * d.requirement_per_activity
    totals = []
    for key, group in d.groupby(GRAIN, sort=False):
        missing = int(group.requirement_per_activity.isna().sum())
        totals.append([*key, group.volume.sum(), group.required.sum() if not missing else np.nan,
                       missing, _sources(group.source), _sources(group.mapping_source),
                       _sources(group.mapping_status), _sources(group.coefficient_source)])
    need = pd.DataFrame(totals, columns=[*GRAIN, 'activity', 'baseline_demand', 'missing_coefficients',
                       'activity_source', 'mapping_source', 'mapping_status', 'coefficient_source'])
    selected_supply = assigned[assigned.cluster_id.isin(cluster_ids) & assigned.year.isin(years)
                              & assigned.resource.eq(resource) & assigned.series.eq(supply_series)]
    owned = inventory[inventory.cluster_id.isin(cluster_ids) & inventory.year.isin(years)
                      & inventory.resource.eq(resource) & inventory.series.eq(supply_series)].copy()
    capacity = selected_supply[selected_supply.ipu.ne('Unallocated')].groupby(GRAIN, as_index=False).agg(
        baseline_supply=('effective_capacity', 'sum'), capacity_source=('source', _sources),
        allocation_source=('allocation_source', _sources))
    names = ipus().ipu.tolist() + (['Unmapped'] if d.ipu.eq('Unmapped').any() else [])
    frame = pd.MultiIndex.from_product([years, cluster_ids, names], names=GRAIN).to_frame(index=False)
    frame = frame.merge(ipus(), on='ipu', how='left', validate='many_to_one')
    frame['system'] = frame.system.fillna('Unmapped')
    frame = frame.merge(need, on=GRAIN, how='left', validate='one_to_one')
    frame = frame.merge(capacity, on=GRAIN, how='left', validate='one_to_one')
    frame = frame.merge(clusters()[['cluster_id', 'cluster_name']], on='cluster_id', validate='many_to_one')
    frame['comparable'] = (frame.baseline_demand.notna() & frame.baseline_supply.notna()
                           & frame.ipu.ne('Unmapped') & bool(scope_confirmed))
    frame = apply_scenario(frame, scenario)
    def reason(r):
        gaps = []
        if pd.isna(r.activity): gaps.append('No activity record')
        if pd.notna(r.missing_coefficients) and r.missing_coefficients > 0: gaps.append('Missing resource coefficient')
        if pd.isna(r.baseline_supply): gaps.append('No allocated capacity record')
        if r.ipu == 'Unmapped': gaps.append('No exact IPU crosswalk')
        if not scope_confirmed: gaps.append('Workload / capacity scope not confirmed')
        return '; '.join(gaps) or 'Comparable within supplied records; completeness not independently verified'
    frame['data_gap'] = frame.apply(reason, axis=1)
    synthetic = demand_series == 'Synthetic forecast' or supply_series == 'Synthetic capacity'
    frame['result_status'] = np.where(frame.comparable,
        'Synthetic estimate — unvalidated' if synthetic else 'Calculated estimate — imported assumptions', 'Unresolved')
    frame['activity_status'] = np.where(frame.activity.notna(), demand_series, 'Unavailable')
    frame['capacity_status'] = np.where(frame.baseline_supply.notna(), supply_series, 'Unavailable')
    frame['resource'], frame['unit'] = resource, UNITS[resource]
    frame['setting'], frame['edition'] = setting, edition
    frame['demand_series'], frame['supply_series'] = demand_series, supply_series
    frame['scenario_anchor_year'] = 2025
    for name, value in asdict(scenario).items(): frame[name] = value
    unallocated = selected_supply[selected_supply.ipu.eq('Unallocated')].copy()
    return frame, unallocated, owned


def summarize(frame, by):
    """Compare only paired IPUs; report coverage, never turn missing into zero.

    A partial comparable subtotal is not an all-IPU/system capacity conclusion.
    Surpluses cannot cancel local shortages in the separate shortage measure.
    """
    rows = []
    for key, group in frame.groupby(by, sort=False, dropna=False):
        key = key if isinstance(key, tuple) else (key,)
        valid = group[group.comparable]
        row = dict(zip(by, key))
        row.update(comparable_pairs=len(valid), expected_pairs=len(group), unresolved_pairs=len(group)-len(valid))
        for field in ['baseline_demand','baseline_supply','baseline_gap','scenario_demand','scenario_supply',
                      'scenario_gap','gap_change','shortage','surplus']:
            row[field] = valid[field].sum(min_count=1)
        row['coverage'] = 'Unresolved' if valid.empty else ('Complete for selected rows' if len(valid)==len(group) else 'Partial comparable subtotal')
        rows.append(row)
    return pd.DataFrame(rows)


def apply_scenario(frame, scenario):
    """Adjust a prepared annual ledger without rebuilding evidence or changing its labels."""
    frame = frame.copy()
    dfactor, sfactor = scenario.factors(frame.year)
    frame['scenario_demand'] = frame.baseline_demand * dfactor
    frame['scenario_supply'] = frame.baseline_supply * sfactor
    frame['demand_factor'], frame['supply_factor'] = dfactor, sfactor
    for prefix in ['baseline', 'scenario']:
        frame[prefix + '_gap'] = (frame[prefix + '_demand'] - frame[prefix + '_supply']).where(frame.comparable)
    frame['gap_change'] = frame.scenario_gap - frame.baseline_gap
    frame['shortage'] = frame.scenario_gap.clip(lower=0)
    frame['surplus'] = (-frame.scenario_gap).clip(lower=0)
    frame['gap_pct_required'] = (100 * frame.scenario_gap / frame.scenario_demand).where(frame.scenario_demand.gt(0))
    for name, value in asdict(scenario).items(): frame[name] = value
    return frame
