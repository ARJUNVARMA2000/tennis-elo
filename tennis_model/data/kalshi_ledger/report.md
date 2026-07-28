# Model vs Kalshi — match-by-match scorecard

_Generated 2026-07-28T07:10:55Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1218 | 1150 | 20 | 5 | 43 | 0 | 8 | 14 | 162 | 2026-05-03..2026-07-29 |
| wta | 1229 | 696 | 40 | 460 | 33 | 0 | 2 | 15 | 17 | 2026-05-02..2026-07-28 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1313 | 0.6003 | 0.5896 | -0.0107 ±0.0058 | -0.0045 ±0.0024 | 0.671 | 0.685 |
| atp | 652 | 0.6051 | 0.6109 | +0.0058 ±0.0081 | +0.0024 ±0.0033 | 0.669 | 0.679 |
| wta | 661 | 0.5955 | 0.5685 | -0.0270 ±0.0081 | -0.0113 ±0.0034 | 0.673 | 0.690 |
| pooled/live | 463 | 0.6004 | 0.5714 | -0.0290 ±0.0102 | -0.0102 ±0.0043 | 0.685 | 0.703 |
| pooled/backtest | 850 | 0.6002 | 0.5994 | -0.0008 ±0.0069 | -0.0014 ±0.0028 | 0.664 | 0.675 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live | 463 | -0.0290 ±0.0102 | -0.0102 ±0.0043 | -2.8 | 0.685 | 0.703 | |
| pred_source: backtest | 850 | -0.0008 ±0.0069 | -0.0014 ±0.0028 | -0.1 | 0.664 | 0.675 | |
| top-20 involved | 420 | +0.0001 ±0.0085 | -0.0002 ±0.0030 | +0.0 | 0.742 | 0.735 | |
| no top-20 player | 893 | -0.0158 ±0.0075 | -0.0065 ±0.0032 | -2.1 | 0.638 | 0.661 | |
| both inside top-50 | 261 | +0.0150 ±0.0107 | +0.0069 ±0.0047 | +1.4 | 0.680 | 0.661 | |
| someone outside top-50 | 1052 | -0.0171 ±0.0067 | -0.0073 ±0.0027 | -2.6 | 0.669 | 0.691 | |
| best rank 1-10 | 237 | +0.0127 ±0.0119 | +0.0043 ±0.0036 | +1.1 | 0.747 | 0.743 | |
| best rank 11-20 | 183 | -0.0162 ±0.0120 | -0.0061 ±0.0050 | -1.4 | 0.735 | 0.724 | |
| best rank 21-50 | 454 | -0.0076 ±0.0087 | -0.0020 ±0.0038 | -0.9 | 0.656 | 0.670 | |
| best rank 51-100 | 362 | -0.0125 ±0.0124 | -0.0060 ±0.0053 | -1.0 | 0.620 | 0.646 | |
| best rank 100+ | 77 | -0.0794 ±0.0372 | -0.0351 ±0.0157 | -2.1 | 0.610 | 0.682 | |
| kalshi favorite 0.5-0.6 | 374 | -0.0237 ±0.0104 | -0.0105 ±0.0048 | -2.3 | 0.517 | 0.567 | |
| kalshi favorite 0.6-0.7 | 378 | -0.0011 ±0.0097 | -0.0005 ±0.0045 | -0.1 | 0.630 | 0.630 | |
| kalshi favorite 0.7-0.8 | 292 | -0.0050 ±0.0110 | -0.0019 ±0.0045 | -0.4 | 0.738 | 0.740 | |
| kalshi favorite 0.8-0.9 | 186 | -0.0090 ±0.0181 | -0.0038 ±0.0066 | -0.5 | 0.833 | 0.833 | |
| kalshi favorite 0.9-1.0 | 83 | -0.0198 ±0.0320 | -0.0063 ±0.0081 | -0.6 | 0.952 | 0.940 | |
| surface: Hard | 39 | -0.0881 ±0.0548 | -0.0343 ±0.0229 | -1.6 | 0.667 | 0.667 | ⚠ small n |
| surface: Clay | 689 | +0.0026 ±0.0073 | -0.0001 ±0.0029 | +0.4 | 0.669 | 0.689 | |
| surface: Grass | 585 | -0.0212 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.681 | |
| tier: atp250 | 477 | -0.0070 ±0.0102 | -0.0035 ±0.0043 | -0.7 | 0.652 | 0.675 | |
| tier: atp500 | 181 | -0.0148 ±0.0103 | -0.0071 ±0.0046 | -1.4 | 0.608 | 0.622 | |
| tier: grand_slam | 476 | -0.0187 ±0.0107 | -0.0074 ±0.0042 | -1.8 | 0.711 | 0.720 | |
| tier: masters | 179 | +0.0046 ±0.0116 | +0.0032 ±0.0051 | +0.4 | 0.679 | 0.682 | |
| round early (R128-R64) | 506 | -0.0197 ±0.0101 | -0.0073 ±0.0041 | -1.9 | 0.712 | 0.722 | |
| round late (QF-F) | 174 | +0.0007 ±0.0116 | -0.0007 ±0.0050 | +0.1 | 0.638 | 0.638 | |
| round mid (R32-R16) | 611 | -0.0067 ±0.0084 | -0.0033 ±0.0036 | -0.8 | 0.652 | 0.672 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 493 | +0.0035 ±0.0090 | -0.0001 ±0.0035 | +0.4 | 0.677 | 0.687 | |
| month 2026-06 | 439 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.640 | 0.662 | |
| month 2026-07 | 381 | -0.0129 ±0.0107 | -0.0034 ±0.0046 | -1.2 | 0.698 | 0.709 | |
| agree (<0.05) | 624 | +0.0022 ±0.0029 | +0.0003 ±0.0009 | +0.7 | 0.702 | 0.704 | |
| mild disagree (0.05-0.10) | 409 | -0.0061 ±0.0087 | -0.0030 ±0.0033 | -0.7 | 0.639 | 0.667 | |
| big disagree (>=0.1) | 280 | -0.0462 ±0.0228 | -0.0174 ±0.0098 | -2.0 | 0.648 | 0.666 | |
| tour: atp | 652 | +0.0058 ±0.0081 | +0.0024 ±0.0033 | +0.7 | 0.669 | 0.679 | |
| tour: wta | 661 | -0.0270 ±0.0081 | -0.0113 ±0.0034 | -3.3 | 0.673 | 0.690 | |

When they disagree by >= 0.1: model closer to the outcome in **104/280** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 12 | 0.067 | 0.083 |
| 0.1-0.2 | 71 | 0.156 | 0.127 |
| 0.2-0.3 | 114 | 0.250 | 0.211 |
| 0.3-0.4 | 185 | 0.352 | 0.314 |
| 0.4-0.5 | 225 | 0.450 | 0.476 |
| 0.5-0.6 | 219 | 0.550 | 0.571 |
| 0.6-0.7 | 202 | 0.645 | 0.624 |
| 0.7-0.8 | 167 | 0.747 | 0.731 |
| 0.8-0.9 | 94 | 0.844 | 0.840 |
| 0.9-1.0 | 24 | 0.927 | 0.875 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 32 | 0.062 | 0.062 |
| 0.1-0.2 | 78 | 0.153 | 0.115 |
| 0.2-0.3 | 124 | 0.254 | 0.258 |
| 0.3-0.4 | 171 | 0.353 | 0.345 |
| 0.4-0.5 | 196 | 0.442 | 0.434 |
| 0.5-0.6 | 180 | 0.558 | 0.561 |
| 0.6-0.7 | 205 | 0.650 | 0.615 |
| 0.7-0.8 | 168 | 0.746 | 0.738 |
| 0.8-0.9 | 108 | 0.844 | 0.796 |
| 0.9-1.0 | 51 | 0.938 | 0.941 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| both inside top-50 | 261 | +0.0150 ±0.0107 | +0.0069 ±0.0047 | +1.4 | 0.680 | 0.661 | |
| best rank 1-10 | 237 | +0.0127 ±0.0119 | +0.0043 ±0.0036 | +1.1 | 0.747 | 0.743 | |
| agree (<0.05) | 624 | +0.0022 ±0.0029 | +0.0003 ±0.0009 | +0.7 | 0.702 | 0.704 | |
| tour: atp | 652 | +0.0058 ±0.0081 | +0.0024 ±0.0033 | +0.7 | 0.669 | 0.679 | |
| tier: masters | 179 | +0.0046 ±0.0116 | +0.0032 ±0.0051 | +0.4 | 0.679 | 0.682 | |
| month 2026-05 | 493 | +0.0035 ±0.0090 | -0.0001 ±0.0035 | +0.4 | 0.677 | 0.687 | |
| surface: Clay | 689 | +0.0026 ±0.0073 | -0.0001 ±0.0029 | +0.4 | 0.669 | 0.689 | |
| round late (QF-F) | 174 | +0.0007 ±0.0116 | -0.0007 ±0.0050 | +0.1 | 0.638 | 0.638 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| no top-20 player | 893 | -0.0158 ±0.0075 | -0.0065 ±0.0032 | -2.1 | 0.638 | 0.661 | |
| best rank 100+ | 77 | -0.0794 ±0.0372 | -0.0351 ±0.0157 | -2.1 | 0.610 | 0.682 | |
| kalshi favorite 0.5-0.6 | 374 | -0.0237 ±0.0104 | -0.0105 ±0.0048 | -2.3 | 0.517 | 0.567 | |
| month 2026-06 | 439 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.640 | 0.662 | |
| surface: Grass | 585 | -0.0212 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.681 | |
| someone outside top-50 | 1052 | -0.0171 ±0.0067 | -0.0073 ±0.0027 | -2.6 | 0.669 | 0.691 | |
| pred_source: live | 463 | -0.0290 ±0.0102 | -0.0102 ±0.0043 | -2.8 | 0.685 | 0.703 | |
| tour: wta | 661 | -0.0270 ±0.0081 | -0.0113 ±0.0034 | -3.3 | 0.673 | 0.690 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1313, mean |Δ|=0.0015, p95=0.0085, >0.05 in 0 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0090 (n=493, >0.05: 0) | 2026-06 p95=0.0085 (n=439, >0.05: 0) | 2026-07 p95=0.0074 (n=381, >0.05: 0)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1313, d_ll -0.0107 ±0.0058 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 386 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'WTA Iasi': 6, 'WTA Hamburg': 5, 'ATP Hamburg': 1, 'ATP Mallorca': 1, 'ATP Stuttgart': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Anhelina Kalinina, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Arantxa Rus, Ashlyn Krueger, Ayana Akli, Bianca Andreescu, Cadence Brace, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Casper Ruud, Celine Naef, Chloe Paquet, Claire Liu, Dalma Galfi, Daphnee Mpetshi Perricard, Darja Semenistaja, Darja Vidmanova, Despina Papamichail, Dominika Salkova, Ekaterine Gorgodze, Eleejah Inisan, Elena Pridankina, Elizabeth Mandlik, Elizara Yaneva, Elsa Jacquemot
