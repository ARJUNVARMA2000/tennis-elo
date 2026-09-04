# Model vs Kalshi — match-by-match scorecard

_Generated 2026-09-04T10:20:44Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1786 | 1698 | 19 | 12 | 57 | 0 | 11 | 19 | 59 | 2026-05-03..2026-09-05 |
| wta | 1773 | 1060 | 16 | 655 | 42 | 0 | 7 | 15 | 34 | 2026-05-02..2026-09-05 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1205 | 0.5979 | 0.5925 | -0.0054 ±0.0056 | -0.0029 ±0.0023 | 0.666 | 0.674 |
| atp | 592 | 0.6204 | 0.6200 | -0.0004 ±0.0076 | -0.0009 ±0.0030 | 0.647 | 0.663 |
| wta | 613 | 0.5762 | 0.5660 | -0.0102 ±0.0081 | -0.0047 ±0.0034 | 0.685 | 0.684 |
| pooled/live_aligned | 288 | 0.5730 | 0.5505 | -0.0225 ±0.0094 | -0.0089 ±0.0039 | 0.691 | 0.693 |
| pooled/backtest | 917 | 0.6057 | 0.6057 | +0.0000 ±0.0067 | -0.0010 ±0.0027 | 0.659 | 0.668 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 288 | -0.0225 ±0.0094 | -0.0089 ±0.0039 | -2.4 | 0.691 | 0.693 | |
| pred_source: backtest | 917 | +0.0000 ±0.0067 | -0.0010 ±0.0027 | +0.0 | 0.659 | 0.668 | |
| top-20 involved | 419 | +0.0064 ±0.0081 | +0.0008 ±0.0027 | +0.8 | 0.732 | 0.732 | |
| no top-20 player | 786 | -0.0116 ±0.0073 | -0.0048 ±0.0032 | -1.6 | 0.632 | 0.643 | |
| both inside top-50 | 262 | -0.0003 ±0.0102 | -0.0003 ±0.0044 | -0.0 | 0.647 | 0.639 | |
| someone outside top-50 | 943 | -0.0068 ±0.0065 | -0.0036 ±0.0026 | -1.0 | 0.672 | 0.683 | |
| best rank 1-10 | 244 | +0.0233 ±0.0113 | +0.0059 ±0.0034 | +2.1 | 0.738 | 0.734 | |
| best rank 11-20 | 175 | -0.0172 ±0.0112 | -0.0063 ±0.0044 | -1.5 | 0.723 | 0.729 | |
| best rank 21-50 | 434 | -0.0148 ±0.0082 | -0.0059 ±0.0036 | -1.8 | 0.654 | 0.685 | |
| best rank 51-100 | 293 | -0.0090 ±0.0134 | -0.0042 ±0.0057 | -0.7 | 0.602 | 0.594 | |
| best rank 100+ | 59 | -0.0016 ±0.0395 | +0.0001 ±0.0170 | -0.0 | 0.610 | 0.576 | |
| kalshi favorite 0.5-0.6 | 344 | -0.0244 ±0.0096 | -0.0115 ±0.0045 | -2.6 | 0.496 | 0.541 | |
| kalshi favorite 0.6-0.7 | 332 | -0.0013 ±0.0100 | +0.0000 ±0.0045 | -0.1 | 0.627 | 0.614 | |
| kalshi favorite 0.7-0.8 | 280 | -0.0026 ±0.0097 | -0.0011 ±0.0039 | -0.3 | 0.738 | 0.736 | |
| kalshi favorite 0.8-0.9 | 170 | +0.0116 ±0.0178 | +0.0041 ±0.0063 | +0.6 | 0.847 | 0.841 | |
| kalshi favorite 0.9-1.0 | 79 | +0.0142 ±0.0325 | +0.0013 ±0.0082 | +0.4 | 0.937 | 0.924 | |
| surface: Hard | 355 | -0.0127 ±0.0094 | -0.0046 ±0.0039 | -1.3 | 0.679 | 0.672 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 332 | -0.0048 ±0.0119 | -0.0030 ±0.0050 | -0.4 | 0.596 | 0.607 | |
| tier: atp500 | 204 | -0.0077 ±0.0100 | -0.0039 ±0.0045 | -0.8 | 0.613 | 0.610 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 444 | -0.0111 ±0.0101 | -0.0058 ±0.0038 | -1.1 | 0.735 | 0.750 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| round early (R128-R64) | 544 | -0.0111 ±0.0086 | -0.0049 ±0.0034 | -1.3 | 0.725 | 0.734 | |
| round late (QF-F) | 137 | +0.0031 ±0.0122 | +0.0006 ±0.0053 | +0.3 | 0.628 | 0.613 | |
| round mid (R32-R16) | 502 | -0.0015 ±0.0088 | -0.0016 ±0.0037 | -0.2 | 0.621 | 0.630 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 278 | -0.0117 ±0.0104 | -0.0044 ±0.0043 | -1.1 | 0.629 | 0.628 | |
| month 2026-09 | 63 | -0.0230 ±0.0145 | -0.0102 ±0.0060 | -1.6 | 0.889 | 0.873 | |
| agree (<0.05) | 647 | -0.0007 ±0.0028 | -0.0009 ±0.0009 | -0.3 | 0.713 | 0.709 | |
| mild disagree (0.05-0.10) | 362 | -0.0121 ±0.0096 | -0.0056 ±0.0036 | -1.3 | 0.609 | 0.646 | |
| big disagree (>=0.1) | 196 | -0.0081 ±0.0278 | -0.0043 ±0.0118 | -0.3 | 0.620 | 0.610 | |
| tour: atp | 592 | -0.0004 ±0.0076 | -0.0009 ±0.0030 | -0.1 | 0.647 | 0.663 | |
| tour: wta | 613 | -0.0102 ±0.0081 | -0.0047 ±0.0034 | -1.3 | 0.685 | 0.684 | |

When they disagree by >= 0.1: model closer to the outcome in **84/196** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 14 | 0.067 | 0.143 |
| 0.1-0.2 | 74 | 0.152 | 0.122 |
| 0.2-0.3 | 103 | 0.254 | 0.252 |
| 0.3-0.4 | 157 | 0.354 | 0.357 |
| 0.4-0.5 | 211 | 0.450 | 0.479 |
| 0.5-0.6 | 195 | 0.552 | 0.549 |
| 0.6-0.7 | 176 | 0.647 | 0.631 |
| 0.7-0.8 | 146 | 0.750 | 0.747 |
| 0.8-0.9 | 88 | 0.847 | 0.830 |
| 0.9-1.0 | 41 | 0.932 | 0.927 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 30 | 0.060 | 0.100 |
| 0.1-0.2 | 70 | 0.152 | 0.129 |
| 0.2-0.3 | 119 | 0.255 | 0.269 |
| 0.3-0.4 | 151 | 0.353 | 0.391 |
| 0.4-0.5 | 180 | 0.444 | 0.456 |
| 0.5-0.6 | 167 | 0.555 | 0.527 |
| 0.6-0.7 | 178 | 0.648 | 0.629 |
| 0.7-0.8 | 161 | 0.748 | 0.739 |
| 0.8-0.9 | 101 | 0.846 | 0.822 |
| 0.9-1.0 | 48 | 0.932 | 0.938 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 244 | +0.0233 ±0.0113 | +0.0059 ±0.0034 | +2.1 | 0.738 | 0.734 | |
| top-20 involved | 419 | +0.0064 ±0.0081 | +0.0008 ±0.0027 | +0.8 | 0.732 | 0.732 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| kalshi favorite 0.8-0.9 | 170 | +0.0116 ±0.0178 | +0.0041 ±0.0063 | +0.6 | 0.847 | 0.841 | |
| kalshi favorite 0.9-1.0 | 79 | +0.0142 ±0.0325 | +0.0013 ±0.0082 | +0.4 | 0.937 | 0.924 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| round late (QF-F) | 137 | +0.0031 ±0.0122 | +0.0006 ±0.0053 | +0.3 | 0.628 | 0.613 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| round early (R128-R64) | 544 | -0.0111 ±0.0086 | -0.0049 ±0.0034 | -1.3 | 0.725 | 0.734 | |
| surface: Hard | 355 | -0.0127 ±0.0094 | -0.0046 ±0.0039 | -1.3 | 0.679 | 0.672 | |
| best rank 11-20 | 175 | -0.0172 ±0.0112 | -0.0063 ±0.0044 | -1.5 | 0.723 | 0.729 | |
| month 2026-09 | 63 | -0.0230 ±0.0145 | -0.0102 ±0.0060 | -1.6 | 0.889 | 0.873 | |
| no top-20 player | 786 | -0.0116 ±0.0073 | -0.0048 ±0.0032 | -1.6 | 0.632 | 0.643 | |
| best rank 21-50 | 434 | -0.0148 ±0.0082 | -0.0059 ±0.0036 | -1.8 | 0.654 | 0.685 | |
| pred_source: live aligned | 288 | -0.0225 ±0.0094 | -0.0089 ±0.0039 | -2.4 | 0.691 | 0.693 | |
| kalshi favorite 0.5-0.6 | 344 | -0.0244 ±0.0096 | -0.0115 ±0.0045 | -2.6 | 0.496 | 0.541 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1205, mean |Δ|=0.0018, p95=0.0087, >0.05 in 2 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0085 (n=278, >0.05: 1) | 2026-09 p95=0.0021 (n=63, >0.05: 0)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1205, d_ll -0.0054 ±0.0056 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 512 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 59, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Cincinnati': 1, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): Adam Walton, Akasha Urhobo, Aleksandr Shevchenko, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari
