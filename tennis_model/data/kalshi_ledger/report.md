# Model vs Kalshi — match-by-match scorecard

_Generated 2026-10-29T09:07:35Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 2297 | 2200 | 13 | 15 | 69 | 0 | 15 | 27 | 55 | 2026-05-03..2026-10-29 |
| wta | 2439 | 1464 | 8 | 894 | 73 | 0 | 11 | 22 | 35 | 2026-05-02..2026-10-30 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1771 | 0.6096 | 0.5918 | -0.0178 ±0.0051 | -0.0074 ±0.0021 | 0.659 | 0.674 |
| atp | 890 | 0.6203 | 0.6101 | -0.0101 ±0.0068 | -0.0044 ±0.0027 | 0.645 | 0.663 |
| wta | 881 | 0.5988 | 0.5732 | -0.0256 ±0.0076 | -0.0105 ±0.0032 | 0.673 | 0.686 |
| pooled/live_aligned | 834 | 0.6132 | 0.5757 | -0.0375 ±0.0078 | -0.0145 ±0.0032 | 0.659 | 0.683 |
| pooled/backtest | 937 | 0.6064 | 0.6061 | -0.0002 ±0.0067 | -0.0011 ±0.0027 | 0.658 | 0.666 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 834 | -0.0375 ±0.0078 | -0.0145 ±0.0032 | -4.8 | 0.659 | 0.683 | |
| pred_source: backtest | 937 | -0.0002 ±0.0067 | -0.0011 ±0.0027 | -0.0 | 0.658 | 0.666 | |
| top-20 involved | 635 | +0.0018 ±0.0076 | -0.0005 ±0.0028 | +0.2 | 0.725 | 0.727 | |
| no top-20 player | 1136 | -0.0288 ±0.0067 | -0.0113 ±0.0028 | -4.3 | 0.622 | 0.645 | |
| both inside top-50 | 459 | -0.0148 ±0.0098 | -0.0058 ±0.0041 | -1.5 | 0.642 | 0.648 | |
| someone outside top-50 | 1312 | -0.0189 ±0.0060 | -0.0080 ±0.0024 | -3.2 | 0.665 | 0.684 | |
| best rank 1-10 | 369 | +0.0121 ±0.0100 | +0.0032 ±0.0034 | +1.2 | 0.740 | 0.737 | |
| best rank 11-20 | 266 | -0.0125 ±0.0119 | -0.0055 ±0.0048 | -1.0 | 0.705 | 0.712 | |
| best rank 21-50 | 610 | -0.0300 ±0.0082 | -0.0121 ±0.0035 | -3.7 | 0.652 | 0.693 | |
| best rank 51-100 | 430 | -0.0235 ±0.0113 | -0.0090 ±0.0048 | -2.1 | 0.587 | 0.590 | |
| best rank 100+ | 96 | -0.0446 ±0.0314 | -0.0166 ±0.0134 | -1.4 | 0.583 | 0.589 | |
| kalshi favorite 0.5-0.6 | 500 | -0.0265 ±0.0086 | -0.0122 ±0.0040 | -3.1 | 0.501 | 0.539 | |
| kalshi favorite 0.6-0.7 | 499 | -0.0105 ±0.0087 | -0.0041 ±0.0039 | -1.2 | 0.609 | 0.613 | |
| kalshi favorite 0.7-0.8 | 411 | -0.0101 ±0.0106 | -0.0039 ±0.0043 | -1.0 | 0.736 | 0.745 | |
| kalshi favorite 0.8-0.9 | 240 | -0.0025 ±0.0148 | -0.0018 ±0.0052 | -0.2 | 0.829 | 0.833 | |
| kalshi favorite 0.9-1.0 | 121 | -0.0688 ±0.0292 | -0.0245 ±0.0092 | -2.4 | 0.917 | 0.934 | |
| surface: Hard | 921 | -0.0321 ±0.0075 | -0.0123 ±0.0031 | -4.3 | 0.657 | 0.674 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 662 | -0.0259 ±0.0093 | -0.0103 ±0.0038 | -2.8 | 0.610 | 0.633 | |
| tier: atp500 | 274 | -0.0154 ±0.0114 | -0.0066 ±0.0051 | -1.4 | 0.639 | 0.648 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 324 | -0.0171 ±0.0108 | -0.0058 ±0.0046 | -1.6 | 0.659 | 0.673 | |
| round early (R128-R64) | 646 | -0.0208 ±0.0083 | -0.0085 ±0.0032 | -2.5 | 0.710 | 0.723 | |
| round late (QF-F) | 245 | -0.0024 ±0.0114 | -0.0013 ±0.0051 | -0.2 | 0.641 | 0.637 | |
| round mid (R32-R16) | 858 | -0.0203 ±0.0078 | -0.0085 ±0.0032 | -2.6 | 0.630 | 0.652 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 320 | -0.0429 ±0.0105 | -0.0177 ±0.0044 | -4.1 | 0.703 | 0.728 | |
| month 2026-10 | 311 | -0.0425 ±0.0162 | -0.0156 ±0.0067 | -2.6 | 0.633 | 0.667 | |
| agree (<0.05) | 937 | -0.0008 ±0.0024 | -0.0007 ±0.0008 | -0.3 | 0.699 | 0.699 | |
| mild disagree (0.05-0.10) | 522 | -0.0084 ±0.0077 | -0.0038 ±0.0030 | -1.1 | 0.637 | 0.656 | |
| big disagree (>=0.1) | 312 | -0.0845 ±0.0246 | -0.0337 ±0.0104 | -3.4 | 0.575 | 0.631 | |
| tour: atp | 890 | -0.0101 ±0.0068 | -0.0044 ±0.0027 | -1.5 | 0.645 | 0.663 | |
| tour: wta | 881 | -0.0256 ±0.0076 | -0.0105 ±0.0032 | -3.4 | 0.673 | 0.686 | |

When they disagree by >= 0.1: model closer to the outcome in **120/312** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 20 | 0.069 | 0.150 |
| 0.1-0.2 | 112 | 0.152 | 0.188 |
| 0.2-0.3 | 161 | 0.250 | 0.261 |
| 0.3-0.4 | 234 | 0.353 | 0.376 |
| 0.4-0.5 | 302 | 0.451 | 0.483 |
| 0.5-0.6 | 270 | 0.551 | 0.544 |
| 0.6-0.7 | 255 | 0.648 | 0.612 |
| 0.7-0.8 | 210 | 0.751 | 0.781 |
| 0.8-0.9 | 144 | 0.846 | 0.785 |
| 0.9-1.0 | 63 | 0.932 | 0.921 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 45 | 0.058 | 0.089 |
| 0.1-0.2 | 96 | 0.154 | 0.167 |
| 0.2-0.3 | 185 | 0.253 | 0.259 |
| 0.3-0.4 | 230 | 0.353 | 0.404 |
| 0.4-0.5 | 254 | 0.445 | 0.457 |
| 0.5-0.6 | 250 | 0.554 | 0.528 |
| 0.6-0.7 | 265 | 0.649 | 0.634 |
| 0.7-0.8 | 226 | 0.748 | 0.748 |
| 0.8-0.9 | 145 | 0.846 | 0.834 |
| 0.9-1.0 | 75 | 0.934 | 0.947 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 369 | +0.0121 ±0.0100 | +0.0032 ±0.0034 | +1.2 | 0.740 | 0.737 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| top-20 involved | 635 | +0.0018 ±0.0076 | -0.0005 ±0.0028 | +0.2 | 0.725 | 0.727 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 937 | -0.0002 ±0.0067 | -0.0011 ±0.0027 | -0.0 | 0.658 | 0.666 | |
| kalshi favorite 0.8-0.9 | 240 | -0.0025 ±0.0148 | -0.0018 ±0.0052 | -0.2 | 0.829 | 0.833 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| round late (QF-F) | 245 | -0.0024 ±0.0114 | -0.0013 ±0.0051 | -0.2 | 0.641 | 0.637 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| someone outside top-50 | 1312 | -0.0189 ±0.0060 | -0.0080 ±0.0024 | -3.2 | 0.665 | 0.684 | |
| tour: wta | 881 | -0.0256 ±0.0076 | -0.0105 ±0.0032 | -3.4 | 0.673 | 0.686 | |
| big disagree (>=0.1) | 312 | -0.0845 ±0.0246 | -0.0337 ±0.0104 | -3.4 | 0.575 | 0.631 | |
| best rank 21-50 | 610 | -0.0300 ±0.0082 | -0.0121 ±0.0035 | -3.7 | 0.652 | 0.693 | |
| month 2026-09 | 320 | -0.0429 ±0.0105 | -0.0177 ±0.0044 | -4.1 | 0.703 | 0.728 | |
| surface: Hard | 921 | -0.0321 ±0.0075 | -0.0123 ±0.0031 | -4.3 | 0.657 | 0.674 | |
| no top-20 player | 1136 | -0.0288 ±0.0067 | -0.0113 ±0.0028 | -4.3 | 0.622 | 0.645 | |
| pred_source: live aligned | 834 | -0.0375 ±0.0078 | -0.0145 ±0.0032 | -4.8 | 0.659 | 0.683 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1771, mean |Δ|=0.0066, p95=0.0124, >0.05 in 49 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0660 (n=320, >0.05: 19) | 2026-10 p95=0.1369 (n=311, >0.05: 28)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1779, d_ll -0.0179 ±0.0051
- Unmatched qualifying markets: 696 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'Billie Jean King Cup Qualifiers Round': 56, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): AYNUR MOVLYAMOVA, Aishath Karin Saizan, Akasha Urhobo, Aleksandr Shevchenko, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Abualhaj, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Aylara Kakabayeva, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao
