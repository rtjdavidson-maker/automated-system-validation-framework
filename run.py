"""Run configurable validation scenarios on simulated devices."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))

from validation.database import history, save_run  # noqa: E402
from validation.device import get_devices  # noqa: E402
from validation.reports import build_report, save_report  # noqa: E402
from validation.rules import evaluate_all, load_cases  # noqa: E402


def make_parser():
    parser = argparse.ArgumentParser(description='Synthetic device validation framework (offline)')
    parser.add_argument('--profile', choices=['baseline', 'recovered', 'outage'], default='baseline')
    parser.add_argument('--config', type=Path, default=ROOT / 'config' / 'validation_cases.json')
    parser.add_argument('--database', type=Path, default=ROOT / 'output' / 'validation.sqlite3')
    parser.add_argument('--output', type=Path, default=ROOT / 'output')
    parser.add_argument('--history', action='store_true', help='Show prior runs without creating a new run')
    return parser


def run(argv=None):
    parser = make_parser()
    args = parser.parse_args(argv)
    if args.history:
        runs = history(args.database)
        if not runs:
            print('No runs recorded yet.')
        else:
            for row in runs:
                print(f'Run #{row["id"]}: {row["profile"]} | '
                      f'PASS={row["passed"]} FAIL={row["failed"]} ERROR={row["errors"]}')
        return 0
    try:
        cases = load_cases(args.config)
        results = evaluate_all(get_devices(args.profile), cases)
        timestamp = datetime.now(timezone.utc).isoformat()
        run_id, comparison = save_run(args.database, created_utc=timestamp,
                                      profile=args.profile, results=results)
        report = build_report(run_id, timestamp, args.profile, results, comparison)
        json_path, html_path = save_report(args.output, report)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print('MODE: SYNTHETIC DEVICE VALIDATION — NO PHYSICAL HARDWARE')
    print(f'Run #{run_id} | profile={args.profile} | checks={report["total"]}')
    print(f'PASS={report["passed"]} FAIL={report["failed"]} ERROR={report["errors"]}')
    for item in results:
        print(f'[{item.status:<5}] {item.device_id} {item.case_id}: '
              f'{item.observed} — {item.detail}')
    if comparison['previous_run_id'] is not None:
        print(f'Changes since run #{comparison["previous_run_id"]}: '
              f'{len(comparison["regressions"])} regressions; '
              f'{len(comparison["improvements"])} improvements')
    print(f'Saved JSON: {json_path}')
    print(f'Saved HTML: {html_path}')
    print('Windows: start "" "output\\dashboard.html"')
    return 0


if __name__ == '__main__':
    raise SystemExit(run())
