# Tennis Prediction Model (ATP + WTA)

A hybrid forecasting system for professional tennis, men's and women's tours. It pairs
**surface Elo with cross-surface transfer** and an **opponent-adjusted serve/return
point model** with a **seed-bagged XGBoost combiner**, producing calibrated
single-match win probabilities, full set-score distributions, and Monte Carlo
tournament-draw projections.

## Why this design

The model combines surface Elo, opponent-adjusted serving and returning, playing style,
and match context. A five-seed boosted-tree ensemble is calibrated in both player
orientations; the final probability averages those orientations so reversing the players
returns the complementary probability.

The corrected retrospective evaluation covers **46,205 ATP and 42,425 WTA matches** in
annual folds from 2010–2026 (2026 is partial), measured on 2026-09-11 UTC after refreshing
the recovery inputs. Market odds are evaluation-only. Exact historical publication times
are not reconstructed; the walk uses verified dates where available and recorded event/round
order otherwise. See the [release measurements](../tasks/research/2026-09-10-general-release.md).

| Model (walk-forward 2010–2026) | ATP accuracy | ATP Brier | WTA accuracy | WTA Brier |
|---|---:|---:|---:|---:|
| Surface Elo + cross-surface transfer | 0.682 | 0.2009 | 0.664 | 0.2098 |
| Serve/return point model | 0.669 | 0.2057 | 0.650 | 0.2131 |
| XGBoost combiner (five-seed ensemble) | 0.692 | 0.1963 | 0.677 | 0.2042 |

These figures replace the July headline metrics, which used an asymmetric evaluation path
with the known winner first. Those old numbers are not a valid before/after comparison.
Bookmaker studies also use different populations; the live Scorecard compares market and
model forecasts on matched rows instead.

ATP includes Challenger and qualifying results in rating history while keeping those rows
out of combiner training. WTA keeps separate main-only and qualifying/125-enriched histories,
selecting the enriched history only when either player has fewer than 32 prior main-draw
matches. The existing tuned parameters and selection policy are unchanged by this release.

Model changes are selected on 2010–2019, checked on 2020+ using paired log-loss
uncertainty, and then evaluated through the complete walk-forward arbiter. Historical
experiments remain in [`tasks/tuning-results-*.md`](../tasks/).

```
data ─┬─ surface Elo + cross-surface transfer  (per-surface ratings, every result feeds
      │        every surface via xsurf; dynamic K, margin-of-victory, tier anchors)
      ├─ serve/return point model  (opponent-adjusted, time-decayed serve%/return% ->
      │        hierarchical point→game→tiebreak→set→match Markov; Bo3/Bo5)
      └─ context  (rest, fatigue, H2H, hand, rank, age, home advantage, MCP style)
                         │
     seed-bagged XGBoost combiner (42 features, 5 averaged fits) ──Platt──>
             calibrated P(A beats B) + set-score distribution
            ┌────────────┴────────────┐
     single-match predictor     Monte Carlo draw simulator (per-round + title odds)
```

- **Cross-surface transfer** (`EloParams.xsurf`, ATP 0.27 / WTA 0.17): a result on one
  surface also updates the others at `xsurf ×` the update, so debutant surface ratings
  are never cold — which lets the tuned surface blend rise to ~0.63.
- **Seed-bagging** (`config.N_BAG = 5`): the production combiner averages five
  seed-varied fits (training orientation + tree seed); `n_bag=1` is bit-identical to a
  single fit. Pure variance reduction, ~0.001 log-loss on both tours; 10 bags measured
  no better.
- **Home advantage**: `data/geo.py` resolves each event's host country (Davis Cup tie
  parsing, year-keyed events like the Olympics, a ~340-name city→IOC map) into an
  antisymmetric `home_flag_diff` feature. Venue is threaded through track/export/sim
  for real matches; hypothetical CLI predictions stay neutral.
- **The point model** is what yields a full **score distribution** and makes Bo3-vs-Bo5
  fall out correctly (a per-point edge compounds over more sets) — the tennis analog of
  a soccer Dixon-Coles goal model. Its probability feeds the combiner as one feature.
- **Per-tour everything**: Elo constants, point-model shrinkages, combiner
  hyperparameters, and context-feature windows (`FeatureParams`, carried on the
  predictor) are tuned and stored per tour (`config.py` `*_PARAM_OVERRIDES`).

## Data

Production data combines full-schema history, a daily serve-stats overlay, fresh weekly
results, hourly ESPN live scores, and lower-tier state overlays, plus Match-Charting style features,
official live rankings, and a Tennis-Data.co.uk odds benchmark (never a model input).
The first-party WTA downloader also acquires qualifying/125 rows into a separate secondary-state
overlay. ATP Challenger + qualifying rows (2005+/2007+) feed every rating walk while remaining
out of combiner training. WTA qualifying/125 rows (2016+) feed a separate secondary state,
selected only when either player has fewer than 32 prior main-draw matches; established matchups
retain the main-only state exactly. The full sourcing story, including fallbacks for upstreams that
keep disappearing, is in the [root README](../README.md). Module map: `data/download.py`
(schema-validated atomic downloads), `data/results.py` (merge + dedup),
`data/names.py` (cross-source name canonicalisation, contract-tested against the
site's TypeScript copy), `data/wta_stats.py` (wtatennis.com API scraper),
`data/rankings.py` (official live rankings), `data/geo.py` (host-country resolution),
`data/health.py` (source + produced-output health sentinel), `data/charting.py` (MCP style),
`data/odds.py` (odds benchmark), `data/draws.py` (source selection/cache),
`data/draws_official.py` (ATP/WTA PDFs + provider-id evidence), and `data/draws_wiki.py`
(Wikipedia fallback plus surface/tier metadata). Complete draws join the board on `espnId`;
provider ids are locators only. Official candidates require calendar overlap and at least 75%
live-field agreement, then Wikipedia and ESPN's partial frontier provide honest degradation.

## Layout

```
src/tennis_model/
  config.py            per-tour tuned parameters (Elo, point model, XGB, features)
  pipeline.py          orchestrator -> predictor.pkl, players.json, meta.json, accuracy.json
  cli.py               ad-hoc predictions / draw projections
  data/                download, results (merge/dedup), names, scores, geo, health,
                       live, odds, rankings, wta_stats, charting, draws (source-neutral
                       cache/orchestrator), draws_official (ATP/WTA PDFs), draws_wiki
                       (fallback + metadata), kalshi, surface, altitude, httpcache
  ratings/             elo.py (math incl. xsurf), build.py (chronological Elo walk)
  points/              serve_return.py (opponent-adjusted skill walk), markov.py
  model/               features.py, train.py (bagged XGBoost + Platt + walk-forward),
                       predict.py, upcoming.py, export.py (site JSON)
  sim/                 draws.py, tournaments.py, simulate.py (Monte Carlo)
  eval/                metrics.py, backtest.py, compare.py (vs market), ab_data.py,
                       track.py (graded point-in-time calls), tune.py (Optuna sweeps),
                       kalshi_ledger.py + kalshi_report.py (vs Kalshi, see below)
```

## Usage

```bash
cd tennis_model

# FIRST: restore the recovery snapshot. Current downloads cannot reconstruct all
# adopted WTA qualifying/125 history or historical serving statistics. The checked
# restorer preserves newer warm-cache files and invalidates stale model state.
gh release download data-archive --pattern 'raw-archive.tar.gz' -O /tmp/raw-archive.tar.gz
PYTHONPATH=src uv run --with-requirements requirements.txt python -m tennis_model.data.raw_archive restore /tmp/raw-archive.tar.gz

# THEN download all sources on top, and build both tours (predictor, site JSON, backtest)
PYTHONPATH=src uv run --with-requirements requirements.txt python -m tennis_model.data.download --kind all
PYTHONPATH=src uv run --with-requirements requirements.txt python -m tennis_model.pipeline --tour all --backtest

# ad-hoc queries (after the pipeline has trained a predictor)
PYTHONPATH=src uv run --with-requirements requirements.txt python -m tennis_model.cli predict "Jannik Sinner" "Carlos Alcaraz" --surface Hard --bo 5
PYTHONPATH=src uv run --with-requirements requirements.txt python -m tennis_model.cli project-slam "Wimbledon" 2025
PYTHONPATH=src uv run --with-requirements requirements.txt python -m tennis_model.cli field "Jannik Sinner" "Carlos Alcaraz" "Novak Djokovic" --surface Clay --bo 5

# tuning (resumable Optuna studies under data/output/tuning/)
PYTHONPATH=src uv run --with-requirements requirements.txt python -m tennis_model.eval.tune --tour wta --group xgb --trials 200
PYTHONPATH=src uv run --with-requirements requirements.txt python -m tennis_model.eval.tune --tour wta --group xgb --validate

# data-health sentinel — checks contracted source coverage/freshness AND the
# produced JSON the web reads (counts, tournaments, matches, predictions make sense).
# Writes data/output/health.json; --strict exits non-zero on any error/warning finding.
PYTHONPATH=src uv run --with-requirements requirements.txt python -m tennis_model.data.health --strict
```

Every refresh run — daily full and hourly quick — invokes this without `--strict`. The
report carries versioned `health-finding-v1` records: a stable code/fingerprint identifies
the invariant and affected entity, while severity, evidence, and human wording can change
without creating a new incident. Errors and warnings each own an independently recoverable
**`data-health` GitHub issue**; informational findings remain visible on `/health` without
alarming. A recurrence reopens its original issue, evidence revisions update that issue,
and an authoritative sentinel recovery closes only the finding that disappeared. A partial
pre-deploy gate report may open or update incidents but cannot close findings it did not
observe. Quick runs red only for a new or
recurrent finding, so standing incidents do not alert hourly; full runs remain the daily
heartbeat. `output_findings()` in `data/health.py` holds the produced-output invariants and
`output_problems()` is its rollout compatibility wrapper. Thresholds are the `HEALTH_*`
constants in `config.py`.
A separate daily `watchdog.yml` workflow guards the pipeline's own liveness: if
`refresh.yml` has no successful run in 26h, it opens a `watchdog` issue and reds itself.

Private outputs land in `data/output/<tour>/`: `predictor.pkl` plus its strict integrity
envelope, `players.json` (current ratings + official live ranks), `meta.json`, and
`accuracy.json` (rolling-window metrics for the site's accuracy view). An all-tour run seals
the exact public JSON graph into a shared manifest; the semantic gate accepts that candidate
before the publisher mirrors only its declared bytes into `web/public/data/`. Single-tour runs
revoke any stale all-tour validity pointer and never publish.

### Kalshi evaluation ledger (benchmark only — never a model input)

`data/kalshi_ledger/{atp,wta}.csv` records every Kalshi tennis match market next to
our pre-match probability and the final result; `report.md` alongside is the
segmented model-vs-market scorecard (paired d±SE by rank band, favorite strength,
surface, tier, round, disagreement size). Both are committed daily by CI. Kalshi
prices are de-vigged bid/ask mids at 08:00 UTC on match day, reconstructed from
1-minute candlesticks — in-play trading makes settled last-prices useless, and
Kalshi's own start timestamps mutate on settled markets, so morning-of is the
latest provably pre-match anchor; `pred_source` separates live-frozen forecasts
from walk-forward backfill.

```bash
# capture market snapshots (public API, no key) + rebuild ledger and scorecard
PYTHONPATH=src uv run --with-requirements requirements.txt python -m tennis_model.data.kalshi --tour all
PYTHONPATH=src uv run --with-requirements requirements.txt python -m tennis_model.eval.kalshi_ledger --tour all
PYTHONPATH=src uv run --with-requirements requirements.txt python -m tennis_model.eval.kalshi_report
```

## Methodology notes

- **No leakage.** Every rating/feature is recorded *before* its match in a single
  chronological pass, so the backtest is walk-forward by construction. Market odds are
  used only to benchmark, never as model inputs.
- **Balanced training.** Features are stored as winner-minus-loser differences, then a
  random half are sign-flipped so the label is ~50/50 — the model can't learn "player A
  always wins."
- **Calibration.** Platt scaling (not isotonic): with a few thousand calibration points
  isotonic forms wide plateaus that collapse distinct matchups to identical
  probabilities. (Stacked and beta calibration were both tried and rejected on
  validation — see the tuning logs.)
- **Adoption gates.** Sweeps optimize the 2010–19 window; candidates must also hold up
  on 2020+ (paired per-match log-loss, ±SE) and then survive a full 2010–2026
  walk-forward with the combiner retrained — component-level wins that the combiner
  absorbs are rejected. Determinism is pinned by tests (`n_bag=1` bit-identity,
  anti-drift locks).

## Limitations / future work

- **Lower-tier state is deliberately asymmetric by tour.** ATP Challengers + qualifying
  (2005+/2007+) feed every Elo/point/context walk. WTA qualifying/125 history begins only in
  2016, so it feeds a second state bundle selected by the frozen 32-main-match cold-start gate;
  protected WTA matchups remain bit-identical to the main-only baseline. Both combiners still
  train, calibrate and score on main draws only.
- The **draw simulator uses current ratings**, ideal for projecting *upcoming* events;
  a true historical sim backtest would need as-of-date ratings.
- **Event-speed serve baselines and Elo-level home bonuses** were built, gated, and
  rejected by the arbiter (the code remains behind default-off flags for future
  rounds).
- The **web frontend** (Python → JSON → Next.js, `web/`) is live at
  https://deuce-forecast.web.app/ — see the root README.
