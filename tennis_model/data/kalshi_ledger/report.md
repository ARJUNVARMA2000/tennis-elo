# Model vs Kalshi — match-by-match scorecard

_Generated 2026-11-24T11:30:51Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 2443 | 2351 | 0 | 19 | 73 | 0 | 18 | 31 | 49 | 2026-05-03..2026-11-22 |
| wta | 2586 | 1571 | 0 | 919 | 96 | 0 | 12 | 24 | 32 | 2026-05-02..2026-11-23 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1971 | 0.6105 | 0.5893 | -0.0213 ±0.0049 | -0.0085 ±0.0020 | 0.662 | 0.675 |
| atp | 998 | 0.6198 | 0.6086 | -0.0111 ±0.0065 | -0.0044 ±0.0025 | 0.650 | 0.665 |
| wta | 973 | 0.6011 | 0.5694 | -0.0317 ±0.0074 | -0.0126 ±0.0031 | 0.674 | 0.684 |
| pooled/live_aligned | 1023 | 0.6165 | 0.5760 | -0.0406 ±0.0071 | -0.0153 ±0.0029 | 0.664 | 0.681 |
| pooled/backtest | 948 | 0.6040 | 0.6036 | -0.0004 ±0.0066 | -0.0010 ±0.0027 | 0.660 | 0.667 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 1023 | -0.0406 ±0.0071 | -0.0153 ±0.0029 | -5.7 | 0.664 | 0.681 | |
| pred_source: backtest | 948 | -0.0004 ±0.0066 | -0.0010 ±0.0027 | -0.1 | 0.660 | 0.667 | |
| top-20 involved | 726 | -0.0013 ±0.0072 | -0.0009 ±0.0026 | -0.2 | 0.728 | 0.727 | |
| no top-20 player | 1245 | -0.0329 ±0.0065 | -0.0128 ±0.0028 | -5.1 | 0.624 | 0.644 | |
| both inside top-50 | 545 | -0.0168 ±0.0088 | -0.0061 ±0.0037 | -1.9 | 0.643 | 0.647 | |
| someone outside top-50 | 1426 | -0.0230 ±0.0059 | -0.0093 ±0.0024 | -3.9 | 0.669 | 0.685 | |
| best rank 1-10 | 431 | +0.0077 ±0.0092 | +0.0023 ±0.0031 | +0.8 | 0.742 | 0.735 | |
| best rank 11-20 | 295 | -0.0143 ±0.0116 | -0.0056 ±0.0045 | -1.2 | 0.707 | 0.714 | |
| best rank 21-50 | 657 | -0.0294 ±0.0079 | -0.0118 ±0.0034 | -3.7 | 0.647 | 0.683 | |
| best rank 51-100 | 469 | -0.0308 ±0.0112 | -0.0119 ±0.0047 | -2.8 | 0.600 | 0.604 | |
| best rank 100+ | 119 | -0.0606 ±0.0274 | -0.0223 ±0.0117 | -2.2 | 0.588 | 0.584 | |
| kalshi favorite 0.5-0.6 | 546 | -0.0236 ±0.0082 | -0.0108 ±0.0038 | -2.9 | 0.506 | 0.532 | |
| kalshi favorite 0.6-0.7 | 565 | -0.0132 ±0.0081 | -0.0053 ±0.0036 | -1.6 | 0.614 | 0.618 | |
| kalshi favorite 0.7-0.8 | 465 | -0.0143 ±0.0104 | -0.0050 ±0.0041 | -1.4 | 0.734 | 0.742 | |
| kalshi favorite 0.8-0.9 | 261 | -0.0090 ±0.0140 | -0.0037 ±0.0048 | -0.6 | 0.835 | 0.839 | |
| kalshi favorite 0.9-1.0 | 134 | -0.0938 ±0.0291 | -0.0331 ±0.0096 | -3.2 | 0.910 | 0.940 | |
| surface: Hard | 1115 | -0.0360 ±0.0068 | -0.0135 ±0.0028 | -5.3 | 0.662 | 0.674 | |
| surface: Clay | 528 | +0.0023 ±0.0087 | -0.0004 ±0.0034 | +0.3 | 0.676 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 834 | -0.0318 ±0.0083 | -0.0121 ±0.0034 | -3.8 | 0.626 | 0.641 | |
| tier: atp500 | 278 | -0.0183 ±0.0117 | -0.0074 ±0.0051 | -1.6 | 0.644 | 0.653 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: davis_cup | 10 | -0.0085 ±0.0937 | +0.0069 ±0.0416 | -0.1 | 0.800 | 0.700 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 324 | -0.0171 ±0.0108 | -0.0058 ±0.0046 | -1.6 | 0.659 | 0.673 | |
| tier: tour_finals | 14 | -0.0089 ±0.0277 | -0.0030 ±0.0132 | -0.3 | 0.571 | 0.571 | ⚠ small n |
| round early (R128-R64) | 664 | -0.0206 ±0.0081 | -0.0084 ±0.0032 | -2.5 | 0.709 | 0.723 | |
| round late (QF-F) | 298 | -0.0082 ±0.0116 | -0.0034 ±0.0050 | -0.7 | 0.658 | 0.651 | |
| round mid (R32-R16) | 954 | -0.0267 ±0.0075 | -0.0105 ±0.0030 | -3.6 | 0.631 | 0.649 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| round round robin | 33 | -0.0076 ±0.0326 | +0.0001 ±0.0148 | -0.2 | 0.788 | 0.727 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 320 | -0.0429 ±0.0105 | -0.0177 ±0.0044 | -4.1 | 0.703 | 0.728 | |
| month 2026-10 | 346 | -0.0523 ±0.0162 | -0.0189 ±0.0065 | -3.2 | 0.639 | 0.669 | |
| month 2026-11 | 165 | -0.0332 ±0.0147 | -0.0111 ±0.0059 | -2.3 | 0.691 | 0.673 | |
| agree (<0.05) | 1028 | -0.0009 ±0.0022 | -0.0007 ±0.0008 | -0.4 | 0.700 | 0.698 | |
| mild disagree (0.05-0.10) | 590 | -0.0101 ±0.0073 | -0.0041 ±0.0028 | -1.4 | 0.642 | 0.653 | |
| big disagree (>=0.1) | 353 | -0.0994 ±0.0232 | -0.0384 ±0.0097 | -4.3 | 0.585 | 0.640 | |
| tour: atp | 998 | -0.0111 ±0.0065 | -0.0044 ±0.0025 | -1.7 | 0.650 | 0.665 | |
| tour: wta | 973 | -0.0317 ±0.0074 | -0.0126 ±0.0031 | -4.3 | 0.674 | 0.684 | |

When they disagree by >= 0.1: model closer to the outcome in **133/353** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 23 | 0.071 | 0.174 |
| 0.1-0.2 | 126 | 0.153 | 0.167 |
| 0.2-0.3 | 181 | 0.250 | 0.260 |
| 0.3-0.4 | 262 | 0.352 | 0.374 |
| 0.4-0.5 | 326 | 0.450 | 0.482 |
| 0.5-0.6 | 299 | 0.551 | 0.555 |
| 0.6-0.7 | 287 | 0.648 | 0.617 |
| 0.7-0.8 | 234 | 0.752 | 0.774 |
| 0.8-0.9 | 161 | 0.846 | 0.776 |
| 0.9-1.0 | 72 | 0.931 | 0.903 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 50 | 0.055 | 0.080 |
| 0.1-0.2 | 105 | 0.156 | 0.152 |
| 0.2-0.3 | 212 | 0.252 | 0.259 |
| 0.3-0.4 | 254 | 0.353 | 0.394 |
| 0.4-0.5 | 277 | 0.445 | 0.469 |
| 0.5-0.6 | 273 | 0.554 | 0.527 |
| 0.6-0.7 | 307 | 0.649 | 0.632 |
| 0.7-0.8 | 253 | 0.748 | 0.743 |
| 0.8-0.9 | 157 | 0.846 | 0.834 |
| 0.9-1.0 | 83 | 0.935 | 0.952 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 431 | +0.0077 ±0.0092 | +0.0023 ±0.0031 | +0.8 | 0.742 | 0.735 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 528 | +0.0023 ±0.0087 | -0.0004 ±0.0034 | +0.3 | 0.676 | 0.687 | |
| pred_source: backtest | 948 | -0.0004 ±0.0066 | -0.0010 ±0.0027 | -0.1 | 0.660 | 0.667 | |
| tier: davis_cup | 10 | -0.0085 ±0.0937 | +0.0069 ±0.0416 | -0.1 | 0.800 | 0.700 | ⚠ small n |
| top-20 involved | 726 | -0.0013 ±0.0072 | -0.0009 ±0.0026 | -0.2 | 0.728 | 0.727 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| round round robin | 33 | -0.0076 ±0.0326 | +0.0001 ±0.0148 | -0.2 | 0.788 | 0.727 | ⚠ small n |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| tier: atp250 | 834 | -0.0318 ±0.0083 | -0.0121 ±0.0034 | -3.8 | 0.626 | 0.641 | |
| someone outside top-50 | 1426 | -0.0230 ±0.0059 | -0.0093 ±0.0024 | -3.9 | 0.669 | 0.685 | |
| month 2026-09 | 320 | -0.0429 ±0.0105 | -0.0177 ±0.0044 | -4.1 | 0.703 | 0.728 | |
| big disagree (>=0.1) | 353 | -0.0994 ±0.0232 | -0.0384 ±0.0097 | -4.3 | 0.585 | 0.640 | |
| tour: wta | 973 | -0.0317 ±0.0074 | -0.0126 ±0.0031 | -4.3 | 0.674 | 0.684 | |
| no top-20 player | 1245 | -0.0329 ±0.0065 | -0.0128 ±0.0028 | -5.1 | 0.624 | 0.644 | |
| surface: Hard | 1115 | -0.0360 ±0.0068 | -0.0135 ±0.0028 | -5.3 | 0.662 | 0.674 | |
| pred_source: live aligned | 1023 | -0.0406 ±0.0071 | -0.0153 ±0.0029 | -5.7 | 0.664 | 0.681 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1971, mean |Δ|=0.0067, p95=0.0127, >0.05 in 55 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0660 (n=320, >0.05: 19) | 2026-10 p95=0.1324 (n=346, >0.05: 29) | 2026-11 p95=0.0158 (n=165, >0.05: 5)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1985, d_ll -0.0213 ±0.0049
- Unmatched qualifying markets: 720 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'Billie Jean King Cup Qualifiers Round': 57, 'US Open': 57, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Stockholm': 3}
- Unmatched Kalshi names, main draw (40): AYNUR MOVLYAMOVA, Adrian Mannarino, Aishath Karin Saizan, Akasha Urhobo, Aleksandr Shevchenko, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Abualhaj, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Aylara Kakabayeva, Bella Payne, Bianca Andreescu, Cadence Brace, Caijsa Wilda Hennemann, Camila Soares
