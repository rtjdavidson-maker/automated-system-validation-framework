"""Offline HTML and JSON validation reports with safe HTML escaping."""
from collections import Counter
from dataclasses import asdict
from html import escape
import json
from pathlib import Path
from .models import TestResult


def build_report(run_id: int, created_utc: str, profile: str,
                 results: list[TestResult], comparison: dict) -> dict:
    counts = Counter(r.status for r in results)
    return {
        'run_id': run_id, 'created_utc': created_utc, 'profile': profile,
        'total': len(results), 'passed': counts['PASS'], 'failed': counts['FAIL'],
        'errors': counts['ERROR'], 'comparison': comparison,
        'results': [asdict(r) for r in results],
        'scope': 'Simulated devices only; no physical hardware was tested',
    }


def render_html(report: dict) -> str:
    rows = []
    for r in report['results']:
        cls = {'PASS': 'pass', 'FAIL': 'fail', 'ERROR': 'error'}[r['status']]
        rows.append('<tr>' + ''.join((
            f'<td>{escape(str(r["device_id"]))}</td>',
            f'<td>{escape(str(r["case_id"]))}</td>',
            f'<td class="{cls}">{r["status"]}</td>',
            f'<td>{escape(json.dumps(r["observed"]))}</td>',
            f'<td>{escape(json.dumps(r["expected"]))}</td>',
            f'<td>{escape(str(r["detail"]))}</td>',
        )) + '</tr>')
    changes = report['comparison']
    if changes['previous_run_id'] is None:
        change_line = 'First recorded run (no baseline available for comparison).'
    else:
        change_line = (f'Compared with run #{changes["previous_run_id"]}: '
                       f'{len(changes["regressions"])} regressions; '
                       f'{len(changes["improvements"])} improvements.')
    html = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Automated System Validation</title>
<style>
:root{font-family:system-ui,-apple-system,Segoe UI,sans-serif;background:#0c1625;color:#e8f0fa}
*{box-sizing:border-box}main{max-width:1160px;margin:36px auto;padding:0 18px}
h1{font-size:clamp(1.5rem,4vw,2.3rem)}p{color:#b2c5d8}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:13px;margin:20px 0}
.card,.panel{background:#1b2c43;border:1px solid #3a526d;border-radius:13px;padding:20px}
.card b{display:block;font-size:2rem;margin-top:6px}.panel{margin:16px 0;overflow-x:auto}
table{width:100%;border-collapse:collapse;min-width:850px}th,td{padding:10px;border-bottom:1px solid #38506b;text-align:left;font-size:.89rem}th{color:#c2d5e9}
.pass{color:#56e0ae;font-weight:700}.fail{color:#ff9f91;font-weight:700}.error{color:#f2cf76;font-weight:700}
</style></head><body><main><h1>Automated System Validation</h1>"""
    html += '<p>Simulated device suite · ' + escape(report['created_utc']) + ' · profile: ' + escape(report['profile']) + '</p>'
    html += '<section class="cards">'
    for label, key in [('Run ID', 'run_id'), ('Checks', 'total'), ('Passed', 'passed'), ('Failed', 'failed'), ('Errors', 'errors')]:
        html += f'<div class="card">{label}<b>{report[key]}</b></div>'
    html += '</section><section class="panel"><h2>Regression comparison</h2><p>' + escape(change_line) + '</p>'
    for key in ('regressions', 'improvements'):
        if changes[key]:
            html += '<p><strong>' + key.title() + ':</strong> ' + escape(', '.join(changes[key])) + '</p>'
    html += '</section><section class="panel"><h2>Test results</h2><table><thead><tr>'
    html += '<th>Device</th><th>Test</th><th>Status</th><th>Observed</th><th>Expected</th><th>Details</th>'
    html += '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table></section>'
    html += '<p>Educational validation using synthetic device readings. No physical devices tested.</p></main></body></html>'
    return html


def save_report(folder: Path, report: dict) -> tuple[Path, Path]:
    folder.mkdir(parents=True, exist_ok=True)
    json_path = folder / 'validation.json'
    html_path = folder / 'dashboard.html'
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    html_path.write_text(render_html(report), encoding='utf-8')
    return json_path, html_path
