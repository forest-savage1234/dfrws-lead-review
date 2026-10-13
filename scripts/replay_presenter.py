"""Replay separately named fictional presenter cases with the unchanged engine."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lead_review.engine import Ledger
from lead_review.model import canonical
from lead_review.runner import run_case


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'presenter/PRESENTER_Trace.json')
    parser.add_argument('--db', type=Path, help='Optional new database for the main journey; existing history is never overwritten.')
    args = parser.parse_args()
    if args.db and args.db.exists():
        parser.error('Choose a new --db path; existing history will not be overwritten.')
    fixture_path = ROOT / 'presenter/PRESENTER_Fixture.json'
    fixture_bytes = fixture_path.read_bytes()
    fixture = json.loads(fixture_bytes)
    stamp = datetime.fromisoformat(fixture['clock'].replace('Z', '+00:00'))
    runs = []
    for index, case in enumerate(fixture['cases']):
        if index == 0 and args.db:
            args.db.parent.mkdir(parents=True, exist_ok=True)
        ledger = Ledger(args.db if index == 0 and args.db else ':memory:', clock=lambda: stamp)
        try:
            runs.append(run_case(ledger, case))
        finally:
            ledger.close()
    result = {'record_kind': 'synthetic_presenter_recorded_execution',
              'fixture_sha256': hashlib.sha256(fixture_bytes).hexdigest(),
              'scope': fixture['scope'], 'conditional_journey': fixture['conditional_journey'],
              'modeled_clock': fixture['clock'], 'runs': runs}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(canonical(result) + '\n', encoding='utf-8', newline='\n')
    summary = [{'case_id': run['case_id'],
                'events': [{'event': event['event'],
                            'new_request_decisions': [r['decision_id'] for r in event['new_requests']],
                            'coverage': event['coverage']['status']} for event in run['events']],
                'original_decisions_preserved': all(n in run['after']['nodes'] for n in run['before']['nodes'] if n['kind'] == 'decision'),
                'integrity': run['after']['integrity']['status']} for run in runs]
    print(json.dumps({'fixture_sha256': result['fixture_sha256'],
                      'trace_sha256': hashlib.sha256(args.out.read_bytes()).hexdigest(),
                      'observed': summary}, indent=2))
    return 0 if all(x['integrity'] == 'pass' and x['original_decisions_preserved'] for x in summary) else 1


if __name__ == '__main__':
    raise SystemExit(main())
