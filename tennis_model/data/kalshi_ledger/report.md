# Model vs Kalshi — match-by-match scorecard

_Generated 2026-08-21T06:44:08Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1491 | 1435 | 2 | 8 | 46 | 0 | 10 | 15 | 42 | 2026-05-03..2026-08-22 |
| wta | 1503 | 924 | 2 | 539 | 38 | 0 | 6 | 15 | 19 | 2026-05-02..2026-08-21 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 938 | 0.6052 | 0.6032 | -0.0020 ±0.0065 | -0.0019 ±0.0026 | 0.660 | 0.670 |
| atp | 452 | 0.6178 | 0.6256 | +0.0077 ±0.0092 | +0.0014 ±0.0037 | 0.653 | 0.670 |
| wta | 486 | 0.5935 | 0.5825 | -0.0110 ±0.0091 | -0.0050 ±0.0037 | 0.667 | 0.670 |
| pooled/live_aligned | 33 | 0.5983 | 0.5920 | -0.0063 ±0.0176 | -0.0043 ±0.0080 | 0.636 | 0.606 |
| pooled/backtest | 905 | 0.6055 | 0.6036 | -0.0019 ±0.0067 | -0.0018 ±0.0027 | 0.661 | 0.672 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 33 | -0.0063 ±0.0176 | -0.0043 ±0.0080 | -0.4 | 0.636 | 0.606 | ⚠ small n |
| pred_source: backtest | 905 | -0.0019 ±0.0067 | -0.0018 ±0.0027 | -0.3 | 0.661 | 0.672 | |
| top-20 involved | 341 | +0.0096 ±0.0095 | +0.0016 ±0.0031 | +1.0 | 0.705 | 0.705 | |
| no top-20 player | 597 | -0.0086 ±0.0086 | -0.0039 ±0.0037 | -1.0 | 0.634 | 0.650 | |
| both inside top-50 | 221 | +0.0063 ±0.0110 | +0.0019 ±0.0048 | +0.6 | 0.658 | 0.654 | |
| someone outside top-50 | 717 | -0.0046 ±0.0078 | -0.0031 ±0.0031 | -0.6 | 0.660 | 0.675 | |
| best rank 1-10 | 200 | +0.0285 ±0.0133 | +0.0075 ±0.0039 | +2.1 | 0.710 | 0.705 | |
| best rank 11-20 | 141 | -0.0173 ±0.0128 | -0.0068 ±0.0051 | -1.3 | 0.699 | 0.706 | |
| best rank 21-50 | 332 | -0.0144 ±0.0095 | -0.0063 ±0.0042 | -1.5 | 0.639 | 0.678 | |
| best rank 51-100 | 223 | +0.0035 ±0.0157 | +0.0010 ±0.0066 | +0.2 | 0.621 | 0.610 | |
| best rank 100+ | 42 | -0.0275 ±0.0502 | -0.0111 ±0.0215 | -0.5 | 0.667 | 0.643 | ⚠ small n |
| kalshi favorite 0.5-0.6 | 271 | -0.0261 ±0.0104 | -0.0122 ±0.0049 | -2.5 | 0.485 | 0.544 | |
| kalshi favorite 0.6-0.7 | 266 | -0.0028 ±0.0111 | -0.0006 ±0.0051 | -0.2 | 0.632 | 0.617 | |
| kalshi favorite 0.7-0.8 | 220 | +0.0047 ±0.0111 | +0.0019 ±0.0046 | +0.4 | 0.748 | 0.745 | |
| kalshi favorite 0.8-0.9 | 122 | +0.0284 ±0.0227 | +0.0088 ±0.0083 | +1.3 | 0.820 | 0.811 | |
| kalshi favorite 0.9-1.0 | 59 | +0.0242 ±0.0434 | +0.0028 ±0.0110 | +0.6 | 0.932 | 0.915 | |
| surface: Hard | 88 | +0.0010 ±0.0203 | +0.0001 ±0.0084 | +0.0 | 0.648 | 0.625 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 282 | -0.0011 ±0.0135 | -0.0017 ±0.0056 | -0.1 | 0.628 | 0.631 | |
| tier: atp500 | 185 | -0.0127 ±0.0102 | -0.0061 ±0.0046 | -1.2 | 0.611 | 0.624 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 253 | -0.0021 ±0.0148 | -0.0038 ±0.0054 | -0.1 | 0.706 | 0.731 | |
| tier: masters | 217 | +0.0056 ±0.0102 | +0.0033 ±0.0045 | +0.6 | 0.689 | 0.687 | |
| round early (R128-R64) | 334 | -0.0038 ±0.0118 | -0.0027 ±0.0046 | -0.3 | 0.708 | 0.722 | |
| round late (QF-F) | 114 | -0.0059 ±0.0135 | -0.0037 ±0.0058 | -0.4 | 0.658 | 0.649 | |
| round mid (R32-R16) | 468 | +0.0004 ±0.0092 | -0.0010 ±0.0038 | +0.0 | 0.634 | 0.644 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 74 | -0.0017 ±0.0150 | -0.0032 ±0.0065 | -0.1 | 0.635 | 0.622 | |
| agree (<0.05) | 489 | -0.0015 ±0.0034 | -0.0015 ±0.0011 | -0.4 | 0.703 | 0.700 | |
| mild disagree (0.05-0.10) | 295 | -0.0004 ±0.0105 | -0.0020 ±0.0040 | -0.0 | 0.612 | 0.651 | |
| big disagree (>=0.1) | 154 | -0.0068 ±0.0322 | -0.0031 ±0.0137 | -0.2 | 0.614 | 0.610 | |
| tour: atp | 452 | +0.0077 ±0.0092 | +0.0014 ±0.0037 | +0.8 | 0.653 | 0.670 | |
| tour: wta | 486 | -0.0110 ±0.0091 | -0.0050 ±0.0037 | -1.2 | 0.667 | 0.670 | |

When they disagree by >= 0.1: model closer to the outcome in **62/154** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 10 | 0.066 | 0.100 |
| 0.1-0.2 | 54 | 0.153 | 0.093 |
| 0.2-0.3 | 79 | 0.253 | 0.253 |
| 0.3-0.4 | 130 | 0.353 | 0.346 |
| 0.4-0.5 | 172 | 0.451 | 0.471 |
| 0.5-0.6 | 155 | 0.552 | 0.535 |
| 0.6-0.7 | 147 | 0.646 | 0.633 |
| 0.7-0.8 | 109 | 0.748 | 0.752 |
| 0.8-0.9 | 61 | 0.846 | 0.803 |
| 0.9-1.0 | 21 | 0.925 | 0.905 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 25 | 0.060 | 0.080 |
| 0.1-0.2 | 50 | 0.153 | 0.140 |
| 0.2-0.3 | 97 | 0.254 | 0.268 |
| 0.3-0.4 | 119 | 0.352 | 0.370 |
| 0.4-0.5 | 144 | 0.442 | 0.438 |
| 0.5-0.6 | 129 | 0.556 | 0.519 |
| 0.6-0.7 | 145 | 0.648 | 0.614 |
| 0.7-0.8 | 123 | 0.746 | 0.756 |
| 0.8-0.9 | 72 | 0.846 | 0.778 |
| 0.9-1.0 | 34 | 0.933 | 0.912 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 200 | +0.0285 ±0.0133 | +0.0075 ±0.0039 | +2.1 | 0.710 | 0.705 | |
| kalshi favorite 0.8-0.9 | 122 | +0.0284 ±0.0227 | +0.0088 ±0.0083 | +1.3 | 0.820 | 0.811 | |
| top-20 involved | 341 | +0.0096 ±0.0095 | +0.0016 ±0.0031 | +1.0 | 0.705 | 0.705 | |
| tour: atp | 452 | +0.0077 ±0.0092 | +0.0014 ±0.0037 | +0.8 | 0.653 | 0.670 | |
| both inside top-50 | 221 | +0.0063 ±0.0110 | +0.0019 ±0.0048 | +0.6 | 0.658 | 0.654 | |
| kalshi favorite 0.9-1.0 | 59 | +0.0242 ±0.0434 | +0.0028 ±0.0110 | +0.6 | 0.932 | 0.915 | |
| tier: masters | 217 | +0.0056 ±0.0102 | +0.0033 ±0.0045 | +0.6 | 0.689 | 0.687 | |
| kalshi favorite 0.7-0.8 | 220 | +0.0047 ±0.0111 | +0.0019 ±0.0046 | +0.4 | 0.748 | 0.745 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| no top-20 player | 597 | -0.0086 ±0.0086 | -0.0039 ±0.0037 | -1.0 | 0.634 | 0.650 | |
| tour: wta | 486 | -0.0110 ±0.0091 | -0.0050 ±0.0037 | -1.2 | 0.667 | 0.670 | |
| tier: atp500 | 185 | -0.0127 ±0.0102 | -0.0061 ±0.0046 | -1.2 | 0.611 | 0.624 | |
| best rank 11-20 | 141 | -0.0173 ±0.0128 | -0.0068 ±0.0051 | -1.3 | 0.699 | 0.706 | |
| best rank 21-50 | 332 | -0.0144 ±0.0095 | -0.0063 ±0.0042 | -1.5 | 0.639 | 0.678 | |
| kalshi favorite 0.5-0.6 | 271 | -0.0261 ±0.0104 | -0.0122 ±0.0049 | -2.5 | 0.485 | 0.544 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=938, mean |Δ|=0.0021, p95=0.0098, >0.05 in 2 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0144 (n=74, >0.05: 1)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=938, d_ll -0.0020 ±0.0065 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 450 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Cincinnati': 2, 'ATP Mallorca': 1, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Alexandra Eala, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Carolyn Ansari, Casper Ruud, Caty McNally, Celine Naef, Chloe Paquet, Claire Liu, Clervie Ngounoue, Dalma Galfi, Daphnee Mpetshi Perricard
