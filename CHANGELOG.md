# Unreleased local candidate — 13 October 2026

Proposed latest-request correction derived from public commit `9987240f934ce00d55f5db8ae04cca4b2b769552`. Human review rejects an older pending request when a later capture generated a request for the same active decision. The older record remains visible as `superseded_request`. The check shares the review's SQLite writer transaction. Editorial/equivalent/identical captures without a new request do not prevent review.

Adds seven regressions, including cross-source supersession and capture/review contention. Local combined verification passed 21 Python methods, including two HTTP workflow methods, and the existing Node harness. Original 16-case metrics and fixture/expected-label bytes remain unchanged. Only the existing reversion case's older request status changes in captured output. Presenter trace and rebuilt viewer remain byte-identical. Integrity remains a bounded source/extraction check, not independent authentication of all decision history. This candidate has not been committed or pushed.

# 0.1.0 — 6 October 2026 UTC

First runnable standalone lead-reassessment implementation. Retains source content versions and decisions, compares explicit reported fields, traverses scoped dependencies, explains review requests, and appends explicit human outcomes. Includes 16 controlled synthetic cases, a separate expected-outcome file, two simplified alert comparators, an offline HTTP demonstration, and engineering checks. Updates Singapore rehearsal deck to v0.6 with measured synthetic results and clear remaining practitioner-evaluation scope.
