# Model vs Kalshi — match-by-match scorecard

_Generated 2026-08-14T07:03:03Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1430 | 1357 | 24 | 4 | 45 | 0 | 9 | 15 | 52 | 2026-05-03..2026-08-14 |
| wta | 1443 | 846 | 54 | 505 | 38 | 0 | 5 | 15 | 29 | 2026-05-02..2026-08-15 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1585 | 0.6059 | 0.5953 | -0.0106 ±0.0051 | -0.0047 ±0.0021 | 0.664 | 0.680 |
| atp | 787 | 0.6134 | 0.6191 | +0.0057 ±0.0073 | +0.0018 ±0.0030 | 0.661 | 0.676 |
| wta | 798 | 0.5986 | 0.5719 | -0.0266 ±0.0073 | -0.0111 ±0.0030 | 0.667 | 0.684 |
| pooled/live | 688 | 0.6071 | 0.5850 | -0.0220 ±0.0080 | -0.0084 ±0.0034 | 0.669 | 0.688 |
| pooled/backtest | 897 | 0.6050 | 0.6032 | -0.0018 ±0.0067 | -0.0018 ±0.0027 | 0.660 | 0.674 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live | 688 | -0.0220 ±0.0080 | -0.0084 ±0.0034 | -2.8 | 0.669 | 0.688 | |
| pred_source: backtest | 897 | -0.0018 ±0.0067 | -0.0018 ±0.0027 | -0.3 | 0.660 | 0.674 | |
| top-20 involved | 528 | -0.0013 ±0.0076 | -0.0010 ±0.0027 | -0.2 | 0.743 | 0.739 | |
| no top-20 player | 1057 | -0.0152 ±0.0067 | -0.0065 ±0.0029 | -2.3 | 0.624 | 0.650 | |
| both inside top-50 | 341 | +0.0071 ±0.0091 | +0.0032 ±0.0040 | +0.8 | 0.673 | 0.669 | |
| someone outside top-50 | 1244 | -0.0154 ±0.0061 | -0.0068 ±0.0025 | -2.5 | 0.661 | 0.683 | |
| best rank 1-10 | 290 | +0.0106 ±0.0103 | +0.0032 ±0.0032 | +1.0 | 0.748 | 0.743 | |
| best rank 11-20 | 238 | -0.0159 ±0.0112 | -0.0060 ±0.0046 | -1.4 | 0.737 | 0.733 | |
| best rank 21-50 | 533 | -0.0130 ±0.0078 | -0.0048 ±0.0034 | -1.7 | 0.645 | 0.670 | |
| best rank 51-100 | 441 | -0.0057 ±0.0112 | -0.0032 ±0.0048 | -0.5 | 0.607 | 0.624 | |
| best rank 100+ | 83 | -0.0795 ±0.0352 | -0.0354 ±0.0149 | -2.3 | 0.578 | 0.669 | |
| kalshi favorite 0.5-0.6 | 465 | -0.0245 ±0.0091 | -0.0111 ±0.0042 | -2.7 | 0.524 | 0.573 | |
| kalshi favorite 0.6-0.7 | 464 | -0.0042 ±0.0088 | -0.0016 ±0.0040 | -0.5 | 0.608 | 0.614 | |
| kalshi favorite 0.7-0.8 | 354 | -0.0051 ±0.0098 | -0.0021 ±0.0040 | -0.5 | 0.747 | 0.749 | |
| kalshi favorite 0.8-0.9 | 214 | +0.0006 ±0.0169 | -0.0010 ±0.0060 | +0.0 | 0.832 | 0.832 | |
| kalshi favorite 0.9-1.0 | 88 | -0.0198 ±0.0302 | -0.0061 ±0.0076 | -0.7 | 0.955 | 0.943 | |
| surface: Hard | 303 | -0.0198 ±0.0123 | -0.0092 ±0.0052 | -1.6 | 0.630 | 0.652 | |
| surface: Clay | 696 | +0.0025 ±0.0073 | -0.0001 ±0.0029 | +0.3 | 0.670 | 0.690 | |
| surface: Grass | 586 | -0.0213 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.682 | |
| tier: atp250 | 646 | -0.0078 ±0.0086 | -0.0044 ±0.0036 | -0.9 | 0.636 | 0.666 | |
| tier: atp500 | 187 | -0.0151 ±0.0103 | -0.0072 ±0.0046 | -1.5 | 0.610 | 0.623 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 476 | -0.0187 ±0.0107 | -0.0074 ±0.0042 | -1.8 | 0.711 | 0.720 | |
| tier: masters | 275 | -0.0005 ±0.0092 | +0.0008 ±0.0042 | -0.1 | 0.682 | 0.682 | |
| round early (R128-R64) | 620 | -0.0178 ±0.0087 | -0.0066 ±0.0035 | -2.1 | 0.698 | 0.704 | |
| round late (QF-F) | 221 | -0.0079 ±0.0106 | -0.0044 ±0.0046 | -0.7 | 0.633 | 0.649 | |
| round mid (R32-R16) | 722 | -0.0053 ±0.0078 | -0.0031 ±0.0032 | -0.7 | 0.649 | 0.672 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 440 | -0.0249 ±0.0103 | -0.0106 ±0.0044 | -2.4 | 0.641 | 0.662 | |
| month 2026-07 | 438 | -0.0076 ±0.0105 | -0.0018 ±0.0044 | -0.7 | 0.683 | 0.696 | |
| month 2026-08 | 208 | -0.0190 ±0.0107 | -0.0089 ±0.0048 | -1.8 | 0.639 | 0.661 | |
| agree (<0.05) | 767 | +0.0015 ±0.0026 | +0.0001 ±0.0009 | +0.6 | 0.694 | 0.697 | |
| mild disagree (0.05-0.10) | 483 | -0.0038 ±0.0079 | -0.0023 ±0.0031 | -0.5 | 0.649 | 0.665 | |
| big disagree (>=0.1) | 335 | -0.0480 ±0.0206 | -0.0191 ±0.0088 | -2.3 | 0.616 | 0.663 | |
| tour: atp | 787 | +0.0057 ±0.0073 | +0.0018 ±0.0030 | +0.8 | 0.661 | 0.676 | |
| tour: wta | 798 | -0.0266 ±0.0073 | -0.0111 ±0.0030 | -3.7 | 0.667 | 0.684 | |

When they disagree by >= 0.1: model closer to the outcome in **128/335** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 13 | 0.066 | 0.077 |
| 0.1-0.2 | 85 | 0.158 | 0.153 |
| 0.2-0.3 | 147 | 0.252 | 0.231 |
| 0.3-0.4 | 227 | 0.351 | 0.335 |
| 0.4-0.5 | 275 | 0.450 | 0.473 |
| 0.5-0.6 | 255 | 0.549 | 0.569 |
| 0.6-0.7 | 245 | 0.645 | 0.608 |
| 0.7-0.8 | 193 | 0.746 | 0.736 |
| 0.8-0.9 | 114 | 0.844 | 0.833 |
| 0.9-1.0 | 31 | 0.926 | 0.903 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 33 | 0.062 | 0.061 |
| 0.1-0.2 | 88 | 0.152 | 0.114 |
| 0.2-0.3 | 162 | 0.254 | 0.259 |
| 0.3-0.4 | 215 | 0.353 | 0.381 |
| 0.4-0.5 | 235 | 0.443 | 0.417 |
| 0.5-0.6 | 233 | 0.558 | 0.562 |
| 0.6-0.7 | 246 | 0.649 | 0.614 |
| 0.7-0.8 | 192 | 0.746 | 0.755 |
| 0.8-0.9 | 126 | 0.847 | 0.794 |
| 0.9-1.0 | 55 | 0.937 | 0.945 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 290 | +0.0106 ±0.0103 | +0.0032 ±0.0032 | +1.0 | 0.748 | 0.743 | |
| tour: atp | 787 | +0.0057 ±0.0073 | +0.0018 ±0.0030 | +0.8 | 0.661 | 0.676 | |
| both inside top-50 | 341 | +0.0071 ±0.0091 | +0.0032 ±0.0040 | +0.8 | 0.673 | 0.669 | |
| agree (<0.05) | 767 | +0.0015 ±0.0026 | +0.0001 ±0.0009 | +0.6 | 0.694 | 0.697 | |
| surface: Clay | 696 | +0.0025 ±0.0073 | -0.0001 ±0.0029 | +0.3 | 0.670 | 0.690 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| kalshi favorite 0.8-0.9 | 214 | +0.0006 ±0.0169 | -0.0010 ±0.0060 | +0.0 | 0.832 | 0.832 | |
| tier: masters | 275 | -0.0005 ±0.0092 | +0.0008 ±0.0042 | -0.1 | 0.682 | 0.682 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 100+ | 83 | -0.0795 ±0.0352 | -0.0354 ±0.0149 | -2.3 | 0.578 | 0.669 | |
| big disagree (>=0.1) | 335 | -0.0480 ±0.0206 | -0.0191 ±0.0088 | -2.3 | 0.616 | 0.663 | |
| surface: Grass | 586 | -0.0213 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.682 | |
| month 2026-06 | 440 | -0.0249 ±0.0103 | -0.0106 ±0.0044 | -2.4 | 0.641 | 0.662 | |
| someone outside top-50 | 1244 | -0.0154 ±0.0061 | -0.0068 ±0.0025 | -2.5 | 0.661 | 0.683 | |
| kalshi favorite 0.5-0.6 | 465 | -0.0245 ±0.0091 | -0.0111 ±0.0042 | -2.7 | 0.524 | 0.573 | |
| pred_source: live | 688 | -0.0220 ±0.0080 | -0.0084 ±0.0034 | -2.8 | 0.669 | 0.688 | |
| tour: wta | 798 | -0.0266 ±0.0073 | -0.0111 ±0.0030 | -3.7 | 0.667 | 0.684 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1585, mean |Δ|=0.0025, p95=0.0091, >0.05 in 7 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0085 (n=440, >0.05: 0) | 2026-07 p95=0.0079 (n=438, >0.05: 1) | 2026-08 p95=0.0150 (n=208, >0.05: 5)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1585, d_ll -0.0106 ±0.0051 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 413 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Mallorca': 1, 'ATP Los Cabos': 1, 'WTA Toronto': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Alexandra Eala, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Carolyn Ansari, Casper Ruud, Caty McNally, Celine Naef, Chloe Paquet, Claire Liu, Clervie Ngounoue, Dalma Galfi, Daphnee Mpetshi Perricard
