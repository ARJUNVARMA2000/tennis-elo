# Model vs Kalshi — match-by-match scorecard

_Generated 2026-11-13T10:11:25Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 2427 | 2333 | 5 | 16 | 73 | 0 | 18 | 31 | 51 | 2026-05-03..2026-11-13 |
| wta | 2554 | 1554 | 2 | 918 | 80 | 0 | 12 | 24 | 33 | 2026-05-02..2026-11-14 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1939 | 0.6131 | 0.5916 | -0.0215 ±0.0049 | -0.0086 ±0.0020 | 0.659 | 0.673 |
| atp | 980 | 0.6237 | 0.6122 | -0.0115 ±0.0066 | -0.0045 ±0.0026 | 0.645 | 0.661 |
| wta | 959 | 0.6024 | 0.5706 | -0.0318 ±0.0074 | -0.0128 ±0.0031 | 0.674 | 0.685 |
| pooled/live_aligned | 1001 | 0.6199 | 0.5786 | -0.0414 ±0.0072 | -0.0157 ±0.0029 | 0.659 | 0.678 |
| pooled/backtest | 938 | 0.6059 | 0.6056 | -0.0003 ±0.0066 | -0.0011 ±0.0027 | 0.659 | 0.667 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 1001 | -0.0414 ±0.0072 | -0.0157 ±0.0029 | -5.7 | 0.659 | 0.678 | |
| pred_source: backtest | 938 | -0.0003 ±0.0066 | -0.0011 ±0.0027 | -0.1 | 0.659 | 0.667 | |
| top-20 involved | 704 | -0.0009 ±0.0074 | -0.0008 ±0.0027 | -0.1 | 0.722 | 0.722 | |
| no top-20 player | 1235 | -0.0333 ±0.0065 | -0.0131 ±0.0028 | -5.1 | 0.623 | 0.645 | |
| both inside top-50 | 523 | -0.0174 ±0.0091 | -0.0064 ±0.0038 | -1.9 | 0.634 | 0.640 | |
| someone outside top-50 | 1416 | -0.0231 ±0.0059 | -0.0094 ±0.0024 | -3.9 | 0.668 | 0.685 | |
| best rank 1-10 | 409 | +0.0088 ±0.0096 | +0.0026 ±0.0032 | +0.9 | 0.733 | 0.729 | |
| best rank 11-20 | 295 | -0.0143 ±0.0116 | -0.0056 ±0.0045 | -1.2 | 0.707 | 0.714 | |
| best rank 21-50 | 653 | -0.0311 ±0.0079 | -0.0125 ±0.0034 | -3.9 | 0.648 | 0.686 | |
| best rank 51-100 | 466 | -0.0306 ±0.0113 | -0.0119 ±0.0047 | -2.7 | 0.598 | 0.602 | |
| best rank 100+ | 116 | -0.0566 ±0.0280 | -0.0209 ±0.0119 | -2.0 | 0.586 | 0.582 | |
| kalshi favorite 0.5-0.6 | 540 | -0.0248 ±0.0082 | -0.0114 ±0.0038 | -3.0 | 0.505 | 0.532 | |
| kalshi favorite 0.6-0.7 | 556 | -0.0128 ±0.0082 | -0.0051 ±0.0037 | -1.6 | 0.613 | 0.617 | |
| kalshi favorite 0.7-0.8 | 457 | -0.0150 ±0.0104 | -0.0054 ±0.0041 | -1.4 | 0.730 | 0.740 | |
| kalshi favorite 0.8-0.9 | 258 | -0.0090 ±0.0141 | -0.0037 ±0.0049 | -0.6 | 0.833 | 0.837 | |
| kalshi favorite 0.9-1.0 | 128 | -0.0940 ±0.0304 | -0.0336 ±0.0100 | -3.1 | 0.906 | 0.938 | |
| surface: Hard | 1089 | -0.0365 ±0.0070 | -0.0137 ±0.0028 | -5.2 | 0.657 | 0.671 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 816 | -0.0326 ±0.0084 | -0.0125 ±0.0034 | -3.9 | 0.619 | 0.636 | |
| tier: atp500 | 278 | -0.0183 ±0.0117 | -0.0074 ±0.0051 | -1.6 | 0.644 | 0.653 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 324 | -0.0171 ±0.0108 | -0.0058 ±0.0046 | -1.6 | 0.659 | 0.673 | |
| tier: tour_finals | 10 | +0.0074 ±0.0274 | +0.0037 ±0.0135 | +0.3 | 0.600 | 0.600 | ⚠ small n |
| round early (R128-R64) | 664 | -0.0206 ±0.0081 | -0.0084 ±0.0032 | -2.5 | 0.709 | 0.723 | |
| round late (QF-F) | 289 | -0.0090 ±0.0119 | -0.0039 ±0.0051 | -0.8 | 0.654 | 0.647 | |
| round mid (R32-R16) | 954 | -0.0267 ±0.0075 | -0.0105 ±0.0030 | -3.6 | 0.631 | 0.649 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| round round robin | 10 | +0.0074 ±0.0274 | +0.0037 ±0.0135 | +0.3 | 0.600 | 0.600 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 320 | -0.0429 ±0.0105 | -0.0177 ±0.0044 | -4.1 | 0.703 | 0.728 | |
| month 2026-10 | 346 | -0.0523 ±0.0162 | -0.0189 ±0.0065 | -3.2 | 0.639 | 0.669 | |
| month 2026-11 | 133 | -0.0399 ±0.0163 | -0.0141 ±0.0064 | -2.5 | 0.654 | 0.647 | |
| agree (<0.05) | 1010 | -0.0007 ±0.0023 | -0.0007 ±0.0008 | -0.3 | 0.697 | 0.695 | |
| mild disagree (0.05-0.10) | 582 | -0.0099 ±0.0073 | -0.0040 ±0.0028 | -1.3 | 0.642 | 0.655 | |
| big disagree (>=0.1) | 347 | -0.1018 ±0.0234 | -0.0395 ±0.0098 | -4.3 | 0.578 | 0.637 | |
| tour: atp | 980 | -0.0115 ±0.0066 | -0.0045 ±0.0026 | -1.7 | 0.645 | 0.661 | |
| tour: wta | 959 | -0.0318 ±0.0074 | -0.0128 ±0.0031 | -4.3 | 0.674 | 0.685 | |

When they disagree by >= 0.1: model closer to the outcome in **131/347** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 23 | 0.071 | 0.174 |
| 0.1-0.2 | 125 | 0.153 | 0.168 |
| 0.2-0.3 | 180 | 0.250 | 0.261 |
| 0.3-0.4 | 258 | 0.352 | 0.380 |
| 0.4-0.5 | 321 | 0.451 | 0.486 |
| 0.5-0.6 | 293 | 0.551 | 0.553 |
| 0.6-0.7 | 282 | 0.648 | 0.617 |
| 0.7-0.8 | 230 | 0.751 | 0.770 |
| 0.8-0.9 | 157 | 0.845 | 0.771 |
| 0.9-1.0 | 70 | 0.931 | 0.900 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 49 | 0.055 | 0.082 |
| 0.1-0.2 | 104 | 0.155 | 0.154 |
| 0.2-0.3 | 210 | 0.251 | 0.262 |
| 0.3-0.4 | 250 | 0.353 | 0.396 |
| 0.4-0.5 | 274 | 0.445 | 0.471 |
| 0.5-0.6 | 270 | 0.554 | 0.530 |
| 0.6-0.7 | 302 | 0.649 | 0.632 |
| 0.7-0.8 | 247 | 0.748 | 0.741 |
| 0.8-0.9 | 155 | 0.846 | 0.832 |
| 0.9-1.0 | 78 | 0.936 | 0.949 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 409 | +0.0088 ±0.0096 | +0.0026 ±0.0032 | +0.9 | 0.733 | 0.729 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| tier: tour_finals | 10 | +0.0074 ±0.0274 | +0.0037 ±0.0135 | +0.3 | 0.600 | 0.600 | ⚠ small n |
| round round robin | 10 | +0.0074 ±0.0274 | +0.0037 ±0.0135 | +0.3 | 0.600 | 0.600 | ⚠ small n |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 938 | -0.0003 ±0.0066 | -0.0011 ±0.0027 | -0.1 | 0.659 | 0.667 | |
| top-20 involved | 704 | -0.0009 ±0.0074 | -0.0008 ±0.0027 | -0.1 | 0.722 | 0.722 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| someone outside top-50 | 1416 | -0.0231 ±0.0059 | -0.0094 ±0.0024 | -3.9 | 0.668 | 0.685 | |
| best rank 21-50 | 653 | -0.0311 ±0.0079 | -0.0125 ±0.0034 | -3.9 | 0.648 | 0.686 | |
| month 2026-09 | 320 | -0.0429 ±0.0105 | -0.0177 ±0.0044 | -4.1 | 0.703 | 0.728 | |
| tour: wta | 959 | -0.0318 ±0.0074 | -0.0128 ±0.0031 | -4.3 | 0.674 | 0.685 | |
| big disagree (>=0.1) | 347 | -0.1018 ±0.0234 | -0.0395 ±0.0098 | -4.3 | 0.578 | 0.637 | |
| no top-20 player | 1235 | -0.0333 ±0.0065 | -0.0131 ±0.0028 | -5.1 | 0.623 | 0.645 | |
| surface: Hard | 1089 | -0.0365 ±0.0070 | -0.0137 ±0.0028 | -5.2 | 0.657 | 0.671 | |
| pred_source: live aligned | 1001 | -0.0414 ±0.0072 | -0.0157 ±0.0029 | -5.7 | 0.659 | 0.678 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1939, mean |Δ|=0.0068, p95=0.0128, >0.05 in 55 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0660 (n=320, >0.05: 19) | 2026-10 p95=0.1324 (n=346, >0.05: 29) | 2026-11 p95=0.0187 (n=133, >0.05: 5)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1953, d_ll -0.0215 ±0.0049
- Unmatched qualifying markets: 720 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'Billie Jean King Cup Qualifiers Round': 56, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): AYNUR MOVLYAMOVA, Aishath Karin Saizan, Akasha Urhobo, Aleksandr Shevchenko, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Abualhaj, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Aylara Kakabayeva, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao
