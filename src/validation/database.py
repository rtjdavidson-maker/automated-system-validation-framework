"""SQLite run history for traceable validation results and regression comparisons."""
import json
import sqlite3
from pathlib import Path
from .models import TestResult

SCHEMA = '''
CREATE TABLE IF NOT EXISTS runs (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 created_utc TEXT NOT NULL,
 profile TEXT NOT NULL,
 passed INTEGER NOT NULL,
 failed INTEGER NOT NULL,
 errors INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS results (
 run_id INTEGER NOT NULL,
 device_id TEXT NOT NULL,
 case_id TEXT NOT NULL,
 status TEXT NOT NULL,
 observed_json TEXT NOT NULL,
 expected_json TEXT NOT NULL,
 detail TEXT NOT NULL,
 PRIMARY KEY(run_id, device_id, case_id),
 FOREIGN KEY(run_id) REFERENCES runs(id)
);
'''


def save_run(path: Path, *, created_utc: str, profile: str,
             results: list[TestResult]) -> tuple[int, dict]:
    """Persist one test run, returning its id and comparisons to previous run."""
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = {status: sum(r.status == status for r in results) for status in ('PASS', 'FAIL', 'ERROR')}
    with sqlite3.connect(path) as con:
        con.executescript(SCHEMA)
        previous = con.execute('SELECT id FROM runs ORDER BY id DESC LIMIT 1').fetchone()
        previous_results = {}
        if previous:
            previous_results = {(d, c): s for d, c, s in con.execute(
                'SELECT device_id, case_id, status FROM results WHERE run_id = ?', (previous[0],))}
        cur = con.execute('INSERT INTO runs(created_utc,profile,passed,failed,errors) VALUES(?,?,?,?,?)',
                          (created_utc, profile, summary['PASS'], summary['FAIL'], summary['ERROR']))
        run_id = cur.lastrowid
        con.executemany('INSERT INTO results VALUES(?,?,?,?,?,?,?)', [
            (run_id, r.device_id, r.case_id, r.status, json.dumps(r.observed), json.dumps(r.expected), r.detail)
            for r in results])
    current = {(r.device_id, r.case_id): r.status for r in results}
    regressions = [f'{d}/{c}' for (d, c), status in current.items()
                   if previous_results.get((d, c)) == 'PASS' and status != 'PASS']
    improvements = [f'{d}/{c}' for (d, c), status in current.items()
                    if previous_results.get((d, c)) in ('FAIL', 'ERROR') and status == 'PASS']
    return run_id, {'previous_run_id': previous[0] if previous else None,
                    'regressions': regressions, 'improvements': improvements}


def history(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with sqlite3.connect(path) as con:
        con.executescript(SCHEMA)
        rows = con.execute('SELECT id,created_utc,profile,passed,failed,errors FROM runs ORDER BY id').fetchall()
    return [dict(zip(('id','created_utc','profile','passed','failed','errors'), row)) for row in rows]
