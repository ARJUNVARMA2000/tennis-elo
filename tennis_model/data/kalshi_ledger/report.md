# Model vs Kalshi — match-by-match scorecard

_Generated 2026-11-06T08:37:30Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 2387 | 2295 | 4 | 16 | 72 | 0 | 16 | 31 | 52 | 2026-05-03..2026-11-06 |
| wta | 2536 | 1531 | 7 | 918 | 80 | 0 | 12 | 23 | 39 | 2026-05-02..2026-11-06 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1892 | 0.6151 | 0.5922 | -0.0229 ±0.0050 | -0.0092 ±0.0020 | 0.657 | 0.673 |
| atp | 955 | 0.6278 | 0.6143 | -0.0135 ±0.0067 | -0.0053 ±0.0026 | 0.641 | 0.659 |
| wta | 937 | 0.6022 | 0.5697 | -0.0325 ±0.0076 | -0.0131 ±0.0031 | 0.673 | 0.686 |
| pooled/live_aligned | 954 | 0.6242 | 0.5791 | -0.0451 ±0.0075 | -0.0171 ±0.0031 | 0.655 | 0.678 |
| pooled/backtest | 938 | 0.6059 | 0.6056 | -0.0003 ±0.0066 | -0.0011 ±0.0027 | 0.659 | 0.667 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 954 | -0.0451 ±0.0075 | -0.0171 ±0.0031 | -6.0 | 0.655 | 0.678 | |
| pred_source: backtest | 938 | -0.0003 ±0.0066 | -0.0011 ±0.0027 | -0.1 | 0.659 | 0.667 | |
| top-20 involved | 683 | -0.0019 ±0.0076 | -0.0012 ±0.0027 | -0.2 | 0.723 | 0.724 | |
| no top-20 player | 1209 | -0.0348 ±0.0066 | -0.0137 ±0.0028 | -5.3 | 0.620 | 0.644 | |
| both inside top-50 | 504 | -0.0192 ±0.0094 | -0.0071 ±0.0039 | -2.0 | 0.630 | 0.638 | |
| someone outside top-50 | 1388 | -0.0243 ±0.0060 | -0.0099 ±0.0024 | -4.1 | 0.667 | 0.685 | |
| best rank 1-10 | 394 | +0.0075 ±0.0100 | +0.0021 ±0.0033 | +0.8 | 0.734 | 0.731 | |
| best rank 11-20 | 289 | -0.0146 ±0.0118 | -0.0056 ±0.0046 | -1.2 | 0.708 | 0.715 | |
| best rank 21-50 | 638 | -0.0335 ±0.0080 | -0.0135 ±0.0034 | -4.2 | 0.646 | 0.687 | |
| best rank 51-100 | 456 | -0.0311 ±0.0115 | -0.0121 ±0.0048 | -2.7 | 0.593 | 0.600 | |
| best rank 100+ | 115 | -0.0569 ±0.0282 | -0.0210 ±0.0120 | -2.0 | 0.583 | 0.578 | |
| kalshi favorite 0.5-0.6 | 528 | -0.0263 ±0.0083 | -0.0121 ±0.0038 | -3.2 | 0.501 | 0.535 | |
| kalshi favorite 0.6-0.7 | 538 | -0.0143 ±0.0084 | -0.0058 ±0.0038 | -1.7 | 0.610 | 0.613 | |
| kalshi favorite 0.7-0.8 | 443 | -0.0175 ±0.0107 | -0.0062 ±0.0042 | -1.6 | 0.728 | 0.738 | |
| kalshi favorite 0.8-0.9 | 255 | -0.0079 ±0.0142 | -0.0032 ±0.0049 | -0.6 | 0.831 | 0.835 | |
| kalshi favorite 0.9-1.0 | 128 | -0.0940 ±0.0304 | -0.0336 ±0.0100 | -3.1 | 0.906 | 0.938 | |
| surface: Hard | 1042 | -0.0397 ±0.0072 | -0.0149 ±0.0029 | -5.5 | 0.654 | 0.671 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 779 | -0.0361 ±0.0088 | -0.0138 ±0.0036 | -4.1 | 0.611 | 0.633 | |
| tier: atp500 | 278 | -0.0183 ±0.0117 | -0.0074 ±0.0051 | -1.6 | 0.644 | 0.653 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 324 | -0.0171 ±0.0108 | -0.0058 ±0.0046 | -1.6 | 0.659 | 0.673 | |
| round early (R128-R64) | 664 | -0.0206 ±0.0081 | -0.0084 ±0.0032 | -2.5 | 0.709 | 0.723 | |
| round late (QF-F) | 268 | -0.0110 ±0.0126 | -0.0046 ±0.0054 | -0.9 | 0.642 | 0.642 | |
| round mid (R32-R16) | 938 | -0.0284 ±0.0076 | -0.0111 ±0.0031 | -3.8 | 0.628 | 0.649 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 320 | -0.0429 ±0.0105 | -0.0177 ±0.0044 | -4.1 | 0.703 | 0.728 | |
| month 2026-10 | 346 | -0.0523 ±0.0162 | -0.0189 ±0.0065 | -3.2 | 0.639 | 0.669 | |
| month 2026-11 | 86 | -0.0806 ±0.0221 | -0.0292 ±0.0084 | -3.7 | 0.605 | 0.628 | |
| agree (<0.05) | 984 | -0.0011 ±0.0023 | -0.0008 ±0.0008 | -0.5 | 0.696 | 0.695 | |
| mild disagree (0.05-0.10) | 566 | -0.0113 ±0.0075 | -0.0045 ±0.0029 | -1.5 | 0.639 | 0.655 | |
| big disagree (>=0.1) | 342 | -0.1051 ±0.0236 | -0.0408 ±0.0099 | -4.4 | 0.575 | 0.637 | |
| tour: atp | 955 | -0.0135 ±0.0067 | -0.0053 ±0.0026 | -2.0 | 0.641 | 0.659 | |
| tour: wta | 937 | -0.0325 ±0.0076 | -0.0131 ±0.0031 | -4.3 | 0.673 | 0.686 | |

When they disagree by >= 0.1: model closer to the outcome in **127/342** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 22 | 0.072 | 0.182 |
| 0.1-0.2 | 122 | 0.152 | 0.172 |
| 0.2-0.3 | 175 | 0.250 | 0.257 |
| 0.3-0.4 | 254 | 0.352 | 0.378 |
| 0.4-0.5 | 317 | 0.450 | 0.486 |
| 0.5-0.6 | 282 | 0.551 | 0.546 |
| 0.6-0.7 | 272 | 0.647 | 0.614 |
| 0.7-0.8 | 226 | 0.752 | 0.765 |
| 0.8-0.9 | 153 | 0.846 | 0.765 |
| 0.9-1.0 | 69 | 0.931 | 0.899 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 49 | 0.055 | 0.082 |
| 0.1-0.2 | 102 | 0.155 | 0.157 |
| 0.2-0.3 | 203 | 0.252 | 0.256 |
| 0.3-0.4 | 246 | 0.353 | 0.402 |
| 0.4-0.5 | 269 | 0.445 | 0.461 |
| 0.5-0.6 | 263 | 0.554 | 0.525 |
| 0.6-0.7 | 288 | 0.649 | 0.632 |
| 0.7-0.8 | 240 | 0.748 | 0.733 |
| 0.8-0.9 | 154 | 0.846 | 0.831 |
| 0.9-1.0 | 78 | 0.936 | 0.949 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 394 | +0.0075 ±0.0100 | +0.0021 ±0.0033 | +0.8 | 0.734 | 0.731 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 938 | -0.0003 ±0.0066 | -0.0011 ±0.0027 | -0.1 | 0.659 | 0.667 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| top-20 involved | 683 | -0.0019 ±0.0076 | -0.0012 ±0.0027 | -0.2 | 0.723 | 0.724 | |
| agree (<0.05) | 984 | -0.0011 ±0.0023 | -0.0008 ±0.0008 | -0.5 | 0.696 | 0.695 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| month 2026-09 | 320 | -0.0429 ±0.0105 | -0.0177 ±0.0044 | -4.1 | 0.703 | 0.728 | |
| tier: atp250 | 779 | -0.0361 ±0.0088 | -0.0138 ±0.0036 | -4.1 | 0.611 | 0.633 | |
| best rank 21-50 | 638 | -0.0335 ±0.0080 | -0.0135 ±0.0034 | -4.2 | 0.646 | 0.687 | |
| tour: wta | 937 | -0.0325 ±0.0076 | -0.0131 ±0.0031 | -4.3 | 0.673 | 0.686 | |
| big disagree (>=0.1) | 342 | -0.1051 ±0.0236 | -0.0408 ±0.0099 | -4.4 | 0.575 | 0.637 | |
| no top-20 player | 1209 | -0.0348 ±0.0066 | -0.0137 ±0.0028 | -5.3 | 0.620 | 0.644 | |
| surface: Hard | 1042 | -0.0397 ±0.0072 | -0.0149 ±0.0029 | -5.5 | 0.654 | 0.671 | |
| pred_source: live aligned | 954 | -0.0451 ±0.0075 | -0.0171 ±0.0031 | -6.0 | 0.655 | 0.678 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1892, mean |Δ|=0.0069, p95=0.0127, >0.05 in 55 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0660 (n=320, >0.05: 19) | 2026-10 p95=0.1324 (n=346, >0.05: 29) | 2026-11 p95=0.0769 (n=86, >0.05: 5)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1905, d_ll -0.0231 ±0.0050
- Unmatched qualifying markets: 720 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'Billie Jean King Cup Qualifiers Round': 56, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): AYNUR MOVLYAMOVA, Aishath Karin Saizan, Akasha Urhobo, Aleksandr Shevchenko, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Abualhaj, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Aylara Kakabayeva, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao
