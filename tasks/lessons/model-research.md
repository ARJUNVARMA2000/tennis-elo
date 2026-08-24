# Model & research

Tuning, features, the arbiter, predictor state and parity, odds/Kalshi evaluation.

Indexed in [`../lessons.md`](../lessons.md).

- **A frozen-field policy needs a VALIDITY predicate, not a kind check — and every
  "who quotes when" race is a leak vector.** (2026-07-09, Kalshi ledger audit: 25
  rows/tour scored in-play Wimbledon prints, 6 ATP rows scored the SETTLED book, one
  market scored an 18-day-old result of the same pair; net effect: ATP headline
  −0.0015→+0.0064, WTA −0.0260→−0.0226, and the whole ATP fav-0.9+ "anomaly" was the
  leak.) The traps, each now pinned by a test + a blocking health invariant:
  (1) *Pending-race freeze*: hourly snapshots freeze an occurrence-anchored (T-5)
  candle; a row written pending then matched later skipped the 08:00 re-anchor because
  the skip set asked "is a candle frozen?" not "is the frozen quote valid for THIS
  row's result_date?" (`_scoring_quote_ok`). The requoter is the only writer allowed to
  override a frozen price (`_requoted` mark) — and it must use the match identity that
  SURVIVES the merge (frozen prior first), else a transient results-source gap strands
  the bad quote. (2) *`include_latest_before_start` is a leak vector*: when a result
  source dates a match day+1, the 08:00 window is empty and the API's synthetic carry
  imports the settled book (0.995 on the winner, "confirmed" 6/6). A carry candle at/
  before the window start with an extreme mid is a settled print, never a line — reject
  at selection (`EXTREME_CARRY_MID`). (3) *A wide join window admits stale rematches*:
  a market listed before its match binds the pair's previous result if it's the only
  in-window candidate, and `_FROZEN_MATCH` locks it forever. Durable fix is layered:
  one result row = one ticker (claims), far-forward candidates must agree with the
  market's parsed tournament (the tiebreaker becomes a validator), Kalshi's own
  settlement contradicting the join is an auto-veto, and healing unfreezes only
  OBJECTIVELY wrong rows (settlement disagreement, double-claim) so archive-dated
  joins stay stable. (4) *Pooled QA hides month-local leaks*: the t30 sentinel's
  pooled p95 (0.010) looked clean while July-only p95 was 0.208 — slice sentinels by
  month/anchor-class; and a sensitivity line that can never fire (retirements: all
  such rows lack p_model by construction) must say so itself.

- **Odds-source coverage can silently truncate an eval window — census the books per era,
  don't trust the frame.** (2026-07-09, market.json) tennis-data stopped carrying Pinnacle
  (PSW/PSL) after 2026-01-13 (ATP 71/1466 rows in 2026, WTA 101/1422, none later), and
  `eval/compare.py` picked ONE book frame-wide ("ps" if the column exists anywhere) then
  `dropna` — so the "2020+ validation" closing-line card gained its last row mid-January and
  sat frozen for ~6 months while rendering next to a May–July Kalshi card. Fix shape: (1)
  coalesce the line PER ROW (ps→b365→avg, same de-vig) and export a per-year `sources.byYear`
  census + derived honest `label` that the UI renders verbatim; (2) export `oosEnd` vs
  `lastMatchedDate` and flag a >60d gap in `health.py` (ADVISORY, not gate-blocking — odds
  are a benchmark, never a deploy dependency); (3) an era-matched `recent` block (trailing
  90d paired Δ±SE) so a 2-month market window is never eyeballed against a 6.5-year average.
  Rules: an eval joined to an external source must state IN ITS PAYLOAD which source backed
  each era — a benchmark labeled "Pinnacle" must fail loudly the day Pinnacle vanishes; and
  benchmark labels in page copy derive from that payload, never hardcoded.

- **A combiner feature that adds no new state is a pre-paid loss: budget a
  ~0.0003 LL capacity toll for any new column.** (2026-07-06, round R2) Adding
  `elo_osgap_diff` — pure algebra of two columns already in the frame — measured
  d_val −0.00038 (ATP) / −0.00032 (WTA) with no compensating tune gain; the
  E1 box-score rejection had the same shape. Even the genuinely-new-state
  surface-count gate lost more to the toll + overfit than its signal was worth.
  Rule: when costing a feature idea, its expected validation signal must clear
  the toll, not zero; pure recombinations of existing columns never qualify
  (trees already approximate them), so spend those Tier-2 slots elsewhere.

- **The tuning feature cache is regime/schema-keyed, not param-keyed.** (2026-07-06)
  After adopting new FeatureParams (fp1), the cached `_features_wta*.pkl` still
  carried pre-adoption feature values; the next `group=xgb` sweep would have tuned
  the combiner against a stale frame and measured deltas off a phantom baseline.
  Production is immune (the pipeline builds frames fresh each run) — only
  `load_or_build_features` consumers are exposed. Rule: after adopting any parameter
  that changes recorded feature values, delete `_features_{tour}*.pkl` before the
  next cache-reading sweep; frame-building groups (feat/elo/point) are immune
  because they rebuild per trial.

- **A data-ingestion experiment is two experiments; separate them or the gate
  measures the wrong thing.** (2026-07-05) Ingesting challengers "fully" (rows in
  the walks AND the combiner) produced +0.0087 tune LL but failed validation with
  ±0.03 per-year swings — the challenger-dominated row mix destabilized fold
  training and prior-season calibration. The ratings-only variant (walks see the
  rows, combiner never does) passed at 7.6 SE with 17/17 years positive and was
  adopted. Rules: (1) score both arms on the IDENTICAL main-draw eval set — new
  rows must never enter the scored set or d measures eval drift, not model
  quality; (2) when a data addition shifts the training distribution, always run
  a ratings-only / states-only variant before concluding anything from the full
  variant; (3) per-year paired d is the instability tripwire — a real prior
  improvement lifts every year a little (17/17 positive), a distribution artifact
  flaps year-to-year at ±10 SE in both directions.

- **Re-read the git tip immediately before finalizing any plan or doc built from
  exploration.** (2026-07-05) A README-refresh plan was drafted from subagent
  exploration of the repo state, but three commits (including an adopted model
  change that moved the headline Brier numbers) landed between exploration and
  the final plan — the plan quoted stale metrics until the user said "check the
  latest commits". Rule: exploration results have a timestamp; before writing
  conclusions that cite repo facts (metrics, features, file lists), run
  `git log` again and diff against the commits the exploration actually saw.

- **Never include the current estimate in the residual it learns from.** (2026-07-02)
  The event-speed accumulator measured residuals against an expectation that
  already contained the current offset — the fixed point of that recursion is
  HALF the true effect, independent of the shrinkage constant. Rule: residual
  accumulators learn against the estimate-free expectation; write a unit test
  that pins the exact converged value, not just the direction.

- **A feature that walks can't be adopted unless the pickled state can replay
  it.** (2026-07-02) Two of today's knobs (event offsets, Elo home bonus) baked
  venue effects into recorded training features while the saved state had no way
  to reproduce them at inference — a parity break invisible to the walk-forward
  arbiter (both sides come from the same pass) that only bites production. Rule:
  every new walk-time signal needs its prediction-time mirror (state method +
  parity test) in the same commit, or must be recorded venue/context-free.

- **An API field's semantics can mutate over an object's lifecycle — validate on
  the SETTLED objects you'll actually score, not the live ones you explored.**
  (2026-07-07) Kalshi's `occurrence_datetime` looked like a clean scheduled-start
  on open markets, but it is a draw-time placeholder for smaller events (actual
  play trailed it by 3–7 days for ~215/955 ATP events) AND on settled markets it
  drifts to ~the determination time (close_time lands seconds after it) — so
  "quote at T−5 before occurrence" silently scored final in-play prices for part
  of the set. The pre-registered leak sentinel (a second quote 30 min earlier,
  p95 |Δ| = 0.23) is what caught it. Rules: (1) join windows against market
  timestamps must tolerate play up to ~a week later (ledger uses −8..+21 vs
  result dates); (2) anchor scoring quotes only to timestamps YOU own — the
  ledger uses 08:00 UTC on the result row's date, provably pre-match for this
  era's event footprint and immune to upstream mutation; (3) always ship a
  cheap redundant-measurement sentinel with any external price/time source.

- **Duplicated construction sites drift: production shipped WTA pickles with fp=None.**
  (2026-07-09) `fit_predictor()` passed `fp=feat_params_for(tour)` to `TennisPredictor`, but
  `pipeline.build_tour` reimplemented the same construction inline and omitted it — so every
  shipped `predictor.pkl` carried `fp=None` and inference fell back to config defaults (WTA:
  layoff 360→120d, peak age 24→26.5) while the combiner was trained on tuned frames. Invisible
  to the walk-forward arbiter (it scores frames, never a `TennisPredictor`) and to the health
  gate (the JSON stays self-consistent — just built from the wrong thresholds). Fix: derive the
  invariant IN the constructor (`fp = fp if fp is not None else feat_params_for(tour)`) so no
  call site can forget it, and drop the redundant explicit arg — leaving it would re-signal that
  callers must remember. `_predictor_current` (quick-path guard) now also compares the pickle's
  `_fp` to the tour's current config and rebuilds on drift, healing shipped-bad pickles within
  an hour. Rules: derive invariants in the constructor, not at call sites; a staleness guard
  must check every config a pickle bakes in (schema AND params), not just the crash-prone part.

- **Widening a helper's return arity is invisible to tests that exercise the helper and its
  caller separately — rebuild the real artefact.** (2026-07-27) `_known_surface` was changed
  to return `(surface, source)` so a card could report where its surface came from. Its unit
  test was updated, its caller `_archive_attrs` was not — and `_archive_attrs` forwards that
  value straight into `resolve_surface_info` as `archive_surface`, which returns it verbatim.
  WTA Memphis therefore shipped the literal tuple `('Hard', 'archive')` as its surface. The
  full suite (381 tests) passed: every test covered one side of the seam. What caught it was
  rebuilding the actual tournament cards from the local frame and eyeballing the fields.
  **How to apply:** after changing any shared helper's shape, grep every call site in the same
  edit — and for a producer whose output ships, regenerate a real artefact and assert on its
  TYPES, not only that the pipeline ran. A one-line `isinstance(t["surface"], str)` over
  rebuilt cards is worth more than another unit test of the helper.

- **A chronological state experiment can still leak backward through full-frame priors.**
  (2026-08-17, WTA qualifying/125 A/B) The first lower rows were in 2016, yet the initial arm
  changed 2010 predictions because the serve/return walk computed its league and surface priors
  from the entire augmented frame before walking. The headline gate passed, but it was not a
  state-only result. **How to apply:** compute shared aggregate priors from the identical admitted
  main population, let experimental rows affect only chronological updates, and hard-fail unless
  predictions before the first intervention row are bit-identical. A plausible d±SE table is not a
  substitute for a negative-control period.

- **A feature-row gate does not protect baseline predictions when its shared combiner is
  retrained.** (2026-08-22, WTA dual-state gate) The first implementation selected enriched
  feature rows only for cold-start matches, but trained one XGBoost/Platt model on that mixed
  frame. Gate-protected rows still regressed by −0.00089±0.00014 and both-top-50 matches by
  −0.00118±0.00025 because the fitted trees and calibration had changed globally. The corrected
  design fits each fold once on the unchanged main-only baseline and applies enriched state only
  to eligible test rows; protected probabilities are then bit-identical, while validation improves
  +0.00098±0.00066. **How to apply:** when a gate promises protection, include the complete fitted
  path—features, model, and calibration—in the invariant, and assert exact output parity on every
  protected row rather than inferring safety from routing logic.

- **A checksum is not a pickle compatibility contract, and inspecting the object after unpickling
  is already too late.** (2026-08-24, Round 4A predictor envelope) A payload hash proves only that
  bytes did not change; it says nothing about the runtime, library versions, feature order, tuned
  parameters, bag membership, calibrator, tour, or inference-state shape those bytes require.
  **How to apply:** bound and parse a strict non-public envelope, verify its exact payload length and
  SHA-256 plus runtime/dependency/configuration contract before deserialization, then validate the
  concrete predictor, every fitted booster, calibrator, and required state structure afterward.
  Make quick reuse call the same guard so the fast path cannot bypass the release contract; keep any
  legacy exception explicit, observable, and temporary.
