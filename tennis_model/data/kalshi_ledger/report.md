# Model vs Kalshi — match-by-match scorecard

_Generated 2026-10-04T22:59:17Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1991 | 1886 | 30 | 14 | 61 | 0 | 11 | 19 | 71 | 2026-05-03..2026-10-05 |
| wta | 2094 | 1287 | 8 | 743 | 56 | 0 | 10 | 15 | 34 | 2026-05-02..2026-10-05 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1496 | 0.6014 | 0.5879 | -0.0135 ±0.0052 | -0.0060 ±0.0021 | 0.664 | 0.678 |
| atp | 711 | 0.6176 | 0.6118 | -0.0058 ±0.0073 | -0.0032 ±0.0029 | 0.648 | 0.665 |
| wta | 785 | 0.5867 | 0.5663 | -0.0204 ±0.0073 | -0.0086 ±0.0030 | 0.679 | 0.689 |
| pooled/live_aligned | 565 | 0.5927 | 0.5554 | -0.0374 ±0.0082 | -0.0150 ±0.0034 | 0.676 | 0.698 |
| pooled/backtest | 931 | 0.6066 | 0.6076 | +0.0010 ±0.0066 | -0.0006 ±0.0027 | 0.657 | 0.665 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 565 | -0.0374 ±0.0082 | -0.0150 ±0.0034 | -4.6 | 0.676 | 0.698 | |
| pred_source: backtest | 931 | +0.0010 ±0.0066 | -0.0006 ±0.0027 | +0.2 | 0.657 | 0.665 | |
| top-20 involved | 518 | +0.0026 ±0.0080 | -0.0007 ±0.0029 | +0.3 | 0.727 | 0.729 | |
| no top-20 player | 978 | -0.0220 ±0.0067 | -0.0088 ±0.0029 | -3.3 | 0.631 | 0.651 | |
| both inside top-50 | 359 | -0.0119 ±0.0101 | -0.0054 ±0.0043 | -1.2 | 0.656 | 0.659 | |
| someone outside top-50 | 1137 | -0.0140 ±0.0060 | -0.0062 ±0.0024 | -2.3 | 0.667 | 0.684 | |
| best rank 1-10 | 309 | +0.0203 ±0.0095 | +0.0054 ±0.0029 | +2.1 | 0.744 | 0.738 | |
| best rank 11-20 | 209 | -0.0236 ±0.0139 | -0.0098 ±0.0056 | -1.7 | 0.701 | 0.715 | |
| best rank 21-50 | 517 | -0.0258 ±0.0080 | -0.0107 ±0.0035 | -3.2 | 0.656 | 0.697 | |
| best rank 51-100 | 373 | -0.0135 ±0.0112 | -0.0053 ±0.0047 | -1.2 | 0.605 | 0.597 | |
| best rank 100+ | 88 | -0.0357 ±0.0320 | -0.0128 ±0.0136 | -1.1 | 0.602 | 0.608 | |
| kalshi favorite 0.5-0.6 | 428 | -0.0269 ±0.0088 | -0.0124 ±0.0041 | -3.1 | 0.496 | 0.537 | |
| kalshi favorite 0.6-0.7 | 416 | -0.0089 ±0.0092 | -0.0035 ±0.0042 | -1.0 | 0.618 | 0.620 | |
| kalshi favorite 0.7-0.8 | 342 | -0.0049 ±0.0088 | -0.0020 ±0.0036 | -0.6 | 0.747 | 0.749 | |
| kalshi favorite 0.8-0.9 | 206 | +0.0081 ±0.0156 | +0.0020 ±0.0055 | +0.5 | 0.840 | 0.840 | |
| kalshi favorite 0.9-1.0 | 104 | -0.0478 ±0.0323 | -0.0192 ±0.0101 | -1.5 | 0.923 | 0.933 | |
| surface: Hard | 646 | -0.0282 ±0.0079 | -0.0111 ±0.0033 | -3.6 | 0.669 | 0.682 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 463 | -0.0192 ±0.0106 | -0.0082 ±0.0044 | -1.8 | 0.605 | 0.623 | |
| tier: atp500 | 250 | -0.0149 ±0.0103 | -0.0067 ±0.0046 | -1.4 | 0.628 | 0.642 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 272 | -0.0109 ±0.0101 | -0.0034 ±0.0044 | -1.1 | 0.671 | 0.680 | |
| round early (R128-R64) | 593 | -0.0164 ±0.0084 | -0.0071 ±0.0033 | -2.0 | 0.714 | 0.726 | |
| round late (QF-F) | 194 | -0.0082 ±0.0116 | -0.0044 ±0.0051 | -0.7 | 0.634 | 0.644 | |
| round mid (R32-R16) | 687 | -0.0127 ±0.0079 | -0.0057 ±0.0033 | -1.6 | 0.635 | 0.650 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 320 | -0.0473 ±0.0116 | -0.0195 ±0.0048 | -4.1 | 0.700 | 0.731 | |
| month 2026-10 | 36 | -0.0125 ±0.0339 | -0.0040 ±0.0148 | -0.4 | 0.694 | 0.722 | ⚠ small n |
| agree (<0.05) | 810 | -0.0003 ±0.0025 | -0.0007 ±0.0009 | -0.1 | 0.707 | 0.706 | |
| mild disagree (0.05-0.10) | 444 | -0.0089 ±0.0086 | -0.0039 ±0.0033 | -1.0 | 0.627 | 0.652 | |
| big disagree (>=0.1) | 242 | -0.0659 ±0.0263 | -0.0277 ±0.0112 | -2.5 | 0.589 | 0.632 | |
| tour: atp | 711 | -0.0058 ±0.0073 | -0.0032 ±0.0029 | -0.8 | 0.648 | 0.665 | |
| tour: wta | 785 | -0.0204 ±0.0073 | -0.0086 ±0.0030 | -2.8 | 0.679 | 0.689 | |

When they disagree by >= 0.1: model closer to the outcome in **93/242** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 17 | 0.066 | 0.176 |
| 0.1-0.2 | 92 | 0.153 | 0.141 |
| 0.2-0.3 | 132 | 0.251 | 0.265 |
| 0.3-0.4 | 192 | 0.353 | 0.359 |
| 0.4-0.5 | 258 | 0.452 | 0.473 |
| 0.5-0.6 | 235 | 0.552 | 0.540 |
| 0.6-0.7 | 220 | 0.647 | 0.618 |
| 0.7-0.8 | 187 | 0.751 | 0.770 |
| 0.8-0.9 | 114 | 0.846 | 0.807 |
| 0.9-1.0 | 49 | 0.933 | 0.939 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 41 | 0.057 | 0.098 |
| 0.1-0.2 | 82 | 0.153 | 0.146 |
| 0.2-0.3 | 151 | 0.254 | 0.265 |
| 0.3-0.4 | 185 | 0.355 | 0.378 |
| 0.4-0.5 | 220 | 0.444 | 0.455 |
| 0.5-0.6 | 212 | 0.555 | 0.524 |
| 0.6-0.7 | 227 | 0.650 | 0.626 |
| 0.7-0.8 | 191 | 0.749 | 0.759 |
| 0.8-0.9 | 125 | 0.846 | 0.832 |
| 0.9-1.0 | 62 | 0.934 | 0.952 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 309 | +0.0203 ±0.0095 | +0.0054 ±0.0029 | +2.1 | 0.744 | 0.738 | |
| kalshi favorite 0.8-0.9 | 206 | +0.0081 ±0.0156 | +0.0020 ±0.0055 | +0.5 | 0.840 | 0.840 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| top-20 involved | 518 | +0.0026 ±0.0080 | -0.0007 ±0.0029 | +0.3 | 0.727 | 0.729 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 931 | +0.0010 ±0.0066 | -0.0006 ±0.0027 | +0.2 | 0.657 | 0.665 | |
| agree (<0.05) | 810 | -0.0003 ±0.0025 | -0.0007 ±0.0009 | -0.1 | 0.707 | 0.706 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| big disagree (>=0.1) | 242 | -0.0659 ±0.0263 | -0.0277 ±0.0112 | -2.5 | 0.589 | 0.632 | |
| tour: wta | 785 | -0.0204 ±0.0073 | -0.0086 ±0.0030 | -2.8 | 0.679 | 0.689 | |
| kalshi favorite 0.5-0.6 | 428 | -0.0269 ±0.0088 | -0.0124 ±0.0041 | -3.1 | 0.496 | 0.537 | |
| best rank 21-50 | 517 | -0.0258 ±0.0080 | -0.0107 ±0.0035 | -3.2 | 0.656 | 0.697 | |
| no top-20 player | 978 | -0.0220 ±0.0067 | -0.0088 ±0.0029 | -3.3 | 0.631 | 0.651 | |
| surface: Hard | 646 | -0.0282 ±0.0079 | -0.0111 ±0.0033 | -3.6 | 0.669 | 0.682 | |
| month 2026-09 | 320 | -0.0473 ±0.0116 | -0.0195 ±0.0048 | -4.1 | 0.700 | 0.731 | |
| pred_source: live aligned | 565 | -0.0374 ±0.0082 | -0.0150 ±0.0034 | -4.6 | 0.676 | 0.698 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1496, mean |Δ|=0.0041, p95=0.0100, >0.05 in 23 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0602 (n=320, >0.05: 18) | 2026-10 p95=0.0992 (n=36, >0.05: 3)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1496, d_ll -0.0135 ±0.0052 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 597 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'WTA Seoul': 3, 'ATP Beijing': 2}
- Unmatched Kalshi names, main draw (40): Akasha Urhobo, Aleksandr Shevchenko, Alevtina Ibragimova, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari
