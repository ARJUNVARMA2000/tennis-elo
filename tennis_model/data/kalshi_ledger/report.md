# Model vs Kalshi — match-by-match scorecard

_Generated 2026-08-01T06:59:02Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1278 | 1194 | 35 | 7 | 42 | 0 | 8 | 14 | 71 | 2026-05-03..2026-08-02 |
| wta | 1273 | 732 | 22 | 487 | 32 | 0 | 3 | 15 | 34 | 2026-05-02..2026-08-01 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1376 | 0.6033 | 0.5934 | -0.0099 ±0.0057 | -0.0043 ±0.0023 | 0.666 | 0.682 |
| atp | 683 | 0.6062 | 0.6150 | +0.0087 ±0.0081 | +0.0033 ±0.0033 | 0.668 | 0.678 |
| wta | 693 | 0.6005 | 0.5723 | -0.0282 ±0.0080 | -0.0118 ±0.0033 | 0.665 | 0.687 |
| pooled/live | 514 | 0.6055 | 0.5826 | -0.0229 ±0.0099 | -0.0084 ±0.0042 | 0.673 | 0.696 |
| pooled/backtest | 862 | 0.6021 | 0.5999 | -0.0022 ±0.0069 | -0.0019 ±0.0028 | 0.662 | 0.675 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live | 514 | -0.0229 ±0.0099 | -0.0084 ±0.0042 | -2.3 | 0.673 | 0.696 | |
| pred_source: backtest | 862 | -0.0022 ±0.0069 | -0.0019 ±0.0028 | -0.3 | 0.662 | 0.675 | |
| top-20 involved | 447 | -0.0004 ±0.0085 | -0.0005 ±0.0030 | -0.0 | 0.742 | 0.737 | |
| no top-20 player | 929 | -0.0145 ±0.0074 | -0.0062 ±0.0032 | -2.0 | 0.630 | 0.656 | |
| both inside top-50 | 280 | +0.0149 ±0.0104 | +0.0066 ±0.0045 | +1.4 | 0.673 | 0.659 | |
| someone outside top-50 | 1096 | -0.0162 ±0.0066 | -0.0071 ±0.0027 | -2.4 | 0.665 | 0.688 | |
| best rank 1-10 | 249 | +0.0124 ±0.0114 | +0.0041 ±0.0035 | +1.1 | 0.751 | 0.747 | |
| best rank 11-20 | 198 | -0.0164 ±0.0128 | -0.0062 ±0.0052 | -1.3 | 0.730 | 0.725 | |
| best rank 21-50 | 471 | -0.0075 ±0.0085 | -0.0021 ±0.0037 | -0.9 | 0.652 | 0.667 | |
| best rank 51-100 | 380 | -0.0087 ±0.0125 | -0.0048 ±0.0053 | -0.7 | 0.609 | 0.637 | |
| best rank 100+ | 78 | -0.0845 ±0.0371 | -0.0376 ±0.0157 | -2.3 | 0.603 | 0.686 | |
| kalshi favorite 0.5-0.6 | 390 | -0.0247 ±0.0102 | -0.0111 ±0.0047 | -2.4 | 0.514 | 0.569 | |
| kalshi favorite 0.6-0.7 | 400 | -0.0043 ±0.0096 | -0.0017 ±0.0044 | -0.4 | 0.620 | 0.623 | |
| kalshi favorite 0.7-0.8 | 309 | -0.0015 ±0.0108 | -0.0006 ±0.0044 | -0.1 | 0.739 | 0.741 | |
| kalshi favorite 0.8-0.9 | 194 | -0.0008 ±0.0184 | -0.0013 ±0.0066 | -0.0 | 0.830 | 0.830 | |
| kalshi favorite 0.9-1.0 | 83 | -0.0198 ±0.0320 | -0.0063 ±0.0081 | -0.6 | 0.952 | 0.940 | |
| surface: Hard | 96 | -0.0289 ±0.0316 | -0.0134 ±0.0127 | -0.9 | 0.604 | 0.635 | |
| surface: Clay | 695 | +0.0022 ±0.0073 | -0.0003 ±0.0029 | +0.3 | 0.669 | 0.690 | |
| surface: Grass | 585 | -0.0212 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.681 | |
| tier: atp250 | 533 | -0.0052 ±0.0099 | -0.0031 ±0.0041 | -0.5 | 0.642 | 0.668 | |
| tier: atp500 | 184 | -0.0139 ±0.0102 | -0.0067 ±0.0046 | -1.4 | 0.614 | 0.628 | |
| tier: grand_slam | 476 | -0.0187 ±0.0107 | -0.0074 ±0.0042 | -1.8 | 0.711 | 0.720 | |
| tier: masters | 183 | +0.0032 ±0.0114 | +0.0026 ±0.0051 | +0.3 | 0.675 | 0.683 | |
| round early (R128-R64) | 509 | -0.0196 ±0.0101 | -0.0072 ±0.0040 | -1.9 | 0.712 | 0.722 | |
| round late (QF-F) | 186 | -0.0031 ±0.0114 | -0.0026 ±0.0049 | -0.3 | 0.624 | 0.634 | |
| round mid (R32-R16) | 659 | -0.0045 ±0.0084 | -0.0026 ±0.0035 | -0.5 | 0.649 | 0.670 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 439 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.640 | 0.662 | |
| month 2026-07 | 436 | -0.0086 ±0.0105 | -0.0023 ±0.0044 | -0.8 | 0.683 | 0.697 | |
| month 2026-08 | 2 | -0.2558 ±0.1379 | -0.1211 ±0.0728 | -1.9 | 0.000 | 0.500 | ⚠ small n |
| agree (<0.05) | 653 | +0.0011 ±0.0028 | -0.0001 ±0.0009 | +0.4 | 0.694 | 0.698 | |
| mild disagree (0.05-0.10) | 423 | -0.0025 ±0.0086 | -0.0018 ±0.0033 | -0.3 | 0.647 | 0.671 | |
| big disagree (>=0.1) | 300 | -0.0443 ±0.0223 | -0.0170 ±0.0095 | -2.0 | 0.635 | 0.665 | |
| tour: atp | 683 | +0.0087 ±0.0081 | +0.0033 ±0.0033 | +1.1 | 0.668 | 0.678 | |
| tour: wta | 693 | -0.0282 ±0.0080 | -0.0118 ±0.0033 | -3.5 | 0.665 | 0.687 | |

When they disagree by >= 0.1: model closer to the outcome in **114/300** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 12 | 0.067 | 0.083 |
| 0.1-0.2 | 78 | 0.158 | 0.141 |
| 0.2-0.3 | 125 | 0.251 | 0.216 |
| 0.3-0.4 | 196 | 0.352 | 0.342 |
| 0.4-0.5 | 233 | 0.449 | 0.481 |
| 0.5-0.6 | 226 | 0.550 | 0.575 |
| 0.6-0.7 | 212 | 0.645 | 0.618 |
| 0.7-0.8 | 171 | 0.747 | 0.737 |
| 0.8-0.9 | 97 | 0.844 | 0.835 |
| 0.9-1.0 | 26 | 0.927 | 0.885 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 32 | 0.062 | 0.062 |
| 0.1-0.2 | 82 | 0.152 | 0.122 |
| 0.2-0.3 | 137 | 0.253 | 0.263 |
| 0.3-0.4 | 181 | 0.352 | 0.365 |
| 0.4-0.5 | 204 | 0.442 | 0.436 |
| 0.5-0.6 | 188 | 0.558 | 0.569 |
| 0.6-0.7 | 217 | 0.650 | 0.618 |
| 0.7-0.8 | 172 | 0.746 | 0.744 |
| 0.8-0.9 | 112 | 0.844 | 0.795 |
| 0.9-1.0 | 51 | 0.938 | 0.941 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| both inside top-50 | 280 | +0.0149 ±0.0104 | +0.0066 ±0.0045 | +1.4 | 0.673 | 0.659 | |
| best rank 1-10 | 249 | +0.0124 ±0.0114 | +0.0041 ±0.0035 | +1.1 | 0.751 | 0.747 | |
| tour: atp | 683 | +0.0087 ±0.0081 | +0.0033 ±0.0033 | +1.1 | 0.668 | 0.678 | |
| agree (<0.05) | 653 | +0.0011 ±0.0028 | -0.0001 ±0.0009 | +0.4 | 0.694 | 0.698 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 695 | +0.0022 ±0.0073 | -0.0003 ±0.0029 | +0.3 | 0.669 | 0.690 | |
| tier: masters | 183 | +0.0032 ±0.0114 | +0.0026 ±0.0051 | +0.3 | 0.675 | 0.683 | |
| kalshi favorite 0.8-0.9 | 194 | -0.0008 ±0.0184 | -0.0013 ±0.0066 | -0.0 | 0.830 | 0.830 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| big disagree (>=0.1) | 300 | -0.0443 ±0.0223 | -0.0170 ±0.0095 | -2.0 | 0.635 | 0.665 | |
| best rank 100+ | 78 | -0.0845 ±0.0371 | -0.0376 ±0.0157 | -2.3 | 0.603 | 0.686 | |
| pred_source: live | 514 | -0.0229 ±0.0099 | -0.0084 ±0.0042 | -2.3 | 0.673 | 0.696 | |
| month 2026-06 | 439 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.640 | 0.662 | |
| surface: Grass | 585 | -0.0212 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.681 | |
| kalshi favorite 0.5-0.6 | 390 | -0.0247 ±0.0102 | -0.0111 ±0.0047 | -2.4 | 0.514 | 0.569 | |
| someone outside top-50 | 1096 | -0.0162 ±0.0066 | -0.0071 ±0.0027 | -2.4 | 0.665 | 0.688 | |
| tour: wta | 693 | -0.0282 ±0.0080 | -0.0118 ±0.0033 | -3.5 | 0.665 | 0.687 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1376, mean |Δ|=0.0020, p95=0.0086, >0.05 in 4 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0085 (n=439, >0.05: 0) | 2026-07 p95=0.0079 (n=436, >0.05: 1) | 2026-08 p95=0.2342 (n=2, >0.05: 2)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1376, d_ll -0.0099 ±0.0057 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 397 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'WTA Memphis': 8, 'WTA Washington': 7, 'WTA Iasi': 6, 'WTA Hamburg': 6, 'ATP Hamburg': 1, 'ATP Los Cabos': 1, 'ATP Washington': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Carolyn Ansari, Casper Ruud, Celine Naef, Chloe Paquet, Claire Liu, Clervie Ngounoue, Dalma Galfi, Daphnee Mpetshi Perricard, Daria Kasatkina, Darja Semenistaja
