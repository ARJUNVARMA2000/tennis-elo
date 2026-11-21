# Model vs Kalshi — match-by-match scorecard

_Generated 2026-11-21T11:50:42Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 2442 | 2348 | 2 | 19 | 73 | 0 | 18 | 31 | 51 | 2026-05-03..2026-11-21 |
| wta | 2578 | 1559 | 19 | 918 | 82 | 0 | 12 | 24 | 43 | 2026-05-02..2026-11-21 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1958 | 0.6118 | 0.5904 | -0.0214 ±0.0049 | -0.0085 ±0.0020 | 0.661 | 0.674 |
| atp | 995 | 0.6205 | 0.6093 | -0.0112 ±0.0065 | -0.0044 ±0.0026 | 0.649 | 0.664 |
| wta | 963 | 0.6028 | 0.5709 | -0.0319 ±0.0074 | -0.0128 ±0.0031 | 0.673 | 0.684 |
| pooled/live_aligned | 1020 | 0.6173 | 0.5766 | -0.0407 ±0.0071 | -0.0154 ±0.0029 | 0.663 | 0.680 |
| pooled/backtest | 938 | 0.6059 | 0.6056 | -0.0003 ±0.0066 | -0.0011 ±0.0027 | 0.659 | 0.667 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 1020 | -0.0407 ±0.0071 | -0.0154 ±0.0029 | -5.7 | 0.663 | 0.680 | |
| pred_source: backtest | 938 | -0.0003 ±0.0066 | -0.0011 ±0.0027 | -0.1 | 0.659 | 0.667 | |
| top-20 involved | 722 | -0.0013 ±0.0073 | -0.0009 ±0.0026 | -0.2 | 0.726 | 0.725 | |
| no top-20 player | 1236 | -0.0331 ±0.0065 | -0.0130 ±0.0028 | -5.1 | 0.623 | 0.644 | |
| both inside top-50 | 542 | -0.0170 ±0.0088 | -0.0062 ±0.0037 | -1.9 | 0.641 | 0.645 | |
| someone outside top-50 | 1416 | -0.0231 ±0.0059 | -0.0094 ±0.0024 | -3.9 | 0.668 | 0.685 | |
| best rank 1-10 | 427 | +0.0078 ±0.0093 | +0.0022 ±0.0031 | +0.8 | 0.740 | 0.733 | |
| best rank 11-20 | 295 | -0.0143 ±0.0116 | -0.0056 ±0.0045 | -1.2 | 0.707 | 0.714 | |
| best rank 21-50 | 654 | -0.0308 ±0.0079 | -0.0124 ±0.0034 | -3.9 | 0.647 | 0.685 | |
| best rank 51-100 | 466 | -0.0306 ±0.0113 | -0.0119 ±0.0047 | -2.7 | 0.598 | 0.602 | |
| best rank 100+ | 116 | -0.0566 ±0.0280 | -0.0209 ±0.0119 | -2.0 | 0.586 | 0.582 | |
| kalshi favorite 0.5-0.6 | 545 | -0.0232 ±0.0082 | -0.0106 ±0.0038 | -2.8 | 0.507 | 0.533 | |
| kalshi favorite 0.6-0.7 | 561 | -0.0132 ±0.0082 | -0.0053 ±0.0036 | -1.6 | 0.613 | 0.617 | |
| kalshi favorite 0.7-0.8 | 463 | -0.0160 ±0.0103 | -0.0058 ±0.0041 | -1.6 | 0.733 | 0.743 | |
| kalshi favorite 0.8-0.9 | 260 | -0.0090 ±0.0140 | -0.0037 ±0.0048 | -0.6 | 0.835 | 0.838 | |
| kalshi favorite 0.9-1.0 | 129 | -0.0932 ±0.0302 | -0.0333 ±0.0099 | -3.1 | 0.907 | 0.938 | |
| surface: Hard | 1108 | -0.0360 ±0.0069 | -0.0135 ±0.0028 | -5.2 | 0.661 | 0.673 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 831 | -0.0319 ±0.0083 | -0.0122 ±0.0034 | -3.8 | 0.625 | 0.640 | |
| tier: atp500 | 278 | -0.0183 ±0.0117 | -0.0074 ±0.0051 | -1.6 | 0.644 | 0.653 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 324 | -0.0171 ±0.0108 | -0.0058 ±0.0046 | -1.6 | 0.659 | 0.673 | |
| tier: tour_finals | 14 | -0.0089 ±0.0277 | -0.0030 ±0.0132 | -0.3 | 0.571 | 0.571 | ⚠ small n |
| round early (R128-R64) | 664 | -0.0206 ±0.0081 | -0.0084 ±0.0032 | -2.5 | 0.709 | 0.723 | |
| round late (QF-F) | 295 | -0.0084 ±0.0117 | -0.0035 ±0.0050 | -0.7 | 0.654 | 0.647 | |
| round mid (R32-R16) | 954 | -0.0267 ±0.0075 | -0.0105 ±0.0030 | -3.6 | 0.631 | 0.649 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| round round robin | 23 | -0.0072 ±0.0257 | -0.0029 ±0.0121 | -0.3 | 0.783 | 0.739 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 320 | -0.0429 ±0.0105 | -0.0177 ±0.0044 | -4.1 | 0.703 | 0.728 | |
| month 2026-10 | 346 | -0.0523 ±0.0162 | -0.0189 ±0.0065 | -3.2 | 0.639 | 0.669 | |
| month 2026-11 | 152 | -0.0356 ±0.0148 | -0.0125 ±0.0059 | -2.4 | 0.678 | 0.664 | |
| agree (<0.05) | 1020 | -0.0008 ±0.0023 | -0.0007 ±0.0008 | -0.3 | 0.699 | 0.697 | |
| mild disagree (0.05-0.10) | 587 | -0.0094 ±0.0073 | -0.0038 ±0.0028 | -1.3 | 0.641 | 0.653 | |
| big disagree (>=0.1) | 351 | -0.1012 ±0.0232 | -0.0393 ±0.0097 | -4.4 | 0.583 | 0.641 | |
| tour: atp | 995 | -0.0112 ±0.0065 | -0.0044 ±0.0026 | -1.7 | 0.649 | 0.664 | |
| tour: wta | 963 | -0.0319 ±0.0074 | -0.0128 ±0.0031 | -4.3 | 0.673 | 0.684 | |

When they disagree by >= 0.1: model closer to the outcome in **132/351** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 23 | 0.071 | 0.174 |
| 0.1-0.2 | 125 | 0.153 | 0.168 |
| 0.2-0.3 | 180 | 0.250 | 0.261 |
| 0.3-0.4 | 261 | 0.352 | 0.375 |
| 0.4-0.5 | 324 | 0.451 | 0.485 |
| 0.5-0.6 | 298 | 0.551 | 0.557 |
| 0.6-0.7 | 284 | 0.648 | 0.616 |
| 0.7-0.8 | 233 | 0.752 | 0.773 |
| 0.8-0.9 | 159 | 0.845 | 0.774 |
| 0.9-1.0 | 71 | 0.930 | 0.901 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 49 | 0.055 | 0.082 |
| 0.1-0.2 | 104 | 0.155 | 0.154 |
| 0.2-0.3 | 212 | 0.252 | 0.259 |
| 0.3-0.4 | 252 | 0.353 | 0.397 |
| 0.4-0.5 | 277 | 0.445 | 0.469 |
| 0.5-0.6 | 272 | 0.554 | 0.529 |
| 0.6-0.7 | 305 | 0.649 | 0.633 |
| 0.7-0.8 | 251 | 0.748 | 0.745 |
| 0.8-0.9 | 157 | 0.846 | 0.834 |
| 0.9-1.0 | 79 | 0.935 | 0.949 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 427 | +0.0078 ±0.0093 | +0.0022 ±0.0031 | +0.8 | 0.740 | 0.733 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 938 | -0.0003 ±0.0066 | -0.0011 ±0.0027 | -0.1 | 0.659 | 0.667 | |
| top-20 involved | 722 | -0.0013 ±0.0073 | -0.0009 ±0.0026 | -0.2 | 0.726 | 0.725 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| round round robin | 23 | -0.0072 ±0.0257 | -0.0029 ±0.0121 | -0.3 | 0.783 | 0.739 | ⚠ small n |
| tier: tour_finals | 14 | -0.0089 ±0.0277 | -0.0030 ±0.0132 | -0.3 | 0.571 | 0.571 | ⚠ small n |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 21-50 | 654 | -0.0308 ±0.0079 | -0.0124 ±0.0034 | -3.9 | 0.647 | 0.685 | |
| someone outside top-50 | 1416 | -0.0231 ±0.0059 | -0.0094 ±0.0024 | -3.9 | 0.668 | 0.685 | |
| month 2026-09 | 320 | -0.0429 ±0.0105 | -0.0177 ±0.0044 | -4.1 | 0.703 | 0.728 | |
| tour: wta | 963 | -0.0319 ±0.0074 | -0.0128 ±0.0031 | -4.3 | 0.673 | 0.684 | |
| big disagree (>=0.1) | 351 | -0.1012 ±0.0232 | -0.0393 ±0.0097 | -4.4 | 0.583 | 0.641 | |
| no top-20 player | 1236 | -0.0331 ±0.0065 | -0.0130 ±0.0028 | -5.1 | 0.623 | 0.644 | |
| surface: Hard | 1108 | -0.0360 ±0.0069 | -0.0135 ±0.0028 | -5.2 | 0.661 | 0.673 | |
| pred_source: live aligned | 1020 | -0.0407 ±0.0071 | -0.0154 ±0.0029 | -5.7 | 0.663 | 0.680 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1958, mean |Δ|=0.0067, p95=0.0128, >0.05 in 55 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0660 (n=320, >0.05: 19) | 2026-10 p95=0.1324 (n=346, >0.05: 29) | 2026-11 p95=0.0175 (n=152, >0.05: 5)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1972, d_ll -0.0214 ±0.0049
- Unmatched qualifying markets: 720 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'Billie Jean King Cup Qualifiers Round': 56, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Stockholm': 3}
- Unmatched Kalshi names, main draw (40): AYNUR MOVLYAMOVA, Adrian Mannarino, Aishath Karin Saizan, Akasha Urhobo, Aleksandr Shevchenko, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Abualhaj, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Aylara Kakabayeva, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee
