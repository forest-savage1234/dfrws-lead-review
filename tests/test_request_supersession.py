"""Focused regressions for the queue's latest-request policy, not source freshness."""
import copy
from datetime import datetime, UTC
import json
from pathlib import Path
import tempfile
import threading
import unittest

from lead_review.engine import Ledger
from lead_review.model import ReviewError, canonical
from lead_review.runner import execute

ROOT = Path(__file__).resolve().parents[1]
CORPUS = json.loads((ROOT / "fixtures/inputs.json").read_text())
CASE = next(c for c in CORPUS["cases"] if c["id"] == "relevant_time")
CLOCK = lambda: datetime(2026, 10, 13, tzinfo=UTC)

class RequestSupersessionTests(unittest.TestCase):
    def setUp(self):
        self.ledger = Ledger(clock=CLOCK)
        for action in CASE["setup"]:
            execute(self.ledger, action)
        self.old = execute(self.ledger, CASE["actions"][0])["review_requests"][0]

    def tearDown(self):
        self.ledger.close()

    def refs(self):
        return [{"node_id": self.ledger.observation(k)["id"], "fields": ["event_time"]}
                for k in ("obs_school", "obs_bus")]

    def capture(self, capture_id, field="event_time", value="2026-10-01T16:00:00+08:00"):
        action = copy.deepcopy(CASE["actions"][0])
        action["capture_id"] = capture_id
        action["content"][field] = value
        return execute(self.ledger, action)

    def review(self, request):
        return self.ledger.review(request["id"], "review_check", "decision_d2", "defer",
                                  "Explicit synthetic human outcome.", self.refs(), "reviewer_demo")

    def test_older_request_rejected_atomically_and_latest_review_succeeds(self):
        new = self.capture("capture_newer")["review_requests"][0]
        state = self.ledger.state()
        self.assertEqual([(r["id"], r["status"]) for r in state["review_requests"]],
                         [(self.old["id"], "superseded_request"), (new["id"], "awaiting_human_review")])
        before = canonical(state)
        with self.assertRaisesRegex(ReviewError, "newer reassessment"):
            self.review(self.old)
        self.assertEqual(canonical(self.ledger.state()), before)
        self.assertFalse(self.ledger.db.in_transaction)
        self.review(new)
        self.assertEqual(self.ledger.state()["human_reviews"][0]["request_id"], new["id"])
        self.assertEqual([d["id"] for d in self.ledger.active_decisions()], ["decision_d2"])
        self.assertEqual(self.ledger.node("decision_d1")["disposition"], "set_aside")

    def test_newer_cross_source_request_supersedes_older_request(self):
        action = {"op": "capture", "capture_id": "capture_school_changed", "source_key": "source_school",
                  "content": {"event_time": "2026-10-01T15:20:00+08:00"}, "retrieved_at": "2026-10-13T00:00:00Z"}
        new = execute(self.ledger, action)["review_requests"][0]
        self.assertEqual(new["decision_id"], self.old["decision_id"])
        with self.assertRaisesRegex(ReviewError, "newer reassessment"):
            self.review(self.old)
        self.review(new)

    def test_editorial_capture_does_not_strand_pending_request(self):
        result = self.capture("capture_editor", "editor_note", "A later editorial change.")
        self.assertEqual(result["review_requests"], [])
        self.assertEqual(self.ledger.state()["review_requests"][0]["status"], "awaiting_human_review")
        self.review(self.old)

    def test_equivalent_timestamp_and_identical_capture_remain_reviewable(self):
        result = self.capture("capture_equivalent", value="2026-10-01T07:40:00Z")
        self.assertEqual(result["review_requests"], [])
        result = self.capture("capture_identical", value="2026-10-01T07:40:00Z")
        self.assertEqual(result["review_requests"], [])
        self.review(self.old)

    def test_request_for_another_decision_does_not_supersede_this_one(self):
        self.ledger.document("source_other", "obs_other", {"event_time": "event_time"}, "https://fixture.invalid/source_other")
        self.ledger.capture("capture_other_first", "source_other", b'{"event_time":"2026-10-01T10:00:00+08:00"}', "2026-10-13T00:00:00Z")
        self.ledger.decision("decision_other", "lead_other", "defer", "Other declared basis.",
                             [{"node_id": self.ledger.observation("obs_other")["id"], "fields": ["event_time"]}])
        self.ledger.capture("capture_other_next", "source_other", b'{"event_time":"2026-10-01T11:00:00+08:00"}', "2026-10-13T00:01:00Z")
        self.review(self.old)

    def test_latest_is_capture_sequence_not_user_timestamp(self):
        action = copy.deepcopy(CASE["actions"][0]);action["capture_id"] = "capture_later_sequence_earlier_clock"
        action["content"]["event_time"] = "2026-10-01T16:00:00+08:00"
        action["retrieved_at"] = "2026-09-01T00:00:00Z"
        new = execute(self.ledger, action)["review_requests"][0]
        with self.assertRaisesRegex(ReviewError, "newer reassessment"):
            self.review(self.old)
        self.review(new)

    def test_concurrent_capture_commits_before_stale_review_check(self):
        with tempfile.TemporaryDirectory(prefix="lead-review-race-") as tmp:
            self.check_concurrent_capture(Path(tmp) / "ledger.sqlite")

    def check_concurrent_capture(self, path):
        writer = Ledger(path, clock=CLOCK)
        for action in CASE["setup"]:
            execute(writer, action)
        old = execute(writer, CASE["actions"][0])["review_requests"][0]
        ready, proceed, attempting = threading.Event(), threading.Event(), threading.Event()
        outcomes = []
        def worker():
            reader = Ledger(path, clock=CLOCK)
            try:
                ready.set()
                if not proceed.wait(3):
                    outcomes.append("worker timeout")
                    return
                refs = [{"node_id": reader.observation(k)["id"], "fields": ["event_time"]}
                        for k in ("obs_school", "obs_bus")]
                attempting.set()
                try:
                    reader.review(old["id"], "review_racing", "decision_racing", "defer",
                                  "Concurrent synthetic human review.", refs, "reviewer_demo")
                    outcomes.append("accepted")
                except ReviewError as exc:
                    outcomes.append(str(exc))
            finally:
                reader.close()
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        try:
            self.assertTrue(ready.wait(3))
            with writer.transaction():
                action = copy.deepcopy(CASE["actions"][0]);action["capture_id"] = "capture_racing_newer"
                action["content"]["event_time"] = "2026-10-01T16:00:00+08:00"
                execute(writer, action)
                proceed.set()
                self.assertTrue(attempting.wait(3))
            thread.join(3)
            self.assertFalse(thread.is_alive())
            self.assertEqual(len(outcomes), 1)
            self.assertIn("newer reassessment", outcomes[0])
            self.assertEqual(writer.state()["human_reviews"], [])
            self.assertEqual([d["id"] for d in writer.active_decisions()], ["decision_d1"])
        finally:
            proceed.set()
            writer.close()

if __name__ == "__main__":
    unittest.main()
