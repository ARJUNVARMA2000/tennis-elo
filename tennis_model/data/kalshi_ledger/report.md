# Model vs Kalshi — match-by-match scorecard

_Generated 2026-10-22T08:28:28Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 2199 | 2108 | 12 | 15 | 64 | 0 | 13 | 25 | 54 | 2026-05-03..2026-10-22 |
| wta | 2311 | 1404 | 35 | 804 | 68 | 0 | 10 | 21 | 36 | 2026-05-02..2026-10-23 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1677 | 0.6122 | 0.5940 | -0.0182 ±0.0051 | -0.0076 ±0.0021 | 0.657 | 0.672 |
| atp | 826 | 0.6269 | 0.6139 | -0.0130 ±0.0072 | -0.0055 ±0.0029 | 0.642 | 0.657 |
| wta | 851 | 0.5980 | 0.5748 | -0.0232 ±0.0073 | -0.0097 ±0.0030 | 0.672 | 0.686 |
| pooled/live_aligned | 741 | 0.6210 | 0.5791 | -0.0420 ±0.0080 | -0.0163 ±0.0033 | 0.655 | 0.677 |
| pooled/backtest | 936 | 0.6053 | 0.6059 | +0.0006 ±0.0066 | -0.0008 ±0.0027 | 0.659 | 0.667 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 741 | -0.0420 ±0.0080 | -0.0163 ±0.0033 | -5.3 | 0.655 | 0.677 | |
| pred_source: backtest | 936 | +0.0006 ±0.0066 | -0.0008 ±0.0027 | +0.1 | 0.659 | 0.667 | |
| top-20 involved | 588 | -0.0004 ±0.0081 | -0.0014 ±0.0030 | -0.1 | 0.719 | 0.720 | |
| no top-20 player | 1089 | -0.0278 ±0.0065 | -0.0110 ±0.0028 | -4.3 | 0.624 | 0.646 | |
| both inside top-50 | 424 | -0.0203 ±0.0102 | -0.0083 ±0.0043 | -2.0 | 0.638 | 0.647 | |
| someone outside top-50 | 1253 | -0.0175 ±0.0059 | -0.0074 ±0.0024 | -3.0 | 0.664 | 0.680 | |
| best rank 1-10 | 348 | +0.0102 ±0.0104 | +0.0023 ±0.0035 | +1.0 | 0.733 | 0.730 | |
| best rank 11-20 | 240 | -0.0159 ±0.0130 | -0.0068 ±0.0052 | -1.2 | 0.698 | 0.706 | |
| best rank 21-50 | 583 | -0.0307 ±0.0080 | -0.0125 ±0.0034 | -3.8 | 0.652 | 0.693 | |
| best rank 51-100 | 413 | -0.0223 ±0.0110 | -0.0085 ±0.0046 | -2.0 | 0.592 | 0.590 | |
| best rank 100+ | 93 | -0.0342 ±0.0313 | -0.0123 ±0.0134 | -1.1 | 0.591 | 0.597 | |
| kalshi favorite 0.5-0.6 | 480 | -0.0255 ±0.0085 | -0.0119 ±0.0039 | -3.0 | 0.499 | 0.536 | |
| kalshi favorite 0.6-0.7 | 468 | -0.0122 ±0.0090 | -0.0047 ±0.0040 | -1.4 | 0.609 | 0.611 | |
| kalshi favorite 0.7-0.8 | 389 | -0.0128 ±0.0099 | -0.0049 ±0.0040 | -1.3 | 0.734 | 0.743 | |
| kalshi favorite 0.8-0.9 | 226 | -0.0026 ±0.0156 | -0.0017 ±0.0055 | -0.2 | 0.827 | 0.832 | |
| kalshi favorite 0.9-1.0 | 114 | -0.0616 ±0.0304 | -0.0223 ±0.0095 | -2.0 | 0.921 | 0.930 | |
| surface: Hard | 827 | -0.0345 ±0.0076 | -0.0133 ±0.0031 | -4.5 | 0.653 | 0.669 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 582 | -0.0275 ±0.0098 | -0.0109 ±0.0041 | -2.8 | 0.603 | 0.620 | |
| tier: atp500 | 260 | -0.0170 ±0.0103 | -0.0075 ±0.0046 | -1.7 | 0.627 | 0.644 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 324 | -0.0171 ±0.0108 | -0.0058 ±0.0046 | -1.6 | 0.659 | 0.673 | |
| round early (R128-R64) | 646 | -0.0208 ±0.0083 | -0.0085 ±0.0032 | -2.5 | 0.710 | 0.723 | |
| round late (QF-F) | 218 | -0.0066 ±0.0115 | -0.0036 ±0.0051 | -0.6 | 0.633 | 0.642 | |
| round mid (R32-R16) | 791 | -0.0197 ±0.0078 | -0.0082 ±0.0032 | -2.5 | 0.625 | 0.642 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 319 | -0.0405 ±0.0103 | -0.0168 ±0.0043 | -3.9 | 0.705 | 0.730 | |
| month 2026-10 | 218 | -0.0596 ±0.0196 | -0.0221 ±0.0080 | -3.0 | 0.606 | 0.640 | |
| agree (<0.05) | 898 | -0.0008 ±0.0025 | -0.0006 ±0.0008 | -0.3 | 0.699 | 0.697 | |
| mild disagree (0.05-0.10) | 493 | -0.0106 ±0.0080 | -0.0048 ±0.0031 | -1.3 | 0.628 | 0.648 | |
| big disagree (>=0.1) | 286 | -0.0860 ±0.0252 | -0.0346 ±0.0106 | -3.4 | 0.575 | 0.633 | |
| tour: atp | 826 | -0.0130 ±0.0072 | -0.0055 ±0.0029 | -1.8 | 0.642 | 0.657 | |
| tour: wta | 851 | -0.0232 ±0.0073 | -0.0097 ±0.0030 | -3.2 | 0.672 | 0.686 | |

When they disagree by >= 0.1: model closer to the outcome in **108/286** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 19 | 0.068 | 0.158 |
| 0.1-0.2 | 106 | 0.152 | 0.189 |
| 0.2-0.3 | 154 | 0.251 | 0.260 |
| 0.3-0.4 | 218 | 0.353 | 0.385 |
| 0.4-0.5 | 290 | 0.451 | 0.472 |
| 0.5-0.6 | 257 | 0.551 | 0.537 |
| 0.6-0.7 | 246 | 0.647 | 0.618 |
| 0.7-0.8 | 198 | 0.752 | 0.773 |
| 0.8-0.9 | 129 | 0.845 | 0.783 |
| 0.9-1.0 | 60 | 0.932 | 0.917 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 44 | 0.058 | 0.091 |
| 0.1-0.2 | 90 | 0.154 | 0.167 |
| 0.2-0.3 | 177 | 0.254 | 0.260 |
| 0.3-0.4 | 215 | 0.354 | 0.400 |
| 0.4-0.5 | 245 | 0.445 | 0.461 |
| 0.5-0.6 | 239 | 0.555 | 0.527 |
| 0.6-0.7 | 249 | 0.649 | 0.627 |
| 0.7-0.8 | 212 | 0.749 | 0.745 |
| 0.8-0.9 | 137 | 0.846 | 0.832 |
| 0.9-1.0 | 69 | 0.934 | 0.942 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 348 | +0.0102 ±0.0104 | +0.0023 ±0.0035 | +1.0 | 0.733 | 0.730 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 936 | +0.0006 ±0.0066 | -0.0008 ±0.0027 | +0.1 | 0.659 | 0.667 | |
| top-20 involved | 588 | -0.0004 ±0.0081 | -0.0014 ±0.0030 | -0.1 | 0.719 | 0.720 | |
| kalshi favorite 0.8-0.9 | 226 | -0.0026 ±0.0156 | -0.0017 ±0.0055 | -0.2 | 0.827 | 0.832 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| agree (<0.05) | 898 | -0.0008 ±0.0025 | -0.0006 ±0.0008 | -0.3 | 0.699 | 0.697 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| month 2026-10 | 218 | -0.0596 ±0.0196 | -0.0221 ±0.0080 | -3.0 | 0.606 | 0.640 | |
| tour: wta | 851 | -0.0232 ±0.0073 | -0.0097 ±0.0030 | -3.2 | 0.672 | 0.686 | |
| big disagree (>=0.1) | 286 | -0.0860 ±0.0252 | -0.0346 ±0.0106 | -3.4 | 0.575 | 0.633 | |
| best rank 21-50 | 583 | -0.0307 ±0.0080 | -0.0125 ±0.0034 | -3.8 | 0.652 | 0.693 | |
| month 2026-09 | 319 | -0.0405 ±0.0103 | -0.0168 ±0.0043 | -3.9 | 0.705 | 0.730 | |
| no top-20 player | 1089 | -0.0278 ±0.0065 | -0.0110 ±0.0028 | -4.3 | 0.624 | 0.646 | |
| surface: Hard | 827 | -0.0345 ±0.0076 | -0.0133 ±0.0031 | -4.5 | 0.653 | 0.669 | |
| pred_source: live aligned | 741 | -0.0420 ±0.0080 | -0.0163 ±0.0033 | -5.3 | 0.655 | 0.677 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1677, mean |Δ|=0.0063, p95=0.0100, >0.05 in 42 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0666 (n=319, >0.05: 19) | 2026-10 p95=0.1549 (n=218, >0.05: 21)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1682, d_ll -0.0184 ±0.0051
- Unmatched qualifying markets: 660 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'WTA Seoul': 3, 'ATP Chengdu': 1}
- Unmatched Kalshi names, main draw (40): Akasha Urhobo, Aleksandr Shevchenko, Alevtina Ibragimova, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari
