# Model vs Kalshi — match-by-match scorecard

_Generated 2026-08-23T04:50:29Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1518 | 1439 | 25 | 8 | 46 | 0 | 10 | 15 | 58 | 2026-05-03..2026-08-23 |
| wta | 1526 | 928 | 21 | 539 | 38 | 0 | 6 | 15 | 29 | 2026-05-02..2026-08-24 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 943 | 0.6063 | 0.6049 | -0.0014 ±0.0065 | -0.0017 ±0.0026 | 0.657 | 0.668 |
| atp | 454 | 0.6188 | 0.6266 | +0.0078 ±0.0091 | +0.0014 ±0.0037 | 0.650 | 0.667 |
| wta | 489 | 0.5947 | 0.5847 | -0.0100 ±0.0091 | -0.0045 ±0.0037 | 0.665 | 0.668 |
| pooled/live_aligned | 37 | 0.6182 | 0.6180 | -0.0002 ±0.0165 | -0.0014 ±0.0075 | 0.595 | 0.568 |
| pooled/backtest | 906 | 0.6058 | 0.6044 | -0.0015 ±0.0067 | -0.0017 ±0.0027 | 0.660 | 0.672 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 37 | -0.0002 ±0.0165 | -0.0014 ±0.0075 | -0.0 | 0.595 | 0.568 | ⚠ small n |
| pred_source: backtest | 906 | -0.0015 ±0.0067 | -0.0017 ±0.0027 | -0.2 | 0.660 | 0.672 | |
| top-20 involved | 344 | +0.0099 ±0.0094 | +0.0017 ±0.0031 | +1.0 | 0.702 | 0.702 | |
| no top-20 player | 599 | -0.0080 ±0.0086 | -0.0036 ±0.0037 | -0.9 | 0.632 | 0.648 | |
| both inside top-50 | 225 | +0.0071 ±0.0108 | +0.0023 ±0.0047 | +0.7 | 0.651 | 0.647 | |
| someone outside top-50 | 718 | -0.0041 ±0.0078 | -0.0029 ±0.0031 | -0.5 | 0.659 | 0.674 | |
| best rank 1-10 | 202 | +0.0293 ±0.0132 | +0.0079 ±0.0039 | +2.2 | 0.708 | 0.703 | |
| best rank 11-20 | 142 | -0.0177 ±0.0127 | -0.0071 ±0.0050 | -1.4 | 0.694 | 0.701 | |
| best rank 21-50 | 334 | -0.0131 ±0.0095 | -0.0058 ±0.0042 | -1.4 | 0.635 | 0.674 | |
| best rank 51-100 | 223 | +0.0035 ±0.0157 | +0.0010 ±0.0066 | +0.2 | 0.621 | 0.610 | |
| best rank 100+ | 42 | -0.0275 ±0.0502 | -0.0111 ±0.0215 | -0.5 | 0.667 | 0.643 | ⚠ small n |
| kalshi favorite 0.5-0.6 | 273 | -0.0258 ±0.0103 | -0.0121 ±0.0049 | -2.5 | 0.485 | 0.544 | |
| kalshi favorite 0.6-0.7 | 268 | -0.0021 ±0.0111 | -0.0003 ±0.0050 | -0.2 | 0.627 | 0.612 | |
| kalshi favorite 0.7-0.8 | 221 | +0.0061 ±0.0111 | +0.0025 ±0.0046 | +0.5 | 0.744 | 0.742 | |
| kalshi favorite 0.8-0.9 | 122 | +0.0284 ±0.0227 | +0.0088 ±0.0083 | +1.3 | 0.820 | 0.811 | |
| kalshi favorite 0.9-1.0 | 59 | +0.0242 ±0.0434 | +0.0028 ±0.0110 | +0.6 | 0.932 | 0.915 | |
| surface: Hard | 93 | +0.0065 ±0.0196 | +0.0026 ±0.0081 | +0.3 | 0.624 | 0.602 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 284 | -0.0010 ±0.0134 | -0.0017 ±0.0056 | -0.1 | 0.623 | 0.627 | |
| tier: atp500 | 185 | -0.0127 ±0.0102 | -0.0061 ±0.0046 | -1.2 | 0.611 | 0.624 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 253 | -0.0021 ±0.0148 | -0.0038 ±0.0054 | -0.1 | 0.706 | 0.731 | |
| tier: masters | 220 | +0.0077 ±0.0101 | +0.0043 ±0.0045 | +0.8 | 0.684 | 0.682 | |
| round early (R128-R64) | 335 | -0.0028 ±0.0118 | -0.0022 ±0.0046 | -0.2 | 0.706 | 0.719 | |
| round late (QF-F) | 118 | -0.0040 ±0.0131 | -0.0028 ±0.0057 | -0.3 | 0.644 | 0.636 | |
| round mid (R32-R16) | 468 | +0.0004 ±0.0092 | -0.0010 ±0.0038 | +0.0 | 0.634 | 0.644 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 79 | +0.0050 ±0.0148 | -0.0000 ±0.0065 | +0.3 | 0.608 | 0.595 | |
| agree (<0.05) | 492 | -0.0013 ±0.0034 | -0.0014 ±0.0011 | -0.4 | 0.699 | 0.696 | |
| mild disagree (0.05-0.10) | 296 | -0.0000 ±0.0105 | -0.0018 ±0.0040 | -0.0 | 0.613 | 0.652 | |
| big disagree (>=0.1) | 155 | -0.0047 ±0.0321 | -0.0022 ±0.0136 | -0.1 | 0.610 | 0.606 | |
| tour: atp | 454 | +0.0078 ±0.0091 | +0.0014 ±0.0037 | +0.8 | 0.650 | 0.667 | |
| tour: wta | 489 | -0.0100 ±0.0091 | -0.0045 ±0.0037 | -1.1 | 0.665 | 0.668 | |

When they disagree by >= 0.1: model closer to the outcome in **63/155** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 10 | 0.066 | 0.100 |
| 0.1-0.2 | 54 | 0.153 | 0.093 |
| 0.2-0.3 | 79 | 0.253 | 0.253 |
| 0.3-0.4 | 130 | 0.353 | 0.346 |
| 0.4-0.5 | 174 | 0.451 | 0.477 |
| 0.5-0.6 | 155 | 0.552 | 0.535 |
| 0.6-0.7 | 150 | 0.646 | 0.627 |
| 0.7-0.8 | 109 | 0.748 | 0.752 |
| 0.8-0.9 | 61 | 0.846 | 0.803 |
| 0.9-1.0 | 21 | 0.925 | 0.905 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 25 | 0.060 | 0.080 |
| 0.1-0.2 | 50 | 0.153 | 0.140 |
| 0.2-0.3 | 97 | 0.254 | 0.268 |
| 0.3-0.4 | 120 | 0.352 | 0.375 |
| 0.4-0.5 | 145 | 0.442 | 0.441 |
| 0.5-0.6 | 130 | 0.556 | 0.523 |
| 0.6-0.7 | 146 | 0.648 | 0.610 |
| 0.7-0.8 | 124 | 0.746 | 0.750 |
| 0.8-0.9 | 72 | 0.846 | 0.778 |
| 0.9-1.0 | 34 | 0.933 | 0.912 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 202 | +0.0293 ±0.0132 | +0.0079 ±0.0039 | +2.2 | 0.708 | 0.703 | |
| kalshi favorite 0.8-0.9 | 122 | +0.0284 ±0.0227 | +0.0088 ±0.0083 | +1.3 | 0.820 | 0.811 | |
| top-20 involved | 344 | +0.0099 ±0.0094 | +0.0017 ±0.0031 | +1.0 | 0.702 | 0.702 | |
| tour: atp | 454 | +0.0078 ±0.0091 | +0.0014 ±0.0037 | +0.8 | 0.650 | 0.667 | |
| tier: masters | 220 | +0.0077 ±0.0101 | +0.0043 ±0.0045 | +0.8 | 0.684 | 0.682 | |
| both inside top-50 | 225 | +0.0071 ±0.0108 | +0.0023 ±0.0047 | +0.7 | 0.651 | 0.647 | |
| kalshi favorite 0.9-1.0 | 59 | +0.0242 ±0.0434 | +0.0028 ±0.0110 | +0.6 | 0.932 | 0.915 | |
| kalshi favorite 0.7-0.8 | 221 | +0.0061 ±0.0111 | +0.0025 ±0.0046 | +0.5 | 0.744 | 0.742 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| no top-20 player | 599 | -0.0080 ±0.0086 | -0.0036 ±0.0037 | -0.9 | 0.632 | 0.648 | |
| tour: wta | 489 | -0.0100 ±0.0091 | -0.0045 ±0.0037 | -1.1 | 0.665 | 0.668 | |
| tier: atp500 | 185 | -0.0127 ±0.0102 | -0.0061 ±0.0046 | -1.2 | 0.611 | 0.624 | |
| best rank 21-50 | 334 | -0.0131 ±0.0095 | -0.0058 ±0.0042 | -1.4 | 0.635 | 0.674 | |
| best rank 11-20 | 142 | -0.0177 ±0.0127 | -0.0071 ±0.0050 | -1.4 | 0.694 | 0.701 | |
| kalshi favorite 0.5-0.6 | 273 | -0.0258 ±0.0103 | -0.0121 ±0.0049 | -2.5 | 0.485 | 0.544 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=943, mean |Δ|=0.0021, p95=0.0098, >0.05 in 2 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0135 (n=79, >0.05: 1)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=943, d_ll -0.0014 ±0.0065 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 450 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Cincinnati': 2, 'ATP Los Cabos': 1, 'ATP Mallorca': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Alexandra Eala, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Carolyn Ansari, Casper Ruud, Caty McNally, Celine Naef, Chloe Paquet, Claire Liu, Clervie Ngounoue, Dalma Galfi, Daphnee Mpetshi Perricard
