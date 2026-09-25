# Model vs Kalshi — match-by-match scorecard

_Generated 2026-09-25T07:03:29Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1866 | 1777 | 21 | 10 | 58 | 0 | 11 | 19 | 56 | 2026-05-03..2026-09-26 |
| wta | 1962 | 1190 | 17 | 703 | 52 | 0 | 9 | 15 | 21 | 2026-05-02..2026-09-25 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1369 | 0.5956 | 0.5881 | -0.0075 ±0.0052 | -0.0037 ±0.0021 | 0.671 | 0.679 |
| atp | 645 | 0.6189 | 0.6177 | -0.0011 ±0.0072 | -0.0015 ±0.0029 | 0.651 | 0.665 |
| wta | 724 | 0.5749 | 0.5616 | -0.0132 ±0.0074 | -0.0057 ±0.0031 | 0.689 | 0.692 |
| pooled/live_aligned | 446 | 0.5726 | 0.5480 | -0.0246 ±0.0079 | -0.0097 ±0.0033 | 0.697 | 0.705 |
| pooled/backtest | 923 | 0.6067 | 0.6074 | +0.0007 ±0.0067 | -0.0008 ±0.0027 | 0.659 | 0.667 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 446 | -0.0246 ±0.0079 | -0.0097 ±0.0033 | -3.1 | 0.697 | 0.705 | |
| pred_source: backtest | 923 | +0.0007 ±0.0067 | -0.0008 ±0.0027 | +0.1 | 0.659 | 0.667 | |
| top-20 involved | 475 | +0.0081 ±0.0075 | +0.0013 ±0.0025 | +1.1 | 0.734 | 0.732 | |
| no top-20 player | 894 | -0.0158 ±0.0069 | -0.0064 ±0.0030 | -2.3 | 0.638 | 0.652 | |
| both inside top-50 | 321 | -0.0051 ±0.0091 | -0.0027 ±0.0039 | -0.6 | 0.662 | 0.656 | |
| someone outside top-50 | 1048 | -0.0083 ±0.0062 | -0.0040 ±0.0025 | -1.3 | 0.674 | 0.687 | |
| best rank 1-10 | 285 | +0.0211 ±0.0101 | +0.0053 ±0.0030 | +2.1 | 0.744 | 0.737 | |
| best rank 11-20 | 190 | -0.0114 ±0.0109 | -0.0046 ±0.0041 | -1.0 | 0.718 | 0.724 | |
| best rank 21-50 | 468 | -0.0181 ±0.0080 | -0.0073 ±0.0035 | -2.3 | 0.660 | 0.691 | |
| best rank 51-100 | 344 | -0.0099 ±0.0118 | -0.0041 ±0.0050 | -0.8 | 0.618 | 0.609 | |
| best rank 100+ | 82 | -0.0275 ±0.0332 | -0.0105 ±0.0143 | -0.8 | 0.598 | 0.604 | |
| kalshi favorite 0.5-0.6 | 393 | -0.0257 ±0.0091 | -0.0119 ±0.0043 | -2.8 | 0.503 | 0.542 | |
| kalshi favorite 0.6-0.7 | 372 | -0.0033 ±0.0093 | -0.0011 ±0.0042 | -0.4 | 0.632 | 0.626 | |
| kalshi favorite 0.7-0.8 | 319 | -0.0022 ±0.0088 | -0.0008 ±0.0035 | -0.2 | 0.745 | 0.743 | |
| kalshi favorite 0.8-0.9 | 191 | +0.0165 ±0.0163 | +0.0052 ±0.0057 | +1.0 | 0.838 | 0.832 | |
| kalshi favorite 0.9-1.0 | 94 | -0.0154 ±0.0297 | -0.0077 ±0.0080 | -0.5 | 0.947 | 0.936 | |
| surface: Hard | 519 | -0.0160 ±0.0078 | -0.0062 ±0.0032 | -2.0 | 0.688 | 0.687 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 390 | -0.0110 ±0.0109 | -0.0050 ±0.0045 | -1.0 | 0.608 | 0.617 | |
| tier: atp500 | 244 | -0.0120 ±0.0099 | -0.0054 ±0.0044 | -1.2 | 0.635 | 0.645 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| round early (R128-R64) | 549 | -0.0098 ±0.0086 | -0.0045 ±0.0034 | -1.1 | 0.724 | 0.731 | |
| round late (QF-F) | 164 | -0.0034 ±0.0108 | -0.0025 ±0.0047 | -0.3 | 0.640 | 0.634 | |
| round mid (R32-R16) | 634 | -0.0067 ±0.0078 | -0.0033 ±0.0032 | -0.9 | 0.640 | 0.651 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 229 | -0.0249 ±0.0109 | -0.0106 ±0.0045 | -2.3 | 0.760 | 0.769 | |
| agree (<0.05) | 738 | -0.0004 ±0.0026 | -0.0009 ±0.0009 | -0.2 | 0.711 | 0.708 | |
| mild disagree (0.05-0.10) | 413 | -0.0097 ±0.0090 | -0.0045 ±0.0034 | -1.1 | 0.626 | 0.655 | |
| big disagree (>=0.1) | 218 | -0.0274 ±0.0264 | -0.0116 ±0.0112 | -1.0 | 0.622 | 0.628 | |
| tour: atp | 645 | -0.0011 ±0.0072 | -0.0015 ±0.0029 | -0.2 | 0.651 | 0.665 | |
| tour: wta | 724 | -0.0132 ±0.0074 | -0.0057 ±0.0031 | -1.8 | 0.689 | 0.692 | |

When they disagree by >= 0.1: model closer to the outcome in **90/218** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 15 | 0.066 | 0.133 |
| 0.1-0.2 | 86 | 0.153 | 0.128 |
| 0.2-0.3 | 124 | 0.252 | 0.266 |
| 0.3-0.4 | 172 | 0.354 | 0.337 |
| 0.4-0.5 | 241 | 0.452 | 0.469 |
| 0.5-0.6 | 216 | 0.552 | 0.551 |
| 0.6-0.7 | 201 | 0.647 | 0.627 |
| 0.7-0.8 | 163 | 0.751 | 0.761 |
| 0.8-0.9 | 104 | 0.847 | 0.817 |
| 0.9-1.0 | 47 | 0.933 | 0.936 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 36 | 0.060 | 0.083 |
| 0.1-0.2 | 79 | 0.153 | 0.139 |
| 0.2-0.3 | 141 | 0.255 | 0.270 |
| 0.3-0.4 | 167 | 0.355 | 0.371 |
| 0.4-0.5 | 198 | 0.445 | 0.449 |
| 0.5-0.6 | 198 | 0.555 | 0.525 |
| 0.6-0.7 | 202 | 0.648 | 0.634 |
| 0.7-0.8 | 178 | 0.749 | 0.753 |
| 0.8-0.9 | 113 | 0.846 | 0.814 |
| 0.9-1.0 | 57 | 0.934 | 0.947 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 285 | +0.0211 ±0.0101 | +0.0053 ±0.0030 | +2.1 | 0.744 | 0.737 | |
| top-20 involved | 475 | +0.0081 ±0.0075 | +0.0013 ±0.0025 | +1.1 | 0.734 | 0.732 | |
| kalshi favorite 0.8-0.9 | 191 | +0.0165 ±0.0163 | +0.0052 ±0.0057 | +1.0 | 0.838 | 0.832 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 923 | +0.0007 ±0.0067 | -0.0008 ±0.0027 | +0.1 | 0.659 | 0.667 | |
| tour: atp | 645 | -0.0011 ±0.0072 | -0.0015 ±0.0029 | -0.2 | 0.651 | 0.665 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| someone outside top-50 | 1048 | -0.0083 ±0.0062 | -0.0040 ±0.0025 | -1.3 | 0.674 | 0.687 | |
| tour: wta | 724 | -0.0132 ±0.0074 | -0.0057 ±0.0031 | -1.8 | 0.689 | 0.692 | |
| surface: Hard | 519 | -0.0160 ±0.0078 | -0.0062 ±0.0032 | -2.0 | 0.688 | 0.687 | |
| best rank 21-50 | 468 | -0.0181 ±0.0080 | -0.0073 ±0.0035 | -2.3 | 0.660 | 0.691 | |
| month 2026-09 | 229 | -0.0249 ±0.0109 | -0.0106 ±0.0045 | -2.3 | 0.760 | 0.769 | |
| no top-20 player | 894 | -0.0158 ±0.0069 | -0.0064 ±0.0030 | -2.3 | 0.638 | 0.652 | |
| kalshi favorite 0.5-0.6 | 393 | -0.0257 ±0.0091 | -0.0119 ±0.0043 | -2.8 | 0.503 | 0.542 | |
| pred_source: live aligned | 446 | -0.0246 ±0.0079 | -0.0097 ±0.0033 | -3.1 | 0.697 | 0.705 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1369, mean |Δ|=0.0027, p95=0.0099, >0.05 in 13 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0159 (n=229, >0.05: 11)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1369, d_ll -0.0075 ±0.0052 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 560 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Cincinnati': 1, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): Akasha Urhobo, Aleksandr Shevchenko, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari, Carson Branstine
