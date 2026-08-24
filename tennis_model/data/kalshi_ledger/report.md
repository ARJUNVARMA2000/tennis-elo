# Model vs Kalshi — match-by-match scorecard

_Generated 2026-08-24T06:53:47Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1591 | 1446 | 89 | 7 | 49 | 0 | 10 | 15 | 113 | 2026-05-03..2026-08-25 |
| wta | 1590 | 931 | 82 | 539 | 38 | 0 | 6 | 15 | 81 | 2026-05-02..2026-08-24 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 956 | 0.6069 | 0.6046 | -0.0023 ±0.0064 | -0.0021 ±0.0026 | 0.656 | 0.667 |
| atp | 463 | 0.6193 | 0.6259 | +0.0066 ±0.0090 | +0.0009 ±0.0036 | 0.646 | 0.665 |
| wta | 493 | 0.5952 | 0.5846 | -0.0106 ±0.0090 | -0.0048 ±0.0037 | 0.665 | 0.668 |
| pooled/live_aligned | 50 | 0.6281 | 0.6161 | -0.0120 ±0.0151 | -0.0069 ±0.0070 | 0.580 | 0.580 |
| pooled/backtest | 906 | 0.6057 | 0.6039 | -0.0018 ±0.0067 | -0.0018 ±0.0027 | 0.660 | 0.672 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 50 | -0.0120 ±0.0151 | -0.0069 ±0.0070 | -0.8 | 0.580 | 0.580 | |
| pred_source: backtest | 906 | -0.0018 ±0.0067 | -0.0018 ±0.0027 | -0.3 | 0.660 | 0.672 | |
| top-20 involved | 350 | +0.0096 ±0.0093 | +0.0016 ±0.0031 | +1.0 | 0.701 | 0.701 | |
| no top-20 player | 606 | -0.0092 ±0.0085 | -0.0042 ±0.0037 | -1.1 | 0.630 | 0.647 | |
| both inside top-50 | 231 | +0.0067 ±0.0106 | +0.0021 ±0.0046 | +0.6 | 0.652 | 0.647 | |
| someone outside top-50 | 725 | -0.0052 ±0.0077 | -0.0034 ±0.0031 | -0.7 | 0.657 | 0.673 | |
| best rank 1-10 | 206 | +0.0292 ±0.0130 | +0.0079 ±0.0038 | +2.2 | 0.709 | 0.704 | |
| best rank 11-20 | 144 | -0.0184 ±0.0126 | -0.0074 ±0.0050 | -1.5 | 0.691 | 0.698 | |
| best rank 21-50 | 335 | -0.0144 ±0.0094 | -0.0063 ±0.0042 | -1.5 | 0.636 | 0.675 | |
| best rank 51-100 | 229 | +0.0018 ±0.0154 | +0.0002 ±0.0065 | +0.1 | 0.614 | 0.607 | |
| best rank 100+ | 42 | -0.0275 ±0.0502 | -0.0111 ±0.0215 | -0.5 | 0.667 | 0.643 | ⚠ small n |
| kalshi favorite 0.5-0.6 | 278 | -0.0265 ±0.0102 | -0.0125 ±0.0048 | -2.6 | 0.480 | 0.538 | |
| kalshi favorite 0.6-0.7 | 273 | -0.0025 ±0.0109 | -0.0005 ±0.0050 | -0.2 | 0.626 | 0.615 | |
| kalshi favorite 0.7-0.8 | 224 | +0.0044 ±0.0109 | +0.0017 ±0.0045 | +0.4 | 0.748 | 0.746 | |
| kalshi favorite 0.8-0.9 | 122 | +0.0284 ±0.0227 | +0.0088 ±0.0083 | +1.3 | 0.820 | 0.811 | |
| kalshi favorite 0.9-1.0 | 59 | +0.0242 ±0.0434 | +0.0028 ±0.0110 | +0.6 | 0.932 | 0.915 | |
| surface: Hard | 106 | -0.0021 ±0.0175 | -0.0014 ±0.0073 | -0.1 | 0.613 | 0.604 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 292 | -0.0029 ±0.0131 | -0.0025 ±0.0055 | -0.2 | 0.620 | 0.627 | |
| tier: atp500 | 187 | -0.0132 ±0.0101 | -0.0063 ±0.0045 | -1.3 | 0.610 | 0.623 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 253 | -0.0021 ±0.0148 | -0.0038 ±0.0054 | -0.1 | 0.706 | 0.731 | |
| tier: masters | 223 | +0.0068 ±0.0099 | +0.0039 ±0.0044 | +0.7 | 0.684 | 0.682 | |
| round early (R128-R64) | 340 | -0.0048 ±0.0117 | -0.0032 ±0.0045 | -0.4 | 0.701 | 0.718 | |
| round late (QF-F) | 124 | -0.0041 ±0.0126 | -0.0029 ±0.0055 | -0.3 | 0.645 | 0.637 | |
| round mid (R32-R16) | 470 | +0.0002 ±0.0092 | -0.0011 ±0.0038 | +0.0 | 0.633 | 0.644 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 92 | -0.0048 ±0.0132 | -0.0043 ±0.0058 | -0.4 | 0.598 | 0.598 | |
| agree (<0.05) | 502 | -0.0007 ±0.0034 | -0.0012 ±0.0011 | -0.2 | 0.697 | 0.694 | |
| mild disagree (0.05-0.10) | 298 | -0.0008 ±0.0105 | -0.0022 ±0.0040 | -0.1 | 0.612 | 0.651 | |
| big disagree (>=0.1) | 156 | -0.0100 ±0.0319 | -0.0047 ±0.0136 | -0.3 | 0.606 | 0.609 | |
| tour: atp | 463 | +0.0066 ±0.0090 | +0.0009 ±0.0036 | +0.7 | 0.646 | 0.665 | |
| tour: wta | 493 | -0.0106 ±0.0090 | -0.0048 ±0.0037 | -1.2 | 0.665 | 0.668 | |

When they disagree by >= 0.1: model closer to the outcome in **62/156** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 10 | 0.066 | 0.100 |
| 0.1-0.2 | 54 | 0.153 | 0.093 |
| 0.2-0.3 | 79 | 0.253 | 0.253 |
| 0.3-0.4 | 133 | 0.353 | 0.346 |
| 0.4-0.5 | 174 | 0.451 | 0.477 |
| 0.5-0.6 | 160 | 0.552 | 0.525 |
| 0.6-0.7 | 152 | 0.646 | 0.632 |
| 0.7-0.8 | 112 | 0.748 | 0.750 |
| 0.8-0.9 | 61 | 0.846 | 0.803 |
| 0.9-1.0 | 21 | 0.925 | 0.905 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 25 | 0.060 | 0.080 |
| 0.1-0.2 | 50 | 0.153 | 0.140 |
| 0.2-0.3 | 98 | 0.254 | 0.265 |
| 0.3-0.4 | 122 | 0.353 | 0.369 |
| 0.4-0.5 | 146 | 0.443 | 0.445 |
| 0.5-0.6 | 134 | 0.556 | 0.515 |
| 0.6-0.7 | 149 | 0.649 | 0.611 |
| 0.7-0.8 | 126 | 0.746 | 0.754 |
| 0.8-0.9 | 72 | 0.846 | 0.778 |
| 0.9-1.0 | 34 | 0.933 | 0.912 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 206 | +0.0292 ±0.0130 | +0.0079 ±0.0038 | +2.2 | 0.709 | 0.704 | |
| kalshi favorite 0.8-0.9 | 122 | +0.0284 ±0.0227 | +0.0088 ±0.0083 | +1.3 | 0.820 | 0.811 | |
| top-20 involved | 350 | +0.0096 ±0.0093 | +0.0016 ±0.0031 | +1.0 | 0.701 | 0.701 | |
| tour: atp | 463 | +0.0066 ±0.0090 | +0.0009 ±0.0036 | +0.7 | 0.646 | 0.665 | |
| tier: masters | 223 | +0.0068 ±0.0099 | +0.0039 ±0.0044 | +0.7 | 0.684 | 0.682 | |
| both inside top-50 | 231 | +0.0067 ±0.0106 | +0.0021 ±0.0046 | +0.6 | 0.652 | 0.647 | |
| kalshi favorite 0.9-1.0 | 59 | +0.0242 ±0.0434 | +0.0028 ±0.0110 | +0.6 | 0.932 | 0.915 | |
| kalshi favorite 0.7-0.8 | 224 | +0.0044 ±0.0109 | +0.0017 ±0.0045 | +0.4 | 0.748 | 0.746 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 50 | -0.0120 ±0.0151 | -0.0069 ±0.0070 | -0.8 | 0.580 | 0.580 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| no top-20 player | 606 | -0.0092 ±0.0085 | -0.0042 ±0.0037 | -1.1 | 0.630 | 0.647 | |
| tour: wta | 493 | -0.0106 ±0.0090 | -0.0048 ±0.0037 | -1.2 | 0.665 | 0.668 | |
| tier: atp500 | 187 | -0.0132 ±0.0101 | -0.0063 ±0.0045 | -1.3 | 0.610 | 0.623 | |
| best rank 11-20 | 144 | -0.0184 ±0.0126 | -0.0074 ±0.0050 | -1.5 | 0.691 | 0.698 | |
| best rank 21-50 | 335 | -0.0144 ±0.0094 | -0.0063 ±0.0042 | -1.5 | 0.636 | 0.675 | |
| kalshi favorite 0.5-0.6 | 278 | -0.0265 ±0.0102 | -0.0125 ±0.0048 | -2.6 | 0.480 | 0.538 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=956, mean |Δ|=0.0020, p95=0.0097, >0.05 in 2 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0114 (n=92, >0.05: 1)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=956, d_ll -0.0023 ±0.0064 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 450 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Mallorca': 1, 'ATP Cincinnati': 1, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Alexandra Eala, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Carolyn Ansari, Casper Ruud, Caty McNally, Celine Naef, Chloe Paquet, Claire Liu, Clervie Ngounoue, Dalma Galfi, Daphnee Mpetshi Perricard
