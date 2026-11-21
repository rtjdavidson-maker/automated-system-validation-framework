"""Behavioral, database and CLI tests for the validation framework."""
from dataclasses import replace
from pathlib import Path
import json
import sqlite3
import subprocess
import sys

import pytest

from validation.database import history, save_run
from validation.device import get_devices
from validation.models import TestResult as ValidationResult
from validation.reports import build_report, render_html, save_report
from validation.rules import evaluate, evaluate_all, load_cases, version_tuple

CONFIG = Path(__file__).resolve().parents[1] / 'config' / 'validation_cases.json'
RUN = Path(__file__).resolve().parents[1] / 'run.py'


def cases():
    return load_cases(CONFIG)


def test_load_five_cases():
    assert len(cases()) == 5


def test_unique_cases():
    assert len({c.case_id for c in cases()}) == 5


def test_baseline_has_three_devices():
    assert [d.device_id for d in get_devices()] == ['UNIT-A','UNIT-B','UNIT-C']


def test_baseline_results_match_expected():
    result = evaluate_all(get_devices(), cases())
    assert len(result) == 15
    assert [r.status for r in result].count('PASS') == 11
    assert [r.status for r in result].count('FAIL') == 4


def test_recovered_profile_all_pass():
    assert all(r.status == 'PASS' for r in evaluate_all(get_devices('recovered'), cases()))


def test_outage_profile_reports_unavailable():
    results = evaluate_all(get_devices('outage'), cases())
    assert sum(r.status == 'ERROR' for r in results) == 4
    assert any(r.case_id == 'DEVICE_ONLINE' and r.status == 'FAIL' for r in results)


def test_unknown_profile_raises():
    with pytest.raises(ValueError):
        get_devices('nonexistent')


def test_voltage_boundary_passes():
    d = replace(get_devices('recovered')[0], voltage_v=3.0)
    assert evaluate(d, cases()[0]).status == 'PASS'


def test_voltage_outside_fails():
    d = replace(get_devices('recovered')[0], voltage_v=2.99)
    assert evaluate(d, cases()[0]).status == 'FAIL'


def test_temperature_outside_fails():
    d = replace(get_devices('recovered')[0], temperature_c=71.0)
    assert evaluate(d, cases()[1]).status == 'FAIL'


def test_latency_max_boundary_passes():
    d = replace(get_devices('recovered')[0], latency_ms=100.0)
    assert evaluate(d, cases()[2]).status == 'PASS'


def test_latency_exceeded_fails():
    d = replace(get_devices('recovered')[0], latency_ms=100.1)
    assert evaluate(d, cases()[2]).status == 'FAIL'


def test_semantic_firmware_version_comparison():
    assert version_tuple('1.10.0') > version_tuple('1.2.0')


def test_old_firmware_fails():
    d = replace(get_devices('recovered')[0], firmware_version='1.1.9')
    assert evaluate(d, cases()[3]).status == 'FAIL'


def test_online_check():
    d = replace(get_devices('recovered')[0], responds=False)
    assert evaluate(d, cases()[4]).status == 'FAIL'


def test_offline_measurements_unknown():
    d = replace(get_devices('recovered')[0], responds=False)
    r = evaluate(d, cases()[0])
    assert r.status == 'ERROR' and r.observed is None


def write_config(tmp_path, data):
    p = tmp_path / 'cases.json'
    p.write_text(json.dumps(data), encoding='utf-8')
    return p


@pytest.mark.parametrize('data', [None, {}, {'cases': []}, {'cases': 'not-a-list'}])
def test_invalid_top_level_config(tmp_path, data):
    with pytest.raises(ValueError):
        load_cases(write_config(tmp_path, data))


def test_duplicate_case_rejected(tmp_path):
    d = {'cases': [dict(id='A',description='a',field='responds',rule='equals',expected=True)] * 2}
    with pytest.raises(ValueError, match='unique'):
        load_cases(write_config(tmp_path, d))


def test_unsupported_rule_rejected(tmp_path):
    d = {'cases': [dict(id='A',description='a',field='responds',rule='eval',expected=True)]}
    with pytest.raises(ValueError, match='Unsupported'):
        load_cases(write_config(tmp_path, d))


def test_inverted_threshold_rejected(tmp_path):
    d = {'cases': [dict(id='A',description='a',field='voltage_v',rule='between',expected=[4,3])]}
    with pytest.raises(ValueError):
        load_cases(write_config(tmp_path, d))


def test_invalid_version_rejected():
    with pytest.raises(ValueError):
        version_tuple('1.2.x')


def test_save_and_retrieve_history(tmp_path):
    db = tmp_path / 'data.sqlite3'
    rs = evaluate_all(get_devices(), cases())
    run_id, compare = save_run(db, created_utc='2026-11-21T00:00:00Z', profile='baseline', results=rs)
    assert run_id == 1
    assert compare['previous_run_id'] is None
    assert history(db)[0]['failed'] == 4


def test_recovery_comparison(tmp_path):
    db = tmp_path / 'data.sqlite3'
    save_run(db, created_utc='t1', profile='baseline', results=evaluate_all(get_devices(), cases()))
    _, comparison = save_run(db, created_utc='t2', profile='recovered', results=evaluate_all(get_devices('recovered'), cases()))
    assert len(comparison['improvements']) == 4
    assert comparison['regressions'] == []


def test_regression_comparison(tmp_path):
    db = tmp_path / 'data.sqlite3'
    save_run(db, created_utc='t1', profile='recovered', results=evaluate_all(get_devices('recovered'), cases()))
    _, comparison = save_run(db, created_utc='t2', profile='baseline', results=evaluate_all(get_devices(), cases()))
    assert len(comparison['regressions']) == 4


def test_history_empty_for_missing_db(tmp_path):
    assert history(tmp_path / 'missing.sqlite') == []


def test_database_stores_15_cases(tmp_path):
    db = tmp_path / 'hist.sqlite3'
    save_run(db, created_utc='t1', profile='baseline', results=evaluate_all(get_devices(), cases()))
    with sqlite3.connect(db) as con:
        assert con.execute('select count(*) from results').fetchone()[0] == 15


def test_report_totals():
    rs = evaluate_all(get_devices(), cases())
    report = build_report(1, 'today', 'baseline', rs, dict(previous_run_id=None,regressions=[],improvements=[]))
    assert (report['total'], report['passed'], report['failed'], report['errors']) == (15,11,4,0)


def test_html_escapes_untrusted_content():
    rs = [ValidationResult('<script>', 'VOLTS', 'FAIL', '<bad>', [3,4], '<img src=x>')]
    report = build_report(1, 'today', 'baseline', rs, dict(previous_run_id=None,regressions=[],improvements=[]))
    html = render_html(report)
    assert '<script>' not in html and '&lt;script&gt;' in html
    assert '<img src=x>' not in html


def test_reports_written(tmp_path):
    rs = evaluate_all(get_devices(), cases())
    report = build_report(1, 'today', 'baseline', rs, dict(previous_run_id=None,regressions=[],improvements=[]))
    json_file, html_file = save_report(tmp_path / 'out', report)
    assert json_file.exists() and html_file.exists()
    assert json.loads(json_file.read_text(encoding='utf-8'))['failed'] == 4


def test_cli_baseline_smoke(tmp_path):
    cmd = [sys.executable, str(RUN), '--database', str(tmp_path / 'h.db'),
           '--output', str(tmp_path / 'out')]
    p = subprocess.run(cmd, capture_output=True, text=True, check=True)
    assert 'PASS=11 FAIL=4 ERROR=0' in p.stdout
    assert (tmp_path / 'out' / 'dashboard.html').exists()


def test_cli_history_smoke(tmp_path):
    db = tmp_path / 'h.db'
    subprocess.run([sys.executable, str(RUN), '--database', str(db), '--output', str(tmp_path / 'out')], check=True, capture_output=True)
    p = subprocess.run([sys.executable, str(RUN), '--database', str(db), '--history'], check=True, capture_output=True, text=True)
    assert 'Run #1' in p.stdout
