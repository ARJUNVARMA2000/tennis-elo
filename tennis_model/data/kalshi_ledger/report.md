# Model vs Kalshi — match-by-match scorecard

_Generated 2026-10-09T09:59:23Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 2072 | 1971 | 26 | 13 | 62 | 0 | 12 | 22 | 53 | 2026-05-03..2026-10-10 |
| wta | 2123 | 1306 | 18 | 743 | 56 | 0 | 10 | 15 | 46 | 2026-05-02..2026-10-10 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1541 | 0.6011 | 0.5851 | -0.0160 ±0.0052 | -0.0069 ±0.0021 | 0.666 | 0.680 |
| atp | 742 | 0.6159 | 0.6066 | -0.0093 ±0.0073 | -0.0044 ±0.0029 | 0.652 | 0.668 |
| wta | 799 | 0.5873 | 0.5651 | -0.0221 ±0.0075 | -0.0093 ±0.0031 | 0.678 | 0.691 |
| pooled/live_aligned | 607 | 0.5943 | 0.5526 | -0.0417 ±0.0084 | -0.0166 ±0.0035 | 0.677 | 0.700 |
| pooled/backtest | 934 | 0.6055 | 0.6062 | +0.0008 ±0.0066 | -0.0007 ±0.0027 | 0.658 | 0.666 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 607 | -0.0417 ±0.0084 | -0.0166 ±0.0035 | -5.0 | 0.677 | 0.700 | |
| pred_source: backtest | 934 | +0.0008 ±0.0066 | -0.0007 ±0.0027 | +0.1 | 0.658 | 0.666 | |
| top-20 involved | 538 | -0.0001 ±0.0084 | -0.0018 ±0.0030 | -0.0 | 0.730 | 0.733 | |
| no top-20 player | 1003 | -0.0245 ±0.0066 | -0.0097 ±0.0028 | -3.7 | 0.632 | 0.651 | |
| both inside top-50 | 377 | -0.0174 ±0.0108 | -0.0078 ±0.0046 | -1.6 | 0.656 | 0.664 | |
| someone outside top-50 | 1164 | -0.0155 ±0.0060 | -0.0067 ±0.0024 | -2.6 | 0.669 | 0.685 | |
| best rank 1-10 | 325 | +0.0141 ±0.0105 | +0.0029 ±0.0035 | +1.3 | 0.748 | 0.745 | |
| best rank 11-20 | 213 | -0.0216 ±0.0137 | -0.0090 ±0.0055 | -1.6 | 0.702 | 0.716 | |
| best rank 21-50 | 529 | -0.0275 ±0.0080 | -0.0115 ±0.0035 | -3.4 | 0.658 | 0.699 | |
| best rank 51-100 | 386 | -0.0177 ±0.0112 | -0.0066 ±0.0047 | -1.6 | 0.602 | 0.595 | |
| best rank 100+ | 88 | -0.0357 ±0.0320 | -0.0128 ±0.0136 | -1.1 | 0.602 | 0.608 | |
| kalshi favorite 0.5-0.6 | 440 | -0.0254 ±0.0086 | -0.0117 ±0.0040 | -2.9 | 0.501 | 0.537 | |
| kalshi favorite 0.6-0.7 | 424 | -0.0108 ±0.0093 | -0.0041 ±0.0042 | -1.2 | 0.618 | 0.620 | |
| kalshi favorite 0.7-0.8 | 356 | -0.0094 ±0.0097 | -0.0039 ±0.0039 | -1.0 | 0.743 | 0.750 | |
| kalshi favorite 0.8-0.9 | 212 | +0.0031 ±0.0157 | -0.0003 ±0.0057 | +0.2 | 0.840 | 0.844 | |
| kalshi favorite 0.9-1.0 | 109 | -0.0562 ±0.0313 | -0.0219 ±0.0099 | -1.8 | 0.927 | 0.936 | |
| surface: Hard | 691 | -0.0327 ±0.0080 | -0.0128 ±0.0033 | -4.1 | 0.671 | 0.686 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 494 | -0.0236 ±0.0104 | -0.0096 ±0.0043 | -2.3 | 0.613 | 0.630 | |
| tier: atp500 | 250 | -0.0149 ±0.0103 | -0.0067 ±0.0046 | -1.4 | 0.628 | 0.642 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 286 | -0.0161 ±0.0113 | -0.0057 ±0.0048 | -1.4 | 0.670 | 0.685 | |
| round early (R128-R64) | 615 | -0.0204 ±0.0084 | -0.0085 ±0.0033 | -2.4 | 0.711 | 0.724 | |
| round late (QF-F) | 203 | -0.0078 ±0.0113 | -0.0043 ±0.0050 | -0.7 | 0.640 | 0.650 | |
| round mid (R32-R16) | 701 | -0.0147 ±0.0081 | -0.0065 ±0.0034 | -1.8 | 0.638 | 0.654 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 319 | -0.0405 ±0.0103 | -0.0168 ±0.0043 | -3.9 | 0.705 | 0.730 | |
| month 2026-10 | 82 | -0.0862 ±0.0373 | -0.0333 ±0.0152 | -2.3 | 0.683 | 0.738 | |
| agree (<0.05) | 834 | +0.0006 ±0.0024 | -0.0003 ±0.0008 | +0.2 | 0.710 | 0.706 | |
| mild disagree (0.05-0.10) | 454 | -0.0092 ±0.0084 | -0.0040 ±0.0032 | -1.1 | 0.629 | 0.653 | |
| big disagree (>=0.1) | 253 | -0.0827 ±0.0265 | -0.0340 ±0.0112 | -3.1 | 0.587 | 0.640 | |
| tour: atp | 742 | -0.0093 ±0.0073 | -0.0044 ±0.0029 | -1.3 | 0.652 | 0.668 | |
| tour: wta | 799 | -0.0221 ±0.0075 | -0.0093 ±0.0031 | -3.0 | 0.678 | 0.691 | |

When they disagree by >= 0.1: model closer to the outcome in **95/253** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 17 | 0.066 | 0.176 |
| 0.1-0.2 | 93 | 0.153 | 0.151 |
| 0.2-0.3 | 138 | 0.251 | 0.254 |
| 0.3-0.4 | 196 | 0.353 | 0.362 |
| 0.4-0.5 | 265 | 0.452 | 0.464 |
| 0.5-0.6 | 241 | 0.552 | 0.535 |
| 0.6-0.7 | 228 | 0.647 | 0.618 |
| 0.7-0.8 | 190 | 0.751 | 0.774 |
| 0.8-0.9 | 120 | 0.846 | 0.800 |
| 0.9-1.0 | 53 | 0.931 | 0.943 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 43 | 0.058 | 0.093 |
| 0.1-0.2 | 84 | 0.154 | 0.143 |
| 0.2-0.3 | 159 | 0.255 | 0.258 |
| 0.3-0.4 | 189 | 0.354 | 0.381 |
| 0.4-0.5 | 225 | 0.445 | 0.453 |
| 0.5-0.6 | 219 | 0.556 | 0.521 |
| 0.6-0.7 | 231 | 0.650 | 0.628 |
| 0.7-0.8 | 197 | 0.749 | 0.756 |
| 0.8-0.9 | 129 | 0.846 | 0.837 |
| 0.9-1.0 | 65 | 0.935 | 0.954 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 325 | +0.0141 ±0.0105 | +0.0029 ±0.0035 | +1.3 | 0.748 | 0.745 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| agree (<0.05) | 834 | +0.0006 ±0.0024 | -0.0003 ±0.0008 | +0.2 | 0.710 | 0.706 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| kalshi favorite 0.8-0.9 | 212 | +0.0031 ±0.0157 | -0.0003 ±0.0057 | +0.2 | 0.840 | 0.844 | |
| pred_source: backtest | 934 | +0.0008 ±0.0066 | -0.0007 ±0.0027 | +0.1 | 0.658 | 0.666 | |
| top-20 involved | 538 | -0.0001 ±0.0084 | -0.0018 ±0.0030 | -0.0 | 0.730 | 0.733 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| kalshi favorite 0.5-0.6 | 440 | -0.0254 ±0.0086 | -0.0117 ±0.0040 | -2.9 | 0.501 | 0.537 | |
| tour: wta | 799 | -0.0221 ±0.0075 | -0.0093 ±0.0031 | -3.0 | 0.678 | 0.691 | |
| big disagree (>=0.1) | 253 | -0.0827 ±0.0265 | -0.0340 ±0.0112 | -3.1 | 0.587 | 0.640 | |
| best rank 21-50 | 529 | -0.0275 ±0.0080 | -0.0115 ±0.0035 | -3.4 | 0.658 | 0.699 | |
| no top-20 player | 1003 | -0.0245 ±0.0066 | -0.0097 ±0.0028 | -3.7 | 0.632 | 0.651 | |
| month 2026-09 | 319 | -0.0405 ±0.0103 | -0.0168 ±0.0043 | -3.9 | 0.705 | 0.730 | |
| surface: Hard | 691 | -0.0327 ±0.0080 | -0.0128 ±0.0033 | -4.1 | 0.671 | 0.686 | |
| pred_source: live aligned | 607 | -0.0417 ±0.0084 | -0.0166 ±0.0035 | -5.0 | 0.677 | 0.700 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1541, mean |Δ|=0.0053, p95=0.0100, >0.05 in 30 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0666 (n=319, >0.05: 19) | 2026-10 p95=0.2070 (n=82, >0.05: 9)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1541, d_ll -0.0160 ±0.0052 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 598 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'WTA Seoul': 3, 'ATP Chengdu': 1}
- Unmatched Kalshi names, main draw (40): Akasha Urhobo, Aleksandr Shevchenko, Alevtina Ibragimova, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari
