# Model vs Kalshi — match-by-match scorecard

_Generated 2026-11-07T09:23:54Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 2395 | 2299 | 8 | 16 | 72 | 0 | 16 | 31 | 56 | 2026-05-03..2026-11-07 |
| wta | 2540 | 1539 | 3 | 918 | 80 | 0 | 12 | 24 | 33 | 2026-05-02..2026-11-07 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1903 | 0.6145 | 0.5915 | -0.0230 ±0.0050 | -0.0092 ±0.0020 | 0.658 | 0.673 |
| atp | 959 | 0.6271 | 0.6138 | -0.0133 ±0.0067 | -0.0052 ±0.0026 | 0.642 | 0.660 |
| wta | 944 | 0.6017 | 0.5689 | -0.0328 ±0.0075 | -0.0132 ±0.0031 | 0.675 | 0.688 |
| pooled/live_aligned | 965 | 0.6229 | 0.5779 | -0.0450 ±0.0075 | -0.0171 ±0.0030 | 0.658 | 0.680 |
| pooled/backtest | 938 | 0.6059 | 0.6056 | -0.0003 ±0.0066 | -0.0011 ±0.0027 | 0.659 | 0.667 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 965 | -0.0450 ±0.0075 | -0.0171 ±0.0030 | -6.0 | 0.658 | 0.680 | |
| pred_source: backtest | 938 | -0.0003 ±0.0066 | -0.0011 ±0.0027 | -0.1 | 0.659 | 0.667 | |
| top-20 involved | 688 | -0.0014 ±0.0076 | -0.0010 ±0.0027 | -0.2 | 0.723 | 0.723 | |
| no top-20 player | 1215 | -0.0352 ±0.0066 | -0.0139 ±0.0028 | -5.3 | 0.622 | 0.645 | |
| both inside top-50 | 507 | -0.0186 ±0.0094 | -0.0068 ±0.0039 | -2.0 | 0.632 | 0.638 | |
| someone outside top-50 | 1396 | -0.0246 ±0.0060 | -0.0101 ±0.0024 | -4.1 | 0.668 | 0.686 | |
| best rank 1-10 | 396 | +0.0082 ±0.0099 | +0.0024 ±0.0033 | +0.8 | 0.735 | 0.730 | |
| best rank 11-20 | 292 | -0.0144 ±0.0117 | -0.0056 ±0.0046 | -1.2 | 0.707 | 0.714 | |
| best rank 21-50 | 640 | -0.0335 ±0.0080 | -0.0135 ±0.0034 | -4.2 | 0.647 | 0.688 | |
| best rank 51-100 | 459 | -0.0321 ±0.0114 | -0.0125 ±0.0048 | -2.8 | 0.596 | 0.602 | |
| best rank 100+ | 116 | -0.0566 ±0.0280 | -0.0209 ±0.0119 | -2.0 | 0.586 | 0.582 | |
| kalshi favorite 0.5-0.6 | 529 | -0.0260 ±0.0083 | -0.0119 ±0.0038 | -3.1 | 0.502 | 0.534 | |
| kalshi favorite 0.6-0.7 | 543 | -0.0146 ±0.0084 | -0.0059 ±0.0037 | -1.7 | 0.613 | 0.617 | |
| kalshi favorite 0.7-0.8 | 446 | -0.0170 ±0.0106 | -0.0060 ±0.0042 | -1.6 | 0.728 | 0.738 | |
| kalshi favorite 0.8-0.9 | 257 | -0.0095 ±0.0142 | -0.0038 ±0.0049 | -0.7 | 0.833 | 0.837 | |
| kalshi favorite 0.9-1.0 | 128 | -0.0940 ±0.0304 | -0.0336 ±0.0100 | -3.1 | 0.906 | 0.938 | |
| surface: Hard | 1053 | -0.0397 ±0.0072 | -0.0149 ±0.0029 | -5.5 | 0.656 | 0.672 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 790 | -0.0361 ±0.0087 | -0.0138 ±0.0035 | -4.2 | 0.615 | 0.635 | |
| tier: atp500 | 278 | -0.0183 ±0.0117 | -0.0074 ±0.0051 | -1.6 | 0.644 | 0.653 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 324 | -0.0171 ±0.0108 | -0.0058 ±0.0046 | -1.6 | 0.659 | 0.673 | |
| round early (R128-R64) | 664 | -0.0206 ±0.0081 | -0.0084 ±0.0032 | -2.5 | 0.709 | 0.723 | |
| round late (QF-F) | 279 | -0.0119 ±0.0122 | -0.0050 ±0.0053 | -1.0 | 0.652 | 0.649 | |
| round mid (R32-R16) | 938 | -0.0284 ±0.0076 | -0.0111 ±0.0031 | -3.8 | 0.628 | 0.649 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 320 | -0.0429 ±0.0105 | -0.0177 ±0.0044 | -4.1 | 0.703 | 0.728 | |
| month 2026-10 | 346 | -0.0523 ±0.0162 | -0.0189 ±0.0065 | -3.2 | 0.639 | 0.669 | |
| month 2026-11 | 97 | -0.0752 ±0.0202 | -0.0275 ±0.0078 | -3.7 | 0.639 | 0.649 | |
| agree (<0.05) | 989 | -0.0010 ±0.0023 | -0.0008 ±0.0008 | -0.4 | 0.697 | 0.696 | |
| mild disagree (0.05-0.10) | 570 | -0.0115 ±0.0075 | -0.0046 ±0.0029 | -1.5 | 0.641 | 0.655 | |
| big disagree (>=0.1) | 344 | -0.1052 ±0.0235 | -0.0409 ±0.0098 | -4.5 | 0.577 | 0.640 | |
| tour: atp | 959 | -0.0133 ±0.0067 | -0.0052 ±0.0026 | -2.0 | 0.642 | 0.660 | |
| tour: wta | 944 | -0.0328 ±0.0075 | -0.0132 ±0.0031 | -4.4 | 0.675 | 0.688 | |

When they disagree by >= 0.1: model closer to the outcome in **128/344** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 22 | 0.072 | 0.182 |
| 0.1-0.2 | 123 | 0.153 | 0.171 |
| 0.2-0.3 | 175 | 0.250 | 0.257 |
| 0.3-0.4 | 256 | 0.352 | 0.379 |
| 0.4-0.5 | 318 | 0.450 | 0.484 |
| 0.5-0.6 | 285 | 0.551 | 0.551 |
| 0.6-0.7 | 275 | 0.647 | 0.618 |
| 0.7-0.8 | 226 | 0.752 | 0.765 |
| 0.8-0.9 | 154 | 0.846 | 0.766 |
| 0.9-1.0 | 69 | 0.931 | 0.899 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 49 | 0.055 | 0.082 |
| 0.1-0.2 | 104 | 0.155 | 0.154 |
| 0.2-0.3 | 204 | 0.252 | 0.260 |
| 0.3-0.4 | 247 | 0.353 | 0.401 |
| 0.4-0.5 | 270 | 0.445 | 0.463 |
| 0.5-0.6 | 263 | 0.554 | 0.525 |
| 0.6-0.7 | 292 | 0.649 | 0.637 |
| 0.7-0.8 | 242 | 0.748 | 0.736 |
| 0.8-0.9 | 154 | 0.846 | 0.831 |
| 0.9-1.0 | 78 | 0.936 | 0.949 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 396 | +0.0082 ±0.0099 | +0.0024 ±0.0033 | +0.8 | 0.735 | 0.730 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 938 | -0.0003 ±0.0066 | -0.0011 ±0.0027 | -0.1 | 0.659 | 0.667 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| top-20 involved | 688 | -0.0014 ±0.0076 | -0.0010 ±0.0027 | -0.2 | 0.723 | 0.723 | |
| agree (<0.05) | 989 | -0.0010 ±0.0023 | -0.0008 ±0.0008 | -0.4 | 0.697 | 0.696 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| someone outside top-50 | 1396 | -0.0246 ±0.0060 | -0.0101 ±0.0024 | -4.1 | 0.668 | 0.686 | |
| tier: atp250 | 790 | -0.0361 ±0.0087 | -0.0138 ±0.0035 | -4.2 | 0.615 | 0.635 | |
| best rank 21-50 | 640 | -0.0335 ±0.0080 | -0.0135 ±0.0034 | -4.2 | 0.647 | 0.688 | |
| tour: wta | 944 | -0.0328 ±0.0075 | -0.0132 ±0.0031 | -4.4 | 0.675 | 0.688 | |
| big disagree (>=0.1) | 344 | -0.1052 ±0.0235 | -0.0409 ±0.0098 | -4.5 | 0.577 | 0.640 | |
| no top-20 player | 1215 | -0.0352 ±0.0066 | -0.0139 ±0.0028 | -5.3 | 0.622 | 0.645 | |
| surface: Hard | 1053 | -0.0397 ±0.0072 | -0.0149 ±0.0029 | -5.5 | 0.656 | 0.672 | |
| pred_source: live aligned | 965 | -0.0450 ±0.0075 | -0.0171 ±0.0030 | -6.0 | 0.658 | 0.680 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1903, mean |Δ|=0.0069, p95=0.0129, >0.05 in 55 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0660 (n=320, >0.05: 19) | 2026-10 p95=0.1324 (n=346, >0.05: 29) | 2026-11 p95=0.0520 (n=97, >0.05: 5)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1917, d_ll -0.0230 ±0.0050
- Unmatched qualifying markets: 720 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'Billie Jean King Cup Qualifiers Round': 56, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): AYNUR MOVLYAMOVA, Aishath Karin Saizan, Akasha Urhobo, Aleksandr Shevchenko, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Abualhaj, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Aylara Kakabayeva, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao
