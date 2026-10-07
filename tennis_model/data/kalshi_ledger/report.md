# Model vs Kalshi — match-by-match scorecard

_Generated 2026-10-07T09:29:59Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 2038 | 1937 | 28 | 12 | 61 | 0 | 11 | 22 | 44 | 2026-05-03..2026-10-08 |
| wta | 2105 | 1301 | 5 | 743 | 56 | 0 | 10 | 15 | 32 | 2026-05-02..2026-10-08 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1516 | 0.6000 | 0.5854 | -0.0146 ±0.0052 | -0.0064 ±0.0021 | 0.667 | 0.680 |
| atp | 722 | 0.6135 | 0.6069 | -0.0065 ±0.0072 | -0.0034 ±0.0029 | 0.654 | 0.669 |
| wta | 794 | 0.5877 | 0.5657 | -0.0220 ±0.0075 | -0.0092 ±0.0031 | 0.679 | 0.690 |
| pooled/live_aligned | 582 | 0.5911 | 0.5519 | -0.0393 ±0.0084 | -0.0157 ±0.0035 | 0.680 | 0.702 |
| pooled/backtest | 934 | 0.6055 | 0.6062 | +0.0008 ±0.0066 | -0.0007 ±0.0027 | 0.658 | 0.666 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 582 | -0.0393 ±0.0084 | -0.0157 ±0.0035 | -4.7 | 0.680 | 0.702 | |
| pred_source: backtest | 934 | +0.0008 ±0.0066 | -0.0007 ±0.0027 | +0.1 | 0.658 | 0.666 | |
| top-20 involved | 532 | +0.0005 ±0.0084 | -0.0016 ±0.0031 | +0.1 | 0.730 | 0.732 | |
| no top-20 player | 984 | -0.0228 ±0.0066 | -0.0091 ±0.0028 | -3.4 | 0.633 | 0.652 | |
| both inside top-50 | 371 | -0.0149 ±0.0107 | -0.0066 ±0.0045 | -1.4 | 0.662 | 0.664 | |
| someone outside top-50 | 1145 | -0.0145 ±0.0060 | -0.0064 ±0.0024 | -2.4 | 0.669 | 0.685 | |
| best rank 1-10 | 319 | +0.0152 ±0.0106 | +0.0034 ±0.0035 | +1.4 | 0.749 | 0.743 | |
| best rank 11-20 | 213 | -0.0216 ±0.0137 | -0.0090 ±0.0055 | -1.6 | 0.702 | 0.716 | |
| best rank 21-50 | 519 | -0.0257 ±0.0080 | -0.0107 ±0.0035 | -3.2 | 0.657 | 0.698 | |
| best rank 51-100 | 377 | -0.0157 ±0.0112 | -0.0060 ±0.0047 | -1.4 | 0.606 | 0.598 | |
| best rank 100+ | 88 | -0.0357 ±0.0320 | -0.0128 ±0.0136 | -1.1 | 0.602 | 0.608 | |
| kalshi favorite 0.5-0.6 | 431 | -0.0263 ±0.0088 | -0.0122 ±0.0041 | -3.0 | 0.500 | 0.538 | |
| kalshi favorite 0.6-0.7 | 421 | -0.0088 ±0.0091 | -0.0034 ±0.0041 | -1.0 | 0.620 | 0.622 | |
| kalshi favorite 0.7-0.8 | 347 | -0.0085 ±0.0099 | -0.0035 ±0.0040 | -0.9 | 0.745 | 0.749 | |
| kalshi favorite 0.8-0.9 | 209 | +0.0069 ±0.0155 | +0.0015 ±0.0055 | +0.4 | 0.842 | 0.842 | |
| kalshi favorite 0.9-1.0 | 108 | -0.0520 ±0.0313 | -0.0203 ±0.0098 | -1.7 | 0.926 | 0.935 | |
| surface: Hard | 666 | -0.0303 ±0.0081 | -0.0119 ±0.0033 | -3.8 | 0.674 | 0.687 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 474 | -0.0200 ±0.0104 | -0.0083 ±0.0043 | -1.9 | 0.614 | 0.630 | |
| tier: atp500 | 250 | -0.0149 ±0.0103 | -0.0067 ±0.0046 | -1.4 | 0.628 | 0.642 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 281 | -0.0156 ±0.0114 | -0.0053 ±0.0049 | -1.4 | 0.671 | 0.683 | |
| round early (R128-R64) | 595 | -0.0174 ±0.0084 | -0.0074 ±0.0033 | -2.1 | 0.715 | 0.727 | |
| round late (QF-F) | 200 | -0.0065 ±0.0113 | -0.0036 ±0.0050 | -0.6 | 0.645 | 0.650 | |
| round mid (R32-R16) | 699 | -0.0148 ±0.0081 | -0.0066 ±0.0034 | -1.8 | 0.637 | 0.653 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 319 | -0.0405 ±0.0103 | -0.0168 ±0.0043 | -3.9 | 0.705 | 0.730 | |
| month 2026-10 | 57 | -0.0811 ±0.0482 | -0.0313 ±0.0198 | -1.7 | 0.719 | 0.772 | |
| agree (<0.05) | 822 | +0.0003 ±0.0025 | -0.0005 ±0.0008 | +0.1 | 0.709 | 0.707 | |
| mild disagree (0.05-0.10) | 447 | -0.0091 ±0.0085 | -0.0040 ±0.0032 | -1.1 | 0.630 | 0.654 | |
| big disagree (>=0.1) | 247 | -0.0741 ±0.0267 | -0.0306 ±0.0113 | -2.8 | 0.593 | 0.636 | |
| tour: atp | 722 | -0.0065 ±0.0072 | -0.0034 ±0.0029 | -0.9 | 0.654 | 0.669 | |
| tour: wta | 794 | -0.0220 ±0.0075 | -0.0092 ±0.0031 | -2.9 | 0.679 | 0.690 | |

When they disagree by >= 0.1: model closer to the outcome in **94/247** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 17 | 0.066 | 0.176 |
| 0.1-0.2 | 92 | 0.153 | 0.141 |
| 0.2-0.3 | 133 | 0.251 | 0.263 |
| 0.3-0.4 | 196 | 0.353 | 0.362 |
| 0.4-0.5 | 260 | 0.451 | 0.469 |
| 0.5-0.6 | 236 | 0.552 | 0.542 |
| 0.6-0.7 | 224 | 0.647 | 0.625 |
| 0.7-0.8 | 188 | 0.751 | 0.771 |
| 0.8-0.9 | 118 | 0.846 | 0.805 |
| 0.9-1.0 | 52 | 0.932 | 0.942 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 42 | 0.058 | 0.095 |
| 0.1-0.2 | 83 | 0.153 | 0.145 |
| 0.2-0.3 | 153 | 0.255 | 0.268 |
| 0.3-0.4 | 188 | 0.355 | 0.378 |
| 0.4-0.5 | 220 | 0.444 | 0.455 |
| 0.5-0.6 | 215 | 0.556 | 0.526 |
| 0.6-0.7 | 229 | 0.650 | 0.629 |
| 0.7-0.8 | 194 | 0.749 | 0.763 |
| 0.8-0.9 | 127 | 0.846 | 0.835 |
| 0.9-1.0 | 65 | 0.935 | 0.954 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 319 | +0.0152 ±0.0106 | +0.0034 ±0.0035 | +1.4 | 0.749 | 0.743 | |
| kalshi favorite 0.8-0.9 | 209 | +0.0069 ±0.0155 | +0.0015 ±0.0055 | +0.4 | 0.842 | 0.842 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 934 | +0.0008 ±0.0066 | -0.0007 ±0.0027 | +0.1 | 0.658 | 0.666 | |
| agree (<0.05) | 822 | +0.0003 ±0.0025 | -0.0005 ±0.0008 | +0.1 | 0.709 | 0.707 | |
| top-20 involved | 532 | +0.0005 ±0.0084 | -0.0016 ±0.0031 | +0.1 | 0.730 | 0.732 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| big disagree (>=0.1) | 247 | -0.0741 ±0.0267 | -0.0306 ±0.0113 | -2.8 | 0.593 | 0.636 | |
| tour: wta | 794 | -0.0220 ±0.0075 | -0.0092 ±0.0031 | -2.9 | 0.679 | 0.690 | |
| kalshi favorite 0.5-0.6 | 431 | -0.0263 ±0.0088 | -0.0122 ±0.0041 | -3.0 | 0.500 | 0.538 | |
| best rank 21-50 | 519 | -0.0257 ±0.0080 | -0.0107 ±0.0035 | -3.2 | 0.657 | 0.698 | |
| no top-20 player | 984 | -0.0228 ±0.0066 | -0.0091 ±0.0028 | -3.4 | 0.633 | 0.652 | |
| surface: Hard | 666 | -0.0303 ±0.0081 | -0.0119 ±0.0033 | -3.8 | 0.674 | 0.687 | |
| month 2026-09 | 319 | -0.0405 ±0.0103 | -0.0168 ±0.0043 | -3.9 | 0.705 | 0.730 | |
| pred_source: live aligned | 582 | -0.0393 ±0.0084 | -0.0157 ±0.0035 | -4.7 | 0.680 | 0.702 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1516, mean |Δ|=0.0047, p95=0.0100, >0.05 in 26 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0666 (n=319, >0.05: 19) | 2026-10 p95=0.2160 (n=57, >0.05: 5)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1516, d_ll -0.0146 ±0.0052 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 597 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'WTA Seoul': 3, 'ATP Chengdu': 1}
- Unmatched Kalshi names, main draw (40): Akasha Urhobo, Aleksandr Shevchenko, Alevtina Ibragimova, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari
