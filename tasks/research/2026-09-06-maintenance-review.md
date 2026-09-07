# Population repair — implementation review and new-reference work

M0–M2 are implemented and pass the full-history preflight. M3 baseline rebuilding and
M4 uncertainty screening are next. This is a correctness repair, not an adopted model
improvement. No production deployment or prospective collection is included.

Worktree: `/Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/worktrees/maintenance`,
branch `codex/model-population-repair`, based on Phase 4 `51c9eb1535dc296e1464fb7c1290a779f7f34c15`.
The original checkout remains documentation-only. Coordinator and Phase 4 code, data,
snapshots and prior runs are protected references. Use the coordinator's preserved
Python 3.13 runtime through `uv run --offline --no-project` with `PYTHONPATH=src` from
this worktree's `tennis_model` directory; no dependency installation is needed.

## What the repaired population actually changes

The Phase 4 claims of 491/513 absent results are superseded. The audit treated the
archive's uniform Monday stamp as outside WTA calendars beginning Tuesday, even though
chronology already documented that convention. It also mixed Rome and Parma results
when their dates overlapped. Preserve those audits as failed evidence, not acceptance lists.

The committed WTA ledger independently enumerates 528 results in five 2024 editions:
Madrid, Rome, Miami, Roland Garros and the US Open. All have reviewed first-party records
and corroborating ESPN results, exact edition mappings, dispositions, source hashes,
retrieval provenance and explicit outcome facts. This is the reviewed universe, not
528 missing matches. Historical publication availability remains unknown.

| Selected history | Old rows | Repaired rows | Real additions | Removed copies/invalid rows |
|---|---:|---:|---:|---:|
| ATP enriched | 284,893 | 284,893 | 0 | 0 |
| WTA main | 128,978 | 129,209 | 255 | 24 |
| WTA enriched | 146,078 | 146,309 | 255 | 24 |

The 255 additions are 127 Roland Garros results, 127 US Open results, and the existing
raw Madrid Swiatek–Cirstea result that broad deduplication had discarded. They comprise
248 completed matches, six retirements and one walkover. Only the restored Madrid
archive row has serving statistics; all 254 restored Slam results keep those fields null.
The 24 removals are 23 duplicated 2024 results and the exact 1980 Berkeley self-match.

The duplicate repair adds only `xin yu wang` → `Xinyu Wang`. The repository's identity
falsifier examined all 146,078 frozen enriched WTA rows, found no opposing-player meeting
or other veto, and confirmed the canonical spelling. All 23 collisions were reviewed
same-edition result copies. Xiyu Wang remains distinct. Source-specific name-order
crosswalks in the review ledger do not become general aliases.

Swiatek beat Cirstea 6-1 6-1 in the R32 at both Doha and Madrid in 2024. A broad
season/pair/round/games key previously collapsed them and allowed Madrid timing to move
Doha's surviving row into April. Reviewed donor groups now require compatible ESPN or
native event identities and bounds before sharing outcomes/timing. Both real results
survive. Unreviewed collision groups remain outside this scoped completeness claim.

## Timing, result admission and gates

The new result adapter admits settled main singles independently of optional stats.
It checks numeric record/header edition IDs, winner identity, role, round, outcome and
score. An optional acquisition accumulator runs before the known-stats skip; ordinary
hourly ingestion of all unreviewed result-only records is not activated by this repair.

Estimated timestamp flags cannot certify played dates. Bounded event evidence is kept
even when no played day is known, and conflicting dates/bounds do not win by source
priority. Among uniquely paired existing rows, no ordering date changes. Timing or
statistics-availability metadata changes on 286 WTA main rows and 8,161 enriched rows;
the latter includes lower history. The enriched changes result in 7,888 event-end and
273 played-date availability bases. ATP timing is unchanged. These are retrospective
availability conventions, not reconstructed historical publication times.

Population version advances from 6 to 7 and chronology policy to
`retrospective-verified-date-or-recorded-event-round-v2`. Strict predictor contracts
also bind the reviewed-result ledger hash. Old artifacts cannot silently load under
the new population. Optional statistics and current profile fields are not fabricated.

Both full and quick exports validate an independently enumerated expected-result receipt
before any output writes. The typed pre-upload gate rejects missing, stale or corrupt
receipts, invalid self-pairs, missing expected results and invalid ledger inputs. Cache
loads also validate actual survivors. ATP has an explicitly empty reviewed catalogue;
coverage outside the five reviewed WTA editions remains unknown rather than certified.

The WTA ledger SHA-256 is
`6273d7786a65892c41aa3674322ff08cc7edf69cbed3dd9f2d21faed3ad2c117`;
ATP is `1381b0f3f34602eb55c11e1c02fa0d45fbfed647fa0fb6b944174ffdc5e5ac87`.
No `eval/` file, adoption inequality, feature schema, combiner setting or tree/calibration
implementation changed. The existing 42-column reference and WTA threshold 32 remain.

## Verification and evidence

The full suite passes: 1,319 tests in 131.42 seconds (`logs/full-004.log`), including
missing one result, omitting an entire event, corrupting identities, source acquisition
order, exact quarantine scope, estimated timing, repeated same-score matches, artifact
contracts, and full/quick export gates. Targeted rematch/source checks passed 70 tests.
Two import-order and four line-break-only lint fixes followed testing; no behavior changed.

Private evidence root:
`/Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/runs/maintenance`.
`population-004/result.json` verifies all three histories, all 528 WTA expected results,
zero invalid self-pairs and zero chronology inversions. Exact addition/removal identities
and timing changes are its adjacent CSVs. Use `adjudication-main-v2.json` and the
`reviewed-*-main-v2.csv` files for source/outcome details. The first supplementary
diagnostic mishandled 45 absent round values; the population driver's empty-string
normalization was already correct. Preserve both diagnostics and their correction.

Population attempts 001–003 are retained: a reporting-type error, an overly strict
archive-calendar coverage check, and the Doha/Madrid chronology failure respectively.
None is a scoring run. Identity and source evidence lives under `staging/`, including
the Xin Yu alias falsifier report and 46-row collision review. No new source acquisition
was required for this implementation; the Phase 4 evidence was reused.

## Exact next work

1. Complete the preservation audit, commit this tested repair, then create a new
   exclusive `runs/maintenance/reference-freeze.json`. Keep ATP cutoff 2026-09-05 and
   WTA cutoff 2026-09-06. Never edit package/config/raw files during accepted runs.
2. Run the unchanged `eval.research_run baseline` for ATP and WTA sequentially, five
   bags and all scoreable years. Then run `tools/maintenance-final.py` separately per
   tour for normal final fitting, strict reload, feature parity, 435-pair exchange,
   producer receipt, state-branch coverage and first/last-fold reproduction.
3. Run `tools/maintenance-compare.py` to report the reference change on unique common
   results. Report changed coverage separately; do not subtract losses over different
   populations or describe maintenance as a candidate win.
4. Preserve this new reference and make a distinct continuation checkout. Finish
   full-history dynamic-state cutoff/save-load parity, then the explicitly separate
   43-column research adapter. Prepared, untested drafts are
   `tools/dynamic_combiner_draft.py` and `tools/test_dynamic_research_draft.py`.
5. Register and run the original eight WTA tune-only settings sequentially:
   sigma0 {0.5, 1.0} × q {1e-6, 1e-5, 1e-4, 1e-3}; five bags, unchanged threshold
   selection and fitting policy, 45-minute screen cap. Select at most one before
   candidate validation is scored. No tune gain means reject the family.
6. If selected, use the unchanged full paired arbiter: d_tune > 0 and
   d_val > −SE_naive. Report week clustering and predefined slices; keep unavailable
   event clustering explicit. Future confirmation and production integration remain
   separate. No candidate has yet been scored or adopted.
