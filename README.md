# DEUCE — Tennis Forecast Engine (ATP + WTA)

[![refresh](https://github.com/ARJUNVARMA2000/tennis-elo/actions/workflows/refresh.yml/badge.svg)](https://github.com/ARJUNVARMA2000/tennis-elo/actions/workflows/refresh.yml)
[![tests](https://github.com/ARJUNVARMA2000/tennis-elo/actions/workflows/test.yml/badge.svg)](https://github.com/ARJUNVARMA2000/tennis-elo/actions/workflows/test.yml)
[![live site](https://img.shields.io/badge/live-arjunvarma2000.github.io%2Ftennis--elo-828fff)](https://arjunvarma2000.github.io/tennis-elo/)

A hybrid forecasting system for men's and women's professional tennis. It pairs
**surface-blended Elo** with an **opponent-adjusted serve/return point model** and
**Match-Charting style features**, fused by a **Platt-calibrated XGBoost combiner**.
Outputs calibrated match win probabilities, full set-score distributions, Monte Carlo
draw projections, and a live web app — data refreshed **hourly**, retrained daily, for
**both tours**, with a real-time ESPN live-score ticker on the site.

🌐 Live site: **https://arjunvarma2000.github.io/tennis-elo/**

## Screenshots

| Slam forecast + live ticker | Rankings | Playing-style radar |
|---|---|---|
| ![Home — round-by-round slam forecast](docs/home.png) | ![Rankings — surface-blended Elo board](docs/rankings.png) | ![Playing style — 13-axis radar comparison](docs/style.png) |

## Why this design

Across the literature, sophisticated ML doesn't beat a good Elo on its own — it only
*matches* it, while the betting market is the ceiling (~69% acc / 0.196 Brier). The
winning recipe is a **hybrid**: engineer strong Elo + point-model features, then let
gradient boosting combine and calibrate them. Walk-forward, leakage-free results:

| Model | ATP Brier | WTA Brier |
|---|---|---|
| Surface-blended Elo | 0.218 | 0.219 |
| Serve/return point model | 0.220 | 0.225 |
| **XGBoost combiner** | **0.205** | **0.210** |
| _Bookmaker (literature anchor)_ | _0.196_ | _0.196_ |

The combiner beats every component and closes ~90% of the Elo→market gap on both tours.
Feature importance confirms the thesis: Elo (overall + surface) is ~78% of the signal.

## Architecture

```
data ─┬─ surface-blended Elo (dynamic K, margin-of-victory)
      ├─ serve/return point model (per-surface, opponent-adjusted; point→game→set→match Markov)
      └─ MCP style + context (rest, fatigue, H2H, hand, rank)
                         │
                  XGBoost combiner  ──Platt──> calibrated P(A beats B) + set distribution
            ┌────────────┴────────────┐
     match predictor            Monte Carlo draw simulator
```

## Data — hourly fresh (the hard part)

Jeff Sackmann's canonical repos went private in 2026, and no single free mirror is both
fresh *and* full-schema. So each tour **merges** two sources:

- **Full-schema historical** (serve stats; slow-moving): `Tennismylife/TML-Database` (ATP),
  a full-schema WTA snapshot (`zeldao08/tennis_players_analysis`).
- **Fresh weekly results** (results-only; drives Elo): `LuckyLoser91/TennisCourtLog`
  (auto-refreshed, both tours).
- **Style**: `JeffSackmann/tennis_MatchChartingProject` (`charting-m/w-*`).

Results (the dominant ~78% signal) stay current to the hour via **ESPN's live scoreboard
API**; serve stats lag harmlessly. Names are canonicalised across sources so the same
player isn't split. A **GitHub Action**
([`.github/workflows/refresh.yml`](.github/workflows/refresh.yml)) re-pulls ESPN results
and redeploys **hourly**, and does a full re-download + retrain of both tours daily.

## Repo layout

```
tennis_model/        Python model + pipeline (see tennis_model/README.md)
  src/tennis_model/  config · data · ratings · points · model · sim · eval
web/                 Next.js 16 app (8 views, ATP/WTA toggle, static export)
.github/workflows/   weekly-refresh + Pages deploy
```

## Run it locally

```bash
# 1. model: download data, train both tours, write JSON
cd tennis_model && pip install -r requirements.txt
PYTHONPATH=src python -m tennis_model.data.download --kind all
PYTHONPATH=src python -m tennis_model.pipeline --tour all --backtest

# ad-hoc queries
PYTHONPATH=src python -m tennis_model.cli predict "Jannik Sinner" "Carlos Alcaraz" --surface Hard --bo 5
PYTHONPATH=src python -m tennis_model.cli project-slam "Wimbledon" 2025

# 2. web: dev server (reads tennis_model JSON, mirrored to web/public/data)
cd ../web && npm install && npm run dev
```

## The twelve views

Slam-focus home (round-by-round title forecast + **live ESPN score ticker with model
win odds, polled straight from the browser**) · Rankings · Match Predictor · Draw
Simulator · Latest results (with model calls) · Player profiles (Elo history, surface
splits, serve/return + style fingerprint, H2H) · Playing-style radar · Serve/return
strength map · Trends & movers · Accuracy vs market · Track record · Method — all with
an ATP/WTA toggle, a Linear-style dark UI, and an "updated Xm ago" freshness pill.
