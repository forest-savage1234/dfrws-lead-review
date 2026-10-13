# Attribution

Standalone lead-review prototype: Forest Savage, 2026, under the root MIT license.

CaseLinker is the existing project created and maintained by Mrinaal Ramachandran and contributors. Forest Savage's merged contributions are source-document/extraction-run provenance (PR #6) and deterministic snapshot manifests/drift verification (PR #7). The separate ledger does not establish upstream integration.

Reused `SourceDocument`, `SourceDocumentVersion`, and `EvidenceReference` models retain their original license at `lead_review/vendor/LICENSE` and pinned draft-fork provenance at `lead_review/vendor/PROVENANCE.json`. Only the existing assertions-module import adaptation is recorded there; the model bytes were not changed in this preparation.

The new `scripts/replay_presenter.py` and `scripts/build_recorded_viewer.py` package a clarified fictional demonstration. They are included under the root MIT license. The original benchmark remains distinct. Existing truth-maintenance, decision-provenance and CASE/UCO foundations receive credit; no general algorithm novelty or validated conformance is claimed.
