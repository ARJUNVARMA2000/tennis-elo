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

- **`O_NOFOLLOW` on the filename is not a trusted-root boundary.** (2026-08-24, Round 4A
  filesystem review) A final-component no-follow open still traverses a symlinked tour directory,
  so a restored cache containing `data/output/atp -> external` could redirect the quick path's
  read and `pickle.loads`, while `mkstemp(dir=path.parent)` could publish payload, envelope, and
  pending files outside `OUTPUT_DIR`. **How to apply:** anchor predictor operations to the expected
  output root; check lexical and resolved containment; `lstat` every existing component from the
  root through the parent; reject symlinks, non-directories, and cross-tour aliases before reading,
  deserializing, creating a temp file, replacing, or unlinking. Keep a portable final-component
  symlink check even when `O_NOFOLLOW` is unavailable, and prove rejection happens before
  `pickle.loads` and before any external filesystem change.

- **Forecast eligibility must follow the state bundle the adopted gate actually selects, not
  baseline archive membership.** (2026-08-29, Frodin–Rybakina) The adopted WTA cold-start path
  could select a qualifying/WTA-125 state, but scheduled acquisition omitted those current-season
  rows and exporters independently checked only the main-state player set. A player with valid
  lower-state evidence was therefore silently unpriced. **How to apply:** bootstrap current-season
  main and lower rows before incremental refreshes, keep the lower rows out of the main population,
  centralize eligibility around the predictor's selected state, and use that contract in every
  forecast consumer. A complete draw with an unpriced real-vs-real match must block publication.
  Treat broader ITF admission as a separate model change requiring walk-forward backtesting.

- **A saved temporal state needs pending evidence as well as admitted totals.** (2026-09-06)
  Recovering event-end availability exposed a gap: the historical walk would admit a
  match's statistics at a later event-end date, but a predictor saved before that date
  discarded the remaining observations. Its later forecasts therefore used another
  prior. Preserve a validated, ordered pending queue in the artifact; a date query
  admits eligible observations into a copied view without changing the saved state.
  Test strict same-day exclusion, later-date walk parity and a real save/load roundtrip.

- **A slice label does not establish the population its counts measure.** (2026-09-06)
  The frozen `low-main-experience` diagnostic reads pre-match state counts. Those are
  main-only for WTA, but include lower history in ATP's adopted enriched walk. The same
  label therefore describes different populations across tours. Preserve and report the
  actual count provenance; do not compare those slices as equivalent. A semantic repair
  belongs in a separately versioned diagnostic change, never a silent mid-round relabeling.

- **Validate numerical integration in the uncertainty regime the model can actually reach.** (2026-09-06)
  A 20-node Gaussian quadrature looked adequate at the initial prior but missed a broad
  logistic-normal probability by 0.03031 after uncertainty growth. Compare predictions
  and posterior moments against an independent high-accuracy integral across variance
  regimes before examining outcome scores. Use adaptive integration or fail explicitly
  when a fixed rule is insufficient; numerical error is not a model improvement.


- **A saved-query equality check and a historical match-row check have different inputs.**
  (2026-09-07, uncertainty shadow) All 43 features survive serialization exactly and
  all 19 learned-state features match their historical walk values, while frozen player
  rank/age metadata differs from what a later match row supplies. Report those contracts
  separately; do not turn a state-parity result into a claim of complete match-context
  equality. Normalize missing context too: `bool(NaN)` made two QA matches falsely
  indoor, despite the training frame's neutral zero. Preserve the original diagnostic
  and correct its input context explicitly, without changing fitted outcomes or sources.

- **A result update is not a complete settlement snapshot.** (2026-09-07)
  The old prospective grader retained source files but indexed only the current batch,
  so reporting a later event would make previously scored forecasts pending again.
  The separately versioned mixed-format runner accumulates all admitted batches,
  keeps pending updates from erasing terminal facts, and excludes conflicting terminal
  claims while preserving them. Test two disjoint batches, retries, partial-to-complete
  evidence and conflicts. Fix the intake endpoint before observing scores; late batches
  must not extend it. Retained files alone do not prove accumulated reporting.


- **HTTP freshness does not establish match-time semantics; represent the bound the experiment needs.** (2026-09-07)
  The real ESPN/WTA source audit corroborated 119 completed results but did not establish
  actual start/finish fields. A false estimate flag, `startDate`, fetch time or score
  transition cannot silently stand in for actual play. Preserve exact acquisition
  receipts and distinguish transport age from upstream update latency. The earlier
  prospective contract also demanded an exact finish unnecessarily: a verified
  completed observation may establish an upper bound, while pre-play proof requires
  a defensible start lower bound. Version that change explicitly and validate the
  evidence producer before live use. Never upgrade clock-simulated QA to live evidence.


- **A result producer must carry contradictions as well as confirmed matches.** (2026-09-07)
  Filtering a source update down to agreeing normal results can make a later terminal
  disagreement disappear, leaving an earlier result eligible forever. The external
  completion producer retains conflicting terminal claims and provider identity rows;
  the bounds evaluator excludes their affected forecasts. Test a real source fixture
  mutated to disagree on one terminal outcome, plus an identity-only replacement update.
  A merely delayed live/complete pair is not two contradictory terminal claims.

- **Resolve the owning checkout and working directory before constructing a research command.** (2026-09-07)
  The original checkout carries documentation while implementation files live in isolated
  research checkouts. Reusing root-relative tennis_model paths after selecting that
  directory caused failed file creation; assuming a test filename caused an empty run.
  Use absolute paths for private drivers/tools, inspect the actual test list, and preserve
  failed launch logs separately. A command launch failure is not a model experiment.


- **A timestamp and its derived elapsed clock can agree throughout corrupted data.** (2026-09-07)
  The US Open point sample had a constant `EpochTimeStart - ElapsedTime` for every
  point in both matches, including 114 start-after-end rows in one match. Algebraic
  agreement is not independent timing validation. Require field semantics, defensible
  precision and real chronological checks before a source can establish pre-play proof;
  retain contradictions and never repair day offsets just to make a history plausible.


- **A schedule catalogue's epoch can identify a different date from its published order.** (2026-09-07)
  US Open's day-17 catalogue epoch resolved to September 7, while the September 8 PDF
  heading, JSON label and every court start agreed on September 8. Preserve each field's
  role; use explicit edition, printed calendar and corroborating venue clocks for schedule
  extraction. Do not promote generic epochs to played times. Keep explicit not-before,
  first-session start and sequence-only evidence separate, even when their UI looks similar.


- **An official catalogue can mix match days with unrelated navigation entries.** (2026-09-07)
  The US Open catalogue includes a practice link with `tournDay: null`; an initial
  all-row numeric-day invariant rejected both valid retained schedules. Classify that
  explicit practice entry before validating match-day identities, while rejecting
  unknown null-day records. Exact whole-response fixtures catch assumptions that
  a handpicked match-only sample misses. The regression belongs in source intake.


- **A provider-looking player number is not proof of a shared ID namespace.** (2026-09-08)
  The official US Open draw prefixes IDs with `wta`, yet 23 matchups have different
  numbers from WTA match rows while 119 full results corroborate the event. Validate
  IDs per canonical player, preserve both numeric claims and exclude disagreements;
  neither stripping a prefix nor matching the unordered ID pair handles side swaps.
  Do not turn this audit into an alias-table edit outside the established proposer.


- **Multiple day listings in one order page are not observed temporal revisions.** (2026-09-08)
  WTA's completed Guadalajara page retained 65 occurrences for 59 MatchIDs, including
  31 main-singles occurrences for 27 matches, but no original start labels. Preserve
  occurrence keys by edition/day/MatchID and compare complete occurrence sets between
  independently timed collections. Do not interpret adjacent rows from one snapshot as
  a revision sequence or reconstruct lost published times from completed API timestamps.
  Whole raw HTML fixtures also preserve whitespace in printed rounds: normalize visible
  text before checking round identity. Test retained page structure, not an invented fragment.


- **A publisher's coarse LIVE status can include OnCourt and warm-up.** (2026-09-08)
  WTA's own bundle maps these pre-play stages into LIVE. Two real Guadalajara event
  arrays have distinct InProgress markers 21–24 minutes after the main match timestamp,
  yet the last scoring records remain P even after the API reports a completed result.
  Keep coarse display state, reported start, final-score corroboration and physical
  clock qualification separate. A synthetic uniform ten-minute shift preserves local/
  UTC/elapsed agreement and still must not become actual-start proof. Whole-record
  fixtures also show MedicalTreatment omits Attributes.type: check conflicting duplicate
  fields only when supplied, rather than treating that real optional field as corruption.


- **An official match-start definition is not a public feed's clock contract.** (2026-09-08)
  Primary rules define first serve and prompt handset scoring, but do not map public WTA
  InProgress.Timestamp to a physical trigger with a measured UTC error. A separate
  authenticated API's actualStartDate cannot supply that missing namespace bridge.
  Verify main-tour rather than WTA 125 sections and keep PDF/printed page numbers distinct.
  For calibration, independently bound observation-clock error and broadcast delay;
  agreement among fields sharing one clock, or a finite sample maximum, cannot certify
  an unseen future error bound. When this premise is missing, preserve a concrete
  measurement protocol rather than implementing another generic audit layer.


- **A blocked live-confirmation dependency must not consume the model-improvement program.** (2026-09-08)
  User correction: return the next round to systematic incumbent errors, new hypotheses
  and bounded historical experiments. Several successive source/clock rounds improved
  evaluation infrastructure without testing another predictive mechanism. Keep that work
  available, but do not make the entire research agenda wait for live timing evidence.
  Diagnose saved walk-forward predictions on tuning years, select and freeze candidates
  there, and report a concrete tried/improved/failed table. Treat reused 2020+ results as
  validation, not an untouched holdout; keep fresh prospective confirmation separate.


- **A systematic calibration slice is a hypothesis source, not proof of its apparent cause.** (2026-09-08)
  First recorded WTA appearances were underconfident by 6.24pp in 696 tuning matches, but
  neutralizing their artificial 365-day absence worsened log loss. A 40-point per-match
  serve cap gained 0.000084 overall yet lost 0.000131 in the later tuning half. Register
  stability requirements before fitting, preserve negative results and keep a small
  pooled gain from buying a new validation look after its required stability check fails.


- **A closed shortlist is not an exhausted research program.** (2026-09-08)
  User correction after three small historical trials: try more mechanisms. Preserve
  the prior round's preregistered stopping and advancement rules, but start a separately
  registered round that seeks new information. Do not equate several failed encoding
  or weighting tweaks with proof that the model cannot improve, and do not substitute
  another infrastructure round for the requested predictive experiments.
