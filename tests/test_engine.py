import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from datetime import datetime, UTC

from lead_review.engine import Ledger, TABLES
from lead_review.evaluate import evaluate, score
from lead_review.model import ReviewError, canonical, descendants, digest, load_source
from lead_review.runner import execute, run_case

ROOT = Path(__file__).resolve().parents[1]
CORPUS = json.loads((ROOT / "fixtures/inputs.json").read_text())
STAMP = datetime(2026, 10, 6, tzinfo=UTC)

class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "ledger.sqlite"
        self.ledger = Ledger(self.path, clock=lambda: STAMP)
        self.case = CORPUS["cases"][0]
        for action in self.case["setup"]:
            execute(self.ledger, action)

    def tearDown(self):
        self.ledger.close()
        self.tmp.cleanup()

    def corrected(self):
        return execute(self.ledger, self.case["actions"][0])

    def test_correction_retains_bytes_and_original_decision(self):
        before = self.ledger.node("decision_d1")
        old = self.ledger.observation("obs_bus")
        request = self.corrected()["review_requests"][0]
        self.assertEqual(request["decision_id"], "decision_d1")
        self.assertEqual(request["dependency_path"], [old["id"], "decision_d1"])
        self.assertEqual(request["old_values"]["event_time"], "2026-10-01T06:40:00Z")
        self.assertEqual(request["new_values"]["event_time"], "2026-10-01T07:40:00Z")
        self.assertEqual(self.ledger.node("decision_d1"), before)
        self.assertEqual(self.ledger.active_decisions()[0]["disposition"], "set_aside")
        state = self.ledger.state()
        for version in state["source_versions"]:
            self.assertEqual(digest(version["content"]), version["sha256"])
        self.assertEqual(state["integrity"]["status"], "pass")
        self.assertFalse(self.corrected()["decision_changes_automatically_applied"])

    def test_replay_is_idempotent_and_collision_rolls_back(self):
        first = self.corrected()
        count = len(self.ledger.state()["captures"])
        self.assertTrue(self.corrected()["replayed"])
        self.assertEqual(len(self.ledger.state()["captures"]), count)
        action = {**self.case["actions"][0], "content": {"event_time": "different"}}
        before = canonical(self.ledger.state())
        with self.assertRaises(ReviewError):
            execute(self.ledger, action)
        self.assertEqual(canonical(self.ledger.state()), before)
        self.assertEqual(len(first["review_requests"]), 1)

    def test_invalid_input_never_partially_writes(self):
        before = canonical(self.ledger.state())
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'\xff', b'[]', b'x' * 65537):
            with self.assertRaises(ReviewError):
                self.ledger.capture("capture_bad", "source_bus", raw, "2026-10-06T00:00:00Z")
        with self.assertRaises(ReviewError):
            self.ledger.capture("capture_bad", "source_bus", b'{}', "2026-10-06")
        self.assertEqual(canonical(self.ledger.state()), before)

    def test_all_ledger_tables_reject_update_and_delete(self):
        self.corrected()
        self.ledger.review(self.ledger.state()["review_requests"][0]["id"], "review_one", "decision_d2",
                           "defer", "Human review retains uncertainty.", self.current_refs(), "reviewer_demo")
        for table in TABLES:
            column = self.ledger.db.execute(f"PRAGMA table_info({table})").fetchone()["name"]
            for command in (f"UPDATE {table} SET {column}={column}", f"DELETE FROM {table}"):
                with self.subTest(table=table, command=command), self.assertRaises(sqlite3.IntegrityError):
                    self.ledger.db.execute(command)
                self.ledger.db.rollback()

    def current_refs(self):
        return [{"node_id": self.ledger.observation(k)["id"], "fields": ["event_time"]} for k in ("obs_school", "obs_bus")]

    def test_failed_human_review_rolls_back_new_decision(self):
        request_id = self.corrected()["review_requests"][0]["id"]
        before = canonical(self.ledger.state())
        self.ledger.db.execute("CREATE TRIGGER reject_review BEFORE INSERT ON reviews BEGIN SELECT RAISE(ABORT,'fixture failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.ledger.review(request_id, "review_one", "decision_d2", "defer", "A human review.", self.current_refs(), "reviewer_demo")
        self.assertEqual(canonical(self.ledger.state()), before)
        self.assertFalse(self.ledger.db.in_transaction)

    def test_human_review_appends_successor_and_blocks_stale_review(self):
        before = self.ledger.node("decision_d1")
        request = self.corrected()["review_requests"][0]
        self.ledger.review(request["id"], "review_one", "decision_d2", "defer", "Human: investigate further.", self.current_refs(), "reviewer_demo")
        self.assertEqual(self.ledger.node("decision_d1"), before)
        self.assertEqual([d["id"] for d in self.ledger.active_decisions()], ["decision_d2"])
        with self.assertRaises(ReviewError):
            self.ledger.review(request["id"], "review_two", "decision_d3", "pursue", "Duplicate.", self.current_refs(), "reviewer_demo")
        with self.assertRaises(ReviewError):
            self.ledger.decision("decision_d3", "lead_bus", "pursue", "Wrong predecessor.", self.current_refs(), supersedes="decision_d1")

    def test_mapping_is_immutable_and_unknown_field_scope_rejected(self):
        with self.assertRaises(ReviewError):
            self.ledger.document("source_bus", "obs_bus", {"event_time": "other_field"}, "https://fixture.invalid/source_bus")
        with self.assertRaises(ReviewError):
            self.ledger.hypothesis("hyp_bad", [{"node_id": self.ledger.observation("obs_bus")["id"], "fields": ["absent_field"]}], "Test.")
        with self.assertRaises(ReviewError):
            self.ledger.hypothesis("hyp_bad", self.current_refs(), "Test.", label="confirmed_identity")

    def test_reopen_and_export_are_deterministic(self):
        self.corrected()
        before = canonical(self.ledger.state())
        self.ledger.close()
        self.ledger = Ledger(self.path, clock=lambda: STAMP)
        self.assertEqual(canonical(self.ledger.state()), before)
        p1, p2 = Path(self.tmp.name) / "a.json", Path(self.tmp.name) / "b.json"
        self.assertEqual(self.ledger.export(p1)["snapshot_sha256"], self.ledger.export(p2)["snapshot_sha256"])
        self.assertEqual(p1.read_bytes(), p2.read_bytes())

    def test_integrity_detects_modified_source_even_if_trigger_is_bypassed(self):
        # Someone controlling the DB file can remove triggers. That is outside
        # the append-only API guarantee; the source integrity check detects it.
        self.ledger.db.execute("DROP TRIGGER immutable_versions_update")
        self.ledger.db.execute("UPDATE versions SET content=? WHERE document_id=(SELECT id FROM documents WHERE source_key='source_bus')", (b'{}',))
        self.ledger.db.commit()
        self.assertEqual(self.ledger.verify_integrity()["status"], "fail")

class GraphAndEvaluationTests(unittest.TestCase):
    def test_transitive_fields_and_cycles_terminate(self):
        edges = [{"input_id": "obs_one", "owner_id": "hyp_one", "fields": ["event_time"]},
                 {"input_id": "hyp_one", "owner_id": "decision_one", "fields": ["*"]},
                 {"input_id": "decision_one", "owner_id": "hyp_one", "fields": ["*"]}]
        self.assertEqual(descendants({"obs_one": {"place"}}, edges), {})
        got = descendants({"obs_one": {"event_time"}}, edges)
        self.assertEqual(got["decision_one"], ["obs_one", "hyp_one", "decision_one"])

    def test_whole_corpus_and_baselines_expose_missing_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = evaluate(ROOT / "fixtures/inputs.json", ROOT / "fixtures/expected.json", tmp)
            self.assertEqual(report["status"], "pass")
            self.assertEqual(report["fixture_count"], 16)
            p, passive, broadcast = report["results"]
            self.assertEqual((p["required"], p["emitted"], p["missed"], p["unnecessary"]), (14, 12, 2, 0))
            self.assertEqual(p["complete_records_missed"], 0)
            self.assertEqual(p["incomplete_records_missed"], 2)
            self.assertEqual(passive["missed"], 14)
            self.assertEqual(broadcast["unnecessary"], 5)
            outputs = json.loads((Path(tmp) / "captured_runs.json").read_text())
            expected = json.loads((ROOT / "fixtures/expected.json").read_text())
            # A broken "emit nothing" mutation must fail complete-record cases.
            for case in outputs:
                for event in case["events"]:
                    event["new_requests"] = []
            self.assertTrue(score(outputs, expected, "prototype")["contract_violations"])

    def test_missing_links_warn_and_ambiguous_time_is_not_guessed(self):
        for name in ("missing_edges", "undeclared_inputs", "ambiguous_time", "removed_field"):
            case = next(c for c in CORPUS["cases"] if c["id"] == name)
            ledger = Ledger(clock=lambda: STAMP)
            try:
                run = run_case(ledger, case)
                self.assertEqual(run["events"][0]["coverage"]["status"], "incomplete")
                self.assertEqual(run["after"]["coverage"]["status"], "incomplete")
                if name in ("ambiguous_time", "removed_field"):
                    self.assertIsNone(ledger.observation("obs_bus")["values"]["event_time"])
            finally:
                ledger.close()

if __name__ == "__main__":
    unittest.main()
