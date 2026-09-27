# Model vs Kalshi — match-by-match scorecard

_Generated 2026-09-27T15:30:02Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1892 | 1798 | 21 | 15 | 58 | 0 | 11 | 19 | 61 | 2026-05-03..2026-09-28 |
| wta | 1998 | 1204 | 35 | 707 | 52 | 0 | 10 | 15 | 43 | 2026-05-02..2026-09-28 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1399 | 0.5980 | 0.5874 | -0.0106 ±0.0052 | -0.0050 ±0.0021 | 0.668 | 0.679 |
| atp | 662 | 0.6183 | 0.6134 | -0.0049 ±0.0072 | -0.0030 ±0.0029 | 0.651 | 0.668 |
| wta | 737 | 0.5797 | 0.5641 | -0.0157 ±0.0075 | -0.0068 ±0.0031 | 0.682 | 0.689 |
| pooled/live_aligned | 474 | 0.5802 | 0.5476 | -0.0326 ±0.0082 | -0.0132 ±0.0034 | 0.686 | 0.704 |
| pooled/backtest | 925 | 0.6071 | 0.6078 | +0.0007 ±0.0067 | -0.0008 ±0.0027 | 0.658 | 0.666 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 474 | -0.0326 ±0.0082 | -0.0132 ±0.0034 | -4.0 | 0.686 | 0.704 | |
| pred_source: backtest | 925 | +0.0007 ±0.0067 | -0.0008 ±0.0027 | +0.1 | 0.658 | 0.666 | |
| top-20 involved | 479 | +0.0053 ±0.0077 | +0.0001 ±0.0026 | +0.7 | 0.730 | 0.730 | |
| no top-20 player | 920 | -0.0189 ±0.0068 | -0.0076 ±0.0029 | -2.8 | 0.635 | 0.653 | |
| both inside top-50 | 326 | -0.0075 ±0.0094 | -0.0038 ±0.0040 | -0.8 | 0.658 | 0.655 | |
| someone outside top-50 | 1073 | -0.0115 ±0.0062 | -0.0054 ±0.0025 | -1.9 | 0.671 | 0.686 | |
| best rank 1-10 | 287 | +0.0204 ±0.0100 | +0.0050 ±0.0030 | +2.0 | 0.742 | 0.735 | |
| best rank 11-20 | 192 | -0.0172 ±0.0117 | -0.0073 ±0.0046 | -1.5 | 0.711 | 0.721 | |
| best rank 21-50 | 485 | -0.0233 ±0.0081 | -0.0096 ±0.0036 | -2.9 | 0.658 | 0.696 | |
| best rank 51-100 | 352 | -0.0107 ±0.0116 | -0.0042 ±0.0049 | -0.9 | 0.615 | 0.607 | |
| best rank 100+ | 83 | -0.0276 ±0.0328 | -0.0105 ±0.0141 | -0.8 | 0.590 | 0.596 | |
| kalshi favorite 0.5-0.6 | 398 | -0.0264 ±0.0091 | -0.0122 ±0.0042 | -2.9 | 0.499 | 0.540 | |
| kalshi favorite 0.6-0.7 | 386 | -0.0063 ±0.0094 | -0.0025 ±0.0043 | -0.7 | 0.624 | 0.624 | |
| kalshi favorite 0.7-0.8 | 325 | -0.0053 ±0.0091 | -0.0022 ±0.0037 | -0.6 | 0.743 | 0.745 | |
| kalshi favorite 0.8-0.9 | 195 | +0.0092 ±0.0165 | +0.0023 ±0.0059 | +0.6 | 0.836 | 0.836 | |
| kalshi favorite 0.9-1.0 | 95 | -0.0208 ±0.0298 | -0.0094 ±0.0081 | -0.7 | 0.947 | 0.937 | |
| surface: Hard | 549 | -0.0234 ±0.0080 | -0.0094 ±0.0033 | -2.9 | 0.678 | 0.686 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 414 | -0.0194 ±0.0108 | -0.0085 ±0.0045 | -1.8 | 0.604 | 0.622 | |
| tier: atp500 | 250 | -0.0149 ±0.0103 | -0.0067 ±0.0046 | -1.4 | 0.628 | 0.642 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| round early (R128-R64) | 549 | -0.0098 ±0.0086 | -0.0045 ±0.0034 | -1.1 | 0.724 | 0.731 | |
| round late (QF-F) | 181 | -0.0149 ±0.0120 | -0.0073 ±0.0053 | -1.2 | 0.624 | 0.635 | |
| round mid (R32-R16) | 647 | -0.0102 ±0.0078 | -0.0048 ±0.0033 | -1.3 | 0.638 | 0.651 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 259 | -0.0394 ±0.0115 | -0.0168 ±0.0048 | -3.4 | 0.730 | 0.757 | |
| agree (<0.05) | 753 | -0.0006 ±0.0026 | -0.0009 ±0.0009 | -0.2 | 0.709 | 0.706 | |
| mild disagree (0.05-0.10) | 417 | -0.0087 ±0.0089 | -0.0041 ±0.0034 | -1.0 | 0.622 | 0.653 | |
| big disagree (>=0.1) | 229 | -0.0469 ±0.0260 | -0.0200 ±0.0111 | -1.8 | 0.614 | 0.638 | |
| tour: atp | 662 | -0.0049 ±0.0072 | -0.0030 ±0.0029 | -0.7 | 0.651 | 0.668 | |
| tour: wta | 737 | -0.0157 ±0.0075 | -0.0068 ±0.0031 | -2.1 | 0.682 | 0.689 | |

When they disagree by >= 0.1: model closer to the outcome in **90/229** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 15 | 0.066 | 0.133 |
| 0.1-0.2 | 87 | 0.153 | 0.138 |
| 0.2-0.3 | 125 | 0.252 | 0.264 |
| 0.3-0.4 | 178 | 0.354 | 0.354 |
| 0.4-0.5 | 244 | 0.452 | 0.471 |
| 0.5-0.6 | 220 | 0.552 | 0.545 |
| 0.6-0.7 | 210 | 0.647 | 0.629 |
| 0.7-0.8 | 169 | 0.751 | 0.763 |
| 0.8-0.9 | 104 | 0.847 | 0.817 |
| 0.9-1.0 | 47 | 0.933 | 0.936 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 36 | 0.060 | 0.083 |
| 0.1-0.2 | 79 | 0.153 | 0.139 |
| 0.2-0.3 | 144 | 0.255 | 0.271 |
| 0.3-0.4 | 173 | 0.355 | 0.376 |
| 0.4-0.5 | 201 | 0.445 | 0.453 |
| 0.5-0.6 | 200 | 0.555 | 0.525 |
| 0.6-0.7 | 210 | 0.649 | 0.633 |
| 0.7-0.8 | 181 | 0.749 | 0.757 |
| 0.8-0.9 | 117 | 0.847 | 0.821 |
| 0.9-1.0 | 58 | 0.935 | 0.948 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 287 | +0.0204 ±0.0100 | +0.0050 ±0.0030 | +2.0 | 0.742 | 0.735 | |
| top-20 involved | 479 | +0.0053 ±0.0077 | +0.0001 ±0.0026 | +0.7 | 0.730 | 0.730 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| kalshi favorite 0.8-0.9 | 195 | +0.0092 ±0.0165 | +0.0023 ±0.0059 | +0.6 | 0.836 | 0.836 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 925 | +0.0007 ±0.0067 | -0.0008 ±0.0027 | +0.1 | 0.658 | 0.666 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| someone outside top-50 | 1073 | -0.0115 ±0.0062 | -0.0054 ±0.0025 | -1.9 | 0.671 | 0.686 | |
| tour: wta | 737 | -0.0157 ±0.0075 | -0.0068 ±0.0031 | -2.1 | 0.682 | 0.689 | |
| no top-20 player | 920 | -0.0189 ±0.0068 | -0.0076 ±0.0029 | -2.8 | 0.635 | 0.653 | |
| best rank 21-50 | 485 | -0.0233 ±0.0081 | -0.0096 ±0.0036 | -2.9 | 0.658 | 0.696 | |
| kalshi favorite 0.5-0.6 | 398 | -0.0264 ±0.0091 | -0.0122 ±0.0042 | -2.9 | 0.499 | 0.540 | |
| surface: Hard | 549 | -0.0234 ±0.0080 | -0.0094 ±0.0033 | -2.9 | 0.678 | 0.686 | |
| month 2026-09 | 259 | -0.0394 ±0.0115 | -0.0168 ±0.0048 | -3.4 | 0.730 | 0.757 | |
| pred_source: live aligned | 474 | -0.0326 ±0.0082 | -0.0132 ±0.0034 | -4.0 | 0.686 | 0.704 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1399, mean |Δ|=0.0034, p95=0.0100, >0.05 in 18 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0666 (n=259, >0.05: 16)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1399, d_ll -0.0106 ±0.0052 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 561 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Chengdu': 3, 'WTA Seoul': 2}
- Unmatched Kalshi names, main draw (40): Adrian Mannarino, Akasha Urhobo, Aleksandr Shevchenko, Alevtina Ibragimova, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide
