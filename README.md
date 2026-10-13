# DFRWS fictional lead-review prototype

This standalone prototype records which information an investigative decision used. When a mapped observation changes, it follows registered relationships and asks a person to reconsider an affected decision. The request shows the changed values, earlier reason and an available dependency path. Old decisions and source versions remain available.

All supplied records are fictional. The code does not identify a child, establish source truth, automatically choose a disposition, or demonstrate recovery benefit. It is separate from CaseLinker and the earlier 24-scenario snapshot study.

## View the recorded example

Download and extract this source, then open **PRESENTER_Recorded_Viewer.html** in a browser. It embeds the captured output and full license/provenance text. No server, Python, Node or remote resource is needed. The controls display recorded stages; they do not execute the engine or change decisions.

Under a proposed school-to-bus-stop journey, departure must precede sighting. D1 sets that journey aside when a 14:40 sighting precedes a 15:10 departure on the same date and +08:00 offset. A correction to 15:40 removes that particular recorded ordering conflict. The engine requests review through a supplied relationship. A simulated actor appends D2, “defer pending corroboration.” A further correction to 16:00 reaches D2. Identity, travel feasibility and correction reliability remain unresolved.

Unrelated-source and editorial controls generate no targeted request. Removing the needed relationship causes a miss with incomplete coverage. A warning cannot restore a relationship; entirely unrecorded dependencies may remain invisible.

The exact separately named inputs and output are in `presenter/PRESENTER_Fixture.json` and `presenter/PRESENTER_Trace.json`. This presenter clarification changes copied D1/D2 rationale, not the engine or original benchmark. Its fixed modeled clock permits deterministic replay; it is not an execution timestamp. No executed database is distributed; the replay command can create one locally.

## Run the engine

Python **3.11 or newer** is required; no additional Python packages or internet downloads are needed. From this directory, on Windows:

```powershell
py -3 -m lead_review evaluate --out my-results
py -3 scripts/replay_presenter.py --out my-presenter-trace.json --db my-presenter-ledger.sqlite
py -3 scripts/build_recorded_viewer.py --trace my-presenter-trace.json --out my-recorded-viewer.html
```

On Linux/macOS replace `py -3` with `python3`. Choose a new database filename; existing history is never overwritten. Omit the presenter's `--db` option for in-memory execution. The replay script runs the unchanged engine; the viewer builder packages its output.

The original demo is also available:

```powershell
py -3 -m lead_review demo --db my-original-ledger.sqlite --out my-original-demo.json
py -3 -m lead_review serve
```

`serve` opens an optional local loopback interface and needs socket permission. Its controls operate the original demonstration fixture, not the separately clarified presenter rationale. The recorded viewer requires no server. Python is needed only to execute or test the engine.

## Reproduce checks

```powershell
py -3 -m unittest discover -s tests -v
node tests/test_frontend.mjs
```

The unittest suite contains 14 original methods, including two actual loopback HTTP workflow tests. A later combined run passed all 14 on byte-identical runtime/test/web/fixture files; `verification/Runtime_Source_Correlation.json` records all 18 shared files and their digests. The Node command checks the actual page script in a limited DOM stand-in. It is optional for Python engine use and does not establish graphical browser compatibility.

GitHub Actions runs those checks plus a byte comparison of freshly replayed presenter output and its rebuilt viewer. It installs no project packages. `FILE_MANIFEST.json` records the selected source bytes, excluding the manifest itself.

## Original controlled ledger evaluation

The unchanged corpus has **16 builder-authored cases, 20 scored events and 14 required review requests**. Freshly reproduced results:

| Policy | Required | Generated | Missed | Unnecessary |
|---|---:|---:|---:|---:|
| Scoped prototype | 14 | 12 | 2 | 0 |
| Passive provenance policy | 14 | 0 | 14 | 0 |
| Byte-change broadcast policy | 14 | 19 | 0 | 5 |

All ten required requests with complete declared dependencies were generated. Four required requests had incomplete records: two requests were generated despite uncertain/removed time fields; two were missed because relationships were absent. Both misses remain part of the results.

`fixtures/inputs.json`, `fixtures/expected.json` and `results/` preserve original benchmark records. Fresh results are separately in `verification/fresh_evaluation/`. Expected labels are read after engine output is captured. The same builder authored inputs and judgments with AI assistance; file separation does not make the evaluation independent. Simplified policies compare software behavior, not products or investigator performance.

The saved abstract describes an **earlier 24-scenario snapshot implementation**, reporting 19 of 20 required reviews across 19 valid scenarios. That is a different implementation/corpus and is not distributed or reproduced here. Its counts are not pooled with this ledger or the separate presenter demonstration.

## Practical limits

The engine accepts bounded structured JSON, explicit observation-field mappings and supplied dependency references. Supported timezone-bearing event times normalize to instants; missing or unusable values remain unresolved. It does not extract arbitrary documents, infer complete reasoning from prose, discover every omitted relationship, authenticate actors or judge the reliability of a correction.

Capture processing follows ledger insertion order. SQLite triggers block ordinary updates/deletes, but control of the database file can bypass application protections. Digests and retained history establish neither source truth nor authenticated investigative custody.

A reviewed request or request for an already superseded decision is rejected. **Source freshness is not enforced:** an older still-open request can be accepted after a newer source capture while its decision remains active. A person must inspect the relevant source versions. `verification/Supplemental_Release_Checks.json` records this observed limit. No general source-staleness rejection is claimed.

No independent practitioner evaluation, operational deployment, comparative superiority, child-recovery benefit or validated CASE/UCO conformance is established. Graphical browser and venue checks remain separate from software tests.

## Attribution and licenses

[CaseLinker](https://github.com/mrinaalr/CaseLinker) was created and is maintained by Mrinaal Ramachandran and contributors. Forest Savage's merged [PR #6](https://github.com/mrinaalr/CaseLinker/pull/6) adds source-document and extraction-run provenance; [PR #7](https://github.com/mrinaalr/CaseLinker/pull/7) adds deterministic snapshot manifests and drift verification. The later ledger is separate software and is not an upstream merged decision engine.

Reused `SourceDocument`, `SourceDocumentVersion` and `EvidenceReference` models come from Forest's draft fork pinned at `4a17a9e5fdf74057de08a819291bf1606b8e3b45`. Their original MIT license and import adaptation are retained in `lead_review/vendor/LICENSE` and `lead_review/vendor/PROVENANCE.json`. Draft-fork reuse does not imply upstream acceptance.

Standalone code and new replay/viewer scripts: Forest Savage, MIT (`LICENSE`). Reused model attribution remains separate. Established truth-maintenance, dependency-analysis, decision-provenance and CASE/UCO work provide foundations; this package claims no new general reasoning algorithm.
