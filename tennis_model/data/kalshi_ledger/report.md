# Model vs Kalshi — match-by-match scorecard

_Generated 2026-10-23T08:16:51Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 2211 | 2120 | 12 | 15 | 64 | 0 | 14 | 25 | 57 | 2026-05-03..2026-10-23 |
| wta | 2331 | 1412 | 47 | 804 | 68 | 0 | 10 | 22 | 38 | 2026-05-02..2026-10-24 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1690 | 0.6107 | 0.5931 | -0.0177 ±0.0051 | -0.0074 ±0.0021 | 0.658 | 0.672 |
| atp | 837 | 0.6241 | 0.6119 | -0.0121 ±0.0072 | -0.0052 ±0.0029 | 0.643 | 0.658 |
| wta | 853 | 0.5977 | 0.5746 | -0.0231 ±0.0073 | -0.0096 ±0.0030 | 0.673 | 0.687 |
| pooled/live_aligned | 754 | 0.6176 | 0.5772 | -0.0404 ±0.0079 | -0.0157 ±0.0033 | 0.656 | 0.679 |
| pooled/backtest | 936 | 0.6053 | 0.6059 | +0.0006 ±0.0066 | -0.0008 ±0.0027 | 0.659 | 0.667 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 754 | -0.0404 ±0.0079 | -0.0157 ±0.0033 | -5.1 | 0.656 | 0.679 | |
| pred_source: backtest | 936 | +0.0006 ±0.0066 | -0.0008 ±0.0027 | +0.1 | 0.659 | 0.667 | |
| top-20 involved | 594 | +0.0001 ±0.0081 | -0.0012 ±0.0030 | +0.0 | 0.721 | 0.723 | |
| no top-20 player | 1096 | -0.0273 ±0.0065 | -0.0108 ±0.0028 | -4.2 | 0.624 | 0.645 | |
| both inside top-50 | 426 | -0.0200 ±0.0102 | -0.0082 ±0.0043 | -2.0 | 0.637 | 0.647 | |
| someone outside top-50 | 1264 | -0.0169 ±0.0059 | -0.0071 ±0.0024 | -2.9 | 0.665 | 0.681 | |
| best rank 1-10 | 350 | +0.0103 ±0.0104 | +0.0024 ±0.0035 | +1.0 | 0.734 | 0.731 | |
| best rank 11-20 | 244 | -0.0144 ±0.0128 | -0.0062 ±0.0052 | -1.1 | 0.703 | 0.711 | |
| best rank 21-50 | 587 | -0.0309 ±0.0080 | -0.0126 ±0.0034 | -3.9 | 0.652 | 0.693 | |
| best rank 51-100 | 416 | -0.0208 ±0.0110 | -0.0079 ±0.0046 | -1.9 | 0.590 | 0.588 | |
| best rank 100+ | 93 | -0.0342 ±0.0313 | -0.0123 ±0.0134 | -1.1 | 0.591 | 0.597 | |
| kalshi favorite 0.5-0.6 | 483 | -0.0253 ±0.0085 | -0.0119 ±0.0039 | -3.0 | 0.498 | 0.535 | |
| kalshi favorite 0.6-0.7 | 470 | -0.0122 ±0.0090 | -0.0047 ±0.0040 | -1.4 | 0.611 | 0.613 | |
| kalshi favorite 0.7-0.8 | 394 | -0.0108 ±0.0100 | -0.0041 ±0.0040 | -1.1 | 0.735 | 0.744 | |
| kalshi favorite 0.8-0.9 | 227 | -0.0024 ±0.0155 | -0.0017 ±0.0054 | -0.2 | 0.828 | 0.833 | |
| kalshi favorite 0.9-1.0 | 116 | -0.0615 ±0.0299 | -0.0221 ±0.0093 | -2.1 | 0.922 | 0.931 | |
| surface: Hard | 840 | -0.0332 ±0.0076 | -0.0127 ±0.0031 | -4.4 | 0.655 | 0.670 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 594 | -0.0261 ±0.0097 | -0.0103 ±0.0040 | -2.7 | 0.606 | 0.623 | |
| tier: atp500 | 261 | -0.0164 ±0.0103 | -0.0072 ±0.0045 | -1.6 | 0.628 | 0.646 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 324 | -0.0171 ±0.0108 | -0.0058 ±0.0046 | -1.6 | 0.659 | 0.673 | |
| round early (R128-R64) | 646 | -0.0208 ±0.0083 | -0.0085 ±0.0032 | -2.5 | 0.710 | 0.723 | |
| round late (QF-F) | 218 | -0.0066 ±0.0115 | -0.0036 ±0.0051 | -0.6 | 0.633 | 0.642 | |
| round mid (R32-R16) | 804 | -0.0185 ±0.0078 | -0.0077 ±0.0032 | -2.4 | 0.627 | 0.644 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 319 | -0.0405 ±0.0103 | -0.0168 ±0.0043 | -3.9 | 0.705 | 0.730 | |
| month 2026-10 | 231 | -0.0534 ±0.0189 | -0.0196 ±0.0077 | -2.8 | 0.615 | 0.647 | |
| agree (<0.05) | 903 | -0.0009 ±0.0025 | -0.0007 ±0.0008 | -0.4 | 0.699 | 0.697 | |
| mild disagree (0.05-0.10) | 500 | -0.0104 ±0.0079 | -0.0047 ±0.0030 | -1.3 | 0.633 | 0.653 | |
| big disagree (>=0.1) | 287 | -0.0831 ±0.0252 | -0.0334 ±0.0107 | -3.3 | 0.573 | 0.631 | |
| tour: atp | 837 | -0.0121 ±0.0072 | -0.0052 ±0.0029 | -1.7 | 0.643 | 0.658 | |
| tour: wta | 853 | -0.0231 ±0.0073 | -0.0096 ±0.0030 | -3.2 | 0.673 | 0.687 | |

When they disagree by >= 0.1: model closer to the outcome in **109/287** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 19 | 0.068 | 0.158 |
| 0.1-0.2 | 107 | 0.151 | 0.187 |
| 0.2-0.3 | 155 | 0.251 | 0.258 |
| 0.3-0.4 | 219 | 0.353 | 0.384 |
| 0.4-0.5 | 291 | 0.451 | 0.474 |
| 0.5-0.6 | 260 | 0.552 | 0.535 |
| 0.6-0.7 | 247 | 0.647 | 0.619 |
| 0.7-0.8 | 201 | 0.752 | 0.776 |
| 0.8-0.9 | 131 | 0.845 | 0.786 |
| 0.9-1.0 | 60 | 0.932 | 0.917 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 44 | 0.058 | 0.091 |
| 0.1-0.2 | 91 | 0.154 | 0.165 |
| 0.2-0.3 | 178 | 0.254 | 0.258 |
| 0.3-0.4 | 215 | 0.354 | 0.400 |
| 0.4-0.5 | 247 | 0.445 | 0.462 |
| 0.5-0.6 | 240 | 0.555 | 0.525 |
| 0.6-0.7 | 251 | 0.649 | 0.629 |
| 0.7-0.8 | 216 | 0.749 | 0.745 |
| 0.8-0.9 | 137 | 0.846 | 0.832 |
| 0.9-1.0 | 71 | 0.934 | 0.944 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 350 | +0.0103 ±0.0104 | +0.0024 ±0.0035 | +1.0 | 0.734 | 0.731 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 936 | +0.0006 ±0.0066 | -0.0008 ±0.0027 | +0.1 | 0.659 | 0.667 | |
| top-20 involved | 594 | +0.0001 ±0.0081 | -0.0012 ±0.0030 | +0.0 | 0.721 | 0.723 | |
| kalshi favorite 0.8-0.9 | 227 | -0.0024 ±0.0155 | -0.0017 ±0.0054 | -0.2 | 0.828 | 0.833 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| agree (<0.05) | 903 | -0.0009 ±0.0025 | -0.0007 ±0.0008 | -0.4 | 0.699 | 0.697 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| kalshi favorite 0.5-0.6 | 483 | -0.0253 ±0.0085 | -0.0119 ±0.0039 | -3.0 | 0.498 | 0.535 | |
| tour: wta | 853 | -0.0231 ±0.0073 | -0.0096 ±0.0030 | -3.2 | 0.673 | 0.687 | |
| big disagree (>=0.1) | 287 | -0.0831 ±0.0252 | -0.0334 ±0.0107 | -3.3 | 0.573 | 0.631 | |
| best rank 21-50 | 587 | -0.0309 ±0.0080 | -0.0126 ±0.0034 | -3.9 | 0.652 | 0.693 | |
| month 2026-09 | 319 | -0.0405 ±0.0103 | -0.0168 ±0.0043 | -3.9 | 0.705 | 0.730 | |
| no top-20 player | 1096 | -0.0273 ±0.0065 | -0.0108 ±0.0028 | -4.2 | 0.624 | 0.645 | |
| surface: Hard | 840 | -0.0332 ±0.0076 | -0.0127 ±0.0031 | -4.4 | 0.655 | 0.670 | |
| pred_source: live aligned | 754 | -0.0404 ±0.0079 | -0.0157 ±0.0033 | -5.1 | 0.656 | 0.679 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1690, mean |Δ|=0.0063, p95=0.0100, >0.05 in 42 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0666 (n=319, >0.05: 19) | 2026-10 p95=0.1516 (n=231, >0.05: 21)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1696, d_ll -0.0178 ±0.0051
- Unmatched qualifying markets: 660 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'WTA Seoul': 3, 'ATP Chengdu': 1}
- Unmatched Kalshi names, main draw (40): Akasha Urhobo, Aleksandr Shevchenko, Alevtina Ibragimova, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari
