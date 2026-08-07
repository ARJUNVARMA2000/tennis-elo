# Task: Improvements round — ship /method + repo consolidation, then Bracket explorer (2026-07-13)

Goal: a broad "any improvements" round. Part 1 (shipped): merge the stranded
method-page-detail branch (the method.json-driven full-methodology /method page) which had
fallen 17 commits behind master, and consolidate repo hygiene. Part 2 (in progress): a new
Bracket/Draw explorer tab rendering the authoritative Wikipedia draws the pipeline already
ingests, round by round, with the model's pre-match win prob on every match.

## Part 1 checklist — DONE
- [x] Pre-flight: no concurrent pipeline/arbiter; origin/master at daily eval-log commit.
- [x] Clean working tree: discard stale todo.md hunk + scheduled-actor data-log churn.
- [x] Rebase method-page-detail (1 commit) onto origin/master (17 ahead). Conflicts only in
      the two append-logs (lessons.md, todo.md) — kept both sides in date order. health.py /
      config.py / test_health.py auto-merged cleanly (my method.json checks grafted onto
      master's rewritten monitoring structure); verified semantically, not just textually.
- [x] Verify: 271 pytest + ruff clean; 148 vitest + eslint clean; static build (18 routes);
      /method rendered both tours on :3001 via Playwright (constants flip ATP 0.63/1.28/145
      ↔ WTA 0.62/320, featureCount 42, no JSX word-glue, no console errors); health --gate green.
- [x] Merge --ff-only to master, push (deploy run 29223604453 green through integrity gate +
      Pages deploy); live method.json serves the new structure (protocol tuneYears/valStart).
- [x] Prune: 4 local branches (freshness-monitoring, health-page, codex/fix-completed-main-draw,
      method-page-detail) + 3 remote + 2 worktrees (Tennis Elo-deploy-fix, heuristic-euclid).

## Part 2 checklist — DONE
- [x] sim/bracket.py: bracket_rounds (slots-forward fold, results-joined; NOT advance_slots'
      frontier fold) + price_bracket + oriented_logged; test_sim_bracket.py (13, incl. the trap).
- [x] Wire sim/tournaments.py (attach bracket in project_tournament/project_upcoming, price in
      build_tournaments via forecast-log join for honest completed-match probs).
- [x] model/export.py split → brackets.json (+ hasBracket on tournaments); data/health.py
      _check_brackets invariants; extend test_export.py (+1) / test_health.py (+12).
- [x] web: /bracket route (BracketTree.tsx, lib/bracket.ts, page + layout, seo.ts, Nav Matches
      group), reach-odds join, deep-link ?e=, empty states; bracket.test.ts (10); verify.mjs route.

## Review
- Part 1 shipped 2026-07-13; production /method live with full methodology for both tours.
- Part 2 shipped 2026-07-13. New /bracket tab renders the authoritative Wikipedia draws the
  pipeline already ingests, round by round. Completed matches carry the honest pre-match prob
  locked in the forecast log (a post-hoc recompute leaks post-match ratings — flagged "retro"
  when unlogged); pending matches use the current model so the bracket and /schedule agree.
- The frontier-fold trap (sim.draws.advance_slots mis-credits a player who won R1 then lost R2)
  is routed around by a results-joined forward fold, pinned by test_sim_bracket.
- Proof: 296 pytest + ruff clean; health --gate green with the new bracket invariants on REAL
  data (ATP Wimbledon 128, WTA 32+128); 158 vitest + lint + typed build (21 routes); Playwright
  walkthrough on :3000 — ATP 128-draw feeders correctly centred, upsets/seeds/scores/logged-vs-
  retro all render, section chips swap the sub-draw, WTA Bo3/2-section cross-tour, mobile scrolls
  the tree inside its box (page body does not), no console errors.
- Deviations: removed the per-card whileInView fade (kept below-the-fold cards invisible until
  scrolled — wrong for a static bracket); pinned round labels above the justify-around cards so
  feeders align. No refresh.yml change (overwrite-only artifact; mirror glob + both run modes cover it).
- **Production hardening (same day).** The first two /bracket deploys were BLOCKED by the
  pre-deploy gate on real data the clean local snapshot never exercised — both were bugs in my
  own invariants, not the data (last good deploy stayed live throughout): (1) the champion
  cross-check compared on casefold, flagging a diacritic-only spelling (results winner_name vs
  elo-canonical) — fixed to compare on _name_key. (2) the drawSize check excluded "Qualifier N"
  placeholders while tournaments.json drawSize counts them, so Gstaad's early-frozen draw (2
  named + 26 qualifiers = 28) read "2 round-0 players but drawSize 28" — fixed to count non-null
  slots. Both reproduced + pinned by tests; lesson recorded. Third deploy went green (Wimbledon
  completed with a champion + Gstaad both pass). (3) Follow-up quality guard: an early-frozen
  draw that's mostly unresolved placeholders shipped a wall of "Qualifier" cards; skip attaching
  a bracket unless a real majority of entrants are named (bracket_is_meaningful) — resolved draws
  (Wimbledon 128/128, a normal event with a few qualifiers) clear it, the 2/28 Gstaad doesn't.

---

# Task: Fix Wimbledon-final deployment failure (2026-07-11)

Goal: restore hourly Pages deploys after the WTA Wimbledon final switched tournament
projection into a completed-event path that included qualifying players and built an
impossible 256-slot bracket.

## Checklist
- [x] Inspect the two failed refresh runs and isolate `KeyError: 256` to WTA projection.
- [x] Reproduce the transition with a completed 128-player main draw plus qualifying rows.
- [x] Filter completed projections to `draw_level == "main"` when that provenance exists.
- [x] Add an output-health invariant blocking any singles draw above 128 players.
- [x] Run targeted and full Python verification.
- [x] Push the production fix and confirm a successful refresh + Pages deployment.

## Review
- Root cause confirmed from two Actions traces: after the WTA final arrived, the
  completed path unioned main + qualifying participants, `standard_seed_draw` padded
  the >128-player set to 256, and `simulate_tournament` failed on unsupported round 256.
- Fix is population-scoped, not a simulator expansion: completed projections now use
  main-draw knockout rounds only. A blocking health invariant rejects any future
  `drawSize > 128`.
- Local proof: focused tournament/health suites 51 passed; full suite 263 passed; ruff clean.
- First production retry (`2651a95`) exposed that source/legacy Q1/Q2 rows can be
  default-labelled `draw_level=main`; the same KeyError survived the provenance-only filter.
  Follow-up regression uses that production shape and filters recognized knockout rounds too.
- Second production retry (`e7e189e`) still produced the generic `KeyError: 256`, proving
  the offending bracket is not identified by those assumptions. Added a fail-fast diagnostic
  carrying tour/event/field/alive/completed/draw-state/wiki-slot context; next production trace
  will identify the exact construction path without weakening the deployment gate.
- Diagnostic run `36bc49a` identified the exact state: `Wimbledon`, field=133,
  completed=True, draw_state=final, wiki_slots=0. The completed path deliberately stopped
  applying the cached authoritative Wikipedia draw, reverting to a noisy results union.
  Final fix retains the Wikipedia field after completion while still running the completed
  (rating-seeded retrospective) simulation mode.
- **Production proof:** final commit `ab0bc18`; refresh run 29170578353 passed WTA export,
  pre-deploy integrity gate, data-health check, static build, artifact upload, and Pages deploy.
  Live cache-busted `data/wta/tournaments.json` reports Wimbledon completed with drawSize=128,
  aliveCount=1, champion Linda Noskova; homepage Last-Modified is 2026-07-11 22:35:38 UTC.

---

# Task: Hidden /health status page (2026-07-10)

Plan: C:\Users\varma\.claude\plans\do-we-have-something-refactored-music.md
Goal: a professional status page at /health (unlinked, URL-only) rendering every
source/check verdict from structured health.json data — one source of truth in health.py,
no client-side threshold logic. NOTE: built on ea1e678 (fresh-overlay alarm shadowed
while stats overlay current) — the shadow state renders as amber "covered", not red.

## Checklist
- [x] config.py: WEB_DATA_DIR moves here from pipeline.py (pipeline imports it)
- [x] health.py: source_checks(tour, h, now) structured rows (incl. shadow note);
      problems() derives from it; main() adds checks + generatedAt + output
      forecast_max_as_of; mirrors health.json to WEB_DATA_DIR after write
- [x] refresh.yml: move "Data health check" (write step) before the site build so the
      deploy ships a current health.json; "Report data health" stays last
- [x] web: useRootData in lib/tour.tsx; PAGE_META health entry; app/health/layout.tsx
      (noindex); app/health/page.tsx (banner, per-tour check grids, output integrity,
      forecast log, drift, build stamps, GitHub-runs strip, outbound links); NO nav link
- [x] tests: test_health.py source_checks structure + problems() consistency + report
      fields + web mirror; web/tests/health.test.ts pure helpers
- [x] Verify: pytest+ruff; local sentinel run mirrors health.json; npm test/lint/tsc;
      Playwright /health on :3001 (both tours, shadowed amber fresh row, screenshot);
      no internal link to /health; CI green -> master -> deployed page fresh

## Review (2026-07-10)
- **Shipped**: /health — an unlisted (URL-only, noindex/nofollow, absent from Nav)
  operations page rendering the sentinel's verdicts verbatim: per-tour source-check
  grids (value vs limit + ok/covered/fail), output-integrity state, forecast-log
  liveness, drift chips from track.json, build stamps, a last-30 pipeline-runs strip
  from the public GitHub API, and outbound links to Actions/issues. One source of
  truth: health.py's new `source_checks()` emits structured rows that problems() now
  DERIVES from (strings unchanged), so page and alerts can never drift; the shadowed
  fresh-overlay state (ea1e678) renders amber "covered". health.json now carries
  checks/generatedAt/forecast_max_as_of and is mirrored to web/public/data on every
  sentinel run; the CI write step moved pre-build so each deploy ships its own report.
- **Proof**: 261 pytest + ruff, 138 vitest (+11 new) + eslint + tsc green; `next build`
  exports /health with noindex; live sentinel run mirrored health.json (ATP fresh 19d
  amber-covered, all else green); Playwright screenshot of :3001/health shows both
  tours, gold covered row (#d9a854 computed), zero internal links to /health.
- **Deviations from plan**: rebased onto ea1e678 mid-task (concurrent session shipped
  the fresh-overlay shadow) — source_checks carries the shadow as an amber note row;
  test helper `row()` needed Partial<CheckRow> typing for tsc.

# Task: Close the input-freshness monitoring gaps (2026-07-10)

Plan: C:\Users\varma\.claude\plans\do-we-have-something-refactored-music.md
Goal: the freshness sentinel becomes hourly (spam-controlled), every silent input source
gets an age invariant, and the pipeline's own liveness is watched from outside it.
Input freshness stays ADVISORY — the pre-deploy --gate remains output-integrity-only.

## Checklist
- [x] config.py: HEALTH_MAX_FORECAST_AGE_DAYS=5 / HEALTH_MAX_CHARTING_AGE_DAYS=90 /
      HEALTH_MAX_FRESH_AGE_DAYS=14
- [x] health.py: charting_date_max()/fresh_date_max() IO seams; tour_health() new fields;
      problems() fresh-overlay (+Jan 1-14 grace) + charting checks; output_problems()
      forecast-log age (gate-ADVISORY marker); main() problems_changed flag
- [x] tests/test_health.py: _h() new defaults; fresh/charting/forecast-age/problems_changed
      cases; hermeticity patches for the 3 tests that hit the new IO seams
- [x] refresh.yml: sentinel + report on ALL modes; mode-aware issue dedup (quick+unchanged
      = quiet green); persist step continue-on-error + retry + trailing red step
- [x] watchdog.yml (new): daily refresh.yml-liveness check -> watchdog issue + red
- [x] web: Freshness.tsx staleness() helper (aging>=6h gold, stale>=26h red) + vitest cases
- [x] README (tennis_model): sentinel paragraph now says hourly
- [x] Verify: pytest + health/--gate live-fixture run + yaml parse + npm test/lint

## Review (2026-07-10)
- **Shipped**: input-freshness monitoring now covers every silent source and runs hourly.
  New sentinel invariants: fresh-overlay age (14d, off-season + Jan 1-14 grace), charting
  age (90d), forecast-log liveness (5d, gate-ADVISORY). The sentinel + data-health issue
  flow runs on quick runs too, dedup'd via health.json `problems_changed` (quick+unchanged
  = warn + stay green, so a standing failure alerts once, not 24x/day; recovery now closes
  the issue within the hour). Persist step hardened: continue-on-error + 4-attempt
  rebase-retry push + trailing step that reds the run after deploy/sentinel. New
  watchdog.yml guards refresh.yml's own liveness (no success in 26h -> watchdog issue +
  red). Web Freshness pill gains aging (>=6h gold) / stale (>=26h red + title) states.
- **Proof**: 260 pytest (+4 new) + ruff green; 127 vitest (+4 new) + eslint + tsc green;
  live-fixture sentinel run flagged the genuinely-stale local ATP fresh overlay (19d>14)
  and stayed quiet on WTA (13d) + charting (50d/47d<90); --gate exit 0 (freshness stays
  advisory); second sentinel run flipped problems_changed True->False; all workflow run
  blocks pass bash -n; Playwright screenshots confirmed gold/red/green pill states with
  computed colors matching --color-champ/--color-loss/--color-win.
- **Deviations from plan + two follow-on fixes shipped the same day**:
  (1) d67cb62 — the FIRST post-merge deploy was blocked by the pre-existing
  power-of-two real-draw gate check (shipped 7/8 during Wimbledon) tripping on Gstaad's
  standard ATP-250 28-draw (32-bracket, 4 byes). Fixed by sanctioning standard bye-draw
  sizes {24,28,48,56,96}; leak signatures (129/29/27) still block. Lesson added.
  (2) 422bd00 — the quick-run dedup design was flawed: `problems_changed` keys off the
  cache-carried prev health.json, but a red job never saves the cache, so every hourly
  run re-redded as "new" (the storm the dedup was meant to prevent). Re-keyed the
  quick-run red on "did this run OPEN the issue" (GitHub state, cache-immune); standing
  failures comment-on-change + exit 0. Lesson added.
- **Live proof in CI**: onset run created data-health issue #3 + red; next quick run
  commented once (stale prev) + green; the one after was fully quiet + green. Watchdog:
  green path, forced-failure path (red + issue #4), recovery (closed #4) all exercised
  via workflow_dispatch. And the new fresh-overlay invariant caught a REAL freeze on
  day one: TennisCourtLog's ATP overlay has published nothing since 2026-06-21 (19d,
  through Wimbledon) — previously invisible because ESPN kept merged result-age fresh.

---

# Task: /method full methodology, driven by exported method.json (2026-07-10)

Plan: C:\Users\varma\.claude\plans\yes-plan-it-out-hashed-starfish.md
Goal: add a "Full methodology" block to /method (exact Elo equations, per-tour tuned
constants, point model, combiner+calibration, adoption protocol) with ZERO hardcoded
tuned constants — a new pipeline-exported per-tour method.json carries the effective
production parameters (from the *_params_for accessors); prose in TSX, numbers from JSON.
Branch: method-page-detail. Daily-log dirty files (forecast_log, kalshi_ledger) belong to
the scheduled actors — never commit them here.

## Checklist
- [x] 1. config.py: hoist TUNE_YEARS/VAL_START; eval/tune.py + eval/ab_data.py +
      eval/compare.py import from config
- [x] 2. train.py: XGB_DEFAULTS + EARLY_STOPPING_ROUNDS hoists (zero behavior change),
      effective_xgb_params(tour)
- [x] 3. export.py: _camel, build_method(tour) (config-pure), _write line in export_all
- [x] 4. test_export.py: matches-accessors / shape+strict-JSON / atp-xgb-defaults tests
- [x] 5. health.py: "method" required stem + _check_method (sanity ranges,
      featureCount cross-check vs meta)
- [x] 6. test_health.py: _healthy_data() gains method key; missing-blocks /
      feature-count-drift / out-of-range tests
- [x] 7. generate method.json locally for both tours + mirror to web/public/data
- [x] 8. web/lib/method.ts: MethodDoc type, fmt, kAt (+ web/tests/method.test.ts)
- [x] 9. web/app/method/page.tsx: six detailed sections, Formula component,
      collapsible 42-feature list, explicit empty state
- [x] Verify: pytest + ruff; health --gate; npm test + lint + build; browser visual
      pass on :3001 (tour toggle flips constants; empty state on missing JSON)

## Review (2026-07-10)
- **Shipped**: /method now carries a six-section "Full methodology" block below the
  overview — exact Elo equations (expected score, update rule, dynamic-K curves with a
  K-at-n table, tier multipliers), surface blend + cross-surface transfer, margin of
  victory, the serve/return Markov model, the XGBoost+Platt combiner (hyperparameter
  table + collapsible 42-feature list), and the adoption protocol with leakage
  guarantees + links to the tuning logs/ledger. Every number renders from a new
  pipeline-exported `method.json` (per tour, written by `export.build_method` — pure
  config via the `*_params_for` accessors, so full AND quick paths always publish
  current production intent). Zero hardcoded tuned constants in page copy — the exact
  failure the 2026-07-09 lessons entry recorded is now structurally impossible for the
  detail sections. `method.json` is a REQUIRED health-gate stem with sanity +
  featureCount-vs-meta drift checks.
- **Proof**: 262 pytest (+6) + ruff green; `health --gate` green with the new stem;
  130 vitest (+7) + lint 0 errors + typed static build green; 20 browser checks on
  :3001 via a playwright-core script (ATP constants 145/0.63/0.27/1.28, WTA
  320/0.62/0.72/no-Bo5/xgb-override table, 42 chips, float noise cleaned, explicit
  empty state with method.json renamed away, overview intact, no orphaned sections).
  Screenshots in web/.verify/shots/.
- **Deviations from plan**: (1) the Plan agent's "force-add the mirrored JSON" step was
  dropped — `git ls-files web/public/data` proved NOTHING under it is tracked; CI
  regenerates all JSON pre-build, local dev regenerates via the one-liner. (2) Next
  16/Turbopack drops SOME same-line spaces after JSX interpolations (rendered
  "ATPtour", "400days", "0.27of the" — while identical patterns elsewhere survived);
  fixed with explicit {" "} after every expression/element followed by prose and a
  rendered-DOM glue scan; recorded in lessons.md.

---

# Task: Forecast drift monitor — event-driven "re-tune recommended" signal (2026-07-10)

Plan: C:\Users\varma\.claude\plans\one-refinement-i-d-suggest-prancy-hellman.md
Goal: semiannual re-tune cadence becomes a ceiling, not a bet — watch the live forecast log
daily and raise an ADVISORY health signal (daily data-health issue) when the model scores
measurably worse than its own stated confidence. Composition-safe statistic: paired per-match
d = realized logloss − forecast entropy (d > 0 = overconfident/decayed), trailing 90d window
anchored to newest graded date, filtered to current model_version.

## Checklist
- [x] config.py: DRIFT_WINDOW_DAYS / DRIFT_MIN_N / DRIFT_TRIGGER_K / DRIFT_MIN_EXCESS
      (+ "bump __version__ when re-tuning" comment)
- [x] eval/track.py: pure _drift_block(graded, baseline, current_version) → status
      ok|drift|insufficient + d/se/t + baseline (accuracy.json combiner, context-only)
      + worstBin; wired into grade()'s matchForecasts as "drift" (NaN-free by construction)
- [x] data/health.py: "forecast drift" _GATE_ADVISORY marker + advisory check on
      track.json drift.status == "drift" ("re-tune recommended" problem string)
- [x] tests/test_track.py: calibrated-ok, overconfident-flags (+ one-sided: lucky window
      never fires), below-min-n, window+version filter, grade() end-to-end JSON-safe
- [x] tests/test_health.py: healthy fixture gets drift block; drift flagged advisory
      (never gate-blocking); insufficient/ok/missing-key silent
- [x] Verify: pytest 256 + ruff green; health + --gate exit 0 both before regeneration
      (missing drift key → silent) and after; quick refresh regenerated track.json

## Review (2026-07-10)
- **Shipped**: the forecast drift monitor. `eval/track.py::_drift_block` computes the
  composition-safe calibration-drift statistic (paired per-match d = realized logloss −
  forecast entropy; d > 0 = overconfident/decayed; one-sided) over a trailing 90d window
  anchored to the newest graded result date, filtered to the current `__version__`, and
  ships it in `track.json.matchForecasts.drift` (auto-mirrored to the web). Trigger:
  n ≥ 150 AND d > 2.5·SE AND d > 0.02 nats → status "drift", which `data/health.py`
  surfaces as an ADVISORY "re-tune recommended" problem — lands in the daily data-health
  GitHub issue, never blocks a deploy. accuracy.json combiner logloss rides along as
  context (`baseline.dLogloss`), never as the trigger (composition-confounded).
- **Proof**: 256 pytest (+6 new) + ruff green. Real-data run: gate exit 0 pre- and
  post-regeneration; quick refresh produced ATP drift `"insufficient"` (n=114 < 150,
  arms in ~1 week) and WTA `"ok"` (n=181, d=+0.0076±0.0282, t=0.27 — calibrated), both
  parsed NaN-free by the gate's strict reader.
- **Deviation from plan**: none. WTA arming immediately (181 graded ≥ 150) was a
  pleasant surprise vs the plan's ATP-only n=113 estimate.
- **Ritual (user-facing)**: the monitor resets on re-tune only if `__version__` is
  bumped — encoded in the config comment; make the bump part of the semiannual re-tune.

---

# Task: Site IA reorganization + attribute Explorer (2026-07-09)

Plan: C:\Users\varma\.claude\plans\lets-talk-from-first-tingly-pizza.md
Goal: first-principles IA cleanup (Matches group, /upcoming→/results rename, label/title
consistency), tour+player state in the URL (shareable deep links + cross-links everywhere),
a new /explorer tab (scatter of any 2 attributes + sortable stat table over one shared
attribute registry), and export enrichment (heightCm, per-surface serve/return, form90,
winRate10) so the explorer has real axes.

## Checklist
- [x] A: Python export enrichment (export.py ctx param + new fields, H2HState.last_results,
      health gate invariants, test_export + test_health cases, regenerated data mirror)
      — 250 pytest + ruff green; quick refresh ran both tours; fields verified in
      web/public/data (Sinner 191cm / winRate10 0.9; WTA heights null 82/200); gate green
- [x] C1-C2: web/lib/url.ts pure helpers + tour-in-URL sync (TourUrlBridge) + url tests
- [x] B: route rename /upcoming -> /results + redirect stub + nav restructure (Matches group,
      Explorer entry) + seo.ts + label/title consistency pass
- [x] D1: extract shared components/ScatterChart.tsx from strength page (pixel-identical)
- [x] D2-D3: EXPLORER_AXES registry + /explorer page (Scatter | Table views, URL state) + tests
- [x] C3-C4: player deep links (/player?p, /style?a&b, /predict?a&b) + cross-links
      (rankings, trends, CallCard, dots, H2H)
- [x] Verify: python pytest + health gate; web test/lint/build; Playwright E2E on :3001

## Review (2026-07-09)
- **Shipped**: the full IA reorg — nav is now Overview | Matches (Schedule, Results) |
  Players (…, Explorer) | Forecasts | Model; /upcoming renamed /results with a client
  redirect (query forwarded); nav labels == page titles (old nicknames moved to eyebrows).
  Tour state lives in the URL (?tour=wta, atp elided; URL > localStorage > default) and
  players are deep-linkable everywhere: /player?p=, /style?a=&b=, /predict?a=&b= (names,
  not indices), with cross-links from rankings rows, trends rows, CallCards (home/
  schedule/results/track), strength+explorer dots, and profile H2H/recent opponents.
  New /explorer: Scatter (any 2 of 20 registry axes, presets, group-mean cross) + Table
  (all axes as sortable columns, nulls last, sticky name column) — both URL-addressable
  (?view/&x/&y/&sort/&dir). Python export now ships heightCm, per-surface serve/return,
  form90, winRate10 (explicit 90d/last-10 windows — NOT the tours' tuned windows).
- **E2E-caught bugs (fixed during verification)**: (1) TourUrlBridge reverted toggles —
  it applied the stale URL param before router.replace landed; fixed by only applying
  URL→state when the search string actually changed (ref-tracked navigation detection).
  (2) The /upcoming redirect's router.replace lost the race against the tour bridge's
  own replace; fixed with a hard window.location.replace (base-path aware).
- **Proof**: Python 250 tests + ruff + health gate green; quick refresh regenerated both
  tours (Sinner 191cm/winRate10 0.9; WTA heights null 82/200 as expected). Web 118 tests
  + lint 0 errors + build 19 routes; scripts/verify.mjs 10/10 routes, 0 console errors;
  Playwright walked every flow above on :3001 (toggle URL round-trip incl. scroll
  preservation, deep-link precedence, diacritic names, redirect with ?tour=wta,
  15-chip mobile strip, table sort desc/asc with URL restore).
- **Deviation from plan**: none of substance; the two race fixes above were within-plan
  contingencies (the plan flagged replace-mechanism fallbacks).

---

# Task: Autonomous WTA-first research round (2026-07-09)

Base: `605ff12b6f588b0b458dea7b37f735b217001000`; branch: `research/2026-07-09-codex`.
Measured start: 2026-07-09 18:44 EDT. Budget: default 8h. Scope: open raw-signal
ideas only; never modify `eval/` or push.

## Checklist

- [x] Read PROGRAM, backlog, ledger, lessons, architecture docs, and config; incumbent pytest green (226).
- [x] Cut isolated research branch and perform round-zero read-only idea fan-out.
- [x] R3-001: 3-year recent H2H feature rejected: WTA passed narrowly, ATP failed both windows.
- [x] Triage retirement-depth and rate-channel ideas; declare the next parity-feasible experiment.
- [x] Run only the required Tier 1/Tier 2 gates; retain or revert each arm honestly.
- [ ] Run final test + ruff verification; no rebuild is needed because no adoption survived.
- [x] Append the narrative result and final ledger diff; leave the branch green.

## Review

- No adoption. R3 stopped under PROGRAM condition 3: the backlog is exhausted and two
  self-generated candidates closed consecutively (MCP coverage decline, ordinal-rank arbiter reject).
  See `tasks/tuning-results-2026-07-09-codex.md`.

---

# Task: Daily output health-check + actionable GitHub-issue alert (2026-07-08)

Plan: C:\Users\varma\.claude\plans\can-we-run-a-greedy-pudding.md
Goal: the daily build already checks source freshness (`data/health.py`); extend it to
also validate the produced JSON the web reads (counts/tournaments/matches/predictions),
and on any problem auto-file/comment/close a single `data-health` GitHub issue with the
exact problems + a ready-to-paste fix prompt, so it can be picked up in a new session.

## Checklist
- [x] config.py: `HEALTH_MIN_MATCHES`, `HEALTH_MAX_BUILD_AGE_DAYS`, `HEALTH_MAX_LIVERANK_NULL_FRAC`
- [x] data/health.py: `read_outputs()` IO seam + pure `output_problems()` (missing/corrupt files,
      feature-schema drift, match floor+monotonic drop, activePlayers, build freshness, eloRank
      contiguity, placeholder-name leak, matrix antisymmetry, tournament status/drawStatus/
      aliveCount≤drawSize, real-draw power-of-two, projection prob-bounds+monotonicity, upcoming
      identical-players, fixtures upset-flag, forecast-log monotonicity, track graded+pending==logged);
      `format_issue_body()` + `--issue-body`; aggregated into `main()`/health.json; `_offseason` shared
- [x] tests/test_health.py: 17 new synthetic cases (healthy-clean, each corruption fires its flag,
      season-gated emptiness/liveRank, read_outputs missing/corrupt, issue-body render) — 24/24 pass
- [x] .github/workflows/refresh.yml: `issues: write`; health runs without `--strict`; new
      "Report data health" step opens/comments/closes the `data-health` issue and reds the run
- [x] tennis_model/README.md: documented the two-layer sentinel + the data-health issue flow

## Review
- **Outcome:** ATP output validates clean; WTA (locally stale, built Jul 6 pre-`drawStatus`) is
  correctly flagged (missing drawStatus + newest-match age) — proving both the happy path and
  detection. `--issue-body` renders the actionable Markdown. ruff clean; test_health 24/24.
- **Deviation 1 (important):** the planned unconditional "drawSize is a power of two" hard-fail was
  WRONG — `drawSize = len(field_pool)`, so completed events are legitimately non-power-of-two
  (34/37/41/43 = main draw + qualifiers). Gated it to `drawStatus == "real"` (a true bracket),
  which is where a leaked TBD (128→129) actually shows. Added a "missing drawStatus" schema check.
- **Deviation 2:** `FEATURES` import lifted to module top (ruff I001; no import cycle); issue body
  capped at 50 problems.
- **Scope note:** runs on the daily FULL run only (matches the existing health step); extending to
  the hourly quick refresh is a deliberate future option. Only takes effect on `master` (daily cron).
- **Unrelated, pre-existing:** this branch's WIP (the MONTH_SURFACE / `enrich_upcoming(tour)` surface
  refactor below) currently breaks `test_upcoming.py`/`test_track.py`/`test_tournament_*` at import
  time — confirmed independent of this task (fails identically with my 3 files stashed). test.yml is
  red until that refactor lands.

---

# Task: Fix clay tournaments mislabeled as GRASS — Wikipedia surface backfill (2026-07-08)

Plan: C:\Users\varma\.claude\plans\indexed-leaping-petal.md
Bug: /schedule showed clay events (Grand Est Open 88, Nordea Open) as GRASS. Surface for
live/new events resolved as archive-name-match -> July="Grass" month fallback; both miss the
archive (Nordea archived under city "Bastad"; Grand Est brand-new). Root-cause fix: Wikipedia
main-article `surface` infobox (both = Clay) as a new tier between archive and month, corrected
at the SOURCE (results.clean) so ratings + every board agree; no hardcoded surface table.

## Checklist
- [x] config.py: MONTH_SURFACE (moved from results._MONTH_SURFACE, next to SURFACE_MAP)
- [x] data/surface.py (new, offline leaf): wiki_surface / wiki_surface_map / resolve_surface
      (archive -> wiki cache -> MONTH_SURFACE); imports only config, never touches the network
- [x] data/draws_wiki.py: _parse_surface (pure regex, SURFACE_MAP-canonical) + event_surface
      (main-article resolve; year + parseable-surface + body-anchor bounds — no infobox-NAME gate,
      which wrongly rejected slams) + surface pass in download_wiki_draws -> wiki_surface.json
      (separate cache, outside draw gate, never caches a miss)
- [x] data/results.py: clean wiki-cache fill between _backfill_event_attrs and month; use
      config.MONTH_SURFACE; drop _MONTH_SURFACE literal
- [x] model/upcoming.py: _surface_best_of + enrich_upcoming take tour, use resolve_surface;
      thread tour from export.build_upcoming + eval/track.log_forecasts
- [x] sim/tournaments.py: project_upcoming uses resolve_surface (left project_tournament —
      it inherits the corrected surface_b)
- [x] tests/test_surface.py (offline): _parse_surface fixtures, wiki_surface(_map) tmp cache,
      resolve_surface priority, loader "Nordea Open"+cache -> surface_b == Clay; test_upcoming
      threaded tour (removed a leaky module-level stub)
- [x] Verify: pytest 193 + ruff clean; live event_surface all correct (Nordea/Grand Est/Palermo/
      Hamburg=Clay, Wimbledon/Eastbourne=Grass); real _download_wiki_surfaces populated
      wiki_surface.json (Grand Est + Nordea -> Clay); loader unit test (cache -> Clay, no cache -> month)

## Review (2026-07-08)
- **Shipped:** Wikipedia main-article `surface` infobox as the authoritative surface source for
  live/new events, cached per tour (`live/<tour>/wiki_surface.json`, written by the existing
  `download_wiki_draws` sweep) and read by one offline helper `data.surface.resolve_surface`
  (archive -> wiki cache -> month). Wired into all three surface-resolution points: the loader
  `results.clean` (fixes `surface_b` at the SOURCE -> ratings + live `tournaments.json` +
  `bySurface` scoring), and the two pre-start paths `upcoming._surface_best_of` (schedule board +
  forecast log) and `tournaments.project_upcoming`. No hardcoded surface table.
- **Root-cause depth:** fixing only the prediction points would have regressed to Grass mid-event
  (project_tournament reads surface_b; live ESPN rows carry month-fallback Grass with no
  provenance that the archive tier would trust). Correcting surface_b in `clean` is the linchpin.
- **Deviation from plan:** dropped the planned "infobox-tennis" name gate in `event_surface` — it
  false-rejected Grand Slams (their main article uses a differently-named infobox) even though the
  `surface=` field parses fine. A parseable `surface=[[…court]]` field IS the tennis-tournament
  signal; kept year-in-title + body-anchor as the wrong-event bounds. Caught by the live smoke
  (Wimbledon returned None -> now Grass).
- **Proof:** pytest 193 + ruff clean. Live `event_surface`: Nordea/Grand Est/Palermo/Hamburg = Clay,
  Wimbledon/Eastbourne = Grass (all correct). Real `_download_wiki_surfaces('wta')` cached the two
  reported events as Clay. `test_surface.py` pins the parser, the cache reader's graceful
  degradation, the resolve priority, and the end-to-end loader (July "Nordea Open" -> Clay with the
  cache, Grass month-fallback without it). Web layer already renders the stored surface verbatim.
- **Not committed** (user hasn't asked); `data/raw/` (incl. wiki_surface.json) is gitignored and
  regenerated by the daily refresh. Change is code + tests only; scoped away from the concurrent
  session's health/tournament_level work in the same tree.

---

# Task: "Up next" upcoming-matches grid on the Overview page (2026-07-08)

Plan: C:\Users\varma\.claude\plans\foamy-hugging-castle.md
Goal: surface the model's latest match predictions on the landing page ("so the latest
models are always available"). Frontend-only — reuses the already-wired upcoming.json +
CallCard(tone="projection"). User-chosen design: a 2-col card grid BELOW the title race.

## Checklist
- [x] web/lib/upcoming.ts: pure `upcomingCard(m)` helper (fav on top → CallCard props);
      dedups the aFav/fav/dog block previously inlined in schedule/page.tsx
- [x] web/app/schedule/page.tsx: consume the helper (behaviour identical)
- [x] web/app/page.tsx: local `UpNext` component (next 6, soonest-first; header + "full
      schedule →" link; self-hides when empty); mounted below SlamHero (slam view) and
      above the tournaments grid (no-slam view); aria-label for parity with LiveTicker
- [x] web/tests/upcoming.test.ts: upcomingCard cases (A-fav, B-fav, complement, meta)
- [x] Verify: npm test (90) + lint (0 err) + build (17 routes) green; :3000 Playwright
      render (grid below title race, fav accent, %s sum to 100, tour swaps, empty-hides,
      /schedule unchanged)

## Review (2026-07-08)
- **Shipped**: an "Up next" grid on the Overview page — next 6 scheduled matches with the
  model's win prob, favourite in accent, "full schedule →" to /schedule. Sits BELOW the
  title race in the Slam view and above the tournaments grid otherwise; self-hides when
  `upcoming.json` is empty (the explicit empty-state stays on /schedule). New local
  `UpNext` in web/app/page.tsx, mounted in both layout branches.
- **Reuse / no drift**: the favourite/underdog → CallCard mapping is now a single pure
  helper `upcomingCard` in web/lib/upcoming.ts, consumed by BOTH the home grid and the
  /schedule board (refactored to it — behaviour identical). Reuses existing `CallCard
  tone="projection"`, `useData`, `Reveal`. Frontend-only — no pipeline/data change.
- **"Latest models always available"**: `upcoming.json` is already regenerated on every
  full and `--quick` refresh and auto-mirrored, so the landing page always shows the
  current model's calls with zero extra plumbing.
- **Proof**: web 90 tests (4 new `upcomingCard`, one tied to real pA=0.6518), lint 0
  errors, build 17 routes. Playwright verified on :3000 (the concurrent session's dev
  server serves the shared tree; a 2nd Next dev on :3001 is refused): WTA + ATP each
  render 6 cards below the title race, every card cross-checked vs upcoming.json (names +
  complementary %s + round; e.g. WTA Bencic 69% / Kalinskaya 31%); empty upcoming.json →
  section absent; /schedule still 16 panels. Screenshots in scratchpad.
- **Coexists with the concurrent Wikipedia-draw session**: both sessions edited
  web/app/page.tsx (their drawStatus/DrawCaveat + my UpNext); combined build/lint/tests
  green.
- **Note**: local upcoming.json is a round behind the local title race (R64 vs R16 stage)
  — a stale-snapshot artifact; production regenerates both together each refresh.

---

# Task: Download the full tournament draw at release (Wikipedia) + honest draw labeling (2026-07-08)

Plan: C:\Users\varma\.claude\plans\do-you-download-the-curried-pancake.md
Goal: ESPN can't supply a full draw at release (fills the bracket by daily order-of-play, so
`live_draw` silently Elo-seeds a hypothetical bracket). Add Wikipedia (MediaWiki API) as the
authoritative draw source — the complete ORDERED bracket the day it's released, down to ATP-250 —
so tournaments project on the REAL draw from release onward (incl. pre-start). ESPN stays for live
scores/eliminations. Add a `drawStatus` (real/partial/seeded/final) label as an honest safety net.
Closes the 2026-07-08 "known limit" below.

## Checklist
- [x] config.py: WIKI_API, WIKI_UA, WIKI_TITLE_OVERRIDES; requirements.txt pin mwparserfromhell==0.7.2
- [x] data/live.py: parse_event_meta (event → start/end/espnId) for pre-start discovery
- [x] data/draws_wiki.py: discover (fetch_events) → resolve title (search API, year+anchor+gender
      gated) → parse `-Compact-` sections in doc order (geometry-aware byes via RD2) → ordered
      slots + seeds + bestOf → wiki_draws.json; idempotent (keep captured draws) + best-effort
- [x] sim/draws.py: advance_slots (collapse ORDERED bracket by eliminated, keeping adjacency —
      chosen over the planned `current_matchups`+live_draw round-trip, which would strength-seed
      downstream halves and lose the real draw); _seat_frontier + draw_status; refactor live_draw
      (bit-identical, existing 5 tests green)
- [x] sim/tournaments.py: _load_wiki_draws; wiki precedence in project_tournament (+drawStatus);
      _simulate_projection helper; project_upcoming + pre-start discovery (display-name dedup +
      already-ended skip) in build_tournaments
- [x] model/upcoming.py: union wiki R1 rows into load_upcoming (schedule board + forecast log)
- [x] pipeline.py + data/download.py: wire download_wiki_draws (quick + full + --kind wiki/live)
- [x] web/lib/ui.ts: drawCaveat; web/app/page.tsx: upcoming status + drawStatus type + DrawCaveat UI
- [x] tests: test_draws_wiki.py, test_tournament_status.py, extend test_sim_draw.py, web ui.test.ts
- [x] Verify: pytest 166 + ruff clean; web 90 tests + lint 0-err + build 17 routes; live smoke
      (draws_wiki → Wimbledon 128 real; --quick → tournaments.json drawStatus real); :3001 Playwright
      (seeded caveat / partial caveat / upcoming badge / real = no caveat, 6/6, 0 console errors)

## Review (2026-07-08)
- **Shipped**: Wikipedia (MediaWiki API) as the authoritative draw source. `data/draws_wiki.py`
  discovers current/upcoming events from the ESPN sweep, resolves each to its draw article
  (year + distinctive-anchor + exact-tour gated — verified this rejects last-year and wrong-tour
  hits, e.g. Winston-Salem→AO and ATP Eastbourne→Women's), and parses the ORDERED bracket by
  stitching the `-Compact-` section templates in document order (byes read from RD2 geometry,
  disambiguators stripped, qualifiers kept distinct). `sim/tournaments.project_tournament` now
  prefers the wiki ordered draw (`advance_slots` collapses it by ESPN eliminations, keeping real
  adjacency → exact every round, closing the "downstream pairings strength-seeded" known limit
  below), and `build_tournaments` surfaces not-yet-started events as `status:"upcoming"`. A
  `drawStatus` (real/partial/seeded/final) rides through to the web, where `DrawCaveat` flags a
  seeded/partial board so a projected bracket never masquerades as the official one.
- **Deviation from plan**: used `advance_slots` (order-preserving collapse) for the wiki path
  instead of `current_matchups`→`live_draw`; the latter re-seats by strength and would have
  re-introduced the very downstream-half error the wiki draw exists to fix. Honest labeling
  (`draw_status`/`_seat_frontier`) still ships for the ESPN-only fallback.
- **Proof**: Python 166 passed + ruff clean; web 90 passed + lint 0 errors + build 17 routes.
  Live: `draws_wiki` parsed 2026 Wimbledon (128, bo5, ordered) + Eastbourne; `--quick` produced
  `tournaments.json` with Wimbledon `status:live drawStatus:real size:128`, no phantom duplicate.
  Playwright on :3001 (server was the concurrent session's :3000): seeded Slam → "PROJECTED DRAW"
  banner, partial → "DRAW INCOMPLETE", upcoming → "DRAW RELEASED" badge + pre-event odds, real →
  unchanged (no caveat); 6/6 assertions, 0 console errors (screenshots in scratchpad).
- **Not done (by design)**: Challenger/ITF draws (spotty on Wikipedia — would need a paid API);
  the seeded-Slam SlamHero shows the banner but keeps the full table (no collapse-to-Champion —
  the banner already makes the projection honest); WTA wiki cache filled on the next full/quick
  refresh (smoke ran ATP only). New lesson recorded in tasks/lessons.md.

---

# Task: "Upcoming matches" predictions page — ATP + WTA (2026-07-08)

Plan: C:\Users\varma\.claude\plans\radiant-sniffing-moonbeam.md
Goal: a /schedule page listing the next set of scheduled matches (from upcoming.csv) with the
model's current win prob, both tours. Future-proof: ONE shared "scheduled matchup → prediction"
primitive reused by the forecast log AND the web export (no duplicated resolve/surface/win_prob).

## Checklist
- [x] model/upcoming.py: load_upcoming, MONTH_SURFACE + event_attrs (relocated from track),
      enrich_upcoming(predictor, df, up_df) -> neutral rows {event,date,round,surface,best_of,
      playerA,playerB,pA}; resolve names, infer surface/bo, win_prob; skip unknown/same
- [x] eval/track.py: consume enrich_upcoming + load_upcoming; drop local copies; behaviour
      preserved (test_track.py green)
- [x] model/export.py: build_upcoming (enrich + _display_name + sort) → write upcoming.json in
      export_all; sim/tournaments._load_upcoming re-points at load_upcoming
- [x] tests/test_upcoming.py; pytest (153) + ruff green
- [x] web bits.tsx: CallCard tone?: "result"|"projection" (favourite in accent, no verdict)
- [x] web/lib/upcoming.ts (type + groupByEvent); app/schedule/{page,layout}.tsx; seo.ts entry;
      Nav.tsx Forecasts item
- [x] web/tests/upcoming.test.ts; npm test (84) + lint (0 err) + build (17 routes) green
- [x] Generated real upcoming.json (atp+wta) from saved predictor; rendered /schedule both tours;
      review below

## Review (2026-07-08)
- **Shipped**: new `/schedule` page ("On Deck", nav "Upcoming matches" in Forecasts) listing
  every scheduled/in-progress match grouped by tournament with the model's current win prob,
  both tours. Backend: one shared primitive `model/upcoming.py` (`load_upcoming`, `event_attrs`,
  `MONTH_SURFACE` reused from `data.results`, `enrich_upcoming`) that `eval/track.py`,
  `model/export.build_upcoming`, and `sim/tournaments._load_upcoming` all consume — the
  name-resolution/surface-inference/`win_prob` logic now lives in exactly one place (the
  future-proofing ask). `CallCard` gained `tone="projection"` (favourite in accent, no
  winner-green/verdict) — merged with the concurrent session's sum-to-100 label change.
- **Behaviour preserved**: `test_track.py` green after the refactor (forecast log unchanged);
  the just-landed live-draw path still gets its matchups (sim `_load_upcoming` → 17 Wimbledon).
- **Proof**: Python 153 passed + ruff clean; web 84 passed + lint 0 errors + build 17 routes.
  Real `upcoming.json` generated from the saved predictor (16 ATP + 16 WTA, Wimbledon R64).
  Cross-check: JSON `pA` == direct `win_prob` with inferred Grass/Bo5, exact. Rendered both
  tours on :3001 (preview_screenshot times out here per the saved note, so verified via DOM
  snapshot + `preview_eval`): favourite on top, labels sum to 100, 16 accent bars / 16 muted /
  **0 green** (projection tone correct), tour toggle re-fetches WTA (Bencic 69% > Kalinskaya 31%).
- **No CI change**: `upcoming.json` is overwrite-only output (like fixtures.json) regenerated by
  `export_all` on full AND `--quick` runs, auto-mirrored by `pipeline._mirror` — not append-only
  state, so no refresh.yml persistence needed. Prod fills it on the next refresh.
- **Extensible / not done (by design)**: flat row schema leaves room for per-player rank/seed
  later; `bestOf` already in the JSON though the card doesn't show it yet.

---

# Task: Redesign "recent calls" match cards — show both projections (2026-07-08)

Plan: C:\Users\varma\.claude\plans\these-also-do-not-harmonic-pudding.md
User: /track "recent calls" cards (and the /upcoming Feed twin) showed one ambiguous
number — P(first-listed player) — decoupled from the green (winner) and the ✓/✗ (model's
pick). Chosen fix (Option A, against a live mockup): stacked probability bars showing BOTH
players' win %, winner in green, verdict falls out of bar length. Pure frontend (data
already carries p and 1−p); no pipeline/retrain.

## Checklist
- [x] bits.tsx: shared `CallCard` (two players, per-side prob bar, winner green + dot,
      footer note + verdict; `glow` opt-in for the Feed's hover) — reuses `.bartrack`,
      `pct`, `surfaceColor`, `SPRING_SOFT`
- [x] track/page.tsx: map `mf.recent` → CallCard (note "model favoured X", verdict
      called it/missed); fix the escaped-brace footnote bug
- [x] upcoming/page.tsx: map `Fixture` → CallCard (winner on top, score as note, upset
      verdict); drop now-unused `pct`/`surfaceColor` imports
- [x] Verify: web lint + build + vitest green; Playwright screenshots of /track + /upcoming
      (atp + wta) show both bars/winner-green/verdict; cross-check 2–3 vs track.json

## Review (2026-07-08)
- **Shipped**: one shared `CallCard` in `web/components/bits.tsx` rendering two players,
  each with their own win-probability bar (winner green + dot + bright text, loser muted
  grey), a footer note (favoured player / match score) and a verdict. Wired into both
  `track/page.tsx` ("recent calls") and `upcoming/page.tsx` (The Feed) — the two can no
  longer drift. Fixed the escaped-brace footnote bug on /track (`P({first player} wins)`).
- **Pure frontend**: both projections derive in-component from the single stored `p`
  (playerB = 1 − p) / `modelProb`; no pipeline, data, or retrain changes.
- **Proof**: `npm run lint` 0 errors; `npm test` 81/81; `npm run build` clean (all 16
  routes). Playwright (chrome, :3000, both tours) + DOM extraction cross-checked vs
  track.json/fixtures.json: the old contradiction now reads right — Majchrzak 72% /
  **Svajda 29% (green, winner)** · "model favoured Majchrzak · missed ✗"; Feed shows the
  winner on top with the score preserved and "upset ✗" on underdog wins (Bergs 48%).
  Screenshots in scratchpad `/shots/{track,upcoming}_{atp,wta}.png`.
- **Labels sum to 100**: `CallCard` rounds the top/authoritative side and shows the other
  as its complement, so the two %s always total 100 even on exact-half splits (bar widths
  still use the true probabilities). Verified: the old 72%/29% Majchrzak–Svajda card now
  reads 72%/28%.
- **Note**: a concurrent session's /schedule task plans to add a `tone` prop to `CallCard`
  to reuse it for pre-match projections — the component is already structured for that.

---

# Task: Live forecast uses the ACTUAL draw, not Elo re-seeding (2026-07-08)

Bug (clear repro): live scorecard showed Sinner 97% / Djokovic 55% to reach the F while
they actually play each other in the SF (must sum to 100%). Root cause: `project_field`
→ `standard_seed_draw` re-seeds survivors into a synthetic 1v4/2v3 bracket, ignoring the
real matchups that `data/live.parse_upcoming` already captures in `upcoming.csv`.
Scope chosen by user: FULL real-draw (respect current-round matchups at every stage;
seed only genuinely-unknown downstream pairings).

## Checklist
- [x] draws.py: `live_draw(alive, matchups, rank)` — seat survivors by real matchups
      (pairs=adjacent, already-advanced players=bye into next round); seed the unknown
      downstream + fall back to `standard_seed_draw` when no/partial matchup info
- [x] tournaments.py: `_load_upcoming(tour)`; thread resolved matchups through
      `build_tournaments` → `project_tournament`; live branch uses `live_draw`,
      completed branch keeps full-field seeding (pre-tournament title odds)
- [x] tests/test_sim_draw.py: real-pairing adjacency, fallback (no/partial matchups),
      and the money test — actual-opponent reach-F probs sum to ~100%
- [x] Verify: pytest (147 passed) + ruff green; before/after reach table printed
      (Sinner+Djokovic 152%→100%); completed path byte-identical to old project_field

## Review (2026-07-08)
- **Shipped**: `sim/draws.live_draw` (real-matchup bracket for live events),
  `sim/tournaments._load_upcoming` + matchup plumbing through
  `build_tournaments`/`project_tournament`, module-docstring rewrite, 5 new tests
  (`test_sim_draw.py`). Live events now honour the actual draw; completed events and
  the hypothetical `draws.json` are untouched (`old.equals(new) == True`).
- **Proof**: with the four Wimbledon survivors, OLD gave Sinner.F+Djokovic.F=152%
  (they play each other!); NEW gives 100% for both real SF pairs and shifts
  Zverev.F 45%→92% (he faces Fery, not Djokovic). Reach-F identity `P(a)+P(b)=1`
  for SF opponents holds to 1e-9 in the test.
- **Scope / known limit (full real-draw, as chosen)**: exact whenever the current
  round's matchups are fully posted (always true SF/F; usually true mid-Slam). A
  partial frontier (some of a round played, rest pending → non-2^k "units") falls
  back to rating seeding for that transient window — never wrong, just less precise,
  and no worse than before. Downstream pairings the feed can't yet know (which half
  two future winners land on) are still strength-seeded; unavoidable without draw
  positions (ESPN omits `match_num`).
- **Not touched (separate/pre-existing)**: the stale on-disk `fields.json` carries a
  leaked `TBD` (129-count) from before the `_PLACEHOLDER_NAMES` filter; current code
  already drops it, so the next refresh self-heals. `live_draw` handles a stray TBD
  safely anyway (unpaired → non-2^k → seed fallback).

---

# Task: Kalshi vs model — ledger + segmented scorecard (2026-07-07)

Plan: C:\Users\varma\.claude\plans\looks-like-we-have-lovely-puddle.md

## Checklist
- [x] config.py: KALSHI_LEDGER_DIR + kalshi_dir(tour) path helpers
- [x] data/kalshi.py: public API client (markets/candlesticks), snapshot cache,
      T-5/T-30 pre-match quotes, KALSHI_ALIASES; tests (parse + candles)
- [x] eval/kalshi_ledger.py: Kalshi→match join (asym −2..+21d window),
      p_model fill (forecast_log live > OOS backtest), per-tour CSV upsert with
      frozen-field policy; tests (orientation, idempotency, RET/WO, rematch)
- [x] One-time local backfill --backfill-since 2026-04-30; seed aliases from
      unmatched table; ≥95% matched acceptance
- [x] eval/kalshi_report.py: paired d±SE scorecard (segments: top-20, rank bands,
      favorite buckets, surface/tier/round/month, disagreement bands), calibration,
      QA/leak sentinel; report.md + kalshi.json; tests
- [x] tests/test_kalshi_purity.py: kalshi never imported by model code
- [x] pipeline.py hook (_kalshi after _track; report + re-mirror in main)
- [x] refresh.yml: widen persist step to data/kalshi_ledger; raw/kalshi in
      release snapshot DIRS
- [x] Verification: pytest (142 passed), double ledger run byte-identical (md5),
      5 rows hand-recomputed from the API (prices exact, orientation + settlement
      consistent), ruff clean; review below

## Review (2026-07-07)
- **Shipped**: data/kalshi.py (public-API client + snapshot cache),
  eval/kalshi_ledger.py (per-tour CSVs, 955 ATP + 975 WTA events), eval/
  kalshi_report.py (paired d±SE scorecard: report.md + kalshi.json), pipeline
  hook, refresh.yml persist/snapshot widening, 37 new tests incl. import-purity
  guard. Backfill spans 2026-04-30 → today; 973 scored matches.
- **Deviation from plan (price anchor)**: planned "T−5 before occurrence_datetime"
  was UNSOUND — the field mutates to ~determination time on settled markets, and
  the T-30 leak sentinel caught final in-play prices contaminating 160 rows (p95
  |Δ|=0.23). Re-anchored ALL scoring quotes to 08:00 UTC on the result row's date
  (provably pre-match; sentinel now 0 rows > 0.05). Comparison is therefore
  "our forecast vs Kalshi MORNING line", not closing line. lessons.md updated.
- **Deviation (join window)**: −2..+21 → −8..+21 (draw-time placeholder dates).
- **Match rates**: ATP 890/955 (13 unmatched, 32 cancelled=scalar fair-price
  settlements); WTA 542/975 — 314 quali + 65 slam-quali-as-R128 markets are
  structurally unmatchable (no WTA quali results source); rest self-heals.
- **Deviation (verification)**: full `pipeline --tour all --backtest` not run
  locally (hook exercised standalone end-to-end instead; soft-fail wrapped).
  First CI daily run is the live proof — check tomorrow's run + committed diff.
- **First scorecard** (n=973, morning line): pooled d_ll −0.011±0.007; ATP at
  parity (−0.001±0.010), WTA behind (−0.021±0.009); parity among top-10 pairs
  and 0.6–0.9 favorites; weakest: coin-flips (0.5–0.6), rank-11–20 pairs, grass/
  June, and big disagreements (model right 71/203 when |Δp|≥0.10).

## Web surfacing (2026-07-07, follow-up)
- New page web/app/scorecard/ ("Vs the Exchange", nav "Vs Kalshi" in the Model
  group) reading the mirrored kalshi.json. Signature viz: an SVG forest plot of
  paired d_ll ± 95% CI per segment (grouped: provenance, rank, favourite band,
  surface, tier, round, month, agreement), colored by significance
  (win-green ahead / loss-red behind / faint even). Headline verdict chip,
  StatCards, coverage table, morning-line caveat. Reused the site's dark Linear
  design system + bits (PageHead/StatCard/Reveal), NOT the artifact's own look.
- Verified: next build (page in static export), 81/81 vitest, tsc clean, page
  0 lint warnings, tour toggle swaps data (ATP parity / WTA behind), no NaN,
  no page overflow. kalshi.json rides the existing _mirror path in CI.

---

# Task: Autoresearch round R2 (2026-07-06 night, /research-round 8h)

Branch research/2026-07-06 (fast-forwarded to base cf241f8); ledger R2-*;
full write-up tasks/tuning-results-2026-07-06-autoresearch-r2.md.

## Experiments
- [x] Round-zero ideation fan-out (3 read-only scouts, 18 proposals → 8 backlog
      survivors, 9 discards with reasons)
- [x] R2-001 fp3 WTA widened-layoff sweep: **REJECT** (flag-off region flat;
      360 was not a ceiling artifact)
- [x] R2-002 eloSx overall−surface gap column: **REJECT both tours** (capacity
      cost without signal; reverted 1f06d9b)
- [x] R2-003 sconf surface-sample gate: **REJECT** (tune-era-only signal, every
      2021+ year negative; reverted d328688; ATP arm skipped)
- [x] R2-004 mty training-window floor 2000/2005: **REJECT** (truncation overpays
      for drift; driver-only)
- [x] R2-005 tierw tier_k^α sample weighting: **REJECT** (uniformly hurts LL while
      helping acc — miscalibration; driver-only)
- [x] R2-006 pooled cross-tour combiner + is_wta: **REJECT** (contamination at
      ±10–32 SE per-year; A5-full shape; driver-only)

## Review
- **Stop condition 2 (plateau)**: five consecutive Tier-2 rejects; round ran
  22:10–23:24 EDT (1h14m of the 8h budget). Nothing adopted; incumbent unchanged
  since fec0fb1 — no production rebuild required.
- Useful residue: quantified ~0.0003 LL capacity toll for stateless feature
  columns (new lessons.md entry); five families added to ideas.md do-not-retry;
  R2-004's Tier-0 probe re-proved bit-reproducibility of frame+bagged-walk.
- OPEN for a future round: h2hr, seedf (verify seeds reach the prediction feed
  first), retd; wta24 remains BLOCKED (supervised).
- Branch left for user review; not pushed.

---

# Task: Harness improvements from R1's observed failures (2026-07-06 evening)

Plan: C:\Users\varma\.claude\plans\fizzy-frolicking-starfish.md (v2)

## Checklist
- [x] tune.py: per-year tripwire in --validate (`_per_year_line` + last_years
      capture in evaluate_vec, all four groups)
- [x] tune.py: TPE anchor fallback to _xgb() defaults for override-free tours
      (reg_alpha/gamma floor-clamped into the log space)
- [x] tune.py: feat layoff_days range 365→730 (WTA optimum sat at ceiling)
- [x] tests/test_tune_validate.py: pinned-value tests for _per_year_line
- [x] ledger.tsv: clock column (HH:MM-HH:MM), R1 rows backfilled from commit times
- [x] PROGRAM.md: measure-don't-estimate clock rule, measured R1 tier costs,
      round-zero ideation stage, PYTHONIOENCODING, parallelism verdict
- [x] SKILL.md: date at round start + round-zero reference
- [x] ideas.md: 3c resolved; new OPEN fp3 (widened layoff space)
- [x] verify: 105 pytest + ruff green; anchor check trial 0 = 0.56383 vs baseline
      0.56406 (enqueued _xgb defaults, floors ≈ off — was a random draw before);
      per-year line live on the real _pa5 study ("val-yrs: 3/7 pos, worst 2022
      -0.00156 (t=-2.7)" — flags the R1-006 overfit at Tier-1); contention
      measured atp 332s / wta 181s solo vs 417s concurrent (1.26× ≤ 1.3 threshold)

## Review
- **All five R1 lessons are now mechanical**: the clock is stamped per ledger row
  and read (never estimated) at stop checks; the per-year tripwire prints at
  Tier-1 --validate (would have saved R1-003-atp's arbiter run); override-free
  tours get a real TPE warm start; the layoff bound is unstuck (fp3 queued);
  round-zero ideation fan-out attacks the actual bottleneck (ideas, not compute).
- **Parallelism verdict**: tour-pairs permitted at Tier 1 with measured honesty —
  19% wall-clock saving, not 2× (XGB already saturates cores); Tier-2 sequential
  by design (adoption changes the incumbent).
- **Measured tier costs** replace docstring folklore in PROGRAM.md (feat ~1 min,
  xgb ~30 s per trial; Tier-2 ~7–8 min per tour — 6× cheaper than budgeted in R1).
- One shell mishap during verification (a backgrounded && chain corrupted the
  first contention run) was caught before producing numbers, killed, and re-run
  as a script; orphan check confirmed a clean rerun.
- Push and branch merge left to the user.

---

# Task: Autoresearch round R1 (2026-07-06, /research-round 8h)

Branch research/2026-07-06 (base 5180300); ledger tasks/research/ledger.tsv R1-*;
full write-up tasks/tuning-results-2026-07-06-autoresearch.md.

## Experiments
- [x] R1-001 ATP feat sweep (_fp1, 20 trials): PASS-comp 5/5, coherent cluster
- [x] R1-002 WTA feat sweep (_fp1, 20 trials): PASS-comp, one val-positive config
- [x] R1-003-atp bagged arbiter: **DECLINED** — formal PASS, zero val carry
      (d_val −0.00006, val years 3/7, 2024 t=−2.5) — 4th ATP tune-overfit instance
- [x] R1-003-wta bagged arbiter: **ADOPTED (fec0fb1)** — d_tune +0.00084±0.00027,
      d_val +0.00085±0.00038, 13/17 years positive; WTA Brier 0.2018→0.2015,
      acc 0.6829→0.6836; FEAT_PARAM_OVERRIDES[wta] + form_days 90→65
- [x] R1-004 WTA xgb re-sweep post-A5+fp1 (_pa5): REJECT — incumbent unbeaten,
      optimum robust across two feature-distribution shifts
- [x] R1-005 WTA feat re-sweep at new incumbent (_fp2, self-gen): REJECT — 0/5,
      fp1 is a local optimum
- [x] R1-006 ATP xgb re-sweep post-A5 (_pa5, self-gen): REJECT — 4th instance of
      the ATP tune-overfit shape, now regime-independent (all top-5 val-negative)
- [x] Round ended on stop condition 3 (backlog exhausted + 2 consecutive self-gen
      rejections), ~2h elapsed of 8h — by the clock this time
- [x] End-of-round: production rebuild (--tour all --backtest) verified — WTA
      deployed-window (2016–26) LL 0.5946→0.5937 / Brier 0.2045, ATP unchanged
      (0.6832 acc / 0.2001 Brier, folds bit-match the arbiter base arm); results
      doc, lessons.md (cache-not-param-keyed), ledger committed per experiment

## Review
- **Adopted**: WTA FeatureParams — first-ever entries in FEAT_PARAM_OVERRIDES
  (fatigue 33d, layoff ~off, peak age 24, winrate window 23, form 65d). Honest
  val-equals-tune gain, healthy per-year profile.
- **Declined/rejected honestly**: ATP FeatureParams (tune-overfit caught by the new
  per-year table on its first live use), WTA xgb re-sweep, WTA feat re-re-sweep.
- **Harness verdict**: loop ran unattended within invariants — ledgered
  experiments, per-experiment commits, no eval/ or gate edits, no downloads.
  Per-year tripwire and the invalidate-stale-feature-cache lesson were the round's
  methodological yields. One self-correction: a premature wall-clock stop after
  R1-005 was retracted (elapsed time had been estimated, not measured — 1.5h real
  vs 7h assumed); the round resumed with the remaining budget.
- Push and branch merge left to the user.

---

# Task: Autoresearch harness — codified overnight research loop (2026-07-06)

Plan: C:\Users\varma\.claude\plans\fizzy-frolicking-starfish.md
Adapt karpathy/autoresearch to this repo: standing agent program + append-only
experiment ledger + seeded ideas backlog + /research-round skill, wrapping the
existing three-stage gate (component sweep → validation window → full arbiter).

## Checklist
- [x] tasks/research/PROGRAM.md — standing program (invariants, tiers with budgets,
      gate parsing formats, git protocol, stop conditions, consolidation)
- [x] tasks/research/ledger.tsv — append-only ledger, seeded R0-000 baseline row
      (ATP 0.6958/0.5700/0.1947, WTA 0.6829/0.5878/0.2018 @ 5c4d012)
- [x] tasks/research/ideas.md — backlog: fp1 FeatureParams sweep, pa5 WTA xgb
      re-sweep post-A5; wta24 BLOCKED (no-download); do-not-retry table; stale
      mcw-range idea recorded as superseded (range already 1–400, mcw=70 adopted)
- [x] .claude/skills/research-round/SKILL.md — thin launcher (args 8h/N/smoke,
      preconditions, branch, resume-from-ledger note)
- [x] ab_data.py _verdict(): per-year paired-d table + N/M-positive summary
      (encodes the lessons.md instability tripwire into every Tier-2 run)
- [x] tests/test_ab_data.py — exact pinned per-year values + GATE line format
- [x] verify: full suite + ruff green (103 passed)
- [x] verify: A5 ground-truth replay through _align+_verdict reproduces the
      documented adoption exactly (d_tune +0.00587±0.00089, d_val +0.00756±0.00100,
      17/17 positive, max |d| 0.01140 — a clean textbook per-year signature)
- [x] verify: smoke experiment — real 30-trial elo sweep (_smoke tag), gate
      parsed, ledger row R0-001 appended, honest REJECT (best = incumbent anchor)

## Review

- **What shipped**: the autoresearch loop (karpathy-style edit→run→gate→log→revert)
  codified over the existing three-stage protocol. PROGRAM.md is the program,
  ledger.tsv the append-only record, ideas.md the backlog, /research-round the
  launcher. One code change: _verdict() now prints the per-year paired-d table +
  N/M-positive summary, so the lessons.md instability tripwire is printed by the
  tool instead of recomputed ad hoc.
- **Deviations from plan**: smoke was executed directly (skill registered mid-
  session, invoked steps manually) and recorded as R0-001 on master rather than a
  throwaway research branch — real rounds (R1+) use research/YYYY-MM-DD branches
  per PROGRAM.md. The queued "WTA mcw range extension" idea was found stale
  (tune.py already sweeps 1–400; mcw=70 adopted) and was replaced by pa5 (WTA xgb
  re-sweep under post-A5 feature values).
- **Verification**: 103 pytest + ruff green; A5 pickle replay bit-matches the
  documented adoption; smoke sweep produced the expected honest REJECT.
- **Next**: `/research-round 8h` for a full overnight round (fp1 → pa5 first);
  `/loop /research-round 8h` for resilience. Push left to the user.

---

# Task: Data-gap round — challenger ingestion + WTA backfill + altitude (2026-07-05)

Plan: C:\Users\varma\.claude\plans\give-me-a-clear-rosy-raccoon.md
Headline: stats.tennismylife.org backfilled {year}_challenger.csv to 1978 and hosts
atp_quali/{year}_atp_quali.csv from 2007 (verified per-year, full serve stats) —
A5 is unblocked. All adoptions via the full walk-forward arbiter (paired d±SE,
tune 2010–19 / val 2020+), scored on the IDENTICAL main-draw eval set.

## Phase A — ATP challenger + qualifying ingestion (A5)
- [x] config: quali_file (+quali_first_year 2007) + ongoing_challenger_file,
      lower_dir(), LOWER_TIER_FIRST_YEAR=2005, TIER_NAMES "Q"→challenger,
      ROUND_ORDER Q1–Q3 (negative = pre-main-draw), stale comment fixed
- [x] download.py: download_lower() + --kind lower + download_all wiring (gated);
      archive bootstrapped: 43 files 2005–2026 (quali starts 2007 upstream)
- [x] results.py: load-time gate — _read_lower(), draw_level marker, __src=4,
      quali rows tourney_level→"Q"
- [x] features.py: draw_level carried through _assemble
- [x] tests: 4 new lower-ingestion tests; suite 96 passed; ruff clean
- [x] sanity: main rows bit-identical with flag on (152,952), +129,968 lower rows
      (100.5k chall + 29.4k qual), stats coverage 79.9%, 2019 upstream dip (3,099)
      + 2020 COVID (2,180) noted, 1,904/5,049 lower players overlap tour population
- [x] A/B arbiter mode=full: REJECT — d_tune +0.00869±0.00087 (10 SE, acc
      0.698→0.708!) but d_val −0.00107±0.00101; per-year d swings ±0.03
      (2024 −0.035 t=−15) ⇒ combiner training/calibration destabilized by
      challenger-dominated row mix, not a rating-priors failure
- [x] A/B arbiter mode=ratings-only: **PASS → ADOPTED** — d_tune +0.00587±0.00089,
      d_val +0.00756±0.00100 (7.6 SE, val > tune), full acc 0.6900→0.6958, Brier
      0.1975→0.1947 (crosses the 0.196 bookmaker anchor); 17/17 years positive
- [x] adoption: INCLUDE_CHALLENGERS=True; INCLUDE_WTA_125=False decoupled;
      pipeline main_rows() combiner filter; tune.py scoring masks main-only;
      regime-keyed feature cache; tests 98 passed + ruff clean
- [x] production rebuild (--tour all --backtest) verified complete 2026-07-06
      02:21 UTC: 2016-26 window ATP acc 0.6757→0.6832 / Brier 0.2034→0.2001;
      42-feature schema clean; health --strict green (ATP season stats 97.6%)
- [x] lessons.md: data-experiments-are-two-experiments lesson
- [ ] README metrics refresh (single pass after the altitude verdict)

## Phase B — WTA stats backfill
- [x] probe: API match detail starts 2016 — 2010–2015 CONFIRMED unreachable
      (tournaments enumerate but matches arrays empty; negative recorded)
- [x] scraper hardening: 404 fast-path; per-event hard-fail tolerance with
      majority-outage raise (+2 tests)
- [x] _enrich_from_local: scraped rows inherit rank/age/ht/hand from the frozen
      historical archive too (backfill years have no fresh overlay) (+1 test)
- [x] backfill 2016 + 2023: 2016 coverage 73.4%→94.3% (+387 recovered matches);
      2023 91.5%→91.8% (API lacks RG/USO stats); production rebuild verified
      WTA LL 0.5966→0.5946 on the 2016-26 window
- [ ] optional follow-up: 2024 top-up (78.2% merged), 2017–2022 marginal

## Phase C — altitude feature (gated experiment)
- [x] static venue→altitude table: data/altitude.py builder + committed
      venue_altitude.csv (331 venues, 0 unresolved; Quito 2854/Bogotá 2582/
      Gstaad 1055 verified); geo.city_key() extracted for shared resolution
- [x] altitude_km symmetric feature + predict.py mirror (event= path) + tests
      (key-set parity tripwire green; venue lookup + sponsor-prefix tests);
      101 passed, ruff clean
- [x] A/B arbiter both tours: **REJECT** — ATP +0.00005 (noise), WTA d_tune
      −0.00005 / d_val −0.00017±0.00012; wiring reverted with tombstone in
      SYMMETRIC; table/module/tests retained; schema re-verified == production
      predictor (42 features)
- [x] README metrics refresh (final numbers, five-source data section,
      data-round doc link, 182-test count)

## Review (round complete 2026-07-06)

- **Adopted**: A5 challenger+quali ingestion, ratings-only form — the largest
  gate-passing result in project history (d_val +0.00756±0.00100, 17/17 years
  positive). Full 2010–26 walk: ATP combiner 0.690→0.6958 acc, 0.1975→0.1947
  Brier — now clears the bookmaker literature anchor on both axes. Component
  effect even larger: ATP Elo-blend Brier 0.2062→0.2006.
- **Data refresh**: WTA 2016 stats 73.4%→94.3% (+387 recovered matches) + 2023
  top-up; 2010–2015 confirmed unreachable via the WTA API (negative recorded).
- **Rejected honestly**: A5 full variant (combiner-training contamination,
  ±0.03/yr instability); altitude feature (noise ATP, negative WTA) — both fully
  documented in tasks/tuning-results-2026-07-05-data-round.md.
- **Deviations from plan**: the plan's single Phase-A A/B became two (full +
  ratings-only) after the per-year instability diagnosis — the split IS the
  result (new lesson in lessons.md). Production pipeline gained the main_rows
  combiner filter, which the plan hadn't anticipated.
- **Verification**: 101 pytest + ruff green; production rebuild artifacts +
  schema verified; data.health --strict green; deployed-window metrics improved
  (ATP acc 0.6757→0.6832 on 2016–26).
- **Follow-ups parked**: WTA 2024 stats top-up (78.2%); WTA lower-tier remains
  gate-untestable; commit/push left to the user.

---

# Task: Autoresearch round — maximize model performance (2026-07-02 evening)

Goal: close the gap to the bookmaker (ATP 0.1983 vs 0.196 Brier; WTA 0.2023 vs 0.196).
Protocol per candidate: implement opt-in (incumbent-default, bit-identical), evaluate on
the full 2010–2026 walk-forward with paired d±SE split into tune (2010–19) / val (2020+)
windows, gate d_tune > 0 AND d_val > −1·SE, adopt plateau centers, document every
negative. Data frozen (no downloads); feature caches of 2026-07-02 19:35/19:45.

## Wave 1 — combiner mechanics (cheap paired A/Bs, both tours)
- [x] W1-impl: train.py opt-in knobs (n_bag/BaggedClassifier, weight_halflife,
      cal="stacked"; monotone via xgb_overrides) — bit-identical at defaults, 79→80 tests
- [x] W1-base: baseline OOS pickles reproduce last round exactly (ATP 0.57845, WTA 0.58889)
- [x] W1a seed-bagging: **bag5 PASS both tours** (ATP d_tune +0.00174/d_val +0.00042;
      WTA +0.00093/+0.00074; full LL ATP →0.57721, WTA →0.58803)
- [x] W1b monotone constraints: REJECTED (val regression both tours)
- [x] W1c stacked calibration: REJECTED (val −0.004/−0.009 — hard no)
- [x] W1d recency weighting: WTA REJECTED; ATP rec10/rec20 formal pass w/ flat val —
      deciding under bag5 (combo runs in flight)
- [x] W1-combine: **bag5 ADOPTED** (config.N_BAG=5, production defaults; bag10
      saturated both tours, recency rejected both tours incl. under bagging)
- SKIP cal2 (two-season Platt): ty−2 rows are in-sample for the fold model → biased
  calibration, and the honest variant costs a training season; pooled-OOS already lost.

## Wave 2 — Elo structure (elo-group sweeps ~5-10s/trial)
- [x] W2a P3 adaptive surface blend: REJECTED both tours BY THE SEARCHES — 400
      trials each, the enqueued incumbent (blend_n50=0) unbeaten; xsurf transfer
      already informs debutant surface ratings
- [x] W2b P2 home advantage: **ADOPTED both tours on the review-fixed geo** (ATP
      d_val +0.00134 (3.6 SE); WTA +0.00034, honest-sized after the Fed Cup fix).
      Adversarial review caught + fixed the Fed Cup host mislabeling that had
      inflated WTA 5×; candidates re-measured clean
- [x] W2c Elo-level home bonus: REJECTED both tours by the `_home` searches
      (home_adv=0 anchor unbeaten in 400 trials each); Elo geometry is a
      triple-confirmed plateau (xsurf → _ablend → _home identical optima)

## Wave 3 — point model
- [x] W3a-impl E3 event-speed serve baselines (review-hardened: off-free svpt-
      weighted residuals, state-mirrored inference, exact-value tests)
- [x] W3a sweeps: WTA REJECTED (noise, event≈off); ATP component gate 5/5 PASS →
      **arbiter REJECTED** (combiner d_val −0.00075 after retraining on shifted
      features — fourth ATP component-pass/arbiter-veto). E3 closed
- [x] W3b probes vs candidate: LR blend (both tours), beta calibration
      (year-unstable acc jitter), base-margin boosting, top-5 rejected configs
      under bagging (both tours) — ALL REJECTED with documented gates

## Wave 4 — consolidation
- [x] Combiner re-sweep check: top-5 study configs re-gated under bag5+home — all
      declined (ATP repeats tune-overfit even bagged; WTA val-only noise)
- [x] A5 challengers: SKIPPED — no source has challenger matches for 2010–19 (TML
      starts 2018; mirrors carry no qual_chall) ⇒ adoption gate powerless; documented
- [x] Final walk-forward table + round summary in
      tasks/tuning-results-2026-07-02-autoresearch.md; lessons.md updated (3 new);
      adopted set committed (9db1f8d) — push left to the user; production verified
      end-to-end (bagged predictor fit/pickle/reload, venue-threaded predictions)

---

# Task: Real-time updates + Linear-style UI overhaul + resume polish

Plan: C:\Users\varma\.claude\plans\can-you-check-if-purrfect-robin.md

## Checklist

### Part 1 — UI overhaul
- [x] Phase 0: globals.css token rewrite (+aliases), Inter/Geist Mono fonts, template.tsx page transition, MotionConfig, footer w/ GitHub link
- [x] Phase 1: lib/motion.ts (variants + useCountUp), bits.tsx restyle (skeleton Loading, animated ProbBar/Spark/Radar, AnimatedNumber/StatCard/Skeleton/GitHubIcon), ui.ts heat() hex ramp
- [x] Phase 2: Nav redesign (grouped dropdowns, layoutId pill, tour thumb, GitHub icon, mobile chips)
- [x] Phase 3 pages: all 12 migrated (home, method, trends, upcoming, simulator, rankings, accuracy, track, player, predict, style, strength)
- [x] Phase 4: alias tokens + .navlink deleted; grep-verified zero stale refs (lime/cyan/gold/coral/ink/anton/hanken)

### Part 2 — Real-time
- [x] web/lib/live.ts (nameKey, fetchLiveMatches, matchContext, winProb)
- [x] web/components/LiveTicker.tsx + mount on home (verified with stubbed ESPN fixture: 2 cards, qualifying/completed excluded, Elo odds join works; real CORS confirmed in-browser)
- [x] refresh.yml hourly cron (17 0-5,7-23) + cadence copy fixes

### Part 3 — Freshness pill
- [x] web/components/Freshness.tsx + mount in Nav (verified: "UPDATED 2D AGO" with local data)

### Part 4 — SEO
- [x] web/lib/seo.ts + 11 route layout.tsx files
- [x] root layout metadataBase/OG/twitter/viewport
- [x] web/app/icon.svg + web/public/og.png (PIL-generated 1200×630)

### Part 5 — Tests + CI
- [x] tests: test_elo.py, test_markov.py, test_names_merge.py, test_live_parse.py (25 passed incl. pre-existing test_track)
- [x] .github/workflows/test.yml

### Part 6 — README
- [x] badges + screenshots (docs/home|rankings|style.png via Playwright) + hourly cadence copy + live ticker mention + twelve-views section

### Verification
- [x] `npm run build` green; basePath build green (og:image = …/tennis-elo/og.png, title template works)
- [x] All 12 routes HTTP 200; browser sweep: correct titles, zero console errors/warnings, no Next error overlays
- [x] LiveTicker: real-browser CORS OK; stubbed-fixture render test (2 cards, qualifying/completed excluded, Elo odds join, WTA/ATP switch); hidden-tab polling pause by design, first fetch forced
- [x] Mobile 375px: chip nav shows, desktop nav hidden, no horizontal overflow
- [x] `pytest tennis_model/tests -q` → 25 passed (run directly, not just via agent)

## Review

- **Real-time**: browser polls ESPN every 60s (CORS confirmed `*`); quick-refresh cron 3h → hourly at :17; freshness pill reads meta.json `lastUpdated` (already existed — no pipeline change).
- **UI overhaul**: full Linear-style token system (near-black neutrals + single indigo accent + desaturated semantic/surface colors), Inter + Geist Mono, entrance template, layoutId nav pill + tour thumb, glass dropdown nav (12 links → 4 groups), skeleton loading, count-ups, Spark draw-in, Radar morph, scatter pop-in, animated bars everywhere. Alias-token strategy kept every step deployable; aliases deleted at the end.
- **Known trade-offs**: heat ramp is monochrome indigo (low probabilities read dim by design); page transitions are entrance-only (App Router exit anims need unsupported hacks); GH Pages CDN caches JSON ~10 min; Actions cron drifts 5–30 min.
- **Deploy-on-push added**: commit `0341407` — refresh.yml now also triggers on push to master (quick mode). Same index-only staging trick; working copy keeps the model-session's in-flight steps. Bot forecast-log pushes can't re-trigger (GITHUB_TOKEN).
- **Shipped**: commit `21265bc` pushed (scoped to this session's 47 files; refresh.yml staged index-only with just the cron change — the model-session's in-flight src/health.py/wta_stats.py changes remain uncommitted). test.yml run green; dispatched quick refresh deployed; live site verified (titles, og:image with basePath, GitHub link, og.png 200).

---

# Task: Model & data quality improvements (separate session)

Plan: C:\Users\varma\.claude\plans\while-the-other-plan-luminous-twilight.md
Scope: tennis_model/ + refresh.yml only (UI untouched — other session owns web/).
Full metrics progression: tasks/baseline-2026-07-01.md

## Checklist

### Track A — Data pipeline
- [x] A0: baseline has_stats % + walk-forward metrics; snapshot staged (CI creates the release)
- [x] A1: ATP stats migration to stats.tennismylife.org (ATP 2026: 8.7%→93% stats; 99.98% overlap agreement; +791 matches rescued by the year-in-dedup-key fix)
- [x] A2: resilience — strict validated atomic downloads, data/health.py sentinel, weekly release snapshots, cache→release→upstream bootstrap
- [x] A3: WTA serve-stats scraper (first-party api.wtatennis.com; real match dates; 125s excluded behind INCLUDE_CHALLENGERS; RET-enrichment score-guarded; 429-aware backoff; loud failure on truncation)
- [x] A4: odds automation (per-tour tennis-data.co.uk 2001/2007→2026 archives; market.json scorecard in the daily run)
- [ ] A5 (deferred, next session): Challenger/125 ingestion experiment

### Track B — Model
- [x] B1+B2: EloParams/ServeReturnParams refactor (bit-identical gate passed both tours). RET/WO: walkover-skip measured WORSE both tours → kept updating; RET down-weight left to tuner (≈1.0, irrelevant)
- [x] B3: eval/tune.py (Optuna, tune 2010-19 / validate 2020+); per-tour constants adopted in config (ELO_PARAM_OVERRIDES, SR_PARAM_OVERRIDES, TIER_ANCHORS)
- [x] B4+B5: 8 new features (layoff pair, form90, winrate10, surface H2H + volume gate, entry_q, peak-age) with predict.py parity
- [x] B6+B7: pooled-OOS + isotonic calibration measured WORSE → per-fold Platt kept (flags remain); BO5_SCALE=1.28 adopted for ATP (validated)
- [ ] B8 (deferred, next session): adaptive surface blend, XGB hyperparam sweep, home advantage

## Review

- **Headline (walk-forward 2010–2026)**: ATP combiner Brier 0.2022→0.1984, acc 0.678→0.686; WTA 0.2065→0.2033, acc 0.670→0.678. Bookmaker anchor 0.196.
- **Component gains (tune window; validation gains even larger)**: ATP Elo LL −0.010 / point model LL −0.020; WTA Elo LL −0.010 / point model LL −0.030. Big finds: serve/return form halflife 540→200 days; surface serve deviations ≈ noise (huge shrinkage toward global skill); Bo5 rating-diff scale 1.28 (ATP); layoff K-boost.
- **Data**: ATP serve stats had been frozen since Jan 17 2026 (TML GitHub died silently); WTA since May 2024. Both restored (ATP 93%, WTA ~90% for 2024–26) with daily refresh + a red-build sentinel so it can't happen silently again.
- **Negative results kept honest**: walkover-skip, pooled-OOS calibration, isotonic, global-only surface serve — all tried, measured, rejected.
- Tuning studies in tennis_model/data/output/tuning/*.db (resumable; `python -m tennis_model.eval.tune`).

---

# Task: Post-landing hardening + B8/A5 (follow-up session)

Plan: C:\Users\varma\.claude\plans\anything-else-we-can-transient-gem.md

## Checklist

### Fixes found by the post-landing deep review (commit 61c696e)
- [x] compare.py pnl TypeError — market.json was silently never written (reproduced live)
- [x] results.py same-day dedup dropped ~181 real RR/finals rematches — round joins the key
- [x] predict.py age_diff/ht_diff inference-parity break (one-missing-side → ±known value)
- [x] pipeline.py quick-mode schema guard (stale cached predictor → full rebuild, not a crash)
- [x] health.py Nov 21+ offseason relax + empty-frame NaT guard
- [x] wta_stats.py atomic write_year + _paged 50-page runaway cap
- [x] download.py strict_fatal() extracted + clamp regression test

### Harness (commit d45eeaa)
- [x] tune.py group=xgb (full walk-forward objective, match-paired trials)
- [x] --validate re-scores on fixed row sets and prints paired d±SE + gate verdict
- [x] point group scores on a FIXED reference serve-sample mask (selection artifact fixed)
- [x] surface_serve_shrinkage range → 10000 (WTA optimum sat at the old 3000 bound)
- [x] explicit XGB random_state=0; xgb_overrides threading; fallback shim suggest_int

### Reliability (commit b80be18)
- [x] data/names.py single name_key + identity-assertion lock + cross-language fixture
- [x] contract tests: _assemble anti-symmetry, oriented-xy flip, scores, calibrators,
      fit-fold determinism, predict-parity key set (suite 25 → 64)
- [x] ruff clean (BLE001 enforced via reasoned noqas) + CI lint step; requirements pinned

### Frontend (commit f511e2d)
- [x] eslint flat config (0 errors / 9 deliberate warnings); vitest 52 tests green
- [x] a11y: ticker list semantics + non-color cues; mobile freshness pill; nav labels
- [x] useData error state + rankings fallback; web CI job (lint+test+build)

### B8 — combiner + point re-sweeps (done; see tasks/tuning-results-2026-07-02.md)
- [x] xgb sweeps (400 trials/tour) + point re-sweeps _xwide (extended range)
- [x] paired-SE gates: WTA combiner ADOPTED (acc 0.679→0.681, Brier 0.2032→0.2027);
      ATP combiner rejected (tune-overfit); WTA point re-sweep = noise (plateau
      confirmed, old 3000 bound not binding); ATP point passed the component gate
      but FAILED the full-pipeline arbiter → reverted, incumbents stand
- [x] full walk-forward table under pinned stack; ATP 0.688/0.5788/0.1984 (0.002 acc
      from the bookmaker anchor — dedup fix contributed the acc gain)
- [x] tasks/tuning-results-2026-07-02.md
- [ ] feature-constant sweeps (FeatureParams), adaptive surface blend, home advantage
- [ ] A5 challenger experiment (INCLUDE_CHALLENGERS)
- [ ] WTA combiner min_child_weight range extension (sat at the 50 bound)

### Blocked on user
- [x] push the 4 local commits — resolved: verified local == origin/master on 2026-07-02

---

# Task: Core round P0/P1/E1/E2 + market stacker + UI track (2026-07-02)

Plan: C:\Users\varma\.claude\plans\did-you-improve-the-composed-manatee.md

## Checklist

### Model track
- [x] P0: **ADOPTED** — WTA combiner re-tuned (5/5 gate PASS; arbiter acc
      0.6811→0.6821, Brier 0.2027→0.2024, d_val +0.00100±0.00036); new
      XGB_PARAM_OVERRIDES["wta"] in config (lr .03, depth 7, mcw 70, alpha 5)
- [x] P1 code: FeatureParams refactor (config constants, dataclass, feat_params_for,
      form_days → EloParams, predict.py parity fix, contract tests); bit-identical
      gate PASSED both tours (WTA dtype-metadata-only delta from pre-pin cache)
- [x] P1 sweeps: REJECTED both tours (ATP 5/5 tune-overfit; WTA 5/5 val-negative,
      2 formal passers declined on direction). Refactor + feat group stand
- [x] E1: REJECTED (block AND workload-pair subset, paired A/B both tours: ATP val
      regression / WTA tune regression) — code fully reverted, tombstone comment in
      ANTISYM, bit-identical gate re-passed. Honest negative recorded in results doc
- [x] E2 BOTH TOURS **ADOPTED** — cross-surface transfer Elo:
      WTA xsurf=0.17 (blend 0.62, k 320/1.5/0.37, anchors 1.22/0.81; arbiter acc
      0.6822→0.6841, Brier 0.2024→0.2023); ATP xsurf=0.27 (blend 0.63, k 145/5/0.21,
      mov halved, anchors 0.91/0.89, bo5 1.28 re-confirmed; arbiter acc
      0.6878→0.6883, Brier 0.1984→0.1983)
- [x] P1 feat ATP: REJECTED (5/5 tune-overfit — third ATP instance of the pattern)
- [x] S1: DONE — ATP stack BEATS the closing market on validation (Brier 0.1996 vs
      0.2016; a_model 0.33); WTA between inputs (0.2004). Paper ROI positive but
      uncaveated — follow-up: audit the 629 ATP stack-disagreement bets for
      odds-join/RET artifacts before trusting +19% flat ROI
- [x] results doc tasks/tuning-results-2026-07-02-core-round.md (SKIP rationale written;
      gate numbers pending)
- suite 71 passed; ruff clean

### UI track (DONE — verified independently: vitest 75/75, lint 0 errors, build green)
- [x] U2: web/components/Dropdown.tsx primitive (~290 lines: listbox ARIA, outside-click,
      Escape→refocus, arrows/Home/End/Enter, 600ms typeahead, searchable variant,
      compact/align props) + 18 vitest tests (pure logic + SSR ARIA contract)
- [x] U2: Nav dropdowns outside-click/Escape/roving focus; strength add-player keyboard
      nav wired in place (add-to-set semantics ≠ primitive's select-one)
- [x] U2: predict/style Pickers + player-page datalist → searchable Dropdown w/ rank
      sublabels
- [x] U1: rankings age filter (rankRows/passesAgeFilter in lib/ui.ts, null-age excluded,
      filter-before-slice) + 7 tests; preview-verified (U23 → 33 rows, all <23)
- [x] U3: ALL layout-property animations → compositor (ProbBar/LiveTicker/home/simulator/
      accuracy/track bars → scaleX; radar vertices → translate; live-dot → ::after
      transform ring; will-change hints; template 0.22s); preview-inspected matrices
- [x] verify: mobile 375px no overflow (panels in-viewport), zero console errors

### Deferred (next candidates)
- [ ] P2 home advantage (ioc backfill + ~300-entry tourney→country map — data verified
      feasible: pair coverage 99.5%+ after backfill)
- [ ] P3 adaptive per-player surface blend (blend_n50 shrinkage param)
- [ ] E3 event-speed serve baseline (per-tourney_id shrunk priors)
- [ ] A5/P4 challenger ingestion (needs load-time gate in results.py first — flag currently
      gates downloads only)
- [ ] ATP combiner re-sweep ONLY if E1/P1 adoption changes the ATP feature frame

## 2026-07-02 — live official rankings + dynamic age filter (rankings page)

- [x] scraper: tennis_model/data/rankings.py — live-tennis.eu u868 table, stdlib HTMLParser,
      browser UA (403 otherwise), fail-closed validation (>=100 rows, first rank 1),
      keep-last-good rankings.json in live_dir; ø/đ/ł Latin fold + additive ALIASES
      (players.json carries duplicate spellings of the same human — both get the rank)
- [x] wiring: pipeline quick + --download paths, download.py all/live kinds (best-effort,
      never strict-fatal)
- [x] export: liveRank/liveRankDelta merged into players.json via name_key + sorted-token
      fallback (Wang Xinyu <-> Xinyu Wang); "matched N/200" log line = drift tripwire
      (currently ATP 189/200, WTA 186/200; all misses verified retired/unranked)
- [x] web: rankings page "Live rank" column (hidden <sm) + green/red movement badge vs last
      official release + live-tennis.eu attribution footnote
- [x] web: age filter now All/Under/Over dropdown + editable number (15-45 clamp, blur
      snap-back, empty input = no filter); parseAgeFilter/passesAgeFilter/rankRows in lib/ui
- [x] tests: +8 pytest (parser fixture from real page, keep-last-good, aliases, merge),
      rankings.test.ts rewritten for direction filter (81 vitest total)
- [x] verify: pytest 79 passed; real scrape 1000/tour; quick pipeline end-to-end both tours;
      vitest/lint/build green; headless Playwright on /rankings — 13/13 checks
      (column values, badges, footnote, under/over/empty/clamp filter behaviors, no console
      errors)

### Review
Scraper is best-effort by contract: any failure (Cloudflare challenge, layout drift) keeps
the previous rankings.json from the CI cache — the site degrades to stale ranks, never a
red build. Freshness = hourly quick run. Name-join residuals are individually verified
retired/doubles/unranked players, correctly shown as "—".

---

# Task: Name the tournament on the home "Up next" cards (2026-07-09)

User: the "Up next" prediction cards show only surface + `round · date` (e.g. "SF ·
2026-07-10") — the tournament is missing. The flat grid mixes tournaments, so each card
should name its event.

## Checklist
- [x] web/lib/upcoming.ts: `upcomingCard(m, { showEvent })` — when set, meta becomes
      `event · round · date` (the exact convention the Feed + Track "recent calls" cards
      already use); default unchanged so the /schedule board (event is a section header)
      stays clean. No change to the shared CallCard.
- [x] web/app/page.tsx: home `UpNext` grid passes `{ showEvent: true }`
- [x] web/tests/upcoming.test.ts: +1 case pinning meta with/without showEvent
- [x] Verify: vitest 12/12 (upcoming suite); `npm run lint` 0 errors

## Review
- **Shipped:** the home "Up next" cards now read e.g. "Wimbledon · SF · 2026-07-10". Chose to
  match the established meta convention (Feed/Track already prefix the event) rather than
  restructure the shared `CallCard` header — one canonical format across all four card
  surfaces, zero drift, minimal diff.
- **Why gated, not always-on:** `upcomingCard` feeds both the home grid and /schedule; the
  schedule board groups cards under a per-event `<h2>` header, so prefixing the event there
  would be redundant. The `showEvent` flag keeps that surface untouched.
- **Verification:** the unit test asserts the exact rendered string, and `CallCard` renders
  `{meta}` verbatim via a path already proven in production by the Feed/Track cards — so no
  new render behavior. No launch.json / Playwright in the tree now (unlike the original
  Up-next task), so browser capture was disproportionate for a proven string concat; the meta
  span wraps (no `whitespace-nowrap`) so long sponsor names degrade gracefully, and the real
  marquee data ("Wimbledon") fits the 3-col grid.

# Task: WTA /player + /style rendered blank — NaN in profiles.json (2026-07-09)

Repro (user): the deployed WTA player & style pages "look like the site is not loading".
Root cause: a scoreless WTA recent-match left `"score": NaN` in `profiles.json`. Python's
`json.dump` emits the bare token `NaN` (valid Python-JSON, accepted by `json.load`), but the
browser's strict `JSON.parse` rejects it → `useData`'s `r.json()` throws → `data` stays null →
the page renders a blank body between header and footer. ATP was clean by luck (no scoreless
top-200 recent match). Confirmed in-browser: `fetch('/data/wta/profiles.json').then(r=>r.json())`
threw `Unexpected token 'N' ... "score": NaN`.

## Changes
- [x] `model/export.py`: `_finite()` recursively maps non-finite floats → None; applied at the
      single write seam `_write` so no field/file/builder can ship NaN/Infinity (`build_fixtures`
      had the same latent `"score": r.score`).
- [x] `data/health.py`: `read_outputs` now parses web JSON with `parse_constant=<raise>`, so a
      NaN/Infinity file lands in `corrupt` → existing "present but unparseable" gate message
      (mirrors the browser; the old plain `json.loads` accepted NaN and never caught it).
- [x] `web/app/player/page.tsx` + `web/app/style/page.tsx`: explicit empty state on `!data`/empty
      roster (schedule-style muted message) instead of a blank body.
- [x] tests: new `tests/test_export.py` (3 cases: `_finite` scalars/nesting, `_write` browser-strict
      round-trip); `tests/test_health.py::test_read_outputs_flags_nan_as_corrupt`.

## Review
- **Verified locally** (Playwright on :3001, regenerated web JSON via the real `_finite`):
  WTA /player renders the full Sabalenka dossier (4 panels), WTA /style renders the radar +
  stat lines, the forced-fetch-failure empty state shows the clean message (not blank), ATP
  unaffected. Full suites green: pytest 222 passed, web vitest 95 passed, `npm run lint` +
  `npm run build` exit 0.
- **Not "unavailable" — a serialization bug over good data:** WTA profiles are complete
  (165/200 have style metrics, more than ATP's 152/200), so the fix makes the pages WORK rather
  than labelling them unavailable per the literal request; the empty state is an honest fallback.
- **Deploy:** code fix on `research/2026-07-09`; the live site keeps serving the NaN file until
  master regenerates + redeploys (gated on explicit user go-ahead). `web/public/data` is
  gitignored, so nothing data-side is committed.
- Lesson recorded in `tasks/lessons.md` (Python NaN vs browser JSON.parse; validate shipped JSON
  with a strict parser).

## Cross-session retrospective + pre-deploy integrity gate (2026-07-09)

Analyzed all 35 project work sessions (5 parallel agents over distilled transcript digests) for
recurring failure modes. Top finding: the dominant class is "shipped a data bug that silently
half-worked until the user caught it" — and `data/health.py` already encoded the right invariants
but ran only post-deploy / full-mode, so it never gated a bad deploy.

Changes (verified, then reconciled onto master — see deviation):
- [x] `health.py`: new `--gate` mode + `_gate_blocks()` — pre-deploy integrity gate over produced
      JSON. Blocks only provably-wrong output (impossible odds, `aliveCount>drawSize`, non-pow2 real
      draw, live event naming a champion, missing/corrupt required JSON); feed-thin/quirky signals
      stay advisory. `prev=None`; never writes health.json. Composes with the sibling session's new
      NaN-strict `read_outputs` (a NaN file → corrupt → blocked).
- [x] `refresh.yml`: `cancel-in-progress: true -> false`; `--gate` step before build/deploy on BOTH
      full and quick.
- [x] `results.py` `_parse_dates`: `format="mixed"` — silences the per-run "Could not infer format"
      warning (behaviour identical).
- [x] `test_health.py`: +2 gate tests. Full suite 225 passed, ruff clean.
- [x] `CLAUDE.md`: pre-deploy-gate hard rule. `lessons.md`: +2 entries (gate-before-not-after;
      cancel-in-progress).
- [x] `.claude/settings.json`: read-only + test/lint/build permission allowlist. `~/.claude/settings.json`
      (device-wide): UTF-8 env.

Deviation (important): a concurrent session sharing this working tree auto-stashed my uncommitted
changes ("pre-switch" stash) and merged its own work (NaN-strict JSON, Bad Homburg dedup) to master
mid-task. My first recovery (`git checkout <stash> -- health.py`) silently CLOBBERED the sibling's
committed `parse_constant` change — caught only because the "check first" pass compared master's
committed health.py against the restore. Correct recovery: ff to master, reset all my target files
to master, re-apply ONLY my hunks from context on top. Lesson: after a shared-tree disruption, never
restore whole files from a pre-disruption stash — diff every target against committed master first.

## Market benchmark un-freeze: per-row odds fallback + honest labels (2026-07-09)

Verified audit finding: tennis-data dropped Pinnacle after 2026-01-13; `compare.py`'s
frame-wide "ps" pick + dropna froze market.json's "2020+" sample at mid-January (last PS row:
ATP 2026-01-13, WTA 2026-01-14) while the scorecard showed it beside a May–July Kalshi card.

- [x] `eval/compare.py`: per-row odds coalesce ps→b365→avg (`_coalesce_odds`), per-year book
      census + derived honest label (`sources`), `oosEnd`/`lastMatchedDate`, era-matched
      `recent` block (trailing 90d paired Δ log-loss ± SE, kalshi_report convention).
- [x] `data/health.py` + `config.py`: staleness invariant — matched odds trailing the newest
      scored match by > `HEALTH_MAX_MARKET_LAG_DAYS` (60) flags; ADVISORY, not gate-blocking
      (odds are never a build dependency). market.json now read NaN-strict as optional output.
- [x] `web/app/scorecard/page.tsx`: hero "Vs closing line" + census label; panel "Vs the
      closing line" + era-matched row; §05 caveat. Pre-census payloads degrade gracefully
      (label falls back to "Pinnacle closing odds", era row hidden, no dangling copy).
- [x] Stale attributions: READMEs, `web/lib/seo.ts`, `kalshi_report.py`, `odds.py` comment.
- [x] Tests: fallback survival + census/label + exact era math (`test_compare.py`), advisory
      staleness (`test_health.py`). 229 Python + 97 web tests pass; ruff + eslint clean.
- [x] Real-data check: coalesced sample now ends 2026-06-28 (ATP) / 2026-06-27 (WTA) vs the
      frozen 2026-01-13/14; ATP 2026 census ps 71 / b365 1386 / avg 9 — matches the audit.
      Both payload shapes rendered and screenshotted via Playwright on :3002.
- **Review:** eval/reporting only — no model change, so no walk-forward arbiter. New payload
  fields ship with the next daily FULL retrain; until then the page renders honest fallbacks.
  Work done in an isolated worktree off origin/master (Codex loop held the shared tree).

## WTA FeatureParams parity fix (2026-07-09)

`pipeline.build_tour` built `TennisPredictor` without `fp=` → shipped pickles carried `fp=None`
and WTA inference used default FeatureParams (layoff 120d, peak 26.5) against a combiner trained
on tuned frames (360d, 24.0). ATP unaffected (no overrides).

- [x] `model/predict.py`: constructor derives `feat_params_for(tour)` when `fp` is omitted
      (explicit `fp=` still wins; legacy-pickle `_fp` fallback untouched); `fit_predictor`
      drops the now-redundant explicit arg.
- [x] `pipeline.py`: `_predictor_current(predictor, tour)` also flags FeatureParams drift
      (fp=None pickles, future `FEAT_PARAM_OVERRIDES` changes, cross-tour mixups) → hourly
      quick run self-heals via full rebuild.
- [x] Tests: `test_constructor_derives_tour_params` (exact magnitudes: peak_age_dev_diff −3.0
      tuned vs 2.0 default), `test_fp_survives_pickle_roundtrip`, `test_predictor_feat_param_guard`.
      Full suite 247 passed, ruff clean.
- [x] Proof on the shipped artifact: `data/output/wta/predictor.pkl` → `fp=None`, `_fp` ==
      defaults; new guard flags it stale; fixed constructor derives the tuned params.
- **Review:** parity bug fix, not a model change → no arbiter gate (walk_forward never touches
  the predictor path; this restores what the WTA `_fp1` arbiter adopted 2026-07-06). Built in a
  worktree off origin/master (Codex loop held the shared tree); merged → master → deploy;
  production heals on the next hourly quick run, daily retrain re-pickles regardless.

## Move the site off github.io → Firebase Hosting (2026-07-16)

Goal: a public URL without the GitHub username in it (ref: `gaffer-wc26.web.app`).
Target: **https://deuce-forecast.web.app/**. GitHub footer/nav links intentionally kept.

- [x] `firebase.json` (new, repo root): `public: web/out`, `trailingSlash: true` matching the
      Next export, no `cleanUrls`. Cache headers are load-bearing — Firebase defaults to a
      1-hour browser cache, which would serve this hourly-refreshed site's odds stale.
- [x] `refresh.yml`: workflow-level `env.SITE_URL` as the single source of truth (build,
      environment link, health-issue link all derive); `configure/upload/deploy-pages` →
      `FirebaseExtended/action-hosting-deploy@v0` (`channelId: live`); dropped
      `NEXT_PUBLIC_BASE_PATH` (root domain now); `HEALTH_PAGE_URL` off `env.SITE_URL` rather
      than the deploy output; pruned `pages:`/`id-token:` perms; concurrency `pages`→`deploy`.
- [x] `layout.tsx`: `SITE_URL` = `NEXT_PUBLIC_SITE_URL || firebase URL` (was hardcoded github.io).
- [x] `test.yml`: dropped `NEXT_PUBLIC_BASE_PATH` so CI exports the root-path build that ships.
- [x] `watchdog.yml`: status link → job-level `HEALTH_URL` (was derived from `${OWNER}.github.io`).
- [x] `pages-redirect.yml` + `.github/pages-redirect/{index,404}.html` (new): one-shot,
      dispatch-only. Pages keeps serving its LAST build forever, so stopping the deploy would
      strand a frozen forecast site on the old URL. The 404.html is what preserves deep links.
- [x] READMEs: live-site badge + URLs. `next.config.ts`: basePath plumbing kept (portability),
      comment corrected.
- [x] Zero Python changes — `HEALTH_PAGE_URL` was already just an env var (`health.py:862`).
- [x] Local proof: 4 workflows + firebase.json parse (strict `json.load`); `npm run build` green
      with og:image = `https://deuce-forecast.web.app/og.png`, zero `github.io` and zero
      `/tennis-elo/` refs in `web/out`, assets root-relative; web 158/158, lint 0 errors
      (13 pre-existing warnings, none in touched files); pytest 299/299.
- [ ] Blocked on user: Firebase project + `FIREBASE_SERVICE_ACCOUNT` secret → then push.
- [ ] Post-deploy: `VERIFY_BASE_URL=https://deuce-forecast.web.app npm run verify`; `curl -I`
      the cache headers; only then dispatch `pages-redirect.yml` once.

## Firebase deploy test suite (2026-07-17)

Goal: a detailed, standing suite that catches Firebase *serving* failures the pre-deploy
data gate can't see (stale CDN content after a green deploy, cache/MIME/trailingSlash/404/
basePath regressions). Decision: detect+alert, post-deploy only (no preview-channel gate,
no standalone monitor).

- [x] `web/scripts/routes.mjs` — canonical ROUTES factored out of verify.mjs; both import it.
- [x] `web/scripts/verify-deploy-lib.mjs` — pure helpers (parseCacheControl, expectedMimeFor,
      contentTypeOk, extractHashedAsset, isAbsoluteOnOrigin, freshnessOk, extractOgImage),
      side-effect-free so the unit test imports them without firing network checks.
- [x] `web/scripts/verify-deploy.mjs` — fetch-based suite vs a live base URL: routes 200+html,
      /method→301→/method/, unknown→404, cache split (data/HTML must-revalidate, /_next/static
      immutable), MIME (js/css/json not html), freshness (live generatedAt == built, with
      retry/backoff; `FRESH_TRIES` env-tunable), og:image absolute+on-origin. Exit 1 on any fail.
- [x] `web/tests/verify-deploy.test.ts` — 15 vitest cases over the pure helpers (incl. the
      html-fall-through and SITE_URL-regression negatives). `npm run verify:deploy` script added.
- [x] `refresh.yml` — post-deploy `Verify live Firebase deploy` (id verifydeploy,
      continue-on-error, EXPECT_GENERATED_AT from out/data/health.json, FRESH_TRIES=18) +
      `Report deploy health` (if: always()) mirroring `Report data health`: deploy-health issue,
      open+red at onset, full-run comment+red heartbeat, quick-run stay-green, close on recovery.
- [x] Docs: CLAUDE.md hard-rule (serving-side gate analogue), lessons.md entry.
- [x] Proof: web 173/173 tests + lint clean; live suite 7/7 PASS (exit 0); negative controls
      bite — wrong stamp → freshness FAIL (exit 1), bad base URL → routes FAIL (exit 1).
- [x] Push → confirmed: run 29611813087 green, `Verify live Firebase deploy` 7/7 in CI with the
      freshness check matching a fresh in-run stamp (2026-07-17T20:41:54Z), `Report deploy health` OK.

**Review:** Detect+alert post-deploy suite, no dual-deploy (user kept the redirect). The suite is the
serving-side analogue of the data gate — it catches what the pre-deploy gate structurally can't. Two
things earned their keep: the freshness retry (else it flakes on CDN propagation) and the negative
controls (proved it fails when it should). No deviations from the approved Phase-2 plan.

## Deploy-health alert misfired on a skipped verification (2026-07-21)

Health check of the repo turned up one real defect. Refresh run 29812819613 (08:03Z) went red
because the `--strict` download failed both tours' fresh 2025/26 files (upstream hiccup;
09:41Z onward recovered on their own). Everything downstream was skipped — including
`Verify live Firebase deploy` — but `Report deploy health` (`if: always()`) read
`outcome != success` as "the live site is broken" and opened deploy-health issue #8 blaming
Firebase, with an empty log block. The site was healthy throughout.

- [x] `refresh.yml` — guard in `Report deploy health`: only `success` (recovery) and `failure`
      (alert) touch the issue; `skipped`/`cancelled`/empty exit 0 without querying `gh`, leaving
      any open issue standing (recovery we never verified can't be claimed).
- [x] Proof: extracted the step's `run:` block from the YAML and ran it against a stubbed `gh`
      over 9 scenarios — 4 never-ran + 5 real-outcome. Post-fix 9/9 PASS; the same harness on
      the pre-fix script fails exactly the 4 never-ran cases (reproducing #8's spurious
      `issue create`) and passes all 5 real-outcome cases, so behaviour is unchanged where it
      mattered.
- [x] Repo health otherwise green: 299/299 pytest, 173/173 vitest, lint 0 errors, live suite
      7/7 vs deuce-forecast.web.app, no open issues, master clean and in sync.
- [x] lessons.md entry.

**Review:** Fixed the alerting, not the transient download — the download failure was upstream and
self-healed, while the misfiring alert would recur on every such hiccup and misdirect diagnosis each
time. The workflow shell has no permanent test harness (the scratchpad one was throwaway); worth
adding if these alert steps grow further.

## Download retry + testable CI alert shell (2026-07-21)

Follow-ups to the deploy-health fix, both requested after the health check.

**1. Download retry.** `download_year` used `_via_https(retries=1)` — zero actual retries — with
`_via_gh` as the only fallback. One instant where both transports missed killed the daily full
retrain (run 29812819613: `atp/fresh` AND `wta/fresh` both FAILED [2025, 2026], because
FRESH_SOURCE points both tours at the same repo).

- [x] `download()` retries failed years with exponential backoff, bounded by a round count
      (`retry_rounds=2`) AND a wall-clock budget (`retry_budget_s=90`). The budget is what keeps
      a genuinely dead 47-year archive from costing three full passes of 30s timeouts; the
      happy path costs nothing (no extra fetch, no sleep).
- [x] `test_download.py` +4 cases: happy path never sleeps, transient blip recovers, permanent
      failure stays bounded (3 attempts, backoff [1,2]), dead archive stops on budget with every
      year still reported failed.
- [x] Negative control: same flaky source with `retry_rounds=0` reproduces the exact production
      log line (`atp/fresh: downloaded 0 year file(s), FAILED 2: [2025, 2026]`); with retries it
      recovers. The retry is load-bearing, not decorative.

**2. Testable CI alert shell.** The alert branch logic was a 30-line inline `run:` block that no
test could reach — which is exactly why the skipped-vs-failed bug shipped.

- [x] Extracted to `.github/scripts/report-deploy-health.sh`; refresh.yml now calls
      `run: bash .github/scripts/report-deploy-health.sh` (19 steps before and after).
      Chosen over parsing the YAML at test time, which would need a PyYAML dep CI does not
      install and would test a copy rather than the artifact CI runs.
- [x] `tennis_model/tests/test_workflow_alerts.py` — 9 cases running the real script under bash
      with a stubbed `gh`, asserting exit code + exact `gh` subcommands: 4 never-ran (no page, no
      red, no call at all), success quiet / success closes, failure opens+reds, full-run comment
      heartbeat, quick-run stays green and silent, verifier log reaches the issue body, plus a
      guard that refresh.yml still invokes the script (else it drifts out of use while green).
- [x] `.gitattributes` pins `*.sh` to LF — repo is developed on Windows with autocrlf on and a
      CRLF shebang fails the Linux runner. Verified the staged blob is LF.
- [x] Negative control: deleting the guard from the script fails exactly the 2 never-ran tests
      and passes the other 7 — the harness bites the real regression without over-constraining.
- [x] Proof: 312/312 pytest (was 299), ruff clean, 173/173 vitest, web lint 0 errors. Simulated
      the exact CI invocation (relative path from repo root) across success/failure/skipped/
      failure-with-open-issue — all four behave correctly.
- [x] CLAUDE.md hard rule + lessons.md entries.

**Review:** The retry fixes a real robustness gap but the *alerting* fix was the higher-value half
— a bad alert costs diagnosis time on every future incident. Deliberately did not extract the
`Report data health` step too: same pattern, but it is working and untouched by this bug, so it
stays a follow-up rather than scope creep in a fix commit.

---

# Task: Fix the three deployment failures of 2026-07-24 (2026-07-24)

Diagnosis of runs 30077588939 (08:03), 30106835566 (15:48), 30133399444 (23:17) — three reds,
three unrelated causes, only one of which was a real pipeline defect.

**1. The fresh overlay had been dark for 5 days (the real defect).** `STRICT: 2 critical
download failure(s): ['atp/fresh:2026','wta/fresh:2026']`, identically on 07-20/21/22/23/24.

- [x] Root cause: `LuckyLoser91/TennisCourtLog` added `*.csv filter=lfs` on 2026-07-19, so
      `raw.githubusercontent.com` returns 200 with a 131-byte LFS pointer — and the `gh`
      contents API returns the pointer too. Confirmed by fetching both directly.
- [x] `download_year` iterates *candidate payloads* (`_candidate_payloads`) and validates each,
      instead of `_via_https(...) or _via_gh(...)` — that `or` only fell through on a `None`, so
      any 200-with-garbage (pointer, HTML error page) skipped the fallback transport entirely.
- [x] LFS resolved via `media.githubusercontent.com/media/{repo}/{ref}/{path}`, derived from the
      raw URL (`_lfs_media_url`), so every GitHub source is covered without config churn.
      Verified live: returns the real 164,611-byte CSV with the correct header.
- [x] Corrected the false premise in `download()`'s docstring: run 29812819613 did NOT self-heal
      — the "recovery" run was a *quick* refresh, which never downloads year files.
- [x] 5 new test_download.py cases: pointer recognised (and never valid as CSV), media URL
      derivation, pointer→media recovery, 200-with-HTML falls through to `gh`, all-transports-bad
      still reports failed (strict gate stays truthful, nothing clobbers good on-disk data).

**2. A GitHub API 504 redded a run in which everything passed (false alarm).** Gate green, 0
output problems, deploy + live verification OK — then both report steps died on an unguarded
`EXISTING=$(gh issue list ...)` under `bash -e`.

- [x] `list_existing()` in both alert scripts: retry 3x, then degrade to UNKNOWN. Healthy +
      unknown stays GREEN; failing + unknown goes RED but files nothing (cannot distinguish
      "no issue yet" from "already open" — guessing opens a duplicate thread hourly).
      `GH_RETRY_SLEEP` env-tunable so tests hit the retry path instantly.
- [x] Extracted `Report data health` to `.github/scripts/report-data-health.sh` — the follow-up
      left open by the previous round, and the bug lived in exactly the branch no test reached.
      Only the health.json read stays in the YAML (data plumbing, not alert logic).
- [x] 11 new test_workflow_alerts.py cases (20 total): 4 API-outage cases across both scripts,
      the full data-health matrix (ok quiet / ok closes on both modes / onset reds on both modes /
      full-run heartbeat / quick stays green when unchanged / quick comments when changed), plus
      a guard that no `gh issue create|close|comment` is left inline in refresh.yml.
- [x] Negative control: the old unguarded logic exits 1 on healthy data + a stubbed 504; the new
      script exits 0 with a warning. The guard bites the exact production regression.

**3. Issue #9 was a false positive.** "'Mubadala Citi DC Open' and 'Memphis' overlap in dates
and share 20 players" — all 20 shared names were `Qualifier N` placeholders; zero real players.

- [x] Washington (WTA 500) and Memphis (WTA 250) genuinely run the same week with different
      fields (Pegula/Svitolina vs Alexandrova/Golubic). Confirmed against the live
      `wta/tournaments.json`: 20/20 shared names matched `^Qualifier \d+$`.
- [x] `_tournament_name_problems` intersects only slots passing `sim.bracket.is_real` — the same
      predicate the draw machinery uses to fill them.
- [x] Caught a second-order gap while verifying: dropping the placeholders also drops the counts,
      so `>=3 shared` alone let a genuine rename through on a draw with only 2 names in it. Added
      a containment rule (one real field wholly inside the other, both >=2) — same impossibility
      at small size. Surfaced by a negative control, not by the test suite.
- [x] 2 new test_health.py cases incl. the real Washington/Memphis shape, a 1-shared-name
      legal case (late wildcard between concurrent events), and an all-placeholder draw.
- [x] Verified against the live shipped JSON: was flagged, now clean; renames still caught.

- [x] Proof: 330/330 pytest (was 312), ruff clean, 173/173 vitest, refresh.yml parses, both
      scripts pass `bash -n`, new script is LF (pinned by `.gitattributes`).

**Review:** Issue #9 should be closed as a false positive once a green run confirms it — the
recovery path auto-closes it. The 5-day silent model staleness is the finding that matters most:
the site never looked broken because the quick path kept deploying fresh scores from a stale
model, so only the daily-retrain red revealed it. Worth a watchdog on model age, not just data
age — logged as a follow-up, deliberately not scoped into this fix.

---

# Task: Future-date guard — the failure the LFS fix uncovered (2026-07-25)

Dispatched a `full` run (30143391810) to prove the LFS fix. The download half worked on the
first try — `atp/fresh: downloaded 2 year file(s)`, `wta/fresh: downloaded 2`, no STRICT line,
the first successful fresh pull since 07-19 — and the run then failed 15 minutes later, deeper
in the pipeline, on a second latent bug the 5-day outage had been hiding.

- [x] Symptom: `AttributeError: 'Pandas' object has no attribute 'SF'` in
      `export.build_draws`, plus `rankings/wta: matched 2/2 exported players` (ATP: 193/200).
- [x] Root cause: the WTA fresh file carries the Iasi final as `2029/7/20`. `elo.last_date`
      → 2029, so `_active()`'s `last_date - ACTIVE_DAYS(550)` cutoff → 2028-01-17, leaving only
      Mayar Sherif and Paula Badosa (the two players in that row) active. `players[:32]` = 2 →
      `standard_seed_draw` pads to a 2-slot bracket → round labels are only `F`/`Champion` →
      `r.SF` raises. Chain confirmed end to end against the real file.
- [x] `results._drop_impossible_dates`, called from BOTH `merge_sources` (the real path, before
      dedup) and `clean` (direct callers). Never silent — prints what it dropped.
- [x] Two thresholds on purpose: `MAX_FUTURE_MATCH_DAYS = 60` at ingest (dropping rows is
      destructive, and the live overlay legitimately carries scheduled matches ~12 days out, so
      a strict `> today` cutoff would silently delete real fixtures) vs
      `HEALTH_MAX_FUTURE_DATE_DAYS = 14` for reporting (cheap, so it can be tighter and still
      catch whatever ingest let through).
- [x] New `future_dates` row in `source_checks` — hung off `date_max`, not `result_age_days`:
      the age check is structurally blind here (a future date makes the age NEGATIVE, which
      sails under its ceiling), and `res_max` is completed-only while this row was a `RET`.
- [x] 2 new tests (test_names_merge.py ingest drop + near-future row SURVIVES;
      test_health.py future-date flagged, negative age not reported as fine, past and
      plausible-near-future both clean). Updated the two pinned `checks` key lists.
- [x] Negative control on the real downloaded CSV: active-player count goes 2 → 261, exactly
      1 of 1611 rows dropped. Reproduces and fixes the production failure.
- [x] Proof: 332/332 pytest (was 330), ruff clean.

**Review:** The LFS fix was correct but incomplete as shipped — it restored the transport and
handed the pipeline a file whose contents had also changed. Worth remembering that the mirror's
"v1.0" commit rewrote the data at the same time it moved to LFS, so this source should be
treated as newly untrusted: it now uses `2026/1/4`-style dates and has at least one hand-typed
year error. Every staleness check in health.py is one-sided ("too old"); this one needed the
other end. Still outstanding from the previous round: a watchdog on MODEL age, not just data
age — the retrain being down for 5 days was invisible because the quick path kept deploying.

---

# Task: Model-age watchdog — the follow-up left open twice (2026-07-25)

The 07-24 and 07-25 rounds both closed with the same deferred item: *"a watchdog on MODEL age,
not just data age — the retrain being down for 5 days was invisible because the quick path kept
deploying."* Confirmed structurally before starting: `export.build_meta` stamps
`lastUpdated = now()` on EVERY export, quick runs included, so `HEALTH_MAX_BUILD_AGE_DAYS`
measures "when did we last write JSON", never "when was the model last trained". Live
`atp/meta.json` carries no model-age field at all (`lastUpdated 2026-07-25T04:57Z` on a model
that could be any age).

## Checklist
- [x] `predict.py`: stamp `trained_at` in `__init__` (both construction sites train-then-construct;
      derive-in-constructor per the fp=None lesson) — travels INSIDE the pickle, so an
      actions/cache restore can't launder it the way an mtime would
- [x] `export.py`: `build_meta(..., trained_at)` -> `modelTrainedAt`; `export_all` passes the
      predictor's stamp (quick runs republish the OLD pickle's stamp — that is the whole point)
- [x] `config.py`: `HEALTH_MAX_MODEL_AGE_DAYS = 3` (= three consecutive missed retrains)
- [x] `health.py`: ADVISORY model-age check in `output_problems` (+ `_GATE_ADVISORY` marker —
      a stale model must never freeze the site) + `model_trained_at` in the output block
- [x] web: `model_trained_at` on the report type; render it next to "built" on /health
      (no client-side threshold — the verdict stays in health.py)
- [x] tests: export (stamp + pickle round-trip + meta field + null degrade), health (over-limit
      flags, advisory not blocking, missing key silent, exactly-at-ceiling clean, main() alert path)
- [x] Verify: 338 pytest (was 332) + ruff clean; 173 vitest + lint 0 errors + build 21 routes;
      end-to-end `--gate` negative control; /health rendered on :3001

## Review
- **Shipped**: `meta.json` now carries `modelTrainedAt` beside `lastUpdated`, and `health.py`
  flags a model older than 3 days. The two timestamps answer different questions —
  `lastUpdated` is "when was this JSON written", `modelTrainedAt` is "when was the predictor
  behind it trained" — and the whole 5-day outage lived in the gap: the hourly quick refresh
  rewrote the first while reusing the pickle behind the second, so `HEALTH_MAX_BUILD_AGE_DAYS`
  was structurally incapable of firing. Confirmed before writing any code: live `atp/meta.json`
  had no model-age field at all.
- **The stamp is derived in `TennisPredictor.__init__`**, not at the two call sites — both
  construct straight out of `train_final`, and the fp=None lesson is that a call site will
  eventually forget. It rides inside the pickle rather than being read off the file mtime,
  because CI hands the quick run its predictor via an `actions/cache` restore.
- **Advisory, never blocking.** A stale model still forecasts; blocking the deploy would strand
  the site on an even older build. Same policy as forecast drift — the problem reaches a human
  through `health.json ok` → the existing `report-data-health.sh` issue flow, so no workflow
  change was needed (pinned by a test that runs `main()` end to end).
- **Missing stamp is silent, on purpose.** Pickles predating this export `modelTrainedAt: null`;
  alerting on that would fire on both tours for one cycle and teach the reader to ignore the
  check. The next daily full retrain fills it in.
- **Proof**: 338 pytest (+6) + ruff clean; 173 vitest + eslint 0 errors + typed build (21
  routes). `--gate` negative control on a 6-day-old model: exit 0 with
  `GATE/atp: warn atp: model last retrained 5d ago ... (advisory)`, and exit 0 clean at 2h.
  /health on :3001 against the live report doctored to the outage shape renders
  `ATP ... built 13d ago · trained 1h ago` / `WTA ... built 13d ago · trained 8d ago` with the
  problem listed under output integrity, 0 console errors.
- **Not fixed (pre-existing, out of scope)**: `npx tsc --noEmit` has 2 errors in
  `web/tests/bracket.test.ts` (a projection-fixture literal narrowing to `SF?: undefined`).
  CI runs eslint + vitest + `next build`, all green; `tsc --noEmit` over the test folder is not
  in the pipeline, which is why it went unnoticed.

---

# Task: The daily retrain was never firing — `github.event.schedule` (2026-07-25)

Found while trying to close the "README metrics refresh" todo: the README's headline numbers
disagreed with live `accuracy.json`, which led to asking when that artifact was last written,
which led here. The model-age watchdog shipped an hour earlier was built to DETECT this; this
is the mechanism that caused it.

**`Decide mode` never selected `full` on a scheduled run.** The inline block compared
`github.event.schedule` to the literal `"0 6 * * *"`. GitHub attributed the run occupying the
daily slot to the *hourly* cron string instead. From run 30147619526's own log:

```
if [ "schedule" = "schedule" ] && [ "17 0-5,7-23 * * *" = "0 6 * * *" ]; then MODE=full; fi
```

- [x] Blast radius: every scheduled run in the 05:00-07:00 window on 07-21/22/23/24/25 selected
      `quick` (30072983446, 29985821119, 29897681810, 29807886697, 30147619526 — checked from
      each run's `Selected mode:` line). The only successful FULL run in that window was
      30144323370, a hand `workflow_dispatch` at 04:36 on 07-25. The daily retrain has not
      fired on its own in at least five days.
- [x] Root cause is trusting *which* cron GitHub says fired. Delivery is delayed and
      re-attributed under load (the affected runs fired 06:30-06:43, never at :00).
- [x] Fix: read the clock, not the cron string. `.github/scripts/decide-mode.sh` — a scheduled
      run landing in `FULL_HOUR` (06 UTC) is the daily retrain, however GitHub labelled it.
- [x] Deliberately NOT "retrain whenever the model is older than N hours": a persistently
      failing full run would then be retried hourly, and since a red full run blocks the
      deploy, the site would freeze instead of coasting on quick refreshes. Mechanism here,
      detection in the model-age watchdog — they are separate on purpose.
- [x] Extracted to a script per the CLAUDE.md rule that already covers the alert shell. This is
      the SECOND inline-`run:`-block regression in a week; the rule earns its keep again.
- [x] 7 new test_workflow_alerts.py cases (26 total): the slot retrains, every other hour stays
      quick, dispatch overrides both ways, missing predictor forces full, push stays quick, and
      a guard asserting no executable line references a cron string ever again.
- [x] Proof: 344 pytest (was 338) + ruff clean; refresh.yml parses; `bash -n`; script is LF;
      unset-`GITHUB_OUTPUT` path exits 0.

**Residual, accepted:** if GitHub ever delays the 06:00 delivery past 07:00 UTC, that day's
retrain is missed. The model-age watchdog now pages after 3 days, which is the right backstop —
a tighter mechanism would trade a rare missed day for a possible hourly full-retrain storm.

**Still open — NOT fixed here.** Live `accuracy.json`, rewritten by today's genuine full run
(04:36, data through 2026-07-24), reports ATP combiner acc **0.6571** / Brier **0.2127** and WTA
**0.6767** / **0.2049**. `tasks/tuning-results-2026-07-05-data-round.md:96` records
**0.6832 / 0.2001** for ATP on the same 2016-26 window at A5 adoption. That is a real ~2.6pt
accuracy / +0.013 Brier regression on a like-for-like window, and both READMEs still advertise
the old 0.696 / 0.1947. Candidates: (a) `main_rows` going inert — `features.py:345` defaults a
missing `draw_level` to `"main"` and `main_rows` early-returns the whole frame if the column is
absent, which would put the challenger-dominated mix A5 explicitly REJECTED back into training
and scoring (ATP n=69,099 for 2016-26 is ~2.5x main-tour volume, consistent with this); note
`main_rows` has NO test. (b) the rewritten LFS mirror degrading recent-year data, already
flagged untrusted in the 07-25 entry. Needs a local rebuild to separate. The READMEs were left
untouched — refreshing them would launder whichever of these is real into a documented fact.

---

# Task: Challengers were 59% of the ATP combiner's "main draw" (2026-07-25)

Found by pulling the data locally to settle the metrics discrepancy from the entry above.
Not the LFS mirror — a labelling gap, and the regression is fully reversed.

## Root cause
`_read_lower` stamps `chall`/`qual` only on files it reads out of `lower_dir`. The ATP
serve-stats source ships `<year>_challenger.csv` into `stats_dir`, which nothing labels, so
those rows inherited `main` from `merge_sources`' `fillna("main")`. Worse, the stats overlay
OUTRANKS the lower overlay in the dedup preference (`__src` 1 vs 4), so for 2021-26 — where
both dirs carry the same challenger matches — the UNLABELLED copy won even though `lower_dir`
had it stamped correctly.

- [x] Measured on real data: 42,135 of the 71,856 ATP rows the combiner treated as main draw
      for 2016-26 were `tourney_level == "C"`. Provenance pinned by counting `C` per source
      dir: historical 0/151,340, fresh 0/4,318, lower 101,204 (stamped), **stats 42,359
      (unstamped)**.
- [x] Onset visible in the per-year main counts: 2016 2,965 / 2017 2,929 (normal tour volume),
      then 2018 jumps to 7,826 and stays ~7-9k. That tracks the stats source's coverage, which
      starts at 2018 — not a model change, a source arriving.
- [x] WTA never affected (no challenger ingestion; `draw_level` all main, steady ~2,600-2,900
      per year) — which is why only ATP regressed.
- [x] Fix: `results._stamp_draw_level` derives draw_level from CONTENT before provenance —
      `tourney_level` says what a match is regardless of which file carried it — with an
      explicit reader stamp still winning. Ratings untouched (walks see every row either way;
      tier K already keys off `tourney_level`); this only decides the combiner's train/eval set.
- [x] Real-data effect: ATP main 2016-26 71,856 -> 29,721, all tour-level, zero `C`. Total rows
      unchanged at 283,567 — relabelled, not dropped.
- [x] 2 new test_lower_ingestion.py cases (6 total): a challenger arriving via stats_dir (incl.
      the dedup-preference case where lower_dir also has it), and a table-driven check that
      content classifies but a reader stamp wins. Both verified to FAIL without the fix.
- [x] 346 pytest (was 344) + ruff clean.

## Review — the measurement
Local `--tour all --backtest` on freshly downloaded data (through 2026-07-24):

| ATP walk-forward 2016-26 | acc | Brier | logloss | n |
|---|---|---|---|---|
| production today (contaminated) | 0.6571 | 0.2127 | 0.6122 | 69,099 |
| recorded at A5 adoption (tuning-results-2026-07-05:96) | 0.6832 | 0.2001 | 0.5826 | — |
| **rebuilt with the fix** | **0.6833** | **0.2005** | **0.5837** | **28,717** |

Reproduces the adoption-time number to 4dp. WTA 0.6767->0.6780 acc / 0.2049->0.2045 Brier
(essentially unchanged, as predicted for an uncontaminated tour).

- **Not an adoption.** This restores the already-arbiter-adopted A5 configuration rather than
  proposing a new one; the near-exact reproduction of the adoption-time metrics IS the evidence
  for that. No arbiter gate run, deliberately — there is no new arm to gate.
- **README left alone.** Its table is the 2010-2026 window, which this run does not produce, so
  its 0.696/0.1947 is still not directly comparable. Now that the 2016-26 window matches its
  recorded value again, the README is plausibly fine as-is — but "plausibly" is not "verified",
  so the metrics-refresh todo stays open pending a 2010-26 run.
- **Local rebuild was stopped before finishing** — after both tours' models, exports and
  accuracy.json were written, the run sat in a rate-limit backoff doing a cold Kalshi ledger
  backfill (unbounded, network-bound, and its output must never be committed from here).
  Killed at that point; `kalshi_ledger/atp.csv` reverted.

---

# Task: Harden the daily ratings walk (2026-07-25)

Context from the same session: a "retrain" is TWO things — re-walking the Elo / serve-return /
context states over the whole history, and refitting the XGBoost combiner + Platt. Only the
first is time-critical (one day adds ~7 ATP main-draw matches to a 45,831-row frame, so the
combiner weights barely move). And `build_tour_quick` reuses the pickle's states verbatim
("No re-walk, no retrain"), so **ratings only ever move on a full run** — an hourly quick run
ships live scores computed from frozen ratings. That makes the daily walk the thing to protect.

Three ways it was being lost, one incident each:

- [x] **A download failure skipped the retrain entirely.** `download --strict` and the pipeline
      shared one `run:` block; a `run:` block is `bash -e`, so a non-zero strict exit aborted it
      before the pipeline line. That is the whole 07-19..24 outage. Split into separate steps;
      download is `continue-on-error` and no longer gates the retrain. Safe because
      `download_year` validates and never clobbers good on-disk data, and other sources (live
      ESPN results) routinely succeed while the mirror is down — so there IS new data to walk.
      Not swallowed: a trailing step reds the run after the deploy, same shape as the
      forecast-log escalation.
- [x] **A red run threw away a completed walk.** `actions/cache` only saves on a green job, so
      any late-stage failure — the 07-11 `KeyError: 256`, the 07-25 `.SF` AttributeError, a
      blocked gate, a Firebase hiccup — discarded a predictor.pkl that had already been written,
      and the next run restored the OLD model. A persistent late-stage bug froze ratings
      indefinitely. Split into `cache/restore` + `cache/save` with `if: always()`; key carries
      `run_attempt` because "Re-run failed jobs" reuses run_id and `cache/save` errors on a
      duplicate key.
- [x] **The backtest could kill the walk.** `walk_forward` runs BEFORE `train_final`, so an
      exception in a pure-metrics artifact aborted `build_tour` before `predictor.save()`. Now
      best-effort (same pattern as `_market_scorecard` / `_kalshi`): accuracy.json keeps the
      previous run's values and the retrain continues.
- [x] 4 new tests (350 total): backtest-crash-still-saves (patched `build_tour`, raises the real
      `KeyError(256)` shape), plus three workflow-text guards — download/retrain never share a
      `run:` block again, a failed download still reds the run, cache restore/save stays split
      with `if: always()`. All 4 verified to FAIL without their fix.
- [x] Proof: 350 pytest (was 346) + ruff clean; refresh.yml parses (22 steps) with the intended
      `continue-on-error` / `if: always()` / key shape.

**Deliberately not done:** decoupling the combiner refit from the ratings walk onto separate
cadences. Measured locally, the walk is 46s ATP / 15s WTA and `train_final` is seconds — the
refit riding along is nearly free, so splitting them buys complexity, not time. The daily
cadence was never the problem; losing the run was.

---

# Task: README metrics refresh — closing the last open todo (2026-07-25)

Closes the "README metrics refresh (single pass after the altitude verdict)" item that had
been open since the 2026-07-05 data round. Measured, not inferred:
`walk_forward(main_rows(build_feature_frame(tour)), start_test=2010, end_test=2026)` scored
with `eval.metrics.score` — the same path `build_accuracy` uses, just the README's window.

| 2010-2026 (measured 07-25, data through 07-24) | ATP acc | ATP Brier | WTA acc | WTA Brier |
|---|---|---|---|---|
| Elo blend | 0.6823 | 0.2006 | 0.6622 | 0.2114 |
| Point model | 0.6690 | 0.2055 | 0.6442 | 0.2152 |
| **Combiner** | **0.6958** | **0.1950** | **0.6848** | **0.2017** |

n = 45,831 ATP / 42,126 WTA. Every prior README row reproduces within rounding, so the docs
were never stale — the *shipped* `accuracy.json` was, via the challenger contamination fixed
in 2a32c0a. Updated both READMEs to the measured values + an as-of date + the repro command.

- [x] ATP measured twice, on separate runs, bit-identical (0.6958/0.1950/0.5707, n=45,831).

## The near-miss, and the structural fix

The FIRST attempt at this measured WTA on an **incomplete local dataset** and I nearly
committed those numbers. `data/raw/wta/stats/{2024,2025}.csv` were absent locally and
`2026.csv` had 242 rows vs 1,485 — because the scraped WTA serve-stats backfill exists ONLY
in the `data-archive` release asset, which CI restores on a cache miss and which a plain
`download --kind all` never fetches. WTA 2024 was 1,214 matches instead of 2,119; the WTA
point model read 0.6420/0.2165 instead of 0.6442/0.2152.

- [x] Caught by the row count, not the metric: README said 42,513 WTA and the run said 41,174.
      Comparing `n` is what surfaced it — the same tell that would have caught the challenger
      contamination in July.
- [x] Nothing wrong was committed; both READMEs were reverted, the snapshot restored, and both
      tours re-measured. ATP was unaffected (local >= snapshot in every source dir: historical
      identical at 151,386 lines, stats local 66,024 vs snapshot 65,445, fresh/lower are
      download-only) — so the contamination diagnosis and its ATP numbers stand unchanged.
- [x] **Corrects an earlier claim in this session**: "WTA moved barely, 0.6767 -> 0.6780" was
      production-complete vs local-incomplete, i.e. not like-for-like and worthless as stated.
      The conclusion it was offered for — WTA was never contaminated — stands on the
      `draw_level` analysis instead (WTA has zero chall/qual rows; `main_rows` is a literal
      no-op there, 127,830 -> 127,830), which does not depend on dataset size.
- [x] Structural fix: `tennis_model/README.md` Usage now leads with the snapshot bootstrap and
      says what breaks without it. Docs only — a startup check that warns when `wta/stats/`
      looks thin would be stronger, and is NOT done here.

## Still open
- WTA 2024 is 2,119 matches even WITH the backfill, vs ~2,600 in neighbouring years:
  `wta/historical/2024.csv` is genuinely truncated upstream at May (months 1-5 only, byte
  identical in local and snapshot) and the stats overlay only partly fills June-December.
  That is the pre-existing "2024 top-up" item, now quantified: ~500 matches short.

---

# Task: Close the last two open items (2026-07-25, cont.)

- [x] **`main_rows` had no direct test** despite encoding an adopted model decision — flagged
      twice earlier today. Two now pin it in `test_features.py`. The valuable one is the LINK:
      `_assemble` is the only thing carrying `draw_level` from the results frame into the
      feature frame, so dropping that one line turns `main_rows` into a no-op and the combiner
      trains on every tier — no error, no failing test, plausible-looking metric. That is the
      contamination arriving by a second route. Also made the missing-column branch print a
      loud WARNING instead of returning silently, and pinned that it stays quiet on the normal
      path. Negative-controlled: the audibility test fails without the change.
- [x] **`npx tsc --noEmit` had 2 pre-existing errors** in `web/tests/bracket.test.ts` — a
      fixture literal whose two `reach` shapes inferred a union with `SF?: undefined`, which
      an index signature rejects. Fixed by annotating the fixture `TournamentLite[]` so the
      literal is checked against the target type instead of inferred.
- [x] **Root cause of the drift, fixed**: `next build` only type-checks what the app imports,
      which excludes `tests/`, so errors could sit there indefinitely with CI fully green.
      Added a `tsc --noEmit` step to `test.yml` between Test and Build.
- [x] Proof: 353 pytest (was 351) + ruff clean; `npx tsc --noEmit` exit 0; 173 vitest; lint 0
      errors (13 pre-existing warnings, none in touched files); test.yml parses.

## Verified in production today
- Dispatched full run 30164231601 (`MODE: full (event=workflow_dispatch hour=15Z)`) regenerated
  `accuracy.json` on the fixed code: ATP 2016-26 combiner **0.6830 / 0.2004, n=28,718** (was
  0.6571 / 0.2127, n=69,099) — within one row and 0.0003 of the local measurement, so CI and
  local agree. WTA 0.6777 / 0.2049.
- First real `modelTrainedAt` stamps are live (ATP 15:59:28Z, WTA 16:09:47Z), `health.json`
  carries `model_trained_at` for both tours, 0 output problems. The watchdog is armed.
- First scheduled run since the cron fix logged `quick (event=schedule hour=15Z — default)`,
  confirming the script runs on real schedule events. The 06:00 full slot is still unproven
  until tomorrow — that is the last open item from today.

---

# Task: The clock fix missed on day one — claim the slot, don't match the hour (2026-07-27)

The 2026-07-25 cron fix replaced "which cron did GitHub say fired" with "did this run land in
hour 06". It missed the very first day. Actual scheduled deliveries on 07-26:

```
04:02Z schedule -> quick (hour=04)
07:05Z schedule -> quick (hour=07)   <- the delayed daily slot
08:03Z schedule -> quick (hour=08)
```

**Nothing was delivered in hour 06 at all.** Scheduled events are not merely late, GitHub drops
slots entirely, so any rule keyed to a specific hour keeps missing. Production went 35h without
a retrain (modelTrainedAt stuck at the 07-25 15:59Z manual dispatch while lastUpdated advanced
hourly) — exactly the divergence the watchdog was built to show, and it showed it.

I had documented this residual on 07-25 and called the watchdog an adequate backstop. That was
wrong: detection is not a substitute for a mechanism that works, and I traded a certain failure
for one I guessed was rare without checking how rare.

- [x] Rule is now **the first scheduled run at or after FULL_HOUR on each UTC day**, not the run
      that lands inside that hour. Jitter-proof: whenever the first post-06:00Z run arrives, it
      retrains.
- [x] A date marker (`data/output/.last_full_run`, carried in the data cache) makes it
      at-most-once-daily. Without it, every hourly run after 06:00Z would launch a ~30-minute
      job that can block the deploy. Written when the retrain STARTS, not when it succeeds, so
      a crashing pipeline cannot retry all day; a persistently broken retrain is the model-age
      watchdog's job.
- [x] `10#` base-10 coercion on the hour comparison — `[ 08 -ge 06 ]` is invalid octal and would
      abort the script under `set -e` precisely in the 08/09 window this fix exists to cover.
- [x] 4 new/rewritten cases (356 total): the real 07-26 delivery sequence replayed, once-per-day
      claiming, the octal trap, pre-slot hours stay quick, plus a workflow guard that the retrain
      step still writes the marker BEFORE the pipeline. 3 verified to fail against the old script.
- [x] Deliberately did NOT dispatch a manual full run to refresh the stale model: the retrain
      step writes today's marker, which would suppress the automatic run and destroy the proof.
      Letting the natural post-06:00Z run do it IS the test.

---

# Task: 16 hours of blocked deploys — an upset flag that disagreed with its own number (2026-07-27)

Every scheduled `refresh` from 07:54Z onward failed identically at the pre-deploy gate:

```
GATE/atp: BLOCK atp: fixtures.json upset flag disagrees with modelProb (0.5)
```

One row, one tour, and the deploy correctly refused to ship. Consequences by 21:00Z:
production stuck at `lastUpdated 04:43Z`, and `modelTrainedAt` still on the 07-25 15:59Z
manual dispatch — even though the 07:54Z run's **full retrain succeeded** (29m45s, step
green) and saved the fresh model to the data cache. The gate ran after it and blocked, so a
current model sat in the cache all day while the site served a two-day-old one.

Root cause, `model/export.py:242`: `"modelProb": round(p, 3)` beside `"upset": bool(p < 0.5)`
taken off full-precision `p`. Any winner priced in `[0.4995, 0.5)` ships `modelProb 0.5` with
`upset true`. `output_problems` can only re-derive the flag from the file, gets `False`, and
blocks. The gate was right — "50.0%" beside an UPSET badge is a visibly wrong card.

- [x] Flag derived from the **rounded value that ships** (`mp = round(p, 3)`; `upset = mp < 0.5`),
      so producer and gate evaluate byte-identical expressions on the same number. True by
      construction, not by tolerance — no gate change, no epsilon.
- [x] `sim/bracket.py` carried the same latent bug at 4dp, including on the `1.0 - p`
      orientation for slot b. Fixed in the same commit, before it fired.
- [x] 2 boundary tests (366 total), both verified to fail against the reverted producers.
      The pre-existing `upset` tests used 0.7/0.3 and would have passed forever.
- [x] Confirmed `build_fixtures` is the only writer of `fixtures.json`.
- [x] Pushed (83d0024). Run 30306780234 green in 7m27s — first passing gate since 04:42Z.
      Live now: `lastUpdated` 04:43Z -> 21:27Z, `dataThrough` 07-27, and `modelTrainedAt`
      07-25T15:59Z -> **07-27T08:03Z** — today's cached retrain shipped on this run, exactly
      as predicted. Only remaining annotation is the pre-existing data-health issue #10.

## Review

The gate did its job: it caught a real defect and held the last good build rather than
shipping a contradictory card. The failure was that nothing turned a *blocked deploy* into a
signal — 10 consecutive red scheduled runs sat unnoticed, and the one alert that did open
(#10) was for an unrelated advisory. The `deploy-health` sentinel watches the LIVE site, which
stayed green the whole time precisely because the old build kept serving. **A gate that blocks
is invisible to a monitor that only checks what's live.** Worth a follow-up: alert on N
consecutive gate blocks, since that is the state where the site is silently frozen.

Deliberately NOT touched: the three tournament-card advisories still firing (Generali Open /
Umag / Palermo alive-counts, `Qualifier 18` as modelFavorite) and issue #10 (wta meta.matches
128794 -> 128724). Both are pre-existing, advisory, and separately tracked — root causes were
logged as unfixed in 772e5d4. Folding them in here would have delayed unblocking the deploy.

---

# Task: The tournament-card advisories — two root causes, not one (2026-07-27)

772e5d4 added three advisory invariants and deliberately left the root causes. Four are
firing on the 21:31Z green run. They are NOT one bug:

```
atp  Generali Open  champion 'Quentin Halys'   but 26 alive   (drawSize 28)
atp  Umag           champion 'Daniel Merida'   but  2 alive   (drawSize 29)
wta  Palermo        champion 'Francesca Jones' but 32 alive   (drawSize 32)
wta  Palermo        modelFavorite 'Qualifier 6' is a draw placeholder
```

## Class 1 — a frozen early draw capture (Palermo, Generali Open; both advisories)

`draws_wiki.download_wiki_draws` keeps any cached entry that already has slots, forever:

```python
if cached.get(name, {}).get("slots"):      # already have this draw — keep it
```

"A draw doesn't change once released" is false for a draw captured BEFORE qualifying
resolves: the `Qualifier N` slots are never replaced. `project_tournament` then treats that
frozen list as the authoritative main-draw population (deliberately — line 315, discarding it
at completion once recreated a 133-player Wimbledon field), so:
- `field_pool` = 32 placeholder strings, which no results row can ever match, so
  `alive = field_pool - eliminated` subtracts **nothing** -> Palermo 32 of 32 alive
- the projection runs over placeholders -> `modelFavorite 'Qualifier 6'`

Proof it is the cache and not the article: the LOCAL `wiki_draws.json` (captured 07-25, after
qualifying) has **0 placeholders and correct accents** for both events — `Alex Molčan`,
`Facundo Díaz Acosta`. CI captured earlier and froze. A re-fetch fixes it.

- [x] `_draw_is_settled(slots)` gates the cache skip: keep a capture only when every named
      slot is a real player. `None` slots are byes and stay legal; an all-`None`/empty list
      is not a draw. A failed re-fetch keeps the stale entry rather than losing the draw.
- [x] Predicate is `sim.bracket.is_real` — the one `health.py:464` already delegates to, so
      ingestion and gate cannot disagree about what "placeholder" means. Verified against the
      exact strings production shipped ('Qualifier 6', 'Qualifier 18', 'Lucky Loser').
- [x] The log now separates `N new` from `N re-fetched`, so a silent re-fetch loop is visible.
- [x] Test on the real cached draw: clean today -> no re-fetch; inject one `Qualifier 6` ->
      re-fetch. Evidence a re-fetch fixes it: the local 07-25 capture of the SAME two articles
      has 0 placeholders and correct accents.

## Class 2 — one player, two identities (Umag)

Not a draw problem — Umag has no wiki draw at all. The results frame carries BOTH spellings:

```
Daniel Merida            <- champion
Daniel Merida Aguilar    <- same player, only ever appears as a loser
```

`results._canonicalize_names` unifies spellings only WITHIN a `_name_key` group; a dropped
surname changes the key, so the two never merge. Consequences: `drawSize` 29 for a 28-draw,
`alive` = {champ, ghost} = 2, and the champion's retrospective title odds are **split across
two entities** in the shipped projection — a user-visible defect the advisory only hints at.

Chose alias table + structural alive (both), so the identity is actually fixed AND the card
cannot contradict itself if a future variant appears before anyone adds an entry.

- [x] `config.PLAYER_ALIASES` ({`_name_key(variant)` -> canonical}), applied at the TOP of
      `results._canonicalize_names` so the existing source/frequency vote runs on merged
      counts. Deliberately hand-kept: a "shorter name is a prefix of the longer" heuristic
      would merge genuine relatives (the Zverevs, the Bryans).
- [x] `alive = {champ}` when an event is completed and names a champion. A finished knockout
      has one player standing by definition; deriving it by set subtraction made it hostage
      to name hygiene on both sides.
- [x] Kept the raw `field_pool - eliminated` as `still_in` for the >128-slot diagnostic, which
      exists to debug exactly this class and would have been blunted by a hardcoded 1.

## Review

367 pytest (+3), ruff clean; all 3 new tests verified to fail against the reverted sources.

The two classes looked like one advisory and were not: Palermo/Generali is an ingestion cache
that froze, Umag is one player counted twice. Worth noting the synthetic fixture in
`test_tournament_status.py` was ALREADY producing `aliveCount 7` on a completed event before
this change — the invariant simply had no test asserting it, so a bug reproducible with zero
network and zero real data sat in the suite the whole time.

Not done, deliberately: promoting the three advisories to blocking. 772e5d4 says "promote once
the ingestion is clean", but today's 16h outage was a blocking gate meeting live data it had
never been tested against. Watch a full refresh cycle confirm these are silent, then promote in
its own commit.

---

# Task: Long-term fix — live schedule/draw correctness + event identity (2026-07-27)

Plan approved (full version: ~/.claude/plans/my-recommendation-in-priority-breezy-bachman.md).
Evidence: 65 incidents catalogued; ~100% of "site showed wrong content" incidents are in the
draw/schedule/naming/surface family; root defect is 19 name-string join seams + no stable
event identity (ESPN's espnId parsed and discarded). Wikipedia-wholesale rejected on
evidence (can't do discovery/dates/live state/schedule); keep ESPN for discovery+results,
Wikipedia for structure, fix the join layer.

## Track A — correctness (one commit each, deploy-watched)
- [x] A1 surface: TWO parse bugs, not one — the field capture stopped at the wikilink pipe
      (Memphis hides the surface in the DISPLAY text behind a generic target) AND \bHard\b
      can't match the one-word `[[Hardcourt|...]]`. Between them every hard-court event had
      NO cached surface. Plus surface_src provenance (a month guess was being read back as
      "the archive value" — self-fulfilling), resolve_surface_info as the single chain with a
      tolerant lookup shared by both paths (fixes the Memphis start-day flip), surfaceSource
      on cards, and 3 gates (canonical BLOCK, month-guess ADV, cross-tour split ADV).
      Verified against LIVE Wikipedia: DC/Memphis/National Bank now all resolve 'Hard';
      Gstaad/Palermo still 'Clay'. 374 pytest (+7, all proven failing-first), ruff clean.
- [x] A3 placeholders: `projection_is_meaningful` (real*2 >= field) — the SAME majority rule
      `bracket_is_meaningful` already uses, so a card whose bracket is withheld as noise can no
      longer still publish odds from that noise. Placeholders stay IN the simulation (they hold
      real draw slots) but are never PUBLISHED as rows; no renormalisation, so each number is
      still a true marginal. Both web renderers guarded (the compact card is a SECOND component
      — the hero-only fix left DC unguarded, caught in the browser). eval/track.py now scores
      only priced snapshots: an unpriced card would have been charged Brier 1.0 for declining
      to guess. Gate: projection names via `is_real` (the exact-set check let the NUMBERED
      "Qualifier 30" through), tier-aware; modelFavorite check promoted to the same severity.
- [x] Fallout from A2's new advisory: it immediately found 'Mifel Tennis Open by Telcel Oppo'
      shipping a generic "ATP Tour" tier — no draw, no surface, no tier, because its sponsor
      title shares no token with "Los Cabos Open". Fixed via the two escape hatches that exist
      for this: WIKI_TITLE_OVERRIDES (also unlocks its surface: Hard) + EVENT_TIER_FALLBACK
      (the article omits `category`, same as Nordea). Gate passed and the site deployed both
      times; it was the SENTINEL that reddened, filing issue #11.
- [x] A2 level (moved ahead of placeholders — tier severity depends on it): tour tags were
      plain substrings and "men" is inside "tournaMENts", so `[[WTA 125 tournaments|WTA 125]]`
      matched the ATP tags outright; plus a LONE link was returned regardless of tour. Both
      gated now (word boundaries + None unless ours or unambiguously neutral). `normalize_level`
      at the single resolve_level choke point, SELF-ENFORCING against LEVEL_VOCAB (a bare "125"
      became "ATP 125", a tier that does not exist). Category cache no longer pins a poisoned
      cross-tour value forever — same first-capture trap as the draws cache.
      Tier-aware severity landed: GATE_BLOCKING_TIERS = Slam/Finals/1000/500 on both tours;
      `_tiered` stamps board-quality problems below that advisory, keeping `_gate_blocks` a
      pure string predicate. Olympics + Davis/BJK Cup deliberately advisory (atypical formats).
      Verified by REBUILDING real cards: 0 levels outside vocabulary, 'ATP 250 series'->'ATP 250',
      'C'->'Challenger'. That rebuild also caught a tuple I'd shipped as WTA Memphis's surface
      (widening `_known_surface`'s return arity; the 381-test suite passed anyway).
      RESIDUAL: a 500+ event that is still upcoming AND has no cached wiki surface resolves
      src="month", which now BLOCKS. Narrow (500s have long-standing articles; the cache
      persists once written; A5 adds retry) but real — that was DC's exact state on 07-25.
- [x] A4 gates: (1) upcoming-but-already-ENDED — the mirror of stuck-'live'; ending while
      never having gone live is impossible, so the card invites clicks on odds for a finished
      event. Tier-aware. (2) started-but-not-live: ADVISORY at every tier, 3d grace, because
      ESPN start dates include QUALIFYING (a Slam legitimately reads upcoming all quali week);
      a strict start<=today would false-fire constantly. (3) lost-bracket: a live event that
      HAD a bracket and now doesn't means its cached wiki draw is gone — the 07-27 Wimbledon
      256-slot class, caught early. Sentinel-only by construction (gate passes prev=None).
      Verified against LIVE production data: 0 blocking, only the Mifel advisory that A3 fixes.
- [x] A5 wiki hygiene: `_get` had NO backoff — alone among this repo's rate-limited fetchers
      (kalshi, wta_stats both handle 429). Now 3 attempts honouring Retry-After; a permanent
      404 still raises on the first try. `event_surface`/`event_category` merged into one
      `event_meta`: both fields live on the SAME article but each function re-resolved the
      title and walked its own candidate loop — ~30 calls per unresolved event, hourly.
      Fallback fetches capped at 5. Misses are STAMPED (never cached as a value) so a
      far-off event isn't re-asked every hour; anything starting within 2 days always retries.
      File formats unchanged, so every reader is untouched. Live check: DC ('Hard','ATP 500'),
      Memphis ('Hard','WTA 250') in one pass each.

## Track A review

All five shipped. The through-line: EVERY commit had a defect that only a real artefact
exposed while the unit suite stayed green — live Wikipedia caught A1's second parse bug (the
wikilink pipe), a card rebuild caught A2's tuple leaking into a surface field, the browser
caught A3's second projection renderer. Three lessons recorded on that alone. Worth keeping
as the working rule for Track B: rebuild the artefact, don't just run the tests.

## Track B — event identity (after A)
- [x] B1 events.py registry (per-tour, names history = alias table) written by both
      downloaders — inert, zero consumers, warms in the CI cache before B3 reads it. Built
      against the REAL feed: 8 ATP / 15 WTA events, and 888-2026 (DC), 306-2026 (Nordea),
      421-2026 (National Bank) each appear on BOTH tours, confirming combined events share
      one id. Key finding pinned in a test: name-only resolution CANNOT bridge the DC rename
      ("Citi" was inserted mid-name, so neither containment direction works) and `id_of`
      correctly refuses rather than guessing — what recovers the orphaned cache entry is the
      espnId draws_wiki already stamps INSIDE it, seeded via `EventResolver(extra=...)`.
      That makes `extra` load-bearing for B3/B4, not decorative.
- [x] B2 espn_id through live.csv/upcoming.csv/fields.json + results CANON. Dedup keys
      UNTOUCHED — the id is a HINT, never a key (the archive predates it and always will, so
      the surviving row after a merge often has none; consumers must take the modal non-null
      per event). upcoming dedup keys on the id when both rows have one, else the name, so
      the ESPN feed and the wiki overlay finally collapse the same matchup.
      NOTE two of my first four tests were duds and I nearly shipped them: `_read_dir` already
      keeps extra columns (so the CANON test proved nothing until rewritten to use an
      ARCHIVE-ONLY frame), and `load_upcoming` imports wiki_upcoming_rows INSIDE the function,
      making the monkeypatch on `upcoming` a silent no-op. Both now fail-first correctly.
      The dedup-unchanged test passes before AND after by design — it is a regression guard.
- [x] B3a id-first LOOKUPS in build_tournaments (split out from B3 — coalescing is the risky
      half and gets its own commit). `_split_by_key` classifies every cache key independently
      (both formats coexist during migration, and a soft-failed downloader can leave the two
      files in different shapes); a name-keyed entry carrying espnId inside is indexed under
      BOTH. `_group_event_id` takes the MODAL non-null espn_id — the merge prefers stat-bearing
      archive rows, which predate the id, so the surviving row often has none. Cards ship
      espnId; the pre-start loop recognises an already-projected event by id as well as name.
      Rebuild proof: DC resolves 888-2026 with bracketSize 32. The regression test replays the
      real rename and fails with `bracketSize: None` against the old code — the production
      symptom exactly. Took three passes to get there: the first two failed on a missing
      attribute and a missing field, either of which would have let a name lookup slip through.
- [x] B3b-pre: the id must SURVIVE the dedup that drops its row. Found by reading production,
      not tests: the WTA board was live-shipping a 12-player "Washington Dc" fragment BESIDE
      the full 28-draw "Mubadala DC Open" — one tournament, two cards, two different
      favourites (Navarro vs Pegula). Mechanism: dedup keys ignore tourney_name and prefer
      stat-bearing archive rows, so the ESPN row — the ONLY one carrying espn_id — is dropped
      and the identity goes with it. `_fill_espn_id` propagates the id across every row of a
      match before each dedup pass. With B3a's seen_ids check that alone suppresses the
      duplicate card. Test reproduces the live split and fails with {nan, nan} without it.
- [x] B3b group coalescing. The agent review never ran (8 of 9 agents died on a spend limit,
      returning an empty result that would have read as a pass), so I re-read it myself and
      found THREE silent defects — none of which failed a test or showed in a board rebuild:
      (1) id-less groups were keyed by normalised display name and ASSIGNED not appended, so
      two feeds spelling one name differently collided and an event vanished off the board;
      (2) the hit search read `by_id` live, so an id-less group could match a synthetic entry
      from an EARLIER id-less group — an undocumented, order-dependent merge; (3) `_real_players`
      counted QUALIFYING rows, and a player who loses quali at one event and plays the main
      draw at another the same week appears in both, which could manufacture three "shared
      players" between a Challenger and a main-tour event and merge two real tournaments.
      Each fix is pinned by reintroducing the defect and watching the test fail.
- [x] B4 RETENTION (the substantive half; the re-key itself is now largely moot because
      B3a's `_split_by_key` already bridges name->id via each entry's embedded espnId).
      The caches were rebuilt each run from the events ESPN currently lists, so a draw was
      DELETED the moment ESPN stopped mentioning its event — while build_tournaments keeps
      projecting that event for weeks (40d window). That is the 256-slot Wimbledon crash at
      its source, and it fired twice because the 07-11 fix made the cache authoritative,
      which only made the 07-27 deletion worse. Entries now survive on the EVENT's own dates
      (45d > the 40d window). Surfaces/tiers get the same treatment.
      Conflict found while writing it: retention initially resurrected the poisoned
      cross-tour tier that A2 drops. Retention protects FACTS, not rejected values — the
      carry-forward re-checks `normalize_level` before keeping a tier.
      Also: the first version of the retention test silently hit the live ESPN API (8.65s vs
      0.13s) because download_wiki_draws imports fetch_events INSIDE the function, making the
      monkeypatch a no-op. Third instance of that trap today; now a lesson.
- [x] B5 calendar completion + gate extensions. Completion keyed ONLY on a round-"F" row, so
      a feed that drops the final stranded the card at the top of the board forever — Iasi
      "live" with 3 alive for NINE days, Hamburg for two. Now: F-row OR calendar-over (event's
      scheduled end + 2d grace, AND no pending matchups), anchored on the DATA's max date so a
      frozen pipeline can't declare live events finished. Ships `finalRecorded: false` and a
      null champion — the card admits the champion is unknown instead of lying about being live.
      Gate: completed-without-final ADVISORY (honest, not a bug); no-champion stays BLOCKING
      when unexplained; duplicate-espnId BLOCKING — safe only because coalescing landed FIRST
      and the live board now has zero duplicate ids (it had one an hour ago; shipping this
      check before coalescing would have blocked the deploy).
      DELIBERATELY SKIPPED from the plan: the "live card not resolvable to the registry"
      advisory. It would fire every run on Bloomfield Hills, a Challenger legitimately outside
      ESPN's tracked set — permanent noise that reds the sentinel with no action attached.
- [x] B6 docs/lessons. The Track B lesson (display names are for display; joins use the
      event id; the name history IS the alias table) plus the four non-obvious things only
      building it revealed: a mid-title insertion defeats containment so resolution must
      REFUSE not guess; the id is a hint never a key; it was being lost in the very dedup step
      that proved two records were one event; and merging must happen BEFORE projection, since
      deduping cards afterwards only hid the fragment. AGENTS.md gotcha added so a future
      session reads it at start rather than rediscovering it.

## Track B review

Six commits. The identity layer now closes the largest bug family in this repo's history at
its root, and three separate live symptoms went away as a consequence: the DC Open's orphaned
draw, the "Washington Dc" 12-player fragment shipping beside the real 28-draw, and the
nine-day stuck-"live" class. Verified in production each time, not just in tests.

What this session actually taught, in one line: EVERY commit had a defect that a green test
suite did not catch. Live Wikipedia found A1's second parse bug; a card rebuild found A2's
tuple leaking into a surface field; the browser found A3's second projection renderer; reading
the production board found the id being dropped by dedup; a manual re-read found three silent
coalescing defects after the agent review returned an empty result that read exactly like a
pass; and wall-clock (8.65s vs 0.13s) found a test calling the live ESPN API. The failing-first
check caught two tests that could not fail. Rebuild the artefact; don't trust the suite alone.

Still open: the LLM alias proposer (offline, evidence-backed, PR-gated, with a deterministic
falsifier — blocked on the account spend limit), and promoting the three 772e5d4 advisories
plus the month-guess advisory to blocking once a full cycle proves them quiet.

## Review — alias proposer (2026-07-28)

Closes the loop the user named: "Can we use an LLM api with search to identify the issues
with the names mismatches etc? This cannot keep happening." Shape chosen: offline proposer
+ PR, so the runtime stays fully deterministic.

Shipped:
- `data/alias_proposer.py` — candidate scan (deterministic) -> Claude + web search
  (adjudicates only what it was handed) -> `falsify()` (deterministic) -> config patch on a
  branch -> human merge. `PLAYER_ALIASES`, `WIKI_TITLE_OVERRIDES`, `EVENT_TIER_FALLBACK`.
- `.github/workflows/propose-aliases.yml` (weekly, restore-only cache, no save) and
  `.github/scripts/open-alias-pr.sh` (creates, can never merge), the latter covered by
  `tests/test_workflow_alerts.py` per the AGENTS.md rule.
- `requirements-propose.txt` keeps `anthropic` out of the pinned pipeline install.
- 23 tests in `tests/test_alias_proposer.py`; each falsifier rule verified failing-first by
  reintroducing its defect (5 defects replayed, all caught).

Found while validating, and fixed in the same commit: **Diego Dedura shipped as two players**
— 36 matches as "Diego Dedura", 3 as "Diego Dedura-Palomero", with Stuttgart 2026-06-09
recorded under both spellings (one match, two rows, two Elo histories). The deterministic
scan surfaced it before any API call. Alias added; the duplicate row collapses.

Still open (deliberately):
- The proposer needs `ANTHROPIC_API_KEY` as a repo secret. Without it the job no-ops with a
  notice rather than failing — it is a convenience on a pipeline that is correct without it.
- One live candidate is genuinely ambiguous and left for the first real run to adjudicate:
  "Luis Felipe Miguel" (3 matches) vs "Luis Miguel" (4) — never played each other, so the
  scan asks rather than decides.
- Promote the three 772e5d4 advisories + the month-guess advisory to blocking once a full
  cycle proves them quiet.

## Round C — close the remaining hardening gaps (2026-07-28)

Evidence before editing: two successive production refreshes after B5 reported 0 output
problems on both tours, including the refresh on `1fa2fcb`; the pre-deploy gate, data-health
sentinel, and test workflow all passed. The placeholder and month-guess checks have already
been promoted under the newer tier-aware policy. Only `stuck 'live'` and completed-with-many-
alive retain their original blanket advisory exemptions. Also, a fresh deterministic proposer
dry-run finds 12 player-name candidates, not the single ambiguous pair recorded above; the
repository still has no `ANTHROPIC_API_KEY` secret.

- [ ] C1 gate promotion: make the two remaining board-quality checks tier-aware like the
      already-promoted placeholder/month checks — 500-and-above blocks; long-tail events keep
      the explicit advisory suffix. Update the classifier comments and fail-first tests for
      both severity branches.
- [ ] C2 identity adjudication: research only the 12 candidates emitted by the deterministic
      scan, retain source URLs/reasoning, run every proposed alias through `falsify()`, and add
      only proposals that both web evidence and the match record support. Pin accepted and
      rejected cases in proposer/config tests so the same spellings do not reappear silently.
- [ ] C3 real-artifact proof: rebuild the affected match/card artifacts, census which rows and
      identities collapse, then run the pre-deploy gate against the rebuild. A green unit suite
      alone is not acceptance.
- [ ] C4 verification: run the focused health/alias/workflow tests, then the full Python suite
      from `tennis_model/` with `PYTHONPATH=src`; run web tests only if regenerated mirrored
      output changes a web contract.
- [ ] C5 review: append the exact accepted/rejected aliases, artifact deltas, commands/results,
      and the still-external `ANTHROPIC_API_KEY` setup to this round. Do not add or expose a
      credential from the code change.

## OpenRouter migration — alias proposer (2026-07-28)

The user supplied an OpenRouter credential to unblock the offline identity adjudicator and
asked to use OpenRouter instead of a direct Anthropic key. The credential itself must never
enter the worktree, logs, tests, or workflow source; because it was pasted into chat, rotate it
before configuring the durable secret.

- [ ] Replace the Anthropic SDK transport in `data/alias_proposer.py` with OpenRouter's
      OpenAI-compatible chat-completions API and its current `openrouter:web_search` server
      tool, while keeping candidate generation, `falsify()`, and PR review unchanged.
- [ ] Rename the workflow contract to `OPENROUTER_API_KEY`, remove the now-unused Anthropic
      dependency, and update project documentation that describes the quarantined client.
- [ ] Add fail-first transport/workflow tests that pin the endpoint, bearer authentication,
      search-tool budget, response parsing, and absence of credentials from tracked files.
- [ ] Run the focused proposer/workflow tests, then the full Python suite from
      `tennis_model/` with `PYTHONPATH=src`; append exact results and any residual setup.

## Review — OpenRouter migration (2026-07-28)

Implemented without copying the supplied credential into the filesystem or another command:

- `ask_openrouter()` now posts to OpenRouter's OpenAI-compatible chat-completions endpoint,
  selects `anthropic/claude-opus-5`, retains high reasoning effort, and exposes only the
  `openrouter:web_search` server tool (8 calls / 24 cumulative results). The deterministic
  candidate scan, `falsify()`, and human-reviewed PR boundary are unchanged.
- The weekly workflow now reads only `secrets.OPENROUTER_API_KEY`. The transport is standard
  library HTTP, so `anthropic` was removed from `requirements-propose.txt` and no LLM client
  entered the pinned pipeline environment.
- Added fail-first tests for the exact endpoint, bearer header, model, prompt roles, reasoning
  config, search limits, refusal handling, workflow secret name, and absence of an OpenRouter
  key prefix from tracked proposer files. The three focused tests failed before implementation
  and passed afterwards.
- Verification: `PYTHONPATH=src uv run python -m pytest -q tests/test_alias_proposer.py
  tests/test_workflow_alerts.py` -> 67 passed; `PYTHONPATH=src uv run python -m pytest -q`
  -> 447 passed; `git diff --check` -> clean. Reconciled against current tip `1fa2fcb`.

Residual external setup: `gh secret list --app actions` shows only
`FIREBASE_SERVICE_ACCOUNT`; `OPENROUTER_API_KEY` is not configured. No live/billable model call
was made with the key pasted into chat. Rotate that exposed key, then store the replacement as
the repository Actions secret `OPENROUTER_API_KEY` before dispatching `propose-aliases`.

## OpenRouter cost reduction (2026-07-28)

User approved the recommended model change after reviewing the proposer's bounded role and
current OpenRouter prices.

- [ ] Switch only the adjudicator from `anthropic/claude-opus-5` at high reasoning to
      `openai/gpt-5.4-mini` at medium reasoning; retain the 8-search / 24-result ceilings and
      every deterministic and human-review gate.
- [ ] Update the transport contract test, run the focused proposer/workflow tests and full
      Python suite, and append exact verification results.

## Review — OpenRouter cost reduction (2026-07-28)

- `MODEL` is now `openai/gpt-5.4-mini`; reasoning is `medium`. Search remains capped at 8
  uses / 24 cumulative results, and no scan, falsifier, patch, workflow, or PR-review behavior
  changed.
- Verification: focused proposer/workflow suite -> 67 passed; full Python suite -> 447 passed.
  A live no-search smoke call through OpenRouter using the configured model and medium
  reasoning returned exactly `OK` via OpenAI: 11 prompt + 15 completion tokens (8 reasoning),
  `$0.00007575`, no API error.

## Round D — keep concurrent tournaments visible (2026-07-28)

Production diagnosis: commit `7afd58f` correctly promoted a live 500-level event to the
round-by-round hero, but reused the Slam-only page composition that collapses every other
tournament. The ATP 250 is present in `tournaments.json`; the page hides it behind “show other
recent events” solely because the ATP 500 was selected as the hero.

- [ ] D1 add a fail-first web invariant: selecting a featured event must leave every other
      live/upcoming tournament in the initially visible set; only completed events may collapse.
- [ ] D2 keep the ATP 500 round-by-round hero, render concurrent live/upcoming ATP 250 cards
      immediately below it, and reserve the disclosure toggle for completed recent events.
- [ ] D3 run the focused web test, full web suite, and lint; then verify in the browser against
      an artifact containing a simultaneous ATP 500 and ATP 250.
- [ ] D4 record the visibility/composition lesson and append exact verification results here.

### Round D plan correction

User clarification after the first plan: the single-event hero is reserved for Grand Slams,
Tour Finals/Olympics, and Masters 1000. A 500-and-below week uses the multi-event card layout,
ordered by tournament prestige (500 before 250 before lower tiers), so no concurrent active
event disappears merely because a more important one is present.

### Round D implementation decision

The event hierarchy is one shared ordering: Grand Slam → Tour Finals → Masters 1000/Olympics
→ 500 → 250 → Cup/125/other. Apply it in two presentation modes:

- **Focused weeks (1000-and-above):** the highest-ranked live/upcoming event owns the full
  round-by-round hero. A compact `View other events (N)` disclosure sits beside the page intro,
  not below the long hero table, and expands every remaining event in the same prestige order.
- **Multi-event weeks (500-and-below):** no event takes the single-event hero. Every active
  tournament card is visible immediately, ordered by prestige; completed recent events follow
  after the active cards rather than displacing or hiding them.
- **Invariant:** selecting a hero changes emphasis, never membership. Every event in the payload
  is either immediately rendered or named by the above-the-fold disclosure, with its count.
- **Test shape:** centralize the hierarchy/view partition in a pure helper returning
  `{ hero, primary, other }`; unit-test the simultaneous 500+250 case, a 1000+500+250 case,
  equal-tier stability, and completed-event handling. The page renders that result instead of
  independently reimplementing selection, sorting, and disclosure.

## Round D review

Implemented the two-mode event hierarchy without touching the running model/data work:

- `HERO_MAX_TIER_RANK` now stops at rank 2 (Grand Slam / Finals / Masters 1000 / Olympics).
  A 500-and-below payload therefore stays in the complete card grid.
- `byTournamentPrestige()` and `tournamentView()` are the single selection/order/membership
  contract. A focused week returns one hero plus every remaining event; a non-focused week
  returns the whole grid, ordered 500 before 250 before lower tiers.
- Focused weeks expose a native `View other events (N)` disclosure immediately below the page
  intro, before the long hero table. Opening it renders the existing full event cards.
- Fail-first proof: the focused UI test failed in 2 places before the cutoff changed because
  `heroEvent()` still selected the ATP 500. After implementation, the focused file passes 20/20.
- Verification: full web suite 178/178; `npx tsc --noEmit` clean; ESLint 0 errors (13 existing
  `set-state-in-effect`/unused-disable warnings outside the touched code); optimized Next.js
  production build compiled and prerendered all 21 routes. Browser, real local ATP payload: DC
  Open ATP 500 rendered first, followed by both live ATP 250s and every other event. Browser,
  temporary local Masters fixture: the 1000 owned the hero, the closed control read
  `View other events (7)`, and opening it revealed all seven remaining events in prestige order.
  The temporary fixture is absent from the final generated artifact.

## Review — Round C hardening (2026-07-28)

Completed alongside the separately committed Round D web work at current tip `d754b62`:

- The stuck-live and completed-with-many-alive board checks now follow the existing tier-aware
  gate contract: 500-and-above blocks; lower tiers retain a named advisory suffix. Fail-first
  tests cover both severity branches.
- Twelve aliases survived both source research and `falsify()`: Gabi Adrian Boitan → Adrian
  Boitan; Luis Guto Miguel and Luis Miguel → Guto Miguel; Igor Ribeiro Marcondes → Igor
  Marcondes; Joel Josef Schwaerzler → Joel Schwaerzler; Caijsa Wilda Hennemann → Caijsa
  Hennemann; Gabriela Andrea Knutson → Gabriela Knutson; Ilinca Dalina Amariei → Ilinca
  Amariei; Irene Burillo Escorihuela → Irene Burillo; Maria Camila Torres Murcia → Maria
  Torres Murcia; Miriam Bianca Bulgaru → Miriam Bulgaru; and Tiantsoa Sarah Rakotomanga
  Rajaonah → Tiantsoa Rakotomanga Rajaonah. A fresh real-data dry-run reports no open
  identities.
- Two tempting subset-name merges were rejected before model adjudication: Joao Silva (ATP
  `S0Y4`) is not Joao Lucas Reis Da Silva (`R0A7`), and Luis Felipe Miguel (`M0OT`) is not
  Luis/Guto Miguel (`M0WY`). The proposer now treats stable alphanumeric ids as refuting
  evidence, keeps source-local numeric WTA ids non-authoritative, carries evidence per tour,
  and resolves three-spelling id clusters directly to one terminal canonical.
- Real archive census: ATP changed 283,565 → 283,561 match rows and 8,154 → 8,149 identities;
  WTA changed 128,762 → 128,737 rows and 5,370 → 5,363 identities. The full local predictor
  rebuild and a production-equivalent live/draw/rankings refresh completed for both tours.
  The pre-deploy gate then passed with zero blockers (one intended below-500 Bloomfield Hills
  stale-live advisory remained).
- A predictor now records the alias-table revision. A push-triggered quick refresh therefore
  promotes itself to a full rebuild after an identity change instead of pairing canonicalized
  matches with cached split rating states.
- Verification: focused health/alias/name/pipeline/workflow suite → 163 passed; the full shared
  worktree → 447 passed; and an isolated worktree built from the Round C commit index → 445
  passed. `git diff --check` was clean. Mirrored JSON changed only as generated data and
  introduced no new web contract, so no additional web run was required beyond Round D's
  independently recorded 178-test/build/browser verification.
- Credential setup moved concurrently from Anthropic to OpenRouter; it remains external to
  this deterministic/runtime change. No credential was added to the repository.

## Post-review identity and OpenRouter publish reconciliation (2026-07-28)

- A final live refresh introduced one candidate after Round C's census: ESPN wrote ATP player
  `W0BH` as `Chak Lam Coleman Wong` at Los Cabos while 180+ archive rows use `Coleman Wong`.
  ATP's own profile URL and Hong Kong media notes join the full and short names to W0BH. Added
  the terminal alias `chak lam coleman wong -> Coleman Wong`; its regression test failed before
  the config entry and passed after it.
- Final archive census against `1fa2fcb`: ATP 283,565 -> 283,561 rows and 8,154 -> 8,148
  identities; WTA 128,762 -> 128,737 rows and 5,370 -> 5,363 identities. The current 180-day
  proposer scan is empty on both tours after all 13 aliases.
- A production-equivalent `pipeline --tour all --quick` detected both cached predictors as
  stale, rebuilt both production combiners, regenerated exports/logs/ledgers, and completed.
  `health --gate` passed with zero blockers; Bloomfield Hills retained the deliberately
  non-blocking below-500 stale-live advisory recorded in Round C.
- The proposer now uses OpenRouter's `openai/gpt-5.4-mini` at medium reasoning with the existing
  8-search / 24-result ceilings. `OPENROUTER_API_KEY` is configured as an external GitHub
  Actions secret; no credential value is tracked.
- Final pre-publish verification on `3e75263`: Python 448 passed; web 178 passed; ESLint 0
  errors / 13 existing warnings; production build compiled and prerendered all 21 routes;
  `git diff --check` clean.

## Follow-up — bound quick-mode predictor rebuilds

- [ ] When `build_tour_quick()` detects a stale predictor and falls back to `build_tour()`,
  preserve the quick-refresh Kalshi ledger/time limits instead of inheriting the full-build
  allowance. Add a regression test for the stale-predictor path and compare deploy duration
  without weakening the alias-revision rebuild or either production health gate.

## Round E — guarantee every begun tournament reaches the site

Definition: an event has **begun** when independent source evidence shows either (a) at least
one real knockout result, or (b) a scheduled/in-progress real-player matchup whose date is no
later than the build date. ESPN calendar dates alone and all-TBD listings remain advisory until
one of those facts exists. Identity is `espnId` first; an id-less event is matched only by date
overlap plus shared real players, never by name similarity.

- [x] E1 add fail-first producer and health tests for a versioned `event_coverage.json` manifest:
      enumerate begun events independently from results + scheduled matchup evidence, attach
      stable evidence-backed keys, and require every expected key to occur exactly once in
      `tournaments.json`. A projector skip must block the pre-upload gate even when every other
      card is valid; future/calendar-only records must not false-positive.
- [x] E2 generate and mirror that manifest on full and quick builds, stamp the same explicit
      coverage key onto each tournament card, and make coverage loss impossible to hide behind
      a caught projection exception. Keep the existing card-validity checks; coverage is a new
      set-completeness contract, not a replacement for them.
- [x] E3 extend the web membership contract so `tournamentView()` is proven to preserve every
      payload event across `{hero, grid, other}`, then publish each tour's expected/shipped
      active coverage keys in `health.json` for serving-side verification.
- [x] E4 extend `verify-deploy.mjs` to fetch live tournament payloads and compare their exact
      coverage-key membership with the freshly deployed `health.json`, retrying through CDN
      propagation. Add pure helper tests and keep the deploy-health alert path unchanged.
- [x] E5 broaden the weekly search proposer with contained `missing_event` / `event_identity`
      questions sourced only from deterministic coverage failures. Search may explain an
      unresolved identity and cite sources, but cannot invent the expected set, mutate runtime
      data, or bypass the existing human-reviewed PR boundary.
- [x] E6 run focused fail-first tests, the full Python and web suites, lint/build, a real-data
      quick export plus `health --gate`, and reconcile the plan against current `git log` before
      recording a review section here.

## Round E plan — keep stale quick rebuilds within the quick Kalshi envelope

- [ ] Add a fail-first pipeline regression using an alias-stale predictor. Exercise the real
  `build_tour_quick()` → full-rebuild path with training/export stubbed, and prove both that the
  rebuilt predictor is saved and that Kalshi receives the 180-second / 4-day quick limits.
- [ ] Thread a keyword-only Kalshi history limit through `build_tour()` and set it only from the
  stale quick fallback; keep ordinary full builds on the 1200-second historical allowance and
  update the stale-path log so aliases are named as part of the predictor contract.
- [ ] Run the focused pipeline/Kalshi/health/workflow tests, the full Python suite, and the
  post-deploy verifier unit test. Do not alter the alias-revision guard, pre-deploy integrity
  gate, or post-deploy live-serving verifier.
- [ ] Record the timing comparison in this round's review: historical stale-rebuild Actions run
  `30407043892` took 22m03s end to end, while recent ordinary quick runs are roughly 7–8 minutes;
  the code change reduces the two-tour Kalshi allowance on that path from 40 to 6 minutes. Treat
  an actual post-change production duration as requiring a deliberate push to `master`.

## Follow-up review — bounded stale quick rebuilds (2026-07-28)

- The fail-first alias-stale regression completed the full ratings/training/save fallback but
  captured the wrong benchmark contract: a 1200-second Kalshi allowance and `recent_days=None`.
  After the routing change it captures the quick caller's 180-second / 4-day limits, while a
  second assertion pins an ordinary full build to the original 1200-second / unbounded-history
  behavior.
- `build_tour()` now accepts one keyword-only `kalshi_recent_days` input and forwards it only to
  `_kalshi()`. The stale quick branch supplies `QUICK_KALSHI_DAYS`; its ratings walk, combiner
  retrain, predictor save, exports, alias-revision guard, and ledger requoting remain unchanged.
  The stale-path diagnostic now names player aliases alongside schema and FeatureParams drift.
- Actions evidence: pre-change quick run `30407043892` confirmed both ATP and WTA stale-predictor
  rebuilds. Its quick step took 19m53s and the job 21m53s (22m03s trigger-to-completion). Ordinary
  quick run `30404025779` took 5m02s for the quick step and 7m26s for the job. The 14m51s step
  delta includes the required two-tour model rebuild, so it is not attributed wholly to Kalshi;
  the deterministic comparison is the two-tour Kalshi allowance dropping from 40 to 6 minutes.
  No production push was made, so an actual post-change stale-rebuild deploy duration remains
  deliberately unmeasured.
- Fail-first proof: the new regression failed with `budgets == [1200]` before the code change and
  passed with `[180]` after it. Verification: focused pipeline/Kalshi/health/workflow suite 137
  passed; post-deploy verifier 15 passed; direct and pytest pipeline-guard runs 5/5 each; current
  shared-worktree Python suite 459 passed; Ruff clean on both touched Python files; and
  `git diff --check` clean. Neither production health gate was changed.

## Round E review — begun-event coverage (2026-07-28)

- `event_coverage.json` now enumerates begun events independently from real knockout results
  and scheduled/in-progress real-player matchups. Stable ESPN ids own identity; an id-less
  cross-source join requires overlapping source-observed dates plus the same real matchup.
  Calendar-only and future-only records do not enter the blocking expected set.
- Every tournament card carries a `coverageKey`. A stable ESPN event is no longer rejected by
  the top-100 heuristic, the arbitrary 14-event projector cap is gone, and a still-unprojectable
  begun event receives an honest `coverageOnly` / `drawStatus=unavailable` shell rather than
  disappearing. Current real data needed no shells: all 8 ATP and 14 WTA expected events built
  full cards, including previously absent WTA Vancouver and Warsaw.
- The pre-upload gate requires every expected key exactly once and publishes expected/shipped
  membership in `health.json`. The web partition test proves `{hero, grid, other}` preserves
  every key. The live verifier fetches both production tournament payloads and retries until
  their exact membership matches the freshly deployed health report.
- The weekly proposer now turns deterministic known-id gaps into `missing_event` questions and
  id-less gaps into `event_identity` questions. Answers are pinned to the asked name/key, a
  known ESPN id cannot be changed, cited sources are mandatory, and only a parser-verified
  Wikipedia override can become a config diff; diagnosis-only answers remain audit artifacts.
- Fail-first proof: the new Python module was absent and the JS coverage helper undefined before
  implementation. Final verification: Python 459 passed; web 181 passed; TypeScript clean;
  ESLint 0 errors / 13 existing warnings; production build rendered all 21 routes; real quick
  pipeline + direct re-export completed; `health --gate` passed with only the pre-existing
  below-500 Bloomfield Hills stale-live advisory. Local browser verification rendered all ATP
  cards and all 14 WTA cards—including Axeria and Odlum—with no console warnings/errors.

## Round F — preserve settled finals in coverage fallback cards

- [x] Add a production-shaped regression where a completed result group contains a final but
  the projector emits no card; require the independent manifest and fallback card to preserve
  the champion/runner-up instead of converting known settled evidence into an unknown final.
- [x] Carry one non-conflicting final result through candidate merging and render a completed
  fallback as a recorded final with honest copy when its historical title projection/draw field
  remains unavailable. Do not weaken the existing completed-event health invariant.
- [x] Run focused producer/health/web tests, full Python and web verification, commit, push, and
  require both the pre-deploy gate and post-deploy live membership verifier to pass; inspect the
  data-health reporter before declaring the deployment green.

## Round F review — settled fallback finals (2026-07-28)

- The first production run (`30411789813`) proved the new membership contract end to end: its
  pre-deploy coverage gate, Firebase upload, and live exact-membership verifier all passed. It
  then correctly ended red in `Report data health`, because the presence-only fallback had
  discarded final results already present in the result rows for ATP/WTA Wimbledon and WTA
  Nordea. Issue #13 named all three missing champions.
- `event_coverage.py` now carries one non-conflicting final winner/runner-up through result
  candidates and identity merging. A completed fallback publishes that settled result with
  `drawStatus=final`; conflicting finals remain unknown for the unchanged health invariant to
  report. The UI says `final recorded` and `Projection unavailable` rather than implying that a
  completed draw is still pending or that a model favourite existed.
- Fail-first proof: the production-shaped final-only regression failed on missing
  `finalRecorded` before the fix. Verification after it: 460 Python tests and 183 web tests
  passed; Ruff and TypeScript were clean; ESLint had 0 errors / 13 existing warnings; and the
  21-route production build passed. Real cached evidence resolved Sinner–Zverev, Noskova–Muchova,
  and Badosa–Waltert before deployment.
- Corrective commit `42dc9be` deployed in run `30412570761` (7m37s). Quick regeneration,
  pre-deploy integrity, data health, Firebase deployment, live Firebase verification, both
  reporters, and cache persistence all passed. The public `health.json` reports `ok: true`, and
  the three fallback cards now expose their recorded champions while exact ATP/WTA expected-key
  membership remains intact.

## Round G — repair Wimbledon cards and restore reach odds on top cards

- [ ] Add failing tournament regressions for the production shapes: refuse an id-less
  Wimbledon/Nordea coalesce without a shared main-draw match, preserve the Bad Homburg
  shared-match merge and same-id merge, discard a player's duplicate match within one knockout
  round, return a factual completed Grand Slam card from an unseatable field with hard draw size
  128, and keep live/upcoming oversized frontiers fatal.
- [ ] Harden tournament construction in the producer: require at least one shared knockout
  match pair for id-less event coalescing, deduplicate impossible second appearances within a
  knockout round, add an extensible known-draw-size authority for Grand Slams, and degrade only
  completed unseatable fields to an empty-projection `fieldUnreliable` record rather than
  throwing or creating a shell.
- [ ] Canonicalize `Soon Woo Kwon` to `Soonwoo Kwon` and `Zheng Qinwen` to `Qinwen Zheng`, add
  walk-level regressions, and diagnose why the deterministic alias proposer omitted the Kwon
  split; keep proposer changes bounded by its candidate/falsifier contract.
- [ ] Add failing coverage-shell regressions, then carry archive tier, surface provenance, and
  best-of evidence through candidate merging. Resolve shells across every registered event name,
  preserve honest generic/null fields where evidence is absent, and use ATP Grand Slam best-of-5
  versus WTA Grand Slam best-of-3 without pretending a shell has a draw.
- [ ] Rebuild real ATP/WTA cards with the Wikipedia draw loader forced empty and prove both
  Wimbledons ship as real `Grand Slam / Grass / 128` cards (ATP best-of-5, WTA best-of-3) while
  Nordea remains separate. Mirror regenerated tournament data into the web payloads before
  introducing new blocking checks.
- [ ] Add failing gate regressions and then enforce canonical non-null surfaces, tier-correct
  best-of, completed generic-tier reporting, non-downgraded `coverageOnly` defects, and exact
  `shellKeys` parity between the coverage manifest and shipped shells. Extend the workflow alert
  tests for live-cache snapshot coverage and keep every new failure class in the pre-upload gate.
- [ ] Make Wikipedia draw retention recoverable: include both tours' `raw/<tour>/live` trees in
  release snapshots and trip detection, and best-effort backfill registry-known events missing
  from `wiki_draws.json` while they remain inside the 40-day window.
- [ ] Add a failing web rendering regression, extract the shared reach strip from `SlamHero`,
  and render it on every non-empty 500+ card without changing `HERO_MAX_TIER_RANK = 2` or the
  existing hero/concurrency membership behavior.
- [ ] Land producer and identity/cache changes in reviewable ordered commits with focused tests,
  full Python verification, Ruff, web tests, TypeScript, lint, and a production build green.
  Push deliberately, observe one scheduled producer run and its gate lines, and only then land
  and deploy the new blocking gate invariants.
- [ ] Verify the final production deploy with the pre-upload integrity gate, post-deploy live
  membership verifier, public data-health report, and direct inspection of Wimbledon/Nordea and
  reach columns. Append a Round G review plus lessons for shared-match event identity and
  separating card content from hero layout.

## Round G deployment addendum — current-year ATP stats on quick runs

- [ ] Add a failing quick-pipeline regression proving the current-year ATP stats source is
  refreshed before export, while WTA keeps its rate-limited live-only quick path.
- [ ] Refresh that ATP source in the quick producer, verify the real Kitzbuhel final becomes
  decided from the same stale-cache shape as CI, and keep the completed-bracket gate blocking.
- [ ] Push the producer correction first, require a scheduled quick run and its existing gate
  to pass, then land the prepared Round G gate and reach-card commits.

## Round G deployment addendum — incomplete draw caches

- [ ] Add a failing-first cache test proving a 28-player draw with fewer than 28 real entrants
  is not settled even when every populated slot is a real name.
- [ ] Make cached-draw settlement validate the recorded entrant count, so unresolved null
  qualifier slots are re-fetched while legitimate byes remain valid.
- [ ] Re-run the real quick build and strict gate, then stage this producer correction before
  the pending gate and UI changes.
- [ ] Withhold an ordered bracket from a completed card when its result fold cannot decide the
  final; keep the factual tournament card and the existing completed-bracket gate unchanged.

## Round G review — Wimbledon field repair and reach cards (2026-07-29)

- Producer fixes landed first in `35f6bc2`, `1751697`, `8ee9b22`, `ce34504`, `427fc32`, and
  `6914380`. Grand Slams now use an authoritative 128 draw; an id-less event merge requires a
  shared real match pair; one player cannot occupy two matches in one knockout round; known
  Kwon/Zheng aliases are canonical; incomplete draw caches are re-fetched; and an
  unreconcilable completed bracket is withheld without erasing the factual tournament card.
  Live oversized fields remain fatal, while a completed unseatable field degrades to an honest
  empty-projection record.
- The producer push run `30421865323` passed quick regeneration, the existing pre-deploy gate,
  data health, build, Firebase deploy, and all 8 live checks with exact membership for 22 begun
  events. Scheduled full run `30429268554` then passed the full retrain, pre-deploy gate, data
  health, build, deploy, and 8/8 live verification before ending red only at the final source
  sentinel: WTA `/tournaments/` was unreachable after five retries, so cached WTA stats were
  retained as designed. Its forecast-ledger commit was reconciled as `2cbe3ec` before the next
  rollout stage.
- The stricter gate landed separately in `1f50a46`. It blocks missing/noncanonical surfaces,
  tier-wrong best-of values, completed generic tiers, downgraded `coverageOnly` defects, and
  `shellKeys` parity mismatches while reporting one problem per actual shell. Focused health
  verification passed 87 tests plus Ruff; deployment `30432522121` passed regeneration, both
  health gates, build, deploy, live verification, and both reporters.
- Shared reach-card rendering landed separately in `df6de1c`. `ReachRow`/`ReachStrip` now serve
  the Slam hero and every non-empty 500+ card, while `HERO_MAX_TIER_RANK = 2` still controls
  hero layout and 250/lower cards retain title-odds bars. The renderer regression passed 24
  focused tests; the full verification before rollout was 476 Python tests and 184 web tests,
  with Ruff clean, ESLint at 0 errors / 13 existing warnings, and the production build green.
  Deployment `30433065154` passed the strengthened gate, data health, build, Firebase deploy,
  and live verification.
- Final production inspection showed exactly one ATP and one WTA Wimbledon card. Both are
  `Grand Slam / Grass / 128 / completed / final / coverageOnly=false`; ATP is best-of-5 with
  champion Jannik Sinner and WTA is best-of-3 with champion Linda Noskova. Nordea Open remains
  a separate `WTA 250 / Clay / 32` final with champion Paula Badosa. Public health was green at
  `2026-07-29T07:55:09Z`. Browser inspection confirmed R16/QF/SF/F/Win columns on both ATP and
  WTA 500 cards and compact odds on 250 cards.

## Round H — prioritize current tournaments on the home board

- Add a failing ordering regression proving live and upcoming tournaments render before
  completed tournaments, while prestige still orders events within the same status group.
- Update the shared tournament ordering helper without changing hero eligibility or dropping
  any event from the `{hero, grid, other}` partition.
- Run focused and full web verification, deploy deliberately, inspect both ATP and WTA boards,
  and append a review with the production run evidence.

## Round H review — current tournaments first (2026-07-29)

- The stale ordering came from one shared helper sorting only by tier, so a completed Grand
  Slam outranked every live 500/250 even after its 48-hour hero linger had expired. Commit
  `54b5b35` replaces that with `live → upcoming → completed`, then applies prestige within
  each status; stable sorting still preserves producer recency for equal-status, equal-tier
  events. Hero eligibility and `{hero, grid, other}` membership are unchanged.
- Fail-first proof: the mixed-status regression received `Wimbledon, Done Thousand, Upcoming
  Five Hundred, Live Five Hundred, Live Two Fifty` before the fix and the intended current-first
  order afterward. Final verification was 185 web tests, ESLint at 0 errors / 13 existing
  warnings, a clean diff check, and a successful 21-page production build.
- Deployment `30450071486` passed quick regeneration, the strengthened pre-deploy gate, data
  health, build, Firebase deployment, live verification, both reporters, and cache persistence.
  Live browser inspection showed ATP beginning with DC Open and Mifel before Wimbledon, and
  WTA beginning with DC Open, Memphis, Axeria, and Odlum Brown VanOpen before Wimbledon.

## Round I — show reach odds for every active tournament

- Add a failing renderer regression proving a live ATP 250 with reach probabilities shows the
  same round-by-round columns as a live ATP 500.
- Replace the card's prestige cutoff with a lifecycle-and-data rule, while retaining compact
  title-odds bars for completed cards and honest empty-projection handling.
- Run the focused renderer regression and the full web test suite, then append a review with
  the verification evidence.
- Hero-week exception: keep the Grand Slam/1000 as the full-width hero, then render every
  concurrent lower-tier event underneath in the compact title-odds card rather than hiding it
  in an above-hero disclosure.

## Round I review — active reach cards and hero-week support (2026-07-29)

- `Card` now shows round-by-round reach columns for every live/upcoming event with meaningful
  reach data, independent of tier. Completed events and explicitly compact cards retain the
  title-odds bars, so a Grand Slam/1000 hero remains dominant while all concurrent events are
  visible in an `Also on tour` grid immediately beneath it.
- Fail-first proof: the live ATP 250 renderer still omitted `R16` before the change. The focused
  suite now pins both a detailed active ATP 250 and the compact hero-week exception.
- Verification passed 186 web tests, production build, and ESLint with 0 errors / 13 existing
  warnings. Local browser inspection of real data confirmed equal 588px side-by-side DC Open
  and Mifel cards, reach tables on both, Mifel's incomplete-draw warning intact, and no console
  errors.

## Round K — faster, gated production deployment (completed 2026-07-29)

- [x] Move historical Kalshi quote repair off the hourly critical path, share one strict
  75-second quick-run budget across both tours, and emit stage timings.
- [x] Reuse each tour's ESPN event sweep across live results and complete-draw acquisition
  while preserving independent best-effort fallback.
- [x] Skip documentation-only deploys; add a safely gated web-only path, required master-push
  tests, Python/npm/Next caches, and immutable Firebase tooling.
- [x] Upgrade Next.js and its lint config to 16.2.12, patch vulnerable production transitive
  dependencies, and retain both the pre-upload and live-serving verification gates.
- [x] Verify the combined draw/deploy worktree: 494 Python tests, Ruff, 186 web tests,
  TypeScript, workflow/shell checks, clean `npm ci`, zero production audit findings, ESLint
  with 0 errors / 13 existing warnings, production build, and `git diff --check`.

## Round L review — keep unsafe Kalshi prices out of the scorecard (2026-07-29)

- The failure was an hourly resurrection, not a bad gate: daily repair had degraded unsafe
  candles to `price_kind=none`, then `requote=False` rebuilt them from the occurrence-time
  snapshot cache. Every ledger upsert now sanitizes the final post-freeze merge without network
  I/O, including retained rows whose snapshots disappeared; valid morning quotes survive and a
  later daily re-quote can still upgrade a neutralized row.
- Cached regeneration neutralized 38 unsafe candles (the 36 scoreable gate failures plus two
  rows without model prices) and rebuilt the report with 1,338 valid scored matches. Both the
  complete pre-upload gate and strict source/output health pass with zero output problems.
- Verification passed 497 Python tests, Ruff, 187 web tests, TypeScript, shell/workflow checks,
  `npm ci`, a zero-finding production dependency audit, ESLint with 0 errors / 13 existing
  warnings, the 21-page production build, and `git diff --check`.

## Round M — show a meaningful tournament field by default (completed 2026-07-30)

- [x] Add renderer regressions for detailed and compact tournament cards proving players 1–16
  are visible by default, player 17 stays behind `show all`, and an event with fewer than 16
  available players renders all of them without an expansion control.
- [x] Replace the card-only five-player cutoff with the same shared 16-player default already
  used by the hero. Preserve sorting, expansion/collapse behavior, compact hero-week hierarchy,
  and naturally shorter cards once fewer than 16 players remain.
- [x] Run focused and full web tests, TypeScript, ESLint, production build, and rendered desktop
  inspection of the real ATP board; append the review. Do not push or deploy without separate
  explicit instruction.

## Round M review — show a meaningful tournament field by default (2026-07-30)

- Hero, detailed, and compact tournament views now share a 16-player default. Events with fewer
  than 16 remaining players show their full field; larger fields retain `show all` / `show less`.
- Fail-first renderer coverage proved the old five-player card cutoff, then passed for both card
  variants at the 16/17 boundary and for a seven-player remaining field without an expansion
  control.
- Verification passed 189 web tests, TypeScript, the 21-page production build, and ESLint with
  0 errors / 13 existing warnings. Rendered ATP inspection showed all 12 DC players and all 15
  Mifel players, while a larger Wimbledon card showed 16 players plus its expansion control.
- Publication was performed only after separate explicit authorization: commit to `master`, push,
  and production deployment through the guarded refresh workflow.

## Round N — honest player links and profile style radar

- [x] Add fail-first regressions proving a player name without a `profiles.json` entry renders as
  plain text, an invalid `?p=` profile URL never substitutes the tour's top player, and a valid
  profile produces a one-player 13-axis percentile radar.
- [x] Gate player and matchup links on the actual profile roster across shared match cards and
  every other player-name link surface; keep unavailable names visible but non-interactive.
- [x] Reuse the comparison page's radar axes, percentile scaling, labels, and chart component in
  the player dossier, with a clear single-player legend and graceful handling of missing metrics.
- [x] Run focused and full web tests, TypeScript, ESLint, production build, and rendered browser
  checks for Cruz Hewitt plus Jessica Pegula; append a review. Do not push or deploy without
  separate explicit instruction.

## Round N review — honest player links and profile style radar (2026-07-30)

- Match cards now receive the exported profile roster and fail closed per name: unavailable
  qualifiers remain visible as plain text, while valid dossiers and two-player style matchups
  remain linked. Player-page opponents use the same rule, and an invalid explicit `?p=` now shows
  an honest not-found panel instead of silently substituting the tour's top profile.
- Individual dossiers reuse the comparison surface's 13 axes, tour-wide percentile scalers, and
  animated radar component. Production inspection confirmed Jessica Pegula's labeled 460px radar
  without horizontal overflow; Cruz Hewitt remained visible on the ATP schedule with zero profile
  or matchup links, and his direct profile URL contained neither Sinner nor a radar.
- Fail-first coverage now pins selection, link, radar, and live-contract behavior. Final local
  verification passed 193 web tests, TypeScript, the 21-page production build, `git diff --check`,
  and ESLint with 0 errors / 13 existing warnings.
- Commits `b8af8bb` and `9668920` were pushed to `master`. Production run `30514234317` passed the
  web-only deploy path, both integrity/data-health gates, Firebase deployment, and all 9 live
  serving checks, including the new `fail-closed-links+single-radar-v1` profile contract.

## Round O — profile links in tournament cards

- [x] Add fail-first renderer coverage proving detailed reach tables and compact title-odds cards
  link players in the exported profile roster while leaving unavailable names as plain text.
- [x] Pass the profile roster through the tournament hero, grid, and concurrent-event renderers,
  and reuse one fail-closed player-name primitive without changing card sorting or expansion.
- [x] Run focused and full web verification plus rendered checks of the WTA DC Open and Memphis
  cards; append a review. Do not push or deploy without separate explicit instruction.

### Review

- Added one shared `PlayerProfileLink` primitive and used it for tournament champions, model
  favourites, focused-event projections, detailed tournament tables, compact title-odds cards,
  and existing matchup cards. Names outside `players.json` remain plain text.
- Added a fail-first server-renderer regression covering both detailed and compact cards. Focused
  tests passed (32), followed by all 194 web tests, TypeScript, production build, and lint with
  zero errors (13 pre-existing warnings).
- Rendered WTA verification found profile links for all 12 Washington DC rows and the six Memphis
  players with dossiers. The six Memphis players without dossiers (including Ma YeXin and Kristina
  Liutova) remained plain text; there were no console errors or horizontal overflow.
- Reconciled against `git log -5`: the prior profile-link and radar repair was the latest shipped
  work before this round. Publication was explicitly approved after implementation verification.

## Round P — restore deployments for unresolved official qualifier slots

- [x] Add a fail-first official-draw regression reproducing Toronto's 96-entrant/128-slot
  provider artifact with repeated unresolved `Qualifier` seats, proving every occupied seat
  remains distinct and the draw population cannot collapse downstream.
- [x] Normalize unresolved first-party draw placeholders to unique numbered slots at ingestion,
  matching the existing Wikipedia draw contract while preserving true byes, bracket order,
  seeds, and provider evidence.
- [x] Run focused official-draw, tournament-projection, bracket, and health-gate tests, then the
  full Python suite; reconcile against the latest git history and append the review. Publish the
  fix and verify a successful guarded refresh only with explicit approval.

### Review

- Reproduced Toronto's provider state as an early 96-entrant/128-slot draw: 80 named players,
  16 repeated bare `Qualifier` labels, and 32 true byes. The fail-first regression proved the
  16 seats collapsed to one identity before the parser repair.
- Official draw ingestion now turns unresolved first-party labels into unique `Qualifier 1..N`
  seat identities while preserving null byes, order, seed ownership, draw size, and evidence.
  This matches the existing Wikipedia draw contract and prevents set-backed field collapse.
- Focused verification passed 132 official-draw, tournament-status, bracket, and health tests;
  the full Python suite passed all 498 tests, and `git diff --check` passed. Reconciled against
  `git log -5`; the intervening remote commits only updated evaluation logs.
- Commit `4b114d0` was pushed to `master` after explicit approval. Production run `30665029676`
  passed Python/web CI, the live quick refresh, pre-deploy integrity and data-health gates,
  Firebase deployment, and live-serving verification.

## Round Q — familiar Canadian Masters names and full-round forecasts

- [x] Add fail-first producer coverage for the shared 2026 Canadian Masters ESPN identity,
  proving its display label is `Toronto` on ATP and `Montreal` on WTA while every data join
  continues to use `espnId`.
- [x] Replace the sponsor title at the display-name boundary and make tournament forecast tables
  show every available reach round (`R128`/`R64`/`R32` through Win), rather than discarding
  everything before R16.
- [x] Run focused and full Python/web verification plus a rendered mobile/desktop check of the
  Canadian Masters table; reconcile against the latest git history and append the review. Do not
  push or deploy without separate explicit instruction.

### Review

- Public naming now resolves at the producer's identity-aware display boundary: exact 2026
  Canadian editions render `Toronto` (ATP) and `Montreal` (WTA), later unknown editions fall
  back to `Canada`, and any sponsor title already joined by stable identity to a familiar
  archive/city alias inherits that alias without fuzzy matching or changing join keys.
- Tournament heroes and detailed cards now select from the complete ordered reach sequence,
  so any available R128/R64/R32 probabilities precede R16 through Win. Missing rounds remain
  omitted, and concurrent compact cards keep their title-only treatment.
- Fail-first regressions reproduced both issues. Final verification passed all 501 Python tests,
  all 195 web tests, TypeScript, the 21-page production build, and `git diff --check`; ESLint
  remained at 0 errors / 13 existing warnings.
- Rendered inspection showed all eight round columns fitting the 1280px desktop without page
  overflow. At 390px mobile, the document stayed 380px wide while the 620px forecast table
  scrolled inside its 314px strip, exposing early rounds first without widening the page.
  Reconciled against `git log -5`; `e81a54f` remained the latest commit before publication.

## Round R — live play owns the current-tournaments page

- [x] Add fail-first view regressions proving ordinary completed events never render on the
  overview, prestige events (Grand Slam/Finals/1000/Olympics) remain for seven days, and an
  upcoming 1000-level draw cannot take the hero while any tournament is live.
- [x] Make live events the primary surface: a live 1000 may own the hero; otherwise every live
  event stays in the detailed grid, while upcoming events move to a compact `Coming up` section.
  Only when nothing is live may an upcoming 1000-level event own the hero.
- [x] Replace completed-event hero/linger behavior with a compact `Recently finished` prestige
  section, update the web lesson with the lifecycle rule, and run focused/full web checks plus
  rendered mixed live/upcoming/completed inspection.
  Reconcile against the latest git history and append the review; do not push or deploy without
  separate explicit instruction.

### Review

- The overview now partitions lifecycle before prestige. Live events are the only primary
  cohort while play is underway; a live Slam/Finals/1000/Olympics may own the hero, otherwise
  all live events receive detailed grid cards. Upcoming draws remain compact under `Coming up`
  and may claim a hero only when no event is live.
- Ordinary completed events leave immediately. Completed Grand Slams, Tour Finals, 1000s, and
  Olympics remain as compact `Recently finished` results for exactly seven days and can never
  become the hero.
- Five fail-first lifecycle regressions reproduced the hierarchy bugs. Final verification passed
  all 197 web tests, TypeScript, the 21-page production build, and `git diff --check`; ESLint
  remained at 0 errors / 13 existing warnings.
- Rendered mixed-state inspection at 1280px showed Washington DC first as a detailed live card,
  Toronto compact under `Coming up`, and Madrid compact under `Recently finished`; ordinary
  completed Estoril was absent and the page had no horizontal overflow. Reconciled against
  `git log -5`; `e81a54f` remained the latest commit before publication.

## Round S — next scheduled matches inside live tournament cards

- [ ] Add fail-first producer and web regressions for a stable `espnId` join between tournament
  cards and scheduled matches; never attach matches by sponsor/city display-name similarity.
- [ ] Add a restrained `Next up` footer to live detailed and live supporting cards only, capped
  at three soonest-first matches with player names, round/date context, win odds, and a link to
  the full schedule. Keep upcoming and completed cards unchanged.
- [ ] Remove the redundant global upcoming-match grid from the tournament overview, then run
  focused and full Python/web checks plus rendered desktop/mobile inspection. Reconcile against
  the latest git history and append the review; do not push or deploy without explicit approval.

## Round T — full upcoming forecasts for top-tier events

- [x] Add a fail-first lifecycle regression proving that, while a lower-tier event is live, an
  upcoming Grand Slam, Tour Finals, 1000, or Olympics draw is separated from compact upcoming
  events without displacing live play.
- [x] Render those upcoming top-tier events with the complete hero-style round-by-round table
  after the live surface; keep lower-tier upcoming events compact and preserve the existing
  no-live hero behavior.
- [x] Record the generalized display rule, run focused/full web checks, and inspect the mixed
  live-plus-Toronto overview at desktop and mobile sizes. Reconcile against current git history
  and append the review; do not push or deploy without explicit approval.

### Review

- Upcoming top-tier detail is now a general lifecycle output, not a Toronto name exception:
  Grand Slams, Tour Finals, 1000s, and Olympics enter `featuredUpcoming` whenever anything is
  live. Live events remain the primary hero/grid cohort; lower-tier future events remain compact.
- The overview renders every featured upcoming event with the same complete forecast surface as
  a hero: player ratings, every available reach round, sortable columns, and the full-field
  expansion. When no event is live, the existing upcoming-top-tier hero behavior is unchanged.
- The fail-first mixed-lifecycle regression failed on the missing `featuredUpcoming` contract,
  then passed for all four top-tier categories while also proving an upcoming 250 stays compact.
  The coverage invariant now includes every lifecycle surface so the new partition cannot drop
  an event. Final verification passed all 202 web tests, TypeScript, the 21-page production build,
  and `git diff --check`; ESLint remained at 0 errors / 13 existing warnings.
- Rendered against the current production ATP data, the 1280px view kept DC/Los Cabos first and
  showed Toronto afterward with R128 through Win. At 390px, Toronto stayed in its 348px panel and
  its 620px table scrolled inside a 314px strip. The separate live-card grid retains a pre-existing
  min-content overflow on mobile; the new Toronto surface did not cause or enlarge it. Reconciled
  against `git log -5`; `7ff211d` remains the latest commit. Nothing was committed or deployed.

## Round U — next scheduled matches inside live tournament cards

- [x] Preserve each scheduled row's stable `espnId` in the web export and add fail-first producer
  and view regressions proving cards never join matches by sponsor/city display name.
- [x] Add a compact live-card `Next up` footer capped at three soonest-first matches, with
  round/date, player names, model odds, profile links, and a full-schedule link. Keep upcoming and
  completed cards unchanged and remove the redundant global six-match grid.
- [x] Run focused and full Python/web checks, inspect the rendered desktop board, reconcile current
  git history, and append the review. Do not commit or deploy without explicit approval.

### Review

- `upcoming.json` now carries the same provider identity already present in the live schedule
  source. `matchesForTournament` requires an exact non-null `espnId` on a live card, preserves the
  producer's soonest-first order, and caps the result at three; missing identity safely withholds
  the footer instead of guessing from names.
- Both the hero and grid/compact card renderers share one small footer. The old cross-tournament
  `Up next` grid was removed, so each matchup appears once in its event context and `/schedule`
  remains the complete board. Upcoming and completed event cards do not receive the footer.
- Fail-first regressions reproduced the missing identity export and the unsafe name-join case.
  Final verification passed all 502 Python tests, all 202 web tests, TypeScript, the 21-page
  production build, and `git diff --check`; ESLint remained at 0 errors / 13 existing warnings.
- The regenerated ATP/WTA artifacts carried IDs through correctly. At 1280px, both live ATP cards
  showed three-row footers within their 588px cards, retained equal density, and introduced no
  horizontal overflow. A rendered-text pass also caught and fixed glued `Player Avs Player B`
  accessibility text. Reconciled against `git log -5`; `7ff211d` remains the latest commit.

## Round V — WTA Toronto official-draw parser repair

- [x] Add a fail-first official-draw regression for WTA PDF rows whose slot number and entry code
  are glued together (the current Toronto artifact contains `124WC`).
- [x] Accept only recognized glued entry codes while preserving the parser's contiguous bracket
  geometry and evidence checks; confirm the current 2026 Toronto PDF reconciles all 96 ESPN players.
- [x] Run focused draw and health tests plus the full Python suite, run `git diff --check`, reconcile
  current git history, and append the review. Do not commit, push, or deploy without explicit approval.

### Review

- The failed scheduled refresh reached the intended pre-deploy gate because Toronto had only a
  coverage shell. Its official WTA PDF was otherwise complete, but extracted slot 124 as `124WC`;
  the parser required whitespace after every slot number and discarded the 128-slot geometry.
- `_slot_line` now permits a missing number/body gap only when the body begins with one of the
  existing recognized entry codes. The contiguous-slot and player/date evidence contracts remain
  unchanged, so arbitrary numbered prose cannot become a draw row.
- The regression failed before the parser change and passed afterward. A fresh in-memory replay
  against WTA source 806 and ESPN event `421-2026` parsed 96 entrants in a 128-slot bracket and
  reconciled all 96 live-field players with no unmatched names.
- Final verification passed all 99 focused draw/health tests, all 503 Python tests, and
  `git diff --check`. Reconciled against `git log -5`; `d58ea3e` remains the latest commit. Nothing
  was committed, pushed, or deployed.

## Round W — search discovery and canonical SEO

- [x] Add fail-first SEO contracts for the complete indexable route set, per-page canonical URLs,
  a permissive production `robots.txt`, and an XML sitemap that excludes the internal health page
  and legacy `/upcoming/` redirect.
- [x] Implement Next static metadata routes plus canonical and WebSite identity metadata, keeping
  `/health/` and `/upcoming/` noindexed and making `/upcoming/` canonicalize to `/results/`.
- [x] Extend the post-deploy verifier to guard the live robots/sitemap/canonical contract, then run
  focused and full web checks, inspect the exported files, reconcile current git history, and
  append the review. Do not commit, push, deploy, or submit Search Console without explicit approval.

### Review

- Next now statically exports a permissive `robots.txt` that advertises the production sitemap and
  a `sitemap.xml` containing all 16 indexable routes exactly once. The internal `/health/` route and
  noindexed legacy `/upcoming/` redirect are excluded; `/upcoming/` canonically points to `/results/`.
- Every indexable page emits an absolute self-canonical URL on the Firebase origin. The root also
  publishes consistent DEUCE application identity and `WebSite` JSON-LD for search-engine site-name
  discovery. Existing route titles, descriptions, Open Graph data, and noindex rules are preserved.
- The shared route inventory now drives the sitemap plus local/live route verification. The live
  verifier checks robots MIME/directives, exact sitemap membership/origin, and every self-canonical.
  A negative control against the still-unmodified production site failed exactly those two new
  checks while the other nine checks passed, proving the new guard bites before deployment.
- Fail-first coverage failed on the missing metadata routes/helpers, then passed all 26 focused
  tests. Final verification passed all 210 web tests, TypeScript, the 23-route static production
  build, exported-file inspection, and `git diff --check`; ESLint stayed at 0 errors / 13 existing
  warnings. Reconciled against `git log -5`; `d34ab0c` remains the latest commit. Nothing was
  committed, pushed, deployed, or submitted to Search Console.

## Round X — Google Search Console ownership verification

- [x] Add the user-issued Google verification token through the root Next metadata contract and
  pin the exact value in a focused regression.
- [x] Build and inspect the exported homepage, extend the post-deploy verifier to require the exact
  live token, and prepare the scoped `master` release. Do not attempt Search Console UI actions on
  the user's behalf.

### Review

- The user-issued token is part of the root Next metadata contract, so every static build emits the
  exact `google-site-verification` tag in the homepage `<head>` without adding a tracking script.
- The post-deploy verifier now extracts and requires the exact token. Its negative control against
  the current pre-release production site failed only the new ownership check while the other 11
  serving checks passed, proving a missing or stale verification tag will block a green release.
- Fail-first tests reproduced both missing contracts, then passed. Final verification passed all
  213 web tests, TypeScript, the 23-route static build, exact exported-HTML inspection, and
  `git diff --check`; ESLint remained at 0 errors / 13 existing warnings. Reconciled against
  `git log -5`; `edfc3d5` remained the latest commit before publication.

## Round Y — WTA 125 live-result policy leak

- [x] Add fail-first regressions proving ESPN live rows are classified through stable `espnId`
  identity, excluded from the model when their resolved tier is WTA 125, and retained for all
  other WTA tiers without removing their board/draw inputs.
- [x] Stamp the resolved live-event tier before source merge, enforce `INCLUDE_WTA_125=False` on
  that ingestion path, and expose a zero-WTA-125 model-row count in `meta.json`; extend the
  pre-deploy output gate so this policy leak cannot ship again.
- [x] Reproduce the July-19 rollover against the live ESPN payload, run focused and full Python
  checks plus `git diff --check`, reconcile current git history, and append the review. Do not
  commit, push, or deploy without explicit approval.

### Review

- The failed run was not an upstream truncation: ESPN's WTA endpoint mixes tour events with WTA
  125s, and the rolling live overlay bypassed `INCLUDE_WTA_125=False`. At the August 3 UTC
  rollover, July 19 left the 14-day query window and five 31-match events disappeared together,
  producing the net `128827 -> 128703` drop.
- The legacy name-keyed tier cache now resolves through the append-only event registry to stable
  `espnId`. Known WTA 125 and unclassified live results are withheld from model state, while their
  rows remain identity hints through de-duplication so eligible stable-source copies keep the id;
  raw live inputs remain available to the tournament board and draw pipeline.
- `meta.json` now audits final WTA-125 rows plus excluded known/unknown live rows. The pre-deploy
  gate requires population schema v2, requires the audit fields, blocks any nonzero WTA-125 model
  count, and reports unclassified exclusions as an advisory. Intentional population changes reset
  run-over-run count comparison only across the explicit version boundary; comparison resumes on
  the next run instead of weakening the existing drop threshold.
- A real July 19 replay classified 278 completed WTA rows: 124 WTA 125 and 31 unclassified rows
  were withheld, while 123 rows from four WTA tour events remained eligible. A production-shaped
  all-tour quick refresh completed; WTA exported 128605 eligible matches with `wta125Matches=0`
  and 93 current live WTA-125 rows excluded. The complete pre-deploy integrity gate passed.
- Fail-first coverage reproduced all four missing contracts. Final verification passed all 508
  Python tests and `git diff --check`. Reconciled against `git log -5`; `a766cf2` remains the
  latest commit. Verification-only forecast/Kalshi log mutations were removed. Nothing was
  committed, pushed, or deployed.

### Review addendum — cached model-state compatibility

- A final release-risk audit found that the quick path could clean the current match frame while
  reusing ratings walked over population v1, then label the export v2. `predictor.pkl` now carries
  its own match-population version; the quick guard rejects missing/mismatched versions and forces
  a full rebuild, while `meta.modelPopulationVersion` lets the pre-deploy gate require exact
  model/data parity.
- Both real legacy ATP/WTA caches were rejected and self-healed through full rebuilds. Their new
  predictors and exports report population v2, WTA still contains zero WTA-125 model rows, and the
  complete integrity gate passes. Final verification after this added state guard passed all 510
  Python tests and `git diff --check`; generated forecast-log mutations were removed. Nothing was
  committed, pushed, or deployed.

## Round Z — publish WTA population fix

- [x] Confirm the intended worktree scope, clean diff, authenticated GitHub remote, current
  `master`, and the push-triggered production workflow.
- [x] Stage only the Round Y fix, tests, and durable project notes; commit directly to `master`
  with a scoped fix message as explicitly authorized.
- [x] Push `master`, monitor the complete refresh workflow through deploy and live verification,
  confirm the original match-count alert is absent, document unrelated remaining health
  advisories, and append the release review.

### Review

- Committed the scoped fix as `9c17a08` (`fix(data): enforce WTA live population policy`) and
  pushed `master`, triggering production run `30778009052`. Both reusable test jobs passed; the
  refresh job completed successfully in 6m56s.
- CI restored the legacy population-v1 predictors, the new compatibility guard rejected both,
  and quick mode performed the intended one-time full ATP/WTA rebuild. The pre-deploy integrity
  gate passed, Firebase deployed, the serving checks passed, both health reporters completed, and
  the migrated cache was saved for subsequent quick runs.
- Live WTA metadata reports 128610 matches, `matchPopulationVersion=2`,
  `modelPopulationVersion=2`, `wta125Matches=0`, 93 excluded WTA-125 live matches, and zero
  unclassified exclusions. The original `meta.matches dropped` failure is absent.
- The shared data-health issue #14 remains open only for two unrelated tournament-board
  advisories (Axeria had not flipped live; the below-500 VanOpen results were not joining). Those
  make the health freshness subcheck advisory-red while all 11 serving/contract checks and the
  deploy-health reporter pass; they were not folded into this population-policy release.

## Round AA — separate WTA model population from board lifecycle evidence

- [x] Add fail-first regressions proving policy-excluded WTA live results remain absent from the
  rating/model dataframe but are present in an event-facing view, and that a final in that view
  makes the exported card completed with the real champion rather than stale-upcoming.
- [x] Preserve the exact post-dedup policy-excluded rows as event-only evidence and use the
  augmented view only for tournament projection and independent event coverage. Keep model
  training, profiles, fixtures, metadata counts, and the zero-WTA-125 gate on the eligible view.
- [x] Rebuild the real WTA event artifacts and confirm Axeria, VanOpen, and Palermo complete with
  their recorded finals; run focused/full Python checks, the integrity gate, `git diff --check`,
  and reconcile current git history. Do not commit, push, or deploy without explicit approval.

### Review

- The WTA population-policy fix correctly removed WTA 125 results from rating state, but the
  exporter reused that same filtered dataframe for tournament cards and independent event
  coverage. It therefore erased the only lifecycle evidence for Axeria and VanOpen even though
  ESPN's raw live file contained both completed draws and finals.
- `merge_sources()` now preserves the exact post-dedup excluded partition as a private event-only
  sidecar. `event_match_view()` cleans and joins that evidence only at the event export seam;
  training, profiles, fixtures, model metadata, and the zero-WTA-125 population invariant still
  consume the unchanged eligible dataframe.
- A production-shaped WTA quick export kept 128605 eligible model matches and projected Axeria,
  VanOpen, and Palermo as completed with their recorded champions (Laura Samson, Taylah Preston,
  and Francesca Jones). All three coverage records carry their final evidence. Both normal health
  and `--gate` report zero output problems.
- Fail-first coverage reproduced the missing producer/view contracts. Final verification passed
  158 focused tests, all 514 Python tests, and `git diff --check`. Reconciled against current
  `master` (`43662db`); the verification-only WTA forecast-log append was removed. Nothing was
  committed, pushed, or deployed.

## Round AB — reconnect Iasi after the ESPN result window expires

- [x] Add fail-first regressions for the August 4 rollover: the stable `Iasi` result group has no
  `espnId`, its final is discarded for the upstream 2029 date typo, and the cached official draw
  is keyed as `874-2026`; date/player/real-match evidence must recover that identity without a
  name-similarity join.
- [x] Share that evidence-derived identity between tournament projection and independent event
  coverage so both produce one completed WTA 250 card for `874-2026`, with the missing final
  reported honestly instead of emitting an id-less generic coverage shell that blocks deploy.
- [x] Reproduce the expired-live-overlay state against the real WTA inputs, run focused/full
  Python checks plus the pre-deploy integrity gate and `git diff --check`, reconcile current git
  history, and append the review. Do not commit, push, or deploy without explicit approval.

### Review

- Production run `30875441383` crossed the UTC date boundary and ESPN's rolling WTA payload fell
  from ten events to nine. Iasi disappeared from the live overlay; the stable feeds still carried
  its main draw only through the semifinals because the fresh final is mistyped as `2029/7/20`
  and correctly rejected. The remaining short `Iasi` group had no `espnId`, so it could not find
  the retained `874-2026` draw/calendar and the coverage gate blocked its generic shell.
- `cached_draw_identity_aliases()` now proves an id-less result group against ID-keyed complete
  draws using overlapping observed dates, at least three shared real players, and at least two
  shared first-round matchups. Tournament projection and independent coverage consume the same
  derived aliases. Names never participate in the join, and ambiguous evidence remains id-less.
- The real expired-overlay replay resolved Iasi from 32 shared players and 16 shared matches;
  overlapping Nordea was rejected despite 13 shared players because only one match agreed. Iasi
  exported exactly once as completed, WTA 250, Clay, key `espn:874-2026`, and not coverage-only.
  Its genuinely missing final/champion remained the intended advisory rather than a blocker.
- Fail-first checks reproduced both missing contracts, then 34 focused tests and all 512 Python
  tests passed. The pre-deploy integrity gate passed with only the two existing Axeria/VanOpen
  advisories, and `git diff --check` passed. Reconciled against current production `master`
  (`43662db`). Nothing was committed, pushed, or deployed.

## Round AC — publish August 4 WTA data-health fixes

- [x] Confirm the combined release scope contains only the WTA125 lifecycle-evidence fix, the
  Iasi expired-overlay identity fix, their regressions, and durable project notes; verify GitHub
  authentication and exact synchronization with production `master`.
- [x] Run the complete Python suite and pre-deploy integrity gate, stage the explicit release
  files, commit directly to `master`, and push the production trigger as authorized.
- [x] Monitor the production workflow through deploy and live verification, confirm issue #14's
  Axeria/VanOpen findings are absent, and append the release review.

### Review

- The scoped data fix shipped as `83e3b3e` (`fix(data): recover WTA tournament lifecycle
  evidence`). Its first workflow stopped before refresh because local verification had omitted
  CI's Ruff step; two new test import blocks violated `I001`. The deterministic import-only fix
  shipped as `c6d6f91` after repository-wide Ruff, all 514 Python tests, and the pre-deploy gate
  passed locally.
- Production run `30880774288` completed successfully in 7m48s: both reusable test jobs passed,
  quick ATP/WTA export completed, the integrity gate passed, the static site built, Firebase
  deployed, and the live serving, data-health reporting, deploy-health reporting, and cache-save
  steps all completed.
- Direct live JSON verification shows Axeria completed with Laura Samson over Kaitlin Quevedo,
  VanOpen completed with Taylah Preston over Maddison Inglis, and Palermo completed with
  Francesca Jones over Fiona Ferro. The latest issue #14 report contains neither original
  Axeria nor VanOpen finding.
- Issue #14 remains open for newly surfaced advisory state: ATP Toronto/DC currently appears as
  overlapping identities with an unresolved tier, and Iasi is now correctly one completed
  `874-2026` event but its upstream-corrupted final remains unavailable. Those advisories make
  live health `ok=false`; the deploy itself and exact begun-event membership verification passed.

## Round AD — resolve issue #14 tournament data-health advisories

- [x] Add fail-first regressions for the ATP same-season rematch collision: two matches with the
  same ordered players and score but different rounds/events must both survive de-duplication, so
  the Washington final keeps its stable id and flips the `888-2026` card out of upcoming.
- [x] Recover only strongly-proven corrupt final years: a far-future final may inherit the unique
  season of its source-native event only when its two players are exactly the two semifinal
  winners and the corrected date fits the tournament window; all ambiguous future rows remain
  dropped. Prove the Iasi final/champion is restored without weakening the future-date guard.
- [x] Resolve tournament tiers through stable `espnId` between current-edition archive evidence
  and legacy name-keyed fallbacks, and pass that identity through live/upcoming cards, coverage,
  and scheduled match output so Toronto remains Masters 1000 after a sponsor-title change.
- [x] Stop the rename heuristic from merging overlapping cards whose distinct stable ids already
  prove distinct events, while retaining the id-less rename detector and duplicate-id invariant.
  Rebuild against the current ATP/WTA inputs; run focused tests, Ruff, the full Python suite,
  normal health, the pre-deploy gate, and `git diff --check`; append the review. Do not commit,
  push, or deploy without explicit approval.

### Review

- Washington's August final repeated the exact players and 7-6 6-4 score of their February
  Delray match. The merge's year-wide key collapsed them before projection and transferred
  `888-2026` to the wrong row. Round-aware de-duplication now preserves distinct rematches while
  treating a missing round as a wildcard only when the source copies prove one unambiguous round.
- Correcting that key restores genuine historical matches, so match population version 3 forces
  cached predictors to rebuild once instead of relabelling version-2 rating state. The exact quick
  migration rebuilt both tours locally and exported model/data population parity at version 3.
- A far-future final year is now repaired only inside one raw source when exactly one season has
  the final's two players as its two semifinal winners within seven days. The real Iasi row became
  2026-07-20; unrelated or ambiguous future rows still reach the existing corruption drop.
- Tier resolution now carries `espnId` through result cards, released-draw cards, coverage shells,
  and scheduled match output. Toronto resolves `421-2026` through the registry to the cached
  sponsor-title tier. The overlap heuristic likewise defers to two distinct stable ids while its
  id-less rename fallback and duplicate-id invariant remain intact.
- Current-data replay exports Toronto live/Masters 1000, Washington completed/ATP 500 with Taylor
  Fritz over Rafael Jodar, and Iasi completed/WTA 250 with Mayar Sherif over Paula Badosa. Normal
  health reports zero problems; the pre-deploy gate, Ruff, `git diff --check`, 177 focused tests,
  and all 521 Python tests pass.

### Production follow-up

- [x] Reproduce the post-deploy one-day ATP `Masters` fragment, fold it into Toronto only on
  inclusive date overlap plus shared real-player/match evidence, and retain negative controls for
  concurrent, adjacent, and ambiguous events. Re-run the focused/full gates and deploy the fix.

### Production follow-up review

- The first `6dff794` deploy passed every blocking gate but its post-deploy sentinel caught a
  transient, one-day id-less ATP card named `Masters`. It shared Toronto's players/matches but the
  producer required two overlap days, so it escaped coalescing and fell back to generic `ATP Tour`.
  The provider corrected itself before local re-download, proving this needed a replay regression
  rather than a source-name exception.
- Commit `51e16a8` makes observed date overlap inclusive: an id-less one-day fragment joins exactly
  one stable-id event only with at least three shared real players and an exact main-draw matchup.
  Same-day groups with the same players but no shared matchup, concurrent disjoint fields,
  qualifying placeholders, and ambiguous multi-id matches remain separate. No name participates.
- Ruff, the focused coalescing tests, all 522 Python tests, `git diff --check`, the pre-deploy gate,
  and a normal two-tour health report passed locally. Production run `30886506358` passed both CI
  jobs and every refresh/build/Firebase/live-verification/report/cache step in 11m38s.
- Direct public-JSON verification at `2026-08-04T07:24:13Z` reports health `ok=true`, zero ATP/WTA
  source or output problems, and model/data population parity at version 3 (ATP 284,016; WTA
  128,832). Toronto is the sole `421-2026` live Masters 1000 card; Washington, Axeria, VanOpen, and
  Iasi are completed with their recovered champions. Issue #14 closed automatically at 07:29Z.

## ESPN live overlay 403 — stale ATP board (2026-08-06)

Zverev lost Toronto/Montreal R32 on 2026-08-05 (Griekspoor 6-7 6-2 6-4) but still ships at 21%
title odds. ATP `date_max` froze at 2026-08-04; WTA stayed current only because its own daily
stats scraper backfills it, which masked a two-tour outage.

Root cause: ESPN's `site.api.espn.com` edge began 403-ing the pipeline's
`User-Agent: Mozilla/5.0 tennis_model` between run `30898710522` (08-04 10:00Z, 129 rows) and
`30960020388` (08-04 23:27Z, 0 rows). Verified: that host 403s *any* custom UA and only admits
curl's default; `site.web.api.espn.com` serves every UA. It went unseen for ~13 refresh runs
because `fetch_events()` swallows all 27 per-query exceptions and returns `[]`, so
`download_live()` prints the benign "no completed matches found" — identical to a quiet day —
and `if not df.empty:` leaves the stale `live.csv` in place.

- [x] Point `SCOREBOARD` at `site.web.api.espn.com` (verified end-to-end: ATP 0 -> 183 completed
      rows through 08-07, Zverev/Griekspoor and Van De Zandschulp/Medvedev both present).
- [x] Make the fetch loud: have `fetch_events()` distinguish "every query failed" from "nothing
      completed", and `download_live()` report a transport failure instead of an empty day.
- [x] Gate coverage. Planned as a new per-live-bracket invariant, but building it surfaced an
      existing equivalent — `HEALTH_MAX_LIVE_EVENT_AGE_DAYS`, on the same `end` field, from
      `772e5d4`. It did not fire because it is off by one against its own stated rationale
      ("a genuine in-progress event is never 3 days idle") and tolerated exactly 3. Tightened
      3 -> 2 and rewrote the message, which asserted a cause the gate cannot observe, rather
      than shipping a second predicate at a different threshold.
- [x] Tests: `test_health.py` for the stalled-feed case at the tier that blocks; `test_live_parse.py`
      for all-queries-failed, single-bad-query, genuinely-empty, and the host lock. Both new tests
      verified to fail against the pre-fix code. Fires on exactly Toronto + WTA Warsaw across both
      shipped 08-07 payloads and nothing else.
- [x] Full Python suite + Ruff, then deploy and verify the recovered board drops Zverev.

### Review

- `d09cea0` deployed via run `31144695662` (tests 55s/51s, refresh 15m59s, all green). Live
  verification at `2026-08-07T03:47:24Z`: ATP `dataThrough` 08-04 -> **2026-08-07**, `result_age`
  3d -> **0d** on both tours, health `ok=true` with zero source and output problems, 284,162
  matches. Toronto now reads 25 alive of 96 with `end=2026-08-07`; **Zverev and Medvedev are off
  the board.** The reported symptom is gone.
- The host swap was the whole repair — 28/28 queries were failing, so nothing downstream was
  wrong. Worth noting the 403 reproduces from a laptop too, so this was never CI-specific and a
  local check would have caught it at any point in the three days.
- Deliberately did NOT add the per-live-bracket invariant I planned. `HEALTH_MAX_LIVE_EVENT_AGE_DAYS`
  already asserted it on the same `end` field; a second predicate at a different threshold would
  have been two gates disagreeing about one question. Tightening the existing one 3 -> 2 makes it
  match the rationale its own commit gave.

### Follow-up found while verifying — withdrawals never eliminate anyone

Felix Auger-Aliassime is now the Toronto **favourite at 14.3%**, and he withdrew before hitting a
ball (back injury in practice, ~2h before his opener on 08-05). This is a DIFFERENT root cause
from the stale feed and survived the fix:

- Eliminations are derived from completed matches, i.e. from losses. A player who withdraws never
  produces a loser row, so nothing can ever eliminate them and they stay alive forever.
- The bracket's ordered draw comes from the official ATP PDF (`drawSource: atp`, `421`) published
  before the withdrawal; his `R128` slot is a bye and his `R64` vs Titouan Droguet still carries
  `winner=None`. Droguet meanwhile advanced on the walkover and has already played round 3.
- The signal to fix it is present and already downloaded: ESPN's field for `421-2026` lists 96
  players and FAA is **not among them**, nor among the 72 eliminated. So "in the ordered draw but
  absent from the live field" is derivable today.
- Both gates are blind to it. The stale-live check now passes (`end` is current), and nothing
  asserts that a bracket's alive set is a subset of the live field. That invariant is the gate
  half of this fix.

- [x] **Stopgap deployed**: `config.EVENT_WITHDRAWN_PLAYERS` (tour -> ESPN edition id -> names)
      folds into `eliminated` in `project_tournament` before the draw is folded, so `advance_slots`
      hands the opponent their walkover instead of stranding the slot. Auger-Aliassime is the only
      entry. An override matching nobody prints a warning rather than no-op'ing silently — the
      failure shape that started this whole round. Not the mechanism, by design.
- [ ] Replace the hand-maintained list with the derived signal: ESPN already drops a withdrawn
      player from the event field, so "in the ordered draw but absent from the live field" needs
      no config. Decide whether that is safe on its own (a field that briefly under-reports would
      eliminate real players) or wants corroboration from the opponent having advanced.
- [ ] Gate half: a bracket's alive set must be a subset of the live field, with a test. Neither
      existing gate sees this class — the stale-live check passes because `end` is current.
- [ ] Unrelated, found on the way: `EVENT_DISPLAY_NAME_OVERRIDES` has ATP `421-2026` -> "Toronto"
      and WTA `421-2026` -> "Montreal", but the 2026 editions are men's Montreal / women's
      Toronto. The two are swapped, and the table's own comment notes the Canadian Masters
      rotates cities. Venue feeds altitude/context features, so confirm before changing.

### Stopgap deploy verified — and it is only half the fix

Run `31146447623` green (tests 49s/43s, refresh 17m58s). Live at `2026-08-07T04:18:13Z`:
health `ok=true`, zero problems both tours. Toronto 25 -> **24 alive**, Auger-Aliassime off the
board, Arthur Fils inherits the favourite slot at 14.9%. The title race is correct.

The BRACKET panel is not, and this is pre-existing rather than caused by the stopgap. Shipped
`brackets.json` still carries `R64: Titouan Droguet vs Felix Auger-Aliassime, winner=None`.
`bracket_rounds` is a results-JOINED forward fold (`sim/bracket.py:145`): two real players with no
result row between them are "pending" and advance `None`, so the walkover never resolves and the
whole path below it dies. Droguet's three real matches are absent from the bracket view:

    2026-08-03  R64  Droguet d. Luca Van Assche   6-4 2-6 7-6
    2026-08-06  R32  Droguet d. Jaime Faria       7-6 6-2
    2026-08-06  R16  Brandon Nakashima d. Droguet 4-6 6-2 7-5

So `project_tournament` (odds) and `bracket_rounds` (draw display) disagree about who is alive.
The stopgap only taught the first one about withdrawals. Fix is small and contained — give
`bracket_rounds` the withdrawal set and let a pairing with exactly one withdrawn side resolve to
the opponent — but it is a second decision about the same mechanism, so it belongs with the
"how to go forward" call rather than in another hotfix.

- [ ] Teach `bracket_rounds` about withdrawals so the draw view and the odds agree.
