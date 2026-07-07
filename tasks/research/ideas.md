# Research ideas backlog

Priority-ordered. Status: `OPEN | IN-PROGRESS | BLOCKED | DONE-<verdict>`. The agent
appends and edits statuses; it never deletes entries. Do-not-retry items at the bottom
are closed questions — re-opening one requires the underlying space to have changed
(new data regime, new feature frame), stated explicitly in the ledger notes.

## Open

1. **fp1 — FeatureParams sweep** (Tier 1, `--group feat`, both tours) —
   `DONE: WTA ADOPT (R1-003-wta, fec0fb1) / ATP DECLINED (R1-003-atp, tune-overfit)`
   The context-feature constants have never been swept: `FATIGUE_WINDOW_DAYS=14.0`,
   `LAYOFF_DAYS=120.0`, `PEAK_AGE=26.5` (config.py:328–330; `FEAT_PARAM_OVERRIDES`
   is empty). ~20 trials/tour (~2–2.5 min each), tag `_fp1`, then `--validate`.

2. **pa5 — WTA xgb re-sweep under post-A5 features** (Tier 1, `--group xgb`, WTA
   first) — `DONE-REJECT (R1-004: incumbent unbeaten post-A5+fp1; optimum robust)`
   A5 (ratings-only challenger ingestion, adopted 2026-07-06) changed the VALUES of
   the Elo/point feature columns the combiner consumes; the adopted WTA xgb params
   predate that shift, and WTA carries the open anchor gap. ~12 trials, tag `_pa5`.
   ATP only if WTA shows a real signal — ATP combiner re-sweeps have tune-overfit
   three times (tasks/tuning-results-2026-07-02.md).

3. **fp2 — WTA feat re-sweep around the post-fp1 incumbent** (self-generated, R1) —
   `DONE-REJECT (R1-005: 0/5 gate, new incumbent unbeaten in its neighborhood)`

3b. **ATP xgb re-sweep post-A5** (self-generated, R1) — `DONE-REJECT (R1-006: 4th
   instance of the ATP tune-overfit shape, regime-independent; do not revisit
   without a material frame change)`

3c. ~~Maintenance: extend feat layoff range~~ — `RESOLVED 2026-07-06` (post-R1
   harness maintenance: tune.py layoff_days range 365→730). Testable via **fp3**.

5. **fp3 — WTA feat re-sweep in the widened layoff space** (Tier 1, `--group feat`,
   WTA; tag `_fp3` — space changed, fresh tag mandatory) — `OPEN`
   The adopted `layoff_days=360` sat at the old 365 ceiling; the widened range
   (→730) makes "layoff flag fully off" reachable. Anchor = current incumbent.
   Low expected yield (R1-005 showed a local optimum) but the bound question is
   now answerable; cheap at measured feat costs (~25 min incl. validate).

4. **wta24 — WTA 2024 stats top-up** (data, needs API scrape) — `BLOCKED
   (user-supervised only: violates the no-download invariant; WTA 429s)`
   2024 merged coverage is 78.2%; a supervised backfill session is the path
   (tasks/tuning-results-2026-07-05-data-round.md, Phase B).

### R2 ideation fan-out (2026-07-06, 3-lens scout triage; discards logged in tuning-results-2026-07-06-autoresearch-r2.md)

6. **eloSx — overall-vs-surface Elo gap delta** (Tier 2, both tours) — `OPEN`
   New antisymmetric column `elo_overall_diff - elo_surface_diff`: an explicit
   surface-dampening term trees only approximate via sequential splits. Pure algebra
   of existing mirrored columns → zero parity burden. Cheapest open feature idea.

7. **sconf — per-surface match-count confidence diff** (Tier 2, both tours) — `OPEN`
   `log(w_sn+1)-log(l_sn+1)`; RatingState already tracks per-surface counts and the
   walk outputs w_sn/l_sn — features.py never surfaces them (only symmetric
   log_min_matches). Lets trees down-weight elo_surface_diff on thin surface history.
   Parity: small state accessor. Mechanism targets WTA surface variance.

8. **mty — combiner training-window floor** (Tier 2 scratch driver, WTA first) — `OPEN`
   Window is ALREADY expanding-from-1991 (train.py:240; scout's rolling→expanding
   premise was a misread). The real knob: `walk_forward(min_train_year=...)` —
   A/B floors 2000/2005 vs 1991; WTA distribution drift may make 1990s rows
   net-negative. Zero tracked-file changes until adoption. CAUTION: same family as
   rejected recency weighting (W1d) — hard truncation is a different mechanism, but
   apply extra per-year val scrutiny.

9. **h2hr — recent-h2h (3-year) diff** (Tier 2, both tours) — `OPEN`
   h2h dicts are career-flat; recent meetings should predict better than 2010-era
   ones. Parity burden medium: pair-date tracking in the h2h state + prediction
   mirror in the same commit.

10. **tierw — per-tier sample weighting in combiner folds** (Tier 2 scratch driver,
    both tours) — `OPEN` sample_weight already plumbed through _fit_fold; weight core
    rows by tier_k. NOT the rejected per-year recency weighting, but same
    importance-weighting family — expect simplicity-bias scrutiny at the gate.

11. **seedf — seed_rank_diff** (Tier 2, both tours) — `OPEN`
    winner_seed/loser_seed ingested but unused (entry_q_diff proves the raw pathway
    works). Redundancy risk vs Elo/rankpts. Parity precondition: verify the
    prediction-time upcoming-match feed carries seeds BEFORE building.

12. **retd — retirement-depth injury signal** (Tier 2, both tours) — `OPEN`
    parse_score discards where in the match a retirement happened; a late-match
    retirement is a stronger injury prior for the player's NEXT matches. Needs
    last-retirement state + mirror. Sparse-row risk; WTA fp1 layoff≈off is mild
    counter-evidence for injury-family signals there.

13. **pooled — cross-tour pooled combiner with is_wta flag** (Tier 2, WTA target) —
    `OPEN, low priority` Concat both frames, one combiner; WTA borrows ATP capacity.
    Heavy complexity (per-tour overrides conflict; eval harness is per-tour) —
    likely DECLINED on simplicity unless the win is large.

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
