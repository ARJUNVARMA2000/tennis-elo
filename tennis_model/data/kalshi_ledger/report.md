# Model vs Kalshi — match-by-match scorecard

_Generated 2026-08-29T10:30:04Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1735 | 1607 | 65 | 9 | 54 | 0 | 11 | 19 | 108 | 2026-05-03..2026-08-30 |
| wta | 1724 | 963 | 113 | 607 | 41 | 0 | 7 | 15 | 83 | 2026-05-02..2026-08-31 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1020 | 0.6126 | 0.6123 | -0.0002 ±0.0062 | -0.0010 ±0.0025 | 0.647 | 0.654 |
| atp | 502 | 0.6292 | 0.6343 | +0.0051 ±0.0085 | +0.0005 ±0.0034 | 0.629 | 0.650 |
| wta | 518 | 0.5964 | 0.5910 | -0.0054 ±0.0089 | -0.0025 ±0.0037 | 0.664 | 0.657 |
| pooled/live_aligned | 105 | 0.6721 | 0.6683 | -0.0039 ±0.0135 | -0.0018 ±0.0060 | 0.543 | 0.529 |
| pooled/backtest | 915 | 0.6057 | 0.6059 | +0.0002 ±0.0067 | -0.0009 ±0.0027 | 0.659 | 0.668 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 105 | -0.0039 ±0.0135 | -0.0018 ±0.0060 | -0.3 | 0.543 | 0.529 | |
| pred_source: backtest | 915 | +0.0002 ±0.0067 | -0.0009 ±0.0027 | +0.0 | 0.659 | 0.668 | |
| top-20 involved | 351 | +0.0086 ±0.0093 | +0.0013 ±0.0031 | +0.9 | 0.699 | 0.699 | |
| no top-20 player | 669 | -0.0049 ±0.0080 | -0.0022 ±0.0035 | -0.6 | 0.620 | 0.630 | |
| both inside top-50 | 234 | +0.0082 ±0.0106 | +0.0028 ±0.0046 | +0.8 | 0.647 | 0.639 | |
| someone outside top-50 | 786 | -0.0027 ±0.0073 | -0.0022 ±0.0030 | -0.4 | 0.647 | 0.658 | |
| best rank 1-10 | 207 | +0.0274 ±0.0130 | +0.0073 ±0.0039 | +2.1 | 0.705 | 0.700 | |
| best rank 11-20 | 144 | -0.0184 ±0.0126 | -0.0074 ±0.0050 | -1.5 | 0.691 | 0.698 | |
| best rank 21-50 | 362 | -0.0122 ±0.0089 | -0.0054 ±0.0040 | -1.4 | 0.630 | 0.666 | |
| best rank 51-100 | 255 | +0.0018 ±0.0143 | +0.0004 ±0.0060 | +0.1 | 0.598 | 0.586 | |
| best rank 100+ | 52 | +0.0140 ±0.0441 | +0.0072 ±0.0189 | +0.3 | 0.654 | 0.596 | |
| kalshi favorite 0.5-0.6 | 305 | -0.0245 ±0.0095 | -0.0115 ±0.0045 | -2.6 | 0.477 | 0.525 | |
| kalshi favorite 0.6-0.7 | 295 | +0.0023 ±0.0106 | +0.0018 ±0.0048 | +0.2 | 0.620 | 0.603 | |
| kalshi favorite 0.7-0.8 | 234 | +0.0054 ±0.0108 | +0.0023 ±0.0044 | +0.5 | 0.737 | 0.735 | |
| kalshi favorite 0.8-0.9 | 126 | +0.0306 ±0.0226 | +0.0098 ±0.0083 | +1.4 | 0.817 | 0.810 | |
| kalshi favorite 0.9-1.0 | 60 | +0.0240 ±0.0427 | +0.0028 ±0.0109 | +0.6 | 0.933 | 0.917 | |
| surface: Hard | 170 | +0.0102 ±0.0140 | +0.0047 ±0.0059 | +0.7 | 0.576 | 0.550 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 331 | -0.0041 ±0.0119 | -0.0027 ±0.0050 | -0.3 | 0.598 | 0.609 | |
| tier: atp500 | 203 | -0.0086 ±0.0100 | -0.0043 ±0.0045 | -0.9 | 0.616 | 0.613 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 262 | +0.0047 ±0.0147 | -0.0007 ±0.0054 | +0.3 | 0.700 | 0.718 | |
| tier: masters | 223 | +0.0068 ±0.0099 | +0.0039 ±0.0044 | +0.7 | 0.684 | 0.682 | |
| round early (R128-R64) | 361 | +0.0004 ±0.0113 | -0.0008 ±0.0044 | +0.0 | 0.697 | 0.705 | |
| round late (QF-F) | 135 | +0.0035 ±0.0122 | +0.0008 ±0.0053 | +0.3 | 0.637 | 0.622 | |
| round mid (R32-R16) | 502 | -0.0015 ±0.0088 | -0.0016 ±0.0037 | -0.2 | 0.621 | 0.630 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 156 | +0.0098 ±0.0123 | +0.0035 ±0.0054 | +0.8 | 0.564 | 0.542 | |
| agree (<0.05) | 537 | +0.0002 ±0.0032 | -0.0006 ±0.0011 | +0.1 | 0.682 | 0.678 | |
| mild disagree (0.05-0.10) | 316 | -0.0013 ±0.0101 | -0.0022 ±0.0039 | -0.1 | 0.616 | 0.649 | |
| big disagree (>=0.1) | 167 | +0.0005 ±0.0308 | +0.0000 ±0.0131 | +0.0 | 0.596 | 0.587 | |
| tour: atp | 502 | +0.0051 ±0.0085 | +0.0005 ±0.0034 | +0.6 | 0.629 | 0.650 | |
| tour: wta | 518 | -0.0054 ±0.0089 | -0.0025 ±0.0037 | -0.6 | 0.664 | 0.657 | |

When they disagree by >= 0.1: model closer to the outcome in **70/167** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 10 | 0.066 | 0.100 |
| 0.1-0.2 | 55 | 0.153 | 0.109 |
| 0.2-0.3 | 86 | 0.254 | 0.256 |
| 0.3-0.4 | 145 | 0.354 | 0.366 |
| 0.4-0.5 | 188 | 0.450 | 0.489 |
| 0.5-0.6 | 173 | 0.551 | 0.526 |
| 0.6-0.7 | 159 | 0.645 | 0.616 |
| 0.7-0.8 | 119 | 0.749 | 0.765 |
| 0.8-0.9 | 63 | 0.845 | 0.794 |
| 0.9-1.0 | 22 | 0.925 | 0.909 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 25 | 0.060 | 0.080 |
| 0.1-0.2 | 53 | 0.155 | 0.151 |
| 0.2-0.3 | 102 | 0.255 | 0.284 |
| 0.3-0.4 | 134 | 0.353 | 0.381 |
| 0.4-0.5 | 160 | 0.443 | 0.469 |
| 0.5-0.6 | 147 | 0.556 | 0.517 |
| 0.6-0.7 | 159 | 0.648 | 0.597 |
| 0.7-0.8 | 132 | 0.746 | 0.750 |
| 0.8-0.9 | 73 | 0.846 | 0.781 |
| 0.9-1.0 | 35 | 0.933 | 0.914 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 207 | +0.0274 ±0.0130 | +0.0073 ±0.0039 | +2.1 | 0.705 | 0.700 | |
| kalshi favorite 0.8-0.9 | 126 | +0.0306 ±0.0226 | +0.0098 ±0.0083 | +1.4 | 0.817 | 0.810 | |
| top-20 involved | 351 | +0.0086 ±0.0093 | +0.0013 ±0.0031 | +0.9 | 0.699 | 0.699 | |
| month 2026-08 | 156 | +0.0098 ±0.0123 | +0.0035 ±0.0054 | +0.8 | 0.564 | 0.542 | |
| both inside top-50 | 234 | +0.0082 ±0.0106 | +0.0028 ±0.0046 | +0.8 | 0.647 | 0.639 | |
| surface: Hard | 170 | +0.0102 ±0.0140 | +0.0047 ±0.0059 | +0.7 | 0.576 | 0.550 | |
| tier: masters | 223 | +0.0068 ±0.0099 | +0.0039 ±0.0044 | +0.7 | 0.684 | 0.682 | |
| tour: atp | 502 | +0.0051 ±0.0085 | +0.0005 ±0.0034 | +0.6 | 0.629 | 0.650 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| tour: wta | 518 | -0.0054 ±0.0089 | -0.0025 ±0.0037 | -0.6 | 0.664 | 0.657 | |
| no top-20 player | 669 | -0.0049 ±0.0080 | -0.0022 ±0.0035 | -0.6 | 0.620 | 0.630 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp500 | 203 | -0.0086 ±0.0100 | -0.0043 ±0.0045 | -0.9 | 0.616 | 0.613 | |
| best rank 21-50 | 362 | -0.0122 ±0.0089 | -0.0054 ±0.0040 | -1.4 | 0.630 | 0.666 | |
| best rank 11-20 | 144 | -0.0184 ±0.0126 | -0.0074 ±0.0050 | -1.5 | 0.691 | 0.698 | |
| kalshi favorite 0.5-0.6 | 305 | -0.0245 ±0.0095 | -0.0115 ±0.0045 | -2.6 | 0.477 | 0.525 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1020, mean |Δ|=0.0020, p95=0.0099, >0.05 in 2 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0123 (n=156, >0.05: 1)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1020, d_ll -0.0002 ±0.0062 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 464 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 55, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Los Cabos': 1, 'ATP Cincinnati': 1}
- Unmatched Kalshi names, main draw (40): Akasha Urhobo, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari, Carson Branstine, Casper Ruud, Caty McNally
