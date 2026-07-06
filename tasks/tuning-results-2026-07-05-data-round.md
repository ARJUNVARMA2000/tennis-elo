# Data round — challenger ingestion (A5), WTA stats backfill, altitude (2026-07-05)

Protocol: full 2010–2026 walk-forward arbiter per data experiment (N_BAG=5, adopted
per-tour combiner params), paired per-match log-loss d±SE on tune (2010–19) / val
(2020+) / full windows, scored on the IDENTICAL main-draw eval set in both arms
(lower-tier rows feed the walks but are never scored — otherwise d measures
eval-set drift, not rating quality). Gate: d_tune > 0 AND d_val > −1·SE.
Harness: `eval/ab_data.py` (new — data experiments need two feature frames, which
`eval/tune.py`'s fixed-frame objectives cannot express).

## Headline discovery (unblocks A5)

stats.tennismylife.org backfilled its challenger archive to **1978** and hosts ATP
qualifying files from **2007** — full Sackmann schema WITH serve stats (verified
per-year by direct fetch: 2010 challenger 4,341 rows; 2015: 4,604; quali 2015:
1,863; plus `challenger_ongoing_tourneys.csv` updated live). The A5 experiment was
skipped in the 2026-07-02 round *solely* because no source covered the 2010–19
tune window; that reason no longer holds. `config.py`'s `first_year: 2018` comment
was stale (applies to tour-level year files only) — fixed.

## Ingestion (INCLUDE_CHALLENGERS load-time gate, off by default)

- `download.download_lower()`: challenger + quali years from LOWER_TIER_FIRST_YEAR
  (2005 — five warm-up years before the tune window; 1978+ would double the walk
  for matches that can't influence any scored year) + the ongoing-challengers file.
- `results._read_lower()`: challenger files keep level `C`; qualifying rows are
  stamped level `Q` → challenger tier (a slam Q1 between challenger-strength
  players must not update at slam K). Every row carries `draw_level`
  (main/chall/qual), which `_assemble` passes through for the arbiter filter.
- `ROUND_ORDER` Q1–Q3 = −3..−1 (qualifying shares the main draw's tourney_id and
  start date; must sort strictly before R128).
- Sanity (flag on vs off): main rows bit-identical (152,952); +129,968 lower rows
  (100,521 chall + 29,447 qual, 2005–2026); lower stats coverage 79.9%; known
  upstream dips: 2019 challenger file 3,099 rows (~25% light), 2020 COVID 2,180.
  1,904 of 5,049 lower-tier players overlap the tour population.

## A5 arbiter, mode=full (lower rows feed walks AND combiner) — REJECT

45,762 paired main-draw matches, ATP:

| window       | base ll  | arm ll   | d±SE                 | base acc | arm acc | base brier | arm brier |
|--------------|----------|----------|----------------------|----------|---------|------------|-----------|
| tune 2010–19 | 0.56831  | 0.55962  | **+0.00869±0.00087** | 0.6981   | 0.7078  | 0.1940     | 0.1902    |
| val 2020+    | 0.58975  | 0.59082  | −0.00107±0.00101     | 0.6767   | 0.6754  | 0.2031     | 0.2037    |
| full         | 0.57647  | 0.57150  | +0.00497±0.00066     | 0.6900   | 0.6955  | 0.1975     | 0.1953    |

Gate: d_tune +0.00869, d_val −0.00107 vs −1·SE −0.00101 → **REJECT** (by 0.00006).

The tune-window gain is an order of magnitude beyond anything measured in prior
rounds (+1.0 accuracy point), but per-year paired d is structurally unstable:
+0.031/+0.037 (2010/11), −0.027 (2013), +0.026 (2017), +0.023 (2020), −0.035
(2024, t=−15), +0.012 (2025). Swings of ±0.03 when parameter experiments move
±0.001 indicate the challenger-dominated row mix (≈2/3 of training rows) is
destabilizing combiner training and the per-fold prior-season calibration — a
training-distribution effect, not a rating-priors failure.

## A5 arbiter, mode=ratings-only — **PASS → ADOPTED** (largest gate-passing
## result in the project's history)

Walks see challengers; the combiner trains, calibrates and scores on main-draw
rows only. Same 45,762 paired matches:

| window       | base ll  | arm ll   | d±SE                 | base acc | arm acc | base brier | arm brier |
|--------------|----------|----------|----------------------|----------|---------|------------|-----------|
| tune 2010–19 | 0.56831  | 0.56244  | +0.00587±0.00089     | 0.6981   | 0.7040  | 0.1940     | 0.1914    |
| val 2020+    | 0.58975  | 0.58218  | **+0.00756±0.00100** | 0.6767   | 0.6826  | 0.2031     | 0.2000    |
| full         | 0.57647  | 0.56996  | +0.00651±0.00067     | 0.6900   | 0.6958  | 0.1975     | **0.1947** |

Validation gain LARGER than tune (7.6 SE) — no overfit story survives that.
Per-year paired d: **17/17 years positive**, min +0.0008 (2020), max +0.0114
(2021), no instability. Full-walk Brier 0.1947 crosses the bookmaker anchor
(0.196); accuracy 0.6958 vs anchor ~0.690. For scale: the previous largest
adoption (seed bagging) was ~+0.001 full LL; this is +0.0065.

Mechanism: better Elo/point/context priors for players crossing the
challenger↔tour boundary (1,904 such players), with challenger-informed
experience counts feeding exp_diff / log_min_matches / log_min_srv_pts
confidence gates — while the combiner's training distribution stays untouched.

### Adoption (production = the ratings-only arm exactly)
- `INCLUDE_CHALLENGERS = True`; new `INCLUDE_WTA_125 = False` decouples the WTA
  scraper's 125 gate (125s remain gate-untestable — no tune-window source).
- `pipeline.build_tour` filters the feature frame through `features.main_rows()`
  before walk_forward + train_final; states walk everything.
- `eval/tune.py` objectives score main rows only (elo/point masks, xgb/feat
  frames) so future sweeps stay comparable to the arbiter.
- `train._cache_path` is regime-keyed (`_features_atp_lower.pkl`) so a stale
  main-only cache can never silently serve a lower-regime run.
- `download_all` pulls the lower archive daily (gated); current-year challenger
  file failures are strict-fatal like the stats overlay.

## Production rebuild under the adopted regime (verified 2026-07-06 02:21 UTC)

`pipeline --tour all --backtest`: ATP frame 282,920 rows (152,952 main), WTA
129,233. Deployed 2016–26 window (accuracy.json): ATP combiner acc
0.6757→**0.6832**, Brier 0.2034→**0.2001**, LL 0.5904→**0.5826**; WTA (backfill
only) LL 0.5966→0.5946, Brier 0.2055→0.2048, acc 0.6773→0.6754 (mixed; primary
metric improved — data refresh, not a gated model change). Predictor schema
42 features (clean, pre-altitude). `data.health --strict` green: results ≤3d,
ATP season stats coverage **97.6%** (challengers raise it), WTA 89.5%.

## Phase B — WTA serve-stats backfill

Probe (api.wtatennis.com): tournaments enumerate back to 2010, but match-level
detail **starts at 2016** — 2010–2015 return empty match arrays (2 events probed
per year for 2010/2013/2014/2015; 2016/2019 return full serve stats). The
2010–2015 WTA stats gap (archive coverage 73–78%) is **confirmed unfixable** from
the first-party API; recorded as a negative.

Actionable remainder: 2016 backfill (73.4% archive coverage, inside the tune
window) + 2023 top-up (91.5%). Scraper hardened for backfill: 404s stop retrying
immediately; a minority of permanently-dead event endpoints (old seasons have a
few — Shenzhen/Auckland 2016) is skipped loudly while a majority still raises as
an outage (the additive merge makes per-event skips safe; a silent husk season
would not be). `_enrich_from_local` now also inherits rank/age/ht/hand from the
frozen historical archive (backfill years have no fresh overlay; the API returns
neither rankings nor per-match age).

Backfill results (merged-frame coverage): **2016: 73.4% → 94.3%** with ~387
matches recovered that were entirely absent from the archive (count 2,651→3,038);
2023: 91.5% → 91.8% (the API carries no stats for RG/US Open even in 2023; only
4 events empty otherwise). API stats boundary mapped precisely: match detail
starts 2016, with per-event holes (34 events incl. slams empty in 2016, shrinking
each year). 2024 sits at 78.2% merged — a candidate for a follow-up top-up scrape.

## Phase C — altitude — REJECT

Static table shipped: `data/altitude.py` + `venue_altitude.csv` (331 venues, all
CITY_IOC keys resolved; country-checked geocoding via open-meteo; extremes
verified: Quito 2854 m, Bogotá 2582 m, Mexico City 2240 m, Gstaad 1055 m).
`geo.city_key()` extracted so altitude resolves sponsor-prefixed names exactly
like the home-advantage feature.

Feature A/B (`ab_data.py --exp altitude`): ONE frame per tour under the adopted
regime; baseline arm zeroes altitude_km so both arms carry identical column
counts/colsample behavior — the paired d isolates the altitude signal exactly.
10,494 ATP / 5,271 WTA main-draw rows sit above 500 m.

| tour | d_tune | d_val | gate |
|------|--------|-------|------|
| ATP  | +0.00005±0.00006 | +0.00008±0.00007 | formal pass, pure noise |
| WTA  | −0.00005±0.00009 | −0.00017±0.00012 | REJECT |

Shared-feature bar is both tours → **REJECTED**; wiring fully reverted (tombstone
in SYMMETRIC), table + module + tests retained as infrastructure. Consistent with
E3: venue physics adds nothing the surface/indoor context and (now
challenger-informed) ratings don't already carry.

## Final walk-forward table (2010–2026, post-round production state)

| model | ATP acc / ll / Brier | WTA acc / ll / Brier |
|-------|----------------------|----------------------|
| Elo blend | 0.6826 / 0.5838 / 0.2006 | 0.6621 / 0.6097 / 0.2112 |
| Point model | 0.6689 / 0.5946 / 0.2055 | 0.6453 / 0.6168 / 0.2148 |
| **Combiner** | **0.6958 / 0.5700 / 0.1947** | **0.6829 / 0.5878 / 0.2018** |

(45,762 ATP / 42,513 WTA matches; WTA n grew by 165 recovered-2016 matches.
Prior round: ATP 0.690 / 0.1975, WTA 0.683 / 0.2019.) The ATP combiner clears
the ~0.690 acc / 0.196 Brier bookmaker literature anchor on both axes. Note the
component-level effect of challenger-informed ratings: ATP Elo-blend Brier
0.2062 → 0.2006 — the raw Elo improved more than most full experiments ever
moved the combiner.
