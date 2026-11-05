# Model vs Kalshi — match-by-match scorecard

_Generated 2026-11-05T11:41:13Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 2383 | 2287 | 8 | 16 | 72 | 0 | 15 | 31 | 56 | 2026-05-03..2026-11-05 |
| wta | 2532 | 1524 | 10 | 918 | 80 | 0 | 12 | 23 | 37 | 2026-05-02..2026-11-06 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1879 | 0.6159 | 0.5928 | -0.0231 ±0.0051 | -0.0092 ±0.0021 | 0.656 | 0.672 |
| atp | 948 | 0.6279 | 0.6141 | -0.0138 ±0.0067 | -0.0055 ±0.0026 | 0.640 | 0.660 |
| wta | 931 | 0.6036 | 0.5711 | -0.0325 ±0.0076 | -0.0131 ±0.0032 | 0.671 | 0.684 |
| pooled/live_aligned | 941 | 0.6258 | 0.5801 | -0.0457 ±0.0076 | -0.0173 ±0.0031 | 0.652 | 0.677 |
| pooled/backtest | 938 | 0.6059 | 0.6056 | -0.0003 ±0.0066 | -0.0011 ±0.0027 | 0.659 | 0.667 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 941 | -0.0457 ±0.0076 | -0.0173 ±0.0031 | -6.0 | 0.652 | 0.677 | |
| pred_source: backtest | 938 | -0.0003 ±0.0066 | -0.0011 ±0.0027 | -0.1 | 0.659 | 0.667 | |
| top-20 involved | 677 | -0.0022 ±0.0077 | -0.0013 ±0.0028 | -0.3 | 0.722 | 0.723 | |
| no top-20 player | 1202 | -0.0348 ±0.0066 | -0.0137 ±0.0028 | -5.3 | 0.619 | 0.643 | |
| both inside top-50 | 499 | -0.0193 ±0.0095 | -0.0071 ±0.0039 | -2.0 | 0.630 | 0.638 | |
| someone outside top-50 | 1380 | -0.0244 ±0.0060 | -0.0100 ±0.0024 | -4.1 | 0.665 | 0.684 | |
| best rank 1-10 | 392 | +0.0072 ±0.0100 | +0.0020 ±0.0033 | +0.7 | 0.735 | 0.732 | |
| best rank 11-20 | 285 | -0.0152 ±0.0120 | -0.0059 ±0.0047 | -1.3 | 0.704 | 0.711 | |
| best rank 21-50 | 635 | -0.0335 ±0.0080 | -0.0136 ±0.0034 | -4.2 | 0.646 | 0.688 | |
| best rank 51-100 | 455 | -0.0315 ±0.0115 | -0.0123 ±0.0048 | -2.7 | 0.592 | 0.599 | |
| best rank 100+ | 112 | -0.0556 ±0.0289 | -0.0203 ±0.0123 | -1.9 | 0.571 | 0.567 | |
| kalshi favorite 0.5-0.6 | 524 | -0.0272 ±0.0084 | -0.0125 ±0.0039 | -3.2 | 0.499 | 0.535 | |
| kalshi favorite 0.6-0.7 | 535 | -0.0141 ±0.0085 | -0.0056 ±0.0038 | -1.7 | 0.607 | 0.611 | |
| kalshi favorite 0.7-0.8 | 439 | -0.0173 ±0.0108 | -0.0061 ±0.0043 | -1.6 | 0.728 | 0.738 | |
| kalshi favorite 0.8-0.9 | 253 | -0.0077 ±0.0143 | -0.0031 ±0.0049 | -0.5 | 0.830 | 0.834 | |
| kalshi favorite 0.9-1.0 | 128 | -0.0940 ±0.0304 | -0.0336 ±0.0100 | -3.1 | 0.906 | 0.938 | |
| surface: Hard | 1029 | -0.0402 ±0.0073 | -0.0151 ±0.0030 | -5.5 | 0.651 | 0.670 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 766 | -0.0368 ±0.0089 | -0.0141 ±0.0036 | -4.1 | 0.607 | 0.631 | |
| tier: atp500 | 278 | -0.0183 ±0.0117 | -0.0074 ±0.0051 | -1.6 | 0.644 | 0.653 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 324 | -0.0171 ±0.0108 | -0.0058 ±0.0046 | -1.6 | 0.659 | 0.673 | |
| round early (R128-R64) | 664 | -0.0206 ±0.0081 | -0.0084 ±0.0032 | -2.5 | 0.709 | 0.723 | |
| round late (QF-F) | 268 | -0.0110 ±0.0126 | -0.0046 ±0.0054 | -0.9 | 0.642 | 0.642 | |
| round mid (R32-R16) | 925 | -0.0288 ±0.0077 | -0.0113 ±0.0031 | -3.8 | 0.625 | 0.647 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 320 | -0.0429 ±0.0105 | -0.0177 ±0.0044 | -4.1 | 0.703 | 0.728 | |
| month 2026-10 | 346 | -0.0523 ±0.0162 | -0.0189 ±0.0065 | -3.2 | 0.639 | 0.669 | |
| month 2026-11 | 73 | -0.0949 ±0.0249 | -0.0346 ±0.0094 | -3.8 | 0.562 | 0.603 | |
| agree (<0.05) | 978 | -0.0013 ±0.0023 | -0.0009 ±0.0008 | -0.5 | 0.695 | 0.694 | |
| mild disagree (0.05-0.10) | 561 | -0.0112 ±0.0075 | -0.0045 ±0.0029 | -1.5 | 0.637 | 0.655 | |
| big disagree (>=0.1) | 340 | -0.1055 ±0.0238 | -0.0410 ±0.0099 | -4.4 | 0.572 | 0.635 | |
| tour: atp | 948 | -0.0138 ±0.0067 | -0.0055 ±0.0026 | -2.0 | 0.640 | 0.660 | |
| tour: wta | 931 | -0.0325 ±0.0076 | -0.0131 ±0.0032 | -4.3 | 0.671 | 0.684 | |

When they disagree by >= 0.1: model closer to the outcome in **126/340** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 22 | 0.072 | 0.182 |
| 0.1-0.2 | 121 | 0.152 | 0.174 |
| 0.2-0.3 | 173 | 0.250 | 0.260 |
| 0.3-0.4 | 253 | 0.352 | 0.379 |
| 0.4-0.5 | 317 | 0.450 | 0.486 |
| 0.5-0.6 | 279 | 0.551 | 0.545 |
| 0.6-0.7 | 269 | 0.647 | 0.610 |
| 0.7-0.8 | 224 | 0.752 | 0.768 |
| 0.8-0.9 | 153 | 0.846 | 0.765 |
| 0.9-1.0 | 68 | 0.931 | 0.897 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 49 | 0.055 | 0.082 |
| 0.1-0.2 | 102 | 0.155 | 0.157 |
| 0.2-0.3 | 200 | 0.252 | 0.260 |
| 0.3-0.4 | 246 | 0.353 | 0.402 |
| 0.4-0.5 | 267 | 0.445 | 0.461 |
| 0.5-0.6 | 261 | 0.554 | 0.525 |
| 0.6-0.7 | 285 | 0.649 | 0.628 |
| 0.7-0.8 | 239 | 0.748 | 0.736 |
| 0.8-0.9 | 152 | 0.847 | 0.829 |
| 0.9-1.0 | 78 | 0.936 | 0.949 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 392 | +0.0072 ±0.0100 | +0.0020 ±0.0033 | +0.7 | 0.735 | 0.732 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 938 | -0.0003 ±0.0066 | -0.0011 ±0.0027 | -0.1 | 0.659 | 0.667 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| top-20 involved | 677 | -0.0022 ±0.0077 | -0.0013 ±0.0028 | -0.3 | 0.722 | 0.723 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| kalshi favorite 0.8-0.9 | 253 | -0.0077 ±0.0143 | -0.0031 ±0.0049 | -0.5 | 0.830 | 0.834 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| someone outside top-50 | 1380 | -0.0244 ±0.0060 | -0.0100 ±0.0024 | -4.1 | 0.665 | 0.684 | |
| tier: atp250 | 766 | -0.0368 ±0.0089 | -0.0141 ±0.0036 | -4.1 | 0.607 | 0.631 | |
| best rank 21-50 | 635 | -0.0335 ±0.0080 | -0.0136 ±0.0034 | -4.2 | 0.646 | 0.688 | |
| tour: wta | 931 | -0.0325 ±0.0076 | -0.0131 ±0.0032 | -4.3 | 0.671 | 0.684 | |
| big disagree (>=0.1) | 340 | -0.1055 ±0.0238 | -0.0410 ±0.0099 | -4.4 | 0.572 | 0.635 | |
| no top-20 player | 1202 | -0.0348 ±0.0066 | -0.0137 ±0.0028 | -5.3 | 0.619 | 0.643 | |
| surface: Hard | 1029 | -0.0402 ±0.0073 | -0.0151 ±0.0030 | -5.5 | 0.651 | 0.670 | |
| pred_source: live aligned | 941 | -0.0457 ±0.0076 | -0.0173 ±0.0031 | -6.0 | 0.652 | 0.677 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1879, mean |Δ|=0.0069, p95=0.0128, >0.05 in 55 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0660 (n=320, >0.05: 19) | 2026-10 p95=0.1324 (n=346, >0.05: 29) | 2026-11 p95=0.1040 (n=73, >0.05: 5)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1892, d_ll -0.0232 ±0.0050
- Unmatched qualifying markets: 720 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'Billie Jean King Cup Qualifiers Round': 56, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): AYNUR MOVLYAMOVA, Aishath Karin Saizan, Akasha Urhobo, Aleksandr Shevchenko, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Abualhaj, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Aylara Kakabayeva, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao
