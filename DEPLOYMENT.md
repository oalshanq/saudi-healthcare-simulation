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

`browser_entry.py` adapts the original CSV download into a browser data-URI link,
because a browser-only deployment has no persistent Streamlit `/media` endpoint.
The exported bytes are the exact CSV supplied by `app.py`; calculations and the
original Python source are unchanged. Native server hosting uses `app.py` directly.

This is the interactive application, not precomputed dashboard images. The same
`app.py` and `aco_sim/model.py` also support ordinary Python server hosting using
`streamlit run app.py`.

No persistent Python server, database, API key or paid compute service is needed
for this prototype. The browser runtime and packages load from public CDNs;
OpenStreetMap supplies the base map. Initial loading needs internet access and
may be slower than later visits. Browser memory and computation limit practical
simulation size. Refreshing clears session results; CSV downloads preserve them.

`manifest.json` records SHA-256 hashes of all deployed Python/data files. The
deployment does not add a full DES engine, calibrated data, real ACO attribution,
DALYs or new clinical capabilities. The model's synthetic supply is derived from
demand, so scenario comparisons do not hold an independent observed supply fixed.

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
