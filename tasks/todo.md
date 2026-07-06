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
