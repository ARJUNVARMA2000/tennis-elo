# Model vs Kalshi — match-by-match scorecard

_Generated 2026-08-25T06:46:00Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1624 | 1469 | 94 | 7 | 54 | 0 | 10 | 15 | 71 | 2026-05-03..2026-08-26 |
| wta | 1615 | 945 | 92 | 539 | 39 | 0 | 6 | 15 | 42 | 2026-05-02..2026-08-26 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 980 | 0.6075 | 0.6073 | -0.0001 ±0.0063 | -0.0011 ±0.0026 | 0.656 | 0.662 |
| atp | 474 | 0.6208 | 0.6276 | +0.0068 ±0.0088 | +0.0010 ±0.0036 | 0.646 | 0.664 |
| wta | 506 | 0.5950 | 0.5884 | -0.0066 ±0.0090 | -0.0030 ±0.0037 | 0.666 | 0.661 |
| pooled/live_aligned | 65 | 0.6318 | 0.6274 | -0.0044 ±0.0132 | -0.0029 ±0.0061 | 0.615 | 0.577 |
| pooled/backtest | 915 | 0.6057 | 0.6059 | +0.0002 ±0.0067 | -0.0009 ±0.0027 | 0.659 | 0.668 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 65 | -0.0044 ±0.0132 | -0.0029 ±0.0061 | -0.3 | 0.615 | 0.577 | |
| pred_source: backtest | 915 | +0.0002 ±0.0067 | -0.0009 ±0.0027 | +0.0 | 0.659 | 0.668 | |
| top-20 involved | 350 | +0.0096 ±0.0093 | +0.0016 ±0.0031 | +1.0 | 0.701 | 0.701 | |
| no top-20 player | 630 | -0.0055 ±0.0083 | -0.0025 ±0.0036 | -0.7 | 0.631 | 0.640 | |
| both inside top-50 | 231 | +0.0067 ±0.0106 | +0.0021 ±0.0046 | +0.6 | 0.652 | 0.647 | |
| someone outside top-50 | 749 | -0.0022 ±0.0076 | -0.0020 ±0.0030 | -0.3 | 0.658 | 0.667 | |
| best rank 1-10 | 206 | +0.0292 ±0.0130 | +0.0079 ±0.0038 | +2.2 | 0.709 | 0.704 | |
| best rank 11-20 | 144 | -0.0184 ±0.0126 | -0.0074 ±0.0050 | -1.5 | 0.691 | 0.698 | |
| best rank 21-50 | 338 | -0.0142 ±0.0093 | -0.0062 ±0.0042 | -1.5 | 0.639 | 0.675 | |
| best rank 51-100 | 240 | +0.0026 ±0.0147 | +0.0006 ±0.0062 | +0.2 | 0.615 | 0.602 | |
| best rank 100+ | 52 | +0.0140 ±0.0441 | +0.0072 ±0.0189 | +0.3 | 0.654 | 0.596 | |
| kalshi favorite 0.5-0.6 | 285 | -0.0242 ±0.0101 | -0.0113 ±0.0048 | -2.4 | 0.486 | 0.530 | |
| kalshi favorite 0.6-0.7 | 281 | +0.0009 ±0.0108 | +0.0011 ±0.0049 | +0.1 | 0.626 | 0.612 | |
| kalshi favorite 0.7-0.8 | 230 | +0.0047 ±0.0106 | +0.0019 ±0.0044 | +0.4 | 0.746 | 0.743 | |
| kalshi favorite 0.8-0.9 | 124 | +0.0323 ±0.0229 | +0.0104 ±0.0084 | +1.4 | 0.815 | 0.806 | |
| kalshi favorite 0.9-1.0 | 60 | +0.0240 ±0.0427 | +0.0028 ±0.0109 | +0.6 | 0.933 | 0.917 | |
| surface: Hard | 130 | +0.0143 ±0.0160 | +0.0061 ±0.0068 | +0.9 | 0.623 | 0.581 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 303 | -0.0022 ±0.0127 | -0.0022 ±0.0053 | -0.2 | 0.620 | 0.625 | |
| tier: atp500 | 191 | -0.0121 ±0.0100 | -0.0058 ±0.0045 | -1.2 | 0.618 | 0.620 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 262 | +0.0047 ±0.0147 | -0.0007 ±0.0054 | +0.3 | 0.700 | 0.718 | |
| tier: masters | 223 | +0.0068 ±0.0099 | +0.0039 ±0.0044 | +0.7 | 0.684 | 0.682 | |
| round early (R128-R64) | 359 | +0.0004 ±0.0114 | -0.0008 ±0.0044 | +0.0 | 0.695 | 0.703 | |
| round late (QF-F) | 124 | -0.0041 ±0.0126 | -0.0029 ±0.0055 | -0.3 | 0.645 | 0.637 | |
| round mid (R32-R16) | 475 | +0.0008 ±0.0091 | -0.0007 ±0.0038 | +0.1 | 0.637 | 0.643 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 116 | +0.0142 ±0.0134 | +0.0047 ±0.0059 | +1.1 | 0.612 | 0.573 | |
| agree (<0.05) | 512 | -0.0004 ±0.0033 | -0.0010 ±0.0011 | -0.1 | 0.695 | 0.689 | |
| mild disagree (0.05-0.10) | 307 | -0.0002 ±0.0102 | -0.0019 ±0.0039 | -0.0 | 0.617 | 0.651 | |
| big disagree (>=0.1) | 161 | +0.0010 ±0.0314 | +0.0002 ±0.0134 | +0.0 | 0.606 | 0.596 | |
| tour: atp | 474 | +0.0068 ±0.0088 | +0.0010 ±0.0036 | +0.8 | 0.646 | 0.664 | |
| tour: wta | 506 | -0.0066 ±0.0090 | -0.0030 ±0.0037 | -0.7 | 0.666 | 0.661 | |

When they disagree by >= 0.1: model closer to the outcome in **67/161** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 10 | 0.066 | 0.100 |
| 0.1-0.2 | 54 | 0.153 | 0.093 |
| 0.2-0.3 | 83 | 0.253 | 0.253 |
| 0.3-0.4 | 138 | 0.353 | 0.362 |
| 0.4-0.5 | 177 | 0.451 | 0.475 |
| 0.5-0.6 | 165 | 0.551 | 0.533 |
| 0.6-0.7 | 154 | 0.646 | 0.630 |
| 0.7-0.8 | 116 | 0.748 | 0.759 |
| 0.8-0.9 | 61 | 0.846 | 0.803 |
| 0.9-1.0 | 22 | 0.925 | 0.909 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 25 | 0.060 | 0.080 |
| 0.1-0.2 | 52 | 0.154 | 0.154 |
| 0.2-0.3 | 101 | 0.254 | 0.277 |
| 0.3-0.4 | 126 | 0.353 | 0.373 |
| 0.4-0.5 | 149 | 0.443 | 0.456 |
| 0.5-0.6 | 138 | 0.556 | 0.514 |
| 0.6-0.7 | 153 | 0.649 | 0.608 |
| 0.7-0.8 | 129 | 0.746 | 0.760 |
| 0.8-0.9 | 72 | 0.846 | 0.778 |
| 0.9-1.0 | 35 | 0.933 | 0.914 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 206 | +0.0292 ±0.0130 | +0.0079 ±0.0038 | +2.2 | 0.709 | 0.704 | |
| kalshi favorite 0.8-0.9 | 124 | +0.0323 ±0.0229 | +0.0104 ±0.0084 | +1.4 | 0.815 | 0.806 | |
| month 2026-08 | 116 | +0.0142 ±0.0134 | +0.0047 ±0.0059 | +1.1 | 0.612 | 0.573 | |
| top-20 involved | 350 | +0.0096 ±0.0093 | +0.0016 ±0.0031 | +1.0 | 0.701 | 0.701 | |
| surface: Hard | 130 | +0.0143 ±0.0160 | +0.0061 ±0.0068 | +0.9 | 0.623 | 0.581 | |
| tour: atp | 474 | +0.0068 ±0.0088 | +0.0010 ±0.0036 | +0.8 | 0.646 | 0.664 | |
| tier: masters | 223 | +0.0068 ±0.0099 | +0.0039 ±0.0044 | +0.7 | 0.684 | 0.682 | |
| both inside top-50 | 231 | +0.0067 ±0.0106 | +0.0021 ±0.0046 | +0.6 | 0.652 | 0.647 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| no top-20 player | 630 | -0.0055 ±0.0083 | -0.0025 ±0.0036 | -0.7 | 0.631 | 0.640 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| tour: wta | 506 | -0.0066 ±0.0090 | -0.0030 ±0.0037 | -0.7 | 0.666 | 0.661 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp500 | 191 | -0.0121 ±0.0100 | -0.0058 ±0.0045 | -1.2 | 0.618 | 0.620 | |
| best rank 11-20 | 144 | -0.0184 ±0.0126 | -0.0074 ±0.0050 | -1.5 | 0.691 | 0.698 | |
| best rank 21-50 | 338 | -0.0142 ±0.0093 | -0.0062 ±0.0042 | -1.5 | 0.639 | 0.675 | |
| kalshi favorite 0.5-0.6 | 285 | -0.0242 ±0.0101 | -0.0113 ±0.0048 | -2.4 | 0.486 | 0.530 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=980, mean |Δ|=0.0021, p95=0.0099, >0.05 in 2 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0140 (n=116, >0.05: 1)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=980, d_ll -0.0001 ±0.0063 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 450 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Mallorca': 1, 'ATP Cincinnati': 1, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Alexandra Eala, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Carolyn Ansari, Casper Ruud, Caty McNally, Celine Naef, Chloe Paquet, Claire Liu, Clervie Ngounoue, Dalma Galfi, Daphnee Mpetshi Perricard
