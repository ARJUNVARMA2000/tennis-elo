# Model vs Kalshi — match-by-match scorecard

_Generated 2026-11-02T08:16:25Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 2355 | 2247 | 23 | 16 | 69 | 0 | 15 | 29 | 50 | 2026-05-03..2026-11-02 |
| wta | 2509 | 1483 | 59 | 894 | 73 | 0 | 12 | 22 | 50 | 2026-05-02..2026-11-02 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1809 | 0.6115 | 0.5914 | -0.0201 ±0.0052 | -0.0082 ±0.0021 | 0.659 | 0.674 |
| atp | 914 | 0.6214 | 0.6101 | -0.0113 ±0.0069 | -0.0046 ±0.0027 | 0.644 | 0.664 |
| wta | 895 | 0.6014 | 0.5724 | -0.0290 ±0.0078 | -0.0118 ±0.0032 | 0.674 | 0.685 |
| pooled/live_aligned | 872 | 0.6170 | 0.5757 | -0.0413 ±0.0079 | -0.0158 ±0.0032 | 0.659 | 0.682 |
| pooled/backtest | 937 | 0.6064 | 0.6061 | -0.0002 ±0.0067 | -0.0011 ±0.0027 | 0.658 | 0.666 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 872 | -0.0413 ±0.0079 | -0.0158 ±0.0032 | -5.2 | 0.659 | 0.682 | |
| pred_source: backtest | 937 | -0.0002 ±0.0067 | -0.0011 ±0.0027 | -0.0 | 0.658 | 0.666 | |
| top-20 involved | 658 | +0.0006 ±0.0077 | -0.0005 ±0.0028 | +0.1 | 0.726 | 0.727 | |
| no top-20 player | 1151 | -0.0319 ±0.0068 | -0.0125 ±0.0029 | -4.7 | 0.621 | 0.644 | |
| both inside top-50 | 477 | -0.0151 ±0.0097 | -0.0057 ±0.0041 | -1.6 | 0.640 | 0.649 | |
| someone outside top-50 | 1332 | -0.0218 ±0.0061 | -0.0091 ±0.0025 | -3.6 | 0.666 | 0.683 | |
| best rank 1-10 | 383 | +0.0106 ±0.0100 | +0.0029 ±0.0033 | +1.1 | 0.742 | 0.739 | |
| best rank 11-20 | 275 | -0.0134 ±0.0122 | -0.0054 ±0.0048 | -1.1 | 0.704 | 0.711 | |
| best rank 21-50 | 614 | -0.0312 ±0.0082 | -0.0126 ±0.0035 | -3.8 | 0.650 | 0.692 | |
| best rank 51-100 | 439 | -0.0296 ±0.0117 | -0.0115 ±0.0049 | -2.5 | 0.589 | 0.591 | |
| best rank 100+ | 98 | -0.0463 ±0.0314 | -0.0171 ±0.0134 | -1.5 | 0.582 | 0.577 | |
| kalshi favorite 0.5-0.6 | 505 | -0.0253 ±0.0086 | -0.0117 ±0.0040 | -3.0 | 0.502 | 0.538 | |
| kalshi favorite 0.6-0.7 | 510 | -0.0125 ±0.0088 | -0.0049 ±0.0039 | -1.4 | 0.610 | 0.614 | |
| kalshi favorite 0.7-0.8 | 424 | -0.0135 ±0.0108 | -0.0048 ±0.0043 | -1.2 | 0.730 | 0.738 | |
| kalshi favorite 0.8-0.9 | 246 | -0.0022 ±0.0144 | -0.0017 ±0.0050 | -0.2 | 0.833 | 0.837 | |
| kalshi favorite 0.9-1.0 | 124 | -0.0877 ±0.0309 | -0.0317 ±0.0101 | -2.8 | 0.911 | 0.935 | |
| surface: Hard | 959 | -0.0358 ±0.0076 | -0.0135 ±0.0031 | -4.7 | 0.657 | 0.674 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 696 | -0.0303 ±0.0094 | -0.0118 ±0.0038 | -3.2 | 0.611 | 0.632 | |
| tier: atp500 | 278 | -0.0183 ±0.0117 | -0.0074 ±0.0051 | -1.6 | 0.644 | 0.653 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 324 | -0.0171 ±0.0108 | -0.0058 ±0.0046 | -1.6 | 0.659 | 0.673 | |
| round early (R128-R64) | 646 | -0.0208 ±0.0083 | -0.0085 ±0.0032 | -2.5 | 0.710 | 0.723 | |
| round late (QF-F) | 268 | -0.0110 ±0.0126 | -0.0046 ±0.0054 | -0.9 | 0.642 | 0.642 | |
| round mid (R32-R16) | 873 | -0.0227 ±0.0078 | -0.0092 ±0.0032 | -2.9 | 0.631 | 0.651 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 320 | -0.0429 ±0.0105 | -0.0177 ±0.0044 | -4.1 | 0.703 | 0.728 | |
| month 2026-10 | 346 | -0.0523 ±0.0162 | -0.0189 ±0.0065 | -3.2 | 0.639 | 0.669 | |
| month 2026-11 | 3 | +0.0482 ±0.1587 | +0.0163 ±0.0625 | +0.3 | 0.333 | 0.333 | ⚠ small n |
| agree (<0.05) | 950 | -0.0008 ±0.0024 | -0.0007 ±0.0008 | -0.3 | 0.699 | 0.699 | |
| mild disagree (0.05-0.10) | 533 | -0.0066 ±0.0076 | -0.0031 ±0.0029 | -0.9 | 0.639 | 0.656 | |
| big disagree (>=0.1) | 326 | -0.0983 ±0.0245 | -0.0383 ±0.0102 | -4.0 | 0.575 | 0.632 | |
| tour: atp | 914 | -0.0113 ±0.0069 | -0.0046 ±0.0027 | -1.6 | 0.644 | 0.664 | |
| tour: wta | 895 | -0.0290 ±0.0078 | -0.0118 ±0.0032 | -3.7 | 0.674 | 0.685 | |

When they disagree by >= 0.1: model closer to the outcome in **124/326** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 21 | 0.071 | 0.190 |
| 0.1-0.2 | 117 | 0.152 | 0.179 |
| 0.2-0.3 | 165 | 0.250 | 0.261 |
| 0.3-0.4 | 240 | 0.352 | 0.379 |
| 0.4-0.5 | 307 | 0.451 | 0.479 |
| 0.5-0.6 | 273 | 0.552 | 0.546 |
| 0.6-0.7 | 257 | 0.648 | 0.611 |
| 0.7-0.8 | 215 | 0.751 | 0.772 |
| 0.8-0.9 | 148 | 0.845 | 0.784 |
| 0.9-1.0 | 66 | 0.931 | 0.909 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 46 | 0.057 | 0.087 |
| 0.1-0.2 | 99 | 0.155 | 0.162 |
| 0.2-0.3 | 192 | 0.253 | 0.266 |
| 0.3-0.4 | 236 | 0.353 | 0.398 |
| 0.4-0.5 | 256 | 0.445 | 0.457 |
| 0.5-0.6 | 253 | 0.554 | 0.526 |
| 0.6-0.7 | 270 | 0.649 | 0.630 |
| 0.7-0.8 | 232 | 0.748 | 0.741 |
| 0.8-0.9 | 148 | 0.847 | 0.838 |
| 0.9-1.0 | 77 | 0.935 | 0.948 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 383 | +0.0106 ±0.0100 | +0.0029 ±0.0033 | +1.1 | 0.742 | 0.739 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| top-20 involved | 658 | +0.0006 ±0.0077 | -0.0005 ±0.0028 | +0.1 | 0.726 | 0.727 | |
| pred_source: backtest | 937 | -0.0002 ±0.0067 | -0.0011 ±0.0027 | -0.0 | 0.658 | 0.666 | |
| kalshi favorite 0.8-0.9 | 246 | -0.0022 ±0.0144 | -0.0017 ±0.0050 | -0.2 | 0.833 | 0.837 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| agree (<0.05) | 950 | -0.0008 ±0.0024 | -0.0007 ±0.0008 | -0.3 | 0.699 | 0.699 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| someone outside top-50 | 1332 | -0.0218 ±0.0061 | -0.0091 ±0.0025 | -3.6 | 0.666 | 0.683 | |
| tour: wta | 895 | -0.0290 ±0.0078 | -0.0118 ±0.0032 | -3.7 | 0.674 | 0.685 | |
| best rank 21-50 | 614 | -0.0312 ±0.0082 | -0.0126 ±0.0035 | -3.8 | 0.650 | 0.692 | |
| big disagree (>=0.1) | 326 | -0.0983 ±0.0245 | -0.0383 ±0.0102 | -4.0 | 0.575 | 0.632 | |
| month 2026-09 | 320 | -0.0429 ±0.0105 | -0.0177 ±0.0044 | -4.1 | 0.703 | 0.728 | |
| no top-20 player | 1151 | -0.0319 ±0.0068 | -0.0125 ±0.0029 | -4.7 | 0.621 | 0.644 | |
| surface: Hard | 959 | -0.0358 ±0.0076 | -0.0135 ±0.0031 | -4.7 | 0.657 | 0.674 | |
| pred_source: live aligned | 872 | -0.0413 ±0.0079 | -0.0158 ±0.0032 | -5.2 | 0.659 | 0.682 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1809, mean |Δ|=0.0067, p95=0.0125, >0.05 in 50 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0660 (n=320, >0.05: 19) | 2026-10 p95=0.1324 (n=346, >0.05: 29) | 2026-11 p95=0.0000 (n=3, >0.05: 0)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1819, d_ll -0.0202 ±0.0051
- Unmatched qualifying markets: 696 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'Billie Jean King Cup Qualifiers Round': 56, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): AYNUR MOVLYAMOVA, Aishath Karin Saizan, Akasha Urhobo, Aleksandr Shevchenko, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Abualhaj, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Aylara Kakabayeva, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao
