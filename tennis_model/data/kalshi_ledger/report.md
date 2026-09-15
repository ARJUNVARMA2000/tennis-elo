# Model vs Kalshi — match-by-match scorecard

_Generated 2026-09-15T08:24:32Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1801 | 1734 | 0 | 10 | 57 | 0 | 11 | 19 | 43 | 2026-05-03..2026-09-13 |
| wta | 1850 | 1103 | 44 | 655 | 48 | 0 | 7 | 15 | 25 | 2026-05-02..2026-09-15 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1282 | 0.5965 | 0.5916 | -0.0049 ±0.0053 | -0.0028 ±0.0022 | 0.668 | 0.676 |
| atp | 628 | 0.6198 | 0.6196 | -0.0002 ±0.0073 | -0.0012 ±0.0029 | 0.650 | 0.665 |
| wta | 654 | 0.5742 | 0.5647 | -0.0095 ±0.0078 | -0.0044 ±0.0032 | 0.687 | 0.687 |
| pooled/live_aligned | 359 | 0.5704 | 0.5510 | -0.0194 ±0.0083 | -0.0081 ±0.0034 | 0.694 | 0.701 |
| pooled/backtest | 923 | 0.6067 | 0.6074 | +0.0007 ±0.0067 | -0.0008 ±0.0027 | 0.659 | 0.667 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 359 | -0.0194 ±0.0083 | -0.0081 ±0.0034 | -2.4 | 0.694 | 0.701 | |
| pred_source: backtest | 923 | +0.0007 ±0.0067 | -0.0008 ±0.0027 | +0.1 | 0.659 | 0.667 | |
| top-20 involved | 468 | +0.0081 ±0.0076 | +0.0013 ±0.0025 | +1.1 | 0.734 | 0.732 | |
| no top-20 player | 814 | -0.0124 ±0.0072 | -0.0052 ±0.0031 | -1.7 | 0.631 | 0.644 | |
| both inside top-50 | 312 | +0.0009 ±0.0089 | -0.0003 ±0.0038 | +0.1 | 0.665 | 0.655 | |
| someone outside top-50 | 970 | -0.0068 ±0.0064 | -0.0036 ±0.0026 | -1.1 | 0.670 | 0.683 | |
| best rank 1-10 | 283 | +0.0217 ±0.0101 | +0.0055 ±0.0030 | +2.1 | 0.746 | 0.739 | |
| best rank 11-20 | 185 | -0.0127 ±0.0111 | -0.0050 ±0.0042 | -1.1 | 0.716 | 0.722 | |
| best rank 21-50 | 447 | -0.0158 ±0.0081 | -0.0064 ±0.0036 | -2.0 | 0.653 | 0.683 | |
| best rank 51-100 | 305 | -0.0080 ±0.0129 | -0.0037 ±0.0055 | -0.6 | 0.602 | 0.597 | |
| best rank 100+ | 62 | -0.0099 ±0.0382 | -0.0038 ±0.0165 | -0.3 | 0.613 | 0.597 | |
| kalshi favorite 0.5-0.6 | 364 | -0.0235 ±0.0092 | -0.0110 ±0.0043 | -2.6 | 0.501 | 0.538 | |
| kalshi favorite 0.6-0.7 | 352 | -0.0033 ±0.0096 | -0.0011 ±0.0044 | -0.3 | 0.625 | 0.622 | |
| kalshi favorite 0.7-0.8 | 300 | -0.0025 ±0.0093 | -0.0009 ±0.0037 | -0.3 | 0.742 | 0.740 | |
| kalshi favorite 0.8-0.9 | 183 | +0.0161 ±0.0169 | +0.0051 ±0.0059 | +1.0 | 0.842 | 0.836 | |
| kalshi favorite 0.9-1.0 | 83 | +0.0147 ±0.0309 | +0.0014 ±0.0078 | +0.5 | 0.940 | 0.928 | |
| surface: Hard | 432 | -0.0100 ±0.0083 | -0.0042 ±0.0034 | -1.2 | 0.683 | 0.679 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 332 | -0.0048 ±0.0119 | -0.0030 ±0.0050 | -0.4 | 0.596 | 0.607 | |
| tier: atp500 | 215 | -0.0077 ±0.0100 | -0.0039 ±0.0045 | -0.8 | 0.614 | 0.621 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| round early (R128-R64) | 549 | -0.0098 ±0.0086 | -0.0045 ±0.0034 | -1.1 | 0.724 | 0.731 | |
| round late (QF-F) | 150 | +0.0006 ±0.0116 | -0.0007 ±0.0051 | +0.1 | 0.647 | 0.633 | |
| round mid (R32-R16) | 561 | -0.0016 ±0.0081 | -0.0018 ±0.0034 | -0.2 | 0.627 | 0.639 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 142 | -0.0120 ±0.0114 | -0.0071 ±0.0046 | -1.0 | 0.789 | 0.796 | |
| agree (<0.05) | 692 | +0.0002 ±0.0027 | -0.0006 ±0.0009 | +0.1 | 0.712 | 0.707 | |
| mild disagree (0.05-0.10) | 386 | -0.0109 ±0.0094 | -0.0054 ±0.0035 | -1.2 | 0.615 | 0.650 | |
| big disagree (>=0.1) | 204 | -0.0109 ±0.0269 | -0.0056 ±0.0115 | -0.4 | 0.620 | 0.620 | |
| tour: atp | 628 | -0.0002 ±0.0073 | -0.0012 ±0.0029 | -0.0 | 0.650 | 0.665 | |
| tour: wta | 654 | -0.0095 ±0.0078 | -0.0044 ±0.0032 | -1.2 | 0.687 | 0.687 | |

When they disagree by >= 0.1: model closer to the outcome in **87/204** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 14 | 0.067 | 0.143 |
| 0.1-0.2 | 80 | 0.153 | 0.138 |
| 0.2-0.3 | 110 | 0.254 | 0.255 |
| 0.3-0.4 | 164 | 0.354 | 0.348 |
| 0.4-0.5 | 223 | 0.451 | 0.471 |
| 0.5-0.6 | 205 | 0.551 | 0.541 |
| 0.6-0.7 | 187 | 0.647 | 0.626 |
| 0.7-0.8 | 154 | 0.750 | 0.760 |
| 0.8-0.9 | 99 | 0.848 | 0.818 |
| 0.9-1.0 | 46 | 0.933 | 0.935 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 30 | 0.060 | 0.100 |
| 0.1-0.2 | 74 | 0.153 | 0.135 |
| 0.2-0.3 | 130 | 0.256 | 0.269 |
| 0.3-0.4 | 158 | 0.355 | 0.380 |
| 0.4-0.5 | 189 | 0.444 | 0.450 |
| 0.5-0.6 | 178 | 0.555 | 0.517 |
| 0.6-0.7 | 191 | 0.648 | 0.634 |
| 0.7-0.8 | 170 | 0.749 | 0.747 |
| 0.8-0.9 | 110 | 0.846 | 0.818 |
| 0.9-1.0 | 52 | 0.932 | 0.942 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 283 | +0.0217 ±0.0101 | +0.0055 ±0.0030 | +2.1 | 0.746 | 0.739 | |
| top-20 involved | 468 | +0.0081 ±0.0076 | +0.0013 ±0.0025 | +1.1 | 0.734 | 0.732 | |
| kalshi favorite 0.8-0.9 | 183 | +0.0161 ±0.0169 | +0.0051 ±0.0059 | +1.0 | 0.842 | 0.836 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| kalshi favorite 0.9-1.0 | 83 | +0.0147 ±0.0309 | +0.0014 ±0.0078 | +0.5 | 0.940 | 0.928 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 923 | +0.0007 ±0.0067 | -0.0008 ±0.0027 | +0.1 | 0.659 | 0.667 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| round early (R128-R64) | 549 | -0.0098 ±0.0086 | -0.0045 ±0.0034 | -1.1 | 0.724 | 0.731 | |
| mild disagree (0.05-0.10) | 386 | -0.0109 ±0.0094 | -0.0054 ±0.0035 | -1.2 | 0.615 | 0.650 | |
| surface: Hard | 432 | -0.0100 ±0.0083 | -0.0042 ±0.0034 | -1.2 | 0.683 | 0.679 | |
| tour: wta | 654 | -0.0095 ±0.0078 | -0.0044 ±0.0032 | -1.2 | 0.687 | 0.687 | |
| no top-20 player | 814 | -0.0124 ±0.0072 | -0.0052 ±0.0031 | -1.7 | 0.631 | 0.644 | |
| best rank 21-50 | 447 | -0.0158 ±0.0081 | -0.0064 ±0.0036 | -2.0 | 0.653 | 0.683 | |
| pred_source: live aligned | 359 | -0.0194 ±0.0083 | -0.0081 ±0.0034 | -2.4 | 0.694 | 0.701 | |
| kalshi favorite 0.5-0.6 | 364 | -0.0235 ±0.0092 | -0.0110 ±0.0043 | -2.6 | 0.501 | 0.538 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1282, mean |Δ|=0.0017, p95=0.0086, >0.05 in 2 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0040 (n=142, >0.05: 0)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1282, d_ll -0.0049 ±0.0053 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 512 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Cincinnati': 1, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): Akasha Urhobo, Aleksandr Shevchenko, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari, Carson Branstine
