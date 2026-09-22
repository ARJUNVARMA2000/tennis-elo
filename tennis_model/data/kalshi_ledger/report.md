# Model vs Kalshi — match-by-match scorecard

_Generated 2026-09-22T17:06:50Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1841 | 1734 | 40 | 10 | 57 | 0 | 11 | 19 | 51 | 2026-05-03..2026-09-23 |
| wta | 1943 | 1175 | 37 | 679 | 52 | 0 | 8 | 15 | 31 | 2026-05-02..2026-09-23 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1341 | 0.5968 | 0.5897 | -0.0071 ±0.0052 | -0.0036 ±0.0021 | 0.670 | 0.679 |
| atp | 628 | 0.6198 | 0.6196 | -0.0002 ±0.0073 | -0.0012 ±0.0029 | 0.650 | 0.665 |
| wta | 713 | 0.5766 | 0.5634 | -0.0132 ±0.0075 | -0.0058 ±0.0031 | 0.687 | 0.691 |
| pooled/live_aligned | 418 | 0.5751 | 0.5507 | -0.0244 ±0.0081 | -0.0099 ±0.0034 | 0.694 | 0.706 |
| pooled/backtest | 923 | 0.6067 | 0.6074 | +0.0007 ±0.0067 | -0.0008 ±0.0027 | 0.659 | 0.667 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 418 | -0.0244 ±0.0081 | -0.0099 ±0.0034 | -3.0 | 0.694 | 0.706 | |
| pred_source: backtest | 923 | +0.0007 ±0.0067 | -0.0008 ±0.0027 | +0.1 | 0.659 | 0.667 | |
| top-20 involved | 473 | +0.0076 ±0.0075 | +0.0012 ±0.0025 | +1.0 | 0.735 | 0.733 | |
| no top-20 player | 868 | -0.0151 ±0.0070 | -0.0062 ±0.0030 | -2.2 | 0.634 | 0.650 | |
| both inside top-50 | 320 | -0.0037 ±0.0090 | -0.0022 ±0.0039 | -0.4 | 0.661 | 0.655 | |
| someone outside top-50 | 1021 | -0.0082 ±0.0063 | -0.0041 ±0.0025 | -1.3 | 0.672 | 0.687 | |
| best rank 1-10 | 284 | +0.0211 ±0.0101 | +0.0053 ±0.0030 | +2.1 | 0.743 | 0.736 | |
| best rank 11-20 | 189 | -0.0127 ±0.0109 | -0.0050 ±0.0041 | -1.2 | 0.722 | 0.728 | |
| best rank 21-50 | 462 | -0.0176 ±0.0080 | -0.0072 ±0.0035 | -2.2 | 0.658 | 0.689 | |
| best rank 51-100 | 327 | -0.0103 ±0.0123 | -0.0044 ±0.0052 | -0.8 | 0.610 | 0.606 | |
| best rank 100+ | 79 | -0.0203 ±0.0338 | -0.0079 ±0.0146 | -0.6 | 0.595 | 0.601 | |
| kalshi favorite 0.5-0.6 | 381 | -0.0267 ±0.0093 | -0.0124 ±0.0043 | -2.9 | 0.500 | 0.545 | |
| kalshi favorite 0.6-0.7 | 370 | -0.0033 ±0.0094 | -0.0011 ±0.0043 | -0.3 | 0.630 | 0.624 | |
| kalshi favorite 0.7-0.8 | 314 | -0.0028 ±0.0089 | -0.0011 ±0.0036 | -0.3 | 0.744 | 0.742 | |
| kalshi favorite 0.8-0.9 | 186 | +0.0160 ±0.0166 | +0.0050 ±0.0058 | +1.0 | 0.839 | 0.833 | |
| kalshi favorite 0.9-1.0 | 90 | -0.0029 ±0.0299 | -0.0038 ±0.0079 | -0.1 | 0.944 | 0.933 | |
| surface: Hard | 491 | -0.0154 ±0.0080 | -0.0062 ±0.0033 | -1.9 | 0.684 | 0.686 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 369 | -0.0107 ±0.0113 | -0.0051 ±0.0047 | -0.9 | 0.602 | 0.615 | |
| tier: atp500 | 237 | -0.0106 ±0.0099 | -0.0050 ±0.0045 | -1.1 | 0.629 | 0.639 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| round early (R128-R64) | 549 | -0.0098 ±0.0086 | -0.0045 ±0.0034 | -1.1 | 0.724 | 0.731 | |
| round late (QF-F) | 164 | -0.0034 ±0.0108 | -0.0025 ±0.0047 | -0.3 | 0.640 | 0.634 | |
| round mid (R32-R16) | 606 | -0.0057 ±0.0080 | -0.0032 ±0.0033 | -0.7 | 0.634 | 0.649 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 201 | -0.0246 ±0.0115 | -0.0111 ±0.0047 | -2.1 | 0.761 | 0.779 | |
| agree (<0.05) | 725 | -0.0004 ±0.0026 | -0.0008 ±0.0009 | -0.2 | 0.709 | 0.706 | |
| mild disagree (0.05-0.10) | 402 | -0.0120 ±0.0091 | -0.0058 ±0.0034 | -1.3 | 0.623 | 0.659 | |
| big disagree (>=0.1) | 214 | -0.0207 ±0.0266 | -0.0091 ±0.0114 | -0.8 | 0.624 | 0.626 | |
| tour: atp | 628 | -0.0002 ±0.0073 | -0.0012 ±0.0029 | -0.0 | 0.650 | 0.665 | |
| tour: wta | 713 | -0.0132 ±0.0075 | -0.0058 ±0.0031 | -1.8 | 0.687 | 0.691 | |

When they disagree by >= 0.1: model closer to the outcome in **90/214** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 14 | 0.067 | 0.143 |
| 0.1-0.2 | 85 | 0.153 | 0.129 |
| 0.2-0.3 | 122 | 0.253 | 0.270 |
| 0.3-0.4 | 169 | 0.354 | 0.343 |
| 0.4-0.5 | 233 | 0.451 | 0.472 |
| 0.5-0.6 | 212 | 0.552 | 0.547 |
| 0.6-0.7 | 198 | 0.647 | 0.626 |
| 0.7-0.8 | 159 | 0.751 | 0.767 |
| 0.8-0.9 | 102 | 0.847 | 0.814 |
| 0.9-1.0 | 47 | 0.933 | 0.936 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 34 | 0.061 | 0.088 |
| 0.1-0.2 | 77 | 0.153 | 0.143 |
| 0.2-0.3 | 138 | 0.255 | 0.275 |
| 0.3-0.4 | 166 | 0.355 | 0.373 |
| 0.4-0.5 | 194 | 0.444 | 0.448 |
| 0.5-0.6 | 190 | 0.555 | 0.526 |
| 0.6-0.7 | 201 | 0.648 | 0.632 |
| 0.7-0.8 | 176 | 0.749 | 0.756 |
| 0.8-0.9 | 110 | 0.846 | 0.818 |
| 0.9-1.0 | 55 | 0.934 | 0.945 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 284 | +0.0211 ±0.0101 | +0.0053 ±0.0030 | +2.1 | 0.743 | 0.736 | |
| top-20 involved | 473 | +0.0076 ±0.0075 | +0.0012 ±0.0025 | +1.0 | 0.735 | 0.733 | |
| kalshi favorite 0.8-0.9 | 186 | +0.0160 ±0.0166 | +0.0050 ±0.0058 | +1.0 | 0.839 | 0.833 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 923 | +0.0007 ±0.0067 | -0.0008 ±0.0027 | +0.1 | 0.659 | 0.667 | |
| tour: atp | 628 | -0.0002 ±0.0073 | -0.0012 ±0.0029 | -0.0 | 0.650 | 0.665 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| mild disagree (0.05-0.10) | 402 | -0.0120 ±0.0091 | -0.0058 ±0.0034 | -1.3 | 0.623 | 0.659 | |
| tour: wta | 713 | -0.0132 ±0.0075 | -0.0058 ±0.0031 | -1.8 | 0.687 | 0.691 | |
| surface: Hard | 491 | -0.0154 ±0.0080 | -0.0062 ±0.0033 | -1.9 | 0.684 | 0.686 | |
| month 2026-09 | 201 | -0.0246 ±0.0115 | -0.0111 ±0.0047 | -2.1 | 0.761 | 0.779 | |
| no top-20 player | 868 | -0.0151 ±0.0070 | -0.0062 ±0.0030 | -2.2 | 0.634 | 0.650 | |
| best rank 21-50 | 462 | -0.0176 ±0.0080 | -0.0072 ±0.0035 | -2.2 | 0.658 | 0.689 | |
| kalshi favorite 0.5-0.6 | 381 | -0.0267 ±0.0093 | -0.0124 ±0.0043 | -2.9 | 0.500 | 0.545 | |
| pred_source: live aligned | 418 | -0.0244 ±0.0081 | -0.0099 ±0.0034 | -3.0 | 0.694 | 0.706 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1341, mean |Δ|=0.0025, p95=0.0091, >0.05 in 9 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0099 (n=201, >0.05: 7)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1341, d_ll -0.0071 ±0.0052 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 536 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Cincinnati': 1, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): Akasha Urhobo, Aleksandr Shevchenko, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari, Carson Branstine
