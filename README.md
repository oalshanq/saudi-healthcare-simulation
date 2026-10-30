# Saudi ACO Supply–Demand Simulation — reference prototype v0.1

## Run
`pip install -r requirements.txt`
`streamlit run app.py`

Streamlit Cloud: repository branch `main`, main file `app.py`.

## Provenance and limitations
- `data/pathways.csv`: extracted directly from Annex K, 23 October 2026, IPU coverage tables, 26 unique IPUs / 49 pathway application records.
- The seventh System of Care (Mental Health) is **proposed**, not nationally designated.
- `aco_sim/model.py`: synthetic population, care rates, specialty-IPU crosswalk, and synthetic capacity supply; **none** are verified regional MOH/GASTAT counts.
- Weighted agent stochastic episode model, plus a finite capacity shortfall proxy. **Not** yet a full SimPy DES with event-calendar queues and transfers.
- National point map is not a choropleth. No fictitious boundaries are supplied.
- Model results are not calibrated, cannot support clinical, budget or investment decisions.
- `tests/test_model.py` checks portfolio size, region-specialty coverage and arithmetic.

## Next development steps
1. Load verified 2023 all-sector regional supply and population data with source citations, missingness and scope.
2. Add real ACO/Network/PCT attribution and provider registry.
3. Implement full event-calendar DES for pathway steps, queues, referrals and handover acceptance.
4. Add IPU resource accounting, shared platform conservation and capacity/access agreements.
5. Add clinical outcomes, DALYs and cost per outcome with calibrated pathway parameters.
6. Bundle licensed administrative boundaries for choropleth maps.
