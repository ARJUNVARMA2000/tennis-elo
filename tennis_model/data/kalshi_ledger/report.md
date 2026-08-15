# Model vs Kalshi — match-by-match scorecard

_Generated 2026-08-15T06:39:37Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1451 | 1377 | 23 | 5 | 46 | 0 | 9 | 15 | 60 | 2026-05-03..2026-08-15 |
| wta | 1465 | 863 | 35 | 529 | 38 | 0 | 5 | 15 | 39 | 2026-05-02..2026-08-15 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1620 | 0.6072 | 0.5968 | -0.0103 ±0.0051 | -0.0046 ±0.0021 | 0.664 | 0.677 |
| atp | 806 | 0.6157 | 0.6202 | +0.0045 ±0.0071 | +0.0013 ±0.0029 | 0.660 | 0.672 |
| wta | 814 | 0.5987 | 0.5737 | -0.0250 ±0.0072 | -0.0104 ±0.0030 | 0.667 | 0.681 |
| pooled/live | 721 | 0.6100 | 0.5883 | -0.0217 ±0.0077 | -0.0083 ±0.0033 | 0.667 | 0.682 |
| pooled/backtest | 899 | 0.6049 | 0.6037 | -0.0012 ±0.0067 | -0.0015 ±0.0027 | 0.661 | 0.672 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live | 721 | -0.0217 ±0.0077 | -0.0083 ±0.0033 | -2.8 | 0.667 | 0.682 | |
| pred_source: backtest | 899 | -0.0012 ±0.0067 | -0.0015 ±0.0027 | -0.2 | 0.661 | 0.672 | |
| top-20 involved | 528 | -0.0013 ±0.0076 | -0.0010 ±0.0027 | -0.2 | 0.743 | 0.739 | |
| no top-20 player | 1092 | -0.0146 ±0.0066 | -0.0063 ±0.0028 | -2.2 | 0.625 | 0.647 | |
| both inside top-50 | 341 | +0.0071 ±0.0091 | +0.0032 ±0.0040 | +0.8 | 0.673 | 0.669 | |
| someone outside top-50 | 1279 | -0.0150 ±0.0060 | -0.0066 ±0.0025 | -2.5 | 0.661 | 0.679 | |
| best rank 1-10 | 290 | +0.0106 ±0.0103 | +0.0032 ±0.0032 | +1.0 | 0.748 | 0.743 | |
| best rank 11-20 | 238 | -0.0159 ±0.0112 | -0.0060 ±0.0046 | -1.4 | 0.737 | 0.733 | |
| best rank 21-50 | 551 | -0.0109 ±0.0077 | -0.0039 ±0.0033 | -1.4 | 0.648 | 0.668 | |
| best rank 51-100 | 458 | -0.0074 ±0.0110 | -0.0039 ±0.0047 | -0.7 | 0.606 | 0.618 | |
| best rank 100+ | 83 | -0.0795 ±0.0352 | -0.0354 ±0.0149 | -2.3 | 0.578 | 0.669 | |
| kalshi favorite 0.5-0.6 | 478 | -0.0245 ±0.0090 | -0.0111 ±0.0042 | -2.7 | 0.526 | 0.568 | |
| kalshi favorite 0.6-0.7 | 479 | -0.0034 ±0.0087 | -0.0012 ±0.0040 | -0.4 | 0.608 | 0.612 | |
| kalshi favorite 0.7-0.8 | 360 | -0.0049 ±0.0097 | -0.0020 ±0.0039 | -0.5 | 0.749 | 0.750 | |
| kalshi favorite 0.8-0.9 | 215 | +0.0005 ±0.0168 | -0.0010 ±0.0060 | +0.0 | 0.833 | 0.833 | |
| kalshi favorite 0.9-1.0 | 88 | -0.0198 ±0.0302 | -0.0061 ±0.0076 | -0.7 | 0.955 | 0.943 | |
| surface: Hard | 338 | -0.0177 ±0.0116 | -0.0082 ±0.0049 | -1.5 | 0.633 | 0.641 | |
| surface: Clay | 696 | +0.0025 ±0.0073 | -0.0001 ±0.0029 | +0.3 | 0.670 | 0.690 | |
| surface: Grass | 586 | -0.0213 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.682 | |
| tier: atp250 | 665 | -0.0089 ±0.0084 | -0.0048 ±0.0035 | -1.1 | 0.636 | 0.662 | |
| tier: atp500 | 187 | -0.0151 ±0.0103 | -0.0072 ±0.0046 | -1.5 | 0.610 | 0.623 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 476 | -0.0187 ±0.0107 | -0.0074 ±0.0042 | -1.8 | 0.711 | 0.720 | |
| tier: masters | 291 | +0.0028 ±0.0093 | +0.0022 ±0.0042 | +0.3 | 0.682 | 0.675 | |
| round early (R128-R64) | 655 | -0.0168 ±0.0084 | -0.0062 ±0.0034 | -2.0 | 0.695 | 0.695 | |
| round late (QF-F) | 221 | -0.0079 ±0.0106 | -0.0044 ±0.0046 | -0.7 | 0.633 | 0.649 | |
| round mid (R32-R16) | 722 | -0.0053 ±0.0078 | -0.0031 ±0.0032 | -0.7 | 0.649 | 0.672 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 440 | -0.0249 ±0.0103 | -0.0106 ±0.0044 | -2.4 | 0.641 | 0.662 | |
| month 2026-07 | 438 | -0.0076 ±0.0105 | -0.0018 ±0.0044 | -0.7 | 0.683 | 0.696 | |
| month 2026-08 | 243 | -0.0161 ±0.0103 | -0.0075 ±0.0047 | -1.6 | 0.642 | 0.644 | |
| agree (<0.05) | 781 | +0.0008 ±0.0025 | -0.0002 ±0.0009 | +0.3 | 0.693 | 0.696 | |
| mild disagree (0.05-0.10) | 496 | -0.0033 ±0.0078 | -0.0021 ±0.0030 | -0.4 | 0.650 | 0.661 | |
| big disagree (>=0.1) | 343 | -0.0457 ±0.0203 | -0.0180 ±0.0087 | -2.3 | 0.617 | 0.656 | |
| tour: atp | 806 | +0.0045 ±0.0071 | +0.0013 ±0.0029 | +0.6 | 0.660 | 0.672 | |
| tour: wta | 814 | -0.0250 ±0.0072 | -0.0104 ±0.0030 | -3.5 | 0.667 | 0.681 | |

When they disagree by >= 0.1: model closer to the outcome in **133/343** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 13 | 0.066 | 0.077 |
| 0.1-0.2 | 86 | 0.158 | 0.151 |
| 0.2-0.3 | 149 | 0.251 | 0.228 |
| 0.3-0.4 | 235 | 0.351 | 0.349 |
| 0.4-0.5 | 281 | 0.450 | 0.463 |
| 0.5-0.6 | 259 | 0.549 | 0.571 |
| 0.6-0.7 | 251 | 0.645 | 0.606 |
| 0.7-0.8 | 201 | 0.746 | 0.736 |
| 0.8-0.9 | 114 | 0.844 | 0.833 |
| 0.9-1.0 | 31 | 0.926 | 0.903 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 33 | 0.062 | 0.061 |
| 0.1-0.2 | 88 | 0.152 | 0.114 |
| 0.2-0.3 | 164 | 0.255 | 0.262 |
| 0.3-0.4 | 220 | 0.353 | 0.382 |
| 0.4-0.5 | 243 | 0.443 | 0.420 |
| 0.5-0.6 | 238 | 0.558 | 0.555 |
| 0.6-0.7 | 256 | 0.649 | 0.609 |
| 0.7-0.8 | 196 | 0.745 | 0.760 |
| 0.8-0.9 | 127 | 0.846 | 0.795 |
| 0.9-1.0 | 55 | 0.937 | 0.945 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 290 | +0.0106 ±0.0103 | +0.0032 ±0.0032 | +1.0 | 0.748 | 0.743 | |
| both inside top-50 | 341 | +0.0071 ±0.0091 | +0.0032 ±0.0040 | +0.8 | 0.673 | 0.669 | |
| tour: atp | 806 | +0.0045 ±0.0071 | +0.0013 ±0.0029 | +0.6 | 0.660 | 0.672 | |
| surface: Clay | 696 | +0.0025 ±0.0073 | -0.0001 ±0.0029 | +0.3 | 0.670 | 0.690 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| agree (<0.05) | 781 | +0.0008 ±0.0025 | -0.0002 ±0.0009 | +0.3 | 0.693 | 0.696 | |
| tier: masters | 291 | +0.0028 ±0.0093 | +0.0022 ±0.0042 | +0.3 | 0.682 | 0.675 | |
| kalshi favorite 0.8-0.9 | 215 | +0.0005 ±0.0168 | -0.0010 ±0.0060 | +0.0 | 0.833 | 0.833 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| big disagree (>=0.1) | 343 | -0.0457 ±0.0203 | -0.0180 ±0.0087 | -2.3 | 0.617 | 0.656 | |
| best rank 100+ | 83 | -0.0795 ±0.0352 | -0.0354 ±0.0149 | -2.3 | 0.578 | 0.669 | |
| surface: Grass | 586 | -0.0213 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.682 | |
| month 2026-06 | 440 | -0.0249 ±0.0103 | -0.0106 ±0.0044 | -2.4 | 0.641 | 0.662 | |
| someone outside top-50 | 1279 | -0.0150 ±0.0060 | -0.0066 ±0.0025 | -2.5 | 0.661 | 0.679 | |
| kalshi favorite 0.5-0.6 | 478 | -0.0245 ±0.0090 | -0.0111 ±0.0042 | -2.7 | 0.526 | 0.568 | |
| pred_source: live | 721 | -0.0217 ±0.0077 | -0.0083 ±0.0033 | -2.8 | 0.667 | 0.682 | |
| tour: wta | 814 | -0.0250 ±0.0072 | -0.0104 ±0.0030 | -3.5 | 0.667 | 0.681 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1620, mean |Δ|=0.0025, p95=0.0093, >0.05 in 7 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0085 (n=440, >0.05: 0) | 2026-07 p95=0.0079 (n=438, >0.05: 1) | 2026-08 p95=0.0149 (n=243, >0.05: 5)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1620, d_ll -0.0103 ±0.0051 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 438 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Mallorca': 1, 'ATP Los Cabos': 1, 'WTA Toronto': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Alexandra Eala, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Carolyn Ansari, Casper Ruud, Caty McNally, Celine Naef, Chloe Paquet, Claire Liu, Clervie Ngounoue, Dalma Galfi, Daphnee Mpetshi Perricard
