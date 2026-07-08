# Lessons

- **A new data-backed web page is a 6-part contract; miss one and it silently
  half-works.** (2026-07-08, /schedule) (1) add a `build_*` in `model/export.py` +
  a `_write(tour, "X.json", ...)` line in `export_all` — it's auto-mirrored to
  `web/public/data/<tour>/` by `pipeline._mirror` and regenerated on full AND
  `--quick` runs; it's overwrite-only output (like fixtures.json), so NO refresh.yml
  persistence step (that's only for append-only state like forecast_log). (2)
  `web/public/data/` is gitignored + machine-generated, so generate the JSON locally
  from the saved model (`TennisPredictor.load(tour)` + `load_matches(tour)` + the
  builder) or the dev page hangs on `<Loading/>`. (3) `page.tsx` is `"use client"` +
  `useData<T>("X.json")` — the global tour context auto-switches ATP/WTA, the page
  does nothing. (4) client pages can't export `metadata`, so add a sibling server
  `layout.tsx` (`export const metadata = pageMetadata(slug)`) AND a `PAGE_META` entry
  in `web/lib/seo.ts`. (5) a `Nav.tsx` GROUPS item — `isActive` uses
  `path.startsWith`, so a slug that prefixes another (`/predictions` vs `/predict`)
  double-highlights; pick a non-prefix slug. (6) handle empty/missing data
  (`useData` sets `data=null`/`error`) with an explicit empty state. Reuse `CallCard`
  (two players + prob bars, `tone` for result vs projection), `pct`, `surfaceColor`.
  See [[future-proof-no-quick-fixes]].

- **Live tournament reach-odds must be seated on the ACTUAL draw, not a rating
  re-seed.** (2026-07-08) The live scorecard showed Sinner 97% + Djokovic 55% to
  reach the same final while they actually met in the SF (must sum to 100%). Cause:
  `project_field` → `standard_seed_draw` re-seeded survivors into a synthetic
  1v4/2v3 bracket. Field-strength dominates *champion* odds on a full draw, so this
  looked harmless — but it makes the round-by-round SF/F reach table nonsense, most
  visibly once the draw is small and the real pairings are known. The real matchups
  were already on disk: `data/live.parse_upcoming` writes them to `upcoming.csv`
  (and `eval/track` reads it), the projector just never opened the file. Fix:
  `sim/draws.live_draw` seats survivors by their real current-round matchups (pairs
  adjacent; already-advanced players get a bye into the next round), seeding only
  the genuinely-unknown downstream pairings; completed events keep full-field
  seeding (that path is a deliberate pre-tournament hypothetical). Rule: any
  live/forecast surface that shows per-round structure must consume the real draw
  from `upcoming.csv`; a "sums to >100% across two players who face each other" is
  the canary. See [[plans-adapt-to-landed-code]].

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

- **Verify a source's naming convention per file, not per format.** (2026-07-02)
  "XXX vs YYY" tie names are host-first in the ATP Davis Cup file but carry NO
  venue order in the WTA Fed Cup file (single-venue weeks; arbitrary/winner-first
  ordering) — the same regex, trusted uniformly, silently mislabeled ~8% of WTA
  training rows with a flag that partially encoded outcomes. Rule: before deriving
  a feature from a naming convention, verify it against known ground truth in EACH
  source file it will touch (a handful of known-venue rows per file suffices).

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

- **Pin dependencies to the environment that owns the production artifacts, not the
  dev machine.** (2026-07-02) Pinning requirements.txt from a local `pip freeze`
  downgraded CI (sklearn 1.9.0 → 1.5.2) under a cached predictor.pkl pickled at
  1.9.0 — the quick deploy crashed on unpickle (`LogisticRegression` lost
  `multi_class`). Rule: before pinning, read the versions out of the last
  successful CI run's install log; upgrade local to match, never the reverse.
  Cross-version pickle compatibility is the constraint, not "what my venv has".

- **A lockfile regenerated on one OS can be incomplete for another.** (2026-07-02)
  `npm install` on Windows wrote a package-lock.json missing Linux-side optional
  native deps (@emnapi/*); CI's `npm ci` refuses it. Rule: after adding a dep, run
  `npm install --package-lock-only` (computes the full cross-platform ideal tree)
  and verify with `npm ci` before committing the lockfile.

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
