# Model vs Kalshi — match-by-match scorecard

_Generated 2026-10-02T07:55:17Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1954 | 1866 | 15 | 12 | 61 | 0 | 11 | 19 | 48 | 2026-05-03..2026-10-03 |
| wta | 2078 | 1254 | 38 | 730 | 56 | 0 | 10 | 15 | 34 | 2026-05-02..2026-10-03 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1459 | 0.6009 | 0.5873 | -0.0136 ±0.0052 | -0.0061 ±0.0021 | 0.663 | 0.676 |
| atp | 697 | 0.6182 | 0.6107 | -0.0075 ±0.0074 | -0.0039 ±0.0030 | 0.647 | 0.666 |
| wta | 762 | 0.5851 | 0.5660 | -0.0191 ±0.0074 | -0.0081 ±0.0031 | 0.678 | 0.686 |
| pooled/live_aligned | 528 | 0.5908 | 0.5516 | -0.0393 ±0.0084 | -0.0158 ±0.0035 | 0.674 | 0.696 |
| pooled/backtest | 931 | 0.6066 | 0.6076 | +0.0010 ±0.0066 | -0.0006 ±0.0027 | 0.657 | 0.665 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 528 | -0.0393 ±0.0084 | -0.0158 ±0.0035 | -4.7 | 0.674 | 0.696 | |
| pred_source: backtest | 931 | +0.0010 ±0.0066 | -0.0006 ±0.0027 | +0.2 | 0.657 | 0.665 | |
| top-20 involved | 496 | +0.0006 ±0.0083 | -0.0017 ±0.0029 | +0.1 | 0.723 | 0.727 | |
| no top-20 player | 963 | -0.0209 ±0.0067 | -0.0083 ±0.0029 | -3.1 | 0.633 | 0.651 | |
| both inside top-50 | 345 | -0.0137 ±0.0103 | -0.0061 ±0.0044 | -1.3 | 0.654 | 0.657 | |
| someone outside top-50 | 1114 | -0.0135 ±0.0061 | -0.0061 ±0.0025 | -2.2 | 0.667 | 0.683 | |
| best rank 1-10 | 296 | +0.0189 ±0.0098 | +0.0045 ±0.0029 | +1.9 | 0.743 | 0.736 | |
| best rank 11-20 | 200 | -0.0264 ±0.0145 | -0.0110 ±0.0058 | -1.8 | 0.693 | 0.713 | |
| best rank 21-50 | 503 | -0.0240 ±0.0080 | -0.0099 ±0.0035 | -3.0 | 0.658 | 0.697 | |
| best rank 51-100 | 372 | -0.0131 ±0.0112 | -0.0051 ±0.0047 | -1.2 | 0.606 | 0.598 | |
| best rank 100+ | 88 | -0.0357 ±0.0320 | -0.0128 ±0.0136 | -1.1 | 0.602 | 0.608 | |
| kalshi favorite 0.5-0.6 | 418 | -0.0265 ±0.0087 | -0.0123 ±0.0041 | -3.0 | 0.492 | 0.531 | |
| kalshi favorite 0.6-0.7 | 405 | -0.0085 ±0.0093 | -0.0034 ±0.0042 | -0.9 | 0.622 | 0.625 | |
| kalshi favorite 0.7-0.8 | 333 | -0.0063 ±0.0090 | -0.0024 ±0.0037 | -0.7 | 0.743 | 0.745 | |
| kalshi favorite 0.8-0.9 | 202 | +0.0082 ±0.0159 | +0.0020 ±0.0057 | +0.5 | 0.837 | 0.837 | |
| kalshi favorite 0.9-1.0 | 101 | -0.0481 ±0.0332 | -0.0197 ±0.0104 | -1.4 | 0.931 | 0.941 | |
| surface: Hard | 609 | -0.0293 ±0.0081 | -0.0116 ±0.0034 | -3.6 | 0.667 | 0.679 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 449 | -0.0223 ±0.0108 | -0.0095 ±0.0045 | -2.1 | 0.601 | 0.622 | |
| tier: atp500 | 250 | -0.0149 ±0.0103 | -0.0067 ±0.0046 | -1.4 | 0.628 | 0.642 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 249 | -0.0060 ±0.0102 | -0.0013 ±0.0045 | -0.6 | 0.669 | 0.671 | |
| round early (R128-R64) | 574 | -0.0146 ±0.0085 | -0.0064 ±0.0033 | -1.7 | 0.717 | 0.726 | |
| round late (QF-F) | 189 | -0.0130 ±0.0115 | -0.0065 ±0.0051 | -1.1 | 0.635 | 0.646 | |
| round mid (R32-R16) | 674 | -0.0131 ±0.0080 | -0.0059 ±0.0033 | -1.6 | 0.631 | 0.648 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 319 | -0.0477 ±0.0117 | -0.0196 ±0.0048 | -4.1 | 0.699 | 0.730 | |
| agree (<0.05) | 787 | -0.0006 ±0.0025 | -0.0009 ±0.0009 | -0.2 | 0.705 | 0.702 | |
| mild disagree (0.05-0.10) | 434 | -0.0105 ±0.0087 | -0.0046 ±0.0033 | -1.2 | 0.623 | 0.651 | |
| big disagree (>=0.1) | 238 | -0.0621 ±0.0264 | -0.0261 ±0.0112 | -2.3 | 0.599 | 0.639 | |
| tour: atp | 697 | -0.0075 ±0.0074 | -0.0039 ±0.0030 | -1.0 | 0.647 | 0.666 | |
| tour: wta | 762 | -0.0191 ±0.0074 | -0.0081 ±0.0031 | -2.6 | 0.678 | 0.686 | |

When they disagree by >= 0.1: model closer to the outcome in **92/238** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 16 | 0.067 | 0.125 |
| 0.1-0.2 | 89 | 0.153 | 0.146 |
| 0.2-0.3 | 129 | 0.252 | 0.264 |
| 0.3-0.4 | 185 | 0.353 | 0.357 |
| 0.4-0.5 | 255 | 0.452 | 0.475 |
| 0.5-0.6 | 230 | 0.552 | 0.539 |
| 0.6-0.7 | 216 | 0.647 | 0.616 |
| 0.7-0.8 | 182 | 0.751 | 0.769 |
| 0.8-0.9 | 110 | 0.847 | 0.809 |
| 0.9-1.0 | 47 | 0.933 | 0.936 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 39 | 0.056 | 0.077 |
| 0.1-0.2 | 82 | 0.153 | 0.146 |
| 0.2-0.3 | 147 | 0.255 | 0.272 |
| 0.3-0.4 | 181 | 0.355 | 0.376 |
| 0.4-0.5 | 214 | 0.445 | 0.458 |
| 0.5-0.6 | 208 | 0.556 | 0.514 |
| 0.6-0.7 | 220 | 0.650 | 0.632 |
| 0.7-0.8 | 186 | 0.749 | 0.758 |
| 0.8-0.9 | 121 | 0.846 | 0.826 |
| 0.9-1.0 | 61 | 0.934 | 0.951 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 296 | +0.0189 ±0.0098 | +0.0045 ±0.0029 | +1.9 | 0.743 | 0.736 | |
| kalshi favorite 0.8-0.9 | 202 | +0.0082 ±0.0159 | +0.0020 ±0.0057 | +0.5 | 0.837 | 0.837 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 931 | +0.0010 ±0.0066 | -0.0006 ±0.0027 | +0.2 | 0.657 | 0.665 | |
| top-20 involved | 496 | +0.0006 ±0.0083 | -0.0017 ±0.0029 | +0.1 | 0.723 | 0.727 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| agree (<0.05) | 787 | -0.0006 ±0.0025 | -0.0009 ±0.0009 | -0.2 | 0.705 | 0.702 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| big disagree (>=0.1) | 238 | -0.0621 ±0.0264 | -0.0261 ±0.0112 | -2.3 | 0.599 | 0.639 | |
| tour: wta | 762 | -0.0191 ±0.0074 | -0.0081 ±0.0031 | -2.6 | 0.678 | 0.686 | |
| best rank 21-50 | 503 | -0.0240 ±0.0080 | -0.0099 ±0.0035 | -3.0 | 0.658 | 0.697 | |
| kalshi favorite 0.5-0.6 | 418 | -0.0265 ±0.0087 | -0.0123 ±0.0041 | -3.0 | 0.492 | 0.531 | |
| no top-20 player | 963 | -0.0209 ±0.0067 | -0.0083 ±0.0029 | -3.1 | 0.633 | 0.651 | |
| surface: Hard | 609 | -0.0293 ±0.0081 | -0.0116 ±0.0034 | -3.6 | 0.667 | 0.679 | |
| month 2026-09 | 319 | -0.0477 ±0.0117 | -0.0196 ±0.0048 | -4.1 | 0.699 | 0.730 | |
| pred_source: live aligned | 528 | -0.0393 ±0.0084 | -0.0158 ±0.0035 | -4.7 | 0.674 | 0.696 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1459, mean |Δ|=0.0038, p95=0.0100, >0.05 in 20 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0605 (n=319, >0.05: 18)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1459, d_ll -0.0136 ±0.0052 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 585 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'WTA Seoul': 3, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): Akasha Urhobo, Aleksandr Shevchenko, Alevtina Ibragimova, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari
