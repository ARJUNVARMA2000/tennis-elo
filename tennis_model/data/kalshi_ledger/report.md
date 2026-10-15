# Model vs Kalshi — match-by-match scorecard

_Generated 2026-10-15T11:03:39Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 2098 | 2020 | 3 | 13 | 62 | 0 | 12 | 24 | 46 | 2026-05-03..2026-10-16 |
| wta | 2190 | 1354 | 6 | 767 | 63 | 0 | 10 | 16 | 33 | 2026-05-02..2026-10-16 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1604 | 0.6076 | 0.5912 | -0.0165 ±0.0052 | -0.0069 ±0.0021 | 0.663 | 0.677 |
| atp | 775 | 0.6191 | 0.6091 | -0.0100 ±0.0073 | -0.0043 ±0.0029 | 0.652 | 0.668 |
| wta | 829 | 0.5969 | 0.5744 | -0.0225 ±0.0074 | -0.0093 ±0.0031 | 0.673 | 0.685 |
| pooled/live_aligned | 668 | 0.6109 | 0.5706 | -0.0404 ±0.0082 | -0.0154 ±0.0034 | 0.668 | 0.690 |
| pooled/backtest | 936 | 0.6053 | 0.6059 | +0.0006 ±0.0066 | -0.0008 ±0.0027 | 0.659 | 0.667 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 668 | -0.0404 ±0.0082 | -0.0154 ±0.0034 | -4.9 | 0.668 | 0.690 | |
| pred_source: backtest | 936 | +0.0006 ±0.0066 | -0.0008 ±0.0027 | +0.1 | 0.659 | 0.667 | |
| top-20 involved | 572 | -0.0018 ±0.0082 | -0.0021 ±0.0030 | -0.2 | 0.719 | 0.723 | |
| no top-20 player | 1032 | -0.0246 ±0.0066 | -0.0095 ±0.0028 | -3.7 | 0.631 | 0.651 | |
| both inside top-50 | 409 | -0.0216 ±0.0103 | -0.0089 ±0.0043 | -2.1 | 0.639 | 0.649 | |
| someone outside top-50 | 1195 | -0.0147 ±0.0060 | -0.0062 ±0.0024 | -2.4 | 0.671 | 0.686 | |
| best rank 1-10 | 341 | +0.0099 ±0.0106 | +0.0021 ±0.0036 | +0.9 | 0.736 | 0.733 | |
| best rank 11-20 | 231 | -0.0191 ±0.0129 | -0.0082 ±0.0052 | -1.5 | 0.695 | 0.708 | |
| best rank 21-50 | 553 | -0.0277 ±0.0081 | -0.0112 ±0.0035 | -3.4 | 0.656 | 0.698 | |
| best rank 51-100 | 391 | -0.0176 ±0.0112 | -0.0064 ±0.0047 | -1.6 | 0.602 | 0.595 | |
| best rank 100+ | 88 | -0.0357 ±0.0320 | -0.0128 ±0.0136 | -1.1 | 0.602 | 0.608 | |
| kalshi favorite 0.5-0.6 | 459 | -0.0231 ±0.0086 | -0.0108 ±0.0040 | -2.7 | 0.504 | 0.544 | |
| kalshi favorite 0.6-0.7 | 442 | -0.0113 ±0.0091 | -0.0042 ±0.0041 | -1.2 | 0.615 | 0.615 | |
| kalshi favorite 0.7-0.8 | 369 | -0.0088 ±0.0097 | -0.0034 ±0.0039 | -0.9 | 0.738 | 0.745 | |
| kalshi favorite 0.8-0.9 | 222 | -0.0027 ±0.0158 | -0.0017 ±0.0055 | -0.2 | 0.829 | 0.833 | |
| kalshi favorite 0.9-1.0 | 112 | -0.0624 ±0.0309 | -0.0227 ±0.0096 | -2.0 | 0.920 | 0.929 | |
| surface: Hard | 754 | -0.0324 ±0.0078 | -0.0122 ±0.0032 | -4.1 | 0.664 | 0.679 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 527 | -0.0238 ±0.0102 | -0.0092 ±0.0041 | -2.3 | 0.615 | 0.632 | |
| tier: atp500 | 250 | -0.0149 ±0.0103 | -0.0067 ±0.0046 | -1.4 | 0.628 | 0.642 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 316 | -0.0176 ±0.0110 | -0.0058 ±0.0047 | -1.6 | 0.657 | 0.671 | |
| round early (R128-R64) | 646 | -0.0208 ±0.0083 | -0.0085 ±0.0032 | -2.5 | 0.710 | 0.723 | |
| round late (QF-F) | 207 | -0.0088 ±0.0112 | -0.0046 ±0.0050 | -0.8 | 0.638 | 0.647 | |
| round mid (R32-R16) | 729 | -0.0151 ±0.0081 | -0.0062 ±0.0033 | -1.9 | 0.633 | 0.648 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 319 | -0.0405 ±0.0103 | -0.0168 ±0.0043 | -3.9 | 0.705 | 0.730 | |
| month 2026-10 | 145 | -0.0612 ±0.0255 | -0.0209 ±0.0100 | -2.4 | 0.641 | 0.679 | |
| agree (<0.05) | 865 | -0.0004 ±0.0025 | -0.0005 ±0.0008 | -0.1 | 0.706 | 0.704 | |
| mild disagree (0.05-0.10) | 472 | -0.0108 ±0.0083 | -0.0047 ±0.0032 | -1.3 | 0.626 | 0.649 | |
| big disagree (>=0.1) | 267 | -0.0787 ±0.0260 | -0.0315 ±0.0109 | -3.0 | 0.586 | 0.637 | |
| tour: atp | 775 | -0.0100 ±0.0073 | -0.0043 ±0.0029 | -1.4 | 0.652 | 0.668 | |
| tour: wta | 829 | -0.0225 ±0.0074 | -0.0093 ±0.0031 | -3.0 | 0.673 | 0.685 | |

When they disagree by >= 0.1: model closer to the outcome in **102/267** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 18 | 0.067 | 0.167 |
| 0.1-0.2 | 100 | 0.152 | 0.180 |
| 0.2-0.3 | 146 | 0.250 | 0.260 |
| 0.3-0.4 | 205 | 0.353 | 0.371 |
| 0.4-0.5 | 272 | 0.451 | 0.467 |
| 0.5-0.6 | 249 | 0.551 | 0.538 |
| 0.6-0.7 | 238 | 0.647 | 0.622 |
| 0.7-0.8 | 194 | 0.752 | 0.773 |
| 0.8-0.9 | 123 | 0.845 | 0.797 |
| 0.9-1.0 | 59 | 0.932 | 0.915 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 43 | 0.058 | 0.093 |
| 0.1-0.2 | 89 | 0.154 | 0.169 |
| 0.2-0.3 | 166 | 0.255 | 0.259 |
| 0.3-0.4 | 199 | 0.354 | 0.392 |
| 0.4-0.5 | 234 | 0.445 | 0.453 |
| 0.5-0.6 | 229 | 0.555 | 0.533 |
| 0.6-0.7 | 239 | 0.649 | 0.628 |
| 0.7-0.8 | 203 | 0.749 | 0.749 |
| 0.8-0.9 | 134 | 0.847 | 0.836 |
| 0.9-1.0 | 68 | 0.934 | 0.941 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 341 | +0.0099 ±0.0106 | +0.0021 ±0.0036 | +0.9 | 0.736 | 0.733 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 936 | +0.0006 ±0.0066 | -0.0008 ±0.0027 | +0.1 | 0.659 | 0.667 | |
| agree (<0.05) | 865 | -0.0004 ±0.0025 | -0.0005 ±0.0008 | -0.1 | 0.706 | 0.704 | |
| kalshi favorite 0.8-0.9 | 222 | -0.0027 ±0.0158 | -0.0017 ±0.0055 | -0.2 | 0.829 | 0.833 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| top-20 involved | 572 | -0.0018 ±0.0082 | -0.0021 ±0.0030 | -0.2 | 0.719 | 0.723 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| kalshi favorite 0.5-0.6 | 459 | -0.0231 ±0.0086 | -0.0108 ±0.0040 | -2.7 | 0.504 | 0.544 | |
| big disagree (>=0.1) | 267 | -0.0787 ±0.0260 | -0.0315 ±0.0109 | -3.0 | 0.586 | 0.637 | |
| tour: wta | 829 | -0.0225 ±0.0074 | -0.0093 ±0.0031 | -3.0 | 0.673 | 0.685 | |
| best rank 21-50 | 553 | -0.0277 ±0.0081 | -0.0112 ±0.0035 | -3.4 | 0.656 | 0.698 | |
| no top-20 player | 1032 | -0.0246 ±0.0066 | -0.0095 ±0.0028 | -3.7 | 0.631 | 0.651 | |
| month 2026-09 | 319 | -0.0405 ±0.0103 | -0.0168 ±0.0043 | -3.9 | 0.705 | 0.730 | |
| surface: Hard | 754 | -0.0324 ±0.0078 | -0.0122 ±0.0032 | -4.1 | 0.664 | 0.679 | |
| pred_source: live aligned | 668 | -0.0404 ±0.0082 | -0.0154 ±0.0034 | -4.9 | 0.668 | 0.690 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1604, mean |Δ|=0.0060, p95=0.0100, >0.05 in 37 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0666 (n=319, >0.05: 19) | 2026-10 p95=0.1986 (n=145, >0.05: 16)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1606, d_ll -0.0165 ±0.0052
- Unmatched qualifying markets: 622 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'WTA Seoul': 3, 'ATP Chengdu': 1}
- Unmatched Kalshi names, main draw (40): Akasha Urhobo, Aleksandr Shevchenko, Alevtina Ibragimova, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari
