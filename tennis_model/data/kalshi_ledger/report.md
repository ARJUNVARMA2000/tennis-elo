# Model vs Kalshi — match-by-match scorecard

_Generated 2026-08-02T07:05:15Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1289 | 1198 | 42 | 7 | 42 | 0 | 8 | 14 | 45 | 2026-05-03..2026-08-03 |
| wta | 1305 | 736 | 46 | 487 | 36 | 0 | 3 | 15 | 42 | 2026-05-02..2026-08-02 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1383 | 0.6037 | 0.5929 | -0.0108 ±0.0057 | -0.0048 ±0.0023 | 0.666 | 0.683 |
| atp | 686 | 0.6058 | 0.6138 | +0.0081 ±0.0081 | +0.0030 ±0.0033 | 0.669 | 0.679 |
| wta | 697 | 0.6017 | 0.5723 | -0.0294 ±0.0080 | -0.0124 ±0.0033 | 0.663 | 0.687 |
| pooled/live | 521 | 0.6064 | 0.5812 | -0.0252 ±0.0098 | -0.0095 ±0.0041 | 0.672 | 0.698 |
| pooled/backtest | 862 | 0.6021 | 0.5999 | -0.0022 ±0.0069 | -0.0019 ±0.0028 | 0.662 | 0.675 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live | 521 | -0.0252 ±0.0098 | -0.0095 ±0.0041 | -2.6 | 0.672 | 0.698 | |
| pred_source: backtest | 862 | -0.0022 ±0.0069 | -0.0019 ±0.0028 | -0.3 | 0.662 | 0.675 | |
| top-20 involved | 451 | -0.0014 ±0.0085 | -0.0009 ±0.0030 | -0.2 | 0.742 | 0.737 | |
| no top-20 player | 932 | -0.0154 ±0.0074 | -0.0066 ±0.0032 | -2.1 | 0.629 | 0.657 | |
| both inside top-50 | 284 | +0.0130 ±0.0103 | +0.0058 ±0.0045 | +1.3 | 0.674 | 0.660 | |
| someone outside top-50 | 1099 | -0.0170 ±0.0066 | -0.0075 ±0.0027 | -2.6 | 0.664 | 0.689 | |
| best rank 1-10 | 251 | +0.0120 ±0.0113 | +0.0039 ±0.0035 | +1.1 | 0.753 | 0.749 | |
| best rank 11-20 | 200 | -0.0182 ±0.0128 | -0.0070 ±0.0052 | -1.4 | 0.728 | 0.723 | |
| best rank 21-50 | 472 | -0.0083 ±0.0085 | -0.0024 ±0.0037 | -1.0 | 0.653 | 0.667 | |
| best rank 51-100 | 381 | -0.0093 ±0.0124 | -0.0051 ±0.0053 | -0.8 | 0.608 | 0.638 | |
| best rank 100+ | 79 | -0.0869 ±0.0367 | -0.0389 ±0.0155 | -2.4 | 0.595 | 0.690 | |
| kalshi favorite 0.5-0.6 | 391 | -0.0253 ±0.0102 | -0.0114 ±0.0047 | -2.5 | 0.513 | 0.570 | |
| kalshi favorite 0.6-0.7 | 403 | -0.0058 ±0.0096 | -0.0024 ±0.0044 | -0.6 | 0.618 | 0.623 | |
| kalshi favorite 0.7-0.8 | 312 | -0.0031 ±0.0108 | -0.0014 ±0.0044 | -0.3 | 0.742 | 0.744 | |
| kalshi favorite 0.8-0.9 | 194 | -0.0008 ±0.0184 | -0.0013 ±0.0066 | -0.0 | 0.830 | 0.830 | |
| kalshi favorite 0.9-1.0 | 83 | -0.0198 ±0.0320 | -0.0063 ±0.0081 | -0.6 | 0.952 | 0.940 | |
| surface: Hard | 103 | -0.0401 ±0.0299 | -0.0185 ±0.0121 | -1.3 | 0.602 | 0.650 | |
| surface: Clay | 695 | +0.0022 ±0.0073 | -0.0003 ±0.0029 | +0.3 | 0.669 | 0.690 | |
| surface: Grass | 585 | -0.0212 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.681 | |
| tier: atp250 | 540 | -0.0076 ±0.0099 | -0.0042 ±0.0041 | -0.8 | 0.641 | 0.670 | |
| tier: atp500 | 184 | -0.0139 ±0.0102 | -0.0067 ±0.0046 | -1.4 | 0.614 | 0.628 | |
| tier: grand_slam | 476 | -0.0187 ±0.0107 | -0.0074 ±0.0042 | -1.8 | 0.711 | 0.720 | |
| tier: masters | 183 | +0.0032 ±0.0114 | +0.0026 ±0.0051 | +0.3 | 0.675 | 0.683 | |
| round early (R128-R64) | 509 | -0.0196 ±0.0101 | -0.0072 ±0.0040 | -1.9 | 0.712 | 0.722 | |
| round late (QF-F) | 193 | -0.0100 ±0.0114 | -0.0057 ±0.0049 | -0.9 | 0.622 | 0.642 | |
| round mid (R32-R16) | 659 | -0.0045 ±0.0084 | -0.0026 ±0.0035 | -0.5 | 0.649 | 0.670 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 439 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.640 | 0.662 | |
| month 2026-07 | 436 | -0.0086 ±0.0105 | -0.0023 ±0.0044 | -0.8 | 0.683 | 0.697 | |
| month 2026-08 | 9 | -0.2072 ±0.0495 | -0.0961 ±0.0240 | -4.2 | 0.444 | 0.778 | ⚠ small n |
| agree (<0.05) | 655 | +0.0010 ±0.0028 | -0.0002 ±0.0009 | +0.4 | 0.695 | 0.698 | |
| mild disagree (0.05-0.10) | 424 | -0.0027 ±0.0086 | -0.0019 ±0.0033 | -0.3 | 0.647 | 0.672 | |
| big disagree (>=0.1) | 304 | -0.0478 ±0.0221 | -0.0186 ±0.0094 | -2.2 | 0.630 | 0.666 | |
| tour: atp | 686 | +0.0081 ±0.0081 | +0.0030 ±0.0033 | +1.0 | 0.669 | 0.679 | |
| tour: wta | 697 | -0.0294 ±0.0080 | -0.0124 ±0.0033 | -3.7 | 0.663 | 0.687 | |

When they disagree by >= 0.1: model closer to the outcome in **114/304** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 12 | 0.067 | 0.083 |
| 0.1-0.2 | 78 | 0.158 | 0.141 |
| 0.2-0.3 | 127 | 0.252 | 0.220 |
| 0.3-0.4 | 198 | 0.352 | 0.338 |
| 0.4-0.5 | 235 | 0.449 | 0.481 |
| 0.5-0.6 | 227 | 0.550 | 0.573 |
| 0.6-0.7 | 212 | 0.645 | 0.618 |
| 0.7-0.8 | 171 | 0.747 | 0.737 |
| 0.8-0.9 | 97 | 0.844 | 0.835 |
| 0.9-1.0 | 26 | 0.927 | 0.885 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 32 | 0.062 | 0.062 |
| 0.1-0.2 | 82 | 0.152 | 0.122 |
| 0.2-0.3 | 140 | 0.253 | 0.257 |
| 0.3-0.4 | 184 | 0.352 | 0.364 |
| 0.4-0.5 | 204 | 0.442 | 0.436 |
| 0.5-0.6 | 189 | 0.558 | 0.571 |
| 0.6-0.7 | 217 | 0.650 | 0.618 |
| 0.7-0.8 | 172 | 0.746 | 0.744 |
| 0.8-0.9 | 112 | 0.844 | 0.795 |
| 0.9-1.0 | 51 | 0.938 | 0.941 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| both inside top-50 | 284 | +0.0130 ±0.0103 | +0.0058 ±0.0045 | +1.3 | 0.674 | 0.660 | |
| best rank 1-10 | 251 | +0.0120 ±0.0113 | +0.0039 ±0.0035 | +1.1 | 0.753 | 0.749 | |
| tour: atp | 686 | +0.0081 ±0.0081 | +0.0030 ±0.0033 | +1.0 | 0.669 | 0.679 | |
| agree (<0.05) | 655 | +0.0010 ±0.0028 | -0.0002 ±0.0009 | +0.4 | 0.695 | 0.698 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 695 | +0.0022 ±0.0073 | -0.0003 ±0.0029 | +0.3 | 0.669 | 0.690 | |
| tier: masters | 183 | +0.0032 ±0.0114 | +0.0026 ±0.0051 | +0.3 | 0.675 | 0.683 | |
| kalshi favorite 0.8-0.9 | 194 | -0.0008 ±0.0184 | -0.0013 ±0.0066 | -0.0 | 0.830 | 0.830 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| big disagree (>=0.1) | 304 | -0.0478 ±0.0221 | -0.0186 ±0.0094 | -2.2 | 0.630 | 0.666 | |
| best rank 100+ | 79 | -0.0869 ±0.0367 | -0.0389 ±0.0155 | -2.4 | 0.595 | 0.690 | |
| month 2026-06 | 439 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.640 | 0.662 | |
| surface: Grass | 585 | -0.0212 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.681 | |
| kalshi favorite 0.5-0.6 | 391 | -0.0253 ±0.0102 | -0.0114 ±0.0047 | -2.5 | 0.513 | 0.570 | |
| someone outside top-50 | 1099 | -0.0170 ±0.0066 | -0.0075 ±0.0027 | -2.6 | 0.664 | 0.689 | |
| pred_source: live | 521 | -0.0252 ±0.0098 | -0.0095 ±0.0041 | -2.6 | 0.672 | 0.698 | |
| tour: wta | 697 | -0.0294 ±0.0080 | -0.0124 ±0.0033 | -3.7 | 0.663 | 0.687 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1383, mean |Δ|=0.0024, p95=0.0089, >0.05 in 6 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0085 (n=439, >0.05: 0) | 2026-07 p95=0.0079 (n=436, >0.05: 1) | 2026-08 p95=0.3580 (n=9, >0.05: 4)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1383, d_ll -0.0108 ±0.0057 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 397 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'WTA Memphis': 8, 'WTA Washington': 7, 'WTA Iasi': 6, 'WTA Hamburg': 6, 'ATP Hamburg': 1, 'ATP Los Cabos': 1, 'ATP Washington': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Carolyn Ansari, Casper Ruud, Celine Naef, Chloe Paquet, Claire Liu, Clervie Ngounoue, Dalma Galfi, Daphnee Mpetshi Perricard, Daria Kasatkina, Darja Semenistaja
