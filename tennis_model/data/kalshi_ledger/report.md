# Model vs Kalshi — match-by-match scorecard

_Generated 2026-09-12T10:14:03Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1801 | 1727 | 1 | 16 | 57 | 0 | 11 | 19 | 44 | 2026-05-03..2026-09-13 |
| wta | 1804 | 1090 | 17 | 655 | 42 | 0 | 7 | 15 | 35 | 2026-05-02..2026-09-12 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1263 | 0.5966 | 0.5910 | -0.0056 ±0.0054 | -0.0030 ±0.0022 | 0.668 | 0.676 |
| atp | 621 | 0.6185 | 0.6174 | -0.0012 ±0.0073 | -0.0014 ±0.0029 | 0.649 | 0.666 |
| wta | 642 | 0.5753 | 0.5655 | -0.0098 ±0.0078 | -0.0046 ±0.0032 | 0.687 | 0.686 |
| pooled/live_aligned | 346 | 0.5724 | 0.5521 | -0.0203 ±0.0083 | -0.0085 ±0.0034 | 0.694 | 0.698 |
| pooled/backtest | 917 | 0.6057 | 0.6057 | +0.0000 ±0.0067 | -0.0010 ±0.0027 | 0.659 | 0.668 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 346 | -0.0203 ±0.0083 | -0.0085 ±0.0034 | -2.4 | 0.694 | 0.698 | |
| pred_source: backtest | 917 | +0.0000 ±0.0067 | -0.0010 ±0.0027 | +0.0 | 0.659 | 0.668 | |
| top-20 involved | 464 | +0.0067 ±0.0075 | +0.0009 ±0.0025 | +0.9 | 0.734 | 0.734 | |
| no top-20 player | 799 | -0.0127 ±0.0073 | -0.0053 ±0.0031 | -1.7 | 0.630 | 0.643 | |
| both inside top-50 | 310 | +0.0005 ±0.0089 | -0.0006 ±0.0039 | +0.1 | 0.663 | 0.656 | |
| someone outside top-50 | 953 | -0.0075 ±0.0065 | -0.0038 ±0.0026 | -1.2 | 0.670 | 0.683 | |
| best rank 1-10 | 280 | +0.0214 ±0.0102 | +0.0053 ±0.0031 | +2.1 | 0.743 | 0.739 | |
| best rank 11-20 | 184 | -0.0157 ±0.0107 | -0.0058 ±0.0042 | -1.5 | 0.720 | 0.726 | |
| best rank 21-50 | 446 | -0.0167 ±0.0081 | -0.0069 ±0.0035 | -2.1 | 0.652 | 0.685 | |
| best rank 51-100 | 294 | -0.0088 ±0.0133 | -0.0041 ±0.0056 | -0.7 | 0.600 | 0.592 | |
| best rank 100+ | 59 | -0.0016 ±0.0395 | +0.0001 ±0.0170 | -0.0 | 0.610 | 0.576 | |
| kalshi favorite 0.5-0.6 | 357 | -0.0246 ±0.0093 | -0.0116 ±0.0043 | -2.7 | 0.497 | 0.538 | |
| kalshi favorite 0.6-0.7 | 347 | -0.0031 ±0.0097 | -0.0010 ±0.0044 | -0.3 | 0.628 | 0.622 | |
| kalshi favorite 0.7-0.8 | 296 | -0.0030 ±0.0094 | -0.0011 ±0.0038 | -0.3 | 0.738 | 0.736 | |
| kalshi favorite 0.8-0.9 | 181 | +0.0142 ±0.0168 | +0.0047 ±0.0059 | +0.8 | 0.845 | 0.840 | |
| kalshi favorite 0.9-1.0 | 82 | +0.0144 ±0.0313 | +0.0014 ±0.0079 | +0.5 | 0.939 | 0.927 | |
| surface: Hard | 413 | -0.0122 ±0.0084 | -0.0048 ±0.0035 | -1.5 | 0.683 | 0.679 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 332 | -0.0048 ±0.0119 | -0.0030 ±0.0050 | -0.4 | 0.596 | 0.607 | |
| tier: atp500 | 204 | -0.0077 ±0.0100 | -0.0039 ±0.0045 | -0.8 | 0.613 | 0.610 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 502 | -0.0109 ±0.0092 | -0.0059 ±0.0035 | -1.2 | 0.732 | 0.747 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| round early (R128-R64) | 544 | -0.0111 ±0.0086 | -0.0049 ±0.0034 | -1.3 | 0.725 | 0.734 | |
| round late (QF-F) | 148 | -0.0003 ±0.0116 | -0.0012 ±0.0051 | -0.0 | 0.642 | 0.635 | |
| round mid (R32-R16) | 549 | -0.0015 ±0.0082 | -0.0017 ±0.0034 | -0.2 | 0.626 | 0.635 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 274 | -0.0110 ±0.0105 | -0.0041 ±0.0044 | -1.0 | 0.628 | 0.626 | |
| month 2026-09 | 125 | -0.0180 ±0.0109 | -0.0089 ±0.0043 | -1.7 | 0.800 | 0.800 | |
| agree (<0.05) | 684 | +0.0001 ±0.0027 | -0.0006 ±0.0009 | +0.0 | 0.711 | 0.705 | |
| mild disagree (0.05-0.10) | 379 | -0.0129 ±0.0094 | -0.0060 ±0.0035 | -1.4 | 0.619 | 0.654 | |
| big disagree (>=0.1) | 200 | -0.0109 ±0.0273 | -0.0056 ±0.0117 | -0.4 | 0.618 | 0.618 | |
| tour: atp | 621 | -0.0012 ±0.0073 | -0.0014 ±0.0029 | -0.2 | 0.649 | 0.666 | |
| tour: wta | 642 | -0.0098 ±0.0078 | -0.0046 ±0.0032 | -1.2 | 0.687 | 0.686 | |

When they disagree by >= 0.1: model closer to the outcome in **85/200** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 14 | 0.067 | 0.143 |
| 0.1-0.2 | 79 | 0.153 | 0.139 |
| 0.2-0.3 | 109 | 0.254 | 0.257 |
| 0.3-0.4 | 161 | 0.354 | 0.354 |
| 0.4-0.5 | 219 | 0.450 | 0.475 |
| 0.5-0.6 | 201 | 0.551 | 0.547 |
| 0.6-0.7 | 185 | 0.647 | 0.627 |
| 0.7-0.8 | 152 | 0.750 | 0.757 |
| 0.8-0.9 | 98 | 0.848 | 0.827 |
| 0.9-1.0 | 45 | 0.933 | 0.933 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 30 | 0.060 | 0.100 |
| 0.1-0.2 | 73 | 0.152 | 0.137 |
| 0.2-0.3 | 127 | 0.255 | 0.276 |
| 0.3-0.4 | 157 | 0.354 | 0.382 |
| 0.4-0.5 | 187 | 0.444 | 0.455 |
| 0.5-0.6 | 173 | 0.555 | 0.520 |
| 0.6-0.7 | 187 | 0.648 | 0.636 |
| 0.7-0.8 | 169 | 0.748 | 0.746 |
| 0.8-0.9 | 109 | 0.846 | 0.826 |
| 0.9-1.0 | 51 | 0.932 | 0.941 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 280 | +0.0214 ±0.0102 | +0.0053 ±0.0031 | +2.1 | 0.743 | 0.739 | |
| top-20 involved | 464 | +0.0067 ±0.0075 | +0.0009 ±0.0025 | +0.9 | 0.734 | 0.734 | |
| kalshi favorite 0.8-0.9 | 181 | +0.0142 ±0.0168 | +0.0047 ±0.0059 | +0.8 | 0.845 | 0.840 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| kalshi favorite 0.9-1.0 | 82 | +0.0144 ±0.0313 | +0.0014 ±0.0079 | +0.5 | 0.939 | 0.927 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| both inside top-50 | 310 | +0.0005 ±0.0089 | -0.0006 ±0.0039 | +0.1 | 0.663 | 0.656 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| mild disagree (0.05-0.10) | 379 | -0.0129 ±0.0094 | -0.0060 ±0.0035 | -1.4 | 0.619 | 0.654 | |
| surface: Hard | 413 | -0.0122 ±0.0084 | -0.0048 ±0.0035 | -1.5 | 0.683 | 0.679 | |
| best rank 11-20 | 184 | -0.0157 ±0.0107 | -0.0058 ±0.0042 | -1.5 | 0.720 | 0.726 | |
| month 2026-09 | 125 | -0.0180 ±0.0109 | -0.0089 ±0.0043 | -1.7 | 0.800 | 0.800 | |
| no top-20 player | 799 | -0.0127 ±0.0073 | -0.0053 ±0.0031 | -1.7 | 0.630 | 0.643 | |
| best rank 21-50 | 446 | -0.0167 ±0.0081 | -0.0069 ±0.0035 | -2.1 | 0.652 | 0.685 | |
| pred_source: live aligned | 346 | -0.0203 ±0.0083 | -0.0085 ±0.0034 | -2.4 | 0.694 | 0.698 | |
| kalshi favorite 0.5-0.6 | 357 | -0.0246 ±0.0093 | -0.0116 ±0.0043 | -2.7 | 0.497 | 0.538 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1263, mean |Δ|=0.0017, p95=0.0086, >0.05 in 2 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=274, >0.05: 1) | 2026-09 p95=0.0039 (n=125, >0.05: 0)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1263, d_ll -0.0056 ±0.0054 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 512 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 63, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Cincinnati': 1, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): Adam Walton, Akasha Urhobo, Aleksandr Shevchenko, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carlos Alcaraz, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide
