# Model vs Kalshi — match-by-match scorecard

_Generated 2026-08-05T07:04:25Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1328 | 1235 | 38 | 12 | 43 | 0 | 8 | 15 | 56 | 2026-05-03..2026-08-06 |
| wta | 1343 | 783 | 19 | 504 | 37 | 0 | 3 | 15 | 25 | 2026-05-02..2026-08-05 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1446 | 0.6039 | 0.5935 | -0.0104 ±0.0055 | -0.0045 ±0.0023 | 0.665 | 0.680 |
| atp | 705 | 0.6075 | 0.6158 | +0.0083 ±0.0079 | +0.0032 ±0.0032 | 0.668 | 0.677 |
| wta | 741 | 0.6005 | 0.5723 | -0.0282 ±0.0077 | -0.0118 ±0.0032 | 0.663 | 0.683 |
| pooled/live | 580 | 0.6061 | 0.5831 | -0.0230 ±0.0092 | -0.0085 ±0.0039 | 0.671 | 0.689 |
| pooled/backtest | 866 | 0.6025 | 0.6005 | -0.0019 ±0.0069 | -0.0018 ±0.0028 | 0.662 | 0.674 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live | 580 | -0.0230 ±0.0092 | -0.0085 ±0.0039 | -2.5 | 0.671 | 0.689 | |
| pred_source: backtest | 866 | -0.0019 ±0.0069 | -0.0018 ±0.0028 | -0.3 | 0.662 | 0.674 | |
| top-20 involved | 460 | -0.0021 ±0.0084 | -0.0012 ±0.0030 | -0.3 | 0.745 | 0.738 | |
| no top-20 player | 986 | -0.0142 ±0.0071 | -0.0060 ±0.0031 | -2.0 | 0.628 | 0.653 | |
| both inside top-50 | 291 | +0.0108 ±0.0102 | +0.0049 ±0.0045 | +1.1 | 0.675 | 0.662 | |
| someone outside top-50 | 1155 | -0.0157 ±0.0064 | -0.0068 ±0.0026 | -2.4 | 0.663 | 0.684 | |
| best rank 1-10 | 256 | +0.0098 ±0.0112 | +0.0030 ±0.0035 | +0.9 | 0.754 | 0.750 | |
| best rank 11-20 | 204 | -0.0171 ±0.0126 | -0.0065 ±0.0052 | -1.4 | 0.733 | 0.723 | |
| best rank 21-50 | 490 | -0.0099 ±0.0083 | -0.0032 ±0.0036 | -1.2 | 0.655 | 0.671 | |
| best rank 51-100 | 413 | -0.0062 ±0.0119 | -0.0034 ±0.0051 | -0.5 | 0.607 | 0.627 | |
| best rank 100+ | 83 | -0.0795 ±0.0352 | -0.0354 ±0.0149 | -2.3 | 0.578 | 0.669 | |
| kalshi favorite 0.5-0.6 | 420 | -0.0245 ±0.0098 | -0.0110 ±0.0046 | -2.5 | 0.518 | 0.567 | |
| kalshi favorite 0.6-0.7 | 420 | -0.0036 ±0.0094 | -0.0013 ±0.0043 | -0.4 | 0.614 | 0.617 | |
| kalshi favorite 0.7-0.8 | 321 | -0.0037 ±0.0107 | -0.0015 ±0.0043 | -0.3 | 0.743 | 0.745 | |
| kalshi favorite 0.8-0.9 | 200 | -0.0019 ±0.0178 | -0.0015 ±0.0064 | -0.1 | 0.835 | 0.835 | |
| kalshi favorite 0.9-1.0 | 85 | -0.0193 ±0.0312 | -0.0061 ±0.0079 | -0.6 | 0.953 | 0.941 | |
| surface: Hard | 164 | -0.0260 ±0.0208 | -0.0114 ±0.0087 | -1.2 | 0.616 | 0.628 | |
| surface: Clay | 696 | +0.0025 ±0.0073 | -0.0001 ±0.0029 | +0.3 | 0.670 | 0.690 | |
| surface: Grass | 586 | -0.0213 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.682 | |
| tier: atp250 | 565 | -0.0062 ±0.0096 | -0.0035 ±0.0040 | -0.7 | 0.642 | 0.665 | |
| tier: atp500 | 187 | -0.0151 ±0.0103 | -0.0072 ±0.0046 | -1.5 | 0.610 | 0.623 | |
| tier: grand_slam | 476 | -0.0187 ±0.0107 | -0.0074 ±0.0042 | -1.8 | 0.711 | 0.720 | |
| tier: masters | 218 | +0.0011 ±0.0108 | +0.0016 ±0.0049 | +0.1 | 0.672 | 0.679 | |
| round early (R128-R64) | 566 | -0.0179 ±0.0094 | -0.0065 ±0.0038 | -1.9 | 0.706 | 0.711 | |
| round late (QF-F) | 196 | -0.0108 ±0.0115 | -0.0060 ±0.0050 | -0.9 | 0.622 | 0.638 | |
| round mid (R32-R16) | 662 | -0.0040 ±0.0084 | -0.0024 ±0.0035 | -0.5 | 0.649 | 0.670 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 440 | -0.0249 ±0.0103 | -0.0106 ±0.0044 | -2.4 | 0.641 | 0.662 | |
| month 2026-07 | 438 | -0.0076 ±0.0105 | -0.0018 ±0.0044 | -0.7 | 0.683 | 0.696 | |
| month 2026-08 | 69 | -0.0318 ±0.0233 | -0.0134 ±0.0109 | -1.4 | 0.623 | 0.623 | |
| agree (<0.05) | 681 | +0.0014 ±0.0027 | +0.0001 ±0.0009 | +0.5 | 0.698 | 0.698 | |
| mild disagree (0.05-0.10) | 446 | -0.0031 ±0.0083 | -0.0019 ±0.0032 | -0.4 | 0.647 | 0.666 | |
| big disagree (>=0.1) | 319 | -0.0456 ±0.0214 | -0.0178 ±0.0091 | -2.1 | 0.622 | 0.660 | |
| tour: atp | 705 | +0.0083 ±0.0079 | +0.0032 ±0.0032 | +1.1 | 0.668 | 0.677 | |
| tour: wta | 741 | -0.0282 ±0.0077 | -0.0118 ±0.0032 | -3.7 | 0.663 | 0.683 | |

When they disagree by >= 0.1: model closer to the outcome in **122/319** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 13 | 0.066 | 0.077 |
| 0.1-0.2 | 80 | 0.158 | 0.138 |
| 0.2-0.3 | 131 | 0.251 | 0.221 |
| 0.3-0.4 | 206 | 0.352 | 0.335 |
| 0.4-0.5 | 248 | 0.449 | 0.476 |
| 0.5-0.6 | 240 | 0.550 | 0.567 |
| 0.6-0.7 | 224 | 0.645 | 0.616 |
| 0.7-0.8 | 177 | 0.747 | 0.734 |
| 0.8-0.9 | 100 | 0.844 | 0.840 |
| 0.9-1.0 | 27 | 0.928 | 0.889 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 33 | 0.062 | 0.061 |
| 0.1-0.2 | 85 | 0.152 | 0.118 |
| 0.2-0.3 | 143 | 0.253 | 0.259 |
| 0.3-0.4 | 193 | 0.353 | 0.368 |
| 0.4-0.5 | 213 | 0.442 | 0.432 |
| 0.5-0.6 | 209 | 0.558 | 0.560 |
| 0.6-0.7 | 225 | 0.650 | 0.609 |
| 0.7-0.8 | 178 | 0.746 | 0.747 |
| 0.8-0.9 | 115 | 0.844 | 0.800 |
| 0.9-1.0 | 52 | 0.938 | 0.942 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| both inside top-50 | 291 | +0.0108 ±0.0102 | +0.0049 ±0.0045 | +1.1 | 0.675 | 0.662 | |
| tour: atp | 705 | +0.0083 ±0.0079 | +0.0032 ±0.0032 | +1.1 | 0.668 | 0.677 | |
| best rank 1-10 | 256 | +0.0098 ±0.0112 | +0.0030 ±0.0035 | +0.9 | 0.754 | 0.750 | |
| agree (<0.05) | 681 | +0.0014 ±0.0027 | +0.0001 ±0.0009 | +0.5 | 0.698 | 0.698 | |
| surface: Clay | 696 | +0.0025 ±0.0073 | -0.0001 ±0.0029 | +0.3 | 0.670 | 0.690 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| tier: masters | 218 | +0.0011 ±0.0108 | +0.0016 ±0.0049 | +0.1 | 0.672 | 0.679 | |
| kalshi favorite 0.8-0.9 | 200 | -0.0019 ±0.0178 | -0.0015 ±0.0064 | -0.1 | 0.835 | 0.835 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| big disagree (>=0.1) | 319 | -0.0456 ±0.0214 | -0.0178 ±0.0091 | -2.1 | 0.622 | 0.660 | |
| best rank 100+ | 83 | -0.0795 ±0.0352 | -0.0354 ±0.0149 | -2.3 | 0.578 | 0.669 | |
| surface: Grass | 586 | -0.0213 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.682 | |
| month 2026-06 | 440 | -0.0249 ±0.0103 | -0.0106 ±0.0044 | -2.4 | 0.641 | 0.662 | |
| someone outside top-50 | 1155 | -0.0157 ±0.0064 | -0.0068 ±0.0026 | -2.4 | 0.663 | 0.684 | |
| kalshi favorite 0.5-0.6 | 420 | -0.0245 ±0.0098 | -0.0110 ±0.0046 | -2.5 | 0.518 | 0.567 | |
| pred_source: live | 580 | -0.0230 ±0.0092 | -0.0085 ±0.0039 | -2.5 | 0.671 | 0.689 | |
| tour: wta | 741 | -0.0282 ±0.0077 | -0.0118 ±0.0032 | -3.7 | 0.663 | 0.683 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1446, mean |Δ|=0.0024, p95=0.0089, >0.05 in 6 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0085 (n=440, >0.05: 0) | 2026-07 p95=0.0079 (n=438, >0.05: 1) | 2026-08 p95=0.0826 (n=69, >0.05: 4)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1446, d_ll -0.0104 ±0.0055 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 413 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'WTA Memphis': 9, 'WTA Washington': 8, 'ATP Montreal': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Los Cabos': 1, 'ATP Mallorca': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Alexandra Eala, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Botic Van de Zandschulp, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Carolyn Ansari, Casper Ruud, Caty McNally, Celine Naef, Chloe Paquet, Claire Liu, Clervie Ngounoue, Dalma Galfi
