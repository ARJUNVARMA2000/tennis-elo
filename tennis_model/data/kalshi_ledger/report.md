# Model vs Kalshi — match-by-match scorecard

_Generated 2026-08-11T06:27:59Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1381 | 1304 | 28 | 6 | 43 | 0 | 9 | 15 | 62 | 2026-05-03..2026-08-11 |
| wta | 1395 | 828 | 26 | 505 | 36 | 0 | 4 | 15 | 40 | 2026-05-02..2026-08-11 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1553 | 0.6042 | 0.5940 | -0.0102 ±0.0052 | -0.0045 ±0.0022 | 0.665 | 0.681 |
| atp | 771 | 0.6119 | 0.6185 | +0.0066 ±0.0074 | +0.0022 ±0.0030 | 0.663 | 0.676 |
| wta | 782 | 0.5966 | 0.5698 | -0.0268 ±0.0073 | -0.0112 ±0.0031 | 0.668 | 0.687 |
| pooled/live | 657 | 0.6028 | 0.5812 | -0.0215 ±0.0082 | -0.0081 ±0.0035 | 0.673 | 0.692 |
| pooled/backtest | 896 | 0.6052 | 0.6033 | -0.0019 ±0.0067 | -0.0019 ±0.0027 | 0.660 | 0.674 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live | 657 | -0.0215 ±0.0082 | -0.0081 ±0.0035 | -2.6 | 0.673 | 0.692 | |
| pred_source: backtest | 896 | -0.0019 ±0.0067 | -0.0019 ±0.0027 | -0.3 | 0.660 | 0.674 | |
| top-20 involved | 519 | -0.0016 ±0.0076 | -0.0011 ±0.0027 | -0.2 | 0.743 | 0.739 | |
| no top-20 player | 1034 | -0.0145 ±0.0068 | -0.0062 ±0.0029 | -2.1 | 0.626 | 0.652 | |
| both inside top-50 | 331 | +0.0073 ±0.0092 | +0.0032 ±0.0040 | +0.8 | 0.672 | 0.669 | |
| someone outside top-50 | 1222 | -0.0150 ±0.0061 | -0.0066 ±0.0025 | -2.4 | 0.663 | 0.685 | |
| best rank 1-10 | 285 | +0.0098 ±0.0103 | +0.0027 ±0.0032 | +0.9 | 0.744 | 0.744 | |
| best rank 11-20 | 234 | -0.0156 ±0.0112 | -0.0058 ±0.0046 | -1.4 | 0.741 | 0.733 | |
| best rank 21-50 | 525 | -0.0119 ±0.0079 | -0.0043 ±0.0034 | -1.5 | 0.646 | 0.667 | |
| best rank 51-100 | 426 | -0.0052 ±0.0115 | -0.0030 ±0.0049 | -0.4 | 0.612 | 0.631 | |
| best rank 100+ | 83 | -0.0795 ±0.0352 | -0.0354 ±0.0149 | -2.3 | 0.578 | 0.669 | |
| kalshi favorite 0.5-0.6 | 447 | -0.0242 ±0.0093 | -0.0110 ±0.0043 | -2.6 | 0.520 | 0.573 | |
| kalshi favorite 0.6-0.7 | 453 | -0.0046 ±0.0089 | -0.0017 ±0.0041 | -0.5 | 0.609 | 0.614 | |
| kalshi favorite 0.7-0.8 | 352 | -0.0044 ±0.0099 | -0.0018 ±0.0040 | -0.4 | 0.749 | 0.750 | |
| kalshi favorite 0.8-0.9 | 213 | +0.0014 ±0.0169 | -0.0007 ±0.0061 | +0.1 | 0.831 | 0.831 | |
| kalshi favorite 0.9-1.0 | 88 | -0.0198 ±0.0302 | -0.0061 ±0.0076 | -0.7 | 0.955 | 0.943 | |
| surface: Hard | 271 | -0.0189 ±0.0133 | -0.0089 ±0.0055 | -1.4 | 0.635 | 0.657 | |
| surface: Clay | 696 | +0.0025 ±0.0073 | -0.0001 ±0.0029 | +0.3 | 0.670 | 0.690 | |
| surface: Grass | 586 | -0.0213 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.682 | |
| tier: atp250 | 631 | -0.0068 ±0.0087 | -0.0039 ±0.0037 | -0.8 | 0.639 | 0.666 | |
| tier: atp500 | 187 | -0.0151 ±0.0103 | -0.0072 ±0.0046 | -1.5 | 0.610 | 0.623 | |
| tier: grand_slam | 476 | -0.0187 ±0.0107 | -0.0074 ±0.0042 | -1.8 | 0.711 | 0.720 | |
| tier: masters | 259 | +0.0005 ±0.0094 | +0.0013 ±0.0042 | +0.1 | 0.685 | 0.691 | |
| round early (R128-R64) | 597 | -0.0168 ±0.0089 | -0.0061 ±0.0036 | -1.9 | 0.704 | 0.709 | |
| round late (QF-F) | 212 | -0.0089 ±0.0107 | -0.0050 ±0.0046 | -0.8 | 0.627 | 0.646 | |
| round mid (R32-R16) | 722 | -0.0053 ±0.0078 | -0.0031 ±0.0032 | -0.7 | 0.649 | 0.672 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 440 | -0.0249 ±0.0103 | -0.0106 ±0.0044 | -2.4 | 0.641 | 0.662 | |
| month 2026-07 | 438 | -0.0076 ±0.0105 | -0.0018 ±0.0044 | -0.7 | 0.683 | 0.696 | |
| month 2026-08 | 176 | -0.0175 ±0.0114 | -0.0083 ±0.0051 | -1.5 | 0.648 | 0.670 | |
| agree (<0.05) | 754 | +0.0011 ±0.0026 | -0.0001 ±0.0009 | +0.4 | 0.694 | 0.697 | |
| mild disagree (0.05-0.10) | 473 | -0.0031 ±0.0080 | -0.0020 ±0.0031 | -0.4 | 0.650 | 0.668 | |
| big disagree (>=0.1) | 326 | -0.0468 ±0.0210 | -0.0184 ±0.0090 | -2.2 | 0.621 | 0.664 | |
| tour: atp | 771 | +0.0066 ±0.0074 | +0.0022 ±0.0030 | +0.9 | 0.663 | 0.676 | |
| tour: wta | 782 | -0.0268 ±0.0073 | -0.0112 ±0.0031 | -3.7 | 0.668 | 0.687 | |

When they disagree by >= 0.1: model closer to the outcome in **125/326** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 13 | 0.066 | 0.077 |
| 0.1-0.2 | 85 | 0.158 | 0.153 |
| 0.2-0.3 | 145 | 0.251 | 0.234 |
| 0.3-0.4 | 220 | 0.352 | 0.336 |
| 0.4-0.5 | 268 | 0.450 | 0.474 |
| 0.5-0.6 | 247 | 0.550 | 0.563 |
| 0.6-0.7 | 239 | 0.645 | 0.619 |
| 0.7-0.8 | 191 | 0.746 | 0.738 |
| 0.8-0.9 | 114 | 0.844 | 0.833 |
| 0.9-1.0 | 31 | 0.926 | 0.903 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 33 | 0.062 | 0.061 |
| 0.1-0.2 | 87 | 0.151 | 0.115 |
| 0.2-0.3 | 161 | 0.254 | 0.261 |
| 0.3-0.4 | 209 | 0.353 | 0.383 |
| 0.4-0.5 | 226 | 0.443 | 0.420 |
| 0.5-0.6 | 223 | 0.558 | 0.561 |
| 0.6-0.7 | 242 | 0.649 | 0.616 |
| 0.7-0.8 | 191 | 0.746 | 0.759 |
| 0.8-0.9 | 126 | 0.847 | 0.794 |
| 0.9-1.0 | 55 | 0.937 | 0.945 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 285 | +0.0098 ±0.0103 | +0.0027 ±0.0032 | +0.9 | 0.744 | 0.744 | |
| tour: atp | 771 | +0.0066 ±0.0074 | +0.0022 ±0.0030 | +0.9 | 0.663 | 0.676 | |
| both inside top-50 | 331 | +0.0073 ±0.0092 | +0.0032 ±0.0040 | +0.8 | 0.672 | 0.669 | |
| agree (<0.05) | 754 | +0.0011 ±0.0026 | -0.0001 ±0.0009 | +0.4 | 0.694 | 0.697 | |
| surface: Clay | 696 | +0.0025 ±0.0073 | -0.0001 ±0.0029 | +0.3 | 0.670 | 0.690 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| kalshi favorite 0.8-0.9 | 213 | +0.0014 ±0.0169 | -0.0007 ±0.0061 | +0.1 | 0.831 | 0.831 | |
| tier: masters | 259 | +0.0005 ±0.0094 | +0.0013 ±0.0042 | +0.1 | 0.685 | 0.691 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| big disagree (>=0.1) | 326 | -0.0468 ±0.0210 | -0.0184 ±0.0090 | -2.2 | 0.621 | 0.664 | |
| best rank 100+ | 83 | -0.0795 ±0.0352 | -0.0354 ±0.0149 | -2.3 | 0.578 | 0.669 | |
| surface: Grass | 586 | -0.0213 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.682 | |
| month 2026-06 | 440 | -0.0249 ±0.0103 | -0.0106 ±0.0044 | -2.4 | 0.641 | 0.662 | |
| someone outside top-50 | 1222 | -0.0150 ±0.0061 | -0.0066 ±0.0025 | -2.4 | 0.663 | 0.685 | |
| kalshi favorite 0.5-0.6 | 447 | -0.0242 ±0.0093 | -0.0110 ±0.0043 | -2.6 | 0.520 | 0.573 | |
| pred_source: live | 657 | -0.0215 ±0.0082 | -0.0081 ±0.0035 | -2.6 | 0.673 | 0.692 | |
| tour: wta | 782 | -0.0268 ±0.0073 | -0.0112 ±0.0031 | -3.7 | 0.668 | 0.687 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1553, mean |Δ|=0.0025, p95=0.0090, >0.05 in 7 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0085 (n=440, >0.05: 0) | 2026-07 p95=0.0079 (n=438, >0.05: 1) | 2026-08 p95=0.0150 (n=176, >0.05: 5)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1553, d_ll -0.0102 ±0.0052 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 413 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Montreal': 2, 'ATP Los Cabos': 1, 'ATP Mallorca': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Alexandra Eala, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Andrey Rublev, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Carolyn Ansari, Casper Ruud, Caty McNally, Celine Naef, Chloe Paquet, Claire Liu, Clervie Ngounoue, Dalma Galfi
