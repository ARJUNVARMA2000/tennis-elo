# Model vs Kalshi — match-by-match scorecard

_Generated 2026-10-10T08:00:29Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 2079 | 1982 | 21 | 14 | 62 | 0 | 12 | 22 | 51 | 2026-05-03..2026-10-11 |
| wta | 2128 | 1307 | 22 | 743 | 56 | 0 | 10 | 15 | 36 | 2026-05-02..2026-10-11 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1549 | 0.6030 | 0.5863 | -0.0167 ±0.0052 | -0.0071 ±0.0021 | 0.666 | 0.679 |
| atp | 749 | 0.6185 | 0.6075 | -0.0111 ±0.0073 | -0.0048 ±0.0029 | 0.653 | 0.668 |
| wta | 800 | 0.5885 | 0.5665 | -0.0220 ±0.0075 | -0.0093 ±0.0031 | 0.677 | 0.690 |
| pooled/live_aligned | 615 | 0.5993 | 0.5560 | -0.0433 ±0.0085 | -0.0170 ±0.0035 | 0.676 | 0.699 |
| pooled/backtest | 934 | 0.6055 | 0.6062 | +0.0008 ±0.0066 | -0.0007 ±0.0027 | 0.658 | 0.666 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 615 | -0.0433 ±0.0085 | -0.0170 ±0.0035 | -5.1 | 0.676 | 0.699 | |
| pred_source: backtest | 934 | +0.0008 ±0.0066 | -0.0007 ±0.0027 | +0.1 | 0.658 | 0.666 | |
| top-20 involved | 543 | -0.0006 ±0.0083 | -0.0021 ±0.0030 | -0.1 | 0.728 | 0.732 | |
| no top-20 player | 1006 | -0.0254 ±0.0067 | -0.0099 ±0.0028 | -3.8 | 0.632 | 0.651 | |
| both inside top-50 | 380 | -0.0184 ±0.0107 | -0.0082 ±0.0046 | -1.7 | 0.654 | 0.662 | |
| someone outside top-50 | 1169 | -0.0162 ±0.0060 | -0.0068 ±0.0024 | -2.7 | 0.669 | 0.685 | |
| best rank 1-10 | 326 | +0.0142 ±0.0104 | +0.0029 ±0.0035 | +1.4 | 0.745 | 0.742 | |
| best rank 11-20 | 217 | -0.0228 ±0.0136 | -0.0096 ±0.0054 | -1.7 | 0.703 | 0.717 | |
| best rank 21-50 | 532 | -0.0293 ±0.0082 | -0.0118 ±0.0035 | -3.6 | 0.658 | 0.699 | |
| best rank 51-100 | 386 | -0.0177 ±0.0112 | -0.0066 ±0.0047 | -1.6 | 0.602 | 0.595 | |
| best rank 100+ | 88 | -0.0357 ±0.0320 | -0.0128 ±0.0136 | -1.1 | 0.602 | 0.608 | |
| kalshi favorite 0.5-0.6 | 441 | -0.0252 ±0.0086 | -0.0116 ±0.0040 | -2.9 | 0.502 | 0.539 | |
| kalshi favorite 0.6-0.7 | 428 | -0.0121 ±0.0093 | -0.0046 ±0.0041 | -1.3 | 0.619 | 0.621 | |
| kalshi favorite 0.7-0.8 | 357 | -0.0091 ±0.0097 | -0.0037 ±0.0039 | -0.9 | 0.744 | 0.751 | |
| kalshi favorite 0.8-0.9 | 214 | -0.0012 ±0.0162 | -0.0011 ±0.0057 | -0.1 | 0.832 | 0.836 | |
| kalshi favorite 0.9-1.0 | 109 | -0.0562 ±0.0313 | -0.0219 ±0.0099 | -1.8 | 0.927 | 0.936 | |
| surface: Hard | 699 | -0.0343 ±0.0081 | -0.0132 ±0.0033 | -4.2 | 0.671 | 0.685 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 501 | -0.0260 ±0.0105 | -0.0103 ±0.0043 | -2.5 | 0.615 | 0.631 | |
| tier: atp500 | 250 | -0.0149 ±0.0103 | -0.0067 ±0.0046 | -1.4 | 0.628 | 0.642 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 287 | -0.0159 ±0.0112 | -0.0056 ±0.0048 | -1.4 | 0.667 | 0.683 | |
| round early (R128-R64) | 622 | -0.0224 ±0.0085 | -0.0090 ±0.0033 | -2.6 | 0.711 | 0.723 | |
| round late (QF-F) | 204 | -0.0075 ±0.0113 | -0.0042 ±0.0050 | -0.7 | 0.637 | 0.647 | |
| round mid (R32-R16) | 701 | -0.0147 ±0.0081 | -0.0065 ±0.0034 | -1.8 | 0.638 | 0.654 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 319 | -0.0405 ±0.0103 | -0.0168 ±0.0043 | -3.9 | 0.705 | 0.730 | |
| month 2026-10 | 90 | -0.0932 ±0.0358 | -0.0343 ±0.0141 | -2.6 | 0.678 | 0.728 | |
| agree (<0.05) | 838 | +0.0007 ±0.0024 | -0.0003 ±0.0008 | +0.3 | 0.710 | 0.706 | |
| mild disagree (0.05-0.10) | 456 | -0.0091 ±0.0084 | -0.0040 ±0.0032 | -1.1 | 0.630 | 0.655 | |
| big disagree (>=0.1) | 255 | -0.0875 ±0.0265 | -0.0352 ±0.0111 | -3.3 | 0.582 | 0.635 | |
| tour: atp | 749 | -0.0111 ±0.0073 | -0.0048 ±0.0029 | -1.5 | 0.653 | 0.668 | |
| tour: wta | 800 | -0.0220 ±0.0075 | -0.0093 ±0.0031 | -3.0 | 0.677 | 0.690 | |

When they disagree by >= 0.1: model closer to the outcome in **95/255** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 17 | 0.066 | 0.176 |
| 0.1-0.2 | 93 | 0.153 | 0.151 |
| 0.2-0.3 | 140 | 0.251 | 0.264 |
| 0.3-0.4 | 197 | 0.353 | 0.360 |
| 0.4-0.5 | 265 | 0.452 | 0.464 |
| 0.5-0.6 | 243 | 0.552 | 0.539 |
| 0.6-0.7 | 229 | 0.647 | 0.620 |
| 0.7-0.8 | 190 | 0.751 | 0.774 |
| 0.8-0.9 | 121 | 0.846 | 0.802 |
| 0.9-1.0 | 54 | 0.931 | 0.926 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 43 | 0.058 | 0.093 |
| 0.1-0.2 | 85 | 0.154 | 0.153 |
| 0.2-0.3 | 159 | 0.255 | 0.258 |
| 0.3-0.4 | 191 | 0.354 | 0.382 |
| 0.4-0.5 | 225 | 0.445 | 0.453 |
| 0.5-0.6 | 220 | 0.555 | 0.523 |
| 0.6-0.7 | 233 | 0.650 | 0.631 |
| 0.7-0.8 | 198 | 0.749 | 0.758 |
| 0.8-0.9 | 130 | 0.846 | 0.831 |
| 0.9-1.0 | 65 | 0.935 | 0.954 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 326 | +0.0142 ±0.0104 | +0.0029 ±0.0035 | +1.4 | 0.745 | 0.742 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| agree (<0.05) | 838 | +0.0007 ±0.0024 | -0.0003 ±0.0008 | +0.3 | 0.710 | 0.706 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 934 | +0.0008 ±0.0066 | -0.0007 ±0.0027 | +0.1 | 0.658 | 0.666 | |
| top-20 involved | 543 | -0.0006 ±0.0083 | -0.0021 ±0.0030 | -0.1 | 0.728 | 0.732 | |
| kalshi favorite 0.8-0.9 | 214 | -0.0012 ±0.0162 | -0.0011 ±0.0057 | -0.1 | 0.832 | 0.836 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| kalshi favorite 0.5-0.6 | 441 | -0.0252 ±0.0086 | -0.0116 ±0.0040 | -2.9 | 0.502 | 0.539 | |
| tour: wta | 800 | -0.0220 ±0.0075 | -0.0093 ±0.0031 | -3.0 | 0.677 | 0.690 | |
| big disagree (>=0.1) | 255 | -0.0875 ±0.0265 | -0.0352 ±0.0111 | -3.3 | 0.582 | 0.635 | |
| best rank 21-50 | 532 | -0.0293 ±0.0082 | -0.0118 ±0.0035 | -3.6 | 0.658 | 0.699 | |
| no top-20 player | 1006 | -0.0254 ±0.0067 | -0.0099 ±0.0028 | -3.8 | 0.632 | 0.651 | |
| month 2026-09 | 319 | -0.0405 ±0.0103 | -0.0168 ±0.0043 | -3.9 | 0.705 | 0.730 | |
| surface: Hard | 699 | -0.0343 ±0.0081 | -0.0132 ±0.0033 | -4.2 | 0.671 | 0.685 | |
| pred_source: live aligned | 615 | -0.0433 ±0.0085 | -0.0170 ±0.0035 | -5.1 | 0.676 | 0.699 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1549, mean |Δ|=0.0052, p95=0.0100, >0.05 in 30 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0666 (n=319, >0.05: 19) | 2026-10 p95=0.1830 (n=90, >0.05: 9)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1549, d_ll -0.0167 ±0.0052 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 598 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'WTA Seoul': 3, 'ATP Cincinnati': 1}
- Unmatched Kalshi names, main draw (40): Akasha Urhobo, Aleksandr Shevchenko, Alevtina Ibragimova, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari
