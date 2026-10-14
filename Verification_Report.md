# Verification of the latest-request correction

Prepared 13 October 2026. This correction derives from public commit `9987240f934ce00d55f5db8ae04cca4b2b769552`. Forest approved publication on 13 October 2026. The original archive remains unchanged. Local_Candidate receipts preserve the pre-publication verification scope. Personal correspondence, conference authoring files, local path inventories and executed databases are excluded from the selected source package.

## Runtime change and preserved records

`lead_review/engine.py` now rejects an older pending request when a later capture produced another request for the same active decision. The check occurs within the review's SQLite writer transaction. `state()` derives the visible `superseded_request` status without rewriting history. Later irrelevant or equivalent captures with no new request do not block review. Capture sequence, rather than user-provided timestamps, selects the latest request. This is not general source-freshness certification.

Seven regression methods are added in `tests/test_request_supersession.py`. Existing models, runner, evaluator, UI/web code, original tests, licenses, and benchmark inputs/expected labels remain unchanged. The file manifest records exact selected source identities.

- Original inputs SHA-256: `693f91e2e9b5256e2ba4b89d85f800f6d377bfbc2b37a2980dab48fca1d8c757`.
- Original expected labels SHA-256: `8e98d56c3c18096ad4366cd037e59ae25a806d22887529264c5dfe1c3fb2e9c3`.
- Presenter fixture SHA-256: `090d9b1b21503ef6dc778280d6a7dd500e3a10080b861111d735e65b74e0c69d`.
- Fresh presenter trace SHA-256: `50022e345a7243697c7000cc14f611be706d409a18c2706933974a26caf689e2`.
- Fresh recorded viewer SHA-256: `0b2afb9dba277acfc11e30e549bd2d1820cf06ac1e8add348a6fdfa5088a2f81`.

## Actual verification

| Check | Observed evidence |
|---|---|
| Local focused checks | 13 methods pass: seven new regressions and six relevant original methods. These cover latest-request rejection/acceptance, irrelevant/equivalent captures, cross-source requests, other decisions, ledger-order semantics, two-connection capture/review contention, retained evidence, replay/collision, rollback, deterministic export and source-byte tamper detection. |
| Local combined candidate checks | All 21 methods pass, including both actual loopback HTTP workflow methods. The existing Node page-script harness passes. The single race regression passes again after switching to automatic temporary-database cleanup. The combined receipt records commands, count, exit codes and observed console tail rather than a saved full per-method log. |
| Queue display | The unchanged actual page script renders an actual candidate state with two requests: older `superseded request`, newer `awaiting human review`, latest bus time 16:00. This is a DOM stand-in check, not graphical browser validation. |
| Original evaluation | Fresh contract pass: 16 cases, 20 events, 14 required; 12 generated, two missed, zero unnecessary. Passive policy misses 14; broadcast emits 19, including five unnecessary. Fixtures and expected labels remain unchanged. |
| Captured evaluation difference | Only the existing `reversion` case's older request status changes from `awaiting_human_review` to `superseded_request`. All other captured state and all evaluation metrics match published records. The canonical output digest is `f89c6ffbfcec5e49ad91a5723956409cb84f9a620e0a01f0eb6e06124f1142c7`; the file digest including its trailing newline is `fba57c62019fc538a16dfc2884810f0a6840e50228bcd717c5338477785e43f0`. |
| Presenter replay/viewer | Fresh trace and rebuilt offline viewer are byte-identical to published artifacts. Embedded trace identity matches. D1 review, explicit D2 defer, later D2 request, unrelated/editorial zero-request controls and missing-link miss with incomplete coverage remain represented. |
| Integrity scope experiment | Altering D1 rationale in a temporary database after disabling the update trigger still produces `pass`. This occurs in the published source and proposed candidate. The check validates foreign keys, source digests/version identifiers, anchors and observation extraction, not independent decision/request/review history authentication. |

Current candidate receipts are under `verification/Local_Candidate/`. Earlier `verification/Runtime_Source_Correlation.json`, `verification/Supplemental_Release_Checks.json`, `results/` and `verification/fresh_evaluation/` are preserved historical evidence for the earlier source. They do not certify changed candidate runtime bytes.

## Interpretation and remaining work

All supplied reports and actor labels are fictional. Expected judgments are builder-authored with AI assistance. No independent practitioner evaluation, source truth, authenticated actor/custody, general algorithm novelty, operational deployment, recovery outcome, comparative superiority or validated CASE/UCO interchange is established.

SQLite append-only triggers prevent normal API updates/deletes; a person controlling the database can bypass them. The export SHA identifies exported bytes, with no externally anchored authenticity guarantee. Entirely unrecorded relationships can remain invisible. Coverage warnings do not restore absent links. A latest-request gate cannot certify current references or source reliability.

The recorded viewer displays executed output and loads no remote resources. It does not run the engine. The original optional interface operates the original fixture, rather than the separately clarified presenter rationale. Forest still needs an aloud rehearsal and actual laptop/browser/venue check before committing to live operation. Graphical browser and multi-process concurrent-export consistency are not certified by these bounded checks.

Root/vendor MIT licenses and provenance are retained. `FILE_MANIFEST.json` excludes itself to avoid a circular digest. Approval to publish this concrete candidate is still required.
