# Model vs Kalshi — match-by-match scorecard

_Generated 2026-07-29T00:24:43Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1223 | 1158 | 18 | 5 | 42 | 0 | 8 | 14 | 166 | 2026-05-03..2026-07-29 |
| wta | 1239 | 700 | 30 | 476 | 33 | 0 | 2 | 15 | 24 | 2026-05-02..2026-07-29 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1322 | 0.6014 | 0.5916 | -0.0098 ±0.0058 | -0.0043 ±0.0024 | 0.669 | 0.684 |
| atp | 658 | 0.6074 | 0.6157 | +0.0083 ±0.0082 | +0.0032 ±0.0033 | 0.666 | 0.676 |
| wta | 664 | 0.5955 | 0.5677 | -0.0278 ±0.0081 | -0.0117 ±0.0034 | 0.673 | 0.691 |
| pooled/live | 472 | 0.6037 | 0.5775 | -0.0262 ±0.0103 | -0.0094 ±0.0043 | 0.680 | 0.700 |
| pooled/backtest | 850 | 0.6002 | 0.5994 | -0.0008 ±0.0069 | -0.0014 ±0.0028 | 0.664 | 0.675 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live | 472 | -0.0262 ±0.0103 | -0.0094 ±0.0043 | -2.6 | 0.680 | 0.700 | |
| pred_source: backtest | 850 | -0.0008 ±0.0069 | -0.0014 ±0.0028 | -0.1 | 0.664 | 0.675 | |
| top-20 involved | 423 | +0.0023 ±0.0086 | +0.0006 ±0.0031 | +0.3 | 0.739 | 0.732 | |
| no top-20 player | 899 | -0.0155 ±0.0074 | -0.0065 ±0.0032 | -2.1 | 0.637 | 0.661 | |
| both inside top-50 | 264 | +0.0170 ±0.0108 | +0.0077 ±0.0047 | +1.6 | 0.676 | 0.657 | |
| someone outside top-50 | 1058 | -0.0165 ±0.0067 | -0.0072 ±0.0027 | -2.5 | 0.668 | 0.690 | |
| best rank 1-10 | 237 | +0.0127 ±0.0119 | +0.0043 ±0.0036 | +1.1 | 0.747 | 0.743 | |
| best rank 11-20 | 186 | -0.0111 ±0.0124 | -0.0041 ±0.0052 | -0.9 | 0.728 | 0.718 | |
| best rank 21-50 | 458 | -0.0083 ±0.0087 | -0.0024 ±0.0038 | -1.0 | 0.655 | 0.670 | |
| best rank 51-100 | 364 | -0.0112 ±0.0125 | -0.0057 ±0.0053 | -0.9 | 0.620 | 0.646 | |
| best rank 100+ | 77 | -0.0794 ±0.0372 | -0.0351 ±0.0157 | -2.1 | 0.610 | 0.682 | |
| kalshi favorite 0.5-0.6 | 376 | -0.0248 ±0.0104 | -0.0111 ±0.0048 | -2.4 | 0.515 | 0.566 | |
| kalshi favorite 0.6-0.7 | 380 | -0.0012 ±0.0096 | -0.0006 ±0.0045 | -0.1 | 0.632 | 0.632 | |
| kalshi favorite 0.7-0.8 | 295 | -0.0012 ±0.0112 | -0.0005 ±0.0045 | -0.1 | 0.734 | 0.736 | |
| kalshi favorite 0.8-0.9 | 188 | -0.0065 ±0.0182 | -0.0032 ±0.0066 | -0.4 | 0.830 | 0.830 | |
| kalshi favorite 0.9-1.0 | 83 | -0.0198 ±0.0320 | -0.0063 ±0.0081 | -0.6 | 0.952 | 0.940 | |
| surface: Hard | 48 | -0.0498 ±0.0503 | -0.0221 ±0.0205 | -1.0 | 0.625 | 0.646 | ⚠ small n |
| surface: Clay | 689 | +0.0026 ±0.0073 | -0.0001 ±0.0029 | +0.4 | 0.669 | 0.689 | |
| surface: Grass | 585 | -0.0212 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.681 | |
| tier: atp250 | 486 | -0.0047 ±0.0102 | -0.0029 ±0.0043 | -0.5 | 0.648 | 0.673 | |
| tier: atp500 | 181 | -0.0148 ±0.0103 | -0.0071 ±0.0046 | -1.4 | 0.608 | 0.622 | |
| tier: grand_slam | 476 | -0.0187 ±0.0107 | -0.0074 ±0.0042 | -1.8 | 0.711 | 0.720 | |
| tier: masters | 179 | +0.0046 ±0.0116 | +0.0032 ±0.0051 | +0.4 | 0.679 | 0.682 | |
| round early (R128-R64) | 506 | -0.0197 ±0.0101 | -0.0073 ±0.0041 | -1.9 | 0.712 | 0.722 | |
| round late (QF-F) | 174 | +0.0007 ±0.0116 | -0.0007 ±0.0050 | +0.1 | 0.638 | 0.638 | |
| round mid (R32-R16) | 620 | -0.0049 ±0.0085 | -0.0028 ±0.0036 | -0.6 | 0.649 | 0.670 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 493 | +0.0035 ±0.0090 | -0.0001 ±0.0035 | +0.4 | 0.677 | 0.687 | |
| month 2026-06 | 439 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.640 | 0.662 | |
| month 2026-07 | 390 | -0.0099 ±0.0108 | -0.0026 ±0.0046 | -0.9 | 0.692 | 0.705 | |
| agree (<0.05) | 625 | +0.0020 ±0.0029 | +0.0002 ±0.0009 | +0.7 | 0.701 | 0.703 | |
| mild disagree (0.05-0.10) | 413 | -0.0044 ±0.0087 | -0.0026 ±0.0033 | -0.5 | 0.640 | 0.668 | |
| big disagree (>=0.1) | 284 | -0.0438 ±0.0227 | -0.0165 ±0.0097 | -1.9 | 0.643 | 0.664 | |
| tour: atp | 658 | +0.0083 ±0.0082 | +0.0032 ±0.0033 | +1.0 | 0.666 | 0.676 | |
| tour: wta | 664 | -0.0278 ±0.0081 | -0.0117 ±0.0034 | -3.4 | 0.673 | 0.691 | |

When they disagree by >= 0.1: model closer to the outcome in **106/284** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 12 | 0.067 | 0.083 |
| 0.1-0.2 | 73 | 0.156 | 0.137 |
| 0.2-0.3 | 115 | 0.250 | 0.209 |
| 0.3-0.4 | 187 | 0.352 | 0.321 |
| 0.4-0.5 | 225 | 0.450 | 0.476 |
| 0.5-0.6 | 220 | 0.550 | 0.573 |
| 0.6-0.7 | 204 | 0.645 | 0.618 |
| 0.7-0.8 | 168 | 0.747 | 0.732 |
| 0.8-0.9 | 94 | 0.844 | 0.840 |
| 0.9-1.0 | 24 | 0.927 | 0.875 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 32 | 0.062 | 0.062 |
| 0.1-0.2 | 80 | 0.153 | 0.125 |
| 0.2-0.3 | 127 | 0.253 | 0.268 |
| 0.3-0.4 | 171 | 0.353 | 0.345 |
| 0.4-0.5 | 197 | 0.442 | 0.431 |
| 0.5-0.6 | 181 | 0.558 | 0.558 |
| 0.6-0.7 | 207 | 0.650 | 0.618 |
| 0.7-0.8 | 168 | 0.746 | 0.738 |
| 0.8-0.9 | 108 | 0.844 | 0.796 |
| 0.9-1.0 | 51 | 0.938 | 0.941 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| both inside top-50 | 264 | +0.0170 ±0.0108 | +0.0077 ±0.0047 | +1.6 | 0.676 | 0.657 | |
| best rank 1-10 | 237 | +0.0127 ±0.0119 | +0.0043 ±0.0036 | +1.1 | 0.747 | 0.743 | |
| tour: atp | 658 | +0.0083 ±0.0082 | +0.0032 ±0.0033 | +1.0 | 0.666 | 0.676 | |
| agree (<0.05) | 625 | +0.0020 ±0.0029 | +0.0002 ±0.0009 | +0.7 | 0.701 | 0.703 | |
| tier: masters | 179 | +0.0046 ±0.0116 | +0.0032 ±0.0051 | +0.4 | 0.679 | 0.682 | |
| month 2026-05 | 493 | +0.0035 ±0.0090 | -0.0001 ±0.0035 | +0.4 | 0.677 | 0.687 | |
| surface: Clay | 689 | +0.0026 ±0.0073 | -0.0001 ±0.0029 | +0.4 | 0.669 | 0.689 | |
| top-20 involved | 423 | +0.0023 ±0.0086 | +0.0006 ±0.0031 | +0.3 | 0.739 | 0.732 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| no top-20 player | 899 | -0.0155 ±0.0074 | -0.0065 ±0.0032 | -2.1 | 0.637 | 0.661 | |
| best rank 100+ | 77 | -0.0794 ±0.0372 | -0.0351 ±0.0157 | -2.1 | 0.610 | 0.682 | |
| kalshi favorite 0.5-0.6 | 376 | -0.0248 ±0.0104 | -0.0111 ±0.0048 | -2.4 | 0.515 | 0.566 | |
| month 2026-06 | 439 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.640 | 0.662 | |
| surface: Grass | 585 | -0.0212 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.681 | |
| someone outside top-50 | 1058 | -0.0165 ±0.0067 | -0.0072 ±0.0027 | -2.5 | 0.668 | 0.690 | |
| pred_source: live | 472 | -0.0262 ±0.0103 | -0.0094 ±0.0043 | -2.6 | 0.680 | 0.700 | |
| tour: wta | 664 | -0.0278 ±0.0081 | -0.0117 ±0.0034 | -3.4 | 0.673 | 0.691 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1322, mean |Δ|=0.0015, p95=0.0085, >0.05 in 0 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0090 (n=493, >0.05: 0) | 2026-06 p95=0.0085 (n=439, >0.05: 0) | 2026-07 p95=0.0073 (n=390, >0.05: 0)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1322, d_ll -0.0098 ±0.0058 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 387 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'WTA Memphis': 7, 'WTA Washington': 7, 'WTA Hamburg': 6, 'WTA Iasi': 6, 'ATP Hamburg': 1, 'ATP Mallorca': 1, 'ATP Stuttgart': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Carolyn Ansari, Casper Ruud, Celine Naef, Chloe Paquet, Claire Liu, Clervie Ngounoue, Dalma Galfi, Daphnee Mpetshi Perricard, Daria Kasatkina, Darja Semenistaja
