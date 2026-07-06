# Research ideas backlog

Priority-ordered. Status: `OPEN | IN-PROGRESS | BLOCKED | DONE-<verdict>`. The agent
appends and edits statuses; it never deletes entries. Do-not-retry items at the bottom
are closed questions — re-opening one requires the underlying space to have changed
(new data regime, new feature frame), stated explicitly in the ledger notes.

## Open

1. **fp1 — FeatureParams sweep** (Tier 1, `--group feat`, both tours) — `OPEN`
   The context-feature constants have never been swept: `FATIGUE_WINDOW_DAYS=14.0`,
   `LAYOFF_DAYS=120.0`, `PEAK_AGE=26.5` (config.py:328–330; `FEAT_PARAM_OVERRIDES`
   is empty). ~20 trials/tour (~2–2.5 min each), tag `_fp1`, then `--validate`.

2. **pa5 — WTA xgb re-sweep under post-A5 features** (Tier 1, `--group xgb`, WTA
   first) — `OPEN`
   A5 (ratings-only challenger ingestion, adopted 2026-07-06) changed the VALUES of
   the Elo/point feature columns the combiner consumes; the adopted WTA xgb params
   predate that shift, and WTA carries the open anchor gap. ~12 trials, tag `_pa5`.
   ATP only if WTA shows a real signal — ATP combiner re-sweeps have tune-overfit
   three times (tasks/tuning-results-2026-07-02.md).

3. **wta24 — WTA 2024 stats top-up** (data, needs API scrape) — `BLOCKED
   (user-supervised only: violates the no-download invariant; WTA 429s)`
   2024 merged coverage is 78.2%; a supervised backfill session is the path
   (tasks/tuning-results-2026-07-05-data-round.md, Phase B).

## Stale / superseded

- **WTA xgb `min_child_weight` range extension** — the todo item predates the
  landed code: tune.py already sweeps mcw 1.0–400.0 (log) and WTA adopted mcw=70
  from that space (P0, tasks/tuning-results-2026-07-02-core-round.md). Nothing to
  extend; superseded by **pa5**.

## Do not retry (closed with documented gates)

| idea | verdict doc |
|------|-------------|
| Elo geometry sweeps (K curves, blends — triple-confirmed plateau: xsurf/_ablend/_home identical optima) | tuning-results-2026-07-02-autoresearch.md W2 |
| Adaptive per-player surface blend (P3) | tuning-results-2026-07-02-autoresearch.md W2a |
| Elo-level home bonus (feature-level flag is adopted; Elo-level rejected) | tuning-results-2026-07-02-autoresearch.md W2c |
| Monotone constraints | tuning-results-2026-07-02-autoresearch.md W1b |
| Stacked calibration | tuning-results-2026-07-02-autoresearch.md W1c |
| Recency weighting | tuning-results-2026-07-02-autoresearch.md W1d |
| E3 event-speed serve baselines (4th ATP component-pass/arbiter-veto) | tuning-results-2026-07-02-autoresearch.md W3a |
| LR raw-blend, beta calibration, base-margin probes | tuning-results-2026-07-02-autoresearch.md W3b |
| Altitude feature | tuning-results-2026-07-05-data-round.md Phase C |
| A5 full variant (combiner-training contamination; ratings-only IS adopted) | tuning-results-2026-07-05-data-round.md Phase A |
| Pooled-OOS / isotonic calibration, walkover-skip | tasks/todo.md Track B (2026-07-01 round) |
