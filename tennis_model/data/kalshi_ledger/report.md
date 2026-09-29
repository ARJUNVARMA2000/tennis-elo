# Model vs Kalshi — match-by-match scorecard

_Generated 2026-09-29T05:08:03Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1929 | 1824 | 34 | 12 | 59 | 0 | 11 | 19 | 75 | 2026-05-03..2026-09-29 |
| wta | 2031 | 1216 | 56 | 706 | 53 | 0 | 10 | 15 | 30 | 2026-05-02..2026-09-29 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1409 | 0.5970 | 0.5870 | -0.0101 ±0.0052 | -0.0047 ±0.0021 | 0.668 | 0.679 |
| atp | 672 | 0.6160 | 0.6121 | -0.0039 ±0.0071 | -0.0025 ±0.0029 | 0.652 | 0.668 |
| wta | 737 | 0.5797 | 0.5641 | -0.0157 ±0.0075 | -0.0068 ±0.0031 | 0.682 | 0.689 |
| pooled/live_aligned | 479 | 0.5776 | 0.5457 | -0.0319 ±0.0081 | -0.0129 ±0.0034 | 0.689 | 0.707 |
| pooled/backtest | 930 | 0.6071 | 0.6082 | +0.0011 ±0.0066 | -0.0006 ±0.0027 | 0.657 | 0.665 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 479 | -0.0319 ±0.0081 | -0.0129 ±0.0034 | -3.9 | 0.689 | 0.707 | |
| pred_source: backtest | 930 | +0.0011 ±0.0066 | -0.0006 ±0.0027 | +0.2 | 0.657 | 0.665 | |
| top-20 involved | 481 | +0.0055 ±0.0076 | +0.0001 ±0.0026 | +0.7 | 0.731 | 0.731 | |
| no top-20 player | 928 | -0.0181 ±0.0068 | -0.0073 ±0.0029 | -2.7 | 0.635 | 0.652 | |
| both inside top-50 | 327 | -0.0075 ±0.0093 | -0.0038 ±0.0040 | -0.8 | 0.659 | 0.656 | |
| someone outside top-50 | 1082 | -0.0108 ±0.0061 | -0.0050 ±0.0025 | -1.8 | 0.671 | 0.686 | |
| best rank 1-10 | 289 | +0.0205 ±0.0100 | +0.0051 ±0.0030 | +2.1 | 0.744 | 0.737 | |
| best rank 11-20 | 192 | -0.0172 ±0.0117 | -0.0073 ±0.0046 | -1.5 | 0.711 | 0.721 | |
| best rank 21-50 | 488 | -0.0230 ±0.0081 | -0.0095 ±0.0036 | -2.8 | 0.660 | 0.698 | |
| best rank 51-100 | 356 | -0.0096 ±0.0115 | -0.0037 ±0.0049 | -0.8 | 0.611 | 0.603 | |
| best rank 100+ | 84 | -0.0261 ±0.0325 | -0.0098 ±0.0140 | -0.8 | 0.595 | 0.601 | |
| kalshi favorite 0.5-0.6 | 402 | -0.0259 ±0.0090 | -0.0120 ±0.0042 | -2.9 | 0.499 | 0.540 | |
| kalshi favorite 0.6-0.7 | 389 | -0.0047 ±0.0094 | -0.0018 ±0.0043 | -0.5 | 0.625 | 0.625 | |
| kalshi favorite 0.7-0.8 | 327 | -0.0053 ±0.0090 | -0.0022 ±0.0037 | -0.6 | 0.745 | 0.746 | |
| kalshi favorite 0.8-0.9 | 195 | +0.0092 ±0.0165 | +0.0023 ±0.0059 | +0.6 | 0.836 | 0.836 | |
| kalshi favorite 0.9-1.0 | 96 | -0.0212 ±0.0295 | -0.0093 ±0.0080 | -0.7 | 0.948 | 0.938 | |
| surface: Hard | 559 | -0.0219 ±0.0079 | -0.0087 ±0.0033 | -2.8 | 0.678 | 0.686 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 424 | -0.0175 ±0.0106 | -0.0076 ±0.0044 | -1.6 | 0.606 | 0.624 | |
| tier: atp500 | 250 | -0.0149 ±0.0103 | -0.0067 ±0.0046 | -1.4 | 0.628 | 0.642 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| round early (R128-R64) | 549 | -0.0098 ±0.0086 | -0.0045 ±0.0034 | -1.1 | 0.724 | 0.731 | |
| round late (QF-F) | 187 | -0.0130 ±0.0117 | -0.0065 ±0.0052 | -1.1 | 0.636 | 0.647 | |
| round mid (R32-R16) | 651 | -0.0096 ±0.0078 | -0.0045 ±0.0033 | -1.2 | 0.635 | 0.649 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 269 | -0.0357 ±0.0113 | -0.0150 ±0.0047 | -3.2 | 0.729 | 0.755 | |
| agree (<0.05) | 758 | -0.0006 ±0.0026 | -0.0009 ±0.0009 | -0.2 | 0.708 | 0.705 | |
| mild disagree (0.05-0.10) | 421 | -0.0081 ±0.0088 | -0.0038 ±0.0033 | -0.9 | 0.626 | 0.657 | |
| big disagree (>=0.1) | 230 | -0.0450 ±0.0260 | -0.0191 ±0.0111 | -1.7 | 0.611 | 0.635 | |
| tour: atp | 672 | -0.0039 ±0.0071 | -0.0025 ±0.0029 | -0.6 | 0.652 | 0.668 | |
| tour: wta | 737 | -0.0157 ±0.0075 | -0.0068 ±0.0031 | -2.1 | 0.682 | 0.689 | |

When they disagree by >= 0.1: model closer to the outcome in **91/230** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 16 | 0.067 | 0.125 |
| 0.1-0.2 | 87 | 0.153 | 0.138 |
| 0.2-0.3 | 126 | 0.252 | 0.262 |
| 0.3-0.4 | 178 | 0.354 | 0.354 |
| 0.4-0.5 | 246 | 0.452 | 0.472 |
| 0.5-0.6 | 223 | 0.552 | 0.543 |
| 0.6-0.7 | 210 | 0.647 | 0.629 |
| 0.7-0.8 | 172 | 0.751 | 0.767 |
| 0.8-0.9 | 104 | 0.847 | 0.817 |
| 0.9-1.0 | 47 | 0.933 | 0.936 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 37 | 0.059 | 0.081 |
| 0.1-0.2 | 79 | 0.153 | 0.139 |
| 0.2-0.3 | 145 | 0.254 | 0.269 |
| 0.3-0.4 | 174 | 0.355 | 0.379 |
| 0.4-0.5 | 202 | 0.445 | 0.450 |
| 0.5-0.6 | 203 | 0.555 | 0.522 |
| 0.6-0.7 | 212 | 0.649 | 0.637 |
| 0.7-0.8 | 182 | 0.749 | 0.758 |
| 0.8-0.9 | 117 | 0.847 | 0.821 |
| 0.9-1.0 | 58 | 0.935 | 0.948 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 289 | +0.0205 ±0.0100 | +0.0051 ±0.0030 | +2.1 | 0.744 | 0.737 | |
| top-20 involved | 481 | +0.0055 ±0.0076 | +0.0001 ±0.0026 | +0.7 | 0.731 | 0.731 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| kalshi favorite 0.8-0.9 | 195 | +0.0092 ±0.0165 | +0.0023 ±0.0059 | +0.6 | 0.836 | 0.836 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 930 | +0.0011 ±0.0066 | -0.0006 ±0.0027 | +0.2 | 0.657 | 0.665 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| someone outside top-50 | 1082 | -0.0108 ±0.0061 | -0.0050 ±0.0025 | -1.8 | 0.671 | 0.686 | |
| tour: wta | 737 | -0.0157 ±0.0075 | -0.0068 ±0.0031 | -2.1 | 0.682 | 0.689 | |
| no top-20 player | 928 | -0.0181 ±0.0068 | -0.0073 ±0.0029 | -2.7 | 0.635 | 0.652 | |
| surface: Hard | 559 | -0.0219 ±0.0079 | -0.0087 ±0.0033 | -2.8 | 0.678 | 0.686 | |
| best rank 21-50 | 488 | -0.0230 ±0.0081 | -0.0095 ±0.0036 | -2.8 | 0.660 | 0.698 | |
| kalshi favorite 0.5-0.6 | 402 | -0.0259 ±0.0090 | -0.0120 ±0.0042 | -2.9 | 0.499 | 0.540 | |
| month 2026-09 | 269 | -0.0357 ±0.0113 | -0.0150 ±0.0047 | -3.2 | 0.729 | 0.755 | |
| pred_source: live aligned | 479 | -0.0319 ±0.0081 | -0.0129 ±0.0034 | -3.9 | 0.689 | 0.707 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1409, mean |Δ|=0.0034, p95=0.0100, >0.05 in 18 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0633 (n=269, >0.05: 16)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1409, d_ll -0.0101 ±0.0052 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 561 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'WTA Seoul': 3, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): Akasha Urhobo, Aleksandr Shevchenko, Alevtina Ibragimova, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari
