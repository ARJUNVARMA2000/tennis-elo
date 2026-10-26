# Model vs Kalshi — match-by-match scorecard

_Generated 2026-10-26T06:59:07Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 2275 | 2165 | 26 | 15 | 68 | 1 | 15 | 26 | 51 | 2026-05-03..2026-10-26 |
| wta | 2419 | 1427 | 89 | 830 | 73 | 0 | 10 | 22 | 37 | 2026-05-02..2026-10-27 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1717 | 0.6111 | 0.5942 | -0.0169 ±0.0051 | -0.0070 ±0.0021 | 0.659 | 0.671 |
| atp | 856 | 0.6262 | 0.6137 | -0.0125 ±0.0071 | -0.0052 ±0.0028 | 0.641 | 0.656 |
| wta | 861 | 0.5962 | 0.5750 | -0.0213 ±0.0073 | -0.0088 ±0.0030 | 0.676 | 0.686 |
| pooled/live_aligned | 781 | 0.6182 | 0.5803 | -0.0379 ±0.0078 | -0.0145 ±0.0032 | 0.658 | 0.676 |
| pooled/backtest | 936 | 0.6053 | 0.6059 | +0.0006 ±0.0066 | -0.0008 ±0.0027 | 0.659 | 0.667 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 781 | -0.0379 ±0.0078 | -0.0145 ±0.0032 | -4.8 | 0.658 | 0.676 | |
| pred_source: backtest | 936 | +0.0006 ±0.0066 | -0.0008 ±0.0027 | +0.1 | 0.659 | 0.667 | |
| top-20 involved | 611 | +0.0006 ±0.0079 | -0.0009 ±0.0029 | +0.1 | 0.721 | 0.721 | |
| no top-20 player | 1106 | -0.0265 ±0.0065 | -0.0104 ±0.0028 | -4.1 | 0.624 | 0.644 | |
| both inside top-50 | 441 | -0.0158 ±0.0101 | -0.0062 ±0.0043 | -1.6 | 0.638 | 0.641 | |
| someone outside top-50 | 1276 | -0.0173 ±0.0059 | -0.0073 ±0.0024 | -2.9 | 0.666 | 0.682 | |
| best rank 1-10 | 359 | +0.0107 ±0.0102 | +0.0026 ±0.0035 | +1.0 | 0.735 | 0.730 | |
| best rank 11-20 | 252 | -0.0139 ±0.0124 | -0.0061 ±0.0051 | -1.1 | 0.700 | 0.708 | |
| best rank 21-50 | 597 | -0.0294 ±0.0080 | -0.0118 ±0.0035 | -3.7 | 0.653 | 0.690 | |
| best rank 51-100 | 416 | -0.0208 ±0.0110 | -0.0079 ±0.0046 | -1.9 | 0.590 | 0.588 | |
| best rank 100+ | 93 | -0.0342 ±0.0313 | -0.0123 ±0.0134 | -1.1 | 0.591 | 0.597 | |
| kalshi favorite 0.5-0.6 | 487 | -0.0242 ±0.0084 | -0.0113 ±0.0039 | -2.9 | 0.500 | 0.535 | |
| kalshi favorite 0.6-0.7 | 482 | -0.0111 ±0.0089 | -0.0042 ±0.0040 | -1.2 | 0.612 | 0.612 | |
| kalshi favorite 0.7-0.8 | 402 | -0.0101 ±0.0100 | -0.0037 ±0.0041 | -1.0 | 0.735 | 0.741 | |
| kalshi favorite 0.8-0.9 | 229 | -0.0033 ±0.0154 | -0.0019 ±0.0054 | -0.2 | 0.825 | 0.830 | |
| kalshi favorite 0.9-1.0 | 117 | -0.0606 ±0.0296 | -0.0219 ±0.0092 | -2.0 | 0.923 | 0.932 | |
| surface: Hard | 867 | -0.0312 ±0.0075 | -0.0118 ±0.0031 | -4.2 | 0.656 | 0.668 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 615 | -0.0263 ±0.0095 | -0.0103 ±0.0039 | -2.8 | 0.607 | 0.623 | |
| tier: atp500 | 267 | -0.0103 ±0.0106 | -0.0044 ±0.0047 | -1.0 | 0.637 | 0.642 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 324 | -0.0171 ±0.0108 | -0.0058 ±0.0046 | -1.6 | 0.659 | 0.673 | |
| round early (R128-R64) | 646 | -0.0208 ±0.0083 | -0.0085 ±0.0032 | -2.5 | 0.710 | 0.723 | |
| round late (QF-F) | 245 | -0.0024 ±0.0114 | -0.0013 ±0.0051 | -0.2 | 0.641 | 0.637 | |
| round mid (R32-R16) | 804 | -0.0185 ±0.0078 | -0.0077 ±0.0032 | -2.4 | 0.627 | 0.644 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 319 | -0.0405 ±0.0103 | -0.0168 ±0.0043 | -3.9 | 0.705 | 0.730 | |
| month 2026-10 | 258 | -0.0445 ±0.0176 | -0.0158 ±0.0072 | -2.5 | 0.624 | 0.641 | |
| agree (<0.05) | 913 | -0.0008 ±0.0024 | -0.0006 ±0.0008 | -0.3 | 0.699 | 0.697 | |
| mild disagree (0.05-0.10) | 513 | -0.0106 ±0.0078 | -0.0047 ±0.0030 | -1.4 | 0.635 | 0.654 | |
| big disagree (>=0.1) | 291 | -0.0785 ±0.0252 | -0.0310 ±0.0107 | -3.1 | 0.576 | 0.622 | |
| tour: atp | 856 | -0.0125 ±0.0071 | -0.0052 ±0.0028 | -1.8 | 0.641 | 0.656 | |
| tour: wta | 861 | -0.0213 ±0.0073 | -0.0088 ±0.0030 | -2.9 | 0.676 | 0.686 | |

When they disagree by >= 0.1: model closer to the outcome in **112/291** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 19 | 0.068 | 0.158 |
| 0.1-0.2 | 110 | 0.152 | 0.191 |
| 0.2-0.3 | 157 | 0.251 | 0.255 |
| 0.3-0.4 | 225 | 0.353 | 0.378 |
| 0.4-0.5 | 294 | 0.451 | 0.476 |
| 0.5-0.6 | 264 | 0.551 | 0.542 |
| 0.6-0.7 | 249 | 0.648 | 0.614 |
| 0.7-0.8 | 205 | 0.752 | 0.776 |
| 0.8-0.9 | 133 | 0.845 | 0.782 |
| 0.9-1.0 | 61 | 0.932 | 0.918 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 44 | 0.058 | 0.091 |
| 0.1-0.2 | 91 | 0.154 | 0.165 |
| 0.2-0.3 | 182 | 0.254 | 0.258 |
| 0.3-0.4 | 222 | 0.354 | 0.401 |
| 0.4-0.5 | 249 | 0.445 | 0.462 |
| 0.5-0.6 | 242 | 0.555 | 0.525 |
| 0.6-0.7 | 256 | 0.649 | 0.629 |
| 0.7-0.8 | 220 | 0.749 | 0.741 |
| 0.8-0.9 | 139 | 0.846 | 0.827 |
| 0.9-1.0 | 72 | 0.934 | 0.944 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 359 | +0.0107 ±0.0102 | +0.0026 ±0.0035 | +1.0 | 0.735 | 0.730 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 936 | +0.0006 ±0.0066 | -0.0008 ±0.0027 | +0.1 | 0.659 | 0.667 | |
| top-20 involved | 611 | +0.0006 ±0.0079 | -0.0009 ±0.0029 | +0.1 | 0.721 | 0.721 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| round late (QF-F) | 245 | -0.0024 ±0.0114 | -0.0013 ±0.0051 | -0.2 | 0.641 | 0.637 | |
| kalshi favorite 0.8-0.9 | 229 | -0.0033 ±0.0154 | -0.0019 ±0.0054 | -0.2 | 0.825 | 0.830 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| tour: wta | 861 | -0.0213 ±0.0073 | -0.0088 ±0.0030 | -2.9 | 0.676 | 0.686 | |
| someone outside top-50 | 1276 | -0.0173 ±0.0059 | -0.0073 ±0.0024 | -2.9 | 0.666 | 0.682 | |
| big disagree (>=0.1) | 291 | -0.0785 ±0.0252 | -0.0310 ±0.0107 | -3.1 | 0.576 | 0.622 | |
| best rank 21-50 | 597 | -0.0294 ±0.0080 | -0.0118 ±0.0035 | -3.7 | 0.653 | 0.690 | |
| month 2026-09 | 319 | -0.0405 ±0.0103 | -0.0168 ±0.0043 | -3.9 | 0.705 | 0.730 | |
| no top-20 player | 1106 | -0.0265 ±0.0065 | -0.0104 ±0.0028 | -4.1 | 0.624 | 0.644 | |
| surface: Hard | 867 | -0.0312 ±0.0075 | -0.0118 ±0.0031 | -4.2 | 0.656 | 0.668 | |
| pred_source: live aligned | 781 | -0.0379 ±0.0078 | -0.0145 ±0.0032 | -4.8 | 0.658 | 0.676 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1717, mean |Δ|=0.0063, p95=0.0101, >0.05 in 44 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0666 (n=319, >0.05: 19) | 2026-10 p95=0.1434 (n=258, >0.05: 23)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1724, d_ll -0.0170 ±0.0051
- Unmatched qualifying markets: 660 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'Billie Jean King Cup Qualifiers Round': 26, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'WTA Seoul': 3}
- Unmatched Kalshi names, main draw (40): AYNUR MOVLYAMOVA, Aishath Karin Saizan, Akasha Urhobo, Aleksandr Shevchenko, Alevtina Ibragimova, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Abualhaj, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Aylara Kakabayeva, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee
