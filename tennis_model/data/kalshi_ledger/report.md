# Model vs Kalshi — match-by-match scorecard

_Generated 2026-09-09T06:22:06Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1798 | 1722 | 3 | 16 | 57 | 0 | 11 | 19 | 45 | 2026-05-03..2026-09-09 |
| wta | 1786 | 1086 | 3 | 655 | 42 | 0 | 7 | 15 | 20 | 2026-05-02..2026-09-11 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1254 | 0.5969 | 0.5916 | -0.0053 ±0.0054 | -0.0029 ±0.0022 | 0.667 | 0.675 |
| atp | 616 | 0.6185 | 0.6180 | -0.0005 ±0.0073 | -0.0011 ±0.0029 | 0.649 | 0.665 |
| wta | 638 | 0.5760 | 0.5662 | -0.0099 ±0.0079 | -0.0046 ±0.0032 | 0.685 | 0.684 |
| pooled/live_aligned | 337 | 0.5729 | 0.5532 | -0.0197 ±0.0085 | -0.0081 ±0.0035 | 0.691 | 0.693 |
| pooled/backtest | 917 | 0.6057 | 0.6057 | +0.0000 ±0.0067 | -0.0010 ±0.0027 | 0.659 | 0.668 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 337 | -0.0197 ±0.0085 | -0.0081 ±0.0035 | -2.3 | 0.691 | 0.693 | |
| pred_source: backtest | 917 | +0.0000 ±0.0067 | -0.0010 ±0.0027 | +0.0 | 0.659 | 0.668 | |
| top-20 involved | 456 | +0.0070 ±0.0076 | +0.0011 ±0.0025 | +0.9 | 0.731 | 0.731 | |
| no top-20 player | 798 | -0.0123 ±0.0073 | -0.0051 ±0.0031 | -1.7 | 0.631 | 0.642 | |
| both inside top-50 | 302 | +0.0022 ±0.0091 | +0.0003 ±0.0039 | +0.2 | 0.661 | 0.651 | |
| someone outside top-50 | 952 | -0.0076 ±0.0065 | -0.0039 ±0.0026 | -1.2 | 0.670 | 0.682 | |
| best rank 1-10 | 272 | +0.0223 ±0.0105 | +0.0057 ±0.0031 | +2.1 | 0.739 | 0.735 | |
| best rank 11-20 | 184 | -0.0157 ±0.0107 | -0.0058 ±0.0042 | -1.5 | 0.720 | 0.726 | |
| best rank 21-50 | 445 | -0.0160 ±0.0081 | -0.0065 ±0.0035 | -2.0 | 0.654 | 0.684 | |
| best rank 51-100 | 294 | -0.0088 ±0.0133 | -0.0041 ±0.0056 | -0.7 | 0.600 | 0.592 | |
| best rank 100+ | 59 | -0.0016 ±0.0395 | +0.0001 ±0.0170 | -0.0 | 0.610 | 0.576 | |
| kalshi favorite 0.5-0.6 | 356 | -0.0247 ±0.0093 | -0.0116 ±0.0044 | -2.7 | 0.496 | 0.537 | |
| kalshi favorite 0.6-0.7 | 344 | -0.0019 ±0.0097 | -0.0004 ±0.0044 | -0.2 | 0.628 | 0.619 | |
| kalshi favorite 0.7-0.8 | 292 | -0.0031 ±0.0095 | -0.0011 ±0.0038 | -0.3 | 0.738 | 0.736 | |
| kalshi favorite 0.8-0.9 | 180 | +0.0142 ±0.0169 | +0.0047 ±0.0060 | +0.8 | 0.844 | 0.839 | |
| kalshi favorite 0.9-1.0 | 82 | +0.0144 ±0.0313 | +0.0014 ±0.0079 | +0.5 | 0.939 | 0.927 | |
| surface: Hard | 404 | -0.0115 ±0.0085 | -0.0044 ±0.0035 | -1.3 | 0.681 | 0.675 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 332 | -0.0048 ±0.0119 | -0.0030 ±0.0050 | -0.4 | 0.596 | 0.607 | |
| tier: atp500 | 204 | -0.0077 ±0.0100 | -0.0039 ±0.0045 | -0.8 | 0.613 | 0.610 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 493 | -0.0103 ±0.0093 | -0.0055 ±0.0035 | -1.1 | 0.731 | 0.744 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| round early (R128-R64) | 544 | -0.0111 ±0.0086 | -0.0049 ±0.0034 | -1.3 | 0.725 | 0.734 | |
| round late (QF-F) | 139 | +0.0026 ±0.0121 | +0.0003 ±0.0053 | +0.2 | 0.633 | 0.619 | |
| round mid (R32-R16) | 549 | -0.0015 ±0.0082 | -0.0017 ±0.0034 | -0.2 | 0.626 | 0.635 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 274 | -0.0110 ±0.0105 | -0.0041 ±0.0044 | -1.0 | 0.628 | 0.626 | |
| month 2026-09 | 116 | -0.0159 ±0.0113 | -0.0077 ±0.0044 | -1.4 | 0.802 | 0.793 | |
| agree (<0.05) | 680 | +0.0002 ±0.0027 | -0.0006 ±0.0009 | +0.1 | 0.710 | 0.705 | |
| mild disagree (0.05-0.10) | 375 | -0.0129 ±0.0095 | -0.0059 ±0.0036 | -1.4 | 0.615 | 0.651 | |
| big disagree (>=0.1) | 199 | -0.0094 ±0.0274 | -0.0049 ±0.0117 | -0.3 | 0.621 | 0.616 | |
| tour: atp | 616 | -0.0005 ±0.0073 | -0.0011 ±0.0029 | -0.1 | 0.649 | 0.665 | |
| tour: wta | 638 | -0.0099 ±0.0079 | -0.0046 ±0.0032 | -1.3 | 0.685 | 0.684 | |

When they disagree by >= 0.1: model closer to the outcome in **85/199** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 14 | 0.067 | 0.143 |
| 0.1-0.2 | 78 | 0.153 | 0.128 |
| 0.2-0.3 | 109 | 0.254 | 0.257 |
| 0.3-0.4 | 161 | 0.354 | 0.354 |
| 0.4-0.5 | 218 | 0.450 | 0.477 |
| 0.5-0.6 | 199 | 0.551 | 0.548 |
| 0.6-0.7 | 183 | 0.647 | 0.623 |
| 0.7-0.8 | 152 | 0.750 | 0.757 |
| 0.8-0.9 | 95 | 0.848 | 0.821 |
| 0.9-1.0 | 45 | 0.933 | 0.933 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 30 | 0.060 | 0.100 |
| 0.1-0.2 | 73 | 0.152 | 0.137 |
| 0.2-0.3 | 126 | 0.256 | 0.270 |
| 0.3-0.4 | 156 | 0.354 | 0.385 |
| 0.4-0.5 | 186 | 0.444 | 0.457 |
| 0.5-0.6 | 173 | 0.555 | 0.520 |
| 0.6-0.7 | 185 | 0.648 | 0.632 |
| 0.7-0.8 | 166 | 0.748 | 0.741 |
| 0.8-0.9 | 108 | 0.846 | 0.824 |
| 0.9-1.0 | 51 | 0.932 | 0.941 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 272 | +0.0223 ±0.0105 | +0.0057 ±0.0031 | +2.1 | 0.739 | 0.735 | |
| top-20 involved | 456 | +0.0070 ±0.0076 | +0.0011 ±0.0025 | +0.9 | 0.731 | 0.731 | |
| kalshi favorite 0.8-0.9 | 180 | +0.0142 ±0.0169 | +0.0047 ±0.0060 | +0.8 | 0.844 | 0.839 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| kalshi favorite 0.9-1.0 | 82 | +0.0144 ±0.0313 | +0.0014 ±0.0079 | +0.5 | 0.939 | 0.927 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| both inside top-50 | 302 | +0.0022 ±0.0091 | +0.0003 ±0.0039 | +0.2 | 0.661 | 0.651 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| surface: Hard | 404 | -0.0115 ±0.0085 | -0.0044 ±0.0035 | -1.3 | 0.681 | 0.675 | |
| mild disagree (0.05-0.10) | 375 | -0.0129 ±0.0095 | -0.0059 ±0.0036 | -1.4 | 0.615 | 0.651 | |
| month 2026-09 | 116 | -0.0159 ±0.0113 | -0.0077 ±0.0044 | -1.4 | 0.802 | 0.793 | |
| best rank 11-20 | 184 | -0.0157 ±0.0107 | -0.0058 ±0.0042 | -1.5 | 0.720 | 0.726 | |
| no top-20 player | 798 | -0.0123 ±0.0073 | -0.0051 ±0.0031 | -1.7 | 0.631 | 0.642 | |
| best rank 21-50 | 445 | -0.0160 ±0.0081 | -0.0065 ±0.0035 | -2.0 | 0.654 | 0.684 | |
| pred_source: live aligned | 337 | -0.0197 ±0.0085 | -0.0081 ±0.0035 | -2.3 | 0.691 | 0.693 | |
| kalshi favorite 0.5-0.6 | 356 | -0.0247 ±0.0093 | -0.0116 ±0.0044 | -2.7 | 0.496 | 0.537 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1254, mean |Δ|=0.0017, p95=0.0086, >0.05 in 2 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=274, >0.05: 1) | 2026-09 p95=0.0039 (n=116, >0.05: 0)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1254, d_ll -0.0053 ±0.0054 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 512 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 63, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Cincinnati': 1, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): Adam Walton, Akasha Urhobo, Aleksandr Shevchenko, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carlos Alcaraz, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide
