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

- [x] Teach `bracket_rounds` about withdrawals so the draw view and the odds agree. (a8f7dd7 — and
      the answer turned out to be a lucky-loser substitution, not a walkover.)

## Complete the withdrawal fix + sweep for other breakage (2026-08-07)

### 1. The withdrawal fix was not only incomplete, it was modelling the wrong event

Chasing the missing bracket path showed the stopgap's premise was wrong. Droguet was never
awarded a walkover: Auger-Aliassime withdrew BEFORE his first match, so the tour admitted a
LUCKY LOSER — Jaime Faria — who played the match and lost it 7-6 6-2. Recording a walkover
would have invented a match that never happened and erased one that did. Both cases are real
(pre-first-match withdrawal -> replacement; mid-event -> walkover), so the config now maps
`withdrawn -> replacement or None` and the two paths differ:

- [x] Replacement named: the slot is SUBSTITUTED in `resolved_draw_slots`, so the real result
      joins and the replacement is judged on their own results. `or slot` on the lookup, since
      a walkover entry maps to None and must not blank the slot into a bye.
- [x] No replacement: unchanged walkover handling — eliminated, and `bracket_rounds` resolves
      the pairing to the opponent with score `W/O`, shipped UNPRICED (a model prob for a match
      nobody played would flag an awarded walkover as an `upset`).
- [x] `project_upcoming` reads the same helper, so a withdrawal between draw release and first
      ball is handled identically pre-start.
- [x] The "matched nobody" warning had to change with it: after a substitution the withdrawn
      player is legitimately absent from the final field, which is indistinguishable from a
      name that matched nothing. Now tracks actual hits against the pre-substitution draw.
- [x] Verified on the real draw: R64 now reads `Droguet d. Faria 7-6 6-2`, R32 `Nakashima d.
      Droguet 4-6 6-2 7-5`. Auger-Aliassime is absent entirely. He never played.

### 2. WTA's fresh-overlay freshness gate has been dead for three weeks

`fresh_age_days = -1078` against a 14-day limit, reported `ok`. The overlay still carries the
Iasi final as `2029/7/20` — the SAME corrupt row as the 2026-07-25 incident. Age is
`now - max`, so one future row pins it negative and the freeze alarm can never fire. The
merged `future_dates` check could not cover it either: it reads the population AFTER
`_drop_impossible_dates` strips the row, so it never sees a bad row in a source file.

- [x] `fresh_date_max(tour, now)` excludes rows beyond the credible horizon -> WTA now reports
      its true newest result (2026-08-03, 4d) instead of a date in 2029.
- [x] New `fresh_future` check names the corrupt row, so fixing the age signal does not just
      hide it. Advisory only (`--gate` is output-integrity), and WTA's fresh alarm stays
      shadowed because its stats overlay is current — so this alerts without blocking.

### 3. The alias proposer reds its own run and buries the branch

The 08-03 weekly run produced two genuine falsifier-surviving proposals, pushed the branch,
then died: `GitHub Actions is not permitted to create or approve pull requests`. `set -e` made
that exit 1, breaking the script's own documented contract that every branch exits 0, and the
pushed branch `alias-proposer/30807596234` has sat unnoticed since.

- [x] Fall back to a `::warning::` naming the compare URL, and exit 0. Proposals are only
      unannounced when this happens, never lost. Test asserts it stays green, still never
      calls `gh pr merge`, and names the branch.
- [x] **Needs the owner, not code**: Settings -> Actions -> General -> "Allow GitHub Actions to
      create and approve pull requests" is off (`can_approve_pull_request_reviews: false`).
      Until it is on, the proposer can push but not open the PR. The two proposals waiting on
      `alias-proposer/30807596234` are Digvijaypratap Singh -> Digvijay Pratap Singh and
      Christopher Oconnell -> Christopher O'Connell.

## Clear the remaining live-round backlog (2026-08-07)

Everything still open at the tail. The older unchecked boxes further up this file belong to
rounds that closed with their own Review sections — this is an append-only log, not a queue.

- [x] **Toronto/Montreal display labels were swapped.** ATP `421-2026` read "Toronto" and WTA
      `421-2026` read "Montreal"; 2026 is men's Montreal (IGA Stadium) / women's Toronto
      (Sobeys Stadium). ESPN cannot arbitrate — it reports "Toronto, Canada" for BOTH tours
      under the shared id, which is why the override table exists at all. The provider ids
      already agreed with the corrected labels (WTA 806 IS the Toronto edition). An existing
      test asserted the inverted pair, so it was pinned wrong rather than unpinned; updated
      with the evidence and a warning that the cities swap every year.
- [x] **Gate half: a drawn entrant the feed no longer lists.** `drawnNotInField` is derived in
      the PRODUCER, not the gate, because the two sides are only comparable after
      `_reconcile_draw_names` — a gate re-deriving it from raw files would rediscover exactly
      the spelling noise that already resolved. Tier-aware, so a Masters board blocks. Guarded
      against a feed that under-reports (a short field indicts nobody), since wrongly removing
      a REAL player is worse than the bug it chases. Absent key reads clean, so a build from
      before this ships does not fail the gate.
- [x] **Regression I caused and the guard for it.** Editing `open-alias-pr.sh` dropped its
      executable bit (100755 -> 100644) and the very dispatch meant to prove the PR fix worked
      died with exit 126, "Permission denied". Nothing local catches this: it still runs under
      `bash x.sh`, and `git diff` shows only the content change. Restored, and a test now
      discovers which scripts a workflow invokes WITHOUT an interpreter and asserts their git
      index mode — `open-alias-pr.sh` is the only one, the rest run as `bash <path>`.

### Deliberately not done

- The hand-maintained withdrawal list stays. `drawnNotInField` now turns that class from a
  silent three-day wrong board into an alert on the next refresh, and adding the config entry
  after it fires takes a minute. Deriving the substitution automatically is the part that can
  go wrong in the dangerous direction — a draw name the feed spells differently is
  indistinguishable from a genuine withdrawal by absence alone, and guessing wrong deletes a
  live player from the board. Detection automated, mutation still explicit and auditable.

### The new check earned its keep within one refresh

`drawnNotInField` shipped at 18:13Z and immediately flagged a THIRD instance nobody had
looked for: WTA Warsaw carried `Jeline Vandromme`, who never played a match there. Three
independent signals agree it is a substitution, not a spelling split — she has no result row
anywhere in the event; `Marcelina Podlinska` is the only name in the feed's field absent from
the draw; and Podlinska's single match was against `Vendula Valdmannova`, the exact occupant
of the slot adjacent to Vandromme's. Recorded as `961-2026: {Vandromme: Podlinska}`.

Worth noting what this says about the deliberate no-auto-derivation call above: the evidence
that made this safe to resolve was the ADJACENCY agreeing, not the absence. Absence alone had
two readings and picked the right one only because a human checked which. That is the argument
for keeping detection automatic and mutation explicit, and it survived contact with a real case.

## Withdrawal detection, automated (2026-08-07)

The hand-maintained list is gone; `EVENT_WITHDRAWN_PLAYERS` now ships EMPTY and
`_derive_withdrawals` works it out from evidence. Checked against both real cases with the
table empty: it reproduces `Auger-Aliassime -> Jaime Faria` (Toronto) and
`Jeline Vandromme -> Marcelina Podlinska` (Warsaw) exactly.

What changed my mind about doing this at all. I argued twice that absence was too ambiguous
to act on — a name the draw and the feed spell differently looks identical to a withdrawal.
That is still true, and it is why the rule is NOT absence. It is **the replacement plays the
match the vacated slot owed**: seat a candidate in the slot, fold the real draw, and see
whether a SCORED result joins. That is the same three-way agreement I checked by hand for
Warsaw, and it is decidable from data the pipeline already has.

The ambiguity I was worried about turns out not to need resolving. If the newcomer is a
genuine lucky loser, the slot is theirs. If it is the same person spelled two ways, the feed's
spelling is the one the results already use — so substituting is right under BOTH readings,
and the board is correct either way. (Live data confirms both happen: WTA 1067 derived
`Ye-Xin Ma -> Ma YeXin`, which is a spelling split, not a withdrawal.)

Guards, each earning its place against real data:
- A scored match is required. Round-0 bye advancement sets a winner too and proves nothing.
- Exactly one corroborating candidate, or it stays unresolved. Never pick between two.
- `MAX_DERIVED_WITHDRAWALS = 4`: above that, derive nothing. Run against the live feed with
  raw (unreconciled) names, ATP 304 showed 13 "absences" that were all diacritics — Molčan,
  Báez, Cinà — and the guard produced ZERO derivations, which is the whole point.
- `drawnNotInField` now reports only the residue derivation could not explain, so a resolved
  withdrawal is no longer a permanent red, and using the override is not either.

- [x] Replace the hand-maintained list with the derived signal.
- [x] Keep the override as an escape hatch for genuinely undecidable cases.

## Deployment health: Challenger activity dates and verifier failures (2026-08-08)

Root cause found: the ongoing lower-tier feed records every Hagen row with the tournament
start date, including current quarterfinals. The card therefore says it was last played five
days ago even though the feed is progressing. Separately, the live verifier requires the
overall data-health flag and its `tee` pipeline masks a non-zero verifier exit from GitHub.

- [x] Add an explicit producer-side date-basis marker for result cards whose source dates are
      tournament starts, and preserve the existing reliable match-date basis for other cards.
- [x] Make the live-event health check honor that marker without weakening the stale-event
      check for reliable cards; add producer and health regressions for both paths.
- [x] Decouple post-deploy serving verification from the data report's advisory/overall `ok`
      flag; verify the deployed artifact's freshness and serving contract, with unit coverage.
- [x] Make the workflow's verifier pipeline propagate the Node verifier exit status, and add a
      workflow regression so a future `tee` change cannot mask a failed live check.
- [x] Run focused Python and web tests plus the applicable health/deploy gates; inspect the
      generated diff and reconcile the final review with the current Git tip.

### Review

- Producer cards now carry `dateBasis: "start"` only when multiple knockout rounds share one
  source date; reliable match-dated cards remain on the full stale-live check.
- Post-deploy verification checks the deployed `generatedAt` and serving contracts without
  failing solely on advisory `health.json.ok` findings; `refresh.yml` uses `pipefail` around
  the verifier log pipeline.
- Verification: 187 Python tests passed; 215 web tests passed; web lint passed with 13 existing
  React hook warnings and no errors.

### Review addendum (2026-08-08)

- The implementation was tightened so lower-tier `draw_level=chall` provenance earns the
  `dateBasis: "start"` exemption when its rows share one date; legacy repeated-round frames
  retain the structural fallback, and mixed observed dates remain match-dated.
- Re-run verification: 553 Python tests passed; 215 web tests passed; Ruff, Node syntax checks,
  and `git diff --check` passed. `npm run lint` exited 0 with the same 13 existing warnings.
- The local `health --gate` blocked the cached local snapshot on stale Toronto and Montreal
  cards (and warned on Warsaw); that cache predates the current Hagen data and is not a
  regression in this fix.

## Deployment verifier: transient route timeout false alarm (2026-08-11)

Run 31545089452 deployed fresh, healthy artifacts, then one route request timed out. The route
check reported only "This operation was aborted" and stopped fetching at `/schedule/`; the
canonical check reused the incomplete HTML map and falsely claimed that every later route had
lost its canonical tag. The next hourly run passed unchanged and auto-closed issue #18.

- [x] Add bounded retry behavior for transient verifier fetch failures, with the failed URL and
      attempt count preserved in the terminal error instead of a context-free abort message.
- [x] Make the canonical check dependency-aware so unavailable route HTML cannot cascade into
      fabricated metadata failures, while still failing genuine missing/wrong canonicals.
- [x] Add deterministic regressions for a recovered transient abort, an exhausted route fetch,
      and suppression of the dependent false diagnosis.
- [x] Run the focused verifier tests, full web tests/lint/build, applicable Python workflow
      tests, and live negative/positive controls; inspect the diff and reconcile against Git tip.

### Review

- Rejected network requests now retry twice by default. Exhaustion reports the exact URL and
  attempt count; actual HTTP responses still go directly to the existing status/MIME checks.
- Canonical validation checks only successfully served route HTML. A failed route remains a
  route failure, while available HTML with a missing or wrong canonical still fails metadata.
- Verification: 30 focused verifier tests and all 219 web tests passed; production build passed;
  47 workflow-alert tests and Ruff passed; Node syntax and `git diff --check` passed. Web lint
  exited 0 with the same 13 existing warnings.
- Live positive control passed all 12 checks against Firebase. A deliberately wrong
  `generatedAt` failed exactly the freshness check, proving the live gate still bites.
- Final reconciliation: local `master` and `origin/master` both pointed to `8f542bb` before this
  review was recorded; the only worktree changes are this fix, its tests, and task/lesson logs.

## Mobile native-feel hardening (2026-08-12)

- [x] Extend the root viewport contract for edge-to-edge rendering and safe-area-aware chrome;
      use dynamic/small viewport units only where they improve the full-page shell.
- [x] Harden coarse-pointer interactions: prevent iOS input zoom, remove sticky custom hover
      states, suppress long-press selection on controls, and give taps immediate pressed feedback
      without interfering with keyboard focus or Framer Motion transforms.
- [x] Keep page and horizontal-nav scrolling intentional on touch hardware: contain page
      overscroll/pull-to-refresh, retain native horizontal panning, and account for every notch
      inset in the header, content, and footer.
- [x] Add focused regressions for the viewport and mobile CSS contracts, then run the relevant
      web tests, lint, production build, and `git diff --check`; inspect the rendered mobile app
      if a local browser target is available.
- [x] Reconcile the completed review against the current Git tip and record verified results.

### Review

- The root emits `viewport-fit=cover`, an explicit dark color scheme, and matching theme chrome;
  safe-area utilities cover the sticky header, both horizontal gutters, and the footer bottom.
- The page shell uses `100svh` with a `100dvh` upgrade and contains browser overscroll. Touch
  controls suppress tap flash and long-press text selection, use `touch-action: manipulation`,
  expose immediate pressed feedback, and force form controls to 16px only on coarse pointers.
  The two handwritten hover treatments are now limited to fine pointers; Tailwind's generated
  hover utilities were already gated.
- The mobile nav retains native horizontal overflow, hides its scrollbar, and contains its own
  horizontal overscroll. At a 390×844 browser viewport it rendered without document overflow;
  the strip exposed 1,374px of content in its 380px scrollport and scrolled independently.
- Verification: all 222 web tests passed (including three new mobile contract regressions), lint
  passed with the same 13 existing React-hook warnings and no errors, the production build and
  `git diff --check` passed, and rendered QA reported no browser errors.
- Final reconciliation: local `master` and `origin/master` both point to `3bfc541`; the worktree
  contains only this mobile hardening, its tests, and this task log.

## Firebase stuck cache keys / deploy-health issue #19 (2026-08-12)

Run 31611366363 served the freshly deployed data and most assets, but bare requests for three
independent paths returned no bytes through two 30-second attempts. The behavior reproduced
locally on both IPv4 and IPv6. Adding a unique query string made the same paths return at once,
isolating the failure to stored Firebase CDN cache keys rather than the built artifacts or Node.

- [x] Replace the mutable HTML/data catch-all's zero-age revalidation policy with Firebase's
      documented `no-cache, no-store` policy; preserve the immutable hashed-static override.
- [x] Extend the live serving invariant and tests to require non-storage for mutable content
      while still proving hashed assets remain immutable and genuine failures remain visible on
      the bare user-facing URLs.
- [x] Run focused/full web tests, lint/build, workflow tests, syntax/config checks, and diff QA;
      record the cache-key evidence, official contract, and completed review against Git tip.

### Review

- The catch-all Hosting header is now `no-cache, no-store`; the later, more-specific hashed
  static rule remains `public, max-age=31536000, immutable` and its ordering is regression-tested.
- The live deploy verifier now requires both non-storage directives on bare HTML and data URLs,
  retains the immutable asset assertion, and rejects the old zero-age stored policy explicitly.
- Evidence: bare mutable paths intermittently returned no bytes on IPv4 and IPv6, while unique
  query keys returned immediately. The still-old live deploy reported the old mutable header on
  HTML/data and the immutable header on hashed JS, proving the new gate will bite after rollout.
- Verification: 33 focused verifier tests and all 225 web tests passed; production build passed;
  47 workflow-alert tests and Ruff passed; Firebase JSON parsing, Node syntax, and
  `git diff --check` passed. Web lint exited 0 with the same 13 existing warnings.
- Final reconciliation: local `master` and `origin/master` both point to `bf00604`; issue #19 is
  still open because this header change has not yet been committed and deployed.

## Beautiful UI-inspired usability pass (2026-08-12)

- [x] Repair the rankings board on narrow screens with an adaptive metric view, reachable data,
      player search, and explicit sortable desktop columns.
- [x] Add an accessible global command search for pages, player profiles, current brackets, and
      direct player-vs-player predictions, with keyboard and mobile entry points.
- [x] Add a compact overview insight strip from existing forecast/schedule data without implying
      AI recommendations or inventing new model outputs.
- [x] Upgrade high-traffic filters with counted status chips on Results and useful event/surface
      controls on Schedule while preserving existing URL and tour behavior.
- [x] Replace generic loading blocks with content-shaped table, card-grid, and forecast states;
      introduce restrained inset layering where it improves scanability.
- [x] Add focused unit/contract coverage, run web tests/lint/build and `git diff --check`, inspect
      desktop and 390px mobile renders, then record the review against the current Git tip.

### Review

- Rankings now use an adaptive three-column mobile board with a selectable metric, player search,
  and sortable Elo/live-rank/serve/return columns on larger screens; the original board rank stays
  visible when a secondary metric changes the display order.
- The global command search is available from every header and via `Cmd/Ctrl+K` or `/`; it searches
  routes immediately and lazy-loads the active tour's players and brackets only when opened, with a
  direct `Player A vs Player B` predictor action.
- The overview adds a factual current-event/title-favourite/closest-match strip from existing model
  outputs. Results adds counted All/Called/Upsets filters, Schedule adds counted surfaces plus a
  searchable event filter, and loading states now reflect the table/card/forecast content shape.
- Rendered QA covered desktop and a 390px viewport across Overview, Rankings, Results, and Schedule.
  The mobile document stayed at 380px client/scroll width, Rankings exposed `# / Player / metric`,
  the insight carousel remained independently scrollable, and browser logs contained no errors.
- Verification: all 236 web tests passed across 18 files; production build and `git diff --check`
  passed; lint exited 0 with the same 13 existing React-hook warnings and no new warnings.
- Final reconciliation: local `master` and `origin/master` both point to `7ac8aa9`; the worktree
  contains this uncommitted UI pass, its focused tests, and this task log.

## WTA Cincinnati wrong official-draw attachment / blocked deploy (2026-08-12)

- [x] Reject adjacent official draws whose date intersection is only a small fraction of the
      event span, while preserving the existing real-player evidence requirement.
- [x] Parse the WTA provider's current glued `Q/LL` entry code and `Qualiﬁer/LL` ligature label
      as distinct unresolved qualifying seats so Cincinnati source `1017` can be selected.
- [x] Carry `espnId` into bracket provenance and block one tour-provider draw id from being
      attached to multiple ESPN events; add regression coverage for the Toronto/Cincinnati case.
- [x] Run the focused parser/draw/health tests, the full Python suite and Ruff, then replay the
      current WTA live draw acquisition in isolation and record the completed review.

### Review

- Runs 31631055085 through 31645393461 were blocked before deploy because Cincinnati exported
  95 unique entrants beside 96 round-0 slots. An isolated replay proved Cincinnati had inherited
  Toronto's provider id `806`: the events shared 72/83 observed players and three boundary days.
- Official attachment now requires at least half of the shorter inclusive calendar span on fresh
  candidates and retained cache. A settled cached draw must contain distinct real entrants, so
  the already-poisoned Actions cache is re-evaluated instead of remaining immutable.
- The provider parser accepts glued `Q/LL` entry codes and normalizes `Qualiﬁer/LL` ligatures into
  unique numbered seats. The real source `1017` PDF parses as 128 slots, 96 non-byes, 96 unique
  entrants and 13 unresolved qualifiers.
- Bracket payloads now retain `espnId`; the pre-upload health gate applies the same substantial
  date contract and blocks one official source id attached to multiple ESPN events.
- Verification: 129 focused draw/export/health tests passed; all 559 Python tests passed; Ruff
  and `git diff --check` passed. A poisoned-cache replay corrected Cincinnati `806` -> `1017`,
  left `806` only on Toronto, updated the registry, rebuilt WTA artifacts, and produced a clean
  WTA output gate.
- Final reconciliation: local and remote `master` remain at `51849cf`; these fixes and records
  are uncommitted, and no production-triggering push was made.

### Deployment execution (2026-08-13)

- Latest refresh run `31724714753` reproduced the same Cincinnati 95/96 integrity failure on
  remote tip `51849cf`; no new failure class appeared.
- Production push approved after diagnosis. Pre-push verification passed: 129 focused tests,
  all 559 Python tests, Ruff, and `git diff --check`.

## ATP Cincinnati repeated qualifying-seat labels / blocked deploy (2026-08-13)

Run 31725933581 proved the WTA attachment fix but exposed the ATP half of Cincinnati: the
official 96-entrant PDF repeats `Qualifier / Lucky Loser` for 13 unresolved seats, and the
parser preserved that shared string. The tournament field's set collapsed those seats into
one (83 named players + one label = 84), while the ordered bracket retained all 96 non-byes.

- [x] Normalize spaced/full-word provider qualifying labels before set-backed consumers and
      number every occurrence as a distinct unresolved seat.
- [x] Add an exact ATP-PDF parser regression and retain the existing 96-seat integrity gate.
- [ ] Reparse official Cincinnati source 422, run focused/full verification, commit, push,
      and monitor the replacement deploy through live Firebase verification.

### Review

- Production source 422 now parses as a 128-slot bracket with 96 non-byes, 96 unique entrants,
  13 uniquely numbered qualifying seats, and no repeated non-null entrant.
- Verification before the replacement commit: 11 parser tests, 191 broader draw/tournament/
  export/health tests, all 560 Python tests, Ruff, and `git diff --check` passed.

## ATP Cincinnati Griekspoor withdrawal / blocked deploy (2026-08-14)

Runs 31817797668 and 31822996593 were blocked before deploy because the retained official
Cincinnati draw still names Tallon Griekspoor after ESPN and the now-updated ATP source replaced
him with Shang Juncheng. The generic evidence derivation cannot act until the replacement plays,
which is the documented escape-hatch case for an event-scoped withdrawal override.

- [x] Add the `718-2026` ATP withdrawal substitution from Tallon Griekspoor to Shang Juncheng.
- [x] Add an exact event-scoping regression that proves the cached draw substitutes Shang, removes
      Griekspoor from the projection, and clears `drawnNotInField` before Shang has played.
- [x] Run focused tournament/health coverage, the full Python suite, Ruff, the pre-deploy gate,
      and `git diff --check`; then record the review before any production-triggering push.

### Review

- The override is keyed only to ESPN edition `718-2026` and replaces Griekspoor with Shang in the
  retained ordered draw until match evidence can establish the same substitution automatically.
- The exact regression starts from the stale draw and current ESPN field before either player has
  a result; Shang occupies Griekspoor's slot against Lorenzo Sonego, enters the projection, and
  `drawnNotInField` clears.
- Verification: 143 focused tournament/health tests and all 561 Python tests passed; Ruff and
  `git diff --check` passed. The local integrity command ran but correctly rejected this checkout's
  nine-day-old generated artifacts; the pushed refresh will validate against the current Actions
  cache before any Firebase deploy.
- Final pre-push reconciliation: local `master` and `origin/master` both point to `0accd3c`; only
  the scoped config change, its regression, and this task record are modified.

### Re-plan after replacement run 31824513915

The override cleared the original missing-player signal but duplicated Shang, who already occupied
another slot in the retained draw, producing a 95-player field. The ATP PDF had re-seated the draw,
so a one-for-one substitution was not valid; the stale official cache itself must be refreshed.

- [x] Remove the incorrect event override and its substitution regression.
- [x] Revalidate an active settled official draw when its membership differs from ESPN's current
      full field, while retaining the cache for unchanged active fields and completed events.
- [x] Add cache-contract regressions and rerun focused/full verification before the correction push.
- [ ] Commit, push, and monitor the next refresh through the integrity gate, Firebase deploy, and
      live verifier.

#### Corrected review

- Active settled official draws now compare canonical membership with ESPN's current full field.
  A match remains cache-only; a drift re-fetches and revalidates the whole provider artifact; an
  ended event remains frozen. This lets current source 422 replace the stale re-seated draw.
- Two cache-contract regressions prove the drift and no-drift branches. Verification: 159 focused
  draw/parser/tournament/health tests and all 562 Python tests passed; Ruff and `git diff --check`
  passed.
- Run 31824513915 proved the original Griekspoor signal cleared but rejected the guessed override's
  95-player duplicate, so nothing deployed. This correction removes that override rather than
  weakening either geometry gate.

## Global wheel scrolling and mobile player overflow (2026-08-15)

- [x] Restore wheel/trackpad scrolling by removing the non-scrolling `body` overflow trap while
      keeping intentional root-level horizontal clipping and boundary behavior.
- [x] Make every player dossier grid child shrink to the mobile content width and adapt the
      fixed-width identity sparkline/surface row so `/player/` has no clipped right edge at 390px.
- [x] Replace the source-only scroll assertions with behavioral regressions for wheel scrolling,
      mobile document width, and the player dossier's viewport containment; extend the live-serving
      gate with a stable shell contract for this user-visible failure class.
- [x] Run focused tests, the full web test/lint/build suite, `git diff --check`, then verify every
      route plus desktop and 390px scorecard/player interactions in a real browser and record the
      review against the current Git tip.

### Review

- Root-only overflow containment restores the normal document scroll chain: on the local scorecard
  a 600px wheel gesture now moves `scrollY` from 0 to 600 while body computes to
  `overflow-y: visible` / `overscroll-behavior: auto`.
- Every player dossier grid child can shrink, and the identity row stacks below `sm`; at 390px the
  root and body both remain 380px wide, all five panels stay inside the viewport, and a 500px wheel
  gesture advances the page by 500px. The scorecard forest plot still scrolls horizontally.
- Verification now runs real wheel input at desktop and mobile widths on all 17 routes, checks
  mobile root/body width everywhere, and checks player-panel containment plus the scorecard's
  horizontal plot. All 34 route/viewport interaction checks passed. The harness's existing global
  console-error rule still reported local ESPN CORS and the absent ignored `market.json` fixture;
  neither affected a route or scrolling assertion.
- Verification: 240 web tests passed; production build, the emitted-CSS deploy contract and
  `git diff --check` passed. Lint exited 0 with the same 13 existing React-hook warnings.
- Final pre-deploy reconciliation: local `master` was fast-forwarded over the non-overlapping daily
  ledger commit and now matches `origin/master` at `fdb2252`; only this scoped web fix, regressions,
  lesson and task record are modified.

## Cincinnati live-result identity, round and date integrity (2026-08-17)

- [x] Reproduce the deployed Cincinnati defects with production-shaped fixtures: a 96-entrant /
      128-slot draw whose ESPN numbered rounds are currently one stage too deep, WTA stable-source
      plus ESPN copies of the same result, and a late Ohio match whose UTC day differs from the
      tournament-local day.
- [x] Infer ESPN numbered rounds from every populated numbered stage (including post-bye rounds),
      so 96-entrant Masters events resolve Round 1/2/3 as R128/R64/R32 without regressing 28-, 32-,
      64-, or 128-slot draws.
- [x] Normalize the verified WTA player-name variants that split the current cross-source matches,
      then make the merge collapse the stable-source and ESPN copies while retaining the preferred
      stat-bearing row and propagating the event's `espnId`.
- [x] Convert ESPN competition timestamps to tournament-local calendar dates from a committed,
      offline venue-to-IANA-timezone table, with an explicit UTC fallback for unknown venues.
- [x] Extend `output_problems()` and its blocking regressions to reject duplicate fixture matches
      and any upcoming matchup whose round disagrees with the same pair in the shipped bracket.
- [x] Run focused parser/merge/health/export tests, the full Python suite and Ruff, replay the
      current Cincinnati payload through the corrected seams, run the real output gate and
      `git diff --check`, then append a review reconciled against the latest Git tip.

### Review

- ESPN draw sizing now uses the positional evidence from every populated numbered stage. Replaying
  the current `718-2026` payload yields 32 R128 and 32 R64 completed matches plus 16 R32 upcoming
  matches on each tour; its Sunday-night Ohio results remain on Sunday.
- A committed 331-venue / 84-IANA-zone table localizes ESPN competition and event boundaries with
  a deterministic UTC fallback. Verified WTA aliases now enter through the shared ESPN athlete
  parser, so results, fields and upcoming forecasts use the same historical identity.
- Exact cross-source matches collapse after the producer correction and retain the preferred
  stat-bearing row plus `espnId`. A residual provider round disagreement is not guessed away:
  event identity propagates, both rows survive, and the blocking fixture invariant exposes it.
- The new gate catches all 26 duplicate fixtures in the deployed WTA payload (including reordered
  and Catherine/Caty names), 15 pair-exact upcoming/bracket R16-vs-R32 disagreements, and future
  completed-fixture round drift through the `espnId` now retained in `fixtures.json`.
- Verification: 573 Python tests and Ruff passed; 240 web tests passed; web lint exited 0 with the
  same 13 existing React-hook warnings; `git diff --check` passed. The real local output gate was
  also exercised, but the repository's 12-day-old generated snapshot remains red on 13 pre-existing
  stale Toronto/Montreal and legacy bracket-provenance failures, so it is not evidence for or
  against this fresh-data fix.
- Final pre-publish reconciliation: local `master` and `origin/master` both remain at `6c2fe48`;
  the approved direct push to production is the next step.

#### Final verification addendum

- Exact one-to-one cross-provider result evidence now resolves a round disagreement before the
  ordinary de-dup pass: the stat-bearing row survives with ESPN's `espnId` and factual live round,
  while a bucket containing more than one row from any source remains untouched as ambiguous.
- A fresh all-tour quick replay rebuilt model state for the new aliases and exported 60 unique
  fixtures per tour. ATP exposed 16 predictable Cincinnati matchups and WTA 15; every exported
  Cincinnati matchup is R32, and neither fixture file has a repeated local-date/player-pair key.
- The refreshed real output passed `python -m tennis_model.data.health --gate`. Replay-only
  forecast/Kalshi appends were removed after verification; no user-authored work was discarded.
- Final verification: 572 Python tests and Ruff passed; 240 web tests passed; web lint exited 0
  with the same 13 existing React-hook warnings; `git diff --check` passed.

#### Fixture-round safety addendum

- Completed fixtures now retain `espnId`, and the pre-deploy gate independently compares each
  uniquely located player pair's fixture round with the shipped bracket. This preserves automatic
  correction while ensuring a future bad live-round inference still blocks publication.
- The final suite count is 573 Python tests (the fixture/bracket regression added after the prior
  572-test note); Ruff, 240 web tests, web lint and `git diff --check` all pass.
- `638d02c` is now the tip of both local and remote `master`; this supersedes the earlier review
  note that described the production push as the next step.

## Cincinnati population-baseline follow-up (2026-08-17)

- [ ] Reproduce the production health failure and confirm that only the run-over-run match-count
      sentinel is red after the integrity gate, build, deploy, and live verifier all passed.
- [ ] Advance the explicit match-population contract for the intentional alias-driven
      canonicalization change, retaining same-version count-drop detection.
- [ ] Run the focused population/health/pipeline tests plus the full Python suite and Ruff.
- [ ] Push the follow-up to `master`, monitor the production workflow through the live verifier,
      and verify the deployed health report and Cincinnati JSON online.

#### Production verification addendum

- Push run `32050687617` passed both test jobs, regenerated both tours, passed the blocking
  pre-deploy integrity gate, built and deployed Firebase, and passed live-site verification.
- The public payload has 60 unique date/winner/loser fixture keys out of 60 rows on each tour;
  every predictable Cincinnati upcoming match is R32, and Tiafoe-Sonego is dated 2026-08-16/R64.
- The overall Actions run ended red only in the post-deploy advisory reporter: removing duplicate
  match rows caused the expected one-run population-drop sentinel (ATP 284513 -> 284429; WTA
  129065 -> 128923), then GitHub's Issues API returned 503 after all three reporter retries. The
  new counts were cached, so the next hourly run can clear the transient advisory; the deployed
  artifacts themselves passed both the pre-deploy and post-deploy gates.

#### Automatic recovery confirmation

- The already-queued scheduled refresh `32051806233` then ran the fixed producer from the saved
  baseline and completed successfully end to end: integrity gate, health scan, Firebase deploy and
  live verification all passed. The deployed `health.json` is `ok: true` with no ATP or WTA output
  problems. Subsequent `tasks/**` review commits are ignored by the refresh workflow; deployed
  producer code remains `638d02c`.

### Population-baseline review

- Production run `32050687617` isolated the only red state to the run-over-run match-count advisory;
  both suites, the integrity gate, data build, Firebase deploy, and live verifier had passed.
- `MATCH_POPULATION_VERSION` is now 4 for the alias-driven canonicalization. A deterministic alias
  fingerprint regression makes future alias edits advance that contract deliberately, while the
  existing health regression continues to reject a greater-than-50-row drop inside one version.
- Verification: 129 focused health/export/pipeline tests passed, the full Python suite passed with
  574 tests, Ruff passed, and `git diff --check` passed.
- The deployed Cincinnati payload was independently fetched after the first deploy: both upcoming
  files contain only R32 for event `718-2026`, each fixture file has 60 unique rows, WTA fixtures
  all retain `espnId`, and the site responds HTTP 200 with `no-cache, no-store`.

## Priority correctness, efficiency, and product round (2026-08-17)

### Phase 1 — correctness and evaluation contracts

- [ ] Reproduce the event-boundary contradiction with production-shaped fixtures, correct event
      bounds at the stable-`espnId` producer seam, and add a blocking output invariant plus
      regression coverage for upcoming/fixture dates that fall outside their event contract.
- [ ] Extend the append-only forecast ledger with idempotent, timestamped pending-match snapshots;
      retain first-sighting evaluation unchanged, and have the Kalshi comparison select the latest
      model snapshot at or before the market quote timestamp so the displayed edge is time-aligned.

### Phase 2 — refresh and payload efficiency

- [ ] Benchmark the current quick-refresh seams, then reuse a fingerprinted pipeline health
      manifest (falling back to standalone recomputation when inputs differ) so the hourly workflow
      does not perform the same normalized data merge twice or weaken the independent health gate.
- [ ] Split full/model-bound exports from quick volatile exports, including workflow/cache/mirror
      wiring, so daily-only projections and predictor artifacts are not rebuilt every hour.
- [ ] Replace the monolithic predictor/profile downloads with generation-aware surface/format and
      per-player shards, a shared URL-keyed in-memory request cache with in-flight deduplication,
      and explicit invalidation when tour metadata advances; retain the host's `no-store` contract.
- [ ] Extend pre-upload health and post-deploy serving verification for shard indexes, referenced
      artifacts, generation parity, and stale/missing-file failure modes, with negative controls.

### Phase 3 — product and responsive UI

- [ ] Add a `/matches` Match Center with Live, Upcoming, and Final tabs, event filters, frozen
      pre-match calls where available, shared match-card primitives, and complete loading, empty,
      error, metadata, search, navigation, and accessibility states.
- [ ] Redesign the mobile tournament table around player and title odds, collapse achieved 100%
      stages and secondary ratings into expandable detail, and preserve the information-dense
      desktop presentation.
- [ ] Replace the mobile chip strip with Home, Matches, Players, and Predictor primary actions plus
      an accessible grouped More sheet that keeps every route reachable and marks active state.
- [ ] Export honest component-level prediction context (Elo blend, point model, and final combiner)
      and scheduled-match forecast movement; add “Why this prediction?” UI without presenting the
      component comparison as causal/SHAP attribution, and omit movement when no history exists.

### Verification and review

- [ ] Run focused producer/gate/evaluation/export tests, the full Python suite and Ruff through
      `uv`, the web test/lint/build suite, real-artifact gate replay, and `git diff --check`.
- [ ] Re-run timing measurements, then browser-test every route and interaction at desktop and
      mobile viewports, including direct loads, keyboard behavior, horizontal overflow, and errors.
- [ ] Reconcile the final diff with the current git tip and append a review summarizing behavior,
      measurements, gate coverage, and any deliberately retained compatibility path.

### Priority round review

- [x] Correctness contracts now agree on stable ESPN event identity: tournament bounds union
      calendar, draw, scheduled-competition, and observed-result evidence. The generated ATP
      Cincinnati card spans 2026-08-11..23 while its R32 schedule (Aug 17/18) and latest R64
      fixtures (Aug 16) all pass the new blocking cross-artifact invariant.
- [x] The forecast log retains first sighting for grading and adds one idempotent pending-match
      snapshot per UTC hour. Kalshi rows upgrade only to the latest snapshot at or before the
      frozen quote; legacy unaligned `live` rows remain visible in coverage but are excluded from
      the aligned headline. UTC-aware snapshot compatibility is pinned at both grading and bracket
      pricing consumers.
- [x] A same-input, same-day source-health manifest reduced the measured standalone health pass
      from about 308s (ATP 180s + WTA 128s) to 0.82s; the independent output gate passed in 0.70s.
      Fingerprint/date drift still forces the original standalone merge.
- [x] With static artifacts already present, the measured two-tour quick forecast export fell from
      about 401s (ATP 233.5s + WTA 167.6s) to 112.69s and reported `[volatile only]` for both tours.
      A missing/legacy static set deliberately triggers a one-time full-artifact compatibility build.
- [x] Route payloads now load a generation index plus the selected context/dossier. ATP predictor
      initial JSON is 654,530 bytes versus roughly 1.4 MB previously; WTA is 654,227 bytes versus
      roughly 722 KB. A selected profile is about 106-109 KB including the index versus roughly
      1.1-1.3 MB. Total hosted matrix storage grows to 3.91 MB ATP / 1.96 MB WTA because all three
      honest component matrices are retained, but no route downloads every shard and the home page
      requests none when there is no live card.
- [x] Pre-upload health follows every shard reference and blocks unsafe/missing/corrupt files,
      malformed indexes, component/context/order drift, and model-generation disagreement. The
      post-deploy verifier independently follows every served reference, checks MIME and generation,
      and validates the profile name / exact matrix component contract.
- [x] Product work shipped `/matches` (Live/Upcoming/Final, keyboard tabs, event filters, frozen
      calls and shared explanations), mobile title-first tournament cards, a four-action + More
      mobile nav with focus trapping/restoration, and honest Elo/point/final + movement disclosures.
- [x] Verification against git tip `b461549`: 586 Python tests and Ruff passed; 247 web tests,
      ESLint (0 errors; 9 retained existing effect warnings), and the 24-route production build
      passed; the real-artifact output gate passed; `git diff --check` passed. The route sweep rendered
      36/36 desktop/mobile route checks without overflow. Its final local-only console audit still
      reports ESPN's localhost CORS refusal and the intentionally absent local market.json; the
      in-app browser independently exercised live cards, tab-arrow navigation, ATP/WTA shard swaps,
      and both explanation disclosures successfully.
- [x] Retained compatibility is explicit: legacy date-only first-sighting rows keep grading, the
      legacy in-memory `build_matrix` caller remains, and quick mode self-heals a missing shard set.
      No commit, push, or production deploy was performed in this round.

#### Publication addendum

- The user subsequently authorized direct publication to the repository's default production
  branch. The review above records the validated pre-publication state.

## WTA coverage and lower-ranked state research (2026-08-17)

### Baseline and source findings

- [ ] Preserve the reproduced baseline in the research record: the current production-shaped
      frame has 2025 WTA serve-stat coverage 80.51% and 2026 coverage 86.48%, versus the current
      2026 ATP manifest at 98.62%; WTA 2026 coverage is 95.30% when both players are top 50 but
      only 84.08% when someone is outside the top 50.
- [ ] Record the upstream boundary before changing ingestion: current first-party WTA endpoints
      expose non-zero Montreal/Cincinnati 2026 serve totals and WTA 125 detail from 2016 onward,
      but the probed 2015 125 endpoint has no match detail and the 2025 Slam stats endpoint returns
      zero totals despite official WTA match pages displaying those stats.

### Resumable one-year WTA acquisition

- [ ] Refactor the WTA scraper to classify main draw, qualifying, and both legacy `125K` and current
      `WTA 125` vocabularies from content; keep main-draw rows in `stats/` and write qualifying/125
      rows to a distinct WTA lower-tier overlay with explicit `draw_level` and challenger-strength
      tier semantics.
- [ ] Make completed-season acquisition resumable and non-regressive at match/event granularity,
      preserve source match IDs, reject zero/inconsistent stat payloads, and enforce exactly one
      requested backfill year per command so API throttling cannot turn a multi-year run into a
      silent partial archive.
- [ ] Repair the current season incrementally, then backfill exactly one completed WTA year per run
      (starting with 2025 and proceeding backward only after the prior year's census is accepted),
      recording main/lower row counts, event holes, rank-band coverage, hard failures, and cache
      reuse after every year rather than treating a successful process exit as proof of coverage.

### State-only experiment and admission boundary

- [ ] Separate WTA lower-state inclusion from the existing event/display policy, and make the
      production combiner training boundary enforce main-draw admission by default. Lower rows may
      update Elo, serve/return, experience, and context states; allowing them into combiner fitting
      must require an explicit research-only opt-in and a production-shaped regression test.
- [ ] Extend the data A/B harness with a WTA lower-state experiment: baseline and arm must score the
      identical main-draw rows, the arm alone walks qualifying/125 history, and reporting must cover
      tune 2010-19, validation 2020+, every affected year, top-50 involvement, and the frozen Kalshi
      subset involving players outside the top 50.
- [ ] Adopt state-only ingestion only if the full walk-forward arbiter passes, affected-year deltas
      are stable rather than bidirectional many-SE swings, and the lower-ranked/Kalshi slices do not
      reveal a concentrated regression. Do not admit lower rows to combiner training in this round;
      a later full-distribution experiment would need its own gate and explicit approval.

### Verification and review

- [ ] Add parser, pagination/cache/resume, legacy-level, partial-event, row-labelling, state-update,
      combiner-exclusion, population-audit, and real-census regressions; run focused tests, the full
      Python suite and Ruff through `uv`, source health, output health, and `git diff --check`.
- [ ] Re-run `git log` before finalizing metrics or adoption claims, append the measured coverage and
      A/B results plus retained upstream holes to this round, and leave all plan items explicitly
      checked or rejected with evidence.

## Radar Elo simplification (2026-08-17)

- [x] Replace the shared Hard/Clay/Grass Elo radar axes with one overall Elo axis and remove
      break-point clutch from the radar, so the player dossier and comparison share 10 axes.
- [x] Thread overall Elo into the shared radar population from `players.json` in both consumers;
      keep the change compatible with the cached `profile-index.json` used by web-only deploys.
- [x] Update every user-facing 13-axis/surface-Elo reference in the Playing Style page, navigation,
      route metadata, tests, and README screenshot to the new 10-axis contract.
- [x] Add focused regressions that pin the single overall-Elo axis and reject the three
      surface-specific axes, then run the relevant web tests, lint, and production build.
- [x] Visually verify both radar consumers at desktop and mobile widths, re-run `git log`, and append
      a review with the final category decision, measured checks, and any retained compatibility path.

### Radar Elo simplification review

- Both radar consumers now render 10 axes: seven durable playing-style dimensions, overall
  serve/return strength, and one Overall Elo percentile. Break-point clutch was removed from the
  radar and comparison stat lines because it is noisy and outcome-like, but remains available in
  the dossier's separate Match Charting stat list.
- Overall Elo is joined from the current `players.json` roster before building either tour-relative
  percentile field. This deliberately supports the cached pre-change `profile-index.json` reused by
  a web-only deploy, so the new spoke cannot silently collapse to a missing-value zero.
- Against git tip `8abe7d7`, all 249 web tests and the 24-route production build passed; ESLint
  completed with 0 errors and the same 9 existing effect warnings; `git diff --check` passed.
  Browser checks covered both consumers at 1440px and 390px, found 10/10 expected labels, no
  horizontal overflow, and no console errors. `docs/style.png` now shows the 10-axis chart.
  No commit, push, or production deploy was performed.

## Upcoming match style links (2026-08-17)

- [x] Give eligible upcoming cards on `/matches` the same whole-card Playing Style drill-in as
      live cards and the legacy `/schedule` board, while preserving individual player links and
      leaving unrated matchups unlinked.
- [x] Extend the match-center regression contract and run focused web tests, lint, and
      `git diff --check`.
- [x] Re-check the deployed-shaped interaction locally, reconcile with the current git tip, and
      append a concise review with the verification result.

### Upcoming match style links review

- Eligible `/matches` upcoming cards now use the shared `CallCard` matchup link guarded by the
  rated-player roster. Individual name links remain above the stretched card link, and a real
  unprofiled Jannik Sinner–Clement Tabur card remained plain in browser verification.
- The post-deploy gate now requires `upcoming-style-links-v1` in the served `/matches/` HTML, with
  unit coverage for present, missing, and stale markers. The match-center source contract pins the
  guarded `hasMatchupProfiles(match, roster)` wiring.
- Against git tip `8abe7d7`, all 248 web tests and the 24-route production build passed; ESLint
  completed with 0 errors and the same 9 existing effect warnings; `git diff --check` passed.
  A local card click opened `/style/?a=Rafael+Jodar&b=Alejandro+Tabilo`, and both Playing Style
  selectors resolved to those exact players. No commit, push, or production deploy was performed.

## Interactive scenarios, forecast timelines, and expectation-adjusted form (2026-08-17)

Implementation begins only after the user approves this plan. The three features share a forecast-
history identity layer, but scenario calculations remain separate from the append-only evaluation
ledger: user-selected outcomes are hypothetical UI state and must never enter grading or model state.

### Product contracts and shared foundations

- [ ] Define one versioned, orientation-safe match identity for new forecast records: stable
      `espnId` when present plus season, round, and the canonical unordered player pair; retain a
      unique legacy fallback for old name-keyed rows, reject ambiguous same-pair rematches, and
      never join on an event display name when a stable id exists.
- [ ] Add a pure forecast-history builder that reads the append-only ledger, normalizes every
      probability to a declared subject player, deduplicates the first-sighting record and its
      same-hour snapshot into one observation, preserves the immutable first-sighting forecast for
      grading, and exposes distinct pending timelines and graded per-player evidence.
- [ ] Extend new hourly snapshots with the already-computed Elo/point/final components and explicit
      model/data provenance where available. Legacy snapshots remain valid with a final probability
      only; no copy may infer a causal reason for a movement the ledger did not record.
- [ ] Refactor the refresh order so event/upcoming artifacts exist, the current hour is logged and
      graded, and then the volatile forecast-derived artifacts are written and mirrored in the same
      run. Quick and full paths must use the same post-track producer and must not leave the newest
      point one refresh behind.

### Feature 1 — interactive bracket scenario lab

- [ ] Add a deterministic exact-probability propagation engine for a fixed single-elimination
      bracket, using the model's pairwise probabilities while preserving real bracket adjacency,
      byes, settled results, unresolved unique seats, withdrawals, and the current live frontier.
      Use it for real-event reach/title odds so the published baseline and interactive recalculation
      cannot disagree through Monte Carlo sampling noise; retain Monte Carlo for the separate
      hypothetical-field simulator unless a later scope explicitly replaces it.
- [ ] Export a lazy event-scoped scenario index and shard keyed by `espnId`, containing version and
      model generation, ordered bracket geometry, deterministic round/match ids, immutable settled
      winners, scenario-eligible unresolved matches, and the complete event-field pairwise matrix.
      Fail closed when event identity, geometry, or model coverage is insufficient; display names
      and provider ids are never scenario keys.
- [ ] Build a TypeScript mirror of the exact propagation engine and pin it to Python fixtures for
      8-, 28/32-, 48/64-, 96/128-, and 128-player shapes, including byes, placeholders, mixed
      decided/pending rounds, orientation swaps, and a locked underdog result. Baseline reach/title
      odds must match the producer within serialized rounding.
- [ ] Add a Scenario mode to `/bracket`: users can choose the winner of any currently unresolved
      real matchup, see title/reach odds and the largest beneficiaries update immediately, undo the
      latest choice, reset all choices, and distinguish hypothetical locks from actual results by
      text/icon as well as color. Settled matches and unresolved placeholder-vs-unknown matches are
      not editable.
- [ ] Make scenarios shareable with compact URL state based on event id plus deterministic match
      ids, not player names. Apply URL-to-state only on navigation, canonicalize legacy event-name
      links without breaking them, discard stale/impossible locks after a data refresh, and support
      keyboard selection, focus restoration, reduced motion, and a complete mobile layout.
- [ ] Add an impact summary for each scenario: title-odds delta for the selected winner, the largest
      beneficiary elsewhere in the draw, and updated most-likely semifinal/final paths. Label all
      deltas “if selected results occur”; never write them into the forecast ledger or track record.

### Feature 2 — point-in-time forecast timeline

- [ ] Export the full unique-hour probability series for every live/upcoming match and recent
      tracked final, oriented to the player shown on the card. Include first/latest timestamps,
      first/current/delta, unique observation count, and optional component values without changing
      the first-sighting grading contract.
- [ ] Decorate `upcoming.json` and the recent `fixtures.json` rows after the current snapshot is
      logged, using the shared stable identity. Handle player-order reversal, sponsor-title changes,
      legacy date-only rows, missing component history, a single observation, and an ambiguous
      rematch by either producing the correct series or omitting it explicitly—never attaching the
      wrong match's history.
- [ ] Replace the current movement-only disclosure on Match Center cards with an accessible chart
      and compact table showing timestamp, player-oriented probability, and change in percentage
      points; keep the first/current summary visible when collapsed. Reuse the same component on the
      Match Predictor when its selected pair/surface/format resolves to a scheduled match.
- [ ] Give completed matches a frozen final timeline on the Final tab, mark the published pre-match
      call separately from later pending snapshots, and state that movement records model/data
      refreshes rather than market movement or a causal explanation.

### Feature 3 — performance versus model expectation

- [ ] Derive the metric only from graded, genuine first-sighting `match` records: for each player,
      over their latest ten eligible tracked calls, expected wins are `sum(P(player wins))`, actual
      wins are observed wins, and performance versus expectation is `actual - expected`. Hourly
      snapshots, retro estimates, walkovers, unresolved/ambiguous joins, and hypothetical scenarios
      are excluded.
- [ ] Produce a compact tour-level expectation index plus per-player detail in the existing lazy
      dossier flow. Each detail row carries date, event, opponent, surface, pre-match probability,
      result, and signed residual; every aggregate carries its exact `n` and as-of time. Preserve
      profiles with no eligible calls and never present fewer observations as a ten-match sample.
- [ ] Add a “Performance vs expectation” card and evidence list to `/player`: for example,
      “7 wins from 5.4 expected across 10 tracked forecasts (+1.6).” Use neutral above/below wording,
      emphasize sample size, and explicitly say this is descriptive live-track performance rather
      than proof of luck, clutch ability, or a new predictive model feature.
- [ ] Add an expectation-based section to `/trends` only for players meeting a pinned minimum
      sample. Rank comparable latest-ten residuals, keep raw Elo risers/fallers as a separate concept,
      and provide an honest insufficient-history state while the ledger continues to accrue.
- [ ] Keep expectation-adjusted form out of `FEATURES`, predictor state, and simulation inputs in
      this round. Any later proposal to feed the residual back into the model requires its own
      leakage-free walk, prediction-time mirror, paired-SE validation, and full walk-forward arbiter.

### Integrity gates and compatibility

- [ ] Extend the pre-upload output gate for scenario shard references, event/model generation
      parity, bracket membership and geometry, matrix bounds/diagonal/antisymmetry, probability
      conservation, reach monotonicity, and locks that contradict settled results. Exercise the
      legitimate calendar shapes and messy draw states rather than only the current event.
- [ ] Extend post-deploy verification to follow every scenario index reference and validate strict
      JSON, served generation, event identity, and the route's scenario/timeline contracts. Forecast
      timeline and expectation products should degrade to explicit unavailable/insufficient states
      when the best-effort ledger is absent, while any produced invalid probability or mismatched
      identity remains blocking.
- [ ] Preserve legacy forecast logs, legacy bracket event-name URLs, cached pre-component snapshots,
      quick-mode static profile shards, and tours/events with no complete draw. Add migrations or
      read-time adapters rather than rewriting the append-only historical ledger.

### Verification and review

- [ ] Add focused Python tests for exact conditional bracket math, Python/TypeScript parity fixtures,
      snapshot idempotency/orientation/dedup, rematch ambiguity, first-sighting immutability,
      expectation aggregation/exclusions, post-track refresh ordering, shard generation, and every
      new health invariant. Run the full Python suite and Ruff through `uv`.
- [ ] Add focused web tests for scenario reducer/URL state, locked-versus-settled presentation,
      probability conservation, timeline rendering and tabular fallback, player expectation copy,
      insufficient states, keyboard/focus behavior, and tour/event navigation. Run all web tests,
      ESLint, the production build, post-deploy verifier tests, and `git diff --check`.
- [ ] Rebuild real ATP and WTA artifacts and audit at least one full draw, one bye-heavy draw, one
      active partial frontier, one sponsor-renamed event, one single-point timeline, one orientation-
      reversed timeline, and player dossiers above/below/without expectation history. Browser-test
      `/bracket`, `/matches`, `/predict`, `/player`, and `/trends` at desktop and mobile widths.
- [ ] Before finalizing facts or screenshots, re-run `git log`, compare exact-propagation baselines
      with the previously published Monte Carlo outputs to confirm changes are sampling-only, replay
      the real-artifact pre-upload gate, and append a review with payload sizes, performance timings,
      coverage counts, verification results, and any deliberately retained degradation path.

### Full bracket presentation addendum — GAFFER reference (2026-08-17)

The reference is `ARJUNVARMA2000/wc-2026-gaffer` `/bracket`: a symmetric connected tree with
settled scores, open-match odds, forward-filled likely winners, candidate-occupancy tooltips, a
centered final/champion card, and an advancement funnel. DEUCE already owns the harder factual
inputs—ordered 28/32/48/56/64/96/128 draws, live results, frozen pre-match calls, and current title
odds—so this round adapts that presentation without confusing projections with confirmed entrants.

- [ ] Evolve the existing `/bracket` page rather than create a competing route. Add explicit
      `Actual draw`, `Forecast path`, and `Scenario` modes: Actual preserves the source-faithful
      sectioned bracket and never fills unknown future participants; Forecast renders the model's
      most likely connected path; Scenario starts from that same forecast tree and applies the
      user's hypothetical locks.
- [ ] In Forecast/Scenario modes, render a GAFFER-style symmetric tree with the final and projected
      champion centered. Completed matches show the real score, winner, upset mark, and frozen call;
      known open matches show head-to-head odds that sum to 100%; future slots show a visibly
      projected leading occupant and that slot's reach/occupancy probability—not a mislabeled
      head-to-head probability.
- [ ] Export top candidate distributions for every projected downstream slot, not only one chalk
      name. Hover, focus, or tap reveals who could occupy the slot and at what conditional
      probability; the chosen projection is highlighted, Escape dismisses, and every tooltip has
      equivalent screen-reader text and a non-hover mobile interaction.
- [ ] Adapt the 32-team reference to tennis draw scale deliberately: keep early 48/56/96/128 draws
      in the current detailed section navigator, add a compact whole-draw progress/minimap, and add
      a consolidated `Finals picture` that forward-fills the eight QF branches into one centered
      QF→SF→F→Champion tree. As actual play reaches a 32-player-or-smaller frontier, allow the full
      surviving tree to use the symmetric forecast presentation directly.
- [ ] Add a round-by-round advancement funnel below the tree, driven by the same reach distribution
      as the bracket. Selecting or focusing a player traces their route in both surfaces; filters
      cover alive players, seeds, and surface specialists, while negligible rows use a documented
      display threshold without changing probability totals.
- [ ] Reuse one match-card semantic contract across the three modes, but keep confirmed,
      model-projected, and user-forced states distinct by label/icon as well as color. Player names
      retain dossier links, eligible known matchups retain Playing Style links, and interactive
      winner controls must not be masked by stretched navigation links.
- [ ] Pin presentation/data parity against the reference-inspired contracts: in-order tree geometry,
      left/right feeder adjacency, a+b open-match odds = 1, candidate slot occupancy sums within
      serialized tolerance, settled winners advance exactly, forecast winners are reversible, and
      Actual mode contains no projected entrant. Browser-verify a 96/128 draw, a 32 draw, a live
      partial frontier, a completed event, keyboard tooltips, touch disclosure, horizontal scrolling,
      and mobile section/finals navigation.
- [ ] When a slot tooltip truncates its candidate list for readability, export and display the
      residual “other paths” mass; assert shown candidates plus that residual equals the full slot
      occupancy probability so the compact list never implies that a partial ranking is exhaustive.

## Matches worth watching and prediction evidence 2.0 addendum (2026-08-17)

Implementation still begins only after the user approves the expanded round. Feature 5 consumes the
exact conditional title distributions from Feature 1, while Feature 6 extends the same versioned
match/evidence record used by upcoming cards, forecast timelines, and the predictor matrix shards.

### Feature 5 — matches worth watching

- [ ] Add a pure, versioned watch-score contract for every predictable upcoming match. Pin a
      transparent 100-point weighting—30 closeness, 25 player quality, 15 style contrast,
      15 tournament stakes, and 15 title-odds leverage—and ship each 0–100 factor, the total,
      evidence-coverage flags, and deterministic tie-break fields. Call this a product ranking,
      not a forecast of entertainment quality, and keep the underlying win probability unchanged.
- [ ] Define the factors from stable model/data facts: closeness is the bounded distance from
      50/50; quality uses both players' surface-blended Elo percentiles rather than public rank;
      style contrast is tour-relative distance across the model's durable charting dimensions only
      when both profiles have adequate coverage; stakes combines the normalized tournament tier and
      knockout round; missing optional evidence contributes no bonus and remains visibly unavailable
      rather than being silently imputed as average.
- [ ] Compute title-odds leverage from Feature 1's exact engine as the total-variation distance
      between the complete conditional champion distributions when player A versus player B is
      locked as the winner. Join only through `espnId` plus the scenario match id/generation; never
      attach leverage by event title or player pair alone, never reuse a stale generation, and mark
      it unavailable when ordered geometry or model coverage is insufficient.
- [ ] Decorate `upcoming.json` after event/scenario outputs exist, preserving its current
      soonest-first source order for schedule consumers while adding `watchRank` and the factor
      breakdown. Give equal totals a stable order by date, event id, round depth, and canonical
      unordered pair so hourly refreshes do not reshuffle ties.
- [ ] Add a ranked “Matches worth watching” surface to the Upcoming tab on `/matches`, with the top
      cross-event cards first and the complete event-by-event chronological schedule retained below.
      Each ranked card exposes its five-factor breakdown, missing-evidence state, current model call,
      style/predictor links, and scheduled time; replace the home page's closeness-only insight with
      the same top-ranked contract so two definitions of “match to watch” cannot drift.
- [ ] Keep ranking distinct from chronology and lifecycle: never promote a completed/in-progress
      row as upcoming, never hide an eligible scheduled row because it lacks style or bracket data,
      and do not let a marquee tier override all other factors. Verify keyboard order, compact factor
      disclosure, touch behavior, long names, and narrow-screen horizontal bounds.

### Feature 6 — prediction explanation 2.0

- [ ] First restore prediction-time parity for the evidence this feature names. Carry the context
      walk's recent dated workload into `H2HState`, pass the scheduled match date/as-of through the
      real-upcoming path, and mirror training's days-since, clipped rest, fatigue, layoff, form, H2H,
      surface H2H, event/host, tier, and round inputs. Hypothetical predictor contexts without an
      event retain an explicit neutral/unavailable home signal; legacy pickles fail the existing
      quick-mode compatibility guard and rebuild rather than fabricating context.
- [ ] Add one orientation-safe `prediction_evidence` primitive over the exact row sent to the
      combiner. Group the named signals into surface Elo, serve/return, form, rest/workload, home
      advantage, H2H, and style; for each group ship player-oriented source facts, availability,
      direction, and signed probability-point sensitivity obtained by neutralizing that input group
      while holding the other model inputs fixed. Rank by absolute sensitivity, but never claim the
      groups are independent, additive, causal, or SHAP explanations.
- [ ] Make each evidence row interpretable without reverse engineering a score: surface-blended Elo
      and its gap; point-model probability plus serve/return skill edges; 90-day Elo form and recent
      win rate; days since play and recent workload; identified host player; overall/surface H2H
      records with sample counts; and the largest available charting-style contrasts. Withhold a
      category when its prerequisites are missing rather than turning missing data into a narrative.
- [ ] Extend scheduled-match payloads and new forecast snapshots with the compact evidence schema.
      Extend lazy matrix shards with the seven signed sensitivity matrices needed for arbitrary
      `/predict` pairs, generated in batches from the same feature rows; keep detailed source facts
      in the smaller player/profile indices or selected upcoming row so the static app does not ship
      per-pair prose. Record schema/model generation and preserve legacy component-only snapshots.
- [ ] Replace `PredictionWhy` and the predictor's current three-number disclosure with one shared,
      accessible “Model evidence” component: lead with the strongest available signals, allow all
      seven categories to expand, show which player each signal supports and by how many model
      percentage points, retain Elo/point/final component agreement, and provide a compact semantic
      table fallback. The standing label says these are model sensitivities/evidence, not reasons an
      athlete will win and not claims about real-world causation.
- [ ] Keep historical honesty: a completed or earlier timeline point may show only evidence actually
      recorded at that time; do not recompute it with today's ratings, form, H2H, style data, or model.
      Single-observation, component-only legacy, absent-style, neutral-home, and orientation-reversed
      matches all receive explicit, non-misleading states.

### Addendum integrity, verification, and review

- [ ] Extend the pre-upload gate for finite/bounded watch totals and factors, complete unique ranks,
      exact score recomputation, eligible-upcoming membership, stable tie ordering, scenario
      generation/match identity, title-leverage conditional distributions, evidence group vocabulary,
      signed orientation, and source-fact bounds. Extend post-deploy verification with the served
      watch/evidence schema markers; unavailable optional evidence degrades, while wrong identity,
      impossible probabilities, stale generations, or internally inconsistent totals block.
- [ ] Add focused Python tests for every factor boundary, missing-evidence behavior, style coverage,
      tier/round stakes, exact title-leverage math, stable ordering, train/inference rest and fatigue
      parity, date orientation, grouped neutralization, bagged/calibrated prediction behavior, and
      legacy predictor/log compatibility. Add TypeScript tests for ranking/filter preservation,
      player-order reversal, evidence sorting/copy, unavailable categories, keyboard disclosure, and
      the shared home/match-center/predictor contract.
- [ ] Measure full and quick export time plus lazy-shard and `upcoming.json` byte growth before
      accepting the schema. Run the full Python suite and Ruff through `uv`; run web tests, ESLint,
      production build, deploy-verifier tests, and `git diff --check`; rebuild both tours and audit
      at least one high-leverage late-round match, one close lower-tier match, one style-covered pair,
      one uncharted pair, one home player, one id-less/no-bracket event, and one reversed orientation.
      Browser-test the ranked list and evidence component at desktop/mobile widths, re-run `git log`,
      and append a review with score distribution, factor coverage, payload/timing measurements, and
      retained degradation paths.

## Interactive scenario, forecast timeline, and expectation implementation review (2026-08-17)

- [x] Shipped a versioned, orientation-safe forecast identity and immutable legacy adapter. New
      records prefer `espnId`; a pre-ID row is bridged only by one real-player/season/round candidate,
      one nearby registry ID, and the 21-day evidence window. Sponsor names never participate, and
      ambiguous pair rematches still fail closed. Hourly histories retain recorded Elo/point/final
      components and evidence, deduplicate same-hour provenance, and keep the first call unchanged.
- [x] Shipped exact fixed-draw propagation in Python and TypeScript, event-scoped lazy scenario
      shards, stable match IDs, settled-result protection, exact conditional title leverage, URL-
      shareable picks, reset/undo behavior, and a GAFFER-inspired connected QF→SF→F→Champion view.
      Actual draw remains source-faithful; Forecast and Scenario label projected and user-forced
      states separately, expose candidate/residual occupancy, and share the same reach funnel.
- [x] Shipped the saved forecast timeline on upcoming and completed Match Center cards and on the
      Predictor when its selected context matches a scheduled call. The semantic table records time,
      probability, components, version, and first-call status; copy states that movement represents
      model/data refreshes, not a market move or causal event.
- [x] Shipped latest-ten actual-minus-expected performance from genuine graded first sightings only,
      excluding walkovers, snapshots, ambiguous/pending results, and scenarios. Compact tour indices
      and lazy player details power dossier evidence and minimum-sample Trends lists. The display is
      explicitly descriptive and the residual is absent from training features and simulation state.
- [x] Extended both release gates. Pre-upload validation now follows scenario references and checks
      identity/generation, matrix complementarity, exact baseline conservation, geometry, timelines,
      and performance arithmetic. Post-deploy contracts follow scenario/profile artifacts and require
      the bracket, Match Center, evidence, and dossier route markers. Regression tests cover JSON-list
      matrices and the legacy-ID migration failure that real WTA history exposed.
- [x] Rebuilt real ATP and WTA outputs. Each tour currently publishes one live Cincinnati 96-player /
      128-slot, seven-round scenario with 14 editable real matchups. Exact champion mass is within
      serialized tolerance of 1.0 and agrees with the tournament display to four decimals. Lazy shard
      sizes are 949,103 bytes ATP and 943,292 bytes WTA; compact performance indices are 23,436 and
      23,694 bytes. They cover 183 ATP and 185 WTA players. Upcoming timelines cover 75/75 ATP rows
      and 72/72 WTA rows; WTA also exercises the honest single-observation state.
- [x] Real-data browser QA covered the connected bracket and a shareable underdog lock, candidate
      tooltips/residual mass, desktop and narrow mobile containment, Match Center disclosure and
      frozen timeline table, and above/below expectation dossier and Trends states. It also exposed
      and fixed stretched whole-card links intercepting the adjacent evidence disclosure.
- [x] Final verification against git tip `8abe7d7`: `622 passed` in the full Python suite; Ruff passed;
      `260 passed` across 21 web files; ESLint completed with zero errors and the same nine existing
      React effect warnings; all 24 static routes built successfully; the real-artifact
      `data.health --gate` passed; and `git diff --check` passed. Quick real-data export took 75.2s
      ATP and 53.3s WTA after shared acquisition.

Retained fail-closed paths: an event without a stable registry ID, complete ordered geometry, or full
model coverage receives no Scenario shard and keeps Actual draw; a legacy/ambiguous forecast receives
no guessed timeline; insufficient player history is labelled as such; scenarios can lock only currently
known unresolved matchups and never projected future pairings. No commit, push, or production deploy was
performed, and unrelated in-progress WTA coverage and other local workspace changes were preserved.

## Matches worth watching and prediction explanation 2.0 implementation review (2026-08-17)

- [x] Shipped `watch-v1` on every predictable upcoming row with the pinned 30/25/15/15/15
      weighting, stable ranks, explicit factor availability, and no change to match probabilities or
      chronological schedule order. The Match Center and home page share the same ranking contract;
      copy identifies it as a product ranking rather than a prediction of entertainment quality.
- [x] Shipped exact title-odds leverage through the scenario generation and stable match identity,
      plus bounded closeness, surface-Elo quality, charted style contrast, and tier/round stakes.
      Missing style or scenario coverage contributes no bonus and remains unavailable. On the real
      artifacts, ATP scores span 34.8–67.2 (mean 53.2) and WTA scores span 27.0–66.9 (mean 51.5).
      Style is available for 52/75 ATP and 53/72 WTA matches; exact title leverage is available for
      the 13 ATP and 12 WTA known open matches that join to the released Cincinnati geometry.
- [x] Shipped `evidence-v1` over the exact inference row, grouped into surface Elo, serve/return,
      form, rest/workload, home advantage, H2H, and style. Each group carries availability, oriented
      facts, supporting player, and signed neutralization sensitivity. The shared UI leads with the
      strongest signals and permanently labels them model evidence—not causal or additive reasons.
- [x] Restored prediction-time context parity for dated workload/rest/form, H2H, host country,
      tournament tier, and round. New forecast snapshots freeze evidence at first sighting; historical
      cards do not recompute it. All real upcoming rows have Elo, point, form, rest, and home evidence;
      H2H covers 69/75 ATP and 66/72 WTA, while style follows the 52/75 and 53/72 charting coverage.
- [x] Added compact upper-triangle basis-point evidence arrays to lazy predictor shards with
      orientation-safe browser decoding. Final hard-Bo3 matrix shards are 457,454 bytes ATP and
      466,253 bytes WTA, replacing the initial roughly 2.8 MB pretty-printed prototype and remaining
      below the earlier component-only predictor payload noted in this log. Upcoming payloads are
      601,582 bytes ATP and 588,474 bytes WTA; scenario and performance payload sizes remain 949,103 /
      943,292 and 23,436 / 23,694 bytes respectively.
- [x] Extended the pre-upload and post-deploy contracts for ranking arithmetic, factor bounds,
      identity/generation joins, seven-group evidence vocabulary/orientation, scenario conservation,
      timelines, and performance arithmetic. Real ATP/WTA outputs pass `data.health --gate`; malformed
      or stale identity, probability, evidence, and score states fail closed, while missing optional
      style/bracket inputs degrade honestly.
- [x] Final verification against git tip `8abe7d7`: 624 Python tests passed; Ruff passed; 261 web
      tests passed; ESLint completed with zero errors and the same nine React effect warnings; all 24
      static routes built; and `git diff --check` passed. Browser QA covered desktop and 390px Match
      Center ranking/evidence, arbitrary Predictor evidence, exact Scenario locking/URL/undo impact,
      player and Trends performance, and found no horizontal overflow or browser console errors.

No commit, push, or production deploy was performed. Generated forecast and Kalshi ledger verification
diffs were removed after the real-artifact audit, and unrelated in-progress workspace changes remain
untouched.

## WTA coverage and lower-ranked state research review (2026-08-17)

- [x] Reproduced the starting gap and repaired current-season acquisition. WTA 2026 moved from
      86.48% serve-stat coverage to 95.78% (1,817/1,897), versus ATP's current 98.59%; the
      non-both-top-50 population moved from 84.08% to 95.36%. WTA 2025 remains 80.51%
      (2,008/2,494; non-both-top-50 80.34%) because the first-party API still returns zero usable
      totals for Australian Open, Roland Garros and Wimbledon rows despite official match pages
      displaying stats. The retained 2025 holes are AO 127, RG 127 and Wimbledon 64 matches.
- [x] Refactored first-party WTA acquisition around one explicit year and main/lower/all scope.
      It now handles legacy/current level vocabularies, qualifying versus WTA 125 roles, the
      provider account header, stable source match IDs, zero/inconsistent payload rejection,
      response-cache resume, deterministic-404 versus transport failure, non-regressive match
      union and atomic year writes. A retry-exhausted outage aborts the year; a historical cached
      404 remains a measured source hole rather than manufacturing an outage.
- [x] Backfilled and individually censused 2016–25 lower data, one completed year per process:
      564, 1,104, 1,152, 1,247, 652, 1,337, 1,731, 1,970, 2,207 and 2,786 rows respectively.
      The ten files contain 14,750 raw rows / 14,561 stable source identities; the production-shaped
      arm retains 14,560 rows (9,009 qualifying, 5,551 WTA 125) after exact boundary dedup and
      cleaning. Every written row has a positive serve total and nonblank unique event/source ID.
      The 2016–19 API is increasingly patchy, and 2015 WTA 125 detail remains unavailable, so 2016
      is the honest start boundary.
- [x] Hardened population admission. Lower files are always read as classification evidence so a
      higher-priority historical duplicate cannot survive as falsely-main, but their unique rows
      enter state only behind the WTA-specific flag. Baseline and state arms contain the identical
      128,822 main rows. Walk-forward and final training centrally filter to main by default; lower
      combiner fitting requires an explicit research-only `allow_lower=True`. Production
      `INCLUDE_WTA_LOWER_STATE` remains false.
- [x] Made the state A/B genuinely chronological. The first run changed 2010 predictions because
      serve league/surface priors were aggregated over the whole augmented frame. The corrected arm
      freezes those priors on the identical main population and now hard-fails unless every
      pre-2016 prediction is bit-identical; final 2010–15 deltas are exactly zero.
- [x] The corrected combined qualifying+125 state arm formally passes the headline arbiter:
      tune d=+0.00012±0.00030, validation d=+0.00127±0.00086 and full d=+0.00054±0.00037.
      Affected outside-top-50 matches improve +0.00164±0.00076 and the frozen Kalshi/outside-50
      subset improves +0.00391±0.00507 (n=351), but both-top-50 matches regress
      -0.00169±0.00055. Qualifying-only adds negligible target benefit (+0.00023±0.00064) and
      worsens the Kalshi slice; WTA-125-only improves the target slice but fails tune
      (d=-0.00001±0.00015). Because the only passing combined arm has a concentrated ~3-SE
      top-50 regression, state ingestion is not adopted globally and no lower rows are admitted to
      combiner training. A later targeted/dual-state design needs its own full gate.
- [x] Verification against git tip `8abe7d7`: 627 Python tests passed; repository-wide Ruff passed;
      WTA source health reports results/stats through 2026-08-17 with 95.78% current-season stats
      and zero output problems; the independent pre-upload output gate passed; `git diff --check`
      passed. Raw WTA lower CSVs and response caches remain local/ignored research data. No commit,
      push, release-asset mutation or production deploy was performed; unrelated concurrent
      scenario/watch/evidence changes were preserved.

## Branded domain and automated X publishing plan (2026-08-17)

Status: proposed for owner approval; no domain purchase, account action, credential change, post, or
production implementation has been performed.

- [ ] Lock the public brand before social launch. Prefer `deuceforecast.com` (no RDAP registration
      record found on 2026-08-17; the registrar checkout remains authoritative), keep DEUCE as the
      product name, and check the matching X handle before purchase. Register the domain in the
      owner's account with 2FA, WHOIS redaction, DNSSEC, auto-renew, and a recovery contact.
- [ ] Attach the apex and `www` domain to the existing Firebase Hosting site rather than rebuilding
      or migrating it. Choose one canonical hostname and redirect the other; keep the current
      `web.app` address working. Update `SITE_URL`, metadata/canonicals, JSON-LD, OG/Twitter cards,
      README links, sitemap/robots output, deployment environment URL, and the live verifier. Prove
      the new origin, redirects, certificate, cache headers, deep links, and fresh data live before
      using it in a post.
- [ ] Create one official DEUCE X account and developer app. The profile should disclose that posts
      are automated model forecasts, link the human operator through X's automated-account label,
      and use matching avatar/header/bio assets. Store OAuth/API credentials only as scoped GitHub
      Actions secrets; enable a developer-console spend cap and alerts.
- [ ] Build a separate `social` publisher that can never delay or block the hourly model refresh.
      It reads the latest successfully deployed public JSON—not training state—and posts only when
      live `health.json` is green, its `generatedAt` matches the verified deploy, and every cited
      event/player/probability is still present in that release.
- [ ] Make fact selection deterministic. Candidate types are: morning ATP/WTA “matches worth
      watching” slate; one match spotlight with probability and the strongest available evidence;
      an exact title-race/scenario change when a connected draw exists; riser/faller or graded
      track-record context; and an occasional model explainer. The model may phrase supplied facts
      but may not invent, recalculate, browse for, or silently omit their provenance. Slate and
      spotlight candidates must be imminent on the published schedule before watch rank or event
      prestige is considered, so a future draw cannot crowd today's active tournament out.
- [ ] Target up to two useful posts per day rather than forcing two near-duplicates: a morning slate
      around 09:00 ET and an afternoon/evening spotlight around 17:30 ET, alternating ATP/WTA lead
      position and skipping a slot when freshness, novelty, or coverage fails. Never auto-post on
      trends, tag players, reply, like, follow, DM, or repost as an engagement tactic.
- [ ] Add a constrained AI copy step in the isolated social workflow, reusing the existing
      standard-library OpenRouter transport pattern. Require structured output, one truthful hook,
      one canonical deep link with a campaign code, at most one relevant hashtag, an explicit
      model/as-of cue, and ordinary-post length below 280 characters. Reject betting guarantees,
      injury/news speculation, causal claims, harassment, clickbait, unsupported superlatives, and
      any number/name absent from the source packet; use a tested deterministic template if the AI
      call is unavailable or its output fails validation.
- [ ] Render consistent, code-generated PNG graphics rather than fresh generative art: (1) a
      matchup probability card, (2) a three-match daily slate, (3) a title-odds/scenario swing card,
      and (4) a weekly calibration/track-record card. Use the site's typography and palette, a safe
      single-image aspect ratio, large mobile-readable labels, non-color cues, an “as of” timestamp,
      model-forecast labeling, and no unlicensed player photos, tour logos, or broadcaster assets.
      Generate and attach concise alt text from the same validated fact packet.
- [ ] Add at-most-once publication semantics. Serialize the workflow; build, render, and validate
      before reserving a date/slot/content hash in a durable `social-state` branch; check the recent
      account timeline before the write; and fail closed on an unavailable dedupe check or an
      ambiguous API response. Record the exact source packet, copy, graphic hash, post ID/URL, model
      response, validation result, and failure reason without recording secrets.
- [ ] Gate the new user-facing channel with tests: malformed/stale health, missing matches, changed
      probabilities, complement arithmetic, placeholder identities, bad deep links, repeated copy,
      disallowed claims, character counting, graphic overflow and accessibility, OAuth signing,
      media/post failures, duplicate/manual reruns, dry-run behavior, and deduplicated social-health
      alerts. CI uses fixtures and a fake X server; it must never publish a real post.
- [ ] Roll out in three explicit stages: seven days of artifact-only dry runs; fourteen days where a
      human reviews the proposed copy/graphics before publication; then a separate owner decision to
      enable autonomous posting. Keep a one-switch kill control and a manual preview/dispatch path.
- [ ] Measure the pilot with per-slot UTM parameters and a weekly report covering posts attempted,
      skips/failures, impressions, engagement rate, profile visits, and site clicks where available.
      After 30 live days, compare content types and posting windows, keep only material differences,
      and decide whether two posts per day is better than one high-quality post.

## Live/upcoming overlap repair (2026-08-19)

Status: implemented; pre-push verification complete, with live verification required after the
production push.

- [x] Preserve ESPN's stable event id on browser-polled live matches and share one live-match state
      between the live ticker and the surrounding page.
- [x] Remove only exact same-event, same-player-pair live matches from scheduled/"Next up" views;
      keep the hourly pre-match forecast available as history rather than showing it as still next.
- [x] Add focused unit coverage for event-id and unordered-player-pair matching, update the deployed
      UI contract so an old bundle cannot pass verification, and run web tests, lint, and the live
      deployment verifier after the production push.
- [x] Add a review section with the observed root cause, files changed, verification results, and
      any residual timing risk before committing or deploying.

### Review

- Root cause: `LiveTicker` owned a minute-polled ESPN state that the hourly scheduled surfaces could
  not observe, and `fetchLiveMatches()` discarded the event's stable ESPN id. The same active pair
  could therefore remain in `upcoming.json` and render with its stale pre-match probability.
- Repair: the page owns one `useLiveMatches()` poll; ESPN's `espnId` survives parsing; the overview,
  tournament footer, match-center schedule, and watchlist all use `excludeLiveMatches()`, which
  requires the same exact event id and unordered normalized player pair. The source forecast stays
  in the artifact for point-in-time/final history.
- Gate: both affected routes now advertise `exact-event-unordered-pair-v1`, the match-center contract
  advanced to `live-dedupe-v4`, and the post-deploy verifier rejects an old or partial bundle.
- Verification before push: 111 focused tests and all 265 web tests passed; the production build
  passed; ESLint reported zero errors and nine unchanged warnings in unrelated files. Local browser
  checks confirmed both route contracts, no active pair in the Upcoming tab, and no console errors.
- Residual risk: if ESPN is unavailable on first load, the schedule remains visible because there is
  no authoritative live state to join; a later successful visibility/poll refresh removes overlaps.
  The existing live-score error state remains explicit on the match center.

## MCP charting health false-alarm repair (2026-08-19)

Status: implemented and verified locally; approved for production deployment.

- [x] Reclassify an old newest-charted-match date as an informational coverage note, while keeping
      missing or unreadable charting files as a data-health failure. The MCP career-style input is
      volunteer batch-updated, and its official file history includes 145–200 day update gaps, so
      match age cannot establish that its repository moved or froze.
- [x] Make the daily full-source download report incomplete MCP fetches through the existing
      post-deploy source-download failure path, so an actually moved, renamed, unreachable, or
      malformed source is detected directly without preventing deployment of the last good data.
- [x] Replace the threshold-relative false-positive test with focused coverage for stale-but-usable
      charting data, absent data, and incomplete MCP downloads; run the relevant Python, workflow,
      integrity, and formatting checks.
- [x] Record the gate-design lesson, add a review section with the observed root cause and evidence,
      commit only the repair paths, push to production, and verify the resulting workflow and live
      health artifact are green.

### Review

- Root cause: `HEALTH_MAX_CHARTING_AGE_DAYS = 90` treated the newest match date inside MCP as a
  repository liveness signal. The official repository was still on `master` with the same files;
  Overview commits on 2025-06-14, 2025-12-31, and 2026-05-25 prove that 145–200 day batch gaps are
  normal. The latest workflow deployed successfully and passed all live-serving checks, then its
  advisory health step failed only when ATP coverage crossed 91 days.
- Repair: charting coverage older than 90 days remains visible as a healthy note; only missing or
  unreadable local charting data is a health problem. The daily full downloader now validates each
  MCP CSV, falls back from invalid HTTPS payloads to the authenticated GitHub transport, writes
  atomically, preserves the last good file, and reports every exhausted filename through the
  existing non-blocking source-download alert.
- Gate: the old threshold-relative test was replaced with explicit stale-note and absent-data
  behavior. Downloader coverage proves invalid-payload fallback, exact failure reporting, and
  last-good preservation; the strict-source policy now treats any named MCP failure as actionable.
- Verification before push: 124 focused and all 628 Python tests passed; repository-wide Ruff and
  `git diff --check` passed; the real MCP fetch validated all 16 files; regenerated health is green
  with zero output problems and the ATP 91-day row rendered as a note; the pre-deploy integrity
  gate passed. All 265 web tests and the production build passed; ESLint reported zero errors and
  nine unchanged warnings in unrelated files.
- Residual risk: MCP can stop publishing new charted matches without failing transport, but there is
  no upstream freshness contract that makes such a delay actionable. Coverage age remains visible
  on `/health`; an actual path, payload, or availability failure alerts on the next daily full run.

## Portfolio README audit (2026-08-20)

Status: in progress.

- [ ] Audit the root GitHub README against the current model, data pipeline, web experience,
      workflows, and recent commits.
- [ ] Reframe the README for portfolio readers: lead with the live product, measurable outcomes,
      differentiating engineering decisions, and concise visual proof.
- [ ] Correct stale source-health, WTA lower-tier, and product-surface claims without changing
      measured model results unless the repository contains newer reproducible evidence.
- [ ] Re-run the recent history check, validate links and commands, inspect the final diff, and add
      a review section documenting what changed and how it was verified.

Scope correction from owner: portfolio framing must preserve and clearly explain operational
detail. The README should remain technically substantive about data acquisition, fallbacks,
training cadence, deployment gates, monitoring, and reproducibility; improve the hierarchy rather
than reducing those details to marketing copy.

## Home-to-bracket discovery (2026-08-20)

Status: implemented, deployed, and verified in production.

- [x] Re-home Brackets from the Matches navigation group to Forecasts, and make Brackets a primary
      mobile destination so the feature is not hidden behind the all-pages sheet.
- [x] Add one event-specific bracket URL helper that prefers the stable `espnId`, preserves the ATP/
      WTA tour, and selects Actual, Forecast path, or Scenario without joining on a display name.
- [x] Put an obvious bracket-lab entry on the home page's current-tournament glance card and add
      explicit Actual draw, Forecast path, and What-if actions to current/released tournament cards.
      Open Forecast path from the primary one-click entry when a scenario shard exists, fall back to
      Actual draw otherwise, and fail closed when no complete bracket is available.
- [x] Add focused URL, navigation, and rendered-card coverage; run the full web tests, lint, and
      production build; browser-check ATP and WTA at desktop and mobile widths; reconcile recent git
      history; then append a review with the exact behavior and verification results.

### Review

- Discovery: the current tournament's above-the-fold glance card now opens its event-specific
  Forecast path when exact scenario data exists, while every complete-draw card exposes Actual draw,
  Forecast path, and Try what-if actions as coverage permits. Brackets moved from Matches to
  Forecasts on desktop and replaced Predictor as a primary mobile destination.
- Identity and degradation: every link uses the stable `espnId` and preserves the tour. A complete
  draw without a scenario shard gets Actual only; missing ids and partial/seeded draws get no guessed
  bracket link.
- Gate: the deployed home route now advertises
  `stable-event-id+actual+forecast+scenario-v1`, and post-deploy verification rejects an old or
  partial bundle that omits the new discovery contract.
- Verification: 271 web tests passed; the production build generated all 24 routes; ESLint reported
  zero errors and nine unchanged warnings. Desktop and 390px browser QA covered ATP/WTA home links,
  the Forecasts menu, all three card actions, exact Cincinnati event selection, WTA tour state, no
  console errors, and no horizontal overflow.
- Deployment: commit `0a58938` was pushed to `master`; production workflow run `32444147592` passed
  tests, integrity, Firebase deploy, live verification, data-health, and deploy-health. An independent
  production verifier passed 20/20 checks, and the live WTA home CTA opened Cincinnati Open in
  Forecast path mode with the correct event id.

## Portfolio README audit review (2026-08-20)

Status: complete; documentation-only changes, not committed or deployed.

### Review

- Audit result: the GitHub README was materially current through the August 17 product expansion,
  but it still said no WTA lower-tier overlay existed, described MCP content age as a source outage
  signal, omitted the current match-center/forecast products, and understated the production gates.
- Portfolio update: the root README now leads with the live product and measurable results, then
  explains the 42-feature hybrid, adoption protocol, source and identity strategy, hourly/daily
  lifecycle, failure semantics, monitoring, repository structure, reproducible bootstrap, and
  honest limitations. Operational detail remains concrete but is grouped for skimmability.
- Technical-doc correction: `tennis_model/README.md` now distinguishes the acquired WTA lower-tier
  research overlay from disabled production-state admission, and describes health checks by their
  current source contracts.
- Evidence: both shipped metadata files list 42 features; config pins five ensemble fits and keeps
  WTA lower state disabled from its 2016 source boundary; package metadata confirms Next.js 16 and
  React 19; workflow definitions confirm the :17 hourly refresh, 06:00 daily retrain, pre-deploy
  gate, live verifier, weekly snapshot, issue reporters, and 26-hour watchdog. The final recent-log
  pass included the August 19 live-overlap and MCP-health repairs.
- Verification: all relative links in both READMEs resolve; `git diff --check` passes; the documented
  downloader, pipeline, and CLI entry points all accept the shown arguments. Full test suites were
  not rerun because no executable code changed. Unrelated concurrent navigation work and the
  pre-existing task-log edits were left untouched.

### Publication

- Owner authorized commit and deployment. The path-scoped documentation commit was rebased onto the
  latest remote `master` and published as `7bd5ebe` (`docs: refresh portfolio README`). The remote
  README blob matches the verified local artifact. GitHub's README is live; the Firebase workflow
  was intentionally not dispatched because no website artifact changed and documentation paths are
  excluded by `refresh.yml`.

## Gated WTA dual-state model (2026-08-22)

Status: implemented and verified after owner authorization on 2026-08-22.

Implementation authorized by owner on 2026-08-22.

- [ ] Build a default-off dual-state research path over one canonical match population: preserve a
  main-draw-only state bundle, build a lower-tier-enriched bundle, score the exact same main-draw
  rows, freeze serve baselines, and assert bit-identical output before the 2016 lower-tier boundary.
- [ ] Define one shared deterministic gate from pre-match main-draw evidence already available at
  walk and prediction time. Pre-register a small main-match-count threshold grid, tune it on
  2010-19 only, and select the enriched bundle only when either player lacks sufficient main-draw
  history; do not use post-match information or inference-only rank data.
- [ ] Freeze the selected gate and run the full bagged walk-forward arbiter on 2020+ validation.
  Report overall, tune, validation, per-year, both-top-50, outside-top-50, gate-eligible count bands,
  and frozen Kalshi deltas. Require the normal adoption gate, a positive target slice, and no
  material both-top-50 regression before production admission.
- [ ] If and only if the arbiter passes, wire the dual state into production: keep the feature schema
  and main-draw combiner population unchanged, store both complete state bundles in the predictor,
  use the same gate helper for walk time and inference, share main-only metadata, add a config
  fingerprint, and bump the inference schema/staleness contract.
- [ ] Add focused tests for row alignment, threshold boundaries, complete-bundle selection, player
  orientation, unseen players, walk/inference parity, serialization/staleness, unchanged ATP output,
  unchanged WTA scoring population, and the quick-refresh path.
- [ ] Run focused and full Python tests via `uv`, lint/type checks that cover touched code, the full
  WTA arbiter, pipeline/health checks if adopted, `git diff --check`, and a final recent-log review.
  If the gate is rejected, remove production wiring and retain only the reproducible experiment
  result required by the research ledger.

Implementation authorized by owner on 2026-08-22. Starting with the default-off research path and
shared walk/inference gate; production admission remains contingent on the frozen arbiter.

### Review

- [x] Built the row-exact dual-state harness over 128,822 unchanged WTA main-draw rows and 14,560
  qualifying/125 state rows. Main-only pre-match counts own the orientation-safe gate; all 42 model
  inputs plus component probabilities switch as one bundle, while identity/audit metadata remains
  baseline-owned. Pre-2016 features and predictions are bit-identical.
- [x] Pre-registered thresholds 8/16/32/64 and selected on 2010-19 only under production five-model
  bagging. Tune deltas were +0.00021±0.00016, +0.00032±0.00020, +0.00042±0.00023, and
  +0.00031±0.00025 respectively, freezing the 32-main-match threshold before validation.
- [x] Rejected the first mixed-training implementation despite its normal gate pass: retraining one
  shared combiner moved protected rows (-0.00089±0.00014) and retained a both-top-50 regression
  (-0.00118±0.00025). Reworked the architecture so every fold fits/calibrates once on the unchanged
  main-only frame and the gate changes eligible prediction inputs only; recorded the general lesson.
- [x] The corrected frozen arbiter passed every admission condition: tune +0.00042±0.00023,
  validation +0.00098±0.00066, full +0.00063±0.00028, outside-top-50 +0.00145±0.00059,
  both-top-50 -0.00007±0.00012 (inside the safety SE), eligible rows +0.00329±0.00148, and
  protected rows exactly +0.00000±0.00000. The frozen Kalshi/outside-50 slice was noisy and negative
  (-0.00157±0.00359, n=352), so it remains a reported benchmark rather than an adoption veto.
- [x] Adopted production threshold 32. The predictor now serializes main-only and enriched
  Elo/serve/context bundles, shares main-only metadata, selects from main-state counts at inference,
  and carries inference schema 3. Full/quick pipelines keep health/export match rows main-only;
  walk-forward accuracy and standalone Kalshi backfills use the same baseline-combiner state gate.
- [x] Extended staleness and integrity contracts. Quick mode rejects a missing/partial/drifted
  secondary state; method.json publishes the gate; predictor-derived meta proves threshold/readiness;
  the WTA output gate blocks a declaration/artifact mismatch without imposing the WTA contract on
  independently stale ATP artifacts.
- [x] Rebuilt the real WTA predictor and outputs. Artifact audit: threshold=32, all lower states
  present, schema=3, quick guard current, 5,313 main-state players vs 6,047 enriched-state players,
  public meta remains 128,822 matches / zero WTA-125 display rows. The 2016-26 production backtest
  contains 26,038 matches (accuracy .6783, log loss .5936, Brier .2043). Forecast/Kalshi ledgers were
  refreshed by the normal full pipeline (73 forecasts; 887 scoreable WTA market rows).
- [x] Verification: 637 Python tests; 271 web tests; TypeScript; Next.js production build; ESLint with
  zero errors (nine pre-existing effect warnings); compileall; git diff check; real WTA full + quick
  builds; and the pre-deploy integrity gate. The only health output is the existing advisory that ATP
  artifacts/model are five days old. Final recent-log reconciliation used HEAD/origin master
  8519492 and confirmed the August 19-20 source-health, forecast, bracket, and README changes.

## Hourly refresh latency + sharded upcoming feed (2026-08-22)

Status: proposed; awaiting owner check-in before implementation.

- [x] Establish a reproducible serial quick-export baseline, then add one low-overhead timing seam
      with per-tour elapsed lines for `load_matches` (including merge/clean/sort detail), event
      projection, scenario generation, upcoming enrichment, and tracking/log grading. Keep timings
      observational: they must not change best-effort error behavior or become a deploy dependency.
- [x] Cache each tour's schema-normalized historical source frame under the existing persisted
      `tennis_model/data` cache. Key it by an explicit cache/schema version, source-file fingerprint,
      Python/pandas compatibility, and any normalization inputs; write atomically, treat corrupt or
      stale entries as misses, and prove cold/warm frames (including attrs/dtypes) are equivalent.
- [x] Build the decorated upcoming snapshot once per export, after tracking has appended the current
      hourly observation, instead of writing it once in `export_all` and rebuilding it in
      `export_forecast_products`. Add focused call-count/order coverage so the latest movement still
      reaches the same deploy and a tracking failure still degrades safely.
- [x] Run ATP and WTA quick tour exports concurrently only after shared live/draw/ranking downloads
      finish. Keep tour-local outputs, caches, logs, mirrors, and returned frames isolated; preserve
      the single-tour path; make worker failures surface; and test real overlap plus serial/parallel
      artifact parity before adopting the concurrent path.
- [x] Replace the monolithic `upcoming.json` web contract with `upcoming-index.json`: compact home
      highlights (the next few rows per event plus top watch candidates), stable per-event references,
      counts, and generation metadata. Publish compact per-event match shards and separate per-event
      evidence/history shards keyed by stable match identity; remove obsolete legacy/stale shards.
      The home page must fetch only the index, schedule/match-center routes must fetch event rows only
      when their upcoming surface is used, and evidence/history must load only for the selected or
      expanded matchup. Preserve exact event-id joins and live-match exclusion behavior.
- [x] Extend `read_outputs()` and `output_problems()` to require the index, reject unsafe/missing/
      corrupt/duplicate shard references, reconstruct every full upcoming row, and run the existing
      probability/component/evidence/history/watch/bracket invariants over that reconstruction. Add
      producer, cache-invalidation, pipeline-concurrency, health-gate, client-loader, and payload
      tests; run full Python and web suites, TypeScript, lint, production build, pre-deploy gate, and
      cold/warm serial/parallel benchmarks. Target a current-feed home index below 50 KB raw and at
      least a 90% raw-byte reduction versus the legacy payload, then append exact timings, sizes, and
      verification results in a review after reconciling the recent git log.

### Review

- [x] Added stage timings for match fingerprint/cache/merge/clean/bios/sort/write, event projection,
      scenario generation, upcoming enrichment/decorating, and forecast tracking. The owner-provided
      last serial quick baseline was 595s (ATP 348s + WTA 216s); the first cold concurrent run
      completed both tours in 237.6s, and the warm concurrent refresh completed in 34.49s: 94.2%
      faster than baseline and about 17.3x the refresh throughput.
- [x] Added atomic, compatibility- and content-fingerprinted historical and fully normalized match
      caches under the ignored `data/cache` tree. Production-size ATP load went 58.237s cold to
      0.250s warm (284,226 rows); WTA went 41.654s to 0.153s (128,822 rows). The real warm quick run
      recorded 0.392s ATP and 0.106s WTA cache reads, with attrs/dtypes, invalidation, and corrupt-cache
      fallbacks covered by tests.
- [x] Upcoming enrichment is prepared once and reused for tracking and the post-tracking export;
      quick all-tour exports run in a two-worker barrier after shared downloads, while single-tour
      mode remains serial and worker failures propagate. The warm run overlapped 13.2s ATP and 13.3s
      WTA tour exports rather than adding them.
- [x] Replaced the legacy file with generation-bound index, event, and evidence shards. ATP's current
      home payload fell from 601,582 to 3,644 raw bytes (770 gzip, 99.39% raw reduction); WTA's fell
      from 10,703,909 to 5,247 raw bytes (966 gzip, 99.95%). The integrity gate reconstructs all rows
      and re-runs the prior semantic invariants; the deploy verifier follows and validates every
      referenced shard; stale legacy/shard files are removed before export.
- [x] In-app browser verification proved both tour home pages fetch only `upcoming-index.json`, the
      match center fetches event shards only after opening Upcoming, and one evidence shard appears
      only after expanding Model evidence; ATP/WTA rendered without console errors. Verification also
      passed 652 Python tests, 275 web tests, TypeScript, compileall, Next's 24-route production build,
      ESLint with zero errors (nine unchanged warnings), the real pre-upload gate, and
      `git diff --check`. The final log reconciliation used HEAD 8519492 and preserved the concurrent model and
      draw/live-odds work already present in the dirty tree.

## US Open draw identity + live-odds semantics (2026-08-23)

Status: proposed; awaiting owner check-in before implementation.

- [ ] Quarantine the false US Open attachments on both tours: WTA event `189-2026` currently points
      to the 2026 Wimbledon women's draw, and ATP event `189-2026` points to the 2026 French Open
      men's draw. Add exact per-tour, per-`espnId` Wikipedia draw locators for the not-yet-published
      US Open articles so a missing article yields no complete bracket rather than a different Slam.
- [ ] Make Wikipedia title resolution fail closed when an ESPN event name has no distinctive anchor
      and no explicit draw locator. Keep metadata aliases and draw locators separate, and cover the
      generic-only name, correct mapped title, wrong-gender result, and missing-page cases offline.
- [ ] Revalidate a retained Wikipedia attachment while its event is live/upcoming before the settled
      cache shortcut can return it. A cached source identity that cannot be proved against the current
      event must be dropped; a validated completed-event cache may retain the existing immutable path.
- [ ] Extend draw-source uniqueness from official PDFs to every published/cache source identity:
      one `drawSourceId` or canonical `drawSourceUrl` may attach to only one ESPN event per tour.
      Quarantine producer duplicates, add a blocking `output_problems()` invariant and regression,
      and have the post-deploy verifier fetch both `brackets.json` files and enforce the same rule.
- [ ] Relabel the live ticker and accessible probability text as **pre-match model odds**. Do not add
      score-conditioned probabilities in this round: the current scoreboard/parser exposes set/game
      totals but does not preserve a reliable server + point state for the existing Markov model.
- [ ] Run focused draw/Wikipedia/health/live/verifier tests, then the full Python suite via `uv`, web
      tests, TypeScript, lint, production build, pre-deploy gate, `git diff --check`, real artifact
      regeneration, and a final live/recent-log reconciliation. Append a review with the quarantined
      artifact evidence and verification results; do not overwrite the concurrent model/latency work.

## Historical incident + one-off-fix automation audit (2026-08-22)

Status: audit in progress; implementation awaits owner check-in.

- [ ] Inventory every repository commit from inception through current HEAD, classifying routine
      data/merge churn separately from substantive incidents, fixes, safeguards, and operational
      changes; correlate repository evidence with GitHub issue and workflow-alert history.
- [ ] For each failure class, record its root cause, original detection path, regression coverage,
      present coverage in the pre-upload integrity gate or post-deploy verifier, and any remaining
      interval where a bad artifact or stale service can look green.
- [ ] Find repeated manual or one-off remedies that can become shared invariants, contract/parity
      tests, deterministic registry proposals, state-machine checks, scheduled canaries, or reusable
      CI alert helpers. Rank candidates by recurrence, user impact, detection latency, false-positive
      risk, maintenance cost, and overlap with safeguards that already shipped later in history.
- [ ] Reconcile the resulting recommendations with current uncommitted work and the latest git log,
      then append a review containing the hash-backed incident map and a small implementation slate
      with exact files/tests. Do not change production behavior until the owner approves that slate.

### Review

Audit status: complete; production implementation awaits owner check-in.

- [x] Accounted for all 308 production commits through `origin/master` `b1b8579`: 128 in
      `316a209..b220ed5`, four late-July-9 bridge commits, 110 from July 10-31, and 66 from
      August 1-22. Routine data/docs/research/merge churn is separated from 186 substantive,
      product, or hardening commits in the full audit.
- [x] Reconciled all 20 closed GitHub issues, the #1/#16 PR-number gaps, and 96 failed workflow
      runs. The three largest repeated gate-block episodes account for 27 failures; their output
      never reached an actionable issue because the gate stopped before the health reporter.
- [x] Verified the two highest-confidence open defects: issue #21 falsely recovered because the
      run-over-run match baseline ratcheted down, and total ESPN acquisition failure is caught and
      printed without a same-run health receipt.
- [x] Ranked the remaining automation work without re-proposing safeguards that already shipped.
      The immediate slate is: (1) tested pipeline/gate/workflow reporting plus watchdog extraction,
      (2) a population-versioned high-water baseline, and (3) per-tour ESPN acquisition receipts.
      Stable finding codes and production-shaped incident replay are the next consolidation round.
- [x] Reconciled against the dirty tree. The active US Open work already covers exact draw locators,
      fail-closed generic names, active cache revalidation, duplicate source quarantine, and both
      pre/post-deploy invariants; the audit deliberately does not duplicate it. The stage-status
      proposal should extend the active timing seam later.
- [x] Full evidence, issue ledger, recurring-class map, ranked backlog, exact files/tests, and the
      compact commit coverage ledger are in
      [`tasks/history-audit-2026-08-22.md`](history-audit-2026-08-22.md). No executable behavior was
      changed and no tests were required for this documentation-only audit.

## US Open draw identity + live-odds semantics review (2026-08-23)

Status: complete locally; implementation is not committed or deployed.

- [x] Confirmed the bad attachment on both tours, not only WTA: ESPN event `189-2026` had retained
      the 2026 French Open men's Wikipedia draw on ATP and the 2026 Wimbledon women's draw on WTA.
      Both cached rows and both published brackets are now absent locally while the exact 2026 US
      Open draw articles remain unavailable.
- [x] Added exact per-tour, per-`espnId` draw locators and made generic-only Wikipedia resolution
      fail closed. Active Wikipedia rows are re-resolved before the settled shortcut; a rejected
      current row cannot return through retention, and quarantine can persist an empty cache.
- [x] Quarantine any source id or canonical source URL attached to multiple ESPN events. The
      producer removes every ambiguous attachment, the pre-upload gate inspects the raw cache as
      well as published bracket payloads, and the post-deploy verifier checks both tour payloads.
- [x] Changed the ticker and accessible probability copy to **pre-match model odds**. In-play odds
      remain out of scope because the current ESPN scoreboard/parser does not preserve reliable
      point and server state for the existing Markov model.
- [x] Regenerated both draw caches and the mirrored web artifacts through the normal quick path.
      Neither tour contains `189-2026`, and neither the raw caches nor published brackets contain a
      duplicate source attachment. The local post-deploy helper reports zero source problems.
- [x] Verification: 653 Python tests and 275 web tests pass; the 141 focused Python and 52 focused
      web regressions pass; TypeScript, bytecode compilation, the production web build, and
      `git diff --check` pass. ESLint reports zero errors and nine pre-existing warnings.
- [x] Preserved concurrent model, latency, audit, and web work. The quick refresh also changed two
      tracked ATP evaluation artifacts that were clean at task start; sandbox policy blocked their
      restoration without explicit owner approval, so they remain visible in the working tree.

## Historical reliability audit — Round 1 automation (2026-08-23)

Status: implementation authorized by owner for Round 1A-1C; in progress.

- [ ] Add an optional atomic structured report to `health --gate` without touching the sentinel's
      deployed `health.json`. Give every load-bearing refresh stage a stable step id, then add a
      tested `pipeline-health` reporter that records the exact failed stage, gate findings, mode,
      and run URL while treating skipped/unknown outcomes explicitly.
- [ ] Add a terminal `if: always()` workflow-health job so push-test failures, refresh jobs that
      never start, timeouts, cancellations, and runner/setup failures reach the same deduplicated
      incident path. Keep upstream pipeline failures separate from `deploy-health` and ensure a
      successful complete run closes the standing pipeline issue.
- [ ] Extract the watchdog's inline issue branching into a tested script, retain its 26-hour
      last-resort liveness contract, and extend the no-inline-alert meta-test across every workflow.
- [ ] Replace the one-run `meta.matches` comparator with a population-versioned high-water state.
      A same-version drop must remain failing on repeated runs; only recovery to the accepted high
      water or an explicit `MATCH_POPULATION_VERSION` transition may clear/reset it.
- [ ] Persist an atomic per-tour ESPN acquisition receipt from the shared scoreboard sweep. Distinguish
      successful-empty, partial-query degradation, total transport failure, and retained last-good
      overlays; surface total failure on the same full or quick run without repeating the network
      sweep or confusing an idle week with an outage.
- [ ] Add negative and recovery controls for every reporter branch, gate-report schema/write
      failure, high-water transition, and ESPN receipt state. Run focused tests first, then the full
      Python suite via `uv`, workflow linter coverage, the real pre-deploy gate, web tests affected by
      the health contract, `git diff --check`, and a final recent-log/worktree reconciliation before
      appending the review.

## Repository consolidation onto `master` (2026-08-23)

Status: owner requested consolidation and branch cleanup; implementation awaits owner check-in.

- [x] Inventory the worktree, stashes, worktrees, and every local/remote branch without mutating
      history. Confirm which commits and uncommitted files are absent from `master`.
- [ ] Preserve the complete dirty tree in a consolidation commit, integrate the two newer
      `origin/master` evaluation-log commits, and resolve any overlap without dropping either side.
- [ ] Run repository-level verification appropriate to the combined Python, workflow, and web
      changes; record any remaining failure explicitly rather than hiding unfinished work.
- [ ] Fast-forward local `master` to the verified consolidated history and delete the redundant
      local `codex/fix-mcp-charting-health` branch.
- [ ] With explicit deploy confirmation, push `master` (which triggers production), then delete the
      stale remote `alias-proposer/30807596234` branch after verifying its two valid player aliases
      already landed independently and its rejected tournament alias remains excluded.
- [ ] Re-fetch/prune and verify that the tree is clean, `master` is the sole branch locally and on
      `origin`, and local/remote `master` resolve to the same commit. Add the final review here.

## Beautiful UI forecast-clarity pass (2026-08-23)

Status: complete locally; implementation is not committed or deployed.

- [x] Adapt the reference Fine-tune Card into an accessible prediction setup panel that groups
      player, surface, and format controls without changing shareable URL state or keyboard behavior.
- [x] Adapt the reference Recommendation Card into a factual prediction summary: name the favorite,
      show calibrated win probability and model edge from 50%, and expose only existing DEUCE actions.
- [x] Adapt the reference Context Cards into clearer model-evidence signals with visible availability,
      direction, magnitude, and plain-language facts while preserving the non-causal explanation.
- [x] Add focused UI/contracts, run the affected and full web checks, inspect desktop and 390px mobile
      renders (including overflow/focus/scroll behavior), reconcile the latest git log and dirty tree,
      then append a review without disturbing the concurrent reliability and consolidation work.

### Review

- [x] Reframed the predictor controls as one labelled fieldset with searchable player selectors,
      accessible pressed-state surface/format controls, a compact live setup summary, and preserved
      deep-link behavior. Desktop uses a balanced instrument panel; mobile stacks without hiding data.
- [x] Added a factual model-call summary with favorite/even-match handling, calibrated probability,
      a meter explicitly defined as distance from 50% (not market edge), and existing profile/style
      drill-ins. Near-even calls resolve the neutral profile action deterministically.
- [x] Reworked shared model evidence into indexed context cards with text-labelled support, neutral,
      and unavailable states; bidirectional impact rails; higher-contrast facts; component probabilities;
      and the existing non-causation warning. The shared lazy disclosure benefits Predictor, Schedule,
      and Match Center without changing any payload contract.
- [x] Verification: 18 focused tests and all 280 web tests pass; TypeScript and `git diff --check`
      pass; ESLint exits with zero errors and the same nine pre-existing hook warnings; the production
      build compiles and statically renders all 24 routes.
- [x] Rendered QA covered desktop and 390×844 mobile, surface and format interactions, evidence-open
      states, focus/pressed semantics, real scrolling, and root/body widths of 380px with no predictor
      console errors. The full harness passed all 36 route/viewport geometry checks but retained its
      non-zero exit for unrelated local ESPN CORS errors and the existing Scorecard 404 console request.
- [x] Final reconciliation used HEAD `8519492`; the extensive pre-existing reliability, draw, model,
      data, and sharded-feed edits remain intact. This round adds two new web files and scoped edits to
      the predictor/evidence/shared-control tests and components; nothing was committed or deployed.

## Historical reliability audit — Round 1 completion (2026-08-23)

Status: Round 1A-1C complete locally; implementation is not committed or deployed.

- [x] Added the atomic `predeploy-gate-v1` report, stable refresh step ids, exact stage/mode/scope
      pipeline incidents, specialist-reporter ownership handshakes, and a terminal workflow backstop
      for tests, jobs that never start, cancellation/timeout, runner/setup, and post-action failures.
- [x] Extracted watchdog alert branching into a tested shell script, fixed exact elapsed-time boundary
      handling and API-unknown behavior, added run/workflow links, and extended the no-inline-alert
      invariant across all workflow YAML files.
- [x] Replaced the ratcheting prior-run population comparator with a population-versioned durable
      high-water. Repeated same-version deficits stay red; valid recovery or an explicit population
      version transition is required to advance/reset the accepted baseline.
- [x] Added atomic per-tour `espn-acquisition-v1` receipts and same-run health reporting for success,
      successful-empty, partial degradation, total failure, processing failure, retained overlays, and
      mixed generations. Majority-failed sweeps preserve the prior overlay and bypass draw handoff;
      only a fully successful, fully updated acquisition advances `lastGoodAt`.
- [x] Added negative, recovery, write-failure, legacy-migration, repeated-run, threshold, ownership,
      API-unknown, and degraded-to-outage controls. Two adversarial review passes found no remaining
      correctness gap after the final ESPN state-machine fix.
- [x] Verification: all 698 Python tests and all 280 web tests pass; scoped Ruff, Actionlint,
      ShellCheck, Bash syntax, `git diff --check`, and the real pre-deploy gate pass. ESLint exits with
      zero errors and nine pre-existing warnings; the production build compiles and statically renders
      all 24 routes.
- [x] Final history reconciliation used HEAD `8519492` (306 commits); the local `origin/master`
      tracking ref is `b1b8579` (308 commits, two evaluation-log commits ahead). The extensive dirty
      concurrent worktree remains intact; no commit, branch change, push, issue mutation, or deploy
      was performed.

## Repository consolidation review (2026-08-23)

Status: local consolidation complete; remote deployment and remote-branch cleanup remain paused for
explicit deploy confirmation.

- [x] Committed the entire reviewed tree as `339287b` (`feat: harden forecasts and production
      reliability`) and rebased it onto `origin/master` `b1b8579` without losing either remote daily
      evaluation update.
- [x] Reconciled the append-only forecast logs by semantic identity: retained remote history through
      August 22, added 137 unique ATP and 167 unique WTA August 23 records, and suppressed ten later
      ATP duplicates of already-frozen first sightings. Both logs parse, remain chronological, and
      have no duplicate semantic keys.
- [x] Replayed the local ledger rows over the remote ledgers through the production frozen-field
      policy, retaining valid remote morning quotes and aligned forecasts while adding every newer
      local ticker. Regenerated the report at 1,518 ATP / 1,526 WTA events and 943 scored matches;
      post-anchor quotes and settlement disagreements are both zero.
- [x] Verification after reconciliation: 698 Python tests and 280 web tests pass; the real pre-upload
      integrity gate, TypeScript, production build (24 routes), Actionlint, ShellCheck, Bash syntax,
      and `git diff --check` pass. ESLint has zero errors and nine pre-existing hook warnings.
- [x] Fast-forwarded local `master` to `339287b` and deleted the redundant local
      `codex/fix-mcp-charting-health` branch. Local `master` is now the only local branch.
- [ ] Push `master` only after explicit confirmation because that push triggers production. Then
      delete the stale remote `alias-proposer/30807596234` branch, fetch/prune, and verify local and
      remote `master` are identical and the remote exposes no non-master branch.

## Production consolidation deployment review (2026-08-23)

Status: complete and live.

- [x] Atomically pushed consolidated `master` and deleted the stale remote
      `alias-proposer/30807596234` branch. GitHub now exposes only `master`; no local feature branch,
      worktree change, stash, or remote cleanup ref remains.
- [x] The first guarded deployment stopped before refresh on two Ruff `I001` import-order findings.
      Corrected only those imports in `11dbebc`, then passed repository-wide Ruff and all 15 affected
      draw-Wikipedia tests before retrying. Workflow-health issue #23 opened for the failed attempt
      and closed automatically after recovery.
- [x] Corrected production run `32619603718` completed successfully in 16m18s: 698 Python tests,
      280 web tests, web lint/type-check/static export, quick refresh, pre-deploy integrity, data
      health, Firebase deployment, live deployment verification, and terminal workflow health all
      passed.
- [x] Final live ref check confirmed local and remote `master` both resolved to `11dbebc` before this
      tasks-only completion note; the remote had no other head. The note itself is excluded from the
      production trigger by `refresh.yml`'s `tasks/**` path ignore.

## ESPN scheduled-round reconciliation repair (2026-08-23)

Status: complete and live.

- [x] Reconcile scheduled and completed matchup rounds from the freshly generated complete bracket
      only when stable `espnId` plus the exact canonical real-player pair identify one unambiguous
      bracket round; do it before scheduled pricing/logging and before completed fixture export.
- [x] Keep the independent pre-deploy round-consistency invariant blocking; do not trust or suppress
      unmatched/ambiguous provider rows.
- [x] Canonicalize cached forecast identities through the same bracket evidence so a failed run's
      wrong-round first sighting remains the one immutable forecast instead of spawning or grading a
      duplicate when the corrected round arrives.
- [x] Add focused regression coverage for ESPN's Winston-Salem failure shape, including ordinary,
      missing-id, unmatched-pair, ambiguous-bracket, and poisoned-cache controls.
- [x] Run the scoped upcoming/health tests, then the full Python suite and repository lint/integrity
      checks proportionate to this production-path change.
- [x] Reconcile the final diff and recent history, commit, push deliberately to `master`, and monitor
      the triggered production deployment through live verification and automatic incident recovery.

### Review

- Local implementation is complete. Exact, alias-aware bracket evidence now corrects round metadata
  before scheduled pricing/tracking and fixture export; ambiguous or incomplete evidence remains
  untouched and is still rejected by the independent health gate.
- Forecast tracking persists validated identity bridges so the blocked run's original first sighting
  remains immutable and grades exactly once after correction, including after the bracket artifact
  expires and across legacy identity chains.
- Verification: 184 focused tests and all 706 Python tests pass; all 280 web tests, Ruff, the real
  pre-deploy gate, `git diff --check`, TypeScript, and the production build of all 24 static routes
  pass. ESLint exits with zero errors and nine pre-existing hook warnings.
- Committed the reviewed change as `6692cfe` and pushed it from a clean, freshly fetched `master`.
  Production run `32683688659` completed successfully in 4m55s: both CI jobs, quick refresh, the
  unchanged pre-deploy integrity gate, data health, static build, Firebase publication, live deploy
  verification, and all terminal health reporters passed.
- Pipeline alert issue #25 closed automatically after recovery. Local `HEAD` and `origin/master`
  both resolved to `6692cfe` before this tasks-only completion note.

## Historical reliability audit — Round 2A/2B (2026-08-23)

Status: complete and live.

- [x] Introduce a versioned structured health-finding contract with stable code, severity, scope,
      tour/entity identity, evidence, message, and deterministic fingerprint. Preserve legacy prose
      lists during migration so the web page, fix prompts, and existing consumers remain compatible.
- [x] Move gate blocking/advisory decisions and report change detection off prose substring matching
      and onto typed severity/fingerprints; classify benign informational notes separately so they do
      not make an otherwise healthy deployment amber.
- [x] Give the data-health reporter a tested per-finding lifecycle with explicit active/resolved
      identity, exact recovery, mode throttling, and GitHub-API UNKNOWN behavior without rotating
      unrelated symptoms through one mutable issue.
- [x] Add a production-shaped incident replay manifest with minimized broken and clean controls that
      traverse the real final health/gate seam and assert stable finding codes for the highest-value
      historical event, date, draw, population, source-attachment, and acquisition failures.
- [x] Add schema/fingerprint uniqueness, compatibility, reporter-migration, negative, recovery, and
      replay-manifest tests; prove each replay bites by checking both broken and clean variants.
- [x] Run repository-wide Ruff, focused and full Python tests, the real pre-deploy integrity gate,
      workflow linters/shell tests, web tests/lint/type-check/build, and `git diff --check`; obtain an
      adversarial review and append the completion evidence before release.
- [x] Commit on a `codex/` branch, fetch/reconcile the latest remote history, fast-forward `master`,
      push deliberately, and monitor tests, Firebase deployment, live verification, and all health
      reporters through successful production recovery.

### Pre-deploy review

- Round 2A replaces prose-coupled health identity with strict `health-finding-v1` records and keeps
  legacy messages as compatibility output. Fingerprints use invariant code/scope/tour plus stable
  provider entity; mutable severity, evidence, and wording form a separate revision. Informational
  source notes stay visible without making the site or issue automation look unhealthy.
- The data reporter now reconciles one durable issue per actionable fingerprint across onset,
  recurrence, evidence update, duplicate cleanup, independent recovery, legacy migration, and
  unreadable GitHub inventory. A failed gate supplies an explicitly partial snapshot: it can
  create/update findings it observed but cannot close unrelated source or run-over-run incidents.
  Specialist-owned red runs likewise cannot claim an older generic pipeline incident recovered.
- Round 2B replays six historical failures with minimized broken and globally clean controls. The
  pre-deploy cases cross the real gate report; sentinel and informational cases cross the real
  serialized health write. Clean controls contain zero actionable findings and every incident owns
  one stable expected code/entity/channel.
- Adversarial review caught and closed false-recovery, issue-recurrence, timestamp-flapping,
  sponsor-title identity, id-less/one-sided event join, bracket/forecast baseline, oversized-body,
  degraded-note, and replay-seam gaps before release. The final CI/reporter review found no blocker;
  the two final health findings (one-sided IDs and total forecast-log disappearance) were repaired
  and re-reviewed with lifecycle regressions.
- Verification on the final tree: all 798 Python tests and 284 web tests pass; repository-wide Ruff,
  330 affected health/reporter/replay tests, the real current-data pre-deploy gate, TypeScript, the
  production build of all 24 static routes, changed-script Bash/ShellCheck, `refresh.yml` Actionlint,
  and `git diff --check` pass. ESLint exits with zero errors and the same nine pre-existing React hook
  warnings. Repository-wide shell/workflow lint additionally reports unchanged findings in two
  alias-proposal paths; the Round 2 scripts and workflow are clean.

### Production deployment review

- Committed the reviewed Round 2A/2B implementation as `9f6bd41`, fetched and confirmed remote
  `master` had not moved, fast-forwarded local `master`, and pushed the exact commit deliberately.
- Production run `32687229574` completed successfully in 11m23s. Both reusable CI jobs passed, then
  quick two-tour regeneration, the typed pre-deploy gate, authoritative data-health write, static
  build, Firebase publication, live verification, desired-state data/deploy/pipeline reporters,
  cache save, and terminal workflow-health classification all passed.
- The deployed `data/health.json` is stamped `2026-08-24T03:49:17Z`, identifies itself as an
  authoritative `health-finding-v1` snapshot, reports `ok=true`, and contains zero actionable
  findings. Its three remaining records are informational coverage/date notes, proving that visible
  context no longer creates an amber/red incident. GitHub has no open issue after reconciliation.
- Local `master` and `origin/master` both resolved to `9f6bd41` before this tasks-only completion
  note. The note is excluded from the production trigger by `refresh.yml`'s `tasks/**` path ignore.

## Historical reliability audit — Round 3A/3B/3C (2026-08-24)

Status: implementation and pre-deploy review complete; commit and production deployment pending.

- [x] Extend the history audit through current `master` with an exact post-cutoff commit ledger and
      reconcile every original ranked proposal against shipped code, tests, and production behavior.
- [x] Round 3A: extend the existing timing seam into atomic per-tour `stage-status-v1` receipts with
      stable stage identity, product/evaluation criticality, attempt outcome, duration, input
      fingerprint, last-success timestamp, and bounded error evidence. Preserve the last known state
      for stages not attempted in a given mode and avoid cross-tour write races.
- [x] Surface current product-stage failures and overdue product-stage success through stable typed
      health findings; keep evaluation-only failures visible but informational. Add broken, repeated,
      recovery, stale-success, malformed-receipt, quick/full, and concurrent-tour controls.
- [x] Round 3B: introduce one source-aware participant/slot classifier covering real player,
      qualifier, lucky loser, wildcard, alternate, bye, and unresolved/TBD states. Make the existing
      real-player, settled-draw, and meaningful-draw policies consume that vocabulary without
      changing legitimate provider-specific context.
- [x] Migrate ESPN, Wikipedia, official-draw, simulation, event-evidence, and health consumers in
      small parity-preserving steps. Add cross-provider vocabulary, numbered-placeholder, null-slot,
      source-context, settled, and meaningful broken/clean controls before deleting local sets.
- [x] Round 3C: put a narrow real-browser scroll/overflow/interaction smoke in CI against deterministic
      fixture data and the built static site. Pin the browser runtime, keep external provider/Firebase
      traffic out of the gate, and prove the historical wheel-chain and horizontal-scroll failures bite.
- [x] Run focused tests after each sub-round, then repository-wide Ruff/Python/web/type/build/workflow
      checks, the real pre-deploy gate, browser smoke, and `git diff --check`; obtain an independent
      adversarial review and reconcile the final diff/history before release.
- [ ] Commit on a `codex/` branch, fetch/reconcile current remote `master`, fast-forward deliberately,
      push to production, and monitor CI, refresh, typed data health, Firebase verification, browser
      serving, terminal workflow health, and issue recovery through a clean live result.

### Review

Pre-deploy review complete; production evidence is pending.

- The history ledger now accounts for all 317 commits through production `b6b1511`, including the
  exact nine post-cutoff commits and incidents #23-#25. The original P0/P1 proposals are reconciled
  to their shipped Round 1/2 implementation, with only the staged artifact envelope/lineage and two
  lower-priority follow-ups still open.
- Round 3A records private, atomic per-tour stage attempts with complete input identities, bounded
  error detail, last-success state, clock-skew validation, and product/evaluation criticality. Public
  health exposes stable safe categories only; legacy rollout stays silent, corrupt/expected/incomplete
  state is explicit, every mirror excludes the receipt, and test runs cannot pollute operational data.
  Partial Kalshi sweeps and zero-match market joins now remain usable while recording informational
  degradation instead of false success.
- Round 3B replaces the distributed placeholder sets with one source/context-aware vocabulary in
  Python and a parity-matched browser vocabulary. Wikipedia omissions become proven byes only from
  explicit/carry evidence; legacy ambiguity is materialized as unique unresolved seats and remains
  safe through failed refresh, retention, simulation, and rendering.
- Round 3C builds a two-tour fixture and tests the exported site in real Chromium without external
  traffic. Its negative controls prove the historical wheel-chain and horizontal-overflow failures
  still bite. The interaction check found and fixed a real reverse-toggle race; URL, rendered data,
  saved preference, active control, base path, unrelated query, and fragment now stay aligned.
- Final verification: 873 Python tests and 288 web tests pass; repository Ruff, TypeScript, current
  live-data pre-deploy gate, Actionlint, browser-script syntax, and `git diff --check` pass. The
  isolated production build exports all 24 routes and the browser smoke passes both negative controls
  plus 4/4 desktop/mobile route checks. ESLint has zero errors and the same nine existing hook
  warnings. Independent adversarial passes closed future-dated receipt, incomplete fingerprint,
  quiet degradation, test pollution, ambiguous null retention, rollback-private receipt and warmed
  cache compatibility, producer-order failure laundering, malformed row isolation, generic-verifier
  fixture coupling, incidental route-height, and URL/hash race findings.

Round 4 will add the pre-unpickle predictor envelope and whole-build lineage manifest after this
release establishes the shared status/criticality vocabulary; the manifest will shadow before it
becomes blocking.
