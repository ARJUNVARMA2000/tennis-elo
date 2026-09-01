# Model vs Kalshi — match-by-match scorecard

_Generated 2026-09-01T06:41:06Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1758 | 1649 | 45 | 8 | 56 | 0 | 11 | 19 | 65 | 2026-05-03..2026-09-02 |
| wta | 1746 | 1008 | 41 | 655 | 42 | 0 | 7 | 15 | 40 | 2026-05-02..2026-09-02 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1105 | 0.6102 | 0.6074 | -0.0028 ±0.0059 | -0.0018 ±0.0024 | 0.651 | 0.657 |
| atp | 544 | 0.6268 | 0.6287 | +0.0018 ±0.0081 | -0.0002 ±0.0032 | 0.632 | 0.652 |
| wta | 561 | 0.5941 | 0.5868 | -0.0073 ±0.0085 | -0.0034 ±0.0035 | 0.668 | 0.662 |
| pooled/live_aligned | 189 | 0.6299 | 0.6127 | -0.0172 ±0.0116 | -0.0062 ±0.0048 | 0.614 | 0.606 |
| pooled/backtest | 916 | 0.6061 | 0.6063 | +0.0002 ±0.0067 | -0.0009 ±0.0027 | 0.658 | 0.668 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 189 | -0.0172 ±0.0116 | -0.0062 ±0.0048 | -1.5 | 0.614 | 0.606 | |
| pred_source: backtest | 916 | +0.0002 ±0.0067 | -0.0009 ±0.0027 | +0.0 | 0.658 | 0.668 | |
| top-20 involved | 374 | +0.0095 ±0.0089 | +0.0017 ±0.0029 | +1.1 | 0.713 | 0.713 | |
| no top-20 player | 731 | -0.0091 ±0.0076 | -0.0036 ±0.0033 | -1.2 | 0.619 | 0.629 | |
| both inside top-50 | 245 | +0.0056 ±0.0105 | +0.0020 ±0.0045 | +0.5 | 0.643 | 0.635 | |
| someone outside top-50 | 860 | -0.0052 ±0.0069 | -0.0029 ±0.0028 | -0.7 | 0.653 | 0.663 | |
| best rank 1-10 | 219 | +0.0285 ±0.0124 | +0.0075 ±0.0037 | +2.3 | 0.717 | 0.712 | |
| best rank 11-20 | 155 | -0.0174 ±0.0120 | -0.0066 ±0.0047 | -1.4 | 0.706 | 0.713 | |
| best rank 21-50 | 400 | -0.0129 ±0.0086 | -0.0050 ±0.0038 | -1.5 | 0.637 | 0.669 | |
| best rank 51-100 | 274 | -0.0065 ±0.0138 | -0.0032 ±0.0058 | -0.5 | 0.589 | 0.580 | |
| best rank 100+ | 57 | +0.0052 ±0.0405 | +0.0033 ±0.0174 | +0.1 | 0.632 | 0.579 | |
| kalshi favorite 0.5-0.6 | 325 | -0.0251 ±0.0095 | -0.0118 ±0.0045 | -2.6 | 0.482 | 0.526 | |
| kalshi favorite 0.6-0.7 | 312 | +0.0022 ±0.0102 | +0.0018 ±0.0047 | +0.2 | 0.619 | 0.603 | |
| kalshi favorite 0.7-0.8 | 256 | +0.0014 ±0.0103 | +0.0007 ±0.0042 | +0.1 | 0.729 | 0.727 | |
| kalshi favorite 0.8-0.9 | 147 | +0.0173 ±0.0203 | +0.0061 ±0.0072 | +0.9 | 0.830 | 0.823 | |
| kalshi favorite 0.9-1.0 | 65 | +0.0227 ±0.0394 | +0.0026 ±0.0100 | +0.6 | 0.938 | 0.923 | |
| surface: Hard | 255 | -0.0044 ±0.0114 | -0.0008 ±0.0047 | -0.4 | 0.616 | 0.598 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 332 | -0.0048 ±0.0119 | -0.0030 ±0.0050 | -0.4 | 0.596 | 0.607 | |
| tier: atp500 | 204 | -0.0077 ±0.0100 | -0.0039 ±0.0045 | -0.8 | 0.613 | 0.610 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 344 | -0.0045 ±0.0122 | -0.0034 ±0.0045 | -0.4 | 0.705 | 0.718 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| round early (R128-R64) | 444 | -0.0060 ±0.0099 | -0.0028 ±0.0039 | -0.6 | 0.699 | 0.706 | |
| round late (QF-F) | 137 | +0.0031 ±0.0122 | +0.0006 ±0.0053 | +0.3 | 0.628 | 0.613 | |
| round mid (R32-R16) | 502 | -0.0015 ±0.0088 | -0.0016 ±0.0037 | -0.2 | 0.621 | 0.630 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 241 | -0.0055 ±0.0106 | -0.0019 ±0.0044 | -0.5 | 0.610 | 0.595 | |
| agree (<0.05) | 589 | -0.0006 ±0.0030 | -0.0010 ±0.0010 | -0.2 | 0.691 | 0.687 | |
| mild disagree (0.05-0.10) | 338 | -0.0071 ±0.0101 | -0.0037 ±0.0038 | -0.7 | 0.605 | 0.636 | |
| big disagree (>=0.1) | 178 | -0.0019 ±0.0295 | -0.0012 ±0.0126 | -0.1 | 0.604 | 0.598 | |
| tour: atp | 544 | +0.0018 ±0.0081 | -0.0002 ±0.0032 | +0.2 | 0.632 | 0.652 | |
| tour: wta | 561 | -0.0073 ±0.0085 | -0.0034 ±0.0035 | -0.9 | 0.668 | 0.662 | |

When they disagree by >= 0.1: model closer to the outcome in **76/178** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 11 | 0.067 | 0.091 |
| 0.1-0.2 | 65 | 0.154 | 0.138 |
| 0.2-0.3 | 95 | 0.254 | 0.263 |
| 0.3-0.4 | 151 | 0.354 | 0.364 |
| 0.4-0.5 | 200 | 0.450 | 0.495 |
| 0.5-0.6 | 183 | 0.551 | 0.536 |
| 0.6-0.7 | 167 | 0.646 | 0.617 |
| 0.7-0.8 | 132 | 0.749 | 0.758 |
| 0.8-0.9 | 72 | 0.847 | 0.819 |
| 0.9-1.0 | 29 | 0.928 | 0.897 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 25 | 0.060 | 0.080 |
| 0.1-0.2 | 61 | 0.153 | 0.148 |
| 0.2-0.3 | 111 | 0.255 | 0.288 |
| 0.3-0.4 | 145 | 0.354 | 0.393 |
| 0.4-0.5 | 169 | 0.444 | 0.473 |
| 0.5-0.6 | 158 | 0.555 | 0.519 |
| 0.6-0.7 | 165 | 0.648 | 0.606 |
| 0.7-0.8 | 145 | 0.747 | 0.738 |
| 0.8-0.9 | 87 | 0.846 | 0.805 |
| 0.9-1.0 | 39 | 0.930 | 0.923 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 219 | +0.0285 ±0.0124 | +0.0075 ±0.0037 | +2.3 | 0.717 | 0.712 | |
| top-20 involved | 374 | +0.0095 ±0.0089 | +0.0017 ±0.0029 | +1.1 | 0.713 | 0.713 | |
| kalshi favorite 0.8-0.9 | 147 | +0.0173 ±0.0203 | +0.0061 ±0.0072 | +0.9 | 0.830 | 0.823 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| kalshi favorite 0.9-1.0 | 65 | +0.0227 ±0.0394 | +0.0026 ±0.0100 | +0.6 | 0.938 | 0.923 | |
| both inside top-50 | 245 | +0.0056 ±0.0105 | +0.0020 ±0.0045 | +0.5 | 0.643 | 0.635 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| round late (QF-F) | 137 | +0.0031 ±0.0122 | +0.0006 ±0.0053 | +0.3 | 0.628 | 0.613 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| tier: atp500 | 204 | -0.0077 ±0.0100 | -0.0039 ±0.0045 | -0.8 | 0.613 | 0.610 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tour: wta | 561 | -0.0073 ±0.0085 | -0.0034 ±0.0035 | -0.9 | 0.668 | 0.662 | |
| no top-20 player | 731 | -0.0091 ±0.0076 | -0.0036 ±0.0033 | -1.2 | 0.619 | 0.629 | |
| best rank 11-20 | 155 | -0.0174 ±0.0120 | -0.0066 ±0.0047 | -1.4 | 0.706 | 0.713 | |
| pred_source: live aligned | 189 | -0.0172 ±0.0116 | -0.0062 ±0.0048 | -1.5 | 0.614 | 0.606 | |
| best rank 21-50 | 400 | -0.0129 ±0.0086 | -0.0050 ±0.0038 | -1.5 | 0.637 | 0.669 | |
| kalshi favorite 0.5-0.6 | 325 | -0.0251 ±0.0095 | -0.0118 ±0.0045 | -2.6 | 0.482 | 0.526 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1105, mean |Δ|=0.0019, p95=0.0094, >0.05 in 2 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0099 (n=241, >0.05: 1)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1105, d_ll -0.0028 ±0.0059 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 512 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 55, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Cincinnati': 1, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): Akasha Urhobo, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari, Carson Branstine, Casper Ruud, Caty McNally
