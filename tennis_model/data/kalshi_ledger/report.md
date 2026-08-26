# Model vs Kalshi — match-by-match scorecard

_Generated 2026-08-26T06:46:36Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1648 | 1483 | 103 | 8 | 54 | 0 | 10 | 15 | 78 | 2026-05-03..2026-08-27 |
| wta | 1637 | 951 | 98 | 547 | 41 | 0 | 6 | 15 | 52 | 2026-05-02..2026-08-26 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 999 | 0.6117 | 0.6105 | -0.0012 ±0.0063 | -0.0015 ±0.0025 | 0.650 | 0.657 |
| atp | 488 | 0.6264 | 0.6306 | +0.0041 ±0.0087 | +0.0001 ±0.0035 | 0.637 | 0.657 |
| wta | 511 | 0.5976 | 0.5913 | -0.0063 ±0.0090 | -0.0030 ±0.0037 | 0.661 | 0.657 |
| pooled/live_aligned | 84 | 0.6768 | 0.6601 | -0.0168 ±0.0154 | -0.0076 ±0.0067 | 0.548 | 0.530 |
| pooled/backtest | 915 | 0.6057 | 0.6059 | +0.0002 ±0.0067 | -0.0009 ±0.0027 | 0.659 | 0.668 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 84 | -0.0168 ±0.0154 | -0.0076 ±0.0067 | -1.1 | 0.548 | 0.530 | |
| pred_source: backtest | 915 | +0.0002 ±0.0067 | -0.0009 ±0.0027 | +0.0 | 0.659 | 0.668 | |
| top-20 involved | 351 | +0.0086 ±0.0093 | +0.0013 ±0.0031 | +0.9 | 0.699 | 0.699 | |
| no top-20 player | 648 | -0.0066 ±0.0082 | -0.0030 ±0.0036 | -0.8 | 0.623 | 0.633 | |
| both inside top-50 | 231 | +0.0067 ±0.0106 | +0.0021 ±0.0046 | +0.6 | 0.652 | 0.647 | |
| someone outside top-50 | 768 | -0.0036 ±0.0075 | -0.0026 ±0.0030 | -0.5 | 0.649 | 0.660 | |
| best rank 1-10 | 207 | +0.0274 ±0.0130 | +0.0073 ±0.0039 | +2.1 | 0.705 | 0.700 | |
| best rank 11-20 | 144 | -0.0184 ±0.0126 | -0.0074 ±0.0050 | -1.5 | 0.691 | 0.698 | |
| best rank 21-50 | 347 | -0.0148 ±0.0091 | -0.0065 ±0.0041 | -1.6 | 0.628 | 0.666 | |
| best rank 51-100 | 249 | +0.0006 ±0.0146 | -0.0002 ±0.0062 | +0.0 | 0.608 | 0.596 | |
| best rank 100+ | 52 | +0.0140 ±0.0441 | +0.0072 ±0.0189 | +0.3 | 0.654 | 0.596 | |
| kalshi favorite 0.5-0.6 | 295 | -0.0258 ±0.0098 | -0.0121 ±0.0047 | -2.6 | 0.480 | 0.525 | |
| kalshi favorite 0.6-0.7 | 286 | -0.0005 ±0.0108 | +0.0006 ±0.0049 | -0.1 | 0.619 | 0.605 | |
| kalshi favorite 0.7-0.8 | 232 | +0.0053 ±0.0108 | +0.0022 ±0.0045 | +0.5 | 0.739 | 0.737 | |
| kalshi favorite 0.8-0.9 | 126 | +0.0306 ±0.0226 | +0.0098 ±0.0083 | +1.4 | 0.817 | 0.810 | |
| kalshi favorite 0.9-1.0 | 60 | +0.0240 ±0.0427 | +0.0028 ±0.0109 | +0.6 | 0.933 | 0.917 | |
| surface: Hard | 149 | +0.0049 ±0.0155 | +0.0023 ±0.0065 | +0.3 | 0.584 | 0.554 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 317 | -0.0059 ±0.0124 | -0.0035 ±0.0052 | -0.5 | 0.609 | 0.617 | |
| tier: atp500 | 196 | -0.0113 ±0.0101 | -0.0056 ±0.0045 | -1.1 | 0.607 | 0.610 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 262 | +0.0047 ±0.0147 | -0.0007 ±0.0054 | +0.3 | 0.700 | 0.718 | |
| tier: masters | 223 | +0.0068 ±0.0099 | +0.0039 ±0.0044 | +0.7 | 0.684 | 0.682 | |
| round early (R128-R64) | 360 | +0.0006 ±0.0113 | -0.0007 ±0.0044 | +0.0 | 0.696 | 0.704 | |
| round late (QF-F) | 124 | -0.0041 ±0.0126 | -0.0029 ±0.0055 | -0.3 | 0.645 | 0.637 | |
| round mid (R32-R16) | 493 | -0.0016 ±0.0090 | -0.0017 ±0.0037 | -0.2 | 0.624 | 0.632 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 135 | +0.0039 ±0.0136 | +0.0007 ±0.0059 | +0.3 | 0.570 | 0.544 | |
| agree (<0.05) | 522 | -0.0001 ±0.0033 | -0.0008 ±0.0011 | -0.0 | 0.690 | 0.684 | |
| mild disagree (0.05-0.10) | 312 | -0.0023 ±0.0102 | -0.0026 ±0.0039 | -0.2 | 0.614 | 0.647 | |
| big disagree (>=0.1) | 165 | -0.0029 ±0.0310 | -0.0015 ±0.0132 | -0.1 | 0.591 | 0.588 | |
| tour: atp | 488 | +0.0041 ±0.0087 | +0.0001 ±0.0035 | +0.5 | 0.637 | 0.657 | |
| tour: wta | 511 | -0.0063 ±0.0090 | -0.0030 ±0.0037 | -0.7 | 0.661 | 0.657 | |

When they disagree by >= 0.1: model closer to the outcome in **68/165** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 10 | 0.066 | 0.100 |
| 0.1-0.2 | 55 | 0.153 | 0.109 |
| 0.2-0.3 | 85 | 0.253 | 0.247 |
| 0.3-0.4 | 143 | 0.354 | 0.371 |
| 0.4-0.5 | 180 | 0.450 | 0.483 |
| 0.5-0.6 | 169 | 0.551 | 0.527 |
| 0.6-0.7 | 156 | 0.646 | 0.622 |
| 0.7-0.8 | 116 | 0.748 | 0.759 |
| 0.8-0.9 | 63 | 0.845 | 0.794 |
| 0.9-1.0 | 22 | 0.925 | 0.909 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 25 | 0.060 | 0.080 |
| 0.1-0.2 | 53 | 0.155 | 0.151 |
| 0.2-0.3 | 101 | 0.254 | 0.277 |
| 0.3-0.4 | 130 | 0.353 | 0.385 |
| 0.4-0.5 | 154 | 0.442 | 0.461 |
| 0.5-0.6 | 143 | 0.556 | 0.510 |
| 0.6-0.7 | 154 | 0.648 | 0.604 |
| 0.7-0.8 | 131 | 0.746 | 0.748 |
| 0.8-0.9 | 73 | 0.846 | 0.781 |
| 0.9-1.0 | 35 | 0.933 | 0.914 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 207 | +0.0274 ±0.0130 | +0.0073 ±0.0039 | +2.1 | 0.705 | 0.700 | |
| kalshi favorite 0.8-0.9 | 126 | +0.0306 ±0.0226 | +0.0098 ±0.0083 | +1.4 | 0.817 | 0.810 | |
| top-20 involved | 351 | +0.0086 ±0.0093 | +0.0013 ±0.0031 | +0.9 | 0.699 | 0.699 | |
| tier: masters | 223 | +0.0068 ±0.0099 | +0.0039 ±0.0044 | +0.7 | 0.684 | 0.682 | |
| both inside top-50 | 231 | +0.0067 ±0.0106 | +0.0021 ±0.0046 | +0.6 | 0.652 | 0.647 | |
| kalshi favorite 0.9-1.0 | 60 | +0.0240 ±0.0427 | +0.0028 ±0.0109 | +0.6 | 0.933 | 0.917 | |
| kalshi favorite 0.7-0.8 | 232 | +0.0053 ±0.0108 | +0.0022 ±0.0045 | +0.5 | 0.739 | 0.737 | |
| tour: atp | 488 | +0.0041 ±0.0087 | +0.0001 ±0.0035 | +0.5 | 0.637 | 0.657 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| tour: wta | 511 | -0.0063 ±0.0090 | -0.0030 ±0.0037 | -0.7 | 0.661 | 0.657 | |
| no top-20 player | 648 | -0.0066 ±0.0082 | -0.0030 ±0.0036 | -0.8 | 0.623 | 0.633 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| pred_source: live aligned | 84 | -0.0168 ±0.0154 | -0.0076 ±0.0067 | -1.1 | 0.548 | 0.530 | |
| tier: atp500 | 196 | -0.0113 ±0.0101 | -0.0056 ±0.0045 | -1.1 | 0.607 | 0.610 | |
| best rank 11-20 | 144 | -0.0184 ±0.0126 | -0.0074 ±0.0050 | -1.5 | 0.691 | 0.698 | |
| best rank 21-50 | 347 | -0.0148 ±0.0091 | -0.0065 ±0.0041 | -1.6 | 0.628 | 0.666 | |
| kalshi favorite 0.5-0.6 | 295 | -0.0258 ±0.0098 | -0.0121 ±0.0047 | -2.6 | 0.480 | 0.525 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=999, mean |Δ|=0.0021, p95=0.0099, >0.05 in 2 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0138 (n=135, >0.05: 1)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=999, d_ll -0.0012 ±0.0063 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 459 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Mallorca': 1, 'ATP Cincinnati': 1, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Alexandra Eala, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Carolyn Ansari, Casper Ruud, Caty McNally, Celine Naef, Chloe Paquet, Claire Liu, Clervie Ngounoue, Dalma Galfi, Daphnee Mpetshi Perricard
