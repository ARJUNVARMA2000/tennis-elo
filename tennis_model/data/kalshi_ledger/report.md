# Model vs Kalshi — match-by-match scorecard

_Generated 2026-09-24T06:53:57Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1852 | 1760 | 25 | 10 | 57 | 0 | 11 | 19 | 54 | 2026-05-03..2026-09-25 |
| wta | 1956 | 1184 | 17 | 703 | 52 | 0 | 9 | 15 | 23 | 2026-05-02..2026-09-25 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1349 | 0.5957 | 0.5881 | -0.0076 ±0.0052 | -0.0038 ±0.0021 | 0.672 | 0.680 |
| atp | 631 | 0.6199 | 0.6197 | -0.0002 ±0.0072 | -0.0012 ±0.0029 | 0.651 | 0.665 |
| wta | 718 | 0.5744 | 0.5604 | -0.0140 ±0.0075 | -0.0060 ±0.0031 | 0.689 | 0.694 |
| pooled/live_aligned | 426 | 0.5719 | 0.5463 | -0.0255 ±0.0080 | -0.0102 ±0.0033 | 0.700 | 0.709 |
| pooled/backtest | 923 | 0.6067 | 0.6074 | +0.0007 ±0.0067 | -0.0008 ±0.0027 | 0.659 | 0.667 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 426 | -0.0255 ±0.0080 | -0.0102 ±0.0033 | -3.2 | 0.700 | 0.709 | |
| pred_source: backtest | 923 | +0.0007 ±0.0067 | -0.0008 ±0.0027 | +0.1 | 0.659 | 0.667 | |
| top-20 involved | 474 | +0.0077 ±0.0075 | +0.0012 ±0.0025 | +1.0 | 0.735 | 0.733 | |
| no top-20 player | 875 | -0.0158 ±0.0069 | -0.0064 ±0.0030 | -2.3 | 0.637 | 0.651 | |
| both inside top-50 | 321 | -0.0051 ±0.0091 | -0.0027 ±0.0039 | -0.6 | 0.662 | 0.656 | |
| someone outside top-50 | 1028 | -0.0083 ±0.0062 | -0.0041 ±0.0025 | -1.3 | 0.675 | 0.688 | |
| best rank 1-10 | 285 | +0.0211 ±0.0101 | +0.0053 ±0.0030 | +2.1 | 0.744 | 0.737 | |
| best rank 11-20 | 189 | -0.0127 ±0.0109 | -0.0050 ±0.0041 | -1.2 | 0.722 | 0.728 | |
| best rank 21-50 | 464 | -0.0187 ±0.0080 | -0.0076 ±0.0035 | -2.3 | 0.659 | 0.691 | |
| best rank 51-100 | 332 | -0.0106 ±0.0121 | -0.0045 ±0.0051 | -0.9 | 0.616 | 0.608 | |
| best rank 100+ | 79 | -0.0203 ±0.0338 | -0.0079 ±0.0146 | -0.6 | 0.595 | 0.601 | |
| kalshi favorite 0.5-0.6 | 384 | -0.0265 ±0.0093 | -0.0123 ±0.0043 | -2.9 | 0.504 | 0.546 | |
| kalshi favorite 0.6-0.7 | 370 | -0.0033 ±0.0094 | -0.0011 ±0.0043 | -0.3 | 0.630 | 0.624 | |
| kalshi favorite 0.7-0.8 | 315 | -0.0030 ±0.0089 | -0.0011 ±0.0036 | -0.3 | 0.744 | 0.743 | |
| kalshi favorite 0.8-0.9 | 188 | +0.0156 ±0.0165 | +0.0049 ±0.0058 | +0.9 | 0.840 | 0.835 | |
| kalshi favorite 0.9-1.0 | 92 | -0.0088 ±0.0297 | -0.0055 ±0.0079 | -0.3 | 0.946 | 0.935 | |
| surface: Hard | 499 | -0.0165 ±0.0080 | -0.0065 ±0.0033 | -2.1 | 0.689 | 0.689 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 374 | -0.0110 ±0.0112 | -0.0052 ±0.0047 | -1.0 | 0.607 | 0.618 | |
| tier: atp500 | 240 | -0.0126 ±0.0100 | -0.0056 ±0.0045 | -1.3 | 0.633 | 0.644 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| round early (R128-R64) | 549 | -0.0098 ±0.0086 | -0.0045 ±0.0034 | -1.1 | 0.724 | 0.731 | |
| round late (QF-F) | 164 | -0.0034 ±0.0108 | -0.0025 ±0.0047 | -0.3 | 0.640 | 0.634 | |
| round mid (R32-R16) | 614 | -0.0067 ±0.0079 | -0.0035 ±0.0033 | -0.8 | 0.639 | 0.651 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 209 | -0.0268 ±0.0113 | -0.0117 ±0.0046 | -2.4 | 0.770 | 0.782 | |
| agree (<0.05) | 729 | -0.0006 ±0.0026 | -0.0009 ±0.0009 | -0.2 | 0.711 | 0.707 | |
| mild disagree (0.05-0.10) | 405 | -0.0120 ±0.0091 | -0.0057 ±0.0034 | -1.3 | 0.626 | 0.659 | |
| big disagree (>=0.1) | 215 | -0.0228 ±0.0266 | -0.0098 ±0.0113 | -0.9 | 0.626 | 0.628 | |
| tour: atp | 631 | -0.0002 ±0.0072 | -0.0012 ±0.0029 | -0.0 | 0.651 | 0.665 | |
| tour: wta | 718 | -0.0140 ±0.0075 | -0.0060 ±0.0031 | -1.9 | 0.689 | 0.694 | |

When they disagree by >= 0.1: model closer to the outcome in **90/215** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 15 | 0.066 | 0.133 |
| 0.1-0.2 | 86 | 0.153 | 0.128 |
| 0.2-0.3 | 122 | 0.253 | 0.270 |
| 0.3-0.4 | 170 | 0.354 | 0.341 |
| 0.4-0.5 | 235 | 0.452 | 0.468 |
| 0.5-0.6 | 213 | 0.552 | 0.549 |
| 0.6-0.7 | 199 | 0.647 | 0.628 |
| 0.7-0.8 | 160 | 0.751 | 0.769 |
| 0.8-0.9 | 102 | 0.847 | 0.814 |
| 0.9-1.0 | 47 | 0.933 | 0.936 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 35 | 0.061 | 0.086 |
| 0.1-0.2 | 78 | 0.152 | 0.141 |
| 0.2-0.3 | 139 | 0.255 | 0.273 |
| 0.3-0.4 | 166 | 0.355 | 0.373 |
| 0.4-0.5 | 195 | 0.445 | 0.446 |
| 0.5-0.6 | 192 | 0.555 | 0.526 |
| 0.6-0.7 | 201 | 0.648 | 0.632 |
| 0.7-0.8 | 176 | 0.749 | 0.756 |
| 0.8-0.9 | 111 | 0.846 | 0.820 |
| 0.9-1.0 | 56 | 0.934 | 0.946 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 285 | +0.0211 ±0.0101 | +0.0053 ±0.0030 | +2.1 | 0.744 | 0.737 | |
| top-20 involved | 474 | +0.0077 ±0.0075 | +0.0012 ±0.0025 | +1.0 | 0.735 | 0.733 | |
| kalshi favorite 0.8-0.9 | 188 | +0.0156 ±0.0165 | +0.0049 ±0.0058 | +0.9 | 0.840 | 0.835 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 923 | +0.0007 ±0.0067 | -0.0008 ±0.0027 | +0.1 | 0.659 | 0.667 | |
| tour: atp | 631 | -0.0002 ±0.0072 | -0.0012 ±0.0029 | -0.0 | 0.651 | 0.665 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| someone outside top-50 | 1028 | -0.0083 ±0.0062 | -0.0041 ±0.0025 | -1.3 | 0.675 | 0.688 | |
| tour: wta | 718 | -0.0140 ±0.0075 | -0.0060 ±0.0031 | -1.9 | 0.689 | 0.694 | |
| surface: Hard | 499 | -0.0165 ±0.0080 | -0.0065 ±0.0033 | -2.1 | 0.689 | 0.689 | |
| no top-20 player | 875 | -0.0158 ±0.0069 | -0.0064 ±0.0030 | -2.3 | 0.637 | 0.651 | |
| best rank 21-50 | 464 | -0.0187 ±0.0080 | -0.0076 ±0.0035 | -2.3 | 0.659 | 0.691 | |
| month 2026-09 | 209 | -0.0268 ±0.0113 | -0.0117 ±0.0046 | -2.4 | 0.770 | 0.782 | |
| kalshi favorite 0.5-0.6 | 384 | -0.0265 ±0.0093 | -0.0123 ±0.0043 | -2.9 | 0.504 | 0.546 | |
| pred_source: live aligned | 426 | -0.0255 ±0.0080 | -0.0102 ±0.0033 | -3.2 | 0.700 | 0.709 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1349, mean |Δ|=0.0026, p95=0.0096, >0.05 in 11 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0100 (n=209, >0.05: 9)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1349, d_ll -0.0076 ±0.0052 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 560 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Cincinnati': 1, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): Akasha Urhobo, Aleksandr Shevchenko, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari, Carson Branstine
