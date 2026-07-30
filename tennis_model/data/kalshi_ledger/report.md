# Model vs Kalshi — match-by-match scorecard

_Generated 2026-07-30T03:23:51Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1234 | 1174 | 12 | 6 | 42 | 0 | 8 | 14 | 108 | 2026-05-03..2026-07-30 |
| wta | 1245 | 716 | 10 | 486 | 33 | 0 | 2 | 15 | 27 | 2026-05-02..2026-07-30 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1338 | 0.6026 | 0.5921 | -0.0105 ±0.0058 | -0.0045 ±0.0024 | 0.667 | 0.683 |
| atp | 667 | 0.6064 | 0.6147 | +0.0082 ±0.0081 | +0.0032 ±0.0033 | 0.666 | 0.678 |
| wta | 671 | 0.5988 | 0.5696 | -0.0292 ±0.0082 | -0.0121 ±0.0034 | 0.669 | 0.689 |
| pooled/live | 486 | 0.6030 | 0.5776 | -0.0254 ±0.0101 | -0.0091 ±0.0043 | 0.677 | 0.701 |
| pooled/backtest | 852 | 0.6023 | 0.6003 | -0.0021 ±0.0070 | -0.0019 ±0.0028 | 0.662 | 0.673 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live | 486 | -0.0254 ±0.0101 | -0.0091 ±0.0043 | -2.5 | 0.677 | 0.701 | |
| pred_source: backtest | 852 | -0.0021 ±0.0070 | -0.0019 ±0.0028 | -0.3 | 0.662 | 0.673 | |
| top-20 involved | 427 | +0.0007 ±0.0089 | +0.0002 ±0.0032 | +0.1 | 0.739 | 0.732 | |
| no top-20 player | 911 | -0.0158 ±0.0074 | -0.0067 ±0.0032 | -2.1 | 0.634 | 0.660 | |
| both inside top-50 | 265 | +0.0180 ±0.0108 | +0.0081 ±0.0047 | +1.7 | 0.674 | 0.655 | |
| someone outside top-50 | 1073 | -0.0176 ±0.0067 | -0.0076 ±0.0027 | -2.6 | 0.666 | 0.690 | |
| best rank 1-10 | 239 | +0.0137 ±0.0119 | +0.0048 ±0.0036 | +1.2 | 0.749 | 0.745 | |
| best rank 11-20 | 188 | -0.0158 ±0.0134 | -0.0057 ±0.0054 | -1.2 | 0.726 | 0.715 | |
| best rank 21-50 | 462 | -0.0080 ±0.0086 | -0.0023 ±0.0037 | -0.9 | 0.654 | 0.669 | |
| best rank 51-100 | 370 | -0.0108 ±0.0123 | -0.0055 ±0.0053 | -0.9 | 0.618 | 0.646 | |
| best rank 100+ | 79 | -0.0848 ±0.0366 | -0.0378 ±0.0155 | -2.3 | 0.595 | 0.677 | |
| kalshi favorite 0.5-0.6 | 383 | -0.0242 ±0.0103 | -0.0108 ±0.0047 | -2.4 | 0.516 | 0.569 | |
| kalshi favorite 0.6-0.7 | 385 | -0.0042 ±0.0099 | -0.0016 ±0.0046 | -0.4 | 0.623 | 0.626 | |
| kalshi favorite 0.7-0.8 | 297 | -0.0009 ±0.0111 | -0.0004 ±0.0045 | -0.1 | 0.736 | 0.737 | |
| kalshi favorite 0.8-0.9 | 190 | -0.0068 ±0.0180 | -0.0033 ±0.0065 | -0.4 | 0.832 | 0.832 | |
| kalshi favorite 0.9-1.0 | 83 | -0.0198 ±0.0320 | -0.0063 ±0.0081 | -0.6 | 0.952 | 0.940 | |
| surface: Hard | 64 | -0.0540 ±0.0421 | -0.0226 ±0.0170 | -1.3 | 0.594 | 0.641 | |
| surface: Clay | 689 | +0.0026 ±0.0073 | -0.0001 ±0.0029 | +0.4 | 0.669 | 0.689 | |
| surface: Grass | 585 | -0.0212 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.681 | |
| tier: atp250 | 502 | -0.0067 ±0.0102 | -0.0035 ±0.0043 | -0.7 | 0.643 | 0.671 | |
| tier: atp500 | 181 | -0.0148 ±0.0103 | -0.0071 ±0.0046 | -1.4 | 0.608 | 0.622 | |
| tier: grand_slam | 476 | -0.0187 ±0.0107 | -0.0074 ±0.0042 | -1.8 | 0.711 | 0.720 | |
| tier: masters | 179 | +0.0046 ±0.0116 | +0.0032 ±0.0051 | +0.4 | 0.679 | 0.682 | |
| round early (R128-R64) | 506 | -0.0197 ±0.0101 | -0.0073 ±0.0041 | -1.9 | 0.712 | 0.722 | |
| round late (QF-F) | 174 | +0.0007 ±0.0116 | -0.0007 ±0.0050 | +0.1 | 0.638 | 0.638 | |
| round mid (R32-R16) | 636 | -0.0065 ±0.0085 | -0.0034 ±0.0035 | -0.8 | 0.645 | 0.669 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 493 | +0.0035 ±0.0090 | -0.0001 ±0.0035 | +0.4 | 0.677 | 0.687 | |
| month 2026-06 | 439 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.640 | 0.662 | |
| month 2026-07 | 406 | -0.0122 ±0.0108 | -0.0034 ±0.0046 | -1.1 | 0.685 | 0.702 | |
| agree (<0.05) | 633 | +0.0018 ±0.0029 | +0.0002 ±0.0009 | +0.6 | 0.698 | 0.701 | |
| mild disagree (0.05-0.10) | 415 | -0.0044 ±0.0087 | -0.0026 ±0.0033 | -0.5 | 0.642 | 0.670 | |
| big disagree (>=0.1) | 290 | -0.0462 ±0.0226 | -0.0173 ±0.0097 | -2.0 | 0.636 | 0.664 | |
| tour: atp | 667 | +0.0082 ±0.0081 | +0.0032 ±0.0033 | +1.0 | 0.666 | 0.678 | |
| tour: wta | 671 | -0.0292 ±0.0082 | -0.0121 ±0.0034 | -3.6 | 0.669 | 0.689 | |

When they disagree by >= 0.1: model closer to the outcome in **109/290** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 12 | 0.067 | 0.083 |
| 0.1-0.2 | 74 | 0.157 | 0.135 |
| 0.2-0.3 | 116 | 0.250 | 0.207 |
| 0.3-0.4 | 189 | 0.352 | 0.328 |
| 0.4-0.5 | 230 | 0.449 | 0.478 |
| 0.5-0.6 | 221 | 0.550 | 0.570 |
| 0.6-0.7 | 206 | 0.645 | 0.617 |
| 0.7-0.8 | 170 | 0.747 | 0.735 |
| 0.8-0.9 | 96 | 0.844 | 0.833 |
| 0.9-1.0 | 24 | 0.927 | 0.875 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 32 | 0.062 | 0.062 |
| 0.1-0.2 | 81 | 0.153 | 0.123 |
| 0.2-0.3 | 127 | 0.253 | 0.268 |
| 0.3-0.4 | 172 | 0.353 | 0.349 |
| 0.4-0.5 | 202 | 0.442 | 0.431 |
| 0.5-0.6 | 183 | 0.558 | 0.563 |
| 0.6-0.7 | 211 | 0.650 | 0.611 |
| 0.7-0.8 | 170 | 0.747 | 0.741 |
| 0.8-0.9 | 109 | 0.844 | 0.798 |
| 0.9-1.0 | 51 | 0.938 | 0.941 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| both inside top-50 | 265 | +0.0180 ±0.0108 | +0.0081 ±0.0047 | +1.7 | 0.674 | 0.655 | |
| best rank 1-10 | 239 | +0.0137 ±0.0119 | +0.0048 ±0.0036 | +1.2 | 0.749 | 0.745 | |
| tour: atp | 667 | +0.0082 ±0.0081 | +0.0032 ±0.0033 | +1.0 | 0.666 | 0.678 | |
| agree (<0.05) | 633 | +0.0018 ±0.0029 | +0.0002 ±0.0009 | +0.6 | 0.698 | 0.701 | |
| tier: masters | 179 | +0.0046 ±0.0116 | +0.0032 ±0.0051 | +0.4 | 0.679 | 0.682 | |
| month 2026-05 | 493 | +0.0035 ±0.0090 | -0.0001 ±0.0035 | +0.4 | 0.677 | 0.687 | |
| surface: Clay | 689 | +0.0026 ±0.0073 | -0.0001 ±0.0029 | +0.4 | 0.669 | 0.689 | |
| top-20 involved | 427 | +0.0007 ±0.0089 | +0.0002 ±0.0032 | +0.1 | 0.739 | 0.732 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| no top-20 player | 911 | -0.0158 ±0.0074 | -0.0067 ±0.0032 | -2.1 | 0.634 | 0.660 | |
| best rank 100+ | 79 | -0.0848 ±0.0366 | -0.0378 ±0.0155 | -2.3 | 0.595 | 0.677 | |
| kalshi favorite 0.5-0.6 | 383 | -0.0242 ±0.0103 | -0.0108 ±0.0047 | -2.4 | 0.516 | 0.569 | |
| month 2026-06 | 439 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.640 | 0.662 | |
| surface: Grass | 585 | -0.0212 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.681 | |
| pred_source: live | 486 | -0.0254 ±0.0101 | -0.0091 ±0.0043 | -2.5 | 0.677 | 0.701 | |
| someone outside top-50 | 1073 | -0.0176 ±0.0067 | -0.0076 ±0.0027 | -2.6 | 0.666 | 0.690 | |
| tour: wta | 671 | -0.0292 ±0.0082 | -0.0121 ±0.0034 | -3.6 | 0.669 | 0.689 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1338, mean |Δ|=0.0018, p95=0.0085, >0.05 in 1 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0090 (n=493, >0.05: 0) | 2026-06 p95=0.0085 (n=439, >0.05: 0) | 2026-07 p95=0.0078 (n=406, >0.05: 1)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1338, d_ll -0.0105 ±0.0058 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 397 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'WTA Memphis': 7, 'WTA Washington': 7, 'WTA Hamburg': 6, 'WTA Iasi': 6, 'ATP Hamburg': 1, 'ATP Los Cabos': 1, 'ATP Mallorca': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Carolyn Ansari, Casper Ruud, Celine Naef, Chloe Paquet, Claire Liu, Clervie Ngounoue, Dalma Galfi, Daphnee Mpetshi Perricard, Daria Kasatkina, Darja Semenistaja
