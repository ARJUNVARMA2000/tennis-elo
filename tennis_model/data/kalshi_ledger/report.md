# Model vs Kalshi — match-by-match scorecard

_Generated 2026-10-16T10:50:54Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 2099 | 2022 | 2 | 13 | 62 | 0 | 12 | 24 | 46 | 2026-05-03..2026-10-17 |
| wta | 2217 | 1360 | 26 | 768 | 63 | 0 | 10 | 16 | 55 | 2026-05-02..2026-10-17 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1610 | 0.6071 | 0.5911 | -0.0161 ±0.0052 | -0.0067 ±0.0021 | 0.663 | 0.677 |
| atp | 777 | 0.6187 | 0.6098 | -0.0090 ±0.0073 | -0.0038 ±0.0029 | 0.653 | 0.667 |
| wta | 833 | 0.5963 | 0.5736 | -0.0227 ±0.0074 | -0.0094 ±0.0031 | 0.673 | 0.685 |
| pooled/live_aligned | 674 | 0.6098 | 0.5706 | -0.0392 ±0.0083 | -0.0149 ±0.0034 | 0.669 | 0.690 |
| pooled/backtest | 936 | 0.6053 | 0.6059 | +0.0006 ±0.0066 | -0.0008 ±0.0027 | 0.659 | 0.667 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 674 | -0.0392 ±0.0083 | -0.0149 ±0.0034 | -4.7 | 0.669 | 0.690 | |
| pred_source: backtest | 936 | +0.0006 ±0.0066 | -0.0008 ±0.0027 | +0.1 | 0.659 | 0.667 | |
| top-20 involved | 575 | -0.0004 ±0.0083 | -0.0014 ±0.0030 | -0.1 | 0.721 | 0.723 | |
| no top-20 player | 1035 | -0.0248 ±0.0066 | -0.0096 ±0.0028 | -3.7 | 0.631 | 0.651 | |
| both inside top-50 | 413 | -0.0205 ±0.0104 | -0.0084 ±0.0044 | -2.0 | 0.640 | 0.650 | |
| someone outside top-50 | 1197 | -0.0145 ±0.0060 | -0.0061 ±0.0024 | -2.4 | 0.671 | 0.686 | |
| best rank 1-10 | 343 | +0.0099 ±0.0105 | +0.0021 ±0.0035 | +0.9 | 0.738 | 0.735 | |
| best rank 11-20 | 232 | -0.0157 ±0.0133 | -0.0066 ±0.0054 | -1.2 | 0.696 | 0.705 | |
| best rank 21-50 | 556 | -0.0280 ±0.0081 | -0.0114 ±0.0035 | -3.5 | 0.656 | 0.698 | |
| best rank 51-100 | 391 | -0.0176 ±0.0112 | -0.0064 ±0.0047 | -1.6 | 0.602 | 0.595 | |
| best rank 100+ | 88 | -0.0357 ±0.0320 | -0.0128 ±0.0136 | -1.1 | 0.602 | 0.608 | |
| kalshi favorite 0.5-0.6 | 460 | -0.0227 ±0.0086 | -0.0106 ±0.0040 | -2.7 | 0.505 | 0.542 | |
| kalshi favorite 0.6-0.7 | 444 | -0.0112 ±0.0091 | -0.0042 ±0.0041 | -1.2 | 0.617 | 0.617 | |
| kalshi favorite 0.7-0.8 | 371 | -0.0078 ±0.0100 | -0.0030 ±0.0041 | -0.8 | 0.737 | 0.744 | |
| kalshi favorite 0.8-0.9 | 223 | -0.0027 ±0.0157 | -0.0017 ±0.0055 | -0.2 | 0.830 | 0.834 | |
| kalshi favorite 0.9-1.0 | 112 | -0.0624 ±0.0309 | -0.0227 ±0.0096 | -2.0 | 0.920 | 0.929 | |
| surface: Hard | 760 | -0.0314 ±0.0079 | -0.0118 ±0.0032 | -4.0 | 0.666 | 0.679 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 529 | -0.0222 ±0.0103 | -0.0085 ±0.0042 | -2.2 | 0.616 | 0.631 | |
| tier: atp500 | 250 | -0.0149 ±0.0103 | -0.0067 ±0.0046 | -1.4 | 0.628 | 0.642 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 320 | -0.0182 ±0.0109 | -0.0061 ±0.0047 | -1.7 | 0.658 | 0.672 | |
| round early (R128-R64) | 646 | -0.0208 ±0.0083 | -0.0085 ±0.0032 | -2.5 | 0.710 | 0.723 | |
| round late (QF-F) | 210 | -0.0069 ±0.0118 | -0.0037 ±0.0053 | -0.6 | 0.638 | 0.648 | |
| round mid (R32-R16) | 732 | -0.0149 ±0.0080 | -0.0061 ±0.0033 | -1.9 | 0.635 | 0.648 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 319 | -0.0405 ±0.0103 | -0.0168 ±0.0043 | -3.9 | 0.705 | 0.730 | |
| month 2026-10 | 151 | -0.0552 ±0.0253 | -0.0184 ±0.0101 | -2.2 | 0.649 | 0.679 | |
| agree (<0.05) | 868 | -0.0003 ±0.0025 | -0.0004 ±0.0008 | -0.1 | 0.707 | 0.705 | |
| mild disagree (0.05-0.10) | 473 | -0.0104 ±0.0083 | -0.0045 ±0.0031 | -1.3 | 0.627 | 0.648 | |
| big disagree (>=0.1) | 269 | -0.0768 ±0.0260 | -0.0307 ±0.0109 | -3.0 | 0.586 | 0.636 | |
| tour: atp | 777 | -0.0090 ±0.0073 | -0.0038 ±0.0029 | -1.2 | 0.653 | 0.667 | |
| tour: wta | 833 | -0.0227 ±0.0074 | -0.0094 ±0.0031 | -3.1 | 0.673 | 0.685 | |

When they disagree by >= 0.1: model closer to the outcome in **103/269** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 19 | 0.068 | 0.158 |
| 0.1-0.2 | 100 | 0.152 | 0.180 |
| 0.2-0.3 | 146 | 0.250 | 0.260 |
| 0.3-0.4 | 206 | 0.353 | 0.369 |
| 0.4-0.5 | 275 | 0.451 | 0.465 |
| 0.5-0.6 | 249 | 0.551 | 0.538 |
| 0.6-0.7 | 239 | 0.647 | 0.623 |
| 0.7-0.8 | 194 | 0.752 | 0.773 |
| 0.8-0.9 | 123 | 0.845 | 0.797 |
| 0.9-1.0 | 59 | 0.932 | 0.915 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 43 | 0.058 | 0.093 |
| 0.1-0.2 | 90 | 0.154 | 0.167 |
| 0.2-0.3 | 166 | 0.255 | 0.259 |
| 0.3-0.4 | 200 | 0.354 | 0.390 |
| 0.4-0.5 | 234 | 0.445 | 0.453 |
| 0.5-0.6 | 230 | 0.555 | 0.530 |
| 0.6-0.7 | 240 | 0.649 | 0.629 |
| 0.7-0.8 | 205 | 0.749 | 0.746 |
| 0.8-0.9 | 134 | 0.847 | 0.836 |
| 0.9-1.0 | 68 | 0.934 | 0.941 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 343 | +0.0099 ±0.0105 | +0.0021 ±0.0035 | +0.9 | 0.738 | 0.735 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 936 | +0.0006 ±0.0066 | -0.0008 ±0.0027 | +0.1 | 0.659 | 0.667 | |
| top-20 involved | 575 | -0.0004 ±0.0083 | -0.0014 ±0.0030 | -0.1 | 0.721 | 0.723 | |
| agree (<0.05) | 868 | -0.0003 ±0.0025 | -0.0004 ±0.0008 | -0.1 | 0.707 | 0.705 | |
| kalshi favorite 0.8-0.9 | 223 | -0.0027 ±0.0157 | -0.0017 ±0.0055 | -0.2 | 0.830 | 0.834 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| kalshi favorite 0.5-0.6 | 460 | -0.0227 ±0.0086 | -0.0106 ±0.0040 | -2.7 | 0.505 | 0.542 | |
| big disagree (>=0.1) | 269 | -0.0768 ±0.0260 | -0.0307 ±0.0109 | -3.0 | 0.586 | 0.636 | |
| tour: wta | 833 | -0.0227 ±0.0074 | -0.0094 ±0.0031 | -3.1 | 0.673 | 0.685 | |
| best rank 21-50 | 556 | -0.0280 ±0.0081 | -0.0114 ±0.0035 | -3.5 | 0.656 | 0.698 | |
| no top-20 player | 1035 | -0.0248 ±0.0066 | -0.0096 ±0.0028 | -3.7 | 0.631 | 0.651 | |
| month 2026-09 | 319 | -0.0405 ±0.0103 | -0.0168 ±0.0043 | -3.9 | 0.705 | 0.730 | |
| surface: Hard | 760 | -0.0314 ±0.0079 | -0.0118 ±0.0032 | -4.0 | 0.666 | 0.679 | |
| pred_source: live aligned | 674 | -0.0392 ±0.0083 | -0.0149 ±0.0034 | -4.7 | 0.669 | 0.690 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1610, mean |Δ|=0.0062, p95=0.0100, >0.05 in 38 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0666 (n=319, >0.05: 19) | 2026-10 p95=0.2176 (n=151, >0.05: 17)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1612, d_ll -0.0161 ±0.0052
- Unmatched qualifying markets: 622 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'WTA Seoul': 3, 'ATP Chengdu': 1}
- Unmatched Kalshi names, main draw (40): Akasha Urhobo, Aleksandr Shevchenko, Alevtina Ibragimova, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari
