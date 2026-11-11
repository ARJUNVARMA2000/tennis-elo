# Model vs Kalshi — match-by-match scorecard

_Generated 2026-11-11T07:00:35Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 2421 | 2326 | 6 | 16 | 73 | 0 | 17 | 31 | 54 | 2026-05-03..2026-11-11 |
| wta | 2550 | 1550 | 2 | 918 | 80 | 0 | 12 | 24 | 33 | 2026-05-02..2026-11-12 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1929 | 0.6133 | 0.5913 | -0.0220 ±0.0050 | -0.0088 ±0.0020 | 0.659 | 0.674 |
| atp | 974 | 0.6242 | 0.6120 | -0.0122 ±0.0066 | -0.0049 ±0.0026 | 0.644 | 0.661 |
| wta | 955 | 0.6022 | 0.5702 | -0.0320 ±0.0074 | -0.0129 ±0.0031 | 0.675 | 0.687 |
| pooled/live_aligned | 991 | 0.6203 | 0.5778 | -0.0425 ±0.0073 | -0.0161 ±0.0030 | 0.660 | 0.680 |
| pooled/backtest | 938 | 0.6059 | 0.6056 | -0.0003 ±0.0066 | -0.0011 ±0.0027 | 0.659 | 0.667 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 991 | -0.0425 ±0.0073 | -0.0161 ±0.0030 | -5.8 | 0.660 | 0.680 | |
| pred_source: backtest | 938 | -0.0003 ±0.0066 | -0.0011 ±0.0027 | -0.1 | 0.659 | 0.667 | |
| top-20 involved | 699 | -0.0011 ±0.0075 | -0.0009 ±0.0027 | -0.2 | 0.725 | 0.725 | |
| no top-20 player | 1230 | -0.0338 ±0.0065 | -0.0133 ±0.0028 | -5.2 | 0.622 | 0.645 | |
| both inside top-50 | 517 | -0.0177 ±0.0092 | -0.0065 ±0.0038 | -1.9 | 0.637 | 0.643 | |
| someone outside top-50 | 1412 | -0.0235 ±0.0059 | -0.0097 ±0.0024 | -4.0 | 0.667 | 0.685 | |
| best rank 1-10 | 405 | +0.0088 ±0.0097 | +0.0026 ±0.0032 | +0.9 | 0.738 | 0.733 | |
| best rank 11-20 | 294 | -0.0148 ±0.0116 | -0.0057 ±0.0046 | -1.3 | 0.706 | 0.713 | |
| best rank 21-50 | 649 | -0.0320 ±0.0079 | -0.0130 ±0.0034 | -4.0 | 0.647 | 0.687 | |
| best rank 51-100 | 465 | -0.0308 ±0.0113 | -0.0119 ±0.0047 | -2.7 | 0.597 | 0.601 | |
| best rank 100+ | 116 | -0.0566 ±0.0280 | -0.0209 ±0.0119 | -2.0 | 0.586 | 0.582 | |
| kalshi favorite 0.5-0.6 | 536 | -0.0257 ±0.0082 | -0.0119 ±0.0038 | -3.1 | 0.507 | 0.536 | |
| kalshi favorite 0.6-0.7 | 553 | -0.0131 ±0.0083 | -0.0052 ±0.0037 | -1.6 | 0.611 | 0.615 | |
| kalshi favorite 0.7-0.8 | 454 | -0.0154 ±0.0105 | -0.0055 ±0.0041 | -1.5 | 0.730 | 0.740 | |
| kalshi favorite 0.8-0.9 | 258 | -0.0090 ±0.0141 | -0.0037 ±0.0049 | -0.6 | 0.833 | 0.837 | |
| kalshi favorite 0.9-1.0 | 128 | -0.0940 ±0.0304 | -0.0336 ±0.0100 | -3.1 | 0.906 | 0.938 | |
| surface: Hard | 1079 | -0.0375 ±0.0070 | -0.0141 ±0.0029 | -5.3 | 0.658 | 0.673 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 810 | -0.0336 ±0.0085 | -0.0129 ±0.0034 | -4.0 | 0.617 | 0.636 | |
| tier: atp500 | 278 | -0.0183 ±0.0117 | -0.0074 ±0.0051 | -1.6 | 0.644 | 0.653 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 324 | -0.0171 ±0.0108 | -0.0058 ±0.0046 | -1.6 | 0.659 | 0.673 | |
| tier: tour_finals | 6 | +0.0058 ±0.0106 | +0.0027 ±0.0050 | +0.5 | 0.833 | 0.833 | ⚠ small n |
| round early (R128-R64) | 664 | -0.0206 ±0.0081 | -0.0084 ±0.0032 | -2.5 | 0.709 | 0.723 | |
| round late (QF-F) | 287 | -0.0092 ±0.0120 | -0.0039 ±0.0052 | -0.8 | 0.655 | 0.648 | |
| round mid (R32-R16) | 950 | -0.0274 ±0.0075 | -0.0108 ±0.0031 | -3.7 | 0.629 | 0.649 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| round round robin | 6 | +0.0058 ±0.0106 | +0.0027 ±0.0050 | +0.5 | 0.833 | 0.833 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 320 | -0.0429 ±0.0105 | -0.0177 ±0.0044 | -4.1 | 0.703 | 0.728 | |
| month 2026-10 | 346 | -0.0523 ±0.0162 | -0.0189 ±0.0065 | -3.2 | 0.639 | 0.669 | |
| month 2026-11 | 123 | -0.0486 ±0.0171 | -0.0177 ±0.0066 | -2.8 | 0.659 | 0.659 | |
| agree (<0.05) | 1005 | -0.0008 ±0.0023 | -0.0007 ±0.0008 | -0.4 | 0.698 | 0.696 | |
| mild disagree (0.05-0.10) | 578 | -0.0103 ±0.0074 | -0.0042 ±0.0028 | -1.4 | 0.643 | 0.657 | |
| big disagree (>=0.1) | 346 | -0.1030 ±0.0234 | -0.0401 ±0.0098 | -4.4 | 0.577 | 0.639 | |
| tour: atp | 974 | -0.0122 ±0.0066 | -0.0049 ±0.0026 | -1.8 | 0.644 | 0.661 | |
| tour: wta | 955 | -0.0320 ±0.0074 | -0.0129 ±0.0031 | -4.3 | 0.675 | 0.687 | |

When they disagree by >= 0.1: model closer to the outcome in **130/346** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 23 | 0.071 | 0.174 |
| 0.1-0.2 | 124 | 0.153 | 0.169 |
| 0.2-0.3 | 178 | 0.250 | 0.258 |
| 0.3-0.4 | 258 | 0.352 | 0.380 |
| 0.4-0.5 | 319 | 0.450 | 0.483 |
| 0.5-0.6 | 291 | 0.551 | 0.553 |
| 0.6-0.7 | 281 | 0.648 | 0.616 |
| 0.7-0.8 | 228 | 0.752 | 0.768 |
| 0.8-0.9 | 157 | 0.845 | 0.771 |
| 0.9-1.0 | 70 | 0.931 | 0.900 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 49 | 0.055 | 0.082 |
| 0.1-0.2 | 104 | 0.155 | 0.154 |
| 0.2-0.3 | 208 | 0.252 | 0.260 |
| 0.3-0.4 | 249 | 0.353 | 0.398 |
| 0.4-0.5 | 271 | 0.445 | 0.465 |
| 0.5-0.6 | 269 | 0.555 | 0.532 |
| 0.6-0.7 | 300 | 0.649 | 0.630 |
| 0.7-0.8 | 246 | 0.748 | 0.740 |
| 0.8-0.9 | 155 | 0.846 | 0.832 |
| 0.9-1.0 | 78 | 0.936 | 0.949 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 405 | +0.0088 ±0.0097 | +0.0026 ±0.0032 | +0.9 | 0.738 | 0.733 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 938 | -0.0003 ±0.0066 | -0.0011 ±0.0027 | -0.1 | 0.659 | 0.667 | |
| top-20 involved | 699 | -0.0011 ±0.0075 | -0.0009 ±0.0027 | -0.2 | 0.725 | 0.725 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| agree (<0.05) | 1005 | -0.0008 ±0.0023 | -0.0007 ±0.0008 | -0.4 | 0.698 | 0.696 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| someone outside top-50 | 1412 | -0.0235 ±0.0059 | -0.0097 ±0.0024 | -4.0 | 0.667 | 0.685 | |
| best rank 21-50 | 649 | -0.0320 ±0.0079 | -0.0130 ±0.0034 | -4.0 | 0.647 | 0.687 | |
| month 2026-09 | 320 | -0.0429 ±0.0105 | -0.0177 ±0.0044 | -4.1 | 0.703 | 0.728 | |
| tour: wta | 955 | -0.0320 ±0.0074 | -0.0129 ±0.0031 | -4.3 | 0.675 | 0.687 | |
| big disagree (>=0.1) | 346 | -0.1030 ±0.0234 | -0.0401 ±0.0098 | -4.4 | 0.577 | 0.639 | |
| no top-20 player | 1230 | -0.0338 ±0.0065 | -0.0133 ±0.0028 | -5.2 | 0.622 | 0.645 | |
| surface: Hard | 1079 | -0.0375 ±0.0070 | -0.0141 ±0.0029 | -5.3 | 0.658 | 0.673 | |
| pred_source: live aligned | 991 | -0.0425 ±0.0073 | -0.0161 ±0.0030 | -5.8 | 0.660 | 0.680 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1929, mean |Δ|=0.0068, p95=0.0129, >0.05 in 55 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0660 (n=320, >0.05: 19) | 2026-10 p95=0.1324 (n=346, >0.05: 29) | 2026-11 p95=0.0198 (n=123, >0.05: 5)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1943, d_ll -0.0220 ±0.0049
- Unmatched qualifying markets: 720 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'Billie Jean King Cup Qualifiers Round': 56, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): AYNUR MOVLYAMOVA, Aishath Karin Saizan, Akasha Urhobo, Aleksandr Shevchenko, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Abualhaj, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Aylara Kakabayeva, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao
