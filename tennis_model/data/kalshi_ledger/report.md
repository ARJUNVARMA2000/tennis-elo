# Model vs Kalshi — match-by-match scorecard

_Generated 2026-10-21T08:19:02Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 2190 | 2092 | 20 | 14 | 64 | 0 | 13 | 25 | 59 | 2026-05-03..2026-10-21 |
| wta | 2296 | 1397 | 39 | 792 | 68 | 0 | 10 | 19 | 35 | 2026-05-02..2026-10-22 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1659 | 0.6107 | 0.5935 | -0.0172 ±0.0051 | -0.0072 ±0.0021 | 0.659 | 0.674 |
| atp | 810 | 0.6241 | 0.6137 | -0.0104 ±0.0071 | -0.0044 ±0.0028 | 0.644 | 0.660 |
| wta | 849 | 0.5979 | 0.5742 | -0.0237 ±0.0073 | -0.0098 ±0.0030 | 0.673 | 0.687 |
| pooled/live_aligned | 723 | 0.6177 | 0.5775 | -0.0402 ±0.0079 | -0.0156 ±0.0033 | 0.658 | 0.682 |
| pooled/backtest | 936 | 0.6053 | 0.6059 | +0.0006 ±0.0066 | -0.0008 ±0.0027 | 0.659 | 0.667 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 723 | -0.0402 ±0.0079 | -0.0156 ±0.0033 | -5.1 | 0.658 | 0.682 | |
| pred_source: backtest | 936 | +0.0006 ±0.0066 | -0.0008 ±0.0027 | +0.1 | 0.659 | 0.667 | |
| top-20 involved | 585 | -0.0008 ±0.0082 | -0.0016 ±0.0030 | -0.1 | 0.719 | 0.721 | |
| no top-20 player | 1074 | -0.0261 ±0.0065 | -0.0103 ±0.0028 | -4.0 | 0.626 | 0.648 | |
| both inside top-50 | 423 | -0.0204 ±0.0102 | -0.0083 ±0.0043 | -2.0 | 0.639 | 0.649 | |
| someone outside top-50 | 1236 | -0.0161 ±0.0059 | -0.0068 ±0.0024 | -2.7 | 0.665 | 0.682 | |
| best rank 1-10 | 348 | +0.0102 ±0.0104 | +0.0023 ±0.0035 | +1.0 | 0.733 | 0.730 | |
| best rank 11-20 | 237 | -0.0170 ±0.0131 | -0.0072 ±0.0053 | -1.3 | 0.698 | 0.707 | |
| best rank 21-50 | 576 | -0.0288 ±0.0079 | -0.0118 ±0.0034 | -3.6 | 0.653 | 0.694 | |
| best rank 51-100 | 407 | -0.0194 ±0.0109 | -0.0072 ±0.0045 | -1.8 | 0.596 | 0.591 | |
| best rank 100+ | 91 | -0.0393 ±0.0317 | -0.0147 ±0.0135 | -1.2 | 0.593 | 0.610 | |
| kalshi favorite 0.5-0.6 | 475 | -0.0241 ±0.0084 | -0.0113 ±0.0039 | -2.9 | 0.502 | 0.540 | |
| kalshi favorite 0.6-0.7 | 461 | -0.0108 ±0.0089 | -0.0041 ±0.0040 | -1.2 | 0.612 | 0.614 | |
| kalshi favorite 0.7-0.8 | 385 | -0.0117 ±0.0099 | -0.0046 ±0.0040 | -1.2 | 0.734 | 0.743 | |
| kalshi favorite 0.8-0.9 | 226 | -0.0026 ±0.0156 | -0.0017 ±0.0055 | -0.2 | 0.827 | 0.832 | |
| kalshi favorite 0.9-1.0 | 112 | -0.0624 ±0.0309 | -0.0227 ±0.0096 | -2.0 | 0.920 | 0.929 | |
| surface: Hard | 809 | -0.0328 ±0.0076 | -0.0125 ±0.0031 | -4.3 | 0.656 | 0.672 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 566 | -0.0241 ±0.0098 | -0.0095 ±0.0040 | -2.5 | 0.606 | 0.624 | |
| tier: atp500 | 258 | -0.0184 ±0.0103 | -0.0081 ±0.0046 | -1.8 | 0.628 | 0.645 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 324 | -0.0171 ±0.0108 | -0.0058 ±0.0046 | -1.6 | 0.659 | 0.673 | |
| round early (R128-R64) | 646 | -0.0208 ±0.0083 | -0.0085 ±0.0032 | -2.5 | 0.710 | 0.723 | |
| round late (QF-F) | 218 | -0.0066 ±0.0115 | -0.0036 ±0.0051 | -0.6 | 0.633 | 0.642 | |
| round mid (R32-R16) | 773 | -0.0175 ±0.0078 | -0.0073 ±0.0032 | -2.3 | 0.628 | 0.645 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 319 | -0.0405 ±0.0103 | -0.0168 ±0.0043 | -3.9 | 0.705 | 0.730 | |
| month 2026-10 | 200 | -0.0550 ±0.0202 | -0.0199 ±0.0081 | -2.7 | 0.615 | 0.652 | |
| agree (<0.05) | 892 | -0.0007 ±0.0025 | -0.0006 ±0.0008 | -0.3 | 0.702 | 0.700 | |
| mild disagree (0.05-0.10) | 486 | -0.0101 ±0.0081 | -0.0045 ±0.0031 | -1.2 | 0.627 | 0.647 | |
| big disagree (>=0.1) | 281 | -0.0818 ±0.0252 | -0.0330 ±0.0106 | -3.3 | 0.578 | 0.637 | |
| tour: atp | 810 | -0.0104 ±0.0071 | -0.0044 ±0.0028 | -1.5 | 0.644 | 0.660 | |
| tour: wta | 849 | -0.0237 ±0.0073 | -0.0098 ±0.0030 | -3.2 | 0.673 | 0.687 | |

When they disagree by >= 0.1: model closer to the outcome in **106/281** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 19 | 0.068 | 0.158 |
| 0.1-0.2 | 103 | 0.152 | 0.184 |
| 0.2-0.3 | 152 | 0.251 | 0.257 |
| 0.3-0.4 | 215 | 0.353 | 0.381 |
| 0.4-0.5 | 286 | 0.451 | 0.469 |
| 0.5-0.6 | 256 | 0.551 | 0.535 |
| 0.6-0.7 | 244 | 0.647 | 0.619 |
| 0.7-0.8 | 197 | 0.752 | 0.777 |
| 0.8-0.9 | 128 | 0.845 | 0.781 |
| 0.9-1.0 | 59 | 0.932 | 0.915 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 43 | 0.058 | 0.093 |
| 0.1-0.2 | 90 | 0.154 | 0.167 |
| 0.2-0.3 | 174 | 0.254 | 0.259 |
| 0.3-0.4 | 210 | 0.354 | 0.395 |
| 0.4-0.5 | 240 | 0.445 | 0.454 |
| 0.5-0.6 | 239 | 0.555 | 0.527 |
| 0.6-0.7 | 247 | 0.649 | 0.628 |
| 0.7-0.8 | 211 | 0.749 | 0.744 |
| 0.8-0.9 | 137 | 0.846 | 0.832 |
| 0.9-1.0 | 68 | 0.934 | 0.941 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 348 | +0.0102 ±0.0104 | +0.0023 ±0.0035 | +1.0 | 0.733 | 0.730 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 936 | +0.0006 ±0.0066 | -0.0008 ±0.0027 | +0.1 | 0.659 | 0.667 | |
| top-20 involved | 585 | -0.0008 ±0.0082 | -0.0016 ±0.0030 | -0.1 | 0.719 | 0.721 | |
| kalshi favorite 0.8-0.9 | 226 | -0.0026 ±0.0156 | -0.0017 ±0.0055 | -0.2 | 0.827 | 0.832 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| agree (<0.05) | 892 | -0.0007 ±0.0025 | -0.0006 ±0.0008 | -0.3 | 0.702 | 0.700 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| kalshi favorite 0.5-0.6 | 475 | -0.0241 ±0.0084 | -0.0113 ±0.0039 | -2.9 | 0.502 | 0.540 | |
| tour: wta | 849 | -0.0237 ±0.0073 | -0.0098 ±0.0030 | -3.2 | 0.673 | 0.687 | |
| big disagree (>=0.1) | 281 | -0.0818 ±0.0252 | -0.0330 ±0.0106 | -3.3 | 0.578 | 0.637 | |
| best rank 21-50 | 576 | -0.0288 ±0.0079 | -0.0118 ±0.0034 | -3.6 | 0.653 | 0.694 | |
| month 2026-09 | 319 | -0.0405 ±0.0103 | -0.0168 ±0.0043 | -3.9 | 0.705 | 0.730 | |
| no top-20 player | 1074 | -0.0261 ±0.0065 | -0.0103 ±0.0028 | -4.0 | 0.626 | 0.648 | |
| surface: Hard | 809 | -0.0328 ±0.0076 | -0.0125 ±0.0031 | -4.3 | 0.656 | 0.672 | |
| pred_source: live aligned | 723 | -0.0402 ±0.0079 | -0.0156 ±0.0033 | -5.1 | 0.658 | 0.682 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1659, mean |Δ|=0.0063, p95=0.0100, >0.05 in 41 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0666 (n=319, >0.05: 19) | 2026-10 p95=0.1672 (n=200, >0.05: 20)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1663, d_ll -0.0172 ±0.0051
- Unmatched qualifying markets: 647 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'WTA Seoul': 3, 'ATP Chengdu': 1}
- Unmatched Kalshi names, main draw (40): Akasha Urhobo, Aleksandr Shevchenko, Alevtina Ibragimova, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari
