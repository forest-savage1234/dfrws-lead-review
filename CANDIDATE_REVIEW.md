# Verified latest-request correction

This working copy derives from public commit `9987240f934ce00d55f5db8ae04cca4b2b769552`. Forest approved publication on 13 October 2026. The baseline archive, benchmark inputs and expected labels, presenter fixtures and trace, and licenses remain unchanged. Initial public commit9987240 had the reproduced request-supersession defect; this correction adds the narrow gate described below.

## Narrow behavior change

If two reassessment requests target the same active decision, only the request associated with the later ledger capture sequence can receive a human outcome. The check runs inside the same SQLite writer transaction as the review. Earlier requests remain retained and appear in the queue as `superseded_request`.

This includes requests produced by different sources for the same decision. Later editorial, identical or semantically equivalent captures that produce no newer request do not strand an existing request. Requests for another decision do not replace it. The policy follows recorded capture sequence, not user-supplied timestamps. It does not certify source freshness, source reliability, completeness of dependencies, or that a person used current input references.

The runtime change is confined to `lead_review/engine.py`: a latest-request gate and a derived queue status. `tests/test_request_supersession.py` adds seven focused regressions, including two SQLite connections contending over capture and review. No stored history is rewritten and no schema migration is required.

## Actual local verification

Thirteen focused test methods pass: seven new methods and six relevant original tests covering retained evidence, capture replay/collision, failed-review rollback, already-reviewed/superseded decisions, deterministic export/reopen, and source-byte tamper detection. A separate combined candidate run passed all 21 methods, including both actual loopback HTTP workflow methods, and the existing Node harness. Its receipt retains exact commands, counts, exit codes and observed console tail rather than a saved full per-method log. After changing the race test to clean up its temporary database automatically, that single test passed again. No graphical browser or venue verification is claimed.

A fresh original 16-case evaluation still returns 12 generated requests from 14 required, two missing-link misses, and zero unnecessary requests. Inputs and expected labels remain byte-identical. The captured output changes only the older pending request's derived status in the existing `reversion` case, from `awaiting_human_review` to `superseded_request`. Evaluation metrics remain identical. Its output digest changes accordingly.

Fresh presenter replay and the rebuilt offline viewer are both byte-identical to the published artifacts. The seven stages remain D1 set aside, corrected-time request for D1, simulated D2 defer, further request for D2, zero unrelated/edit requests, and a missing-relationship miss with incomplete coverage. The recorded controls display captured stages and do not execute software.

The self-contained source package stores candidate receipts/logs and fresh evaluation output in `verification/Local_Candidate/`.

## Integrity scope remains limited

The integrity check validates foreign keys, retained source digests/version identifiers, evidence anchors and deterministic structured observation extraction. It does not independently authenticate decision rationale, request or review payload history. A bounded temporary-database experiment altered D1 rationale after disabling its update trigger; the check still returned `pass`. Ordinary API writes remain append-only, but a person controlling the database can bypass triggers. An export SHA identifies exported bytes and provides no externally anchored authenticity guarantee.

The candidate README/changelog and file manifest describe the proposed change and precise scope. Publication is approved; remote CI must be checked against the resulting commit. Retained Local_Candidate files record pre-publication verification rather than a later remote result. The unchanged recorded viewer can remain the conference fallback. Forest still needs an aloud rehearsal and the actual venue/laptop/browser check before promising a live demonstration.
