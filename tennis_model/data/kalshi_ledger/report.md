# Model vs Kalshi — match-by-match scorecard

_Generated 2026-10-01T06:49:24Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1944 | 1850 | 22 | 12 | 60 | 0 | 11 | 19 | 48 | 2026-05-03..2026-10-02 |
| wta | 2067 | 1235 | 72 | 706 | 54 | 0 | 10 | 15 | 50 | 2026-05-02..2026-10-02 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1436 | 0.6007 | 0.5878 | -0.0129 ±0.0053 | -0.0059 ±0.0022 | 0.664 | 0.677 |
| atp | 684 | 0.6191 | 0.6114 | -0.0077 ±0.0075 | -0.0040 ±0.0030 | 0.646 | 0.665 |
| wta | 752 | 0.5839 | 0.5663 | -0.0176 ±0.0074 | -0.0076 ±0.0031 | 0.680 | 0.688 |
| pooled/live_aligned | 506 | 0.5889 | 0.5503 | -0.0386 ±0.0086 | -0.0157 ±0.0036 | 0.676 | 0.699 |
| pooled/backtest | 930 | 0.6071 | 0.6082 | +0.0011 ±0.0066 | -0.0006 ±0.0027 | 0.657 | 0.665 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 506 | -0.0386 ±0.0086 | -0.0157 ±0.0036 | -4.5 | 0.676 | 0.699 | |
| pred_source: backtest | 930 | +0.0011 ±0.0066 | -0.0006 ±0.0027 | +0.2 | 0.657 | 0.665 | |
| top-20 involved | 489 | +0.0005 ±0.0084 | -0.0018 ±0.0030 | +0.1 | 0.725 | 0.729 | |
| no top-20 player | 947 | -0.0198 ±0.0067 | -0.0080 ±0.0029 | -2.9 | 0.632 | 0.650 | |
| both inside top-50 | 337 | -0.0142 ±0.0106 | -0.0064 ±0.0045 | -1.3 | 0.651 | 0.654 | |
| someone outside top-50 | 1099 | -0.0125 ±0.0061 | -0.0057 ±0.0025 | -2.0 | 0.667 | 0.684 | |
| best rank 1-10 | 292 | +0.0196 ±0.0099 | +0.0047 ±0.0030 | +2.0 | 0.743 | 0.736 | |
| best rank 11-20 | 197 | -0.0277 ±0.0147 | -0.0116 ±0.0059 | -1.9 | 0.698 | 0.718 | |
| best rank 21-50 | 495 | -0.0246 ±0.0081 | -0.0102 ±0.0036 | -3.0 | 0.657 | 0.696 | |
| best rank 51-100 | 367 | -0.0118 ±0.0113 | -0.0045 ±0.0048 | -1.0 | 0.606 | 0.598 | |
| best rank 100+ | 85 | -0.0260 ±0.0321 | -0.0098 ±0.0138 | -0.8 | 0.600 | 0.606 | |
| kalshi favorite 0.5-0.6 | 411 | -0.0269 ±0.0089 | -0.0125 ±0.0041 | -3.0 | 0.495 | 0.535 | |
| kalshi favorite 0.6-0.7 | 400 | -0.0062 ±0.0092 | -0.0026 ±0.0042 | -0.7 | 0.623 | 0.625 | |
| kalshi favorite 0.7-0.8 | 330 | -0.0062 ±0.0091 | -0.0024 ±0.0037 | -0.7 | 0.741 | 0.742 | |
| kalshi favorite 0.8-0.9 | 197 | +0.0086 ±0.0163 | +0.0022 ±0.0058 | +0.5 | 0.838 | 0.838 | |
| kalshi favorite 0.9-1.0 | 98 | -0.0468 ±0.0342 | -0.0197 ±0.0107 | -1.4 | 0.929 | 0.939 | |
| surface: Hard | 586 | -0.0282 ±0.0083 | -0.0113 ±0.0035 | -3.4 | 0.667 | 0.680 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 436 | -0.0230 ±0.0112 | -0.0098 ±0.0046 | -2.1 | 0.599 | 0.620 | |
| tier: atp500 | 250 | -0.0149 ±0.0103 | -0.0067 ±0.0046 | -1.4 | 0.628 | 0.642 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 239 | -0.0006 ±0.0101 | +0.0006 ±0.0045 | -0.1 | 0.672 | 0.674 | |
| round early (R128-R64) | 564 | -0.0125 ±0.0085 | -0.0057 ±0.0034 | -1.5 | 0.719 | 0.728 | |
| round late (QF-F) | 189 | -0.0130 ±0.0115 | -0.0065 ±0.0051 | -1.1 | 0.635 | 0.646 | |
| round mid (R32-R16) | 661 | -0.0134 ±0.0082 | -0.0060 ±0.0034 | -1.6 | 0.630 | 0.647 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 296 | -0.0469 ±0.0123 | -0.0197 ±0.0051 | -3.8 | 0.703 | 0.736 | |
| agree (<0.05) | 771 | -0.0005 ±0.0026 | -0.0008 ±0.0009 | -0.2 | 0.704 | 0.701 | |
| mild disagree (0.05-0.10) | 429 | -0.0097 ±0.0088 | -0.0044 ±0.0033 | -1.1 | 0.626 | 0.654 | |
| big disagree (>=0.1) | 236 | -0.0590 ±0.0265 | -0.0251 ±0.0113 | -2.2 | 0.600 | 0.640 | |
| tour: atp | 684 | -0.0077 ±0.0075 | -0.0040 ±0.0030 | -1.0 | 0.646 | 0.665 | |
| tour: wta | 752 | -0.0176 ±0.0074 | -0.0076 ±0.0031 | -2.4 | 0.680 | 0.688 | |

When they disagree by >= 0.1: model closer to the outcome in **92/236** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 16 | 0.067 | 0.125 |
| 0.1-0.2 | 87 | 0.153 | 0.138 |
| 0.2-0.3 | 128 | 0.252 | 0.266 |
| 0.3-0.4 | 183 | 0.353 | 0.361 |
| 0.4-0.5 | 250 | 0.452 | 0.472 |
| 0.5-0.6 | 228 | 0.552 | 0.539 |
| 0.6-0.7 | 214 | 0.647 | 0.617 |
| 0.7-0.8 | 177 | 0.751 | 0.768 |
| 0.8-0.9 | 106 | 0.847 | 0.811 |
| 0.9-1.0 | 47 | 0.933 | 0.936 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 39 | 0.056 | 0.077 |
| 0.1-0.2 | 79 | 0.153 | 0.139 |
| 0.2-0.3 | 146 | 0.254 | 0.274 |
| 0.3-0.4 | 181 | 0.355 | 0.376 |
| 0.4-0.5 | 208 | 0.445 | 0.457 |
| 0.5-0.6 | 206 | 0.556 | 0.519 |
| 0.6-0.7 | 216 | 0.649 | 0.634 |
| 0.7-0.8 | 184 | 0.749 | 0.755 |
| 0.8-0.9 | 119 | 0.847 | 0.824 |
| 0.9-1.0 | 58 | 0.935 | 0.948 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 292 | +0.0196 ±0.0099 | +0.0047 ±0.0030 | +2.0 | 0.743 | 0.736 | |
| kalshi favorite 0.8-0.9 | 197 | +0.0086 ±0.0163 | +0.0022 ±0.0058 | +0.5 | 0.838 | 0.838 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 930 | +0.0011 ±0.0066 | -0.0006 ±0.0027 | +0.2 | 0.657 | 0.665 | |
| top-20 involved | 489 | +0.0005 ±0.0084 | -0.0018 ±0.0030 | +0.1 | 0.725 | 0.729 | |
| tier: masters | 239 | -0.0006 ±0.0101 | +0.0006 ±0.0045 | -0.1 | 0.672 | 0.674 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| big disagree (>=0.1) | 236 | -0.0590 ±0.0265 | -0.0251 ±0.0113 | -2.2 | 0.600 | 0.640 | |
| tour: wta | 752 | -0.0176 ±0.0074 | -0.0076 ±0.0031 | -2.4 | 0.680 | 0.688 | |
| no top-20 player | 947 | -0.0198 ±0.0067 | -0.0080 ±0.0029 | -2.9 | 0.632 | 0.650 | |
| kalshi favorite 0.5-0.6 | 411 | -0.0269 ±0.0089 | -0.0125 ±0.0041 | -3.0 | 0.495 | 0.535 | |
| best rank 21-50 | 495 | -0.0246 ±0.0081 | -0.0102 ±0.0036 | -3.0 | 0.657 | 0.696 | |
| surface: Hard | 586 | -0.0282 ±0.0083 | -0.0113 ±0.0035 | -3.4 | 0.667 | 0.680 | |
| month 2026-09 | 296 | -0.0469 ±0.0123 | -0.0197 ±0.0051 | -3.8 | 0.703 | 0.736 | |
| pred_source: live aligned | 506 | -0.0386 ±0.0086 | -0.0157 ±0.0036 | -4.5 | 0.676 | 0.699 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1436, mean |Δ|=0.0038, p95=0.0100, >0.05 in 20 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0682 (n=296, >0.05: 18)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1436, d_ll -0.0129 ±0.0053 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 561 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'WTA Seoul': 3, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): Akasha Urhobo, Aleksandr Shevchenko, Alevtina Ibragimova, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari
