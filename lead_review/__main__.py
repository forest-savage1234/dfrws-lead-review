import argparse
from datetime import datetime
import json
from pathlib import Path
from .engine import Ledger
from .evaluate import evaluate
from .runner import run_case

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description="Offline synthetic lead-reassessment prototype.")
    subs = parser.add_subparsers(dest="command", required=True)
    demo = subs.add_parser("demo", help="Write a complete correction and human-review trace.")
    demo.add_argument("--db", type=Path, default=Path("demo-ledger.sqlite"))
    demo.add_argument("--out", type=Path, default=Path("demo-trace.json"))
    evaluation = subs.add_parser("evaluate", help="Run the 16 synthetic fixtures and two alert comparators.")
    evaluation.add_argument("--out", type=Path, default=Path("results"))
    serve = subs.add_parser("serve", help="Open the local interactive demo; no network dependencies.")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--folder", type=Path, default=Path("demo_sessions"))
    serve.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    if args.command == "evaluate":
        report = evaluate(ROOT / "fixtures/inputs.json", ROOT / "fixtures/expected.json", args.out)
        print((args.out / "EVALUATION.txt").read_text())
        return 0 if report["status"] == "pass" else 1
    if args.command == "demo":
        if args.db.exists():
            parser.error("Choose a new --db path; existing demonstration history will not be overwritten.")
        args.db.parent.mkdir(parents=True, exist_ok=True)
        corpus = json.loads((ROOT / "fixtures/inputs.json").read_text())
        stamp = datetime.fromisoformat(corpus["recorded_at"].replace("Z", "+00:00"))
        case = next(c for c in corpus["cases"] if c["id"] == "review_successor")
        ledger = Ledger(args.db, clock=lambda: stamp)
        try:
            run_case(ledger, case)
            print(json.dumps(ledger.export(args.out), indent=2))
        finally:
            ledger.close()
        return 0
    from .ui import serve_demo
    serve_demo(args.folder, args.port, open_browser=not args.no_browser)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
