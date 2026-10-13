"""Execute first, then score captured output against a separate expected file."""
from datetime import datetime
import json
from pathlib import Path
import tempfile
from .engine import Ledger
from .model import canonical, digest
from .runner import run_case

def score(outputs, expected, mode):
    counts = {"required": 0, "emitted": 0, "missed": 0, "unnecessary": 0,
              "complete_records_required": 0, "complete_records_missed": 0,
              "incomplete_records_required": 0, "incomplete_records_missed": 0}
    details, violations = [], []
    gold = {c["case_id"]: c for c in expected["cases"]}
    for run in outputs:
        case = gold[run["case_id"]]
        if len(run["events"]) != len(case["events"]):
            raise ValueError("Event count differs from the expected fixture.")
        for event, want in zip(run["events"], case["events"]):
            if event["event"] != want["event"]:
                raise ValueError("Expected event ordering differs.")
            required = set(want["required_decisions"])
            if mode == "prototype":
                emitted = {r["decision_id"] for r in event["new_requests"]}
            elif mode == "hash_broadcast":
                emitted = set(event["hash_broadcast_decisions"])
            elif mode == "passive_provenance":
                emitted = set()
            else:
                raise ValueError("Unknown comparator.")
            missed, unnecessary = required - emitted, emitted - required
            complete = want["coverage"] == "complete_within_declared_records"
            prefix = "complete_records" if complete else "incomplete_records"
            counts["required"] += len(required)
            counts["emitted"] += len(emitted)
            counts["missed"] += len(missed)
            counts["unnecessary"] += len(unnecessary)
            counts[prefix + "_required"] += len(required)
            counts[prefix + "_missed"] += len(missed)
            if mode == "prototype" and ((complete and missed) or unnecessary or event["coverage"]["status"] != want["coverage"]):
                violations.append({"case_id": run["case_id"], "event": event["event"], "reason": "fixture contract mismatch"})
            details.append({"case_id": run["case_id"], "event": event["event"], "required": sorted(required),
                            "emitted": sorted(emitted), "missed": sorted(missed), "unnecessary": sorted(unnecessary),
                            "coverage": event["coverage"]["status"]})
        if mode == "prototype":
            after = run["after"]
            checks = {"source_versions": len(after["source_versions"]),
                      "review_requests": len(after["review_requests"]), "human_reviews": len(after["human_reviews"]),
                      "original_decisions_preserved": all(
                          d in after["nodes"] for d in run["before"]["nodes"] if d["kind"] == "decision"),
                      "original_versions_preserved": all(v in after["source_versions"] for v in run["before"]["source_versions"]),
                      "original_captures_preserved": all(c in after["captures"] for c in run["before"]["captures"]),
                      "integrity": after["integrity"]["status"]}
            for key, value in case["final"].items():
                if checks[key] != value:
                    violations.append({"case_id": run["case_id"], "check": key, "expected": value, "actual": checks[key]})
    return {"comparator": mode, **counts, "contract_violations": violations, "events": details}

def evaluate(inputs_path, expected_path, output_dir):
    inputs_path, expected_path, output_dir = Path(inputs_path), Path(expected_path), Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    inputs_bytes = inputs_path.read_bytes()
    corpus = json.loads(inputs_bytes)
    stamp = datetime.fromisoformat(corpus["recorded_at"].replace("Z", "+00:00"))
    outputs = []
    with tempfile.TemporaryDirectory(prefix="lead-review-evaluation-") as tmp:
        for case in corpus["cases"]:
            ledger = Ledger(Path(tmp) / (case["id"] + ".sqlite"), clock=lambda: stamp)
            try:
                outputs.append(run_case(ledger, case))
            finally:
                ledger.close()
    captured = canonical(outputs).encode("utf-8")
    (output_dir / "captured_runs.json").write_bytes(captured + b"\n")
    # No expected outcome was read during execution.
    expected_bytes = expected_path.read_bytes()
    expected = json.loads(expected_bytes)
    if {c["id"] for c in corpus["cases"]} != {c["case_id"] for c in expected["cases"]}:
        raise ValueError("Input and expected fixture sets differ.")
    results = [score(outputs, expected, mode) for mode in ("prototype", "passive_provenance", "hash_broadcast")]
    report = {"evaluation": "controlled_synthetic_reassessment_v1", "fixture_count": len(outputs),
              "inputs_sha256": digest(inputs_bytes), "expected_sha256": digest(expected_bytes),
              "captured_runs_sha256": digest(captured), "results": results,
              "status": "pass" if not results[0]["contract_violations"] else "fail",
              "limitations": [
                  "Fixtures and expected outcomes are builder-authored; this is not independent practitioner validation.",
                  "Explicit structured fields and curated dependency references; arbitrary prose extraction is outside scope.",
                  "Incomplete dependency records can miss targeted requests. Coverage warnings do not repair absent links.",
                  "Baselines compare automated alert generation, not investigator performance or human review speed.",
                  "No field deployment, child recovery benefit, authenticated chain of custody, or CASE conformance established."]}
    (output_dir / "evaluation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = ["SINGAPORE LEAD REVIEW: CONTROLLED SYNTHETIC EVALUATION", "",
             f"Fixtures: {len(outputs)}; contract: {report['status']}", "",
             "Comparator                 Required  Emitted  Missed  Unnecessary"]
    for result in results:
        lines.append(f"{result['comparator']:27} {result['required']:8} {result['emitted']:8} {result['missed']:7} {result['unnecessary']:12}")
    p = results[0]
    lines.extend(["", f"Complete recorded dependencies: {p['complete_records_missed']} misses / {p['complete_records_required']} required requests.",
                  f"Incomplete records: {p['incomplete_records_missed']} misses / {p['incomplete_records_required']} required requests.",
                  "", *report["limitations"], "", "Hashes:", "inputs: " + report["inputs_sha256"],
                  "expected: " + report["expected_sha256"], "captured outputs: " + report["captured_runs_sha256"]])
    (output_dir / "EVALUATION.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
