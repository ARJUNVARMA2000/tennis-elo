# Model vs Kalshi — match-by-match scorecard

_Generated 2026-10-30T07:56:36Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 2305 | 2212 | 8 | 16 | 69 | 0 | 15 | 28 | 53 | 2026-05-03..2026-10-30 |
| wta | 2444 | 1471 | 6 | 894 | 73 | 0 | 12 | 22 | 36 | 2026-05-02..2026-10-31 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1788 | 0.6110 | 0.5914 | -0.0197 ±0.0051 | -0.0080 ±0.0021 | 0.659 | 0.674 |
| atp | 901 | 0.6225 | 0.6107 | -0.0118 ±0.0069 | -0.0048 ±0.0027 | 0.645 | 0.663 |
| wta | 887 | 0.5995 | 0.5718 | -0.0277 ±0.0076 | -0.0112 ±0.0032 | 0.674 | 0.685 |
| pooled/live_aligned | 851 | 0.6162 | 0.5752 | -0.0410 ±0.0079 | -0.0156 ±0.0032 | 0.660 | 0.683 |
| pooled/backtest | 937 | 0.6064 | 0.6061 | -0.0002 ±0.0067 | -0.0011 ±0.0027 | 0.658 | 0.666 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 851 | -0.0410 ±0.0079 | -0.0156 ±0.0032 | -5.2 | 0.660 | 0.683 | |
| pred_source: backtest | 937 | -0.0002 ±0.0067 | -0.0011 ±0.0027 | -0.0 | 0.658 | 0.666 | |
| top-20 involved | 646 | -0.0008 ±0.0078 | -0.0011 ±0.0028 | -0.1 | 0.725 | 0.727 | |
| no top-20 player | 1142 | -0.0303 ±0.0067 | -0.0119 ±0.0029 | -4.5 | 0.622 | 0.644 | |
| both inside top-50 | 466 | -0.0162 ±0.0099 | -0.0061 ±0.0041 | -1.6 | 0.641 | 0.647 | |
| someone outside top-50 | 1322 | -0.0209 ±0.0060 | -0.0086 ±0.0024 | -3.5 | 0.666 | 0.684 | |
| best rank 1-10 | 376 | +0.0097 ±0.0102 | +0.0025 ±0.0034 | +1.0 | 0.739 | 0.737 | |
| best rank 11-20 | 270 | -0.0154 ±0.0123 | -0.0062 ±0.0048 | -1.3 | 0.706 | 0.713 | |
| best rank 21-50 | 612 | -0.0308 ±0.0082 | -0.0124 ±0.0035 | -3.8 | 0.652 | 0.693 | |
| best rank 51-100 | 434 | -0.0264 ±0.0114 | -0.0101 ±0.0048 | -2.3 | 0.589 | 0.589 | |
| best rank 100+ | 96 | -0.0446 ±0.0314 | -0.0166 ±0.0134 | -1.4 | 0.583 | 0.589 | |
| kalshi favorite 0.5-0.6 | 501 | -0.0261 ±0.0086 | -0.0121 ±0.0040 | -3.1 | 0.502 | 0.538 | |
| kalshi favorite 0.6-0.7 | 502 | -0.0119 ±0.0088 | -0.0046 ±0.0039 | -1.4 | 0.610 | 0.614 | |
| kalshi favorite 0.7-0.8 | 418 | -0.0145 ±0.0109 | -0.0051 ±0.0043 | -1.3 | 0.731 | 0.739 | |
| kalshi favorite 0.8-0.9 | 244 | -0.0018 ±0.0145 | -0.0016 ±0.0051 | -0.1 | 0.832 | 0.836 | |
| kalshi favorite 0.9-1.0 | 123 | -0.0774 ±0.0294 | -0.0275 ±0.0093 | -2.6 | 0.919 | 0.935 | |
| surface: Hard | 938 | -0.0354 ±0.0076 | -0.0133 ±0.0031 | -4.7 | 0.658 | 0.674 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 676 | -0.0290 ±0.0094 | -0.0112 ±0.0038 | -3.1 | 0.611 | 0.632 | |
| tier: atp500 | 277 | -0.0194 ±0.0117 | -0.0080 ±0.0051 | -1.7 | 0.643 | 0.652 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 324 | -0.0171 ±0.0108 | -0.0058 ±0.0046 | -1.6 | 0.659 | 0.673 | |
| round early (R128-R64) | 646 | -0.0208 ±0.0083 | -0.0085 ±0.0032 | -2.5 | 0.710 | 0.723 | |
| round late (QF-F) | 247 | -0.0072 ±0.0118 | -0.0029 ±0.0052 | -0.6 | 0.644 | 0.640 | |
| round mid (R32-R16) | 873 | -0.0227 ±0.0078 | -0.0092 ±0.0032 | -2.9 | 0.631 | 0.651 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 320 | -0.0429 ±0.0105 | -0.0177 ±0.0044 | -4.1 | 0.703 | 0.728 | |
| month 2026-10 | 328 | -0.0513 ±0.0163 | -0.0182 ±0.0066 | -3.1 | 0.637 | 0.666 | |
| agree (<0.05) | 945 | -0.0006 ±0.0024 | -0.0006 ±0.0008 | -0.2 | 0.699 | 0.699 | |
| mild disagree (0.05-0.10) | 525 | -0.0077 ±0.0077 | -0.0035 ±0.0030 | -1.0 | 0.639 | 0.656 | |
| big disagree (>=0.1) | 318 | -0.0961 ±0.0246 | -0.0372 ±0.0103 | -3.9 | 0.574 | 0.629 | |
| tour: atp | 901 | -0.0118 ±0.0069 | -0.0048 ±0.0027 | -1.7 | 0.645 | 0.663 | |
| tour: wta | 887 | -0.0277 ±0.0076 | -0.0112 ±0.0032 | -3.6 | 0.674 | 0.685 | |

When they disagree by >= 0.1: model closer to the outcome in **120/318** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 21 | 0.071 | 0.190 |
| 0.1-0.2 | 114 | 0.152 | 0.184 |
| 0.2-0.3 | 163 | 0.250 | 0.258 |
| 0.3-0.4 | 236 | 0.353 | 0.377 |
| 0.4-0.5 | 304 | 0.451 | 0.480 |
| 0.5-0.6 | 272 | 0.551 | 0.548 |
| 0.6-0.7 | 255 | 0.648 | 0.612 |
| 0.7-0.8 | 211 | 0.751 | 0.777 |
| 0.8-0.9 | 146 | 0.845 | 0.781 |
| 0.9-1.0 | 66 | 0.931 | 0.909 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 46 | 0.057 | 0.087 |
| 0.1-0.2 | 98 | 0.155 | 0.163 |
| 0.2-0.3 | 188 | 0.253 | 0.266 |
| 0.3-0.4 | 232 | 0.353 | 0.401 |
| 0.4-0.5 | 254 | 0.445 | 0.457 |
| 0.5-0.6 | 251 | 0.554 | 0.526 |
| 0.6-0.7 | 266 | 0.649 | 0.632 |
| 0.7-0.8 | 230 | 0.748 | 0.743 |
| 0.8-0.9 | 147 | 0.847 | 0.837 |
| 0.9-1.0 | 76 | 0.935 | 0.947 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 376 | +0.0097 ±0.0102 | +0.0025 ±0.0034 | +1.0 | 0.739 | 0.737 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 937 | -0.0002 ±0.0067 | -0.0011 ±0.0027 | -0.0 | 0.658 | 0.666 | |
| top-20 involved | 646 | -0.0008 ±0.0078 | -0.0011 ±0.0028 | -0.1 | 0.725 | 0.727 | |
| kalshi favorite 0.8-0.9 | 244 | -0.0018 ±0.0145 | -0.0016 ±0.0051 | -0.1 | 0.832 | 0.836 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| agree (<0.05) | 945 | -0.0006 ±0.0024 | -0.0006 ±0.0008 | -0.2 | 0.699 | 0.699 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| someone outside top-50 | 1322 | -0.0209 ±0.0060 | -0.0086 ±0.0024 | -3.5 | 0.666 | 0.684 | |
| tour: wta | 887 | -0.0277 ±0.0076 | -0.0112 ±0.0032 | -3.6 | 0.674 | 0.685 | |
| best rank 21-50 | 612 | -0.0308 ±0.0082 | -0.0124 ±0.0035 | -3.8 | 0.652 | 0.693 | |
| big disagree (>=0.1) | 318 | -0.0961 ±0.0246 | -0.0372 ±0.0103 | -3.9 | 0.574 | 0.629 | |
| month 2026-09 | 320 | -0.0429 ±0.0105 | -0.0177 ±0.0044 | -4.1 | 0.703 | 0.728 | |
| no top-20 player | 1142 | -0.0303 ±0.0067 | -0.0119 ±0.0029 | -4.5 | 0.622 | 0.644 | |
| surface: Hard | 938 | -0.0354 ±0.0076 | -0.0133 ±0.0031 | -4.7 | 0.658 | 0.674 | |
| pred_source: live aligned | 851 | -0.0410 ±0.0079 | -0.0156 ±0.0032 | -5.2 | 0.660 | 0.683 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1788, mean |Δ|=0.0066, p95=0.0123, >0.05 in 49 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0660 (n=320, >0.05: 19) | 2026-10 p95=0.1318 (n=328, >0.05: 28)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1797, d_ll -0.0197 ±0.0051
- Unmatched qualifying markets: 696 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'Billie Jean King Cup Qualifiers Round': 56, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): AYNUR MOVLYAMOVA, Aishath Karin Saizan, Akasha Urhobo, Aleksandr Shevchenko, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Abualhaj, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Aylara Kakabayeva, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao
