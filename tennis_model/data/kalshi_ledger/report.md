# Model vs Kalshi — match-by-match scorecard

_Generated 2026-09-03T10:39:05Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1778 | 1683 | 26 | 12 | 57 | 0 | 11 | 19 | 58 | 2026-05-03..2026-09-04 |
| wta | 1765 | 1044 | 24 | 655 | 42 | 0 | 7 | 15 | 31 | 2026-05-02..2026-09-04 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1175 | 0.6014 | 0.5964 | -0.0050 ±0.0057 | -0.0027 ±0.0023 | 0.661 | 0.670 |
| atp | 578 | 0.6189 | 0.6193 | +0.0003 ±0.0077 | -0.0008 ±0.0031 | 0.644 | 0.662 |
| wta | 597 | 0.5845 | 0.5743 | -0.0101 ±0.0083 | -0.0046 ±0.0034 | 0.678 | 0.678 |
| pooled/live_aligned | 258 | 0.5862 | 0.5634 | -0.0228 ±0.0102 | -0.0090 ±0.0042 | 0.671 | 0.676 |
| pooled/backtest | 917 | 0.6057 | 0.6057 | +0.0000 ±0.0067 | -0.0010 ±0.0027 | 0.659 | 0.668 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 258 | -0.0228 ±0.0102 | -0.0090 ±0.0042 | -2.2 | 0.671 | 0.676 | |
| pred_source: backtest | 917 | +0.0000 ±0.0067 | -0.0010 ±0.0027 | +0.0 | 0.659 | 0.668 | |
| top-20 involved | 402 | +0.0079 ±0.0084 | +0.0012 ±0.0028 | +0.9 | 0.728 | 0.728 | |
| no top-20 player | 773 | -0.0117 ±0.0074 | -0.0048 ±0.0032 | -1.6 | 0.627 | 0.640 | |
| both inside top-50 | 256 | +0.0028 ±0.0102 | +0.0010 ±0.0044 | +0.3 | 0.646 | 0.639 | |
| someone outside top-50 | 919 | -0.0072 ±0.0067 | -0.0038 ±0.0027 | -1.1 | 0.665 | 0.678 | |
| best rank 1-10 | 235 | +0.0258 ±0.0116 | +0.0067 ±0.0034 | +2.2 | 0.736 | 0.732 | |
| best rank 11-20 | 167 | -0.0174 ±0.0117 | -0.0065 ±0.0046 | -1.5 | 0.716 | 0.722 | |
| best rank 21-50 | 423 | -0.0144 ±0.0083 | -0.0056 ±0.0037 | -1.7 | 0.648 | 0.680 | |
| best rank 51-100 | 291 | -0.0098 ±0.0134 | -0.0045 ±0.0057 | -0.7 | 0.600 | 0.595 | |
| best rank 100+ | 59 | -0.0016 ±0.0395 | +0.0001 ±0.0170 | -0.0 | 0.610 | 0.576 | |
| kalshi favorite 0.5-0.6 | 341 | -0.0253 ±0.0096 | -0.0119 ±0.0045 | -2.6 | 0.491 | 0.540 | |
| kalshi favorite 0.6-0.7 | 328 | +0.0001 ±0.0100 | +0.0006 ±0.0046 | +0.0 | 0.625 | 0.613 | |
| kalshi favorite 0.7-0.8 | 273 | -0.0016 ±0.0098 | -0.0007 ±0.0040 | -0.2 | 0.738 | 0.736 | |
| kalshi favorite 0.8-0.9 | 156 | +0.0123 ±0.0194 | +0.0045 ±0.0069 | +0.6 | 0.833 | 0.827 | |
| kalshi favorite 0.9-1.0 | 77 | +0.0164 ±0.0333 | +0.0016 ±0.0085 | +0.5 | 0.948 | 0.935 | |
| surface: Hard | 325 | -0.0120 ±0.0100 | -0.0043 ±0.0042 | -1.2 | 0.662 | 0.657 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 332 | -0.0048 ±0.0119 | -0.0030 ±0.0050 | -0.4 | 0.596 | 0.607 | |
| tier: atp500 | 204 | -0.0077 ±0.0100 | -0.0039 ±0.0045 | -0.8 | 0.613 | 0.610 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 414 | -0.0105 ±0.0107 | -0.0056 ±0.0041 | -1.0 | 0.726 | 0.744 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| round early (R128-R64) | 514 | -0.0105 ±0.0090 | -0.0047 ±0.0036 | -1.2 | 0.717 | 0.729 | |
| round late (QF-F) | 137 | +0.0031 ±0.0122 | +0.0006 ±0.0053 | +0.3 | 0.628 | 0.613 | |
| round mid (R32-R16) | 502 | -0.0015 ±0.0088 | -0.0016 ±0.0037 | -0.2 | 0.621 | 0.630 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 278 | -0.0117 ±0.0104 | -0.0044 ±0.0043 | -1.1 | 0.629 | 0.628 | |
| month 2026-09 | 33 | -0.0258 ±0.0175 | -0.0125 ±0.0076 | -1.5 | 0.909 | 0.909 | ⚠ small n |
| agree (<0.05) | 627 | -0.0004 ±0.0029 | -0.0009 ±0.0009 | -0.1 | 0.707 | 0.703 | |
| mild disagree (0.05-0.10) | 357 | -0.0116 ±0.0097 | -0.0053 ±0.0037 | -1.2 | 0.606 | 0.644 | |
| big disagree (>=0.1) | 191 | -0.0076 ±0.0283 | -0.0040 ±0.0121 | -0.3 | 0.615 | 0.610 | |
| tour: atp | 578 | +0.0003 ±0.0077 | -0.0008 ±0.0031 | +0.0 | 0.644 | 0.662 | |
| tour: wta | 597 | -0.0101 ±0.0083 | -0.0046 ±0.0034 | -1.2 | 0.678 | 0.678 | |

When they disagree by >= 0.1: model closer to the outcome in **81/191** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 12 | 0.066 | 0.083 |
| 0.1-0.2 | 69 | 0.153 | 0.130 |
| 0.2-0.3 | 102 | 0.254 | 0.255 |
| 0.3-0.4 | 156 | 0.354 | 0.359 |
| 0.4-0.5 | 210 | 0.450 | 0.481 |
| 0.5-0.6 | 192 | 0.551 | 0.542 |
| 0.6-0.7 | 175 | 0.647 | 0.629 |
| 0.7-0.8 | 140 | 0.750 | 0.750 |
| 0.8-0.9 | 80 | 0.847 | 0.825 |
| 0.9-1.0 | 39 | 0.931 | 0.923 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 29 | 0.060 | 0.069 |
| 0.1-0.2 | 64 | 0.153 | 0.141 |
| 0.2-0.3 | 117 | 0.255 | 0.274 |
| 0.3-0.4 | 151 | 0.353 | 0.391 |
| 0.4-0.5 | 178 | 0.444 | 0.455 |
| 0.5-0.6 | 165 | 0.555 | 0.527 |
| 0.6-0.7 | 175 | 0.648 | 0.623 |
| 0.7-0.8 | 156 | 0.748 | 0.744 |
| 0.8-0.9 | 93 | 0.846 | 0.806 |
| 0.9-1.0 | 47 | 0.931 | 0.936 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 235 | +0.0258 ±0.0116 | +0.0067 ±0.0034 | +2.2 | 0.736 | 0.732 | |
| top-20 involved | 402 | +0.0079 ±0.0084 | +0.0012 ±0.0028 | +0.9 | 0.728 | 0.728 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| kalshi favorite 0.8-0.9 | 156 | +0.0123 ±0.0194 | +0.0045 ±0.0069 | +0.6 | 0.833 | 0.827 | |
| kalshi favorite 0.9-1.0 | 77 | +0.0164 ±0.0333 | +0.0016 ±0.0085 | +0.5 | 0.948 | 0.935 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| both inside top-50 | 256 | +0.0028 ±0.0102 | +0.0010 ±0.0044 | +0.3 | 0.646 | 0.639 | |
| round late (QF-F) | 137 | +0.0031 ±0.0122 | +0.0006 ±0.0053 | +0.3 | 0.628 | 0.613 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| mild disagree (0.05-0.10) | 357 | -0.0116 ±0.0097 | -0.0053 ±0.0037 | -1.2 | 0.606 | 0.644 | |
| tour: wta | 597 | -0.0101 ±0.0083 | -0.0046 ±0.0034 | -1.2 | 0.678 | 0.678 | |
| month 2026-09 | 33 | -0.0258 ±0.0175 | -0.0125 ±0.0076 | -1.5 | 0.909 | 0.909 | ⚠ small n |
| best rank 11-20 | 167 | -0.0174 ±0.0117 | -0.0065 ±0.0046 | -1.5 | 0.716 | 0.722 | |
| no top-20 player | 773 | -0.0117 ±0.0074 | -0.0048 ±0.0032 | -1.6 | 0.627 | 0.640 | |
| best rank 21-50 | 423 | -0.0144 ±0.0083 | -0.0056 ±0.0037 | -1.7 | 0.648 | 0.680 | |
| pred_source: live aligned | 258 | -0.0228 ±0.0102 | -0.0090 ±0.0042 | -2.2 | 0.671 | 0.676 | |
| kalshi favorite 0.5-0.6 | 341 | -0.0253 ±0.0096 | -0.0119 ±0.0045 | -2.6 | 0.491 | 0.540 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1175, mean |Δ|=0.0018, p95=0.0088, >0.05 in 2 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0085 (n=278, >0.05: 1) | 2026-09 p95=0.0016 (n=33, >0.05: 0)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1175, d_ll -0.0050 ±0.0057 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 512 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 59, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Cincinnati': 1, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): Adam Walton, Akasha Urhobo, Aleksandr Shevchenko, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari
