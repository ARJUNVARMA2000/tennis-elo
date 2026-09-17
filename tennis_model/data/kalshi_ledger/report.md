# Model vs Kalshi — match-by-match scorecard

_Generated 2026-09-17T14:56:04Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1801 | 1734 | 0 | 10 | 57 | 0 | 11 | 19 | 43 | 2026-05-03..2026-09-13 |
| wta | 1867 | 1128 | 11 | 679 | 49 | 0 | 8 | 15 | 30 | 2026-05-02..2026-09-18 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1304 | 0.5959 | 0.5902 | -0.0058 ±0.0053 | -0.0032 ±0.0022 | 0.669 | 0.678 |
| atp | 628 | 0.6198 | 0.6196 | -0.0002 ±0.0073 | -0.0012 ±0.0029 | 0.650 | 0.665 |
| wta | 676 | 0.5738 | 0.5628 | -0.0109 ±0.0077 | -0.0050 ±0.0032 | 0.688 | 0.691 |
| pooled/live_aligned | 381 | 0.5699 | 0.5485 | -0.0215 ±0.0084 | -0.0090 ±0.0035 | 0.696 | 0.706 |
| pooled/backtest | 923 | 0.6067 | 0.6074 | +0.0007 ±0.0067 | -0.0008 ±0.0027 | 0.659 | 0.667 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 381 | -0.0215 ±0.0084 | -0.0090 ±0.0035 | -2.6 | 0.696 | 0.706 | |
| pred_source: backtest | 923 | +0.0007 ±0.0067 | -0.0008 ±0.0027 | +0.1 | 0.659 | 0.667 | |
| top-20 involved | 469 | +0.0081 ±0.0075 | +0.0013 ±0.0025 | +1.1 | 0.735 | 0.732 | |
| no top-20 player | 835 | -0.0135 ±0.0071 | -0.0057 ±0.0031 | -1.9 | 0.633 | 0.648 | |
| both inside top-50 | 313 | -0.0004 ±0.0090 | -0.0010 ±0.0039 | -0.0 | 0.663 | 0.657 | |
| someone outside top-50 | 991 | -0.0074 ±0.0064 | -0.0039 ±0.0026 | -1.2 | 0.672 | 0.685 | |
| best rank 1-10 | 283 | +0.0217 ±0.0101 | +0.0055 ±0.0030 | +2.1 | 0.746 | 0.739 | |
| best rank 11-20 | 186 | -0.0126 ±0.0110 | -0.0050 ±0.0042 | -1.1 | 0.718 | 0.723 | |
| best rank 21-50 | 452 | -0.0167 ±0.0081 | -0.0069 ±0.0036 | -2.1 | 0.655 | 0.687 | |
| best rank 51-100 | 311 | -0.0069 ±0.0127 | -0.0032 ±0.0054 | -0.5 | 0.603 | 0.598 | |
| best rank 100+ | 72 | -0.0226 ±0.0362 | -0.0089 ±0.0156 | -0.6 | 0.625 | 0.618 | |
| kalshi favorite 0.5-0.6 | 372 | -0.0265 ±0.0095 | -0.0123 ±0.0044 | -2.8 | 0.501 | 0.542 | |
| kalshi favorite 0.6-0.7 | 357 | -0.0033 ±0.0095 | -0.0011 ±0.0043 | -0.4 | 0.627 | 0.625 | |
| kalshi favorite 0.7-0.8 | 306 | -0.0017 ±0.0091 | -0.0006 ±0.0037 | -0.2 | 0.743 | 0.742 | |
| kalshi favorite 0.8-0.9 | 184 | +0.0157 ±0.0168 | +0.0050 ±0.0059 | +0.9 | 0.842 | 0.837 | |
| kalshi favorite 0.9-1.0 | 85 | +0.0136 ±0.0302 | +0.0012 ±0.0077 | +0.4 | 0.941 | 0.929 | |
| surface: Hard | 454 | -0.0122 ±0.0083 | -0.0051 ±0.0034 | -1.5 | 0.685 | 0.685 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 348 | -0.0066 ±0.0118 | -0.0036 ±0.0049 | -0.6 | 0.601 | 0.612 | |
| tier: atp500 | 221 | -0.0096 ±0.0099 | -0.0049 ±0.0045 | -1.0 | 0.620 | 0.631 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| round early (R128-R64) | 549 | -0.0098 ±0.0086 | -0.0045 ±0.0034 | -1.1 | 0.724 | 0.731 | |
| round late (QF-F) | 150 | +0.0006 ±0.0116 | -0.0007 ±0.0051 | +0.1 | 0.647 | 0.633 | |
| round mid (R32-R16) | 583 | -0.0036 ±0.0081 | -0.0026 ±0.0034 | -0.4 | 0.630 | 0.645 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 164 | -0.0177 ±0.0123 | -0.0092 ±0.0050 | -1.4 | 0.780 | 0.796 | |
| agree (<0.05) | 704 | +0.0002 ±0.0027 | -0.0006 ±0.0009 | +0.1 | 0.713 | 0.710 | |
| mild disagree (0.05-0.10) | 392 | -0.0101 ±0.0093 | -0.0050 ±0.0035 | -1.1 | 0.621 | 0.653 | |
| big disagree (>=0.1) | 208 | -0.0177 ±0.0270 | -0.0086 ±0.0115 | -0.7 | 0.613 | 0.620 | |
| tour: atp | 628 | -0.0002 ±0.0073 | -0.0012 ±0.0029 | -0.0 | 0.650 | 0.665 | |
| tour: wta | 676 | -0.0109 ±0.0077 | -0.0050 ±0.0032 | -1.4 | 0.688 | 0.691 | |

When they disagree by >= 0.1: model closer to the outcome in **88/208** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 14 | 0.067 | 0.143 |
| 0.1-0.2 | 81 | 0.153 | 0.136 |
| 0.2-0.3 | 116 | 0.254 | 0.250 |
| 0.3-0.4 | 165 | 0.354 | 0.345 |
| 0.4-0.5 | 226 | 0.451 | 0.469 |
| 0.5-0.6 | 207 | 0.551 | 0.541 |
| 0.6-0.7 | 191 | 0.647 | 0.623 |
| 0.7-0.8 | 157 | 0.751 | 0.764 |
| 0.8-0.9 | 100 | 0.847 | 0.810 |
| 0.9-1.0 | 47 | 0.933 | 0.936 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 31 | 0.060 | 0.097 |
| 0.1-0.2 | 75 | 0.153 | 0.133 |
| 0.2-0.3 | 134 | 0.256 | 0.269 |
| 0.3-0.4 | 160 | 0.355 | 0.375 |
| 0.4-0.5 | 191 | 0.444 | 0.445 |
| 0.5-0.6 | 184 | 0.555 | 0.516 |
| 0.6-0.7 | 194 | 0.648 | 0.634 |
| 0.7-0.8 | 172 | 0.749 | 0.750 |
| 0.8-0.9 | 110 | 0.846 | 0.818 |
| 0.9-1.0 | 53 | 0.932 | 0.943 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 283 | +0.0217 ±0.0101 | +0.0055 ±0.0030 | +2.1 | 0.746 | 0.739 | |
| top-20 involved | 469 | +0.0081 ±0.0075 | +0.0013 ±0.0025 | +1.1 | 0.735 | 0.732 | |
| kalshi favorite 0.8-0.9 | 184 | +0.0157 ±0.0168 | +0.0050 ±0.0059 | +0.9 | 0.842 | 0.837 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| kalshi favorite 0.9-1.0 | 85 | +0.0136 ±0.0302 | +0.0012 ±0.0077 | +0.4 | 0.941 | 0.929 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 923 | +0.0007 ±0.0067 | -0.0008 ±0.0027 | +0.1 | 0.659 | 0.667 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| someone outside top-50 | 991 | -0.0074 ±0.0064 | -0.0039 ±0.0026 | -1.2 | 0.672 | 0.685 | |
| tour: wta | 676 | -0.0109 ±0.0077 | -0.0050 ±0.0032 | -1.4 | 0.688 | 0.691 | |
| month 2026-09 | 164 | -0.0177 ±0.0123 | -0.0092 ±0.0050 | -1.4 | 0.780 | 0.796 | |
| surface: Hard | 454 | -0.0122 ±0.0083 | -0.0051 ±0.0034 | -1.5 | 0.685 | 0.685 | |
| no top-20 player | 835 | -0.0135 ±0.0071 | -0.0057 ±0.0031 | -1.9 | 0.633 | 0.648 | |
| best rank 21-50 | 452 | -0.0167 ±0.0081 | -0.0069 ±0.0036 | -2.1 | 0.655 | 0.687 | |
| pred_source: live aligned | 381 | -0.0215 ±0.0084 | -0.0090 ±0.0035 | -2.6 | 0.696 | 0.706 | |
| kalshi favorite 0.5-0.6 | 372 | -0.0265 ±0.0095 | -0.0123 ±0.0044 | -2.8 | 0.501 | 0.542 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1304, mean |Δ|=0.0017, p95=0.0086, >0.05 in 2 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0065 (n=164, >0.05: 0)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1304, d_ll -0.0058 ±0.0053 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 536 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Cincinnati': 1, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): Akasha Urhobo, Aleksandr Shevchenko, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari, Carson Branstine
