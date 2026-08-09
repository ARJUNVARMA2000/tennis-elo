# Model vs Kalshi — match-by-match scorecard

_Generated 2026-08-09T06:21:28Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1353 | 1300 | 5 | 5 | 43 | 0 | 9 | 15 | 40 | 2026-05-03..2026-08-09 |
| wta | 1367 | 822 | 4 | 505 | 36 | 0 | 4 | 15 | 18 | 2026-05-02..2026-08-09 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1543 | 0.6054 | 0.5951 | -0.0104 ±0.0052 | -0.0046 ±0.0022 | 0.664 | 0.680 |
| atp | 767 | 0.6122 | 0.6190 | +0.0068 ±0.0074 | +0.0023 ±0.0030 | 0.664 | 0.675 |
| wta | 776 | 0.5987 | 0.5714 | -0.0273 ±0.0074 | -0.0114 ±0.0031 | 0.665 | 0.684 |
| pooled/live | 647 | 0.6057 | 0.5836 | -0.0221 ±0.0083 | -0.0083 ±0.0035 | 0.671 | 0.689 |
| pooled/backtest | 896 | 0.6052 | 0.6033 | -0.0019 ±0.0067 | -0.0019 ±0.0027 | 0.660 | 0.674 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live | 647 | -0.0221 ±0.0083 | -0.0083 ±0.0035 | -2.6 | 0.671 | 0.689 | |
| pred_source: backtest | 896 | -0.0019 ±0.0067 | -0.0019 ±0.0027 | -0.3 | 0.660 | 0.674 | |
| top-20 involved | 510 | -0.0019 ±0.0077 | -0.0012 ±0.0028 | -0.3 | 0.740 | 0.734 | |
| no top-20 player | 1033 | -0.0145 ±0.0068 | -0.0062 ±0.0029 | -2.1 | 0.627 | 0.653 | |
| both inside top-50 | 324 | +0.0070 ±0.0094 | +0.0031 ±0.0041 | +0.7 | 0.668 | 0.662 | |
| someone outside top-50 | 1219 | -0.0150 ±0.0061 | -0.0066 ±0.0025 | -2.4 | 0.663 | 0.685 | |
| best rank 1-10 | 280 | +0.0100 ±0.0105 | +0.0029 ±0.0033 | +1.0 | 0.743 | 0.739 | |
| best rank 11-20 | 230 | -0.0165 ±0.0114 | -0.0062 ±0.0047 | -1.5 | 0.737 | 0.728 | |
| best rank 21-50 | 524 | -0.0118 ±0.0079 | -0.0042 ±0.0034 | -1.5 | 0.647 | 0.668 | |
| best rank 51-100 | 426 | -0.0052 ±0.0115 | -0.0030 ±0.0049 | -0.4 | 0.612 | 0.631 | |
| best rank 100+ | 83 | -0.0795 ±0.0352 | -0.0354 ±0.0149 | -2.3 | 0.578 | 0.669 | |
| kalshi favorite 0.5-0.6 | 444 | -0.0243 ±0.0094 | -0.0110 ±0.0043 | -2.6 | 0.521 | 0.572 | |
| kalshi favorite 0.6-0.7 | 452 | -0.0047 ±0.0089 | -0.0018 ±0.0041 | -0.5 | 0.608 | 0.613 | |
| kalshi favorite 0.7-0.8 | 346 | -0.0047 ±0.0100 | -0.0019 ±0.0041 | -0.5 | 0.744 | 0.746 | |
| kalshi favorite 0.8-0.9 | 213 | +0.0014 ±0.0169 | -0.0007 ±0.0061 | +0.1 | 0.831 | 0.831 | |
| kalshi favorite 0.9-1.0 | 88 | -0.0198 ±0.0302 | -0.0061 ±0.0076 | -0.7 | 0.955 | 0.943 | |
| surface: Hard | 261 | -0.0201 ±0.0138 | -0.0093 ±0.0057 | -1.5 | 0.628 | 0.648 | |
| surface: Clay | 696 | +0.0025 ±0.0073 | -0.0001 ±0.0029 | +0.3 | 0.670 | 0.690 | |
| surface: Grass | 586 | -0.0213 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.682 | |
| tier: atp250 | 627 | -0.0067 ±0.0088 | -0.0039 ±0.0037 | -0.8 | 0.640 | 0.665 | |
| tier: atp500 | 187 | -0.0151 ±0.0103 | -0.0072 ±0.0046 | -1.5 | 0.610 | 0.623 | |
| tier: grand_slam | 476 | -0.0187 ±0.0107 | -0.0074 ±0.0042 | -1.8 | 0.711 | 0.720 | |
| tier: masters | 253 | -0.0003 ±0.0096 | +0.0010 ±0.0043 | -0.0 | 0.678 | 0.684 | |
| round early (R128-R64) | 597 | -0.0168 ±0.0089 | -0.0061 ±0.0036 | -1.9 | 0.704 | 0.709 | |
| round late (QF-F) | 202 | -0.0099 ±0.0112 | -0.0054 ±0.0049 | -0.9 | 0.619 | 0.634 | |
| round mid (R32-R16) | 722 | -0.0053 ±0.0078 | -0.0031 ±0.0032 | -0.7 | 0.649 | 0.672 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 440 | -0.0249 ±0.0103 | -0.0106 ±0.0044 | -2.4 | 0.641 | 0.662 | |
| month 2026-07 | 438 | -0.0076 ±0.0105 | -0.0018 ±0.0044 | -0.7 | 0.683 | 0.696 | |
| month 2026-08 | 166 | -0.0192 ±0.0120 | -0.0090 ±0.0053 | -1.6 | 0.639 | 0.657 | |
| agree (<0.05) | 747 | +0.0011 ±0.0026 | -0.0001 ±0.0009 | +0.4 | 0.693 | 0.695 | |
| mild disagree (0.05-0.10) | 470 | -0.0033 ±0.0081 | -0.0021 ±0.0031 | -0.4 | 0.648 | 0.666 | |
| big disagree (>=0.1) | 326 | -0.0468 ±0.0210 | -0.0184 ±0.0090 | -2.2 | 0.621 | 0.664 | |
| tour: atp | 767 | +0.0068 ±0.0074 | +0.0023 ±0.0030 | +0.9 | 0.664 | 0.675 | |
| tour: wta | 776 | -0.0273 ±0.0074 | -0.0114 ±0.0031 | -3.7 | 0.665 | 0.684 | |

When they disagree by >= 0.1: model closer to the outcome in **125/326** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 13 | 0.066 | 0.077 |
| 0.1-0.2 | 85 | 0.158 | 0.153 |
| 0.2-0.3 | 141 | 0.251 | 0.241 |
| 0.3-0.4 | 219 | 0.352 | 0.338 |
| 0.4-0.5 | 265 | 0.450 | 0.472 |
| 0.5-0.6 | 247 | 0.550 | 0.563 |
| 0.6-0.7 | 239 | 0.645 | 0.619 |
| 0.7-0.8 | 190 | 0.746 | 0.737 |
| 0.8-0.9 | 113 | 0.844 | 0.832 |
| 0.9-1.0 | 31 | 0.926 | 0.903 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 33 | 0.062 | 0.061 |
| 0.1-0.2 | 87 | 0.151 | 0.115 |
| 0.2-0.3 | 156 | 0.254 | 0.269 |
| 0.3-0.4 | 209 | 0.353 | 0.383 |
| 0.4-0.5 | 224 | 0.443 | 0.420 |
| 0.5-0.6 | 222 | 0.558 | 0.559 |
| 0.6-0.7 | 241 | 0.649 | 0.614 |
| 0.7-0.8 | 190 | 0.746 | 0.758 |
| 0.8-0.9 | 126 | 0.847 | 0.794 |
| 0.9-1.0 | 55 | 0.937 | 0.945 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 280 | +0.0100 ±0.0105 | +0.0029 ±0.0033 | +1.0 | 0.743 | 0.739 | |
| tour: atp | 767 | +0.0068 ±0.0074 | +0.0023 ±0.0030 | +0.9 | 0.664 | 0.675 | |
| both inside top-50 | 324 | +0.0070 ±0.0094 | +0.0031 ±0.0041 | +0.7 | 0.668 | 0.662 | |
| agree (<0.05) | 747 | +0.0011 ±0.0026 | -0.0001 ±0.0009 | +0.4 | 0.693 | 0.695 | |
| surface: Clay | 696 | +0.0025 ±0.0073 | -0.0001 ±0.0029 | +0.3 | 0.670 | 0.690 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| kalshi favorite 0.8-0.9 | 213 | +0.0014 ±0.0169 | -0.0007 ±0.0061 | +0.1 | 0.831 | 0.831 | |
| tier: masters | 253 | -0.0003 ±0.0096 | +0.0010 ±0.0043 | -0.0 | 0.678 | 0.684 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| big disagree (>=0.1) | 326 | -0.0468 ±0.0210 | -0.0184 ±0.0090 | -2.2 | 0.621 | 0.664 | |
| best rank 100+ | 83 | -0.0795 ±0.0352 | -0.0354 ±0.0149 | -2.3 | 0.578 | 0.669 | |
| surface: Grass | 586 | -0.0213 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.682 | |
| month 2026-06 | 440 | -0.0249 ±0.0103 | -0.0106 ±0.0044 | -2.4 | 0.641 | 0.662 | |
| someone outside top-50 | 1219 | -0.0150 ±0.0061 | -0.0066 ±0.0025 | -2.4 | 0.663 | 0.685 | |
| kalshi favorite 0.5-0.6 | 444 | -0.0243 ±0.0094 | -0.0110 ±0.0043 | -2.6 | 0.521 | 0.572 | |
| pred_source: live | 647 | -0.0221 ±0.0083 | -0.0083 ±0.0035 | -2.6 | 0.671 | 0.689 | |
| tour: wta | 776 | -0.0273 ±0.0074 | -0.0114 ±0.0031 | -3.7 | 0.665 | 0.684 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1543, mean |Δ|=0.0025, p95=0.0091, >0.05 in 7 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0085 (n=440, >0.05: 0) | 2026-07 p95=0.0079 (n=438, >0.05: 1) | 2026-08 p95=0.0151 (n=166, >0.05: 5)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1543, d_ll -0.0104 ±0.0052 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 413 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Los Cabos': 1, 'ATP Montreal': 1, 'ATP Mallorca': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Alexandra Eala, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Andrey Rublev, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Carolyn Ansari, Casper Ruud, Caty McNally, Celine Naef, Chloe Paquet, Claire Liu, Clervie Ngounoue, Dalma Galfi
