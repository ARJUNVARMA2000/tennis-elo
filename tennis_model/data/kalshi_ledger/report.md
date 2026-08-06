# Model vs Kalshi — match-by-match scorecard

_Generated 2026-08-06T07:07:25Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1340 | 1235 | 49 | 12 | 44 | 0 | 8 | 15 | 48 | 2026-05-03..2026-08-07 |
| wta | 1354 | 800 | 13 | 504 | 37 | 0 | 3 | 15 | 25 | 2026-05-02..2026-08-06 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1462 | 0.6028 | 0.5925 | -0.0103 ±0.0055 | -0.0045 ±0.0023 | 0.666 | 0.680 |
| atp | 705 | 0.6075 | 0.6158 | +0.0083 ±0.0079 | +0.0032 ±0.0032 | 0.668 | 0.677 |
| wta | 757 | 0.5984 | 0.5708 | -0.0276 ±0.0076 | -0.0116 ±0.0032 | 0.663 | 0.683 |
| pooled/live | 595 | 0.6019 | 0.5794 | -0.0225 ±0.0090 | -0.0084 ±0.0038 | 0.672 | 0.690 |
| pooled/backtest | 867 | 0.6034 | 0.6015 | -0.0019 ±0.0069 | -0.0018 ±0.0028 | 0.661 | 0.673 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live | 595 | -0.0225 ±0.0090 | -0.0084 ±0.0038 | -2.5 | 0.672 | 0.690 | |
| pred_source: backtest | 867 | -0.0019 ±0.0069 | -0.0018 ±0.0028 | -0.3 | 0.661 | 0.673 | |
| top-20 involved | 469 | -0.0025 ±0.0082 | -0.0013 ±0.0029 | -0.3 | 0.745 | 0.739 | |
| no top-20 player | 993 | -0.0139 ±0.0071 | -0.0059 ±0.0030 | -2.0 | 0.628 | 0.652 | |
| both inside top-50 | 293 | +0.0108 ±0.0101 | +0.0049 ±0.0044 | +1.1 | 0.674 | 0.660 | |
| someone outside top-50 | 1169 | -0.0156 ±0.0064 | -0.0068 ±0.0026 | -2.4 | 0.663 | 0.685 | |
| best rank 1-10 | 261 | +0.0102 ±0.0110 | +0.0031 ±0.0034 | +0.9 | 0.755 | 0.751 | |
| best rank 11-20 | 208 | -0.0184 ±0.0124 | -0.0069 ±0.0051 | -1.5 | 0.733 | 0.724 | |
| best rank 21-50 | 496 | -0.0097 ±0.0082 | -0.0032 ±0.0036 | -1.2 | 0.653 | 0.669 | |
| best rank 51-100 | 414 | -0.0059 ±0.0118 | -0.0033 ±0.0051 | -0.5 | 0.607 | 0.628 | |
| best rank 100+ | 83 | -0.0795 ±0.0352 | -0.0354 ±0.0149 | -2.3 | 0.578 | 0.669 | |
| kalshi favorite 0.5-0.6 | 422 | -0.0248 ±0.0098 | -0.0112 ±0.0045 | -2.5 | 0.515 | 0.564 | |
| kalshi favorite 0.6-0.7 | 423 | -0.0032 ±0.0094 | -0.0011 ±0.0043 | -0.3 | 0.615 | 0.617 | |
| kalshi favorite 0.7-0.8 | 327 | -0.0039 ±0.0105 | -0.0016 ±0.0043 | -0.4 | 0.742 | 0.743 | |
| kalshi favorite 0.8-0.9 | 204 | -0.0013 ±0.0175 | -0.0014 ±0.0063 | -0.1 | 0.838 | 0.838 | |
| kalshi favorite 0.9-1.0 | 86 | -0.0195 ±0.0309 | -0.0061 ±0.0078 | -0.6 | 0.953 | 0.942 | |
| surface: Hard | 180 | -0.0238 ±0.0191 | -0.0105 ±0.0080 | -1.2 | 0.622 | 0.633 | |
| surface: Clay | 696 | +0.0025 ±0.0073 | -0.0001 ±0.0029 | +0.3 | 0.670 | 0.690 | |
| surface: Grass | 586 | -0.0213 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.682 | |
| tier: atp250 | 565 | -0.0062 ±0.0096 | -0.0035 ±0.0040 | -0.7 | 0.642 | 0.665 | |
| tier: atp500 | 187 | -0.0151 ±0.0103 | -0.0072 ±0.0046 | -1.5 | 0.610 | 0.623 | |
| tier: grand_slam | 476 | -0.0187 ±0.0107 | -0.0074 ±0.0042 | -1.8 | 0.711 | 0.720 | |
| tier: masters | 234 | +0.0009 ±0.0102 | +0.0014 ±0.0046 | +0.1 | 0.673 | 0.679 | |
| round early (R128-R64) | 582 | -0.0174 ±0.0091 | -0.0064 ±0.0037 | -1.9 | 0.705 | 0.710 | |
| round late (QF-F) | 196 | -0.0108 ±0.0115 | -0.0060 ±0.0050 | -0.9 | 0.622 | 0.638 | |
| round mid (R32-R16) | 662 | -0.0040 ±0.0084 | -0.0024 ±0.0035 | -0.5 | 0.649 | 0.670 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 440 | -0.0249 ±0.0103 | -0.0106 ±0.0044 | -2.4 | 0.641 | 0.662 | |
| month 2026-07 | 438 | -0.0076 ±0.0105 | -0.0018 ±0.0044 | -0.7 | 0.683 | 0.696 | |
| month 2026-08 | 85 | -0.0261 ±0.0194 | -0.0112 ±0.0090 | -1.3 | 0.635 | 0.635 | |
| agree (<0.05) | 691 | +0.0017 ±0.0027 | +0.0002 ±0.0009 | +0.6 | 0.698 | 0.698 | |
| mild disagree (0.05-0.10) | 452 | -0.0036 ±0.0082 | -0.0021 ±0.0032 | -0.4 | 0.647 | 0.666 | |
| big disagree (>=0.1) | 319 | -0.0456 ±0.0214 | -0.0178 ±0.0091 | -2.1 | 0.622 | 0.660 | |
| tour: atp | 705 | +0.0083 ±0.0079 | +0.0032 ±0.0032 | +1.1 | 0.668 | 0.677 | |
| tour: wta | 757 | -0.0276 ±0.0076 | -0.0116 ±0.0032 | -3.7 | 0.663 | 0.683 | |

When they disagree by >= 0.1: model closer to the outcome in **122/319** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 13 | 0.066 | 0.077 |
| 0.1-0.2 | 82 | 0.158 | 0.146 |
| 0.2-0.3 | 134 | 0.250 | 0.224 |
| 0.3-0.4 | 207 | 0.352 | 0.338 |
| 0.4-0.5 | 248 | 0.449 | 0.476 |
| 0.5-0.6 | 241 | 0.550 | 0.564 |
| 0.6-0.7 | 226 | 0.645 | 0.615 |
| 0.7-0.8 | 179 | 0.747 | 0.737 |
| 0.8-0.9 | 103 | 0.845 | 0.845 |
| 0.9-1.0 | 29 | 0.927 | 0.897 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 33 | 0.062 | 0.061 |
| 0.1-0.2 | 86 | 0.151 | 0.116 |
| 0.2-0.3 | 147 | 0.253 | 0.265 |
| 0.3-0.4 | 193 | 0.353 | 0.368 |
| 0.4-0.5 | 214 | 0.442 | 0.435 |
| 0.5-0.6 | 210 | 0.558 | 0.557 |
| 0.6-0.7 | 228 | 0.649 | 0.610 |
| 0.7-0.8 | 180 | 0.746 | 0.750 |
| 0.8-0.9 | 118 | 0.845 | 0.805 |
| 0.9-1.0 | 53 | 0.938 | 0.943 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| both inside top-50 | 293 | +0.0108 ±0.0101 | +0.0049 ±0.0044 | +1.1 | 0.674 | 0.660 | |
| tour: atp | 705 | +0.0083 ±0.0079 | +0.0032 ±0.0032 | +1.1 | 0.668 | 0.677 | |
| best rank 1-10 | 261 | +0.0102 ±0.0110 | +0.0031 ±0.0034 | +0.9 | 0.755 | 0.751 | |
| agree (<0.05) | 691 | +0.0017 ±0.0027 | +0.0002 ±0.0009 | +0.6 | 0.698 | 0.698 | |
| surface: Clay | 696 | +0.0025 ±0.0073 | -0.0001 ±0.0029 | +0.3 | 0.670 | 0.690 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| tier: masters | 234 | +0.0009 ±0.0102 | +0.0014 ±0.0046 | +0.1 | 0.673 | 0.679 | |
| kalshi favorite 0.8-0.9 | 204 | -0.0013 ±0.0175 | -0.0014 ±0.0063 | -0.1 | 0.838 | 0.838 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| big disagree (>=0.1) | 319 | -0.0456 ±0.0214 | -0.0178 ±0.0091 | -2.1 | 0.622 | 0.660 | |
| best rank 100+ | 83 | -0.0795 ±0.0352 | -0.0354 ±0.0149 | -2.3 | 0.578 | 0.669 | |
| surface: Grass | 586 | -0.0213 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.682 | |
| month 2026-06 | 440 | -0.0249 ±0.0103 | -0.0106 ±0.0044 | -2.4 | 0.641 | 0.662 | |
| someone outside top-50 | 1169 | -0.0156 ±0.0064 | -0.0068 ±0.0026 | -2.4 | 0.663 | 0.685 | |
| pred_source: live | 595 | -0.0225 ±0.0090 | -0.0084 ±0.0038 | -2.5 | 0.672 | 0.690 | |
| kalshi favorite 0.5-0.6 | 422 | -0.0248 ±0.0098 | -0.0112 ±0.0045 | -2.5 | 0.515 | 0.564 | |
| tour: wta | 757 | -0.0276 ±0.0076 | -0.0116 ±0.0032 | -3.7 | 0.663 | 0.683 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1462, mean |Δ|=0.0024, p95=0.0090, >0.05 in 6 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0085 (n=440, >0.05: 0) | 2026-07 p95=0.0079 (n=438, >0.05: 1) | 2026-08 p95=0.0182 (n=85, >0.05: 4)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1462, d_ll -0.0103 ±0.0055 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 413 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'WTA Memphis': 9, 'WTA Washington': 8, 'ATP Montreal': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Los Cabos': 1, 'ATP Mallorca': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Alexandra Eala, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Botic Van de Zandschulp, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Carolyn Ansari, Casper Ruud, Caty McNally, Celine Naef, Chloe Paquet, Claire Liu, Clervie Ngounoue, Dalma Galfi
