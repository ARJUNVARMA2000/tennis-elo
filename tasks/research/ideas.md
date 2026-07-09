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
   WTA; tag `_fp3` — space changed, fresh tag mandatory) — `DONE-REJECT (R2-001:
   anchor unbeaten; layoff 493–695 configs val-negative or exactly zero — the
   flag-off region is flat, 360 was not a ceiling artifact)`
   The adopted `layoff_days=360` sat at the old 365 ceiling; the widened range
   (→730) makes "layoff flag fully off" reachable. Anchor = current incumbent.
   Low expected yield (R1-005 showed a local optimum) but the bound question is
   now answerable; cheap at measured feat costs (~25 min incl. validate).

4. **wta24 — WTA 2024 stats top-up** (data, needs API scrape) — `BLOCKED
   (user-supervised only: violates the no-download invariant; WTA 429s)`
   2024 merged coverage is 78.2%; a supervised backfill session is the path
   (tasks/tuning-results-2026-07-05-data-round.md, Phase B).

### R2 ideation fan-out (2026-07-06, 3-lens scout triage; discards logged in tuning-results-2026-07-06-autoresearch-r2.md)

6. **eloSx — overall-vs-surface Elo gap delta** (Tier 2, both tours) —
   `DONE-REJECT (R2-002: ATP d_val −0.00038 t≈−4, WTA tune-noise/val-negative;
   explicit recombinations of existing Elo columns are pure capacity cost — same
   shape as the E1 box-score rejection)`

7. **sconf — per-surface match-count confidence** (Tier 2, both tours) —
   `DONE-REJECT (R2-003: symmetric log_min_surf_matches gate; WTA d_val −0.00045
   at −3.75 SE with every 2021+ year negative — tune-era-only signal; ATP arm
   skipped. The antisym w_sn/l_sn diff variant is presumed dominated: weaker prior
   + R2-002's capacity-cost evidence — do not spend a Tier-2 without new reasoning)`

8. **mty — combiner training-window floor** (Tier 2 scratch driver, WTA first) —
   `DONE-REJECT (R2-004: floors 2000/2005 both d_tune-negative; early test years
   lose the most and 2024-26 gains a little — drift exists but truncation overpays
   for it, and the graded version is the already-rejected W1d recency weighting)`

9. **h2hr — recent-h2h (3-year) diff** (Tier 2, both tours) — `DONE-REJECT (R3-001: WTA passed narrowly, but ATP d_tune -0.00004 / d_val -0.00014; 6/17 years positive)`
   h2h dicts are career-flat; recent meetings should predict better than 2010-era
   ones. Parity burden medium: pair-date tracking in the h2h state + prediction
   mirror in the same commit.

9b. **srrp — rate-conditioned serve prior** (Tier 1/2, WTA-only) — `DONE-REJECT (R3-003: component pass at 0.25, but full WTA arbiter d_val -0.00043+/-0.00010; 8/17 years positive)`
    The rejected E1 block exposed raw ace/DF/first-in differences to the combiner.
    This distinct mechanism stores decayed rate state and uses it only as a shrunk
    prior for the existing opponent-adjusted SPW estimate when direct SPW evidence
    is thin; it adds no combiner columns and vanishes for well-observed players.

9c. **rankord — ordinal-rank difference** (Tier 2, WTA-first) — `IN-PROGRESS (R3-004; self-generated)`
    `rank_points` is modeled but the raw ordinal rank is not. Historical main-draw
    pair coverage is 96.5% WTA / 97.9% ATP; prediction uses the existing official
    rankings cache with a latest-historical-rank fallback. This is raw new state,
    not an algebraic recombination.

9d. **mcp-shortwin — charted short-rally win rate** — `DONE-DECLINED (R3 ideation: two-player coverage shifts 22.9% tune -> 68.4% validation; sparse star-biased regime and two-column capacity cost make the result inadmissible this round)`

10. **tierw — per-tier sample weighting in combiner folds** (Tier 2 scratch driver,
    both tours) — `DONE-REJECT (R2-005: tier_k^2 uniformly negative on WTA LL,
    tier_k^4 monotonically worse — upweighting slams sharpens accuracy but
    miscalibrates; importance-weighting family 0-for-2 with W1d)`

11. **seedf — seed_rank_diff** (Tier 2, both tours) — `BLOCKED (R3: upcoming feed has no seeds; wiki cache requires a separate data/integration experiment with explicit missingness semantics)`
    winner_seed/loser_seed ingested but unused (entry_q_diff proves the raw pathway
    works). Redundancy risk vs Elo/rankpts. Parity precondition: verify the
    prediction-time upcoming-match feed carries seeds BEFORE building.

12. **retd — retirement-depth injury signal** (Tier 2, both tours) — `DONE-DECLINED (R3 Tier 0: 2010+ next-match win rate rises rather than falls for late retirements: WTA 53.4% early vs 54.0% late; ATP 50.6% vs 53.1%; no evidence to justify reopening the rejected ret_recent family)`
    parse_score discards where in the match a retirement happened; a late-match
    retirement is a stronger injury prior for the player's NEXT matches. Needs
    last-retirement state + mirror. Sparse-row risk; WTA fp1 layoff≈off is mild
    counter-evidence for injury-family signals there.

13. **pooled — cross-tour pooled combiner with is_wta flag** (Tier 2, WTA target) —
    `DONE-REJECT (R2-006: WTA d_val −0.00578 with ±10–18 SE per-year flapping, ATP
    ±32 SE — training-distribution contamination exactly like the A5 full variant;
    a tour flag does not rescue pooling)`

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
| Pure-recombination combiner features (eloSx; also the E1 shape) — new columns must carry NEW state, and even then face a ~0.0003 LL capacity toll | tuning-results-2026-07-06-autoresearch-r2.md R2-002 |
| Surface-sample confidence gate (sconf log_min_surf_matches; antisym variant presumed dominated) | tuning-results-2026-07-06-autoresearch-r2.md R2-003 |
| Combiner training-window truncation (mty; graded version = W1d) | tuning-results-2026-07-06-autoresearch-r2.md R2-004 |
| Tier/importance sample weighting in combiner folds (tierw; family 0-for-2 with W1d) | tuning-results-2026-07-06-autoresearch-r2.md R2-005 |
| Cross-tour pooled combiner, tour flag or not (contamination = A5-full shape) | tuning-results-2026-07-06-autoresearch-r2.md R2-006 |
