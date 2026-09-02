# Model vs Kalshi — match-by-match scorecard

_Generated 2026-09-02T10:06:21Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1765 | 1660 | 40 | 8 | 57 | 0 | 11 | 19 | 70 | 2026-05-03..2026-09-03 |
| wta | 1754 | 1023 | 34 | 655 | 42 | 0 | 7 | 15 | 47 | 2026-05-02..2026-09-03 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1131 | 0.6070 | 0.6043 | -0.0027 ±0.0058 | -0.0017 ±0.0024 | 0.654 | 0.661 |
| atp | 555 | 0.6252 | 0.6264 | +0.0012 ±0.0080 | -0.0004 ±0.0032 | 0.636 | 0.653 |
| wta | 576 | 0.5894 | 0.5830 | -0.0064 ±0.0084 | -0.0031 ±0.0035 | 0.672 | 0.669 |
| pooled/live_aligned | 215 | 0.6104 | 0.5957 | -0.0147 ±0.0110 | -0.0051 ±0.0046 | 0.637 | 0.635 |
| pooled/backtest | 916 | 0.6061 | 0.6063 | +0.0002 ±0.0067 | -0.0009 ±0.0027 | 0.658 | 0.668 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 215 | -0.0147 ±0.0110 | -0.0051 ±0.0046 | -1.3 | 0.637 | 0.635 | |
| pred_source: backtest | 916 | +0.0002 ±0.0067 | -0.0009 ±0.0027 | +0.0 | 0.658 | 0.668 | |
| top-20 involved | 384 | +0.0084 ±0.0087 | +0.0014 ±0.0029 | +1.0 | 0.717 | 0.717 | |
| no top-20 player | 747 | -0.0084 ±0.0076 | -0.0034 ±0.0033 | -1.1 | 0.622 | 0.633 | |
| both inside top-50 | 246 | +0.0052 ±0.0104 | +0.0019 ±0.0045 | +0.5 | 0.644 | 0.636 | |
| someone outside top-50 | 885 | -0.0048 ±0.0068 | -0.0027 ±0.0027 | -0.7 | 0.657 | 0.668 | |
| best rank 1-10 | 225 | +0.0274 ±0.0120 | +0.0073 ±0.0036 | +2.3 | 0.724 | 0.720 | |
| best rank 11-20 | 159 | -0.0183 ±0.0120 | -0.0069 ±0.0047 | -1.5 | 0.708 | 0.714 | |
| best rank 21-50 | 406 | -0.0109 ±0.0086 | -0.0041 ±0.0038 | -1.3 | 0.643 | 0.674 | |
| best rank 51-100 | 282 | -0.0061 ±0.0135 | -0.0029 ±0.0057 | -0.5 | 0.594 | 0.585 | |
| best rank 100+ | 59 | -0.0016 ±0.0395 | +0.0001 ±0.0170 | -0.0 | 0.610 | 0.576 | |
| kalshi favorite 0.5-0.6 | 330 | -0.0221 ±0.0096 | -0.0104 ±0.0045 | -2.3 | 0.486 | 0.530 | |
| kalshi favorite 0.6-0.7 | 317 | +0.0016 ±0.0102 | +0.0014 ±0.0046 | +0.2 | 0.621 | 0.609 | |
| kalshi favorite 0.7-0.8 | 263 | +0.0007 ±0.0101 | +0.0003 ±0.0041 | +0.1 | 0.728 | 0.726 | |
| kalshi favorite 0.8-0.9 | 151 | +0.0144 ±0.0200 | +0.0053 ±0.0071 | +0.7 | 0.828 | 0.821 | |
| kalshi favorite 0.9-1.0 | 70 | +0.0200 ±0.0366 | +0.0022 ±0.0093 | +0.5 | 0.943 | 0.929 | |
| surface: Hard | 281 | -0.0037 ±0.0109 | -0.0005 ±0.0045 | -0.3 | 0.633 | 0.621 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 332 | -0.0048 ±0.0119 | -0.0030 ±0.0050 | -0.4 | 0.596 | 0.607 | |
| tier: atp500 | 204 | -0.0077 ±0.0100 | -0.0039 ±0.0045 | -0.8 | 0.613 | 0.610 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 370 | -0.0040 ±0.0116 | -0.0029 ±0.0043 | -0.3 | 0.712 | 0.727 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| round early (R128-R64) | 470 | -0.0055 ±0.0096 | -0.0025 ±0.0037 | -0.6 | 0.705 | 0.714 | |
| round late (QF-F) | 137 | +0.0031 ±0.0122 | +0.0006 ±0.0053 | +0.3 | 0.628 | 0.613 | |
| round mid (R32-R16) | 502 | -0.0015 ±0.0088 | -0.0016 ±0.0037 | -0.2 | 0.621 | 0.630 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 265 | -0.0050 ±0.0102 | -0.0016 ±0.0043 | -0.5 | 0.626 | 0.617 | |
| month 2026-09 | 2 | +0.0405 ±0.0097 | +0.0173 ±0.0077 | +4.2 | 1.000 | 1.000 | ⚠ small n |
| agree (<0.05) | 604 | -0.0007 ±0.0030 | -0.0010 ±0.0010 | -0.2 | 0.697 | 0.693 | |
| mild disagree (0.05-0.10) | 344 | -0.0092 ±0.0100 | -0.0044 ±0.0038 | -0.9 | 0.603 | 0.637 | |
| big disagree (>=0.1) | 183 | +0.0033 ±0.0290 | +0.0007 ±0.0124 | +0.1 | 0.609 | 0.604 | |
| tour: atp | 555 | +0.0012 ±0.0080 | -0.0004 ±0.0032 | +0.2 | 0.636 | 0.653 | |
| tour: wta | 576 | -0.0064 ±0.0084 | -0.0031 ±0.0035 | -0.8 | 0.672 | 0.669 | |

When they disagree by >= 0.1: model closer to the outcome in **80/183** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 12 | 0.066 | 0.083 |
| 0.1-0.2 | 67 | 0.153 | 0.134 |
| 0.2-0.3 | 98 | 0.255 | 0.255 |
| 0.3-0.4 | 152 | 0.354 | 0.362 |
| 0.4-0.5 | 201 | 0.450 | 0.493 |
| 0.5-0.6 | 188 | 0.551 | 0.537 |
| 0.6-0.7 | 168 | 0.646 | 0.619 |
| 0.7-0.8 | 135 | 0.749 | 0.748 |
| 0.8-0.9 | 77 | 0.848 | 0.818 |
| 0.9-1.0 | 33 | 0.928 | 0.909 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 27 | 0.060 | 0.074 |
| 0.1-0.2 | 62 | 0.152 | 0.145 |
| 0.2-0.3 | 114 | 0.256 | 0.281 |
| 0.3-0.4 | 147 | 0.354 | 0.388 |
| 0.4-0.5 | 170 | 0.444 | 0.471 |
| 0.5-0.6 | 162 | 0.554 | 0.525 |
| 0.6-0.7 | 168 | 0.648 | 0.613 |
| 0.7-0.8 | 149 | 0.748 | 0.732 |
| 0.8-0.9 | 90 | 0.845 | 0.800 |
| 0.9-1.0 | 42 | 0.931 | 0.929 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 225 | +0.0274 ±0.0120 | +0.0073 ±0.0036 | +2.3 | 0.724 | 0.720 | |
| top-20 involved | 384 | +0.0084 ±0.0087 | +0.0014 ±0.0029 | +1.0 | 0.717 | 0.717 | |
| kalshi favorite 0.8-0.9 | 151 | +0.0144 ±0.0200 | +0.0053 ±0.0071 | +0.7 | 0.828 | 0.821 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| kalshi favorite 0.9-1.0 | 70 | +0.0200 ±0.0366 | +0.0022 ±0.0093 | +0.5 | 0.943 | 0.929 | |
| both inside top-50 | 246 | +0.0052 ±0.0104 | +0.0019 ±0.0045 | +0.5 | 0.644 | 0.636 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| round late (QF-F) | 137 | +0.0031 ±0.0122 | +0.0006 ±0.0053 | +0.3 | 0.628 | 0.613 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| tier: atp500 | 204 | -0.0077 ±0.0100 | -0.0039 ±0.0045 | -0.8 | 0.613 | 0.610 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| mild disagree (0.05-0.10) | 344 | -0.0092 ±0.0100 | -0.0044 ±0.0038 | -0.9 | 0.603 | 0.637 | |
| no top-20 player | 747 | -0.0084 ±0.0076 | -0.0034 ±0.0033 | -1.1 | 0.622 | 0.633 | |
| best rank 21-50 | 406 | -0.0109 ±0.0086 | -0.0041 ±0.0038 | -1.3 | 0.643 | 0.674 | |
| pred_source: live aligned | 215 | -0.0147 ±0.0110 | -0.0051 ±0.0046 | -1.3 | 0.637 | 0.635 | |
| best rank 11-20 | 159 | -0.0183 ±0.0120 | -0.0069 ±0.0047 | -1.5 | 0.708 | 0.714 | |
| kalshi favorite 0.5-0.6 | 330 | -0.0221 ±0.0096 | -0.0104 ±0.0045 | -2.3 | 0.486 | 0.530 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1131, mean |Δ|=0.0019, p95=0.0091, >0.05 in 2 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0087 (n=265, >0.05: 1) | 2026-09 p95=0.0038 (n=2, >0.05: 0)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1131, d_ll -0.0027 ±0.0058 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 512 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 55, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Cincinnati': 1, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): Akasha Urhobo, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari, Carson Branstine, Casper Ruud, Caty McNally
