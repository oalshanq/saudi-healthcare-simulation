# Annual demand–supply gap scenarios

Open **Demand–supply gap** in the sidebar. Select clusters, 2025–2054 years,
resource, System of Care and IPU. Positive gap means required capacity exceeds
available capacity; negative means surplus. Units are never mixed. Shortages are
capacity equivalents, not patient counts or evidence of unmet clinical need.

## Evidence and completeness

- Published evidence remains actual cluster totals in 2024. There are no bundled
  verified annual IPU allocations, coded extracts or calibrated workload conversion
  coefficients; the planning ledger therefore displays unresolved values. No public
  totals are distributed across IPUs, and no missing observation is forecast forward.
- Existing project simulation retains its 16-IPU synthetic profiles and all 26
  reference IPUs. Ten IPUs remain uncalibrated, with blank requirements/gaps.
  The original engine, data and source files are unchanged.
- Imported Observed activity/capacity labels and Approved mapping labels are
  supplied by the user, not independently verified. Calculated resource requirements
  and scenario results remain estimates even when their inputs are observed.
- Every IPU/cluster/year is materialized. Missing activity, any missing coefficient
  within an IPU, absent allocations, missing crosswalks and unconfirmed workload
  scope prevent a numeric gap. Explicit zero records remain zero.
- Totals and charts use **only comparable IPU pairs** and show their coverage.
  Partial totals do not represent all demand or capacity in a cluster/System.
  Known values without a comparable counterpart remain in the detailed ledger.
  Unmapped activity is retained as an unresolved row; unallocated supply is retained
  separately, never silently assigned. Surplus in one IPU does not resolve shortage
  in another: local shortages/surpluses and the signed net total are separate.

## Baseline and scenario arithmetic

The baseline is the selected annual input path (including its existing growth and,
for the synthetic data, the selected integrated-care scenario and seed).

For each available year `y`:

```
demand factor = (1 + demand adjustment / 100) × (1 + extra demand growth / 100)^(y − 2025)
supply factor = (1 + capacity adjustment / 100) × (1 + extra capacity growth / 100)^(y − 2025)
scenario required = baseline required × demand factor
scenario available = baseline allocated effective capacity × supply factor
gap = required − available
```

Growth is additional to the input path; 2025 is the fixed anchor even if the
visible year range changes. Zero adjustments reproduce the baseline. Controls
apply uniformly to the selected scope. They are sensitivity assumptions, not
approved investments or statistical uncertainty intervals. Missing years remain
blank, including when adjustments would multiply them by zero. Annual snapshot
resources (beds, rooms, FTE) must not be summed across years.

## Resource conversions

The synthetic mode exactly re-expresses original v0.1 demand equations against
its annual DEMO activity:

- Beds: admissions × specialty LOS / (365 × 0.82 target occupancy).
- Clinic rooms: outpatient encounters / (240 × 8 × 2.2 consultations/hour).
- Physicians: encounters / visits-per-episode × physician hours / 1,550.
- Nurses: encounters / visits-per-episode × (nursing hours + admission probability
  × LOS × 2.5 bed-day nursing hours) / 1,550.

Workforce covers the whole original synthetic episode, including inpatient nursing;
outpatient volume is used to reconstruct episodes, not to claim outpatient-only
staffing. These coefficients are unvalidated original assumptions. No synthetic
coefficients are provided for theatre hours, imaging slots or laboratory tests.

Imports require a resource coefficient CSV:
`code_system,edition,code,resource,unit,requirement_per_activity,source`.
The coefficient is resource units required per activity count for that exact code
and edition. Supply resource/unit pairs follow the existing register schema.
Only one demand series, capacity series and coding edition are compared at a time.
Duplicate keys, invalid units, negative and nonfinite factors are rejected. A
missing factor invalidates the IPU total; a zero must be explicitly recorded.
No DEMO coefficients are automatically applied to imported clinical codes.

For setting-specific imports, the user must confirm allocations and coefficients
cover the same workload as the selected activity. Shared workforce/rooms must be
allocated to that workload before import. The view does not assert that an import
contains every code or asset in reality: completeness is not independently verified.

## Outputs and preservation

Baseline/scenario gap bars can be grouped by cluster, System of Care or IPU.
Annual gap lines and a signed cluster heatmap retain missing values. CSV exports
include the leaf ledger, annual summaries and unresolved rows; JSON stores scenario
settings. The main ledger retains sources, mapping status, coefficients' provenance,
activity/capacity evidence labels, scenario parameters, synthetic seed and integrated
care selection. Browser imports remain local to the browser and disappear on reload.

Unit tests compare all four synthetic resource calculations to the untouched
original engine and test missing data, partial conversion, zero, no allocation,
fixed-anchor growth, 2054, invalid units, imports and source labels.
