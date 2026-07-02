# Men's Tennis Prediction Model

A hybrid forecasting system for men's (ATP) singles tennis. It pairs **surface-blended
Elo** and a **serve/return point model** with an **XGBoost combiner**, producing
calibrated single-match win probabilities, full set-score distributions, and Monte
Carlo tournament-draw projections.

## Why this design

The research is consistent: sophisticated ML does **not** beat a good Elo on its own —
even graph neural nets only *match* Weighted Elo (~66% acc / 0.212 Brier), while the
betting market is the ceiling (~69% / 0.196). The winning recipe is a **hybrid**:
engineer strong Elo- and point-model features, then let gradient boosting *combine and
calibrate* them. So Elo isn't replaced by XGBoost — it's the dominant feature feeding it.

**Walk-forward, leakage-free results** (no future info, no market odds as inputs):

| Model | Accuracy | Log-loss | Brier |
|---|---|---|---|
| Elo blended (overall + surface) | 0.670 | 0.615 | 0.211 |
| Serve/return point model | 0.635 | 0.631 | 0.221 |
| **XGBoost combiner** | **0.684** | **0.581** | **0.1995** |
| _Bookmaker anchor (literature)_ | _0.690_ | — | _0.196_ |

(2012–2025 OOS; on the tougher 2018–2025 era the combiner is 0.659 / 0.210 vs Elo
0.651 / 0.222 — it wins on every metric in both windows.) The combiner closes ~95% of
the Elo→market gap, and its calibration is near-perfect after Platt scaling.

The Monte Carlo simulator, run on the four 2025 Grand Slam draws (reconstructed from
results), made the two actual finalists its top-2 favorites **every time**, with the
actual champion ranked #1 or #2 in all four.

## Architecture

```
data ─┬─ surface-blended Elo  (overall + hard/clay/grass, dynamic K, margin-of-victory)
      ├─ serve/return point model  (time-decayed serve%/return% -> hierarchical
      │                             point→game→tiebreak→set→match Markov; Bo3/Bo5)
      └─ context  (rest, in-window fatigue, head-to-head, hand, rank, age, ...)
                         │
                  XGBoost combiner  (24 features) ──Platt──>  calibrated P(A beats B)
                         │                                    + set-score distribution
            ┌────────────┴────────────┐
     single-match predictor     Monte Carlo draw simulator (per-round + title odds)
```

The point model is what yields a full **score distribution** and makes Bo3-vs-Bo5 fall
out correctly (a per-point edge compounds over more sets) — it's the tennis analog of a
soccer Dixon-Coles goal model. XGBoost is the best single-number combiner. Feeding the
point-model probability in as one feature gives the best of both.

## Data

- **Backbone: [Tennismylife/TML-Database](https://github.com/Tennismylife/TML-Database)** —
  a live mirror of the (now-private) `JeffSackmann/tennis_atp`, identical schema plus an
  `indoor` flag. 151,340 tour matches 1980→present; serve stats from 1991 (~90%+).
  Downloaded via plain HTTPS with an authenticated `gh api` fallback (`data/download.py`).
- **Benchmark (optional): Tennis-Data.co.uk** — closing Pinnacle/Bet365 odds, for the
  model-vs-market scorecard (`eval/compare.py`). Drop yearly spreadsheets into
  `data/raw/odds/` if your network blocks the download.
- **Evaluated and *not* used as backbone:** the Match Charting Project charts only ~12%
  of post-2010 matches and is star-biased (top-20 players = 35% of data), so it can't
  anchor a rating system. It's reserved as a future *player-style* feature layer.

## Layout

```
src/tennis_model/
  config.py            tunable parameters (K-factors, surface blend, decay, paths)
  pipeline.py          orchestrator -> predictor.pkl, players.json, meta.json
  cli.py               ad-hoc predictions / draw projections
  data/                download, score parsing, loading + cleaning, odds
  ratings/             elo.py (math), build.py (chronological Elo walk)
  points/              serve_return.py (skill walk), markov.py (hierarchical model)
  model/               features.py, train.py (XGBoost + Platt + walk-forward), predict.py
  sim/                 draws.py (bracket build/reconstruct), simulate.py (Monte Carlo)
  eval/                metrics.py, backtest.py, compare.py (vs market)
```

## Usage

```bash
pip install -r requirements.txt
cd tennis_model

# build everything (data is already cached under data/raw/matches)
PYTHONPATH=src python -m tennis_model.pipeline --download --backtest

# ad-hoc queries (after the pipeline has trained a predictor)
PYTHONPATH=src python -m tennis_model.cli predict "Jannik Sinner" "Carlos Alcaraz" --surface Hard --bo 5
PYTHONPATH=src python -m tennis_model.cli project-slam "Wimbledon" 2025
PYTHONPATH=src python -m tennis_model.cli field "Jannik Sinner" "Carlos Alcaraz" "Novak Djokovic" --surface Clay --bo 5

# evaluation
PYTHONPATH=src python -m tennis_model.eval.backtest --start 2010      # Elo baselines
PYTHONPATH=src python -m tennis_model.model.train --start 2012        # combiner walk-forward
PYTHONPATH=src python -m tennis_model.eval.compare                    # vs market (needs odds files)
```

Outputs land in `data/output/`: `predictor.pkl`, `players.json` (current ratings),
`meta.json` (metadata + backtest metrics).

## Methodology notes

- **No leakage.** Every rating/feature is recorded *before* its match in a single
  chronological pass, so the backtest is walk-forward by construction. Market odds are
  used only to benchmark, never as model inputs.
- **Balanced training.** Features are stored as winner-minus-loser differences, then a
  random half are sign-flipped so the label is ~50/50 — the model can't learn "player A
  always wins."
- **Calibration.** Platt scaling (not isotonic): with a few thousand calibration points
  isotonic forms wide plateaus that collapse distinct matchups to identical probabilities.
- **Dynamic K** `250/(n+5)^0.4`, surface ratings seeded from overall on first appearance,
  margin-of-victory from games won.

## Limitations / future work

- **Challengers** aren't in the TML mirror, so coverage is tour-level only.
- The **draw simulator uses current ratings**, ideal for projecting *upcoming* events;
  a true historical sim backtest would need as-of-date ratings.
- **MCP tactical-profile layer**, surface-specific serve skill, and opponent-adjusted
  (strength-of-schedule) serve/return are the highest-value next features.
- The **web frontend** (Python → JSON → Next.js, `web/`) is live at
  https://arjunvarma2000.github.io/tennis-elo/ — see the root README.
```
