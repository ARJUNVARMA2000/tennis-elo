# Model vs Kalshi — match-by-match scorecard

_Generated 2026-11-12T13:31:50Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 2425 | 2330 | 6 | 16 | 73 | 0 | 17 | 31 | 53 | 2026-05-03..2026-11-12 |
| wta | 2552 | 1552 | 2 | 918 | 80 | 0 | 12 | 24 | 33 | 2026-05-02..2026-11-13 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1935 | 0.6129 | 0.5913 | -0.0216 ±0.0050 | -0.0087 ±0.0020 | 0.659 | 0.673 |
| atp | 978 | 0.6230 | 0.6115 | -0.0115 ±0.0066 | -0.0046 ±0.0026 | 0.645 | 0.661 |
| wta | 957 | 0.6026 | 0.5706 | -0.0319 ±0.0074 | -0.0128 ±0.0031 | 0.674 | 0.685 |
| pooled/live_aligned | 997 | 0.6195 | 0.5779 | -0.0416 ±0.0073 | -0.0158 ±0.0030 | 0.660 | 0.679 |
| pooled/backtest | 938 | 0.6059 | 0.6056 | -0.0003 ±0.0066 | -0.0011 ±0.0027 | 0.659 | 0.667 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 997 | -0.0416 ±0.0073 | -0.0158 ±0.0030 | -5.7 | 0.660 | 0.679 | |
| pred_source: backtest | 938 | -0.0003 ±0.0066 | -0.0011 ±0.0027 | -0.1 | 0.659 | 0.667 | |
| top-20 involved | 702 | -0.0010 ±0.0074 | -0.0008 ±0.0027 | -0.1 | 0.723 | 0.723 | |
| no top-20 player | 1233 | -0.0334 ±0.0065 | -0.0131 ±0.0028 | -5.1 | 0.623 | 0.645 | |
| both inside top-50 | 519 | -0.0177 ±0.0092 | -0.0065 ±0.0038 | -1.9 | 0.635 | 0.641 | |
| someone outside top-50 | 1416 | -0.0231 ±0.0059 | -0.0094 ±0.0024 | -3.9 | 0.668 | 0.685 | |
| best rank 1-10 | 407 | +0.0087 ±0.0097 | +0.0026 ±0.0032 | +0.9 | 0.735 | 0.730 | |
| best rank 11-20 | 295 | -0.0143 ±0.0116 | -0.0056 ±0.0045 | -1.2 | 0.707 | 0.714 | |
| best rank 21-50 | 651 | -0.0312 ±0.0079 | -0.0126 ±0.0034 | -4.0 | 0.648 | 0.687 | |
| best rank 51-100 | 466 | -0.0306 ±0.0113 | -0.0119 ±0.0047 | -2.7 | 0.598 | 0.602 | |
| best rank 100+ | 116 | -0.0566 ±0.0280 | -0.0209 ±0.0119 | -2.0 | 0.586 | 0.582 | |
| kalshi favorite 0.5-0.6 | 539 | -0.0250 ±0.0082 | -0.0115 ±0.0038 | -3.0 | 0.506 | 0.533 | |
| kalshi favorite 0.6-0.7 | 555 | -0.0128 ±0.0082 | -0.0051 ±0.0037 | -1.6 | 0.613 | 0.616 | |
| kalshi favorite 0.7-0.8 | 455 | -0.0151 ±0.0104 | -0.0054 ±0.0041 | -1.4 | 0.731 | 0.741 | |
| kalshi favorite 0.8-0.9 | 258 | -0.0090 ±0.0141 | -0.0037 ±0.0049 | -0.6 | 0.833 | 0.837 | |
| kalshi favorite 0.9-1.0 | 128 | -0.0940 ±0.0304 | -0.0336 ±0.0100 | -3.1 | 0.906 | 0.938 | |
| surface: Hard | 1085 | -0.0367 ±0.0070 | -0.0138 ±0.0029 | -5.2 | 0.658 | 0.672 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 814 | -0.0328 ±0.0085 | -0.0125 ±0.0034 | -3.9 | 0.619 | 0.636 | |
| tier: atp500 | 278 | -0.0183 ±0.0117 | -0.0074 ±0.0051 | -1.6 | 0.644 | 0.653 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 324 | -0.0171 ±0.0108 | -0.0058 ±0.0046 | -1.6 | 0.659 | 0.673 | |
| tier: tour_finals | 8 | +0.0053 ±0.0342 | +0.0025 ±0.0169 | +0.2 | 0.625 | 0.625 | ⚠ small n |
| round early (R128-R64) | 664 | -0.0206 ±0.0081 | -0.0084 ±0.0032 | -2.5 | 0.709 | 0.723 | |
| round late (QF-F) | 287 | -0.0092 ±0.0120 | -0.0039 ±0.0052 | -0.8 | 0.655 | 0.648 | |
| round mid (R32-R16) | 954 | -0.0267 ±0.0075 | -0.0105 ±0.0030 | -3.6 | 0.631 | 0.649 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| round round robin | 8 | +0.0053 ±0.0342 | +0.0025 ±0.0169 | +0.2 | 0.625 | 0.625 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 320 | -0.0429 ±0.0105 | -0.0177 ±0.0044 | -4.1 | 0.703 | 0.728 | |
| month 2026-10 | 346 | -0.0523 ±0.0162 | -0.0189 ±0.0065 | -3.2 | 0.639 | 0.669 | |
| month 2026-11 | 129 | -0.0418 ±0.0168 | -0.0148 ±0.0065 | -2.5 | 0.659 | 0.651 | |
| agree (<0.05) | 1006 | -0.0007 ±0.0023 | -0.0007 ±0.0008 | -0.3 | 0.698 | 0.696 | |
| mild disagree (0.05-0.10) | 582 | -0.0099 ±0.0073 | -0.0040 ±0.0028 | -1.3 | 0.642 | 0.655 | |
| big disagree (>=0.1) | 347 | -0.1018 ±0.0234 | -0.0395 ±0.0098 | -4.3 | 0.578 | 0.637 | |
| tour: atp | 978 | -0.0115 ±0.0066 | -0.0046 ±0.0026 | -1.8 | 0.645 | 0.661 | |
| tour: wta | 957 | -0.0319 ±0.0074 | -0.0128 ±0.0031 | -4.3 | 0.674 | 0.685 | |

When they disagree by >= 0.1: model closer to the outcome in **131/347** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 23 | 0.071 | 0.174 |
| 0.1-0.2 | 125 | 0.153 | 0.168 |
| 0.2-0.3 | 179 | 0.250 | 0.257 |
| 0.3-0.4 | 258 | 0.352 | 0.380 |
| 0.4-0.5 | 320 | 0.451 | 0.484 |
| 0.5-0.6 | 293 | 0.551 | 0.553 |
| 0.6-0.7 | 281 | 0.648 | 0.616 |
| 0.7-0.8 | 229 | 0.752 | 0.769 |
| 0.8-0.9 | 157 | 0.845 | 0.771 |
| 0.9-1.0 | 70 | 0.931 | 0.900 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 49 | 0.055 | 0.082 |
| 0.1-0.2 | 104 | 0.155 | 0.154 |
| 0.2-0.3 | 209 | 0.252 | 0.258 |
| 0.3-0.4 | 250 | 0.353 | 0.396 |
| 0.4-0.5 | 273 | 0.445 | 0.469 |
| 0.5-0.6 | 270 | 0.554 | 0.530 |
| 0.6-0.7 | 301 | 0.649 | 0.631 |
| 0.7-0.8 | 246 | 0.748 | 0.740 |
| 0.8-0.9 | 155 | 0.846 | 0.832 |
| 0.9-1.0 | 78 | 0.936 | 0.949 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 407 | +0.0087 ±0.0097 | +0.0026 ±0.0032 | +0.9 | 0.735 | 0.730 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 938 | -0.0003 ±0.0066 | -0.0011 ±0.0027 | -0.1 | 0.659 | 0.667 | |
| top-20 involved | 702 | -0.0010 ±0.0074 | -0.0008 ±0.0027 | -0.1 | 0.723 | 0.723 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| agree (<0.05) | 1006 | -0.0007 ±0.0023 | -0.0007 ±0.0008 | -0.3 | 0.698 | 0.696 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| someone outside top-50 | 1416 | -0.0231 ±0.0059 | -0.0094 ±0.0024 | -3.9 | 0.668 | 0.685 | |
| best rank 21-50 | 651 | -0.0312 ±0.0079 | -0.0126 ±0.0034 | -4.0 | 0.648 | 0.687 | |
| month 2026-09 | 320 | -0.0429 ±0.0105 | -0.0177 ±0.0044 | -4.1 | 0.703 | 0.728 | |
| tour: wta | 957 | -0.0319 ±0.0074 | -0.0128 ±0.0031 | -4.3 | 0.674 | 0.685 | |
| big disagree (>=0.1) | 347 | -0.1018 ±0.0234 | -0.0395 ±0.0098 | -4.3 | 0.578 | 0.637 | |
| no top-20 player | 1233 | -0.0334 ±0.0065 | -0.0131 ±0.0028 | -5.1 | 0.623 | 0.645 | |
| surface: Hard | 1085 | -0.0367 ±0.0070 | -0.0138 ±0.0029 | -5.2 | 0.658 | 0.672 | |
| pred_source: live aligned | 997 | -0.0416 ±0.0073 | -0.0158 ±0.0030 | -5.7 | 0.660 | 0.679 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1935, mean |Δ|=0.0068, p95=0.0128, >0.05 in 55 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0660 (n=320, >0.05: 19) | 2026-10 p95=0.1324 (n=346, >0.05: 29) | 2026-11 p95=0.0191 (n=129, >0.05: 5)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1949, d_ll -0.0216 ±0.0049
- Unmatched qualifying markets: 720 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'Billie Jean King Cup Qualifiers Round': 56, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): AYNUR MOVLYAMOVA, Aishath Karin Saizan, Akasha Urhobo, Aleksandr Shevchenko, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Abualhaj, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Aylara Kakabayeva, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao
