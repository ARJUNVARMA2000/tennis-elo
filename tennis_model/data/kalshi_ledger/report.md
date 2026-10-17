# Model vs Kalshi — match-by-match scorecard

_Generated 2026-10-17T17:32:31Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 2139 | 2036 | 28 | 13 | 62 | 0 | 12 | 24 | 68 | 2026-05-03..2026-10-18 |
| wta | 2231 | 1363 | 37 | 768 | 63 | 0 | 10 | 16 | 42 | 2026-05-02..2026-10-18 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1616 | 0.6082 | 0.5923 | -0.0159 ±0.0052 | -0.0066 ±0.0021 | 0.663 | 0.676 |
| atp | 780 | 0.6202 | 0.6112 | -0.0090 ±0.0073 | -0.0038 ±0.0029 | 0.651 | 0.666 |
| wta | 836 | 0.5970 | 0.5747 | -0.0223 ±0.0073 | -0.0092 ±0.0030 | 0.673 | 0.685 |
| pooled/live_aligned | 680 | 0.6123 | 0.5738 | -0.0386 ±0.0082 | -0.0147 ±0.0034 | 0.668 | 0.688 |
| pooled/backtest | 936 | 0.6053 | 0.6059 | +0.0006 ±0.0066 | -0.0008 ±0.0027 | 0.659 | 0.667 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 680 | -0.0386 ±0.0082 | -0.0147 ±0.0034 | -4.7 | 0.668 | 0.688 | |
| pred_source: backtest | 936 | +0.0006 ±0.0066 | -0.0008 ±0.0027 | +0.1 | 0.659 | 0.667 | |
| top-20 involved | 580 | -0.0001 ±0.0082 | -0.0013 ±0.0030 | -0.0 | 0.718 | 0.720 | |
| no top-20 player | 1036 | -0.0247 ±0.0066 | -0.0096 ±0.0028 | -3.7 | 0.632 | 0.652 | |
| both inside top-50 | 419 | -0.0198 ±0.0103 | -0.0080 ±0.0043 | -1.9 | 0.638 | 0.648 | |
| someone outside top-50 | 1197 | -0.0145 ±0.0060 | -0.0061 ±0.0024 | -2.4 | 0.671 | 0.686 | |
| best rank 1-10 | 348 | +0.0102 ±0.0104 | +0.0023 ±0.0035 | +1.0 | 0.733 | 0.730 | |
| best rank 11-20 | 232 | -0.0157 ±0.0133 | -0.0066 ±0.0054 | -1.2 | 0.696 | 0.705 | |
| best rank 21-50 | 557 | -0.0280 ±0.0081 | -0.0114 ±0.0035 | -3.5 | 0.657 | 0.698 | |
| best rank 51-100 | 391 | -0.0176 ±0.0112 | -0.0064 ±0.0047 | -1.6 | 0.602 | 0.595 | |
| best rank 100+ | 88 | -0.0357 ±0.0320 | -0.0128 ±0.0136 | -1.1 | 0.602 | 0.608 | |
| kalshi favorite 0.5-0.6 | 461 | -0.0226 ±0.0085 | -0.0106 ±0.0040 | -2.6 | 0.507 | 0.543 | |
| kalshi favorite 0.6-0.7 | 446 | -0.0108 ±0.0091 | -0.0040 ±0.0040 | -1.2 | 0.617 | 0.617 | |
| kalshi favorite 0.7-0.8 | 373 | -0.0082 ±0.0099 | -0.0031 ±0.0040 | -0.8 | 0.736 | 0.743 | |
| kalshi favorite 0.8-0.9 | 224 | -0.0018 ±0.0157 | -0.0014 ±0.0055 | -0.1 | 0.826 | 0.830 | |
| kalshi favorite 0.9-1.0 | 112 | -0.0624 ±0.0309 | -0.0227 ±0.0096 | -2.0 | 0.920 | 0.929 | |
| surface: Hard | 766 | -0.0309 ±0.0078 | -0.0116 ±0.0032 | -4.0 | 0.664 | 0.678 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 532 | -0.0222 ±0.0102 | -0.0084 ±0.0042 | -2.2 | 0.615 | 0.630 | |
| tier: atp500 | 250 | -0.0149 ±0.0103 | -0.0067 ±0.0046 | -1.4 | 0.628 | 0.642 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 323 | -0.0172 ±0.0109 | -0.0058 ±0.0046 | -1.6 | 0.658 | 0.672 | |
| round early (R128-R64) | 646 | -0.0208 ±0.0083 | -0.0085 ±0.0032 | -2.5 | 0.710 | 0.723 | |
| round late (QF-F) | 216 | -0.0058 ±0.0116 | -0.0032 ±0.0052 | -0.5 | 0.634 | 0.644 | |
| round mid (R32-R16) | 732 | -0.0149 ±0.0080 | -0.0061 ±0.0033 | -1.9 | 0.635 | 0.648 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 319 | -0.0405 ±0.0103 | -0.0168 ±0.0043 | -3.9 | 0.705 | 0.730 | |
| month 2026-10 | 157 | -0.0519 ±0.0245 | -0.0172 ±0.0097 | -2.1 | 0.643 | 0.672 | |
| agree (<0.05) | 872 | -0.0004 ±0.0025 | -0.0005 ±0.0008 | -0.2 | 0.706 | 0.704 | |
| mild disagree (0.05-0.10) | 475 | -0.0098 ±0.0082 | -0.0042 ±0.0031 | -1.2 | 0.626 | 0.647 | |
| big disagree (>=0.1) | 269 | -0.0768 ±0.0260 | -0.0307 ±0.0109 | -3.0 | 0.586 | 0.636 | |
| tour: atp | 780 | -0.0090 ±0.0073 | -0.0038 ±0.0029 | -1.2 | 0.651 | 0.666 | |
| tour: wta | 836 | -0.0223 ±0.0073 | -0.0092 ±0.0030 | -3.0 | 0.673 | 0.685 | |

When they disagree by >= 0.1: model closer to the outcome in **103/269** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 19 | 0.068 | 0.158 |
| 0.1-0.2 | 102 | 0.152 | 0.186 |
| 0.2-0.3 | 146 | 0.250 | 0.260 |
| 0.3-0.4 | 206 | 0.353 | 0.369 |
| 0.4-0.5 | 276 | 0.451 | 0.464 |
| 0.5-0.6 | 250 | 0.551 | 0.536 |
| 0.6-0.7 | 240 | 0.647 | 0.625 |
| 0.7-0.8 | 194 | 0.752 | 0.773 |
| 0.8-0.9 | 124 | 0.845 | 0.790 |
| 0.9-1.0 | 59 | 0.932 | 0.915 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 43 | 0.058 | 0.093 |
| 0.1-0.2 | 90 | 0.154 | 0.167 |
| 0.2-0.3 | 168 | 0.254 | 0.262 |
| 0.3-0.4 | 200 | 0.354 | 0.390 |
| 0.4-0.5 | 235 | 0.445 | 0.451 |
| 0.5-0.6 | 230 | 0.555 | 0.530 |
| 0.6-0.7 | 242 | 0.649 | 0.628 |
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
| top-20 involved | 580 | -0.0001 ±0.0082 | -0.0013 ±0.0030 | -0.0 | 0.718 | 0.720 | |
| kalshi favorite 0.8-0.9 | 224 | -0.0018 ±0.0157 | -0.0014 ±0.0055 | -0.1 | 0.826 | 0.830 | |
| agree (<0.05) | 872 | -0.0004 ±0.0025 | -0.0005 ±0.0008 | -0.2 | 0.706 | 0.704 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| kalshi favorite 0.5-0.6 | 461 | -0.0226 ±0.0085 | -0.0106 ±0.0040 | -2.6 | 0.507 | 0.543 | |
| big disagree (>=0.1) | 269 | -0.0768 ±0.0260 | -0.0307 ±0.0109 | -3.0 | 0.586 | 0.636 | |
| tour: wta | 836 | -0.0223 ±0.0073 | -0.0092 ±0.0030 | -3.0 | 0.673 | 0.685 | |
| best rank 21-50 | 557 | -0.0280 ±0.0081 | -0.0114 ±0.0035 | -3.5 | 0.657 | 0.698 | |
| no top-20 player | 1036 | -0.0247 ±0.0066 | -0.0096 ±0.0028 | -3.7 | 0.632 | 0.652 | |
| month 2026-09 | 319 | -0.0405 ±0.0103 | -0.0168 ±0.0043 | -3.9 | 0.705 | 0.730 | |
| surface: Hard | 766 | -0.0309 ±0.0078 | -0.0116 ±0.0032 | -4.0 | 0.664 | 0.678 | |
| pred_source: live aligned | 680 | -0.0386 ±0.0082 | -0.0147 ±0.0034 | -4.7 | 0.668 | 0.688 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1616, mean |Δ|=0.0061, p95=0.0100, >0.05 in 38 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0666 (n=319, >0.05: 19) | 2026-10 p95=0.2130 (n=157, >0.05: 17)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1618, d_ll -0.0159 ±0.0052
- Unmatched qualifying markets: 622 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'WTA Seoul': 3, 'ATP Chengdu': 1}
- Unmatched Kalshi names, main draw (40): Akasha Urhobo, Aleksandr Shevchenko, Alevtina Ibragimova, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari
