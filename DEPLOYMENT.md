# Hosting and preservation

The recovered application is `saudi_aco_sim_v0_1.zip`, downloaded from the
Healthcare Simulation Model Plan chat on 30 October 2026. Its Python entrypoint,
`aco_sim` package, pathway CSV, requirements, README and original tests are retained.
Compiled Python caches are excluded from deployment.

## Architecture

GitHub stores the complete source. Netlify builds the static distribution with
`python3 scripts/build_site.py` and publishes `dist/`. Stlite 1.12.0 runs the
original Streamlit application and NumPy/Pandas model inside each visitor's
browser through Pyodide. Plotly 6.3.0 is pinned for the browser runtime.

`browser_entry.py` opens `dashboard.py` and adapts CSV downloads into browser data-URI links,
because a browser-only deployment has no persistent Streamlit `/media` endpoint.
The exported bytes are the exact CSV supplied by the views. The original
`app.py` and `aco_sim/model.py` remain unchanged and are accessible through
the Regional prototype selector. Native hosting for the current workspace uses
`streamlit run dashboard.py`; `streamlit run app.py` still opens the original view.

The current workspace adds yearly cluster demand/supply views, CSV imports and
capacity allocation reconciliation. See `CLUSTER_PLANNING.md` for data scope,
source reuse and assumptions. It remains an interactive Python application.

No persistent Python server, database, API key or paid compute service is needed
for this prototype. The browser runtime and packages load from public CDNs;
OpenStreetMap supplies the base map. Initial loading needs internet access and
may be slower than later visits. Browser memory and computation limit practical
simulation size. Refreshing clears session results; CSV downloads preserve them.

`manifest.json` records SHA-256 hashes of all deployed Python/data files. The
deployment does not add a full DES engine, calibrated data, real ACO attribution,
DALYs or new clinical capabilities. The original regional model derives synthetic
supply from demand. The new cluster views freeze its synthetic 2025 status-quo
supply baseline and project it independently from later demand scenarios;
this is not observed supply.

## Build and test

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt pytest
.venv/bin/python -m pytest -q
python3 scripts/build_site.py
python3 -m http.server 8765 --directory dist
```

For Netlify continuous deployment, use repository `oalshanq/saudi-healthcare-simulation`,
production branch `main`, the root `netlify.toml`, and publish directory `dist`.
`.netlify/` is ignored to keep local site-link state out of Git.

Verify the live dashboard, charts, filters, pathway catalogue, CSV export and
served file hashes after deployment. Deployment-specific results are recorded
in `DEPLOYMENT_REPORT.md`.
# Published evidence update

The default dashboard now loads the public datasets and complete IPU coverage
views documented in `PUBLISHED_DATA.md`. The build packages 15 application/data
files. Historical 2024 observations, undated HHC profiles, 2025–2054 planning
gaps, browser-local imports and existing synthetic simulations remain distinct.
No server-side storage or new hosting service was introduced.
