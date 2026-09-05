# Model vs Kalshi — match-by-match scorecard

_Generated 2026-09-05T09:59:37Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1790 | 1705 | 15 | 13 | 57 | 0 | 11 | 19 | 55 | 2026-05-03..2026-09-06 |
| wta | 1777 | 1068 | 12 | 655 | 42 | 0 | 7 | 15 | 27 | 2026-05-02..2026-09-06 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1220 | 0.5972 | 0.5924 | -0.0049 ±0.0055 | -0.0026 ±0.0022 | 0.667 | 0.674 |
| atp | 599 | 0.6185 | 0.6189 | +0.0005 ±0.0075 | -0.0005 ±0.0030 | 0.649 | 0.664 |
| wta | 621 | 0.5767 | 0.5667 | -0.0100 ±0.0080 | -0.0047 ±0.0033 | 0.684 | 0.684 |
| pooled/live_aligned | 303 | 0.5715 | 0.5519 | -0.0197 ±0.0090 | -0.0077 ±0.0038 | 0.693 | 0.691 |
| pooled/backtest | 917 | 0.6057 | 0.6057 | +0.0000 ±0.0067 | -0.0010 ±0.0027 | 0.659 | 0.668 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 303 | -0.0197 ±0.0090 | -0.0077 ±0.0038 | -2.2 | 0.693 | 0.691 | |
| pred_source: backtest | 917 | +0.0000 ±0.0067 | -0.0010 ±0.0027 | +0.0 | 0.659 | 0.668 | |
| top-20 involved | 431 | +0.0069 ±0.0079 | +0.0010 ±0.0026 | +0.9 | 0.732 | 0.732 | |
| no top-20 player | 789 | -0.0113 ±0.0073 | -0.0046 ±0.0032 | -1.5 | 0.632 | 0.642 | |
| both inside top-50 | 275 | +0.0018 ±0.0098 | +0.0006 ±0.0042 | +0.2 | 0.653 | 0.642 | |
| someone outside top-50 | 945 | -0.0068 ±0.0065 | -0.0036 ±0.0026 | -1.0 | 0.671 | 0.683 | |
| best rank 1-10 | 252 | +0.0234 ±0.0109 | +0.0059 ±0.0033 | +2.1 | 0.738 | 0.734 | |
| best rank 11-20 | 179 | -0.0163 ±0.0110 | -0.0059 ±0.0043 | -1.5 | 0.723 | 0.729 | |
| best rank 21-50 | 437 | -0.0141 ±0.0082 | -0.0056 ±0.0036 | -1.7 | 0.654 | 0.683 | |
| best rank 51-100 | 293 | -0.0090 ±0.0134 | -0.0042 ±0.0057 | -0.7 | 0.602 | 0.594 | |
| best rank 100+ | 59 | -0.0016 ±0.0395 | +0.0001 ±0.0170 | -0.0 | 0.610 | 0.576 | |
| kalshi favorite 0.5-0.6 | 345 | -0.0241 ±0.0095 | -0.0113 ±0.0045 | -2.5 | 0.497 | 0.539 | |
| kalshi favorite 0.6-0.7 | 338 | -0.0005 ±0.0098 | +0.0003 ±0.0045 | -0.1 | 0.627 | 0.615 | |
| kalshi favorite 0.7-0.8 | 286 | -0.0018 ±0.0095 | -0.0008 ±0.0039 | -0.2 | 0.736 | 0.734 | |
| kalshi favorite 0.8-0.9 | 171 | +0.0114 ±0.0177 | +0.0041 ±0.0063 | +0.6 | 0.848 | 0.842 | |
| kalshi favorite 0.9-1.0 | 80 | +0.0143 ±0.0321 | +0.0013 ±0.0081 | +0.4 | 0.938 | 0.925 | |
| surface: Hard | 370 | -0.0107 ±0.0090 | -0.0038 ±0.0038 | -1.2 | 0.681 | 0.672 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 332 | -0.0048 ±0.0119 | -0.0030 ±0.0050 | -0.4 | 0.596 | 0.607 | |
| tier: atp500 | 204 | -0.0077 ±0.0100 | -0.0039 ±0.0045 | -0.8 | 0.613 | 0.610 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 459 | -0.0096 ±0.0098 | -0.0051 ±0.0037 | -1.0 | 0.735 | 0.747 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| round early (R128-R64) | 544 | -0.0111 ±0.0086 | -0.0049 ±0.0034 | -1.3 | 0.725 | 0.734 | |
| round late (QF-F) | 137 | +0.0031 ±0.0122 | +0.0006 ±0.0053 | +0.3 | 0.628 | 0.613 | |
| round mid (R32-R16) | 517 | -0.0004 ±0.0086 | -0.0012 ±0.0036 | -0.0 | 0.624 | 0.632 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 278 | -0.0117 ±0.0104 | -0.0044 ±0.0043 | -1.1 | 0.629 | 0.628 | |
| month 2026-09 | 78 | -0.0118 ±0.0124 | -0.0054 ±0.0051 | -1.0 | 0.859 | 0.833 | |
| agree (<0.05) | 659 | -0.0004 ±0.0028 | -0.0008 ±0.0009 | -0.2 | 0.712 | 0.706 | |
| mild disagree (0.05-0.10) | 365 | -0.0111 ±0.0096 | -0.0052 ±0.0036 | -1.2 | 0.612 | 0.649 | |
| big disagree (>=0.1) | 196 | -0.0081 ±0.0278 | -0.0043 ±0.0118 | -0.3 | 0.620 | 0.610 | |
| tour: atp | 599 | +0.0005 ±0.0075 | -0.0005 ±0.0030 | +0.1 | 0.649 | 0.664 | |
| tour: wta | 621 | -0.0100 ±0.0080 | -0.0047 ±0.0033 | -1.2 | 0.684 | 0.684 | |

When they disagree by >= 0.1: model closer to the outcome in **84/196** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 14 | 0.067 | 0.143 |
| 0.1-0.2 | 75 | 0.152 | 0.120 |
| 0.2-0.3 | 107 | 0.254 | 0.262 |
| 0.3-0.4 | 159 | 0.354 | 0.352 |
| 0.4-0.5 | 212 | 0.450 | 0.476 |
| 0.5-0.6 | 195 | 0.552 | 0.549 |
| 0.6-0.7 | 180 | 0.647 | 0.628 |
| 0.7-0.8 | 147 | 0.750 | 0.748 |
| 0.8-0.9 | 89 | 0.847 | 0.831 |
| 0.9-1.0 | 42 | 0.932 | 0.929 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 30 | 0.060 | 0.100 |
| 0.1-0.2 | 70 | 0.152 | 0.129 |
| 0.2-0.3 | 124 | 0.255 | 0.274 |
| 0.3-0.4 | 153 | 0.354 | 0.386 |
| 0.4-0.5 | 180 | 0.444 | 0.456 |
| 0.5-0.6 | 168 | 0.555 | 0.524 |
| 0.6-0.7 | 182 | 0.647 | 0.626 |
| 0.7-0.8 | 162 | 0.748 | 0.741 |
| 0.8-0.9 | 102 | 0.846 | 0.824 |
| 0.9-1.0 | 49 | 0.932 | 0.939 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 252 | +0.0234 ±0.0109 | +0.0059 ±0.0033 | +2.1 | 0.738 | 0.734 | |
| top-20 involved | 431 | +0.0069 ±0.0079 | +0.0010 ±0.0026 | +0.9 | 0.732 | 0.732 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| kalshi favorite 0.8-0.9 | 171 | +0.0114 ±0.0177 | +0.0041 ±0.0063 | +0.6 | 0.848 | 0.842 | |
| kalshi favorite 0.9-1.0 | 80 | +0.0143 ±0.0321 | +0.0013 ±0.0081 | +0.4 | 0.938 | 0.925 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| round late (QF-F) | 137 | +0.0031 ±0.0122 | +0.0006 ±0.0053 | +0.3 | 0.628 | 0.613 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| surface: Hard | 370 | -0.0107 ±0.0090 | -0.0038 ±0.0038 | -1.2 | 0.681 | 0.672 | |
| tour: wta | 621 | -0.0100 ±0.0080 | -0.0047 ±0.0033 | -1.2 | 0.684 | 0.684 | |
| round early (R128-R64) | 544 | -0.0111 ±0.0086 | -0.0049 ±0.0034 | -1.3 | 0.725 | 0.734 | |
| best rank 11-20 | 179 | -0.0163 ±0.0110 | -0.0059 ±0.0043 | -1.5 | 0.723 | 0.729 | |
| no top-20 player | 789 | -0.0113 ±0.0073 | -0.0046 ±0.0032 | -1.5 | 0.632 | 0.642 | |
| best rank 21-50 | 437 | -0.0141 ±0.0082 | -0.0056 ±0.0036 | -1.7 | 0.654 | 0.683 | |
| pred_source: live aligned | 303 | -0.0197 ±0.0090 | -0.0077 ±0.0038 | -2.2 | 0.693 | 0.691 | |
| kalshi favorite 0.5-0.6 | 345 | -0.0241 ±0.0095 | -0.0113 ±0.0045 | -2.5 | 0.497 | 0.539 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1220, mean |Δ|=0.0018, p95=0.0086, >0.05 in 2 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0085 (n=278, >0.05: 1) | 2026-09 p95=0.0030 (n=78, >0.05: 0)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1220, d_ll -0.0049 ±0.0055 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 512 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 60, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Cincinnati': 1, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): Adam Walton, Akasha Urhobo, Aleksandr Shevchenko, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari
