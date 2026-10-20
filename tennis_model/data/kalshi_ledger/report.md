# Model vs Kalshi — match-by-match scorecard

_Generated 2026-10-20T08:08:34Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 2178 | 2071 | 30 | 13 | 64 | 0 | 12 | 25 | 57 | 2026-05-03..2026-10-21 |
| wta | 2271 | 1383 | 54 | 768 | 66 | 0 | 10 | 17 | 39 | 2026-05-02..2026-10-21 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1632 | 0.6086 | 0.5928 | -0.0159 ±0.0051 | -0.0066 ±0.0021 | 0.661 | 0.675 |
| atp | 790 | 0.6216 | 0.6127 | -0.0089 ±0.0072 | -0.0038 ±0.0029 | 0.647 | 0.663 |
| wta | 842 | 0.5965 | 0.5741 | -0.0224 ±0.0073 | -0.0093 ±0.0030 | 0.675 | 0.686 |
| pooled/live_aligned | 696 | 0.6132 | 0.5751 | -0.0380 ±0.0081 | -0.0145 ±0.0033 | 0.664 | 0.685 |
| pooled/backtest | 936 | 0.6053 | 0.6059 | +0.0006 ±0.0066 | -0.0008 ±0.0027 | 0.659 | 0.667 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 696 | -0.0380 ±0.0081 | -0.0145 ±0.0033 | -4.7 | 0.664 | 0.685 | |
| pred_source: backtest | 936 | +0.0006 ±0.0066 | -0.0008 ±0.0027 | +0.1 | 0.659 | 0.667 | |
| top-20 involved | 584 | -0.0009 ±0.0082 | -0.0016 ±0.0030 | -0.1 | 0.718 | 0.720 | |
| no top-20 player | 1048 | -0.0242 ±0.0066 | -0.0094 ±0.0028 | -3.7 | 0.629 | 0.650 | |
| both inside top-50 | 423 | -0.0204 ±0.0102 | -0.0083 ±0.0043 | -2.0 | 0.639 | 0.649 | |
| someone outside top-50 | 1209 | -0.0143 ±0.0059 | -0.0060 ±0.0024 | -2.4 | 0.669 | 0.684 | |
| best rank 1-10 | 348 | +0.0102 ±0.0104 | +0.0023 ±0.0035 | +1.0 | 0.733 | 0.730 | |
| best rank 11-20 | 236 | -0.0173 ±0.0132 | -0.0074 ±0.0053 | -1.3 | 0.697 | 0.706 | |
| best rank 21-50 | 561 | -0.0271 ±0.0080 | -0.0110 ±0.0035 | -3.4 | 0.658 | 0.699 | |
| best rank 51-100 | 398 | -0.0179 ±0.0111 | -0.0065 ±0.0046 | -1.6 | 0.597 | 0.592 | |
| best rank 100+ | 89 | -0.0348 ±0.0317 | -0.0124 ±0.0134 | -1.1 | 0.596 | 0.601 | |
| kalshi favorite 0.5-0.6 | 466 | -0.0226 ±0.0085 | -0.0106 ±0.0039 | -2.7 | 0.505 | 0.542 | |
| kalshi favorite 0.6-0.7 | 451 | -0.0104 ±0.0090 | -0.0038 ±0.0040 | -1.1 | 0.612 | 0.614 | |
| kalshi favorite 0.7-0.8 | 378 | -0.0088 ±0.0098 | -0.0034 ±0.0040 | -0.9 | 0.737 | 0.743 | |
| kalshi favorite 0.8-0.9 | 225 | -0.0017 ±0.0156 | -0.0014 ±0.0055 | -0.1 | 0.827 | 0.831 | |
| kalshi favorite 0.9-1.0 | 112 | -0.0624 ±0.0309 | -0.0227 ±0.0096 | -2.0 | 0.920 | 0.929 | |
| surface: Hard | 782 | -0.0306 ±0.0077 | -0.0115 ±0.0032 | -4.0 | 0.661 | 0.675 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 543 | -0.0213 ±0.0101 | -0.0081 ±0.0041 | -2.1 | 0.610 | 0.624 | |
| tier: atp500 | 254 | -0.0166 ±0.0102 | -0.0074 ±0.0046 | -1.6 | 0.630 | 0.648 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 324 | -0.0171 ±0.0108 | -0.0058 ±0.0046 | -1.6 | 0.659 | 0.673 | |
| round early (R128-R64) | 646 | -0.0208 ±0.0083 | -0.0085 ±0.0032 | -2.5 | 0.710 | 0.723 | |
| round late (QF-F) | 218 | -0.0066 ±0.0115 | -0.0036 ±0.0051 | -0.6 | 0.633 | 0.642 | |
| round mid (R32-R16) | 746 | -0.0147 ±0.0079 | -0.0060 ±0.0033 | -1.9 | 0.632 | 0.647 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 319 | -0.0405 ±0.0103 | -0.0168 ±0.0043 | -3.9 | 0.705 | 0.730 | |
| month 2026-10 | 173 | -0.0485 ±0.0225 | -0.0163 ±0.0090 | -2.2 | 0.630 | 0.662 | |
| agree (<0.05) | 881 | -0.0004 ±0.0025 | -0.0005 ±0.0008 | -0.2 | 0.705 | 0.703 | |
| mild disagree (0.05-0.10) | 478 | -0.0102 ±0.0082 | -0.0045 ±0.0031 | -1.2 | 0.624 | 0.647 | |
| big disagree (>=0.1) | 273 | -0.0757 ±0.0257 | -0.0302 ±0.0108 | -2.9 | 0.584 | 0.634 | |
| tour: atp | 790 | -0.0089 ±0.0072 | -0.0038 ±0.0029 | -1.2 | 0.647 | 0.663 | |
| tour: wta | 842 | -0.0224 ±0.0073 | -0.0093 ±0.0030 | -3.1 | 0.675 | 0.686 | |

When they disagree by >= 0.1: model closer to the outcome in **105/273** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 19 | 0.068 | 0.158 |
| 0.1-0.2 | 102 | 0.152 | 0.186 |
| 0.2-0.3 | 149 | 0.250 | 0.262 |
| 0.3-0.4 | 210 | 0.353 | 0.371 |
| 0.4-0.5 | 280 | 0.451 | 0.471 |
| 0.5-0.6 | 252 | 0.551 | 0.540 |
| 0.6-0.7 | 241 | 0.647 | 0.622 |
| 0.7-0.8 | 195 | 0.752 | 0.774 |
| 0.8-0.9 | 125 | 0.845 | 0.792 |
| 0.9-1.0 | 59 | 0.932 | 0.915 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 43 | 0.058 | 0.093 |
| 0.1-0.2 | 90 | 0.154 | 0.167 |
| 0.2-0.3 | 172 | 0.255 | 0.262 |
| 0.3-0.4 | 202 | 0.354 | 0.396 |
| 0.4-0.5 | 237 | 0.445 | 0.456 |
| 0.5-0.6 | 233 | 0.555 | 0.532 |
| 0.6-0.7 | 245 | 0.649 | 0.629 |
| 0.7-0.8 | 206 | 0.749 | 0.748 |
| 0.8-0.9 | 136 | 0.846 | 0.831 |
| 0.9-1.0 | 68 | 0.934 | 0.941 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 348 | +0.0102 ±0.0104 | +0.0023 ±0.0035 | +1.0 | 0.733 | 0.730 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 936 | +0.0006 ±0.0066 | -0.0008 ±0.0027 | +0.1 | 0.659 | 0.667 | |
| kalshi favorite 0.8-0.9 | 225 | -0.0017 ±0.0156 | -0.0014 ±0.0055 | -0.1 | 0.827 | 0.831 | |
| top-20 involved | 584 | -0.0009 ±0.0082 | -0.0016 ±0.0030 | -0.1 | 0.718 | 0.720 | |
| agree (<0.05) | 881 | -0.0004 ±0.0025 | -0.0005 ±0.0008 | -0.2 | 0.705 | 0.703 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| kalshi favorite 0.5-0.6 | 466 | -0.0226 ±0.0085 | -0.0106 ±0.0039 | -2.7 | 0.505 | 0.542 | |
| big disagree (>=0.1) | 273 | -0.0757 ±0.0257 | -0.0302 ±0.0108 | -2.9 | 0.584 | 0.634 | |
| tour: wta | 842 | -0.0224 ±0.0073 | -0.0093 ±0.0030 | -3.1 | 0.675 | 0.686 | |
| best rank 21-50 | 561 | -0.0271 ±0.0080 | -0.0110 ±0.0035 | -3.4 | 0.658 | 0.699 | |
| no top-20 player | 1048 | -0.0242 ±0.0066 | -0.0094 ±0.0028 | -3.7 | 0.629 | 0.650 | |
| month 2026-09 | 319 | -0.0405 ±0.0103 | -0.0168 ±0.0043 | -3.9 | 0.705 | 0.730 | |
| surface: Hard | 782 | -0.0306 ±0.0077 | -0.0115 ±0.0032 | -4.0 | 0.661 | 0.675 | |
| pred_source: live aligned | 696 | -0.0380 ±0.0081 | -0.0145 ±0.0033 | -4.7 | 0.664 | 0.685 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1632, mean |Δ|=0.0062, p95=0.0100, >0.05 in 39 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0666 (n=319, >0.05: 19) | 2026-10 p95=0.1759 (n=173, >0.05: 18)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1634, d_ll -0.0159 ±0.0051
- Unmatched qualifying markets: 622 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'WTA Seoul': 3, 'ATP Chengdu': 1}
- Unmatched Kalshi names, main draw (40): Akasha Urhobo, Aleksandr Shevchenko, Alevtina Ibragimova, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari
