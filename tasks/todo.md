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
