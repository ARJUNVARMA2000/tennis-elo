# Model vs Kalshi — match-by-match scorecard

_Generated 2026-10-06T04:13:38Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 2025 | 1917 | 35 | 12 | 61 | 0 | 11 | 21 | 77 | 2026-05-03..2026-10-06 |
| wta | 2102 | 1295 | 8 | 743 | 56 | 0 | 10 | 15 | 37 | 2026-05-02..2026-10-07 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1509 | 0.5999 | 0.5868 | -0.0131 ±0.0051 | -0.0059 ±0.0021 | 0.666 | 0.679 |
| atp | 718 | 0.6148 | 0.6092 | -0.0056 ±0.0072 | -0.0031 ±0.0029 | 0.652 | 0.667 |
| wta | 791 | 0.5864 | 0.5665 | -0.0199 ±0.0073 | -0.0084 ±0.0030 | 0.679 | 0.689 |
| pooled/live_aligned | 575 | 0.5909 | 0.5552 | -0.0357 ±0.0080 | -0.0143 ±0.0034 | 0.678 | 0.698 |
| pooled/backtest | 934 | 0.6055 | 0.6062 | +0.0008 ±0.0066 | -0.0007 ±0.0027 | 0.658 | 0.666 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 575 | -0.0357 ±0.0080 | -0.0143 ±0.0034 | -4.4 | 0.678 | 0.698 | |
| pred_source: backtest | 934 | +0.0008 ±0.0066 | -0.0007 ±0.0027 | +0.1 | 0.658 | 0.666 | |
| top-20 involved | 528 | +0.0038 ±0.0079 | -0.0002 ±0.0028 | +0.5 | 0.730 | 0.730 | |
| no top-20 player | 981 | -0.0222 ±0.0066 | -0.0089 ±0.0029 | -3.3 | 0.631 | 0.651 | |
| both inside top-50 | 367 | -0.0102 ±0.0099 | -0.0046 ±0.0042 | -1.0 | 0.661 | 0.661 | |
| someone outside top-50 | 1142 | -0.0141 ±0.0060 | -0.0063 ±0.0024 | -2.3 | 0.668 | 0.684 | |
| best rank 1-10 | 315 | +0.0210 ±0.0093 | +0.0058 ±0.0029 | +2.3 | 0.749 | 0.740 | |
| best rank 11-20 | 213 | -0.0216 ±0.0137 | -0.0090 ±0.0055 | -1.6 | 0.702 | 0.716 | |
| best rank 21-50 | 518 | -0.0258 ±0.0080 | -0.0107 ±0.0035 | -3.2 | 0.656 | 0.698 | |
| best rank 51-100 | 375 | -0.0141 ±0.0112 | -0.0055 ±0.0047 | -1.3 | 0.604 | 0.596 | |
| best rank 100+ | 88 | -0.0357 ±0.0320 | -0.0128 ±0.0136 | -1.1 | 0.602 | 0.608 | |
| kalshi favorite 0.5-0.6 | 430 | -0.0261 ±0.0088 | -0.0121 ±0.0041 | -3.0 | 0.499 | 0.537 | |
| kalshi favorite 0.6-0.7 | 420 | -0.0086 ±0.0092 | -0.0033 ±0.0041 | -0.9 | 0.619 | 0.621 | |
| kalshi favorite 0.7-0.8 | 345 | -0.0040 ±0.0088 | -0.0016 ±0.0035 | -0.5 | 0.746 | 0.748 | |
| kalshi favorite 0.8-0.9 | 208 | +0.0067 ±0.0156 | +0.0014 ±0.0055 | +0.4 | 0.841 | 0.841 | |
| kalshi favorite 0.9-1.0 | 106 | -0.0470 ±0.0316 | -0.0189 ±0.0099 | -1.5 | 0.925 | 0.934 | |
| surface: Hard | 659 | -0.0271 ±0.0077 | -0.0107 ±0.0032 | -3.5 | 0.672 | 0.684 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 470 | -0.0187 ±0.0105 | -0.0079 ±0.0044 | -1.8 | 0.611 | 0.627 | |
| tier: atp500 | 250 | -0.0149 ±0.0103 | -0.0067 ±0.0046 | -1.4 | 0.628 | 0.642 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 278 | -0.0097 ±0.0099 | -0.0029 ±0.0043 | -1.0 | 0.671 | 0.680 | |
| round early (R128-R64) | 593 | -0.0164 ±0.0084 | -0.0071 ±0.0033 | -2.0 | 0.714 | 0.726 | |
| round late (QF-F) | 198 | -0.0063 ±0.0114 | -0.0035 ±0.0051 | -0.6 | 0.641 | 0.646 | |
| round mid (R32-R16) | 696 | -0.0125 ±0.0078 | -0.0056 ±0.0032 | -1.6 | 0.637 | 0.652 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 319 | -0.0405 ±0.0103 | -0.0168 ±0.0043 | -3.9 | 0.705 | 0.730 | |
| month 2026-10 | 50 | -0.0457 ±0.0443 | -0.0174 ±0.0184 | -1.0 | 0.700 | 0.740 | |
| agree (<0.05) | 820 | +0.0001 ±0.0025 | -0.0005 ±0.0008 | +0.0 | 0.709 | 0.707 | |
| mild disagree (0.05-0.10) | 445 | -0.0087 ±0.0086 | -0.0038 ±0.0033 | -1.0 | 0.628 | 0.653 | |
| big disagree (>=0.1) | 244 | -0.0658 ±0.0262 | -0.0275 ±0.0111 | -2.5 | 0.592 | 0.631 | |
| tour: atp | 718 | -0.0056 ±0.0072 | -0.0031 ±0.0029 | -0.8 | 0.652 | 0.667 | |
| tour: wta | 791 | -0.0199 ±0.0073 | -0.0084 ±0.0030 | -2.7 | 0.679 | 0.689 | |

When they disagree by >= 0.1: model closer to the outcome in **94/244** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 17 | 0.066 | 0.176 |
| 0.1-0.2 | 92 | 0.153 | 0.141 |
| 0.2-0.3 | 132 | 0.251 | 0.265 |
| 0.3-0.4 | 196 | 0.353 | 0.362 |
| 0.4-0.5 | 259 | 0.452 | 0.471 |
| 0.5-0.6 | 235 | 0.552 | 0.540 |
| 0.6-0.7 | 223 | 0.647 | 0.623 |
| 0.7-0.8 | 188 | 0.751 | 0.771 |
| 0.8-0.9 | 115 | 0.847 | 0.809 |
| 0.9-1.0 | 52 | 0.932 | 0.942 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 41 | 0.057 | 0.098 |
| 0.1-0.2 | 83 | 0.153 | 0.145 |
| 0.2-0.3 | 152 | 0.255 | 0.270 |
| 0.3-0.4 | 187 | 0.355 | 0.380 |
| 0.4-0.5 | 220 | 0.444 | 0.455 |
| 0.5-0.6 | 214 | 0.555 | 0.523 |
| 0.6-0.7 | 229 | 0.650 | 0.629 |
| 0.7-0.8 | 193 | 0.749 | 0.762 |
| 0.8-0.9 | 126 | 0.846 | 0.833 |
| 0.9-1.0 | 64 | 0.934 | 0.953 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 315 | +0.0210 ±0.0093 | +0.0058 ±0.0029 | +2.3 | 0.749 | 0.740 | |
| top-20 involved | 528 | +0.0038 ±0.0079 | -0.0002 ±0.0028 | +0.5 | 0.730 | 0.730 | |
| kalshi favorite 0.8-0.9 | 208 | +0.0067 ±0.0156 | +0.0014 ±0.0055 | +0.4 | 0.841 | 0.841 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 934 | +0.0008 ±0.0066 | -0.0007 ±0.0027 | +0.1 | 0.658 | 0.666 | |
| agree (<0.05) | 820 | +0.0001 ±0.0025 | -0.0005 ±0.0008 | +0.0 | 0.709 | 0.707 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| big disagree (>=0.1) | 244 | -0.0658 ±0.0262 | -0.0275 ±0.0111 | -2.5 | 0.592 | 0.631 | |
| tour: wta | 791 | -0.0199 ±0.0073 | -0.0084 ±0.0030 | -2.7 | 0.679 | 0.689 | |
| kalshi favorite 0.5-0.6 | 430 | -0.0261 ±0.0088 | -0.0121 ±0.0041 | -3.0 | 0.499 | 0.537 | |
| best rank 21-50 | 518 | -0.0258 ±0.0080 | -0.0107 ±0.0035 | -3.2 | 0.656 | 0.698 | |
| no top-20 player | 981 | -0.0222 ±0.0066 | -0.0089 ±0.0029 | -3.3 | 0.631 | 0.651 | |
| surface: Hard | 659 | -0.0271 ±0.0077 | -0.0107 ±0.0032 | -3.5 | 0.672 | 0.684 | |
| month 2026-09 | 319 | -0.0405 ±0.0103 | -0.0168 ±0.0043 | -3.9 | 0.705 | 0.730 | |
| pred_source: live aligned | 575 | -0.0357 ±0.0080 | -0.0143 ±0.0034 | -4.4 | 0.678 | 0.698 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1509, mean |Δ|=0.0043, p95=0.0100, >0.05 in 24 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0666 (n=319, >0.05: 19) | 2026-10 p95=0.0477 (n=50, >0.05: 3)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1509, d_ll -0.0131 ±0.0051 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 597 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'WTA Seoul': 3, 'ATP Chengdu': 1}
- Unmatched Kalshi names, main draw (40): Akasha Urhobo, Aleksandr Shevchenko, Alevtina Ibragimova, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari
