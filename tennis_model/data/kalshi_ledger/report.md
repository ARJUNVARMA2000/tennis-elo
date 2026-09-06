# Model vs Kalshi — match-by-match scorecard

_Generated 2026-09-06T09:52:12Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1794 | 1713 | 10 | 14 | 57 | 0 | 11 | 19 | 51 | 2026-05-03..2026-09-07 |
| wta | 1781 | 1076 | 8 | 655 | 42 | 0 | 7 | 15 | 26 | 2026-05-02..2026-09-07 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1236 | 0.5972 | 0.5925 | -0.0047 ±0.0054 | -0.0026 ±0.0022 | 0.667 | 0.674 |
| atp | 607 | 0.6193 | 0.6198 | +0.0005 ±0.0074 | -0.0006 ±0.0030 | 0.649 | 0.663 |
| wta | 629 | 0.5759 | 0.5662 | -0.0097 ±0.0079 | -0.0046 ±0.0033 | 0.685 | 0.684 |
| pooled/live_aligned | 319 | 0.5728 | 0.5546 | -0.0182 ±0.0087 | -0.0074 ±0.0036 | 0.693 | 0.691 |
| pooled/backtest | 917 | 0.6057 | 0.6057 | +0.0000 ±0.0067 | -0.0010 ±0.0027 | 0.659 | 0.668 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 319 | -0.0182 ±0.0087 | -0.0074 ±0.0036 | -2.1 | 0.693 | 0.691 | |
| pred_source: backtest | 917 | +0.0000 ±0.0067 | -0.0010 ±0.0027 | +0.0 | 0.659 | 0.668 | |
| top-20 involved | 442 | +0.0079 ±0.0077 | +0.0013 ±0.0026 | +1.0 | 0.732 | 0.732 | |
| no top-20 player | 794 | -0.0117 ±0.0073 | -0.0048 ±0.0031 | -1.6 | 0.632 | 0.642 | |
| both inside top-50 | 287 | +0.0027 ±0.0095 | +0.0006 ±0.0041 | +0.3 | 0.657 | 0.646 | |
| someone outside top-50 | 949 | -0.0069 ±0.0065 | -0.0036 ±0.0026 | -1.1 | 0.671 | 0.682 | |
| best rank 1-10 | 259 | +0.0242 ±0.0107 | +0.0061 ±0.0032 | +2.3 | 0.737 | 0.734 | |
| best rank 11-20 | 183 | -0.0151 ±0.0108 | -0.0055 ±0.0042 | -1.4 | 0.724 | 0.730 | |
| best rank 21-50 | 441 | -0.0149 ±0.0081 | -0.0060 ±0.0036 | -1.8 | 0.655 | 0.684 | |
| best rank 51-100 | 294 | -0.0088 ±0.0133 | -0.0041 ±0.0056 | -0.7 | 0.600 | 0.592 | |
| best rank 100+ | 59 | -0.0016 ±0.0395 | +0.0001 ±0.0170 | -0.0 | 0.610 | 0.576 | |
| kalshi favorite 0.5-0.6 | 350 | -0.0241 ±0.0094 | -0.0113 ±0.0044 | -2.6 | 0.496 | 0.537 | |
| kalshi favorite 0.6-0.7 | 340 | -0.0013 ±0.0098 | -0.0000 ±0.0045 | -0.1 | 0.629 | 0.618 | |
| kalshi favorite 0.7-0.8 | 288 | -0.0017 ±0.0094 | -0.0008 ±0.0038 | -0.2 | 0.738 | 0.736 | |
| kalshi favorite 0.8-0.9 | 176 | +0.0137 ±0.0173 | +0.0047 ±0.0061 | +0.8 | 0.841 | 0.835 | |
| kalshi favorite 0.9-1.0 | 82 | +0.0144 ±0.0313 | +0.0014 ±0.0079 | +0.5 | 0.939 | 0.927 | |
| surface: Hard | 386 | -0.0099 ±0.0087 | -0.0037 ±0.0036 | -1.1 | 0.681 | 0.672 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 332 | -0.0048 ±0.0119 | -0.0030 ±0.0050 | -0.4 | 0.596 | 0.607 | |
| tier: atp500 | 204 | -0.0077 ±0.0100 | -0.0039 ±0.0045 | -0.8 | 0.613 | 0.610 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 475 | -0.0089 ±0.0095 | -0.0050 ±0.0036 | -0.9 | 0.734 | 0.745 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| round early (R128-R64) | 544 | -0.0111 ±0.0086 | -0.0049 ±0.0034 | -1.3 | 0.725 | 0.734 | |
| round late (QF-F) | 137 | +0.0031 ±0.0122 | +0.0006 ±0.0053 | +0.3 | 0.628 | 0.613 | |
| round mid (R32-R16) | 533 | -0.0001 ±0.0084 | -0.0012 ±0.0035 | -0.0 | 0.626 | 0.633 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 278 | -0.0117 ±0.0104 | -0.0044 ±0.0043 | -1.1 | 0.629 | 0.628 | |
| month 2026-09 | 94 | -0.0082 ±0.0113 | -0.0049 ±0.0046 | -0.7 | 0.830 | 0.809 | |
| agree (<0.05) | 671 | +0.0002 ±0.0028 | -0.0006 ±0.0009 | +0.1 | 0.711 | 0.706 | |
| mild disagree (0.05-0.10) | 368 | -0.0111 ±0.0095 | -0.0053 ±0.0036 | -1.2 | 0.613 | 0.649 | |
| big disagree (>=0.1) | 197 | -0.0093 ±0.0276 | -0.0048 ±0.0118 | -0.3 | 0.622 | 0.612 | |
| tour: atp | 607 | +0.0005 ±0.0074 | -0.0006 ±0.0030 | +0.1 | 0.649 | 0.663 | |
| tour: wta | 629 | -0.0097 ±0.0079 | -0.0046 ±0.0033 | -1.2 | 0.685 | 0.684 | |

When they disagree by >= 0.1: model closer to the outcome in **84/197** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 14 | 0.067 | 0.143 |
| 0.1-0.2 | 77 | 0.153 | 0.130 |
| 0.2-0.3 | 109 | 0.254 | 0.257 |
| 0.3-0.4 | 160 | 0.354 | 0.350 |
| 0.4-0.5 | 216 | 0.450 | 0.477 |
| 0.5-0.6 | 196 | 0.551 | 0.551 |
| 0.6-0.7 | 181 | 0.647 | 0.624 |
| 0.7-0.8 | 148 | 0.750 | 0.750 |
| 0.8-0.9 | 91 | 0.847 | 0.824 |
| 0.9-1.0 | 44 | 0.933 | 0.932 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 30 | 0.060 | 0.100 |
| 0.1-0.2 | 72 | 0.152 | 0.139 |
| 0.2-0.3 | 126 | 0.256 | 0.270 |
| 0.3-0.4 | 154 | 0.354 | 0.383 |
| 0.4-0.5 | 184 | 0.444 | 0.457 |
| 0.5-0.6 | 169 | 0.555 | 0.521 |
| 0.6-0.7 | 183 | 0.647 | 0.628 |
| 0.7-0.8 | 162 | 0.748 | 0.741 |
| 0.8-0.9 | 105 | 0.846 | 0.819 |
| 0.9-1.0 | 51 | 0.932 | 0.941 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 259 | +0.0242 ±0.0107 | +0.0061 ±0.0032 | +2.3 | 0.737 | 0.734 | |
| top-20 involved | 442 | +0.0079 ±0.0077 | +0.0013 ±0.0026 | +1.0 | 0.732 | 0.732 | |
| kalshi favorite 0.8-0.9 | 176 | +0.0137 ±0.0173 | +0.0047 ±0.0061 | +0.8 | 0.841 | 0.835 | |
| tier: masters | 224 | +0.0067 ±0.0099 | +0.0038 ±0.0044 | +0.7 | 0.681 | 0.679 | |
| kalshi favorite 0.9-1.0 | 82 | +0.0144 ±0.0313 | +0.0014 ±0.0079 | +0.5 | 0.939 | 0.927 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| both inside top-50 | 287 | +0.0027 ±0.0095 | +0.0006 ±0.0041 | +0.3 | 0.657 | 0.646 | |
| round late (QF-F) | 137 | +0.0031 ±0.0122 | +0.0006 ±0.0053 | +0.3 | 0.628 | 0.613 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| mild disagree (0.05-0.10) | 368 | -0.0111 ±0.0095 | -0.0053 ±0.0036 | -1.2 | 0.613 | 0.649 | |
| tour: wta | 629 | -0.0097 ±0.0079 | -0.0046 ±0.0033 | -1.2 | 0.685 | 0.684 | |
| round early (R128-R64) | 544 | -0.0111 ±0.0086 | -0.0049 ±0.0034 | -1.3 | 0.725 | 0.734 | |
| best rank 11-20 | 183 | -0.0151 ±0.0108 | -0.0055 ±0.0042 | -1.4 | 0.724 | 0.730 | |
| no top-20 player | 794 | -0.0117 ±0.0073 | -0.0048 ±0.0031 | -1.6 | 0.632 | 0.642 | |
| best rank 21-50 | 441 | -0.0149 ±0.0081 | -0.0060 ±0.0036 | -1.8 | 0.655 | 0.684 | |
| pred_source: live aligned | 319 | -0.0182 ±0.0087 | -0.0074 ±0.0036 | -2.1 | 0.693 | 0.691 | |
| kalshi favorite 0.5-0.6 | 350 | -0.0241 ±0.0094 | -0.0113 ±0.0044 | -2.6 | 0.496 | 0.537 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1236, mean |Δ|=0.0017, p95=0.0086, >0.05 in 2 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0085 (n=278, >0.05: 1) | 2026-09 p95=0.0036 (n=94, >0.05: 0)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1236, d_ll -0.0047 ±0.0054 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 512 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 61, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Cincinnati': 1, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): Adam Walton, Akasha Urhobo, Aleksandr Shevchenko, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari
