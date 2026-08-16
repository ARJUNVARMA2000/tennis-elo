# Model vs Kalshi — match-by-match scorecard

_Generated 2026-08-16T06:35:17Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1463 | 1393 | 17 | 7 | 46 | 0 | 9 | 15 | 52 | 2026-05-03..2026-08-16 |
| wta | 1475 | 878 | 22 | 537 | 38 | 0 | 5 | 15 | 27 | 2026-05-02..2026-08-16 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1650 | 0.6074 | 0.5972 | -0.0102 ±0.0050 | -0.0044 ±0.0021 | 0.665 | 0.678 |
| atp | 821 | 0.6159 | 0.6203 | +0.0043 ±0.0070 | +0.0013 ±0.0029 | 0.661 | 0.675 |
| wta | 829 | 0.5990 | 0.5743 | -0.0247 ±0.0072 | -0.0101 ±0.0030 | 0.669 | 0.681 |
| pooled/live | 749 | 0.6104 | 0.5892 | -0.0212 ±0.0076 | -0.0080 ±0.0032 | 0.670 | 0.685 |
| pooled/backtest | 901 | 0.6050 | 0.6038 | -0.0011 ±0.0067 | -0.0015 ±0.0027 | 0.661 | 0.672 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live | 749 | -0.0212 ±0.0076 | -0.0080 ±0.0032 | -2.8 | 0.670 | 0.685 | |
| pred_source: backtest | 901 | -0.0011 ±0.0067 | -0.0015 ±0.0027 | -0.2 | 0.661 | 0.672 | |
| top-20 involved | 544 | -0.0020 ±0.0075 | -0.0010 ±0.0027 | -0.3 | 0.744 | 0.739 | |
| no top-20 player | 1106 | -0.0143 ±0.0065 | -0.0062 ±0.0028 | -2.2 | 0.627 | 0.648 | |
| both inside top-50 | 350 | +0.0071 ±0.0090 | +0.0032 ±0.0040 | +0.8 | 0.679 | 0.671 | |
| someone outside top-50 | 1300 | -0.0149 ±0.0059 | -0.0065 ±0.0024 | -2.5 | 0.662 | 0.680 | |
| best rank 1-10 | 296 | +0.0104 ±0.0101 | +0.0032 ±0.0032 | +1.0 | 0.750 | 0.745 | |
| best rank 11-20 | 248 | -0.0167 ±0.0111 | -0.0059 ±0.0045 | -1.5 | 0.736 | 0.732 | |
| best rank 21-50 | 564 | -0.0105 ±0.0076 | -0.0038 ±0.0033 | -1.4 | 0.651 | 0.670 | |
| best rank 51-100 | 459 | -0.0072 ±0.0109 | -0.0038 ±0.0047 | -0.7 | 0.607 | 0.617 | |
| best rank 100+ | 83 | -0.0795 ±0.0352 | -0.0354 ±0.0149 | -2.3 | 0.578 | 0.669 | |
| kalshi favorite 0.5-0.6 | 488 | -0.0231 ±0.0089 | -0.0105 ±0.0041 | -2.6 | 0.534 | 0.571 | |
| kalshi favorite 0.6-0.7 | 488 | -0.0033 ±0.0085 | -0.0012 ±0.0039 | -0.4 | 0.611 | 0.617 | |
| kalshi favorite 0.7-0.8 | 369 | -0.0046 ±0.0095 | -0.0019 ±0.0038 | -0.5 | 0.747 | 0.748 | |
| kalshi favorite 0.8-0.9 | 216 | -0.0028 ±0.0170 | -0.0018 ±0.0060 | -0.2 | 0.829 | 0.829 | |
| kalshi favorite 0.9-1.0 | 89 | -0.0194 ±0.0298 | -0.0060 ±0.0075 | -0.7 | 0.955 | 0.944 | |
| surface: Hard | 368 | -0.0168 ±0.0109 | -0.0074 ±0.0046 | -1.5 | 0.644 | 0.648 | |
| surface: Clay | 696 | +0.0025 ±0.0073 | -0.0001 ±0.0029 | +0.3 | 0.670 | 0.690 | |
| surface: Grass | 586 | -0.0213 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.682 | |
| tier: atp250 | 680 | -0.0088 ±0.0082 | -0.0047 ±0.0035 | -1.1 | 0.638 | 0.665 | |
| tier: atp500 | 187 | -0.0151 ±0.0103 | -0.0072 ±0.0046 | -1.5 | 0.610 | 0.623 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 476 | -0.0187 ±0.0107 | -0.0074 ±0.0042 | -1.8 | 0.711 | 0.720 | |
| tier: masters | 306 | +0.0021 ±0.0093 | +0.0022 ±0.0041 | +0.2 | 0.688 | 0.675 | |
| round early (R128-R64) | 657 | -0.0167 ±0.0084 | -0.0062 ±0.0034 | -2.0 | 0.696 | 0.695 | |
| round late (QF-F) | 221 | -0.0079 ±0.0106 | -0.0044 ±0.0046 | -0.7 | 0.633 | 0.649 | |
| round mid (R32-R16) | 750 | -0.0054 ±0.0076 | -0.0030 ±0.0032 | -0.7 | 0.653 | 0.675 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 440 | -0.0249 ±0.0103 | -0.0106 ±0.0044 | -2.4 | 0.641 | 0.662 | |
| month 2026-07 | 438 | -0.0076 ±0.0105 | -0.0018 ±0.0044 | -0.7 | 0.683 | 0.696 | |
| month 2026-08 | 273 | -0.0150 ±0.0098 | -0.0065 ±0.0043 | -1.5 | 0.656 | 0.654 | |
| agree (<0.05) | 798 | +0.0007 ±0.0025 | -0.0002 ±0.0009 | +0.3 | 0.695 | 0.697 | |
| mild disagree (0.05-0.10) | 506 | -0.0028 ±0.0078 | -0.0016 ±0.0030 | -0.4 | 0.653 | 0.664 | |
| big disagree (>=0.1) | 346 | -0.0464 ±0.0202 | -0.0184 ±0.0087 | -2.3 | 0.614 | 0.653 | |
| tour: atp | 821 | +0.0043 ±0.0070 | +0.0013 ±0.0029 | +0.6 | 0.661 | 0.675 | |
| tour: wta | 829 | -0.0247 ±0.0072 | -0.0101 ±0.0030 | -3.5 | 0.669 | 0.681 | |

When they disagree by >= 0.1: model closer to the outcome in **134/346** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 13 | 0.066 | 0.077 |
| 0.1-0.2 | 87 | 0.158 | 0.149 |
| 0.2-0.3 | 152 | 0.252 | 0.237 |
| 0.3-0.4 | 239 | 0.351 | 0.343 |
| 0.4-0.5 | 284 | 0.451 | 0.461 |
| 0.5-0.6 | 264 | 0.549 | 0.576 |
| 0.6-0.7 | 256 | 0.645 | 0.609 |
| 0.7-0.8 | 205 | 0.746 | 0.741 |
| 0.8-0.9 | 117 | 0.844 | 0.829 |
| 0.9-1.0 | 33 | 0.926 | 0.879 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 33 | 0.062 | 0.061 |
| 0.1-0.2 | 88 | 0.152 | 0.114 |
| 0.2-0.3 | 167 | 0.255 | 0.269 |
| 0.3-0.4 | 224 | 0.353 | 0.375 |
| 0.4-0.5 | 244 | 0.443 | 0.418 |
| 0.5-0.6 | 247 | 0.557 | 0.559 |
| 0.6-0.7 | 261 | 0.649 | 0.613 |
| 0.7-0.8 | 202 | 0.746 | 0.762 |
| 0.8-0.9 | 128 | 0.846 | 0.789 |
| 0.9-1.0 | 56 | 0.937 | 0.946 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 296 | +0.0104 ±0.0101 | +0.0032 ±0.0032 | +1.0 | 0.750 | 0.745 | |
| both inside top-50 | 350 | +0.0071 ±0.0090 | +0.0032 ±0.0040 | +0.8 | 0.679 | 0.671 | |
| tour: atp | 821 | +0.0043 ±0.0070 | +0.0013 ±0.0029 | +0.6 | 0.661 | 0.675 | |
| surface: Clay | 696 | +0.0025 ±0.0073 | -0.0001 ±0.0029 | +0.3 | 0.670 | 0.690 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| agree (<0.05) | 798 | +0.0007 ±0.0025 | -0.0002 ±0.0009 | +0.3 | 0.695 | 0.697 | |
| tier: masters | 306 | +0.0021 ±0.0093 | +0.0022 ±0.0041 | +0.2 | 0.688 | 0.675 | |
| kalshi favorite 0.8-0.9 | 216 | -0.0028 ±0.0170 | -0.0018 ±0.0060 | -0.2 | 0.829 | 0.829 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 100+ | 83 | -0.0795 ±0.0352 | -0.0354 ±0.0149 | -2.3 | 0.578 | 0.669 | |
| big disagree (>=0.1) | 346 | -0.0464 ±0.0202 | -0.0184 ±0.0087 | -2.3 | 0.614 | 0.653 | |
| surface: Grass | 586 | -0.0213 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.682 | |
| month 2026-06 | 440 | -0.0249 ±0.0103 | -0.0106 ±0.0044 | -2.4 | 0.641 | 0.662 | |
| someone outside top-50 | 1300 | -0.0149 ±0.0059 | -0.0065 ±0.0024 | -2.5 | 0.662 | 0.680 | |
| kalshi favorite 0.5-0.6 | 488 | -0.0231 ±0.0089 | -0.0105 ±0.0041 | -2.6 | 0.534 | 0.571 | |
| pred_source: live | 749 | -0.0212 ±0.0076 | -0.0080 ±0.0032 | -2.8 | 0.670 | 0.685 | |
| tour: wta | 829 | -0.0247 ±0.0072 | -0.0101 ±0.0030 | -3.5 | 0.669 | 0.681 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1650, mean |Δ|=0.0025, p95=0.0091, >0.05 in 7 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0085 (n=440, >0.05: 0) | 2026-07 p95=0.0079 (n=438, >0.05: 1) | 2026-08 p95=0.0133 (n=273, >0.05: 5)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1650, d_ll -0.0102 ±0.0050 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 447 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Cincinnati': 1, 'ATP Mallorca': 1, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Alexandra Eala, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Carolyn Ansari, Casper Ruud, Caty McNally, Celine Naef, Chloe Paquet, Claire Liu, Clervie Ngounoue, Dalma Galfi, Daphnee Mpetshi Perricard
