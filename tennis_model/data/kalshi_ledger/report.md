# Model vs Kalshi — match-by-match scorecard

_Generated 2026-08-04T07:12:13Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1309 | 1235 | 28 | 4 | 42 | 0 | 8 | 15 | 48 | 2026-05-03..2026-08-05 |
| wta | 1332 | 771 | 38 | 487 | 36 | 0 | 3 | 15 | 35 | 2026-05-02..2026-08-04 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1435 | 0.6056 | 0.5953 | -0.0103 ±0.0056 | -0.0044 ±0.0023 | 0.664 | 0.679 |
| atp | 705 | 0.6075 | 0.6158 | +0.0083 ±0.0079 | +0.0032 ±0.0032 | 0.668 | 0.677 |
| wta | 730 | 0.6037 | 0.5754 | -0.0283 ±0.0078 | -0.0118 ±0.0033 | 0.660 | 0.681 |
| pooled/live | 569 | 0.6103 | 0.5873 | -0.0230 ±0.0093 | -0.0085 ±0.0040 | 0.668 | 0.686 |
| pooled/backtest | 866 | 0.6025 | 0.6005 | -0.0019 ±0.0069 | -0.0018 ±0.0028 | 0.662 | 0.674 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live | 569 | -0.0230 ±0.0093 | -0.0085 ±0.0040 | -2.5 | 0.668 | 0.686 | |
| pred_source: backtest | 866 | -0.0019 ±0.0069 | -0.0018 ±0.0028 | -0.3 | 0.662 | 0.674 | |
| top-20 involved | 453 | -0.0024 ±0.0085 | -0.0014 ±0.0030 | -0.3 | 0.741 | 0.736 | |
| no top-20 player | 982 | -0.0139 ±0.0071 | -0.0059 ±0.0031 | -1.9 | 0.629 | 0.652 | |
| both inside top-50 | 289 | +0.0106 ±0.0103 | +0.0048 ±0.0045 | +1.0 | 0.673 | 0.659 | |
| someone outside top-50 | 1146 | -0.0156 ±0.0065 | -0.0068 ±0.0027 | -2.4 | 0.662 | 0.684 | |
| best rank 1-10 | 253 | +0.0100 ±0.0113 | +0.0031 ±0.0035 | +0.9 | 0.751 | 0.747 | |
| best rank 11-20 | 200 | -0.0182 ±0.0128 | -0.0070 ±0.0052 | -1.4 | 0.728 | 0.723 | |
| best rank 21-50 | 486 | -0.0093 ±0.0083 | -0.0029 ±0.0036 | -1.1 | 0.656 | 0.671 | |
| best rank 51-100 | 413 | -0.0062 ±0.0119 | -0.0034 ±0.0051 | -0.5 | 0.607 | 0.627 | |
| best rank 100+ | 83 | -0.0795 ±0.0352 | -0.0354 ±0.0149 | -2.3 | 0.578 | 0.669 | |
| kalshi favorite 0.5-0.6 | 416 | -0.0241 ±0.0099 | -0.0108 ±0.0046 | -2.4 | 0.518 | 0.567 | |
| kalshi favorite 0.6-0.7 | 419 | -0.0038 ±0.0094 | -0.0014 ±0.0043 | -0.4 | 0.613 | 0.616 | |
| kalshi favorite 0.7-0.8 | 320 | -0.0037 ±0.0107 | -0.0015 ±0.0043 | -0.3 | 0.742 | 0.744 | |
| kalshi favorite 0.8-0.9 | 197 | -0.0017 ±0.0181 | -0.0015 ±0.0065 | -0.1 | 0.832 | 0.832 | |
| kalshi favorite 0.9-1.0 | 83 | -0.0198 ±0.0320 | -0.0063 ±0.0081 | -0.6 | 0.952 | 0.940 | |
| surface: Hard | 153 | -0.0263 ±0.0221 | -0.0115 ±0.0092 | -1.2 | 0.601 | 0.614 | |
| surface: Clay | 696 | +0.0025 ±0.0073 | -0.0001 ±0.0029 | +0.3 | 0.670 | 0.690 | |
| surface: Grass | 586 | -0.0213 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.682 | |
| tier: atp250 | 565 | -0.0062 ±0.0096 | -0.0035 ±0.0040 | -0.7 | 0.642 | 0.665 | |
| tier: atp500 | 187 | -0.0151 ±0.0103 | -0.0072 ±0.0046 | -1.5 | 0.610 | 0.623 | |
| tier: grand_slam | 476 | -0.0187 ±0.0107 | -0.0074 ±0.0042 | -1.8 | 0.711 | 0.720 | |
| tier: masters | 207 | +0.0022 ±0.0112 | +0.0023 ±0.0050 | +0.2 | 0.664 | 0.671 | |
| round early (R128-R64) | 555 | -0.0178 ±0.0095 | -0.0064 ±0.0038 | -1.9 | 0.704 | 0.709 | |
| round late (QF-F) | 196 | -0.0108 ±0.0115 | -0.0060 ±0.0050 | -0.9 | 0.622 | 0.638 | |
| round mid (R32-R16) | 662 | -0.0040 ±0.0084 | -0.0024 ±0.0035 | -0.5 | 0.649 | 0.670 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 440 | -0.0249 ±0.0103 | -0.0106 ±0.0044 | -2.4 | 0.641 | 0.662 | |
| month 2026-07 | 438 | -0.0076 ±0.0105 | -0.0018 ±0.0044 | -0.7 | 0.683 | 0.696 | |
| month 2026-08 | 58 | -0.0339 ±0.0267 | -0.0141 ±0.0125 | -1.3 | 0.586 | 0.586 | |
| agree (<0.05) | 673 | +0.0016 ±0.0028 | +0.0001 ±0.0009 | +0.6 | 0.695 | 0.696 | |
| mild disagree (0.05-0.10) | 444 | -0.0037 ±0.0083 | -0.0022 ±0.0032 | -0.4 | 0.645 | 0.667 | |
| big disagree (>=0.1) | 318 | -0.0446 ±0.0214 | -0.0173 ±0.0092 | -2.1 | 0.624 | 0.659 | |
| tour: atp | 705 | +0.0083 ±0.0079 | +0.0032 ±0.0032 | +1.1 | 0.668 | 0.677 | |
| tour: wta | 730 | -0.0283 ±0.0078 | -0.0118 ±0.0033 | -3.6 | 0.660 | 0.681 | |

When they disagree by >= 0.1: model closer to the outcome in **122/318** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 12 | 0.067 | 0.083 |
| 0.1-0.2 | 80 | 0.158 | 0.138 |
| 0.2-0.3 | 130 | 0.251 | 0.223 |
| 0.3-0.4 | 206 | 0.352 | 0.335 |
| 0.4-0.5 | 247 | 0.449 | 0.478 |
| 0.5-0.6 | 240 | 0.550 | 0.567 |
| 0.6-0.7 | 220 | 0.646 | 0.618 |
| 0.7-0.8 | 177 | 0.747 | 0.734 |
| 0.8-0.9 | 97 | 0.844 | 0.835 |
| 0.9-1.0 | 26 | 0.927 | 0.885 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 32 | 0.062 | 0.062 |
| 0.1-0.2 | 85 | 0.152 | 0.118 |
| 0.2-0.3 | 142 | 0.253 | 0.261 |
| 0.3-0.4 | 193 | 0.353 | 0.368 |
| 0.4-0.5 | 212 | 0.442 | 0.434 |
| 0.5-0.6 | 206 | 0.558 | 0.563 |
| 0.6-0.7 | 224 | 0.650 | 0.607 |
| 0.7-0.8 | 178 | 0.746 | 0.747 |
| 0.8-0.9 | 112 | 0.844 | 0.795 |
| 0.9-1.0 | 51 | 0.938 | 0.941 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| tour: atp | 705 | +0.0083 ±0.0079 | +0.0032 ±0.0032 | +1.1 | 0.668 | 0.677 | |
| both inside top-50 | 289 | +0.0106 ±0.0103 | +0.0048 ±0.0045 | +1.0 | 0.673 | 0.659 | |
| best rank 1-10 | 253 | +0.0100 ±0.0113 | +0.0031 ±0.0035 | +0.9 | 0.751 | 0.747 | |
| agree (<0.05) | 673 | +0.0016 ±0.0028 | +0.0001 ±0.0009 | +0.6 | 0.695 | 0.696 | |
| surface: Clay | 696 | +0.0025 ±0.0073 | -0.0001 ±0.0029 | +0.3 | 0.670 | 0.690 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| tier: masters | 207 | +0.0022 ±0.0112 | +0.0023 ±0.0050 | +0.2 | 0.664 | 0.671 | |
| kalshi favorite 0.8-0.9 | 197 | -0.0017 ±0.0181 | -0.0015 ±0.0065 | -0.1 | 0.832 | 0.832 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| big disagree (>=0.1) | 318 | -0.0446 ±0.0214 | -0.0173 ±0.0092 | -2.1 | 0.624 | 0.659 | |
| best rank 100+ | 83 | -0.0795 ±0.0352 | -0.0354 ±0.0149 | -2.3 | 0.578 | 0.669 | |
| someone outside top-50 | 1146 | -0.0156 ±0.0065 | -0.0068 ±0.0027 | -2.4 | 0.662 | 0.684 | |
| surface: Grass | 586 | -0.0213 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.682 | |
| month 2026-06 | 440 | -0.0249 ±0.0103 | -0.0106 ±0.0044 | -2.4 | 0.641 | 0.662 | |
| kalshi favorite 0.5-0.6 | 416 | -0.0241 ±0.0099 | -0.0108 ±0.0046 | -2.4 | 0.518 | 0.567 | |
| pred_source: live | 569 | -0.0230 ±0.0093 | -0.0085 ±0.0040 | -2.5 | 0.668 | 0.686 | |
| tour: wta | 730 | -0.0283 ±0.0078 | -0.0118 ±0.0033 | -3.6 | 0.660 | 0.681 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1435, mean |Δ|=0.0024, p95=0.0089, >0.05 in 6 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0085 (n=440, >0.05: 0) | 2026-07 p95=0.0079 (n=438, >0.05: 1) | 2026-08 p95=0.1422 (n=58, >0.05: 4)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1435, d_ll -0.0103 ±0.0056 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 397 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'WTA Memphis': 9, 'WTA Washington': 7, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Mallorca': 1, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Carolyn Ansari, Casper Ruud, Caty McNally, Celine Naef, Chloe Paquet, Claire Liu, Clervie Ngounoue, Dalma Galfi, Daphnee Mpetshi Perricard, Daria Kasatkina
