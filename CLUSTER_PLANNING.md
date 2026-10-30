# Annual cluster planning views

## What is shown

The new default workspace has annual cluster demand, annual cluster supply and
data/mapping views for 2025–2054. The original regional prototype remains
available through the View selector; its app and calculation module are unchanged.

Demand is counted separately as inpatient admissions by DRG and outpatient
encounters by primary ICD-10-AM diagnosis. Grouping is cluster → System of Care
→ accountable IPU. Code system, edition, code, mapping status, activity/forecast
series and source are retained. A supplied code must match its edition exactly.
Unmapped volume is retained. Observed activity measures delivered care, not all
population need. Diagnosis codes alone do not specify outpatient procedures or
resource requirements, and there is no licensed/certified DRG grouper here.

Supply has a unique asset/cluster/year ledger with one owner: IPU, Network or
Platform. Each asset describes one resource and unit. Effective capacity is the
minimum of physical/established, staffed and funded capacity, multiplied by its
availability fraction. IPU capacity agreements allocate shares of the same owned
inventory. Allocated shares cannot exceed 100%; duplicate assets and orphan
agreements are rejected. Unallocated capacity is retained. Owned inventory and
IPU allocations must never be added together as separate supply.

Beds, rooms and FTE are snapshots for each year; throughput resources have
explicit units per year. Different units/resources are not summed. Missing
cluster-years remain blank rather than zero, and imported observations are not
extrapolated into unreported years.

## Existing project data and explicit assumptions

The existing 26-IPU / 49-pathway catalogue, synthetic regional populations,
person-agent risks, 18 specialty care profiles, admission probabilities and
clinic-visit coefficients are reused. Regional population is divided equally
among its clusters as an illustrative assumption. The subset of IPUs represented
by those existing profiles receives synthetic estimates; other reference IPUs
remain unavailable. Mental Health as a seventh System remains proposed.

DEMO-DRG and DEMO-ICD-10-AM grouping tokens are visibly synthetic and are not
actual clinical codes. Actual annual coded records and their version-specific
IPU crosswalk must be imported for DRG/ICD-10-AM activity reporting.

Supply freezes the existing model's synthetic 2025 status-quo baseline and grows
it 0.8% annually, independent of the demand scenario. Two illustrative Networks
own beds/clinic rooms. Baseline workforce is partitioned 90% to IPUs and 10% to
one shared clinical Platform, conserving the existing total. These are assumed
organisational assignments, not actual Networks or Platforms. Physical capacity
is assumed to be staffed capacity / 0.85, funded capacity equals staffed capacity
and availability is 1. No actual staffing, funding or operational readiness is
asserted. Theatre hours, imaging slots and laboratory-test supply remain
unavailable because they are absent from the existing model.

The cluster registry uses Health Holding's published 20 names, checked
30 October 2026. IDs are application-specific. It does not establish boundaries,
cluster population attribution or a verified capacity time series.

Sources:
- https://www.health.sa/en/clusters/list
- https://www.chi.gov.sa/Rules/article11/Documents/5.pdf
- Existing `data/pathways.csv` and `aco_sim/model.py`.

## Import

Use the four header-only CSV templates under `data/templates`, also downloadable
in Data & mappings. Upload annual aggregates rather than identifiable records.
The deployed Stlite app processes them within the browser and does not commit or
save them to Netlify/GitHub. Uploads and session results clear on reload.

`Demand` requires one annual aggregate per cluster, setting, code system, edition,
code and series. Outpatient encounters are assigned once, using a primary
diagnosis. Multiple diagnosis lines, claim lines or duplicate aggregate rows
must not be counted as additional encounters. DRG admission aggregates must
already be grouped by an appropriate upstream grouper.

Demand series: Observed activity, Forecast demand, Synthetic forecast.
Supply series: Observed capacity, Planned capacity, Synthetic capacity.
Mappings: Approved, Proposed, Illustrative. Imported approval/source labels
remain user-supplied and are not independently verified by this application.
Each mapping names one accountable IPU from the reference portfolio.

Asset keys are year, cluster_id and asset_id. Asset IDs must include resource
distinction if a physical site supplies several resources. Allocation shares are
fractions from 0 to 1. Unknown cluster IDs, missing/non-finite/negative capacity,
ambiguous mappings and excess allocations stop the affected import; they are
not silently replaced with demonstration data. Reported zero is accepted as
zero. Blank or absent capacity is not recast as zero.
