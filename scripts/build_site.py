"""Package the original Python application for a browser-hosted Stlite runtime."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist'
SOURCE_FILES = ['app.py', 'aco_sim/__init__.py', 'aco_sim/model.py', 'data/pathways.csv', 'browser_entry.py']

def build():
    OUT.mkdir(exist_ok=True)
    manifest = {}
    for name in SOURCE_FILES:
        source = ROOT / name
        destination = OUT / 'app' / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        manifest[name] = {'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                          'bytes': source.stat().st_size}
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    rules = tomllib.loads((ROOT / 'netlify.toml').read_text())['headers']
    (OUT / '_headers').write_text('\n'.join(
        rule['for'] + '\n' + '\n'.join('  ' + key + ': ' + value
                                      for key, value in rule['values'].items())
        for rule in rules) + '\n')
    (OUT / 'index.html').write_text('''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="Saudi ACO supply–demand research prototype. Synthetic population, pathway and capacity simulation.">
  <title>Saudi ACO Supply–Demand Simulation</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@stlite/browser@1.12.0/build/stlite.css">
  <style>
    body { margin:0; font-family:system-ui,sans-serif; color:#123d39; background:#f8faf9; }
    #loading { max-width:650px; margin:12vh auto; padding:32px; line-height:1.6; }
    h1 { font-size:30px; line-height:1.2; }
    a { color:#126e63; }
    noscript { display:block; padding:32px; }
  </style>
</head>
<body>
  <div id="root"><div id="loading" role="status">
    <h1>Saudi ACO Supply–Demand Simulation</h1>
    <p>Preparing your simulation workspace. The first visit downloads the calculation tools and may take a minute.</p>
    <p>Research prototype · Synthetic, unvalidated inputs</p>
    <p>Your calculations run in this browser. Download any results you want to keep before closing the page.</p>
  </div></div>
  <noscript>Enable JavaScript to run this interactive simulation.</noscript>
  <script type="module">
    const root = document.getElementById('root');
    try {
      const response = await fetch('./manifest.json', {cache:'no-store'});
      if (!response.ok) throw new Error('Application files could not be loaded.');
      const manifest = await response.json();
      const files = Object.fromEntries(Object.keys(manifest).map(name =>
        [name, {url:new URL('./app/' + name, location.href).href}]
      ));
      const {mount} = await import('https://cdn.jsdelivr.net/npm/@stlite/browser@1.12.0/build/stlite.js');
      mount({
        entrypoint:'browser_entry.py',
        files,
        requirements:['numpy', 'pandas', 'plotly==6.3.0'],
        streamlitConfig:{'client.toolbarMode':'viewer', 'theme.primaryColor':'#126e63'}
      }, root);
    } catch (error) {
      root.textContent = '';
      const message = document.createElement('div');
      message.id = 'loading';
      message.textContent = 'The simulation could not start. Check your internet connection and reload. ' + error.message;
      root.appendChild(message);
    }
  </script>
</body>
</html>
''')
    with zipfile.ZipFile(OUT / 'saudi-aco-simulation-source.zip', 'w', zipfile.ZIP_DEFLATED) as bundle:
        for name in SOURCE_FILES + ['requirements.txt', 'README.md', 'tests/test_model.py',
                                    'scripts/build_site.py', 'netlify.toml', 'DEPLOYMENT.md']:
            bundle.write(ROOT / name, name)
    print(f'Built {len(SOURCE_FILES)} unchanged application files in {OUT}')

if __name__ == '__main__':
    build()
