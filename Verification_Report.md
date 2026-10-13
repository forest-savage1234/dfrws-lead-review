# Verification of the selected synthetic source

Prepared 13 October 2026. This repository selection contains code, fictional fixture/trace records, retained results, licenses/provenance, and reproduction instructions. Personal correspondence, conference authoring files, local path inventories and executed databases are excluded.

## Preserved code and benchmark

The engine, models, runner, evaluator, optional UI, web page, original tests and 16-case benchmark inputs/expected labels are unchanged from the retained Bridge implementation. Engine SHA-256: `1d4dc6cb4bad259bf9822f2f7fdb034e8fe2452ba6a46285bb8843d4dd31bda3`.

The original inputs and labels have SHA-256:

- Inputs: `693f91e2e9b5256e2ba4b89d85f800f6d377bfbc2b37a2980dab48fca1d8c757`.
- Expected labels: `8e98d56c3c18096ad4366cd037e59ae25a806d22887529264c5dfe1c3fb2e9c3`.

The evaluator's canonical captured-output digest is `83a99b9d9809fe5d74aa3ea32edde617d41f36a6aae29490913117a6f3a4529c`, excluding the output file's trailing newline. File digests are separately recorded by `FILE_MANIFEST.json`.

The new presenter fixture copies existing setup/actions and clarifies the conditional school-to-stop D1 reason and simulated D2 rationale. Its SHA-256 is `090d9b1b21503ef6dc778280d6a7dd500e3a10080b861111d735e65b74e0c69d`; trace file SHA-256 is `50022e345a7243697c7000cc14f611be706d409a18c2706933974a26caf689e2`. It is separate from the original 16-case benchmark and earlier 24-scenario snapshot study.

## Completed verification evidence

| Check | Observed evidence |
|---|---|
| Original Python methods | A later combined verification passed all 14 methods, including both HTTP methods. `verification/Runtime_Source_Correlation.json` confirms all 18 shared runtime/model/test/web/fixture files match that tested source byte-for-byte. An earlier restricted run passed 12 and blocked two HTTP connections; that block was resolved in the later permitted verification. |
| Existing frontend harness | Actual page-script correction display, review history, missing-link warning and literal text handling passed in a DOM stand-in. |
| Original evaluation | Contract pass: 16 cases, 20 events, 14 required; 12 generated, 2 missed, 0 unnecessary. Passive policy misses 14; broadcast emits 19, including 5 unnecessary. |
| Presenter replay | D1 correction produces a request; simulated D2 is appended while D1 remains; later correction targets D2. Unrelated/editorial controls emit zero; missing relationship emits zero with incomplete coverage. All four internal integrity checks pass. |
| Clean extraction/reproduction | The retained source selection reproduced original evaluation output, presenter trace and recorded-viewer bytes. The original CLI demo export matched its retained object. |
| Recorded viewer | Embedded trace identity, complete root/vendor MIT licenses/provenance and all seven stages passed content checks in a limited DOM stand-in. No remote resources or network calls in shipped recorded HTML. |
| Supplemental release behavior | Reviewed or superseded-decision requests are rejected; identical replay does not duplicate requests. An older open request is accepted after a newer capture if its decision remains active: no source-freshness guard. See `verification/Supplemental_Release_Checks.json`. |

The 14-method evidence applies to byte-matched code; it does not claim that every packaging variant had an identical combined test execution. This publication checkout changes documentation/selection and adds CI, not runtime code, benchmark or presenter trace. The committed workflow provides a fresh run against the published checkout.

## Content and interpretation limits

Fixed synthetic reports use `fixture.invalid` labels. The optional interface fetches only its local loopback endpoints; the recorded viewer loads none. Source content, actor labels and decisions are fictional. The repository contains no personal email/chat/session exports, local-user paths, credentials or private case records identified in the bounded content review. This is not a comprehensive vulnerability or sensitivity certification.

Expected judgments are builder-authored with AI assistance. No independent investigative judgment, source truth, actor authentication, authenticated custody, general algorithm novelty, operational deployment, recovery outcome, comparative superiority or validated CASE/UCO interchange is established.

Graphical browser rendering, actual venue behavior and aloud delivery remain separate checks. A coverage warning describes a recorded gap; it cannot prove comprehensive dependencies or restore an absent link. A person reviewing an older open request must inspect source freshness because the engine does not enforce it.

The source's internal `FILE_MANIFEST.json` is self-contained. It excludes itself to avoid a circular digest; no external archive receipt or private preparation directory is required to use this repository.
