# Resume after the completed historical error round

The round is **complete with no adoption**. Read the [review](2026-09-08-historical-error-review.md),
[comparison](2026-09-08-historical-comparison.csv), [per-year results](2026-09-08-historical-years.csv)
and [manifest](2026-09-08-historical-error-result.json). Do not resume it as unfinished
timing infrastructure or as a pending model fit.

`R = /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation`.
Latest worktree `R/worktrees/historical-errors`, branch `codex/model-historical-errors`,
base `0214834d535654bd92da28180c0d74fb6d33b41b`. Resolve its final acceptance tip before
new isolated work. Experiment source freeze is `814def6`; later commits record results
and documentation only. Production remains in the original checkout and received no code.

## What is fixed and what actually happened

The corrected 42-column WTA maintenance incumbent was reproduced on all 26,794 tuning
rows. Three fixed variants from two mechanisms were fit with the same population,
threshold32, five bags and annual folds. One had a small positive average tune gain
but negative 2015–2019 performance; the other two had negative average gain. None passed
the registered tune-selection rule. **No 2020+ candidate score, ATP fit or final predictor
fit exists.** Do not fill those table cells with previous candidate results or call the
registered absence of validation an incomplete experiment.

Preserve the older uncertainty shadow as its own deferred candidate. It was not included
in this shortlist, retuned or promoted as a fallback. The new appearance and capped states
are experimental research objects, not production-approved predictor artifacts.

## Files and reconstruction

`R/runs/historical-errors` contains:

- `protected-run-files.json`, `setup.json`: earlier evidence and start state.
- `diagnostic-registration.json`, `diagnostics.csv`, `diagnostic-summary.json` and
  `baseline-replay-001`: tune-only diagnosis and exact incumbent reproduction.
- `refinement-registration.json`, `refined-diagnostics.csv`, `prior-match-points.json`:
  recorded follow-up diagnosis before candidate fits.
- `shortlist-registration.json`, `experiment-freeze.json`, `real-parity.json`:
  exact variants, selection rule, code hashes and parity controls.
- `tune-01`, `tune-02`, `tune-03`: immutable registration, OOS predictions, serialized
  experimental states and completion metrics for every trial.
- `selection.json`: explicitly no finalist; `comparison.csv`, `years.csv`,
  `uncertainty.json`, `pytest-focused.txt`, `acceptance.json`: completed results/checks.

The manifest hashes all **32** new files; combine with the 664 protected prior files for
**696** next-phase files. Preserve sixteen accepted checkouts after this branch's final
acceptance commit. The corrected incumbent and older shadow hashes are in `setup.json`
and the result manifest. No large training inputs were copied into this worktree.

Private drivers `R/tools/historical-diagnose.py`, `historical-experiments.py`,
`historical-closeout.py` are create-only and hashed. Do not rerun them into accepted
destinations. Diagnostic code originally used by the diagnostic registration is in
`3d8ce38`; subsequent import/format cleanup at `814def6` preceded the experiment freeze.
No scoring behavior changed in that cleanup. Raw inputs are independently hash-checked
against the maintenance receipts before loading.

From the worktree's `tennis_model` directory, use the existing runtime:

```text
UV_CACHE_DIR=/private/tmp/deuce-research-coordinator-uv PYTHONPATH=src:research
uv run --offline --no-project --python
/Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/worktrees/coordinator/tennis_model/.venv/bin/python
python -m pytest -q tests/test_historical_errors.py tests/test_historical_candidates.py
tests/test_serve_return.py tests/test_temporal_features.py tests/test_features.py
tests/test_probability.py tests/test_research_protocol.py
```

Join those displayed lines into one shell command. Actual completed result: 60 passed
in 1.06s. Twenty real-data checks separately verified identity controls and serialized
prefix/query parity; the maximum saved capped-state point-probability error was zero.
No full-suite pass is claimed for this round.

## Boundaries for another round

The remaining first-appearance underconfidence is an observed tuning pattern, not a
proven causal fault. The straightforward absence transform failed to fix it. The cap
family is also closed here: do not expand its grid based on the exposed trial outcomes.
Consult all rejection documents, including this round, before proposing a materially
different mechanism. Use the corrected incumbent, never an experimental state or an
older production artifact, as the reference. Keep new diagnostic/selection work within
tuning years; 2020+ remains previously examined validation.

Verify preservation before new experiments. Only `points/serve_return.py` differs from
the earlier package, with a default-preserving construction hook; there are two new
external research modules and their tests. Keep that distinction when reusing this
checkout's code and defining another freeze. Large external training/snapshot inventories
were last fully checked at 2026-09-08T01:58:44.035725+00:00. Do not repeat downloads or
timing-source surveys as the default next predictive experiment.
