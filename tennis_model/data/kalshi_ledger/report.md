# Model vs Kalshi — match-by-match scorecard

_Generated 2026-09-19T10:32:15Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1801 | 1734 | 0 | 10 | 57 | 0 | 11 | 19 | 43 | 2026-05-03..2026-09-13 |
| wta | 1900 | 1145 | 26 | 679 | 50 | 0 | 8 | 15 | 29 | 2026-05-02..2026-09-20 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1319 | 0.5971 | 0.5905 | -0.0066 ±0.0053 | -0.0035 ±0.0021 | 0.669 | 0.678 |
| atp | 628 | 0.6198 | 0.6196 | -0.0002 ±0.0073 | -0.0012 ±0.0029 | 0.650 | 0.665 |
| wta | 691 | 0.5764 | 0.5641 | -0.0124 ±0.0076 | -0.0056 ±0.0031 | 0.686 | 0.690 |
| pooled/live_aligned | 396 | 0.5747 | 0.5512 | -0.0236 ±0.0081 | -0.0099 ±0.0034 | 0.692 | 0.705 |
| pooled/backtest | 923 | 0.6067 | 0.6074 | +0.0007 ±0.0067 | -0.0008 ±0.0027 | 0.659 | 0.667 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 396 | -0.0236 ±0.0081 | -0.0099 ±0.0034 | -2.9 | 0.692 | 0.705 | |
| pred_source: backtest | 923 | +0.0007 ±0.0067 | -0.0008 ±0.0027 | +0.1 | 0.659 | 0.667 | |
| top-20 involved | 472 | +0.0076 ±0.0075 | +0.0011 ±0.0025 | +1.0 | 0.734 | 0.732 | |
| no top-20 player | 847 | -0.0144 ±0.0070 | -0.0061 ±0.0030 | -2.0 | 0.632 | 0.648 | |
| both inside top-50 | 318 | -0.0019 ±0.0089 | -0.0016 ±0.0038 | -0.2 | 0.659 | 0.653 | |
| someone outside top-50 | 1001 | -0.0080 ±0.0063 | -0.0041 ±0.0026 | -1.3 | 0.672 | 0.686 | |
| best rank 1-10 | 284 | +0.0211 ±0.0101 | +0.0053 ±0.0030 | +2.1 | 0.743 | 0.736 | |
| best rank 11-20 | 188 | -0.0128 ±0.0109 | -0.0051 ±0.0042 | -1.2 | 0.721 | 0.726 | |
| best rank 21-50 | 455 | -0.0172 ±0.0080 | -0.0071 ±0.0035 | -2.1 | 0.653 | 0.685 | |
| best rank 51-100 | 317 | -0.0080 ±0.0124 | -0.0037 ±0.0053 | -0.6 | 0.607 | 0.603 | |
| best rank 100+ | 75 | -0.0252 ±0.0348 | -0.0103 ±0.0150 | -0.7 | 0.613 | 0.620 | |
| kalshi favorite 0.5-0.6 | 376 | -0.0268 ±0.0094 | -0.0125 ±0.0044 | -2.8 | 0.499 | 0.541 | |
| kalshi favorite 0.6-0.7 | 364 | -0.0050 ±0.0094 | -0.0019 ±0.0043 | -0.5 | 0.629 | 0.626 | |
| kalshi favorite 0.7-0.8 | 309 | -0.0024 ±0.0090 | -0.0009 ±0.0036 | -0.3 | 0.743 | 0.741 | |
| kalshi favorite 0.8-0.9 | 184 | +0.0157 ±0.0168 | +0.0050 ±0.0059 | +0.9 | 0.842 | 0.837 | |
| kalshi favorite 0.9-1.0 | 86 | +0.0127 ±0.0299 | +0.0011 ±0.0076 | +0.4 | 0.942 | 0.930 | |
| surface: Hard | 469 | -0.0142 ±0.0081 | -0.0060 ±0.0034 | -1.8 | 0.682 | 0.684 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 357 | -0.0083 ±0.0115 | -0.0044 ±0.0048 | -0.7 | 0.602 | 0.616 | |
| tier: atp500 | 227 | -0.0116 ±0.0097 | -0.0057 ±0.0044 | -1.2 | 0.617 | 0.628 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| round early (R128-R64) | 549 | -0.0098 ±0.0086 | -0.0045 ±0.0034 | -1.1 | 0.724 | 0.731 | |
| round late (QF-F) | 160 | -0.0048 ±0.0110 | -0.0030 ±0.0049 | -0.4 | 0.644 | 0.637 | |
| round mid (R32-R16) | 588 | -0.0040 ±0.0080 | -0.0027 ±0.0034 | -0.5 | 0.630 | 0.645 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 179 | -0.0227 ±0.0114 | -0.0112 ±0.0047 | -2.0 | 0.765 | 0.785 | |
| agree (<0.05) | 715 | -0.0007 ±0.0027 | -0.0009 ±0.0009 | -0.3 | 0.710 | 0.707 | |
| mild disagree (0.05-0.10) | 396 | -0.0113 ±0.0092 | -0.0055 ±0.0035 | -1.2 | 0.622 | 0.657 | |
| big disagree (>=0.1) | 208 | -0.0177 ±0.0270 | -0.0086 ±0.0115 | -0.7 | 0.613 | 0.620 | |
| tour: atp | 628 | -0.0002 ±0.0073 | -0.0012 ±0.0029 | -0.0 | 0.650 | 0.665 | |
| tour: wta | 691 | -0.0124 ±0.0076 | -0.0056 ±0.0031 | -1.6 | 0.686 | 0.690 | |

When they disagree by >= 0.1: model closer to the outcome in **88/208** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 14 | 0.067 | 0.143 |
| 0.1-0.2 | 82 | 0.153 | 0.134 |
| 0.2-0.3 | 118 | 0.254 | 0.254 |
| 0.3-0.4 | 167 | 0.354 | 0.347 |
| 0.4-0.5 | 230 | 0.451 | 0.470 |
| 0.5-0.6 | 208 | 0.551 | 0.543 |
| 0.6-0.7 | 195 | 0.647 | 0.621 |
| 0.7-0.8 | 158 | 0.750 | 0.766 |
| 0.8-0.9 | 100 | 0.847 | 0.810 |
| 0.9-1.0 | 47 | 0.933 | 0.936 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 32 | 0.061 | 0.094 |
| 0.1-0.2 | 75 | 0.153 | 0.133 |
| 0.2-0.3 | 136 | 0.256 | 0.272 |
| 0.3-0.4 | 164 | 0.354 | 0.372 |
| 0.4-0.5 | 192 | 0.444 | 0.448 |
| 0.5-0.6 | 187 | 0.555 | 0.519 |
| 0.6-0.7 | 197 | 0.648 | 0.635 |
| 0.7-0.8 | 173 | 0.749 | 0.751 |
| 0.8-0.9 | 110 | 0.846 | 0.818 |
| 0.9-1.0 | 53 | 0.932 | 0.943 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 284 | +0.0211 ±0.0101 | +0.0053 ±0.0030 | +2.1 | 0.743 | 0.736 | |
| top-20 involved | 472 | +0.0076 ±0.0075 | +0.0011 ±0.0025 | +1.0 | 0.734 | 0.732 | |
| kalshi favorite 0.8-0.9 | 184 | +0.0157 ±0.0168 | +0.0050 ±0.0059 | +0.9 | 0.842 | 0.837 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| kalshi favorite 0.9-1.0 | 86 | +0.0127 ±0.0299 | +0.0011 ±0.0076 | +0.4 | 0.942 | 0.930 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 923 | +0.0007 ±0.0067 | -0.0008 ±0.0027 | +0.1 | 0.659 | 0.667 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| someone outside top-50 | 1001 | -0.0080 ±0.0063 | -0.0041 ±0.0026 | -1.3 | 0.672 | 0.686 | |
| tour: wta | 691 | -0.0124 ±0.0076 | -0.0056 ±0.0031 | -1.6 | 0.686 | 0.690 | |
| surface: Hard | 469 | -0.0142 ±0.0081 | -0.0060 ±0.0034 | -1.8 | 0.682 | 0.684 | |
| month 2026-09 | 179 | -0.0227 ±0.0114 | -0.0112 ±0.0047 | -2.0 | 0.765 | 0.785 | |
| no top-20 player | 847 | -0.0144 ±0.0070 | -0.0061 ±0.0030 | -2.0 | 0.632 | 0.648 | |
| best rank 21-50 | 455 | -0.0172 ±0.0080 | -0.0071 ±0.0035 | -2.1 | 0.653 | 0.685 | |
| kalshi favorite 0.5-0.6 | 376 | -0.0268 ±0.0094 | -0.0125 ±0.0044 | -2.8 | 0.499 | 0.541 | |
| pred_source: live aligned | 396 | -0.0236 ±0.0081 | -0.0099 ±0.0034 | -2.9 | 0.692 | 0.705 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1319, mean |Δ|=0.0017, p95=0.0086, >0.05 in 2 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0072 (n=179, >0.05: 0)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1319, d_ll -0.0066 ±0.0053 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 536 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Cincinnati': 1, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): Akasha Urhobo, Aleksandr Shevchenko, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari, Carson Branstine
