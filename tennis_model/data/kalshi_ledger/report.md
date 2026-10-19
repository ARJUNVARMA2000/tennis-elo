# Model vs Kalshi — match-by-match scorecard

_Generated 2026-10-19T11:32:13Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 2172 | 2059 | 37 | 13 | 63 | 0 | 12 | 24 | 59 | 2026-05-03..2026-10-20 |
| wta | 2261 | 1373 | 56 | 768 | 64 | 0 | 10 | 17 | 37 | 2026-05-02..2026-10-20 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1622 | 0.6086 | 0.5926 | -0.0160 ±0.0052 | -0.0067 ±0.0021 | 0.662 | 0.676 |
| atp | 783 | 0.6211 | 0.6119 | -0.0092 ±0.0073 | -0.0039 ±0.0029 | 0.649 | 0.665 |
| wta | 839 | 0.5969 | 0.5745 | -0.0224 ±0.0073 | -0.0093 ±0.0030 | 0.673 | 0.687 |
| pooled/live_aligned | 686 | 0.6131 | 0.5744 | -0.0387 ±0.0082 | -0.0148 ±0.0034 | 0.665 | 0.688 |
| pooled/backtest | 936 | 0.6053 | 0.6059 | +0.0006 ±0.0066 | -0.0008 ±0.0027 | 0.659 | 0.667 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 686 | -0.0387 ±0.0082 | -0.0148 ±0.0034 | -4.7 | 0.665 | 0.688 | |
| pred_source: backtest | 936 | +0.0006 ±0.0066 | -0.0008 ±0.0027 | +0.1 | 0.659 | 0.667 | |
| top-20 involved | 583 | -0.0004 ±0.0082 | -0.0014 ±0.0030 | -0.1 | 0.718 | 0.720 | |
| no top-20 player | 1039 | -0.0248 ±0.0066 | -0.0096 ±0.0028 | -3.7 | 0.630 | 0.652 | |
| both inside top-50 | 421 | -0.0201 ±0.0103 | -0.0082 ±0.0043 | -2.0 | 0.638 | 0.647 | |
| someone outside top-50 | 1201 | -0.0146 ±0.0060 | -0.0061 ±0.0024 | -2.4 | 0.670 | 0.686 | |
| best rank 1-10 | 348 | +0.0102 ±0.0104 | +0.0023 ±0.0035 | +1.0 | 0.733 | 0.730 | |
| best rank 11-20 | 235 | -0.0163 ±0.0132 | -0.0069 ±0.0053 | -1.2 | 0.696 | 0.704 | |
| best rank 21-50 | 558 | -0.0273 ±0.0081 | -0.0111 ±0.0035 | -3.4 | 0.656 | 0.697 | |
| best rank 51-100 | 393 | -0.0187 ±0.0112 | -0.0069 ±0.0047 | -1.7 | 0.599 | 0.597 | |
| best rank 100+ | 88 | -0.0357 ±0.0320 | -0.0128 ±0.0136 | -1.1 | 0.602 | 0.608 | |
| kalshi favorite 0.5-0.6 | 464 | -0.0232 ±0.0085 | -0.0109 ±0.0040 | -2.7 | 0.505 | 0.544 | |
| kalshi favorite 0.6-0.7 | 448 | -0.0107 ±0.0091 | -0.0040 ±0.0041 | -1.2 | 0.614 | 0.616 | |
| kalshi favorite 0.7-0.8 | 374 | -0.0082 ±0.0099 | -0.0031 ±0.0040 | -0.8 | 0.737 | 0.743 | |
| kalshi favorite 0.8-0.9 | 224 | -0.0018 ±0.0157 | -0.0014 ±0.0055 | -0.1 | 0.826 | 0.830 | |
| kalshi favorite 0.9-1.0 | 112 | -0.0624 ±0.0309 | -0.0227 ±0.0096 | -2.0 | 0.920 | 0.929 | |
| surface: Hard | 772 | -0.0311 ±0.0078 | -0.0117 ±0.0032 | -4.0 | 0.662 | 0.677 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 535 | -0.0224 ±0.0102 | -0.0085 ±0.0042 | -2.2 | 0.611 | 0.628 | |
| tier: atp500 | 252 | -0.0155 ±0.0103 | -0.0070 ±0.0046 | -1.5 | 0.627 | 0.645 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 324 | -0.0171 ±0.0108 | -0.0058 ±0.0046 | -1.6 | 0.659 | 0.673 | |
| round early (R128-R64) | 646 | -0.0208 ±0.0083 | -0.0085 ±0.0032 | -2.5 | 0.710 | 0.723 | |
| round late (QF-F) | 218 | -0.0066 ±0.0115 | -0.0036 ±0.0051 | -0.6 | 0.633 | 0.642 | |
| round mid (R32-R16) | 736 | -0.0150 ±0.0080 | -0.0062 ±0.0033 | -1.9 | 0.632 | 0.649 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 319 | -0.0405 ±0.0103 | -0.0168 ±0.0043 | -3.9 | 0.705 | 0.730 | |
| month 2026-10 | 163 | -0.0520 ±0.0238 | -0.0175 ±0.0095 | -2.2 | 0.632 | 0.672 | |
| agree (<0.05) | 874 | -0.0004 ±0.0025 | -0.0005 ±0.0008 | -0.2 | 0.707 | 0.705 | |
| mild disagree (0.05-0.10) | 477 | -0.0105 ±0.0082 | -0.0046 ±0.0031 | -1.3 | 0.624 | 0.647 | |
| big disagree (>=0.1) | 271 | -0.0762 ±0.0259 | -0.0304 ±0.0109 | -2.9 | 0.581 | 0.635 | |
| tour: atp | 783 | -0.0092 ±0.0073 | -0.0039 ±0.0029 | -1.3 | 0.649 | 0.665 | |
| tour: wta | 839 | -0.0224 ±0.0073 | -0.0093 ±0.0030 | -3.1 | 0.673 | 0.687 | |

When they disagree by >= 0.1: model closer to the outcome in **104/271** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 19 | 0.068 | 0.158 |
| 0.1-0.2 | 102 | 0.152 | 0.186 |
| 0.2-0.3 | 147 | 0.250 | 0.259 |
| 0.3-0.4 | 207 | 0.353 | 0.372 |
| 0.4-0.5 | 279 | 0.451 | 0.470 |
| 0.5-0.6 | 251 | 0.551 | 0.538 |
| 0.6-0.7 | 240 | 0.647 | 0.625 |
| 0.7-0.8 | 194 | 0.752 | 0.773 |
| 0.8-0.9 | 124 | 0.845 | 0.790 |
| 0.9-1.0 | 59 | 0.932 | 0.915 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 43 | 0.058 | 0.093 |
| 0.1-0.2 | 90 | 0.154 | 0.167 |
| 0.2-0.3 | 169 | 0.254 | 0.260 |
| 0.3-0.4 | 201 | 0.354 | 0.393 |
| 0.4-0.5 | 236 | 0.445 | 0.453 |
| 0.5-0.6 | 232 | 0.555 | 0.534 |
| 0.6-0.7 | 243 | 0.649 | 0.630 |
| 0.7-0.8 | 205 | 0.749 | 0.746 |
| 0.8-0.9 | 135 | 0.846 | 0.830 |
| 0.9-1.0 | 68 | 0.934 | 0.941 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 348 | +0.0102 ±0.0104 | +0.0023 ±0.0035 | +1.0 | 0.733 | 0.730 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 936 | +0.0006 ±0.0066 | -0.0008 ±0.0027 | +0.1 | 0.659 | 0.667 | |
| top-20 involved | 583 | -0.0004 ±0.0082 | -0.0014 ±0.0030 | -0.1 | 0.718 | 0.720 | |
| kalshi favorite 0.8-0.9 | 224 | -0.0018 ±0.0157 | -0.0014 ±0.0055 | -0.1 | 0.826 | 0.830 | |
| agree (<0.05) | 874 | -0.0004 ±0.0025 | -0.0005 ±0.0008 | -0.2 | 0.707 | 0.705 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| kalshi favorite 0.5-0.6 | 464 | -0.0232 ±0.0085 | -0.0109 ±0.0040 | -2.7 | 0.505 | 0.544 | |
| big disagree (>=0.1) | 271 | -0.0762 ±0.0259 | -0.0304 ±0.0109 | -2.9 | 0.581 | 0.635 | |
| tour: wta | 839 | -0.0224 ±0.0073 | -0.0093 ±0.0030 | -3.1 | 0.673 | 0.687 | |
| best rank 21-50 | 558 | -0.0273 ±0.0081 | -0.0111 ±0.0035 | -3.4 | 0.656 | 0.697 | |
| no top-20 player | 1039 | -0.0248 ±0.0066 | -0.0096 ±0.0028 | -3.7 | 0.630 | 0.652 | |
| month 2026-09 | 319 | -0.0405 ±0.0103 | -0.0168 ±0.0043 | -3.9 | 0.705 | 0.730 | |
| surface: Hard | 772 | -0.0311 ±0.0078 | -0.0117 ±0.0032 | -4.0 | 0.662 | 0.677 | |
| pred_source: live aligned | 686 | -0.0387 ±0.0082 | -0.0148 ±0.0034 | -4.7 | 0.665 | 0.688 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1622, mean |Δ|=0.0062, p95=0.0100, >0.05 in 39 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0666 (n=319, >0.05: 19) | 2026-10 p95=0.2043 (n=163, >0.05: 18)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1624, d_ll -0.0160 ±0.0052
- Unmatched qualifying markets: 622 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'WTA Seoul': 3, 'ATP Chengdu': 1}
- Unmatched Kalshi names, main draw (40): Akasha Urhobo, Aleksandr Shevchenko, Alevtina Ibragimova, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari
