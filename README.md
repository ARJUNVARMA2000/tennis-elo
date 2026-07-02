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

| Model (walk-forward 2010–2026) | ATP Brier | WTA Brier |
|---|---|---|
| Surface-blended Elo (tuned per tour) | 0.207 | 0.212 |
| Serve/return point model (tuned) | 0.209 | 0.215 |
| **XGBoost combiner** | **0.198** | **0.203** |
| _Bookmaker (literature anchor)_ | _0.196_ | _0.196_ |

The combiner beats every component on both tours; the ATP model sits within ~0.002
Brier of the bookmaker ceiling. Every constant is tuned offline per tour (Optuna,
2010–19 tune window, 2020+ validation — see `eval/tune.py`); feature importance
confirms the thesis: Elo (overall + surface) carries most of the signal.

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

Jeff Sackmann's canonical repos went private in 2026 and the free mirrors keep freezing,
so each tour **merges four sources**, deduplicated with stats-bearing rows winning:

- **Full-schema historical** (serve stats; frozen upstreams, snapshot-backed):
  `Tennismylife/TML-Database` (ATP), a full-schema WTA snapshot.
- **Daily stats overlay** (serve stats, current season): ATP from
  [stats.tennismylife.org](https://stats.tennismylife.org) (TML's daily-updated home);
  WTA **scraped from the first-party wtatennis.com API** (`data/wta_stats.py`) — no free
  bulk source has carried WTA serve stats since mid-2024.
- **Fresh weekly results** (results-only): `LuckyLoser91/TennisCourtLog` (both tours).
- **Style**: `JeffSackmann/tennis_MatchChartingProject`; **odds benchmark**:
  Tennis-Data.co.uk closing odds (Pinnacle/Bet365), auto-downloaded, never a model input.

Results (the dominant signal) stay current to the hour via **ESPN's live scoreboard
API**. Names are canonicalised across sources so the same player isn't split. A
**GitHub Action** ([`.github/workflows/refresh.yml`](.github/workflows/refresh.yml))
re-pulls ESPN results and redeploys **hourly**, does a full re-download + retrain of
both tours daily, snapshots the raw data to a release asset weekly (upstreams keep
disappearing), and a **freshness sentinel** (`data/health.py`) turns the build red if
any source silently stalls — schema-validated, atomic downloads mean a broken upstream
can never clobber good data.

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
