"""Append-only source, observation, dependency, decision, and review ledger.

The engine sees recorded input references, never evaluation gold labels. It
compares explicit structured observation fields, not arbitrary prose meaning.
"""
from __future__ import annotations
from dataclasses import asdict
from contextlib import contextmanager
from functools import wraps
from datetime import datetime, UTC
import json
from pathlib import Path
import sqlite3
from typing import Callable

from .model import (ReviewError, canonical, digest, identifier, text, utc_time,
                    load_source, input_refs, descendants)
from .vendor.documents import SourceDocument, SourceDocumentVersion, canonical_utc
from .vendor.assertions import EvidenceReference

SCHEMA = "lead-review-ledger-1"
TABLES = ("meta", "documents", "versions", "captures", "nodes", "edges", "assessments", "requests", "reviews")
DDL = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS documents(
 id TEXT PRIMARY KEY, source_key TEXT UNIQUE NOT NULL, mapping TEXT NOT NULL,
 observation_key TEXT UNIQUE NOT NULL, metadata TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS versions(
 id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id),
 sha256 TEXT NOT NULL, content BLOB NOT NULL, metadata TEXT NOT NULL,
 UNIQUE(document_id,sha256));
CREATE TABLE IF NOT EXISTS captures(
 seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL,
 document_id TEXT NOT NULL REFERENCES documents(id), version_id TEXT NOT NULL REFERENCES versions(id),
 retrieved_at TEXT NOT NULL, published_at TEXT);
CREATE TABLE IF NOT EXISTS nodes(
 seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('observation','hypothesis','decision')),
 payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS edges(
 input_id TEXT NOT NULL REFERENCES nodes(id), owner_id TEXT NOT NULL REFERENCES nodes(id),
 fields TEXT NOT NULL, PRIMARY KEY(input_id,owner_id), CHECK(input_id != owner_id));
CREATE TABLE IF NOT EXISTS assessments(
 capture_id TEXT PRIMARY KEY REFERENCES captures(id), payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS requests(
 id TEXT PRIMARY KEY, capture_id TEXT NOT NULL REFERENCES captures(id),
 decision_id TEXT NOT NULL REFERENCES nodes(id), payload TEXT NOT NULL,
 UNIQUE(capture_id,decision_id));
CREATE TABLE IF NOT EXISTS reviews(
 seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL,
 request_id TEXT UNIQUE NOT NULL REFERENCES requests(id),
 new_decision_id TEXT UNIQUE NOT NULL REFERENCES nodes(id), payload TEXT NOT NULL);
"""

def atomic(method):
    """Include read-before-write checks in the same SQLite writer transaction."""
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        with self.transaction():
            return method(self, *args, **kwargs)
    return wrapped

class Ledger:
    def __init__(self, path: str | Path = ":memory:", clock: Callable[[], datetime] | None = None):
        self.path = str(path)
        self.clock = clock or (lambda: datetime.now(UTC))
        self.db = sqlite3.connect(self.path, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript(DDL)
        with self.db:
            existing = self.db.execute("SELECT value FROM meta WHERE key='schema'").fetchone()
            if existing and existing[0] != SCHEMA:
                raise ReviewError("Unsupported ledger schema.")
            if not existing:
                self.db.execute("INSERT INTO meta VALUES('schema',?)", (SCHEMA,))
            for table in TABLES:
                for action in ("UPDATE", "DELETE"):
                    self.db.execute(f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{action.lower()} "
                                    f"BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'append-only ledger'); END")

    def close(self):
        self.db.close()

    @contextmanager
    def transaction(self):
        """One writer; nested operations share the enclosing atomic change."""
        if self.db.in_transaction:
            yield
            return
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            self.db.rollback()
            raise
        else:
            self.db.commit()

    def _now(self):
        return canonical_utc(self.clock())

    @atomic
    def document(self, source_key: str, observation_key: str, mapping: dict[str, str], url: str):
        identifier(source_key); identifier(observation_key)
        if not isinstance(mapping, dict) or not mapping or len(mapping) > 20:
            raise ReviewError("A source needs an explicit, bounded field mapping.")
        for field, source_field in mapping.items():
            identifier(field); identifier(source_field)
        now = self.clock()
        doc_id = "doc_" + digest(source_key)[:32]
        doc = SourceDocument(doc_id, source_key, url, "fixture_url_v1", "structured_fixture", now)
        metadata = asdict(doc); metadata["recorded_at"] = canonical_utc(now)
        row = (doc_id, source_key, canonical(mapping), observation_key, canonical(metadata))
        existing = self.db.execute("SELECT * FROM documents WHERE source_key=?", (source_key,)).fetchone()
        if existing:
            if existing["mapping"] != row[2] or existing["observation_key"] != observation_key or json.loads(existing["metadata"])["canonical_url"] != url:
                raise ReviewError("A document mapping is immutable; register a new observation definition.")
            return doc_id
        with self.transaction():
            self.db.execute("INSERT INTO documents VALUES(?,?,?,?,?)", row)
        return doc_id

    def _document(self, source_key):
        row = self.db.execute("SELECT * FROM documents WHERE source_key=?", (source_key,)).fetchone()
        if row is None:
            raise ReviewError("Register the source and its observation mapping first.")
        return row

    def _extract(self, document, version_id: str, source_text: str, value: dict):
        mapping = json.loads(document["mapping"])
        values, issues = {}, []
        for field, source_field in sorted(mapping.items()):
            raw = value.get(source_field)
            if raw is None:
                values[field] = None
                issues.append({"field": field, "reason": "reported field is missing"})
                continue
            try:
                if field == "event_time":
                    values[field] = utc_time(raw)
                elif isinstance(raw, (str, bool, int)) and not isinstance(raw, float):
                    values[field] = raw if not isinstance(raw, str) else text(raw, field, 500)
                else:
                    raise ReviewError("Only bounded scalar reported fields are supported.")
            except ReviewError as exc:
                values[field] = None
                issues.append({"field": field, "reason": str(exc)})
        # Exact anchor covers the complete structured source. Field pointers
        # below identify the declared extraction, without pretending a regex
        # located an unambiguous quoted span in arbitrary text.
        anchor = EvidenceReference.from_text(document_version_id=version_id,
                                            normalized_text=source_text, start_char=0, end_char=len(source_text))
        return {"observation_key": document["observation_key"], "source_key": document["source_key"],
                "source_version_id": version_id, "values": values, "issues": issues,
                "field_pointers": {f: "/" + k for f, k in mapping.items()},
                "evidence": asdict(anchor), "extractor": "structured_json_v1", "inputs": []}

    @atomic
    def capture(self, capture_id: str, source_key: str, content: bytes,
                retrieved_at: str, published_at: str | None = None):
        identifier(capture_id)
        source_text, value = load_source(content)
        if not source_text:
            raise ReviewError("An empty source has no evidence anchor.")
        document = self._document(source_key)
        retrieved_at = utc_time(retrieved_at)
        published_at = utc_time(published_at) if published_at else None
        sha = digest(content)
        version_id = "docv_" + digest(document["id"] + ":" + sha)[:32]
        obs_id = "obs_" + digest(document["observation_key"] + ":" + version_id)[:32]
        existing = self.db.execute("SELECT * FROM captures WHERE id=?", (capture_id,)).fetchone()
        if existing:
            if (existing["document_id"], existing["version_id"], existing["retrieved_at"], existing["published_at"]) != (document["id"], version_id, retrieved_at, published_at):
                raise ReviewError("Capture idempotency key was reused with different evidence or metadata.")
            answer = json.loads(self.db.execute("SELECT payload FROM assessments WHERE capture_id=?", (capture_id,)).fetchone()[0])
            return {**answer, "replayed": True}
        previous = self.db.execute("SELECT * FROM captures WHERE document_id=? ORDER BY seq DESC LIMIT 1", (document["id"],)).fetchone()
        old_obs = self._observation_for_version(document["observation_key"], previous["version_id"]) if previous else None
        extracted = self._extract(document, version_id, source_text, value)
        now = self.clock()
        version = SourceDocumentVersion.capture(version_id=version_id, document_id=document["id"], content=content,
                  retrieved_at=datetime.fromisoformat(retrieved_at.replace("Z", "+00:00")),
                  published_at=datetime.fromisoformat(published_at.replace("Z", "+00:00")) if published_at else None,
                  recorded_at=now, mime_type="application/json", http_status=200, http_etag=None,
                  http_last_modified=None, parser_name="synthetic_json", parser_version="1", normalized_text=source_text)
        metadata = asdict(version)
        for k in ("retrieved_at", "published_at", "recorded_at", "http_last_modified"):
            if metadata[k] is not None:
                metadata[k] = canonical_utc(metadata[k])
        with self.transaction():
            self.db.execute("INSERT OR IGNORE INTO versions VALUES(?,?,?,?,?)", (version_id, document["id"], sha, content, canonical(metadata)))
            self.db.execute("INSERT OR IGNORE INTO nodes(id,kind,payload) VALUES(?,'observation',?)", (obs_id, canonical(extracted)))
            self.db.execute("INSERT INTO captures(id,document_id,version_id,retrieved_at,published_at) VALUES(?,?,?,?,?)",
                            (capture_id, document["id"], version_id, retrieved_at, published_at))
            result = self._assess(capture_id, document, previous, old_obs, obs_id, extracted)
            self.db.execute("INSERT INTO assessments VALUES(?,?)", (capture_id, canonical(result)))
        return result

    def _observation_for_version(self, observation_key, version_id):
        for row in self.db.execute("SELECT * FROM nodes WHERE kind='observation'"):
            payload = json.loads(row["payload"])
            if payload["observation_key"] == observation_key and payload["source_version_id"] == version_id:
                return {"id": row["id"], **payload}
        return None

    def observation(self, observation_key):
        document = self.db.execute("SELECT * FROM documents WHERE observation_key=?", (observation_key,)).fetchone()
        if document is None:
            raise ReviewError("Unknown observation definition.")
        latest = self.db.execute("SELECT version_id FROM captures WHERE document_id=? ORDER BY seq DESC LIMIT 1", (document["id"],)).fetchone()
        if latest is None:
            raise ReviewError("No captured source for this observation.")
        return self._observation_for_version(observation_key, latest[0])

    def node(self, node_id):
        row = self.db.execute("SELECT * FROM nodes WHERE id=?", (node_id,)).fetchone()
        if row is None:
            raise ReviewError("Unknown dependency node: " + str(node_id))
        return {"id": row["id"], "kind": row["kind"], **json.loads(row["payload"])}

    @atomic
    def _record(self, node_id, kind, payload, register=True):
        identifier(node_id)
        refs = input_refs(payload["inputs"])
        if not refs and register:
            raise ReviewError("A normal hypothesis or decision requires explicit inputs.")
        for ref in refs:
            if ref["node_id"] == node_id:
                raise ReviewError("A node cannot depend on itself.")
            source = self.node(ref["node_id"])
            if source["kind"] == "decision":
                raise ReviewError("Decisions are review endpoints, not evidence observations.")
            if source["kind"] != "observation" and ref["fields"] != ["*"]:
                raise ReviewError("Derived inputs propagate possible impact as a whole record.")
            if source["kind"] == "observation" and ref["fields"] != ["*"] and not set(ref["fields"]) <= set(source["values"]):
                raise ReviewError("The dependency scope names a field outside the observation.")
        payload = {**payload, "inputs": refs, "recorded_at": self._now()}
        with self.transaction():
            self.db.execute("INSERT INTO nodes(id,kind,payload) VALUES(?,?,?)", (node_id, kind, canonical(payload)))
            if register:
                for ref in refs:
                    self.db.execute("INSERT INTO edges VALUES(?,?,?)", (ref["node_id"], node_id, canonical(ref["fields"])))
        return self.node(node_id)

    def hypothesis(self, node_id, refs, rationale, label="possibly_same"):
        if label != "possibly_same":
            raise ReviewError("This prototype preserves an identity hypothesis; it does not establish identity.")
        return self._record(node_id, "hypothesis", {"inputs": refs, "rationale": text(rationale, "rationale"), "identity_status": label})

    @atomic
    def decision(self, node_id, lead_id, disposition, rationale, refs, reviewer_id="reviewer_demo", supersedes=None, legacy_reason=None):
        identifier(lead_id); identifier(reviewer_id)
        if disposition not in {"set_aside", "pursue", "defer"}:
            raise ReviewError("Unknown investigative disposition.")
        active = [d for d in self.active_decisions() if d["lead_id"] == lead_id]
        if active:
            if supersedes != active[0]["id"]:
                raise ReviewError("A later decision must explicitly supersede the current decision for this lead.")
        elif supersedes is not None:
            raise ReviewError("There is no current decision to supersede.")
        if legacy_reason is not None:
            text(legacy_reason, "legacy coverage reason")
        payload = {"lead_id": lead_id, "disposition": disposition, "rationale": text(rationale, "rationale"),
                   "inputs": refs, "reviewer_id": reviewer_id, "supersedes": supersedes,
                   "coverage_declaration": "unknown" if legacy_reason else "declared",
                   "legacy_reason": legacy_reason}
        return self._record(node_id, "decision", payload, register=legacy_reason is None)

    def active_decisions(self):
        rows = [self.node(r[0]) for r in self.db.execute("SELECT id FROM nodes WHERE kind='decision' ORDER BY seq")]
        superseded = {r["supersedes"] for r in rows if r["supersedes"] is not None}
        return [r for r in rows if r["id"] not in superseded]

    def edge_records(self):
        return [{"input_id": r["input_id"], "owner_id": r["owner_id"], "fields": json.loads(r["fields"])}
                for r in self.db.execute("SELECT * FROM edges ORDER BY input_id,owner_id")]

    def coverage(self):
        """Reconcile declared record inputs and registered edges.

        The decision record is a second representation of the declared inputs,
        not an evaluation oracle. Completely unrecorded external dependencies
        remain outside this auditable universe.
        """
        edges = {(r["input_id"], r["owner_id"]): r["fields"] for r in self.edge_records()}
        issues = []
        checked = set()
        def visit(node_id, scope, path):
            if node_id in path:
                issues.append({"node_id": node_id, "reason": "dependency cycle in declared records"})
                return
            node = self.node(node_id)
            marker = (node_id, tuple(scope))
            if marker in checked:
                return
            checked.add(marker)
            if node["kind"] == "observation":
                latest = self.observation(node["observation_key"])
                versions_to_check = [node] if node["id"] == latest["id"] else [node, latest]
                for observation in versions_to_check:
                    for issue in observation["issues"]:
                        if "*" in scope or issue["field"] in scope:
                            issues.append({"node_id": observation["id"], "reason": "unresolved observation field", **issue})
                return
            if node.get("coverage_declaration") == "unknown":
                issues.append({"node_id": node_id, "reason": "dependency coverage is undeclared", "detail": node["legacy_reason"]})
            expected = {ref["node_id"]: ref["fields"] for ref in node["inputs"]}
            for ref in node["inputs"]:
                actual = edges.get((ref["node_id"], node_id))
                if actual != ref["fields"]:
                    issues.append({"node_id": node_id, "input_id": ref["node_id"], "reason": "missing or mismatched registered dependency"})
                visit(ref["node_id"], ref["fields"], path + [node_id])
            for (input_id, owner), fields in edges.items():
                if owner == node_id and input_id not in expected:
                    issues.append({"node_id": node_id, "input_id": input_id, "reason": "registered edge absent from declared inputs"})
        for decision in self.active_decisions():
            visit(decision["id"], ["*"], [])
        return {"status": "incomplete" if issues else "complete_within_declared_records", "issues": issues,
                "scope": "Stored decisions and declared input references only; external or entirely unrecorded dependencies cannot be ruled out."}

    def _assess(self, capture_id, document, previous, old_obs, obs_id, extracted):
        old_values = old_obs["values"] if old_obs else {}
        new_values = extracted["values"]
        old_issues = {x["field"]: x["reason"] for x in old_obs["issues"]} if old_obs else {}
        new_issues = {x["field"]: x["reason"] for x in extracted["issues"]}
        changed = sorted(f for f in new_values if old_obs and
                         (old_values.get(f) != new_values[f] or old_issues.get(f) != new_issues.get(f)))
        source_changed = previous is not None and previous["version_id"] != extracted["source_version_id"]
        roots = {}
        if changed:
            for row in self.db.execute("SELECT id,payload FROM nodes WHERE kind='observation'"):
                if json.loads(row["payload"])["observation_key"] == document["observation_key"]:
                    roots[row["id"]] = set(changed)
        paths = descendants(roots, self.edge_records())
        requests = []
        for decision in self.active_decisions():
            if decision["id"] not in paths:
                continue
            path = paths[decision["id"]]
            pinned = self.node(path[0])
            request_id = "req_" + digest(capture_id + ":" + decision["id"])[:32]
            request = {"id": request_id, "capture_id": capture_id, "decision_id": decision["id"],
                       "lead_id": decision["lead_id"], "request_type": "human_reassessment",
                       "reason": "Recorded input fields changed: " + ", ".join(changed),
                       "original_disposition": decision["disposition"], "original_rationale": decision["rationale"],
                       "dependency_path": path, "changed_fields": changed,
                       "old_values": old_values, "new_values": new_values,
                       "decision_basis_values": pinned["values"],
                       "decision_basis_version_id": pinned["source_version_id"],
                       "old_source_version_id": previous["version_id"],
                       "new_source_version_id": extracted["source_version_id"],
                       "previous_capture_id": previous["id"], "recorded_at": self._now(),
                       "conclusion": "Human review requested. No identity, lead validity, or recovery conclusion."}
            self.db.execute("INSERT INTO requests VALUES(?,?,?,?)", (request_id, capture_id, decision["id"], canonical(request)))
            requests.append(request)
        coverage = self.coverage()
        if extracted["issues"]:
            coverage = {**coverage, "status": "incomplete", "issues": [*coverage["issues"],
                        {"node_id": obs_id, "reason": "new observation has unresolved fields", "fields": extracted["issues"]}]}
        return {"capture_id": capture_id, "observation_id": obs_id, "source_changed": source_changed,
                "changed_fields": changed, "review_requests": requests, "coverage": coverage,
                "replayed": False, "decision_changes_automatically_applied": False}

    def review(self, request_id, review_id, new_decision_id, disposition, rationale, refs, reviewer_id):
        """Append a human outcome and a superseding decision atomically."""
        identifier(review_id); identifier(new_decision_id); identifier(reviewer_id)
        with self.transaction():
            row = self.db.execute("SELECT payload FROM requests WHERE id=?", (request_id,)).fetchone()
            if row is None:
                raise ReviewError("Unknown reassessment request.")
            if self.db.execute("SELECT 1 FROM reviews WHERE request_id=?", (request_id,)).fetchone():
                raise ReviewError("This request already has a recorded human review.")
            request = json.loads(row[0])
            active = {d["id"] for d in self.active_decisions()}
            if request["decision_id"] not in active:
                raise ReviewError("The requested decision has already been superseded; review its current successor.")
            current = self.node(request["decision_id"])
            decision = self.decision(new_decision_id, current["lead_id"], disposition, rationale, refs,
                                     reviewer_id=reviewer_id, supersedes=current["id"])
            review = {"id": review_id, "request_id": request_id, "new_decision_id": new_decision_id,
                      "reviewer_id": reviewer_id, "rationale": text(rationale, "rationale"), "recorded_at": self._now(),
                      "authority": "Local demonstration actor label; not an authenticated investigative identity."}
            self.db.execute("INSERT INTO reviews(id,request_id,new_decision_id,payload) VALUES(?,?,?,?)",
                            (review_id, request_id, new_decision_id, canonical(review)))
        return {"review": review, "new_decision": decision}

    def verify_integrity(self):
        findings = []
        fk = list(self.db.execute("PRAGMA foreign_key_check"))
        if fk:
            findings.append("Foreign-key violations in the ledger.")
        versions = {r["id"]: r for r in self.db.execute("SELECT * FROM versions")}
        for version_id, row in versions.items():
            metadata = json.loads(row["metadata"])
            expected_id = "docv_" + digest(row["document_id"] + ":" + digest(row["content"]))[:32]
            if digest(row["content"]) != row["sha256"] or metadata["content_sha256"] != row["sha256"] or metadata["byte_length"] != len(row["content"]) or expected_id != version_id:
                findings.append("Source digest or version identity mismatch: " + version_id)
        for row in self.db.execute("SELECT * FROM nodes WHERE kind='observation'"):
            obs = json.loads(row["payload"])
            version = versions.get(obs["source_version_id"])
            if version is None:
                findings.append("Missing observation source: " + row["id"])
                continue
            try:
                source_text, value = load_source(version["content"])
                anchor = EvidenceReference(**obs["evidence"])
                if not anchor.matches(source_text):
                    findings.append("Evidence anchor mismatch: " + row["id"])
                document = self._document(obs["source_key"])
                replay = self._extract(document, version["id"], source_text, value)
                if canonical(obs) != canonical(replay):
                    findings.append("Observation extraction does not replay: " + row["id"])
            except (ValueError, TypeError) as exc:
                findings.append("Invalid observation: " + row["id"] + ": " + str(exc))
        return {"status": "pass" if not findings else "fail", "findings": findings,
                "boundary": "Internal integrity and deterministic structured extraction; not source truth or authenticated chain of custody."}

    def state(self):
        nodes = [self.node(r[0]) for r in self.db.execute("SELECT id FROM nodes ORDER BY seq")]
        versions = []
        for row in self.db.execute("SELECT * FROM versions ORDER BY id"):
            versions.append({"id": row["id"], "document_id": row["document_id"], "sha256": row["sha256"],
                             "content": row["content"].decode("utf-8"), "metadata": json.loads(row["metadata"])})
        requests = [json.loads(r[0]) for r in self.db.execute("SELECT payload FROM requests ORDER BY rowid")]
        reviews = [json.loads(r[0]) for r in self.db.execute("SELECT payload FROM reviews ORDER BY seq")]
        reviewed = {r["request_id"] for r in reviews}
        active = {d["id"] for d in self.active_decisions()}
        for request in requests:
            request["status"] = "reviewed" if request["id"] in reviewed else "superseded_decision" if request["decision_id"] not in active else "awaiting_human_review"
        return {"schema": SCHEMA, "synthetic_demonstration": True, "source_versions": versions,
                "captures": [dict(r) for r in self.db.execute("SELECT * FROM captures ORDER BY seq")],
                "nodes": nodes, "dependencies": self.edge_records(), "active_decisions": self.active_decisions(),
                "assessments": [json.loads(r[0]) for r in self.db.execute("SELECT payload FROM assessments ORDER BY rowid")],
                "review_requests": requests, "human_reviews": reviews,
                "coverage": self.coverage(), "integrity": self.verify_integrity()}

    def export(self, path: str | Path):
        snapshot = self.state()
        serialized = canonical(snapshot).encode("utf-8")
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(serialized + b"\n")
        return {"path": str(target), "snapshot_sha256": digest(serialized), "scope": "An internally reproducible synthetic ledger, not proof of field effectiveness."}
