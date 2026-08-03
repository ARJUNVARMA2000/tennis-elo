# Model vs Kalshi — match-by-match scorecard

_Generated 2026-08-03T08:04:05Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1298 | 1216 | 33 | 7 | 42 | 0 | 8 | 15 | 45 | 2026-05-03..2026-08-03 |
| wta | 1311 | 744 | 43 | 488 | 36 | 0 | 3 | 15 | 20 | 2026-05-02..2026-08-03 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1392 | 0.6035 | 0.5928 | -0.0107 ±0.0057 | -0.0047 ±0.0023 | 0.667 | 0.682 |
| atp | 687 | 0.6057 | 0.6138 | +0.0081 ±0.0080 | +0.0030 ±0.0033 | 0.670 | 0.680 |
| wta | 705 | 0.6014 | 0.5723 | -0.0291 ±0.0079 | -0.0122 ±0.0033 | 0.664 | 0.685 |
| pooled/live | 529 | 0.6058 | 0.5812 | -0.0245 ±0.0097 | -0.0092 ±0.0041 | 0.673 | 0.695 |
| pooled/backtest | 863 | 0.6021 | 0.5999 | -0.0023 ±0.0069 | -0.0020 ±0.0028 | 0.663 | 0.675 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live | 529 | -0.0245 ±0.0097 | -0.0092 ±0.0041 | -2.5 | 0.673 | 0.695 | |
| pred_source: backtest | 863 | -0.0023 ±0.0069 | -0.0020 ±0.0028 | -0.3 | 0.663 | 0.675 | |
| top-20 involved | 451 | -0.0014 ±0.0085 | -0.0009 ±0.0030 | -0.2 | 0.742 | 0.737 | |
| no top-20 player | 941 | -0.0152 ±0.0073 | -0.0065 ±0.0031 | -2.1 | 0.631 | 0.656 | |
| both inside top-50 | 284 | +0.0130 ±0.0103 | +0.0058 ±0.0045 | +1.3 | 0.674 | 0.660 | |
| someone outside top-50 | 1108 | -0.0168 ±0.0066 | -0.0074 ±0.0027 | -2.6 | 0.665 | 0.688 | |
| best rank 1-10 | 251 | +0.0120 ±0.0113 | +0.0039 ±0.0035 | +1.1 | 0.753 | 0.749 | |
| best rank 11-20 | 200 | -0.0182 ±0.0128 | -0.0070 ±0.0052 | -1.4 | 0.728 | 0.723 | |
| best rank 21-50 | 475 | -0.0089 ±0.0085 | -0.0027 ±0.0037 | -1.1 | 0.653 | 0.667 | |
| best rank 51-100 | 386 | -0.0082 ±0.0123 | -0.0046 ±0.0052 | -0.7 | 0.613 | 0.637 | |
| best rank 100+ | 80 | -0.0864 ±0.0362 | -0.0386 ±0.0154 | -2.4 | 0.588 | 0.681 | |
| kalshi favorite 0.5-0.6 | 397 | -0.0249 ±0.0101 | -0.0112 ±0.0047 | -2.5 | 0.515 | 0.567 | |
| kalshi favorite 0.6-0.7 | 404 | -0.0054 ±0.0096 | -0.0022 ±0.0044 | -0.6 | 0.619 | 0.624 | |
| kalshi favorite 0.7-0.8 | 313 | -0.0035 ±0.0108 | -0.0015 ±0.0044 | -0.3 | 0.743 | 0.744 | |
| kalshi favorite 0.8-0.9 | 195 | -0.0008 ±0.0183 | -0.0012 ±0.0066 | -0.0 | 0.831 | 0.831 | |
| kalshi favorite 0.9-1.0 | 83 | -0.0198 ±0.0320 | -0.0063 ±0.0081 | -0.6 | 0.952 | 0.940 | |
| surface: Hard | 112 | -0.0366 ±0.0278 | -0.0169 ±0.0113 | -1.3 | 0.616 | 0.643 | |
| surface: Clay | 695 | +0.0022 ±0.0073 | -0.0003 ±0.0029 | +0.3 | 0.669 | 0.690 | |
| surface: Grass | 585 | -0.0212 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.681 | |
| tier: atp250 | 548 | -0.0073 ±0.0098 | -0.0040 ±0.0041 | -0.7 | 0.642 | 0.668 | |
| tier: atp500 | 184 | -0.0139 ±0.0102 | -0.0067 ±0.0046 | -1.4 | 0.614 | 0.628 | |
| tier: grand_slam | 476 | -0.0187 ±0.0107 | -0.0074 ±0.0042 | -1.8 | 0.711 | 0.720 | |
| tier: masters | 184 | +0.0026 ±0.0114 | +0.0023 ±0.0051 | +0.2 | 0.677 | 0.685 | |
| round early (R128-R64) | 517 | -0.0198 ±0.0099 | -0.0074 ±0.0040 | -2.0 | 0.713 | 0.721 | |
| round late (QF-F) | 194 | -0.0085 ±0.0115 | -0.0050 ±0.0050 | -0.7 | 0.624 | 0.639 | |
| round mid (R32-R16) | 659 | -0.0045 ±0.0084 | -0.0026 ±0.0035 | -0.5 | 0.649 | 0.670 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 439 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.640 | 0.662 | |
| month 2026-07 | 436 | -0.0086 ±0.0105 | -0.0023 ±0.0044 | -0.8 | 0.683 | 0.697 | |
| month 2026-08 | 18 | -0.1023 ±0.0430 | -0.0471 ±0.0203 | -2.4 | 0.611 | 0.667 | ⚠ small n |
| agree (<0.05) | 659 | +0.0011 ±0.0028 | -0.0001 ±0.0009 | +0.4 | 0.695 | 0.697 | |
| mild disagree (0.05-0.10) | 427 | -0.0037 ±0.0085 | -0.0024 ±0.0033 | -0.4 | 0.648 | 0.672 | |
| big disagree (>=0.1) | 306 | -0.0460 ±0.0220 | -0.0178 ±0.0094 | -2.1 | 0.632 | 0.665 | |
| tour: atp | 687 | +0.0081 ±0.0080 | +0.0030 ±0.0033 | +1.0 | 0.670 | 0.680 | |
| tour: wta | 705 | -0.0291 ±0.0079 | -0.0122 ±0.0033 | -3.7 | 0.664 | 0.685 | |

When they disagree by >= 0.1: model closer to the outcome in **116/306** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 12 | 0.067 | 0.083 |
| 0.1-0.2 | 79 | 0.157 | 0.139 |
| 0.2-0.3 | 127 | 0.252 | 0.220 |
| 0.3-0.4 | 199 | 0.352 | 0.337 |
| 0.4-0.5 | 236 | 0.449 | 0.479 |
| 0.5-0.6 | 229 | 0.550 | 0.576 |
| 0.6-0.7 | 215 | 0.645 | 0.614 |
| 0.7-0.8 | 172 | 0.747 | 0.738 |
| 0.8-0.9 | 97 | 0.844 | 0.835 |
| 0.9-1.0 | 26 | 0.927 | 0.885 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 32 | 0.062 | 0.062 |
| 0.1-0.2 | 83 | 0.152 | 0.120 |
| 0.2-0.3 | 140 | 0.253 | 0.257 |
| 0.3-0.4 | 184 | 0.352 | 0.364 |
| 0.4-0.5 | 204 | 0.442 | 0.436 |
| 0.5-0.6 | 195 | 0.558 | 0.564 |
| 0.6-0.7 | 218 | 0.650 | 0.619 |
| 0.7-0.8 | 173 | 0.746 | 0.746 |
| 0.8-0.9 | 112 | 0.844 | 0.795 |
| 0.9-1.0 | 51 | 0.938 | 0.941 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| both inside top-50 | 284 | +0.0130 ±0.0103 | +0.0058 ±0.0045 | +1.3 | 0.674 | 0.660 | |
| best rank 1-10 | 251 | +0.0120 ±0.0113 | +0.0039 ±0.0035 | +1.1 | 0.753 | 0.749 | |
| tour: atp | 687 | +0.0081 ±0.0080 | +0.0030 ±0.0033 | +1.0 | 0.670 | 0.680 | |
| agree (<0.05) | 659 | +0.0011 ±0.0028 | -0.0001 ±0.0009 | +0.4 | 0.695 | 0.697 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 695 | +0.0022 ±0.0073 | -0.0003 ±0.0029 | +0.3 | 0.669 | 0.690 | |
| tier: masters | 184 | +0.0026 ±0.0114 | +0.0023 ±0.0051 | +0.2 | 0.677 | 0.685 | |
| kalshi favorite 0.8-0.9 | 195 | -0.0008 ±0.0183 | -0.0012 ±0.0066 | -0.0 | 0.831 | 0.831 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| month 2026-08 | 18 | -0.1023 ±0.0430 | -0.0471 ±0.0203 | -2.4 | 0.611 | 0.667 | ⚠ small n |
| best rank 100+ | 80 | -0.0864 ±0.0362 | -0.0386 ±0.0154 | -2.4 | 0.588 | 0.681 | |
| month 2026-06 | 439 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.640 | 0.662 | |
| surface: Grass | 585 | -0.0212 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.681 | |
| kalshi favorite 0.5-0.6 | 397 | -0.0249 ±0.0101 | -0.0112 ±0.0047 | -2.5 | 0.515 | 0.567 | |
| pred_source: live | 529 | -0.0245 ±0.0097 | -0.0092 ±0.0041 | -2.5 | 0.673 | 0.695 | |
| someone outside top-50 | 1108 | -0.0168 ±0.0066 | -0.0074 ±0.0027 | -2.6 | 0.665 | 0.688 | |
| tour: wta | 705 | -0.0291 ±0.0079 | -0.0122 ±0.0033 | -3.7 | 0.664 | 0.685 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1392, mean |Δ|=0.0024, p95=0.0088, >0.05 in 6 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0085 (n=439, >0.05: 0) | 2026-07 p95=0.0079 (n=436, >0.05: 1) | 2026-08 p95=0.2770 (n=18, >0.05: 4)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1392, d_ll -0.0107 ±0.0057 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 397 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'WTA Memphis': 9, 'WTA Washington': 7, 'WTA Iasi': 6, 'WTA Hamburg': 6, 'ATP Hamburg': 1, 'ATP Los Cabos': 1, 'ATP Washington': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Carolyn Ansari, Casper Ruud, Caty McNally, Celine Naef, Chloe Paquet, Claire Liu, Clervie Ngounoue, Dalma Galfi, Daphnee Mpetshi Perricard, Daria Kasatkina
