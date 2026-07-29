# Model vs Kalshi — match-by-match scorecard

_Generated 2026-07-29T07:37:35Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1227 | 1166 | 14 | 5 | 42 | 0 | 8 | 14 | 170 | 2026-05-03..2026-07-30 |
| wta | 1240 | 707 | 24 | 476 | 33 | 0 | 2 | 15 | 26 | 2026-05-02..2026-07-30 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1330 | 0.6028 | 0.5923 | -0.0105 ±0.0058 | -0.0045 ±0.0024 | 0.668 | 0.683 |
| atp | 660 | 0.6063 | 0.6147 | +0.0084 ±0.0082 | +0.0033 ±0.0033 | 0.667 | 0.677 |
| wta | 670 | 0.5993 | 0.5702 | -0.0291 ±0.0082 | -0.0121 ±0.0034 | 0.669 | 0.688 |
| pooled/live | 478 | 0.6035 | 0.5780 | -0.0255 ±0.0102 | -0.0092 ±0.0043 | 0.678 | 0.700 |
| pooled/backtest | 852 | 0.6023 | 0.6003 | -0.0021 ±0.0070 | -0.0019 ±0.0028 | 0.662 | 0.673 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live | 478 | -0.0255 ±0.0102 | -0.0092 ±0.0043 | -2.5 | 0.678 | 0.700 | |
| pred_source: backtest | 852 | -0.0021 ±0.0070 | -0.0019 ±0.0028 | -0.3 | 0.662 | 0.673 | |
| top-20 involved | 426 | +0.0001 ±0.0089 | -0.0001 ±0.0031 | +0.0 | 0.738 | 0.731 | |
| no top-20 player | 904 | -0.0155 ±0.0074 | -0.0065 ±0.0032 | -2.1 | 0.634 | 0.660 | |
| both inside top-50 | 265 | +0.0180 ±0.0108 | +0.0081 ±0.0047 | +1.7 | 0.674 | 0.655 | |
| someone outside top-50 | 1065 | -0.0176 ±0.0067 | -0.0076 ±0.0027 | -2.6 | 0.666 | 0.690 | |
| best rank 1-10 | 238 | +0.0128 ±0.0119 | +0.0043 ±0.0036 | +1.1 | 0.748 | 0.744 | |
| best rank 11-20 | 188 | -0.0158 ±0.0134 | -0.0057 ±0.0054 | -1.2 | 0.726 | 0.715 | |
| best rank 21-50 | 460 | -0.0079 ±0.0087 | -0.0023 ±0.0037 | -0.9 | 0.652 | 0.667 | |
| best rank 51-100 | 366 | -0.0104 ±0.0124 | -0.0053 ±0.0053 | -0.8 | 0.619 | 0.645 | |
| best rank 100+ | 78 | -0.0845 ±0.0371 | -0.0376 ±0.0157 | -2.3 | 0.603 | 0.686 | |
| kalshi favorite 0.5-0.6 | 378 | -0.0244 ±0.0104 | -0.0109 ±0.0048 | -2.4 | 0.515 | 0.566 | |
| kalshi favorite 0.6-0.7 | 384 | -0.0042 ±0.0100 | -0.0016 ±0.0046 | -0.4 | 0.625 | 0.628 | |
| kalshi favorite 0.7-0.8 | 297 | -0.0009 ±0.0111 | -0.0004 ±0.0045 | -0.1 | 0.736 | 0.737 | |
| kalshi favorite 0.8-0.9 | 188 | -0.0065 ±0.0182 | -0.0032 ±0.0066 | -0.4 | 0.830 | 0.830 | |
| kalshi favorite 0.9-1.0 | 83 | -0.0198 ±0.0320 | -0.0063 ±0.0081 | -0.6 | 0.952 | 0.940 | |
| surface: Hard | 56 | -0.0595 ±0.0476 | -0.0249 ±0.0191 | -1.3 | 0.589 | 0.625 | |
| surface: Clay | 689 | +0.0026 ±0.0073 | -0.0001 ±0.0029 | +0.4 | 0.669 | 0.689 | |
| surface: Grass | 585 | -0.0212 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.681 | |
| tier: atp250 | 494 | -0.0065 ±0.0103 | -0.0035 ±0.0043 | -0.6 | 0.644 | 0.670 | |
| tier: atp500 | 181 | -0.0148 ±0.0103 | -0.0071 ±0.0046 | -1.4 | 0.608 | 0.622 | |
| tier: grand_slam | 476 | -0.0187 ±0.0107 | -0.0074 ±0.0042 | -1.8 | 0.711 | 0.720 | |
| tier: masters | 179 | +0.0046 ±0.0116 | +0.0032 ±0.0051 | +0.4 | 0.679 | 0.682 | |
| round early (R128-R64) | 506 | -0.0197 ±0.0101 | -0.0073 ±0.0041 | -1.9 | 0.712 | 0.722 | |
| round late (QF-F) | 174 | +0.0007 ±0.0116 | -0.0007 ±0.0050 | +0.1 | 0.638 | 0.638 | |
| round mid (R32-R16) | 628 | -0.0064 ±0.0085 | -0.0033 ±0.0036 | -0.7 | 0.646 | 0.668 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 493 | +0.0035 ±0.0090 | -0.0001 ±0.0035 | +0.4 | 0.677 | 0.687 | |
| month 2026-06 | 439 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.640 | 0.662 | |
| month 2026-07 | 398 | -0.0121 ±0.0110 | -0.0034 ±0.0046 | -1.1 | 0.686 | 0.701 | |
| agree (<0.05) | 628 | +0.0019 ±0.0029 | +0.0002 ±0.0009 | +0.7 | 0.699 | 0.701 | |
| mild disagree (0.05-0.10) | 414 | -0.0043 ±0.0087 | -0.0026 ±0.0033 | -0.5 | 0.641 | 0.669 | |
| big disagree (>=0.1) | 288 | -0.0465 ±0.0227 | -0.0174 ±0.0097 | -2.0 | 0.637 | 0.661 | |
| tour: atp | 660 | +0.0084 ±0.0082 | +0.0033 ±0.0033 | +1.0 | 0.667 | 0.677 | |
| tour: wta | 670 | -0.0291 ±0.0082 | -0.0121 ±0.0034 | -3.6 | 0.669 | 0.688 | |

When they disagree by >= 0.1: model closer to the outcome in **108/288** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 12 | 0.067 | 0.083 |
| 0.1-0.2 | 73 | 0.156 | 0.137 |
| 0.2-0.3 | 116 | 0.250 | 0.207 |
| 0.3-0.4 | 189 | 0.352 | 0.328 |
| 0.4-0.5 | 226 | 0.449 | 0.478 |
| 0.5-0.6 | 221 | 0.550 | 0.570 |
| 0.6-0.7 | 204 | 0.645 | 0.618 |
| 0.7-0.8 | 169 | 0.747 | 0.734 |
| 0.8-0.9 | 96 | 0.844 | 0.833 |
| 0.9-1.0 | 24 | 0.927 | 0.875 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 32 | 0.062 | 0.062 |
| 0.1-0.2 | 80 | 0.153 | 0.125 |
| 0.2-0.3 | 127 | 0.253 | 0.268 |
| 0.3-0.4 | 172 | 0.353 | 0.349 |
| 0.4-0.5 | 199 | 0.442 | 0.432 |
| 0.5-0.6 | 181 | 0.558 | 0.558 |
| 0.6-0.7 | 210 | 0.650 | 0.614 |
| 0.7-0.8 | 170 | 0.747 | 0.741 |
| 0.8-0.9 | 108 | 0.844 | 0.796 |
| 0.9-1.0 | 51 | 0.938 | 0.941 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| both inside top-50 | 265 | +0.0180 ±0.0108 | +0.0081 ±0.0047 | +1.7 | 0.674 | 0.655 | |
| best rank 1-10 | 238 | +0.0128 ±0.0119 | +0.0043 ±0.0036 | +1.1 | 0.748 | 0.744 | |
| tour: atp | 660 | +0.0084 ±0.0082 | +0.0033 ±0.0033 | +1.0 | 0.667 | 0.677 | |
| agree (<0.05) | 628 | +0.0019 ±0.0029 | +0.0002 ±0.0009 | +0.7 | 0.699 | 0.701 | |
| tier: masters | 179 | +0.0046 ±0.0116 | +0.0032 ±0.0051 | +0.4 | 0.679 | 0.682 | |
| month 2026-05 | 493 | +0.0035 ±0.0090 | -0.0001 ±0.0035 | +0.4 | 0.677 | 0.687 | |
| surface: Clay | 689 | +0.0026 ±0.0073 | -0.0001 ±0.0029 | +0.4 | 0.669 | 0.689 | |
| round late (QF-F) | 174 | +0.0007 ±0.0116 | -0.0007 ±0.0050 | +0.1 | 0.638 | 0.638 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| no top-20 player | 904 | -0.0155 ±0.0074 | -0.0065 ±0.0032 | -2.1 | 0.634 | 0.660 | |
| best rank 100+ | 78 | -0.0845 ±0.0371 | -0.0376 ±0.0157 | -2.3 | 0.603 | 0.686 | |
| kalshi favorite 0.5-0.6 | 378 | -0.0244 ±0.0104 | -0.0109 ±0.0048 | -2.4 | 0.515 | 0.566 | |
| month 2026-06 | 439 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.640 | 0.662 | |
| surface: Grass | 585 | -0.0212 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.681 | |
| pred_source: live | 478 | -0.0255 ±0.0102 | -0.0092 ±0.0043 | -2.5 | 0.678 | 0.700 | |
| someone outside top-50 | 1065 | -0.0176 ±0.0067 | -0.0076 ±0.0027 | -2.6 | 0.666 | 0.690 | |
| tour: wta | 670 | -0.0291 ±0.0082 | -0.0121 ±0.0034 | -3.6 | 0.669 | 0.688 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1330, mean |Δ|=0.0015, p95=0.0084, >0.05 in 0 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0090 (n=493, >0.05: 0) | 2026-06 p95=0.0085 (n=439, >0.05: 0) | 2026-07 p95=0.0072 (n=398, >0.05: 0)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1330, d_ll -0.0105 ±0.0058 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 387 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'WTA Washington': 7, 'WTA Memphis': 7, 'WTA Iasi': 6, 'WTA Hamburg': 6, 'ATP Stuttgart': 1, 'ATP Hamburg': 1, 'ATP Mallorca': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Carolyn Ansari, Casper Ruud, Celine Naef, Chloe Paquet, Claire Liu, Clervie Ngounoue, Dalma Galfi, Daphnee Mpetshi Perricard, Daria Kasatkina, Darja Semenistaja
