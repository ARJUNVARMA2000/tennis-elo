# Phase 0 completed — preserved baseline and implementation handoff

Phase 0 preparation is complete. Phase 1 implementation has not started. This phase
preserved the incumbent, reproduced the assessment, verified isolated environments and
fixed five implementation contracts. It did not measure a model improvement.

Read next: [interface decisions](/Users/varma/Projects/DEUCE/tasks/research/2026-09-06-phase0-interfaces.md),
[full phase plan](/Users/varma/Projects/DEUCE/tasks/research/2026-09-06-model-research-plan.md),
and [machine-readable results](/Users/varma/Projects/DEUCE/tasks/research/2026-09-06-phase0-result.json).

## Preserved source and data

Preparation started at **2026-09-06T21:33:48Z**. The verified source base is
`f4a221b08317e796165031202a55a2807a01b056`; its model implementation is unchanged from
`e1702985bd2849905c9a4ea40c05243eca312dc7`. Commit
`d95afc6f7013b7410e5c29bf824ce4646183d782` preserved the assessment, evidence, detailed
plan, task log and private-directory ignore rule before creating worktrees. The Phase 0
completion commit adds only documentation. See local Git for its final SHA; no remote
branch or deployment was changed.

Private durable run root:

```text
/Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation
```

The `snapshot/` directory is read-only. Its `manifest.json` SHA-256 is:

```text
8636748e1012a1fa1f5a31ea0cdd52f414acfaa78ca5123931e24d1c86473cb9
```

The manifest covers 25,826 entries, including **18,791 data files / 740,260,277 data
bytes**. It preserves the complete local `tennis_model/data` tree, raw charting inputs,
normalized cache identities and row keys, both predictors and envelopes, saved A/B
frames, selected player lists, feature partition, strict model contracts, source archive,
installed dependency identities and copied runtime. This is a snapshot of available
local data, not proof that upstream match history is complete.

Source data was hashed before and after cloning and matched the copied inventory.
Subsequent verification checked snapshot content and read-only modes, and found the
original project's data unchanged. The snapshot is local and ignored by Git; copying
the repository alone to another machine will not transfer it. Keep this run directory
and its manifest when transferring the research.

## Prepared workspaces and ownership

All four worktrees started at `d95afc6` and receive the same Phase 0 completion documents
by a fast-forward. Their model code remains the preserved incumbent. The main checkout
is on `codex/model-research-preparation`; `master` remains at `f4a221b`.

Each root below is beneath the private run root's `worktrees/` directory:

| Root | Branch | Next allocated responsibility |
|---|---|---|
| `coordinator` | `codex/model-foundation` | 1D protocol, shared files, schema/config, integration and gates |
| `a` | `codex/model-foundation-a` | 1A probability consistency and focused tests |
| `b` | `codex/model-foundation-b` | 1B temporal charting/serve state and timing audit |
| `c` | `codex/model-foundation-c` | 1C read-only coverage/source census and acquisition proposal |

No agents or background research jobs were launched. These are prepared Git worktrees,
not separate app tasks. The owner table allocates future work; it does not start it.

Each worktree has its own `tennis_model/data/{raw,cache,output}`, `.venv`, copied Ruff
binary, and `.research/phase0/{scratch,logs}`. `workspace-map.json` gives absolute paths.
Data was copied using APFS clones, not writable hard links or symlinks. Every one of
the 18,791 data files has a distinct inode across the original, snapshot and four
worktrees. All four worktree data trees contain no symlinks.

Independent environment probes confirmed that `config.MODEL_DIR`, `sys.prefix` and
NumPy/pandas/scikit-learn/XGBoost imports resolve inside the intended worktree. The
copied environments share the existing uv-managed **base Python interpreter**, which
is outside these worktrees and must not be upgraded during this work. Site-packages
and data/output roots are separate. Runtime identity: Python 3.13.14, pandas 3.0.3,
NumPy 2.5.0, scikit-learn 1.9.0, XGBoost 3.3.0, pytest 8.3.3, Ruff 0.15.21 and uv
0.11.28. No dependency was installed, upgraded or repinned. Optuna is not installed;
component sweeps are not part of this preparation and will need a separately verified
compatible research environment before use.

## Checks and reproduced evidence

| Check | Result | Measured elapsed time |
|---|---|---|
| Full incumbent Python suite, isolated coordinator | **1,198 passed** | pytest 64.68 s; enclosing process 65.37 s |
| Ruff over `tennis_model` | **Passed** | 0.47 s |
| Both saved predictors through `TennisPredictor.load`, all four worktrees | **8 strict loads passed** | Per-probe receipts retained |
| Saved exchange probe, archived WTA comparison and four normalized reconstructions | **Passed** | 200.66 s total |
| Data/runtime snapshot creation | **Passed** | 16.77 s |
| Four workspace data/runtime copies and initial inventory verification | **Passed** | 23.93 s |

Times are measured preparation costs on this machine; they do not estimate future
walk-forward or model-training costs. The Python suite was run once. Tests changed four
ignored coordinator cache files; those four were restored from the preserved snapshot
after recording their before/after hashes. The diagnostic workspace A retains its four
normally rebuilt normalized caches. Final isolation checks found all raw and output
files unchanged in every worktree. Coordinator, B and C data trees match the snapshot
in full; A differs only in those four derived caches.

The eight selected predictor/envelope/archived-frame fingerprints match the assessment.
The exchange probe uses the frozen first 30 players with non-null exported `liveRank`
for each tour, all 435 unordered pairs, and independently builds both directional
feature rows before calling the saved classifier plus calibrator. Context: Hard,
best-of-three, outdoor, tier 1, round order 3, `as_of=2026-09-06`, no named event.
This preserves the original diagnostic recipe; Phase 1 adds public-entry-point tests.

| Tour | Mean absolute exchange gap | 95th percentile | Maximum |
|---|---:|---:|---:|
| ATP | 0.973199943 pp | 2.342077911 pp | 4.682525020 pp |
| WTA | 1.465939694 pp | 3.677770737 pp | 6.632095008 pp |

Saved ATP artifact ID: `6698386b-2d0c-41b3-b7d8-95a72e43c1df`.
Saved WTA artifact ID: `c28905e5-36d9-455f-b5a5-f1618372e04d`.
Do not substitute a main-only WTA walk for the production threshold-32 dual-state path.

Archived WTA threshold-32 comparison, validation 2020+ through 2026-08-17:
**15,247 paired rows**, mean log-loss reduction **+0.000982254589040282**, naive SE
**0.0006594380819309958**, paired SD **0.08142658551564082**. Row-key columns were
asserted equal before calculation. This re-derives old evidence, not a fresh A/B or
prospective confirmation. Full pair CSVs and metric receipts live in `runs/diagnostics/`.

## Normalized data and cache findings

The existing normalized-match fingerprint contains the absolute input path and UTC day.
A copied cache therefore requires normal validation/reconstruction in its destination.
Do not patch the fingerprint or deserialize a cache directly as proof of a valid input.

| Frame | Preserved cache rows | Normal-loader reconstruction | Comparison |
|---|---:|---:|---|
| ATP main | 1 | **153,480** | Preserved one-row cache is not the main population |
| ATP enriched | 284,893 | **284,893** | Frame-value hash exactly matches |
| WTA main | 1 | **128,978** | Preserved one-row cache is not the main population |
| WTA enriched | 146,078 | **146,078** | Frame-value hash exactly matches |

The one-row main caches were preserved as found; their origin was not established.
The normal loader rejected them in the copied root. All four rebuilt frames have zero
duplicates on the recorded composite key. ATP data ends 2026-09-05; WTA ends 2026-09-06
on their normalized date fields. This is not a claim about verified observation times.
Rebuilt fingerprints, frame-value hashes, ordered key files and hashes are recorded in
`runs/diagnostics/normalized-reproduction.json` and the committed result summary.

The same loader reproduced completed main-row serve-stat coverage:

| Tour/year | Completed rows | Rows with serve statistics |
|---|---:|---:|
| ATP 2025 | 2,809 | 91.2% |
| WTA 2025 | 2,402 | 83.4% |
| ATP partial 2026 | 2,187 | 94.5% |
| WTA partial 2026 | 1,991 | 99.4% |
| WTA 2024 | 2,078 | 100.0% |

These measure fields within recorded rows. They cannot identify missing matches.
No external source census or new acquisition occurred; those belong to 1C/4A.

## Decisions ready for implementation

The linked interface record is authoritative for this first implementation pass:

1. **Probability:** one calibrated two-orientation average shared by scalar, matrix,
   evidence and evaluation paths; independent reverse-feature fixtures and gate evidence.
2. **Style:** historical evidence strictly precedes the cutoff; immutable profiles/counts
   belong to the saved predictor; distinguish played date from proven publication time.
3. **Serve priors:** chronological sufficient statistics with the existing 0.62 fallback
   only before evidence exists. A fixed pre-1991 warm-up is unsupported: WTA has no stats,
   ATP only 62 matches / 9,002 service points, all Hard. B must still prove the estimator
   algebra and resolve information-time admission, batching and saved-state parity.
4. **Evaluation:** outcome-independent canonical orientation, existing tune/validation
   split and full arbiter retained; legacy winner-first metrics labeled separately.
5. **Identity:** versioned temporal/feature/cache/receipt contracts; coordinator owns
   common schema, configuration and shared-file integration.

`PROGRAM.md` and evaluator code were not modified. Protocol maintenance must be
completed before a numerical research round. Look-ahead magnitude, correction impact,
prospective performance and gains from additional data remain unmeasured.

## Resume instructions

Start in the prepared coordinator worktree and inspect Git status/history plus the tail
of `tasks/todo.md`. Read this review, the five decisions, relevant research lessons and
the full phase plan before editing. `runs/git-handoff.json` records the final branch
SHAs after documentation synchronization; verify them against current Git.

Use the existing worktree interpreter explicitly; for example, the coordinator checks
were run with the equivalents of:

```bash
cd /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/worktrees/coordinator/tennis_model
UV_CACHE_DIR=/private/tmp/deuce-research-coordinator-uv PYTHONPATH=src uv run --offline --no-project --python .venv/bin/python python -m pytest -q
../.research/phase0/bin/ruff check .
```

Substitute A/B/C's own worktree and uv-cache path for those lanes. Do not reuse a
different worktree's writable cache, output, study DB or environment. Run each normal
loader in its own root before trusting copied normalized caches. Revalidate saved
predictors through `TennisPredictor.load`; do not bypass envelope checks if later
source/schema edits make the old artifact incompatible.

Private preparation drivers are retained under `tools/` with hashes in the result
summary; they are not production code or committed scratch drivers. Logs and receipts
are under `runs/`; `snapshot-verification.json` and `workspace-map.json` live at the run
root. Reproduce only checks invalidated by later edits; do not restart Phase 0 or rerun
an old diagnostic as a new experiment.

The next scope is Phase 1A/1B/1C in their separate lanes, with 1D and shared integration
owned by the coordinator. B's style and serve changes need independent prefix tests
before integration; C's census can proceed without their code. Merge shared callers
sequentially in Phase 2, freeze the evaluator, then establish corrected ATP and dual-state
WTA baselines in Phase 3 before choosing candidate searches. Phase 1 work awaits its
scope being started; no model repair, full retrain, experiment, collector or release has
been initiated here.
