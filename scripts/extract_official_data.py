"""Reproducibly extract public observations; run with openpyxl.

Inputs are downloaded unchanged into validation/research (not deployed).
No clinical codes, IPU allocations, staffing or reporting years are inferred.
"""
from pathlib import Path
import csv
import hashlib
import json
import re
import openpyxl
from html.parser import HTMLParser


class Paragraphs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items, self.parts, self.inside = [], [], False

    def handle_starttag(self, tag, attrs):
        if tag == 'p':
            self.inside, self.parts = True, []

    def handle_data(self, data):
        if self.inside:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == 'p' and self.inside:
            self.items.append(' '.join(' '.join(self.parts).split()))
            self.inside = False

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://www.moh.gov.sa/en/Ministry/Statistics/book/Documents/Statistical-Yearbook-2024.xlsx'
HHC = 'https://www.health.sa/en/clusters/list'
ACCESSED = '2026-10-31'
NAMES = {
    'Riyadh First Health Cluster': 'RYD1', 'Riyadh Second Health Cluster': 'RYD2',
    'Riyadh Third Health Cluster': 'RYD3', 'Qassim Health Cluster': 'QAS',
    'Eastern Health Cluster': 'EST', 'Al Ahsa Health Cluster': 'AHS',
    'Hafr Al Batin Health Cluster': 'HBT', 'Makkah Health Cluster': 'MKH',
    'Madinah Health Cluster': 'MDN', 'Jeddah First Health Cluster': 'JED1',
    'Jeddah Second Health Cluster': 'JED2', 'Taif Health Cluster': 'TAF',
    'Hail Health Cluster': 'HAI', 'Tabuk Health Cluster': 'TAB',
    'Al Jouf Health Cluster': 'JOF', 'Northern Borders Health Cluster': 'NBR',
    'Asir Health Cluster': 'ASR', 'Najran Health Cluster': 'NJR',
    'Jazan Health Cluster': 'JZN', 'Al Baha Health Cluster': 'BAH',
    # These three source subtotals each represent ONE whole cluster. Exclude
    # their component rows and the Riyadh/Jeddah multi-cluster subtotals.
    'Total Makkah Health Cluster': 'MKH', 'Total Asir Health Cluster': 'ASR',
    'Total Al Jouf Health Cluster': 'JOF',
}


def write_csv(name, rows):
    with (ROOT / 'data' / name).open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def extract():
    path = ROOT / 'validation/research/moh-yearbook-2024.xlsx'
    book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    # table, cluster-name column, value column, metric, category, unit, caveat
    specs = [
        ('2-7', 'R', 'Q', 'Hospital beds', 'Capacity', 'beds', 'Reported beds; staffed, funded and available beds unspecified.'),
        ('2-7', 'R', 'P', 'Hospitals', 'Capacity', 'facilities', 'Hospital count; not throughput or independently additive to other facility categories.'),
        ('4-22', 'H', 'G', 'Hospital admissions', 'Activity', 'admissions', 'All-cause admissions; no DRG or IPU classification; delivered care is not unmet need.'),
        ('4-5', 'G', 'F', 'Hospital outpatient encounters', 'Activity', 'encounters', 'No ICD-10-AM diagnosis breakdown; excludes PHC encounters in table 4-1.'),
        ('4-1', 'H', 'G', 'PHC encounters and consultations', 'Activity', 'encounters/consultations', 'No ICD-10-AM codes; not unique people; may overlap programme-specific contacts.'),
        ('4-3', 'G', 'F', 'Medical emergency encounters', 'Activity', 'encounters', 'Emergency presentations, not inpatient admissions or unique patients.'),
        ('4-4', 'G', 'F', 'Surgical emergency encounters', 'Activity', 'encounters', 'Not a trauma-only cohort; do not infer an injury diagnosis.'),
        ('4-16', 'G', 'F', 'Diabetes clinic encounters', 'Activity', 'encounters', 'Service-specific count; may overlap hospital outpatient totals; not all cardiometabolic demand.'),
    ]
    for col, metric in [('B', 'Primary healthcare centres'), ('D', 'Cardiology centres'),
                        ('E', 'Oncology centres'), ('F', 'Diabetes and endocrinology centres'),
                        ('G', 'Dialysis centres / units'), ('H', 'Dental centres'),
                        ('I', 'Rehabilitation centres'), ('J', 'Central / regional laboratories')]:
        specs.append(('2-4', 'N', col, metric, 'Capacity', 'facilities/units',
                      'Facility or unit count; no stations, sessions, rooms, staffing or ownership allocation inferred.'))
    for col, metric in [('B', 'General beds'), ('C', 'Medicine beds'), ('D', 'Surgery beds'),
                        ('E', 'Obstetric / gynaecology beds'), ('F', 'Paediatric beds'),
                        ('G', 'Intensive care beds'), ('H', 'Psychiatry / neurology beds'), ('I', 'Isolation beds')]:
        specs.append(('2-9', 'K', col, metric, 'Capacity', 'beds',
                      'Specialty component of hospital beds; not an IPU allocation; do not add to hospital-bed total.'))
    for col, metric in [('B', 'Neonatal ICU beds'), ('C', 'Paediatric ICU beds'), ('D', 'Adult ICU beds')]:
        specs.append(('2-12', 'E', col, metric, 'Capacity', 'beds',
                      'Component of intensive care beds; do not add to ICU or hospital-bed totals.'))
    specs.append(('2-13', 'E', 'D', 'Emergency department beds', 'Capacity', 'beds',
                  'Separate ER inventory; no assertion that additive to the inpatient bed inventory.'))
    for col, metric in [('B', 'General surgery interventions'), ('C', 'Cardiac / chest / vascular interventions'),
                        ('D', 'Urology interventions'), ('E', 'Plastic surgery interventions'),
                        ('F', 'Orthopaedic interventions'), ('G', 'ENT interventions'),
                        ('H', 'Faciodental interventions'), ('I', 'Paediatric surgery interventions'),
                        ('J', 'Obstetric / gynaecology interventions'), ('K', 'Ophthalmology interventions'),
                        ('L', 'Neurosurgery interventions')]:
        specs.append(('4-36', 'O', col, metric, 'Activity', 'interventions',
                      'Procedures by hospital section, not DRG admissions or unique patients; not additive to admissions.'))
    rows, checks = [], []
    for table, name_col, col, metric, category, unit, caveat in specs:
        sheet = book[table]
        assert '2024' in str(sheet['A2'].value), table
        seen = set()
        total = None
        values = []
        unassigned = 0
        for i in range(1, sheet.max_row + 1):
            name = str(sheet[f'{name_col}{i}'].value or '').strip()
            value = sheet[f'{col}{i}'].value
            if name == 'Total':
                total = value
            if name == 'Undefined':
                unassigned += value
            if name not in NAMES:
                continue
            cid = NAMES[name]
            assert cid not in seen, (table, cid)
            seen.add(cid)
            assert value is None or (isinstance(value, (int, float)) and value >= 0), (table, col, i, value)
            if value is not None:
                values.append(value)
            rows.append(dict(observation_id=f'MOH2024-{table}-{col}{i}', cluster_id=cid,
                             year=2024, period='2024', dataset='MOH yearbook 2024', category=category,
                             metric=metric, value='' if value is None else value, unit=unit,
                             status='Source cell blank' if value is None else 'Published observation',
                             scope='MoH facilities in reporting cluster; not all sectors',
                             source_url=URL, source_table=table, source_cell=f'{col}{i}',
                             source_cluster_label=name, retrieved_on=ACCESSED, limitation=caveat))
        assert len(seen) == 20, (table, seen)
        assert total is not None and sum(values) + unassigned == total, (table, metric, sum(values), unassigned, total)
        checks.append(dict(metric=metric, source_table=table, cluster_sum=sum(values), published_total=total,
                           source_unassigned=unassigned, reported_clusters=len(values), missing_clusters=20-len(values)))
    write_csv('published_observations.csv', rows)
    write_csv('published_reconciliation.csv', checks)

    html_path = ROOT / 'validation/research/hhc-clusters.html'
    parser = Paragraphs()
    parser.feed(html_path.read_text())
    descriptions = []
    for text in parser.items:
        if 'total bed capacity' in text and 'beneficiaries' in text and text not in descriptions:
            descriptions.append(text)
    assert len(descriptions) == 20, len(descriptions)
    aliases = {'Al-Ahsa':'Al Ahsa', 'Hafar Al-Batin':'Hafr Al Batin', 'AlTaif':'Taif',
               'Al-Jouf':'Al Jouf', 'Aseer':'Asir', 'Al-Baha':'Al Baha'}
    snapshots = []
    for description in descriptions:
        name = description.split(' provides')[0].removeprefix('The ')
        for old, new in aliases.items():
            name = name.replace(old, new)
        cid = NAMES[name]
        for pattern, metric, unit in [
            (r'bed capacity of (?:up to )?([\d,]+) beds', 'Hospital beds', 'beds'),
            (r'([\d,]+) primary care centers', 'Primary healthcare centres', 'facilities'),
            (r'([\d,]+) hospitals', 'Hospitals', 'facilities'),
            (r'([\d,]+) specialized centers', 'Specialized centres', 'facilities')]:
            match = re.search(pattern, description)
            assert match, description
            snapshots.append(dict(observation_id=f'HHC-{cid}-{len(snapshots)}', cluster_id=cid,
                year='', period='Reporting year unspecified', dataset='HHC undated profile', category='Capacity',
                metric=metric, value=int(match[1].replace(',', '')), unit=unit,
                status='Published snapshot — year unspecified', scope='HHC cluster profile; bed operational definition unspecified',
                source_url=HHC, source_table='Cluster profile', source_cell='', source_cluster_label=name,
                retrieved_on=ACCESSED, limitation=('Beds stated as up to this value. ' if 'up to' in description and unit=='beds' else '') +
                'Retrieval date is not reporting year; not an annual observation or proof of staffed capacity.'))
    write_csv('hhc_capacity_snapshots.csv', snapshots)
    meta = {'retrieved_on': ACCESSED, 'inputs': [{
        'filename': p.name, 'url': url, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
        for p, url in [(path, URL), (html_path, HHC)]],
        'observation_count': len(rows), 'hhc_snapshot_count': len(snapshots),
        'extraction': 'scripts/extract_official_data.py; exact source cells; all metrics reconcile to national controls',
        'cluster_crosswalk': 'Use whole-cluster totals for Makkah/Asir/Al Jouf; exclude their component rows and multi-cluster Riyadh/Jeddah totals.'}
    (ROOT / 'data/published_sources.json').write_text(json.dumps(meta, indent=2) + '\n')
    print(json.dumps(meta, indent=2))


if __name__ == '__main__':
    extract()
