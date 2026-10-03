# Model vs Kalshi — match-by-match scorecard

_Generated 2026-10-03T11:19:03Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1960 | 1875 | 10 | 14 | 61 | 0 | 11 | 19 | 48 | 2026-05-03..2026-10-04 |
| wta | 2089 | 1274 | 17 | 742 | 56 | 0 | 10 | 15 | 40 | 2026-05-02..2026-10-04 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1479 | 0.6000 | 0.5863 | -0.0137 ±0.0052 | -0.0062 ±0.0021 | 0.665 | 0.677 |
| atp | 703 | 0.6177 | 0.6106 | -0.0071 ±0.0073 | -0.0037 ±0.0029 | 0.649 | 0.666 |
| wta | 776 | 0.5840 | 0.5644 | -0.0196 ±0.0074 | -0.0084 ±0.0031 | 0.679 | 0.688 |
| pooled/live_aligned | 548 | 0.5888 | 0.5501 | -0.0387 ±0.0083 | -0.0157 ±0.0035 | 0.677 | 0.698 |
| pooled/backtest | 931 | 0.6066 | 0.6076 | +0.0010 ±0.0066 | -0.0006 ±0.0027 | 0.657 | 0.665 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 548 | -0.0387 ±0.0083 | -0.0157 ±0.0035 | -4.7 | 0.677 | 0.698 | |
| pred_source: backtest | 931 | +0.0010 ±0.0066 | -0.0006 ±0.0027 | +0.2 | 0.657 | 0.665 | |
| top-20 involved | 505 | +0.0012 ±0.0082 | -0.0014 ±0.0029 | +0.2 | 0.728 | 0.730 | |
| no top-20 player | 974 | -0.0214 ±0.0067 | -0.0086 ±0.0029 | -3.2 | 0.632 | 0.650 | |
| both inside top-50 | 350 | -0.0143 ±0.0102 | -0.0064 ±0.0043 | -1.4 | 0.656 | 0.659 | |
| someone outside top-50 | 1129 | -0.0135 ±0.0060 | -0.0061 ±0.0024 | -2.2 | 0.667 | 0.683 | |
| best rank 1-10 | 301 | +0.0189 ±0.0096 | +0.0046 ±0.0029 | +2.0 | 0.748 | 0.741 | |
| best rank 11-20 | 204 | -0.0248 ±0.0143 | -0.0103 ±0.0057 | -1.7 | 0.699 | 0.713 | |
| best rank 21-50 | 513 | -0.0247 ±0.0080 | -0.0103 ±0.0035 | -3.1 | 0.657 | 0.697 | |
| best rank 51-100 | 373 | -0.0135 ±0.0112 | -0.0053 ±0.0047 | -1.2 | 0.605 | 0.597 | |
| best rank 100+ | 88 | -0.0357 ±0.0320 | -0.0128 ±0.0136 | -1.1 | 0.602 | 0.608 | |
| kalshi favorite 0.5-0.6 | 426 | -0.0273 ±0.0088 | -0.0126 ±0.0041 | -3.1 | 0.496 | 0.535 | |
| kalshi favorite 0.6-0.7 | 410 | -0.0086 ±0.0092 | -0.0034 ±0.0042 | -0.9 | 0.620 | 0.622 | |
| kalshi favorite 0.7-0.8 | 337 | -0.0056 ±0.0089 | -0.0022 ±0.0036 | -0.6 | 0.746 | 0.748 | |
| kalshi favorite 0.8-0.9 | 204 | +0.0081 ±0.0158 | +0.0020 ±0.0056 | +0.5 | 0.838 | 0.838 | |
| kalshi favorite 0.9-1.0 | 102 | -0.0477 ±0.0329 | -0.0195 ±0.0103 | -1.5 | 0.931 | 0.941 | |
| surface: Hard | 629 | -0.0291 ±0.0080 | -0.0116 ±0.0033 | -3.6 | 0.669 | 0.681 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 455 | -0.0215 ±0.0107 | -0.0091 ±0.0045 | -2.0 | 0.604 | 0.623 | |
| tier: atp500 | 250 | -0.0149 ±0.0103 | -0.0067 ±0.0046 | -1.4 | 0.628 | 0.642 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 263 | -0.0083 ±0.0103 | -0.0024 ±0.0045 | -0.8 | 0.671 | 0.677 | |
| round early (R128-R64) | 588 | -0.0154 ±0.0084 | -0.0068 ±0.0033 | -1.8 | 0.717 | 0.727 | |
| round late (QF-F) | 189 | -0.0130 ±0.0115 | -0.0065 ±0.0051 | -1.1 | 0.635 | 0.646 | |
| round mid (R32-R16) | 680 | -0.0126 ±0.0080 | -0.0057 ±0.0033 | -1.6 | 0.633 | 0.648 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 320 | -0.0473 ±0.0116 | -0.0195 ±0.0048 | -4.1 | 0.700 | 0.731 | |
| month 2026-10 | 19 | -0.0277 ±0.0506 | -0.0127 ±0.0230 | -0.5 | 0.737 | 0.737 | ⚠ small n |
| agree (<0.05) | 799 | -0.0005 ±0.0025 | -0.0008 ±0.0009 | -0.2 | 0.708 | 0.705 | |
| mild disagree (0.05-0.10) | 440 | -0.0092 ±0.0086 | -0.0040 ±0.0033 | -1.1 | 0.624 | 0.649 | |
| big disagree (>=0.1) | 240 | -0.0660 ±0.0264 | -0.0279 ±0.0112 | -2.5 | 0.594 | 0.637 | |
| tour: atp | 703 | -0.0071 ±0.0073 | -0.0037 ±0.0029 | -1.0 | 0.649 | 0.666 | |
| tour: wta | 776 | -0.0196 ±0.0074 | -0.0084 ±0.0031 | -2.7 | 0.679 | 0.688 | |

When they disagree by >= 0.1: model closer to the outcome in **92/240** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 16 | 0.067 | 0.125 |
| 0.1-0.2 | 91 | 0.153 | 0.143 |
| 0.2-0.3 | 131 | 0.252 | 0.267 |
| 0.3-0.4 | 190 | 0.353 | 0.358 |
| 0.4-0.5 | 257 | 0.451 | 0.471 |
| 0.5-0.6 | 233 | 0.552 | 0.541 |
| 0.6-0.7 | 217 | 0.647 | 0.613 |
| 0.7-0.8 | 184 | 0.751 | 0.772 |
| 0.8-0.9 | 112 | 0.847 | 0.812 |
| 0.9-1.0 | 48 | 0.933 | 0.938 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 39 | 0.056 | 0.077 |
| 0.1-0.2 | 82 | 0.153 | 0.146 |
| 0.2-0.3 | 150 | 0.254 | 0.267 |
| 0.3-0.4 | 183 | 0.355 | 0.377 |
| 0.4-0.5 | 220 | 0.444 | 0.455 |
| 0.5-0.6 | 210 | 0.556 | 0.519 |
| 0.6-0.7 | 223 | 0.650 | 0.628 |
| 0.7-0.8 | 187 | 0.749 | 0.759 |
| 0.8-0.9 | 123 | 0.846 | 0.829 |
| 0.9-1.0 | 62 | 0.934 | 0.952 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 301 | +0.0189 ±0.0096 | +0.0046 ±0.0029 | +2.0 | 0.748 | 0.741 | |
| kalshi favorite 0.8-0.9 | 204 | +0.0081 ±0.0158 | +0.0020 ±0.0056 | +0.5 | 0.838 | 0.838 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 931 | +0.0010 ±0.0066 | -0.0006 ±0.0027 | +0.2 | 0.657 | 0.665 | |
| top-20 involved | 505 | +0.0012 ±0.0082 | -0.0014 ±0.0029 | +0.2 | 0.728 | 0.730 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| agree (<0.05) | 799 | -0.0005 ±0.0025 | -0.0008 ±0.0009 | -0.2 | 0.708 | 0.705 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| big disagree (>=0.1) | 240 | -0.0660 ±0.0264 | -0.0279 ±0.0112 | -2.5 | 0.594 | 0.637 | |
| tour: wta | 776 | -0.0196 ±0.0074 | -0.0084 ±0.0031 | -2.7 | 0.679 | 0.688 | |
| best rank 21-50 | 513 | -0.0247 ±0.0080 | -0.0103 ±0.0035 | -3.1 | 0.657 | 0.697 | |
| kalshi favorite 0.5-0.6 | 426 | -0.0273 ±0.0088 | -0.0126 ±0.0041 | -3.1 | 0.496 | 0.535 | |
| no top-20 player | 974 | -0.0214 ±0.0067 | -0.0086 ±0.0029 | -3.2 | 0.632 | 0.650 | |
| surface: Hard | 629 | -0.0291 ±0.0080 | -0.0116 ±0.0033 | -3.6 | 0.669 | 0.681 | |
| month 2026-09 | 320 | -0.0473 ±0.0116 | -0.0195 ±0.0048 | -4.1 | 0.700 | 0.731 | |
| pred_source: live aligned | 548 | -0.0387 ±0.0083 | -0.0157 ±0.0035 | -4.7 | 0.677 | 0.698 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1479, mean |Δ|=0.0041, p95=0.0100, >0.05 in 23 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0602 (n=320, >0.05: 18) | 2026-10 p95=0.2144 (n=19, >0.05: 3)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1479, d_ll -0.0137 ±0.0052 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 597 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'WTA Seoul': 3, 'ATP Beijing': 2}
- Unmatched Kalshi names, main draw (40): Akasha Urhobo, Aleksandr Shevchenko, Alevtina Ibragimova, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari
