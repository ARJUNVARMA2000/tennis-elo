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
- **Deviations from plan**: none material. Ruff re-sorted the health.py import line its
  own way; the report-step issue title dropped "Daily" since quick runs can now open it.

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
