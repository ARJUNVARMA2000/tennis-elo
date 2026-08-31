# Model vs Kalshi — match-by-match scorecard

_Generated 2026-08-31T12:17:37Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1741 | 1623 | 54 | 8 | 56 | 0 | 11 | 19 | 49 | 2026-05-03..2026-09-02 |
| wta | 1726 | 980 | 50 | 655 | 41 | 0 | 7 | 15 | 32 | 2026-05-02..2026-09-02 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1051 | 0.6122 | 0.6110 | -0.0011 ±0.0061 | -0.0013 ±0.0025 | 0.646 | 0.654 |
| atp | 518 | 0.6302 | 0.6335 | +0.0033 ±0.0084 | -0.0000 ±0.0034 | 0.627 | 0.650 |
| wta | 533 | 0.5946 | 0.5892 | -0.0054 ±0.0088 | -0.0026 ±0.0036 | 0.664 | 0.658 |
| pooled/live_aligned | 135 | 0.6531 | 0.6431 | -0.0100 ±0.0136 | -0.0039 ±0.0060 | 0.563 | 0.559 |
| pooled/backtest | 916 | 0.6061 | 0.6063 | +0.0002 ±0.0067 | -0.0009 ±0.0027 | 0.658 | 0.668 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 135 | -0.0100 ±0.0136 | -0.0039 ±0.0060 | -0.7 | 0.563 | 0.559 | |
| pred_source: backtest | 916 | +0.0002 ±0.0067 | -0.0009 ±0.0027 | +0.0 | 0.658 | 0.668 | |
| top-20 involved | 358 | +0.0076 ±0.0092 | +0.0010 ±0.0030 | +0.8 | 0.703 | 0.703 | |
| no top-20 player | 693 | -0.0057 ±0.0079 | -0.0025 ±0.0034 | -0.7 | 0.617 | 0.628 | |
| both inside top-50 | 239 | +0.0073 ±0.0106 | +0.0027 ±0.0046 | +0.7 | 0.642 | 0.634 | |
| someone outside top-50 | 812 | -0.0036 ±0.0072 | -0.0025 ±0.0029 | -0.5 | 0.647 | 0.659 | |
| best rank 1-10 | 211 | +0.0272 ±0.0128 | +0.0072 ±0.0038 | +2.1 | 0.711 | 0.706 | |
| best rank 11-20 | 147 | -0.0205 ±0.0125 | -0.0079 ±0.0049 | -1.6 | 0.690 | 0.697 | |
| best rank 21-50 | 377 | -0.0103 ±0.0087 | -0.0045 ±0.0039 | -1.2 | 0.631 | 0.664 | |
| best rank 51-100 | 262 | -0.0026 ±0.0143 | -0.0016 ±0.0060 | -0.2 | 0.590 | 0.584 | |
| best rank 100+ | 54 | +0.0117 ±0.0425 | +0.0064 ±0.0182 | +0.3 | 0.648 | 0.593 | |
| kalshi favorite 0.5-0.6 | 316 | -0.0261 ±0.0097 | -0.0122 ±0.0046 | -2.7 | 0.476 | 0.525 | |
| kalshi favorite 0.6-0.7 | 302 | +0.0042 ±0.0105 | +0.0027 ±0.0048 | +0.4 | 0.616 | 0.599 | |
| kalshi favorite 0.7-0.8 | 238 | +0.0049 ±0.0106 | +0.0021 ±0.0043 | +0.5 | 0.737 | 0.735 | |
| kalshi favorite 0.8-0.9 | 133 | +0.0240 ±0.0217 | +0.0076 ±0.0079 | +1.1 | 0.820 | 0.812 | |
| kalshi favorite 0.9-1.0 | 62 | +0.0234 ±0.0413 | +0.0027 ±0.0105 | +0.6 | 0.935 | 0.919 | |
| surface: Hard | 201 | +0.0039 ±0.0132 | +0.0022 ±0.0056 | +0.3 | 0.582 | 0.565 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 332 | -0.0048 ±0.0119 | -0.0030 ±0.0050 | -0.4 | 0.596 | 0.607 | |
| tier: atp500 | 204 | -0.0077 ±0.0100 | -0.0039 ±0.0045 | -0.8 | 0.613 | 0.610 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 290 | +0.0012 ±0.0139 | -0.0017 ±0.0052 | +0.1 | 0.698 | 0.717 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| round early (R128-R64) | 390 | -0.0019 ±0.0109 | -0.0015 ±0.0043 | -0.2 | 0.694 | 0.704 | |
| round late (QF-F) | 137 | +0.0031 ±0.0122 | +0.0006 ±0.0053 | +0.3 | 0.628 | 0.613 | |
| round mid (R32-R16) | 502 | -0.0015 ±0.0088 | -0.0016 ±0.0037 | -0.2 | 0.621 | 0.630 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 187 | +0.0030 ±0.0120 | +0.0010 ±0.0052 | +0.3 | 0.572 | 0.559 | |
| agree (<0.05) | 554 | +0.0002 ±0.0032 | -0.0006 ±0.0010 | +0.1 | 0.684 | 0.681 | |
| mild disagree (0.05-0.10) | 324 | -0.0018 ±0.0100 | -0.0021 ±0.0038 | -0.2 | 0.610 | 0.642 | |
| big disagree (>=0.1) | 173 | -0.0043 ±0.0303 | -0.0020 ±0.0129 | -0.1 | 0.592 | 0.587 | |
| tour: atp | 518 | +0.0033 ±0.0084 | -0.0000 ±0.0034 | +0.4 | 0.627 | 0.650 | |
| tour: wta | 533 | -0.0054 ±0.0088 | -0.0026 ±0.0036 | -0.6 | 0.664 | 0.658 | |

When they disagree by >= 0.1: model closer to the outcome in **72/173** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 11 | 0.067 | 0.091 |
| 0.1-0.2 | 57 | 0.153 | 0.123 |
| 0.2-0.3 | 90 | 0.253 | 0.256 |
| 0.3-0.4 | 147 | 0.354 | 0.367 |
| 0.4-0.5 | 195 | 0.450 | 0.497 |
| 0.5-0.6 | 176 | 0.551 | 0.523 |
| 0.6-0.7 | 163 | 0.645 | 0.620 |
| 0.7-0.8 | 123 | 0.748 | 0.764 |
| 0.8-0.9 | 66 | 0.847 | 0.803 |
| 0.9-1.0 | 23 | 0.925 | 0.913 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 25 | 0.060 | 0.080 |
| 0.1-0.2 | 57 | 0.155 | 0.158 |
| 0.2-0.3 | 103 | 0.255 | 0.282 |
| 0.3-0.4 | 138 | 0.353 | 0.391 |
| 0.4-0.5 | 165 | 0.443 | 0.473 |
| 0.5-0.6 | 153 | 0.555 | 0.516 |
| 0.6-0.7 | 162 | 0.648 | 0.599 |
| 0.7-0.8 | 135 | 0.747 | 0.748 |
| 0.8-0.9 | 77 | 0.846 | 0.792 |
| 0.9-1.0 | 36 | 0.932 | 0.917 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 211 | +0.0272 ±0.0128 | +0.0072 ±0.0038 | +2.1 | 0.711 | 0.706 | |
| kalshi favorite 0.8-0.9 | 133 | +0.0240 ±0.0217 | +0.0076 ±0.0079 | +1.1 | 0.820 | 0.812 | |
| top-20 involved | 358 | +0.0076 ±0.0092 | +0.0010 ±0.0030 | +0.8 | 0.703 | 0.703 | |
| both inside top-50 | 239 | +0.0073 ±0.0106 | +0.0027 ±0.0046 | +0.7 | 0.642 | 0.634 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| kalshi favorite 0.9-1.0 | 62 | +0.0234 ±0.0413 | +0.0027 ±0.0105 | +0.6 | 0.935 | 0.919 | |
| kalshi favorite 0.7-0.8 | 238 | +0.0049 ±0.0106 | +0.0021 ±0.0043 | +0.5 | 0.737 | 0.735 | |
| kalshi favorite 0.6-0.7 | 302 | +0.0042 ±0.0105 | +0.0027 ±0.0048 | +0.4 | 0.616 | 0.599 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| no top-20 player | 693 | -0.0057 ±0.0079 | -0.0025 ±0.0034 | -0.7 | 0.617 | 0.628 | |
| pred_source: live aligned | 135 | -0.0100 ±0.0136 | -0.0039 ±0.0060 | -0.7 | 0.563 | 0.559 | |
| tier: atp500 | 204 | -0.0077 ±0.0100 | -0.0039 ±0.0045 | -0.8 | 0.613 | 0.610 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| best rank 21-50 | 377 | -0.0103 ±0.0087 | -0.0045 ±0.0039 | -1.2 | 0.631 | 0.664 | |
| best rank 11-20 | 147 | -0.0205 ±0.0125 | -0.0079 ±0.0049 | -1.6 | 0.690 | 0.697 | |
| kalshi favorite 0.5-0.6 | 316 | -0.0261 ±0.0097 | -0.0122 ±0.0046 | -2.7 | 0.476 | 0.525 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1051, mean |Δ|=0.0020, p95=0.0098, >0.05 in 2 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0102 (n=187, >0.05: 1)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1051, d_ll -0.0011 ±0.0061 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 512 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 55, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Cincinnati': 1, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): Akasha Urhobo, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari, Carson Branstine, Casper Ruud, Caty McNally
