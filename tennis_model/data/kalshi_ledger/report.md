# Model vs Kalshi — match-by-match scorecard

_Generated 2026-08-17T06:47:38Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1471 | 1409 | 9 | 7 | 46 | 0 | 9 | 15 | 48 | 2026-05-03..2026-08-17 |
| wta | 1484 | 896 | 10 | 540 | 38 | 0 | 5 | 15 | 26 | 2026-05-02..2026-08-17 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1684 | 0.6062 | 0.5954 | -0.0109 ±0.0050 | -0.0048 ±0.0021 | 0.666 | 0.680 |
| atp | 837 | 0.6165 | 0.6201 | +0.0037 ±0.0069 | +0.0010 ±0.0028 | 0.661 | 0.676 |
| wta | 847 | 0.5961 | 0.5709 | -0.0253 ±0.0071 | -0.0104 ±0.0030 | 0.671 | 0.684 |
| pooled/live | 780 | 0.6069 | 0.5855 | -0.0214 ±0.0074 | -0.0082 ±0.0031 | 0.672 | 0.689 |
| pooled/backtest | 904 | 0.6057 | 0.6039 | -0.0018 ±0.0067 | -0.0018 ±0.0027 | 0.660 | 0.672 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live | 780 | -0.0214 ±0.0074 | -0.0082 ±0.0031 | -2.9 | 0.672 | 0.689 | |
| pred_source: backtest | 904 | -0.0018 ±0.0067 | -0.0018 ±0.0027 | -0.3 | 0.660 | 0.672 | |
| top-20 involved | 560 | -0.0013 ±0.0073 | -0.0007 ±0.0026 | -0.2 | 0.747 | 0.743 | |
| no top-20 player | 1124 | -0.0156 ±0.0065 | -0.0068 ±0.0028 | -2.4 | 0.625 | 0.649 | |
| both inside top-50 | 361 | +0.0053 ±0.0088 | +0.0023 ±0.0039 | +0.6 | 0.675 | 0.676 | |
| someone outside top-50 | 1323 | -0.0153 ±0.0058 | -0.0067 ±0.0024 | -2.6 | 0.663 | 0.681 | |
| best rank 1-10 | 306 | +0.0114 ±0.0098 | +0.0036 ±0.0031 | +1.2 | 0.755 | 0.750 | |
| best rank 11-20 | 254 | -0.0167 ±0.0109 | -0.0059 ±0.0044 | -1.5 | 0.738 | 0.734 | |
| best rank 21-50 | 582 | -0.0132 ±0.0075 | -0.0050 ±0.0033 | -1.8 | 0.646 | 0.671 | |
| best rank 51-100 | 459 | -0.0072 ±0.0109 | -0.0038 ±0.0047 | -0.7 | 0.607 | 0.617 | |
| best rank 100+ | 83 | -0.0795 ±0.0352 | -0.0354 ±0.0149 | -2.3 | 0.578 | 0.669 | |
| kalshi favorite 0.5-0.6 | 497 | -0.0249 ±0.0088 | -0.0114 ±0.0041 | -2.8 | 0.530 | 0.573 | |
| kalshi favorite 0.6-0.7 | 495 | -0.0046 ±0.0085 | -0.0017 ±0.0039 | -0.5 | 0.610 | 0.616 | |
| kalshi favorite 0.7-0.8 | 380 | -0.0032 ±0.0092 | -0.0015 ±0.0037 | -0.3 | 0.751 | 0.753 | |
| kalshi favorite 0.8-0.9 | 221 | -0.0032 ±0.0166 | -0.0019 ±0.0059 | -0.2 | 0.828 | 0.828 | |
| kalshi favorite 0.9-1.0 | 91 | -0.0192 ±0.0292 | -0.0059 ±0.0074 | -0.7 | 0.956 | 0.945 | |
| surface: Hard | 402 | -0.0189 ±0.0103 | -0.0084 ±0.0043 | -1.8 | 0.647 | 0.659 | |
| surface: Clay | 696 | +0.0025 ±0.0073 | -0.0001 ±0.0029 | +0.3 | 0.670 | 0.690 | |
| surface: Grass | 586 | -0.0213 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.682 | |
| tier: atp250 | 696 | -0.0093 ±0.0081 | -0.0049 ±0.0034 | -1.1 | 0.638 | 0.667 | |
| tier: atp500 | 187 | -0.0151 ±0.0103 | -0.0072 ±0.0046 | -1.5 | 0.610 | 0.623 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 476 | -0.0187 ±0.0107 | -0.0074 ±0.0042 | -1.8 | 0.711 | 0.720 | |
| tier: masters | 324 | -0.0009 ±0.0091 | +0.0008 ±0.0040 | -0.1 | 0.690 | 0.682 | |
| round early (R128-R64) | 660 | -0.0175 ±0.0084 | -0.0066 ±0.0034 | -2.1 | 0.695 | 0.695 | |
| round late (QF-F) | 221 | -0.0079 ±0.0106 | -0.0044 ±0.0046 | -0.7 | 0.633 | 0.649 | |
| round mid (R32-R16) | 781 | -0.0063 ±0.0074 | -0.0034 ±0.0031 | -0.8 | 0.655 | 0.680 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 440 | -0.0249 ±0.0103 | -0.0106 ±0.0044 | -2.4 | 0.641 | 0.662 | |
| month 2026-07 | 438 | -0.0076 ±0.0105 | -0.0018 ±0.0044 | -0.7 | 0.683 | 0.696 | |
| month 2026-08 | 307 | -0.0180 ±0.0094 | -0.0079 ±0.0041 | -1.9 | 0.658 | 0.668 | |
| agree (<0.05) | 812 | +0.0007 ±0.0025 | -0.0002 ±0.0009 | +0.3 | 0.697 | 0.699 | |
| mild disagree (0.05-0.10) | 520 | -0.0037 ±0.0077 | -0.0021 ±0.0030 | -0.5 | 0.653 | 0.671 | |
| big disagree (>=0.1) | 352 | -0.0483 ±0.0200 | -0.0193 ±0.0086 | -2.4 | 0.612 | 0.649 | |
| tour: atp | 837 | +0.0037 ±0.0069 | +0.0010 ±0.0028 | +0.5 | 0.661 | 0.676 | |
| tour: wta | 847 | -0.0253 ±0.0071 | -0.0104 ±0.0030 | -3.6 | 0.671 | 0.684 | |

When they disagree by >= 0.1: model closer to the outcome in **137/352** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 14 | 0.065 | 0.071 |
| 0.1-0.2 | 91 | 0.159 | 0.143 |
| 0.2-0.3 | 155 | 0.252 | 0.239 |
| 0.3-0.4 | 241 | 0.351 | 0.340 |
| 0.4-0.5 | 286 | 0.451 | 0.465 |
| 0.5-0.6 | 269 | 0.550 | 0.572 |
| 0.6-0.7 | 259 | 0.645 | 0.606 |
| 0.7-0.8 | 211 | 0.747 | 0.744 |
| 0.8-0.9 | 123 | 0.844 | 0.821 |
| 0.9-1.0 | 35 | 0.925 | 0.886 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 34 | 0.061 | 0.059 |
| 0.1-0.2 | 88 | 0.152 | 0.114 |
| 0.2-0.3 | 173 | 0.254 | 0.260 |
| 0.3-0.4 | 225 | 0.353 | 0.373 |
| 0.4-0.5 | 247 | 0.443 | 0.417 |
| 0.5-0.6 | 253 | 0.557 | 0.561 |
| 0.6-0.7 | 267 | 0.649 | 0.610 |
| 0.7-0.8 | 207 | 0.746 | 0.763 |
| 0.8-0.9 | 133 | 0.847 | 0.789 |
| 0.9-1.0 | 57 | 0.937 | 0.947 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 306 | +0.0114 ±0.0098 | +0.0036 ±0.0031 | +1.2 | 0.755 | 0.750 | |
| both inside top-50 | 361 | +0.0053 ±0.0088 | +0.0023 ±0.0039 | +0.6 | 0.675 | 0.676 | |
| tour: atp | 837 | +0.0037 ±0.0069 | +0.0010 ±0.0028 | +0.5 | 0.661 | 0.676 | |
| surface: Clay | 696 | +0.0025 ±0.0073 | -0.0001 ±0.0029 | +0.3 | 0.670 | 0.690 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| agree (<0.05) | 812 | +0.0007 ±0.0025 | -0.0002 ±0.0009 | +0.3 | 0.697 | 0.699 | |
| tier: masters | 324 | -0.0009 ±0.0091 | +0.0008 ±0.0040 | -0.1 | 0.690 | 0.682 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| no top-20 player | 1124 | -0.0156 ±0.0065 | -0.0068 ±0.0028 | -2.4 | 0.625 | 0.649 | |
| big disagree (>=0.1) | 352 | -0.0483 ±0.0200 | -0.0193 ±0.0086 | -2.4 | 0.612 | 0.649 | |
| surface: Grass | 586 | -0.0213 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.682 | |
| month 2026-06 | 440 | -0.0249 ±0.0103 | -0.0106 ±0.0044 | -2.4 | 0.641 | 0.662 | |
| someone outside top-50 | 1323 | -0.0153 ±0.0058 | -0.0067 ±0.0024 | -2.6 | 0.663 | 0.681 | |
| kalshi favorite 0.5-0.6 | 497 | -0.0249 ±0.0088 | -0.0114 ±0.0041 | -2.8 | 0.530 | 0.573 | |
| pred_source: live | 780 | -0.0214 ±0.0074 | -0.0082 ±0.0031 | -2.9 | 0.672 | 0.689 | |
| tour: wta | 847 | -0.0253 ±0.0071 | -0.0104 ±0.0030 | -3.6 | 0.671 | 0.684 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1684, mean |Δ|=0.0025, p95=0.0091, >0.05 in 7 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0085 (n=440, >0.05: 0) | 2026-07 p95=0.0079 (n=438, >0.05: 1) | 2026-08 p95=0.0121 (n=307, >0.05: 5)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1684, d_ll -0.0109 ±0.0050 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 450 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Cincinnati': 1, 'ATP Mallorca': 1, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Alexandra Eala, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Carolyn Ansari, Casper Ruud, Caty McNally, Celine Naef, Chloe Paquet, Claire Liu, Clervie Ngounoue, Dalma Galfi, Daphnee Mpetshi Perricard
