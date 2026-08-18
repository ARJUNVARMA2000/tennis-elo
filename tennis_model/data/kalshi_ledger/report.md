# Model vs Kalshi — match-by-match scorecard

_Generated 2026-08-18T06:41:53Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1479 | 1418 | 7 | 8 | 46 | 0 | 10 | 15 | 48 | 2026-05-03..2026-08-18 |
| wta | 1491 | 906 | 8 | 539 | 38 | 0 | 5 | 15 | 24 | 2026-05-02..2026-08-18 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 905 | 0.6055 | 0.6036 | -0.0019 ±0.0067 | -0.0018 ±0.0027 | 0.661 | 0.672 |
| atp | 435 | 0.6141 | 0.6238 | +0.0097 ±0.0095 | +0.0022 ±0.0038 | 0.657 | 0.676 |
| wta | 470 | 0.5975 | 0.5849 | -0.0125 ±0.0094 | -0.0056 ±0.0039 | 0.664 | 0.669 |
| pooled/live_aligned | 0 | | | | | | |
| pooled/backtest | 905 | 0.6055 | 0.6036 | -0.0019 ±0.0067 | -0.0018 ±0.0027 | 0.661 | 0.672 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: backtest | 905 | -0.0019 ±0.0067 | -0.0018 ±0.0027 | -0.3 | 0.661 | 0.672 | |
| top-20 involved | 312 | +0.0102 ±0.0102 | +0.0017 ±0.0033 | +1.0 | 0.713 | 0.716 | |
| no top-20 player | 593 | -0.0082 ±0.0087 | -0.0037 ±0.0037 | -0.9 | 0.633 | 0.649 | |
| both inside top-50 | 194 | +0.0079 ±0.0122 | +0.0027 ±0.0053 | +0.6 | 0.673 | 0.673 | |
| someone outside top-50 | 711 | -0.0045 ±0.0078 | -0.0031 ±0.0031 | -0.6 | 0.658 | 0.672 | |
| best rank 1-10 | 180 | +0.0307 ±0.0146 | +0.0080 ±0.0042 | +2.1 | 0.717 | 0.717 | |
| best rank 11-20 | 132 | -0.0178 ±0.0135 | -0.0069 ±0.0053 | -1.3 | 0.708 | 0.716 | |
| best rank 21-50 | 329 | -0.0139 ±0.0095 | -0.0061 ±0.0043 | -1.5 | 0.638 | 0.678 | |
| best rank 51-100 | 222 | +0.0039 ±0.0157 | +0.0012 ±0.0066 | +0.3 | 0.619 | 0.608 | |
| best rank 100+ | 42 | -0.0275 ±0.0502 | -0.0111 ±0.0215 | -0.5 | 0.667 | 0.643 | ⚠ small n |
| kalshi favorite 0.5-0.6 | 262 | -0.0256 ±0.0107 | -0.0120 ±0.0050 | -2.4 | 0.487 | 0.552 | |
| kalshi favorite 0.6-0.7 | 259 | -0.0019 ±0.0114 | -0.0002 ±0.0052 | -0.2 | 0.637 | 0.622 | |
| kalshi favorite 0.7-0.8 | 210 | +0.0031 ±0.0116 | +0.0013 ±0.0048 | +0.3 | 0.745 | 0.743 | |
| kalshi favorite 0.8-0.9 | 117 | +0.0298 ±0.0236 | +0.0092 ±0.0086 | +1.3 | 0.821 | 0.812 | |
| kalshi favorite 0.9-1.0 | 57 | +0.0244 ±0.0449 | +0.0028 ±0.0114 | +0.5 | 0.930 | 0.912 | |
| surface: Hard | 55 | +0.0053 ±0.0308 | +0.0027 ±0.0126 | +0.2 | 0.655 | 0.636 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 265 | +0.0016 ±0.0143 | -0.0005 ±0.0059 | +0.1 | 0.634 | 0.638 | |
| tier: atp500 | 185 | -0.0127 ±0.0102 | -0.0061 ±0.0046 | -1.2 | 0.611 | 0.624 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 253 | -0.0021 ±0.0148 | -0.0038 ±0.0054 | -0.1 | 0.706 | 0.731 | |
| tier: masters | 201 | +0.0034 ±0.0109 | +0.0026 ±0.0049 | +0.3 | 0.684 | 0.687 | |
| round early (R128-R64) | 334 | -0.0038 ±0.0118 | -0.0027 ±0.0046 | -0.3 | 0.708 | 0.722 | |
| round late (QF-F) | 110 | -0.0040 ±0.0137 | -0.0029 ±0.0059 | -0.3 | 0.655 | 0.645 | |
| round mid (R32-R16) | 439 | +0.0003 ±0.0098 | -0.0009 ±0.0041 | +0.0 | 0.634 | 0.648 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 41 | +0.0020 ±0.0234 | -0.0023 ±0.0099 | +0.1 | 0.634 | 0.634 | ⚠ small n |
| agree (<0.05) | 472 | -0.0013 ±0.0035 | -0.0015 ±0.0011 | -0.4 | 0.710 | 0.707 | |
| mild disagree (0.05-0.10) | 280 | -0.0007 ±0.0110 | -0.0021 ±0.0041 | -0.1 | 0.605 | 0.650 | |
| big disagree (>=0.1) | 153 | -0.0057 ±0.0324 | -0.0026 ±0.0138 | -0.2 | 0.611 | 0.608 | |
| tour: atp | 435 | +0.0097 ±0.0095 | +0.0022 ±0.0038 | +1.0 | 0.657 | 0.676 | |
| tour: wta | 470 | -0.0125 ±0.0094 | -0.0056 ±0.0039 | -1.3 | 0.664 | 0.669 | |

When they disagree by >= 0.1: model closer to the outcome in **62/153** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 9 | 0.065 | 0.111 |
| 0.1-0.2 | 51 | 0.152 | 0.098 |
| 0.2-0.3 | 76 | 0.253 | 0.250 |
| 0.3-0.4 | 126 | 0.353 | 0.341 |
| 0.4-0.5 | 167 | 0.451 | 0.473 |
| 0.5-0.6 | 152 | 0.552 | 0.539 |
| 0.6-0.7 | 142 | 0.646 | 0.641 |
| 0.7-0.8 | 104 | 0.747 | 0.750 |
| 0.8-0.9 | 59 | 0.847 | 0.814 |
| 0.9-1.0 | 19 | 0.923 | 0.895 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 24 | 0.060 | 0.083 |
| 0.1-0.2 | 48 | 0.154 | 0.146 |
| 0.2-0.3 | 92 | 0.253 | 0.272 |
| 0.3-0.4 | 118 | 0.352 | 0.373 |
| 0.4-0.5 | 136 | 0.442 | 0.426 |
| 0.5-0.6 | 128 | 0.556 | 0.523 |
| 0.6-0.7 | 139 | 0.649 | 0.626 |
| 0.7-0.8 | 118 | 0.746 | 0.754 |
| 0.8-0.9 | 69 | 0.846 | 0.783 |
| 0.9-1.0 | 33 | 0.934 | 0.909 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 180 | +0.0307 ±0.0146 | +0.0080 ±0.0042 | +2.1 | 0.717 | 0.717 | |
| kalshi favorite 0.8-0.9 | 117 | +0.0298 ±0.0236 | +0.0092 ±0.0086 | +1.3 | 0.821 | 0.812 | |
| tour: atp | 435 | +0.0097 ±0.0095 | +0.0022 ±0.0038 | +1.0 | 0.657 | 0.676 | |
| top-20 involved | 312 | +0.0102 ±0.0102 | +0.0017 ±0.0033 | +1.0 | 0.713 | 0.716 | |
| both inside top-50 | 194 | +0.0079 ±0.0122 | +0.0027 ±0.0053 | +0.6 | 0.673 | 0.673 | |
| kalshi favorite 0.9-1.0 | 57 | +0.0244 ±0.0449 | +0.0028 ±0.0114 | +0.5 | 0.930 | 0.912 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| tier: masters | 201 | +0.0034 ±0.0109 | +0.0026 ±0.0049 | +0.3 | 0.684 | 0.687 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| no top-20 player | 593 | -0.0082 ±0.0087 | -0.0037 ±0.0037 | -0.9 | 0.633 | 0.649 | |
| tier: atp500 | 185 | -0.0127 ±0.0102 | -0.0061 ±0.0046 | -1.2 | 0.611 | 0.624 | |
| best rank 11-20 | 132 | -0.0178 ±0.0135 | -0.0069 ±0.0053 | -1.3 | 0.708 | 0.716 | |
| tour: wta | 470 | -0.0125 ±0.0094 | -0.0056 ±0.0039 | -1.3 | 0.664 | 0.669 | |
| best rank 21-50 | 329 | -0.0139 ±0.0095 | -0.0061 ±0.0043 | -1.5 | 0.638 | 0.678 | |
| kalshi favorite 0.5-0.6 | 262 | -0.0256 ±0.0107 | -0.0120 ±0.0050 | -2.4 | 0.487 | 0.552 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=905, mean |Δ|=0.0021, p95=0.0099, >0.05 in 2 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0212 (n=41, >0.05: 1)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=905, d_ll -0.0019 ±0.0067 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 450 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Cincinnati': 2, 'ATP Mallorca': 1, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Alexandra Eala, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Carolyn Ansari, Casper Ruud, Caty McNally, Celine Naef, Chloe Paquet, Claire Liu, Clervie Ngounoue, Dalma Galfi, Daphnee Mpetshi Perricard
