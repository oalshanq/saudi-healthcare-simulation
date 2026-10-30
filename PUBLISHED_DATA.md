# Published cluster evidence — checked 31 October 2026

The deployed app defaults to public evidence. The original synthetic models,
regional prototype, import validation and allocation ledgers are preserved.

## Actual observations integrated

- **MoH Statistical Yearbook 2024:** 780 source cells, 39 measures, 20 clusters.
  Includes admissions, hospital outpatient activity, PHC contacts, medical and
  surgical emergency encounters, diabetes-clinic visits, surgical interventions,
  hospital and specialty beds, ICU/ER beds and selected facility counts.
- **HHC cluster profiles:** 80 published values, four measures, 20 clusters.
  These profiles do not state their reporting year. Their retrieval date is
  31 October 2026; they are not relabelled as 2026 actuals.

Annual actual observations are shown in a historical **2024** column beside the
unchanged **2025–2054** planning horizon. No data is carried forward, interpolated
or mixed into the synthetic model. Blank means unavailable; published zeros are
preserved. Missing source cells also remain blank.

Sources:
- https://www.moh.gov.sa/en/Ministry/Statistics/book/Documents/Statistical-Yearbook-2024.xlsx
- https://www.moh.gov.sa/en/Ministry/Statistics/book/Pages/default.aspx
- https://www.health.sa/en/clusters/list
- https://www.moh.gov.sa/en/Ministry/OpenData/Pages/Open-Data-Library.aspx

## Reproducibility and reconciliation

`scripts/extract_official_data.py` extracts exact workbook cells using openpyxl
and parses HHC's published descriptions with the standard HTML parser. Download
the source workbook and HHC HTML into `validation/research` using the filenames
in `data/published_sources.json`, then run the script in an environment with
openpyxl. The application runtime does not require openpyxl or network scraping.
Raw sources stay in the local research folder; deployed extracts retain URL,
table, cell, period, scope, status, limitation and retrieval date. Original source
SHA-256 values are retained in `published_sources.json`.

Use Makkah, Asir and Al Jouf whole-cluster subtotals once. Exclude their component
rows and the multi-cluster Riyadh/Jeddah totals. This yields exactly 20 clusters
per measure without double counting. Every extracted metric reconciles to its
published national control, including the **16,783 PHC contacts labelled
Undefined** by the source; these are not assigned to any cluster. The reconciliation
file retains them separately. National controls: 46,905 beds; 1,876,723 admissions;
16,796,225 hospital outpatient encounters.

HHC and MoH bed figures differ for some clusters. Both remain visible with their
source period. This is an unresolved scope/date/definition comparison, not a
capacity-change time series. No automatic preference overwrites a source.

## Classification, capacity and coverage limits

No usable annual cluster-level DRG or ICD-10-AM activity extract was found in the
searched official/public and connected project sources. This is a search outcome,
not proof that such records do not exist. CHI coding publications describe coding
standards, not cluster activity. The CHI data-centre page failed retrieval during
review. Targeted connected GitHub and Drive searches returned policy/reference
material rather than a usable current cluster extract. Local Eastern ACO register
content is explicitly simulated planning. The legacy `real_supply_data.csv` lacks
verifiable provenance and is regional. Neither was promoted to actual evidence.

The workbook does contain ICD-10 disease-group tables: 4-14 (private outpatient
and ER visits), 4-18 (MoH mental-health activity) and 4-30 (private inpatients).
Their inspected headers have no cluster dimension and do not establish an
ICD-10-AM edition. They were not disaggregated into invented cluster/code counts.

Admissions are not DRGs; outpatient clinic counts are not primary-diagnosis
ICD-10-AM counts; surgical interventions are not admissions; delivered activity
does not measure unmet need. No clinical code, codebook or approved crosswalk is
invented. Existing exact code-and-edition imports remain available.

Published beds and facilities do not establish staffing, funding or availability.
Facility counts do not establish FTE, rooms, stations, slots or annual throughput.
Specialty and ICU beds are nested components and must not be added to total beds.
ER inventory is separate without an asserted additive relationship. Service
metrics may overlap and are never summed into a combined activity total.

Network/Platform ownership and IPU capacity agreements were not found. Public
counts therefore stay at cluster/service-category level. Effective capacity and
organisational allocations remain unavailable; the original invented two-Network
split stays only in the explicitly synthetic scenario.

## Completing the ten remaining IPUs

All **26 IPUs / 49 pathways** now have explicit evidence definitions, annual
coverage records, import support, evidence links where relevant, and data and
calibration requirements. The ten added coverage modules are Emergency and Acute
Assessment; Acute Coronary Syndrome; Stroke; Major Trauma; Urology;
Cardiometabolic; Respiratory; Musculoskeletal and Rheumatology; Renal and Dialysis;
and Mental Health. These are data-ready coverage modules, not ten newly validated
clinical simulations. Their rate parameters and exclusive IPU volumes remain
unavailable. The original 16 synthetic-profile IPUs are preserved unchanged.

Related service indicators are explicit **proposed contextual associations**,
not code-to-IPU mappings, complete IPU demand or capacity allocation. For example,
diabetes-clinic contacts are context for Cardiometabolic, urology interventions
for Urology, and dialysis-unit counts for Renal and Dialysis. Psychiatric/neurology
beds cannot be isolated as Mental Health capacity. Broad indicators are left
unassigned where they would misrepresent the IPU. The proposed seventh System
of Care designation remains visible. All annual missing values remain blank.

The gap register covers cluster × year × IPU for the selected 2025–2054 period.
It identifies missing DRG admissions, ICD-10-AM outpatient counts, IPU allocations
and forecast calibration. The annual simulation/import view also exports all
26 IPUs, including missing rows and genuine reported zeroes.
