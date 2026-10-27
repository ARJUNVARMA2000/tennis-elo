# Model vs Kalshi — match-by-match scorecard

_Generated 2026-10-27T11:46:50Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 2283 | 2175 | 24 | 15 | 69 | 0 | 15 | 27 | 53 | 2026-05-03..2026-10-28 |
| wta | 2431 | 1449 | 65 | 844 | 73 | 0 | 10 | 22 | 42 | 2026-05-02..2026-10-28 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1738 | 0.6107 | 0.5931 | -0.0176 ±0.0051 | -0.0073 ±0.0021 | 0.659 | 0.673 |
| atp | 865 | 0.6235 | 0.6118 | -0.0117 ±0.0070 | -0.0049 ±0.0028 | 0.644 | 0.660 |
| wta | 873 | 0.5980 | 0.5747 | -0.0233 ±0.0075 | -0.0097 ±0.0031 | 0.674 | 0.686 |
| pooled/live_aligned | 801 | 0.6158 | 0.5780 | -0.0378 ±0.0079 | -0.0146 ±0.0033 | 0.659 | 0.680 |
| pooled/backtest | 937 | 0.6064 | 0.6061 | -0.0002 ±0.0067 | -0.0011 ±0.0027 | 0.658 | 0.666 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 801 | -0.0378 ±0.0079 | -0.0146 ±0.0033 | -4.8 | 0.659 | 0.680 | |
| pred_source: backtest | 937 | -0.0002 ±0.0067 | -0.0011 ±0.0027 | -0.0 | 0.658 | 0.666 | |
| top-20 involved | 617 | +0.0006 ±0.0078 | -0.0009 ±0.0029 | +0.1 | 0.724 | 0.724 | |
| no top-20 player | 1121 | -0.0276 ±0.0067 | -0.0109 ±0.0028 | -4.1 | 0.623 | 0.645 | |
| both inside top-50 | 446 | -0.0161 ±0.0100 | -0.0063 ±0.0042 | -1.6 | 0.640 | 0.645 | |
| someone outside top-50 | 1292 | -0.0181 ±0.0060 | -0.0077 ±0.0024 | -3.0 | 0.665 | 0.683 | |
| best rank 1-10 | 360 | +0.0109 ±0.0102 | +0.0027 ±0.0035 | +1.1 | 0.736 | 0.731 | |
| best rank 11-20 | 257 | -0.0138 ±0.0122 | -0.0061 ±0.0050 | -1.1 | 0.706 | 0.714 | |
| best rank 21-50 | 604 | -0.0305 ±0.0082 | -0.0123 ±0.0035 | -3.7 | 0.654 | 0.694 | |
| best rank 51-100 | 421 | -0.0195 ±0.0112 | -0.0075 ±0.0047 | -1.7 | 0.588 | 0.588 | |
| best rank 100+ | 96 | -0.0446 ±0.0314 | -0.0166 ±0.0134 | -1.4 | 0.583 | 0.589 | |
| kalshi favorite 0.5-0.6 | 491 | -0.0256 ±0.0085 | -0.0119 ±0.0039 | -3.0 | 0.498 | 0.535 | |
| kalshi favorite 0.6-0.7 | 490 | -0.0115 ±0.0088 | -0.0045 ±0.0040 | -1.3 | 0.614 | 0.616 | |
| kalshi favorite 0.7-0.8 | 407 | -0.0106 ±0.0106 | -0.0040 ±0.0044 | -1.0 | 0.733 | 0.742 | |
| kalshi favorite 0.8-0.9 | 233 | -0.0038 ±0.0152 | -0.0022 ±0.0053 | -0.3 | 0.828 | 0.833 | |
| kalshi favorite 0.9-1.0 | 117 | -0.0606 ±0.0296 | -0.0219 ±0.0092 | -2.0 | 0.923 | 0.932 | |
| surface: Hard | 888 | -0.0322 ±0.0076 | -0.0123 ±0.0031 | -4.2 | 0.657 | 0.671 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 631 | -0.0262 ±0.0095 | -0.0104 ±0.0039 | -2.8 | 0.609 | 0.628 | |
| tier: atp500 | 272 | -0.0142 ±0.0114 | -0.0061 ±0.0051 | -1.2 | 0.636 | 0.645 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 324 | -0.0171 ±0.0108 | -0.0058 ±0.0046 | -1.6 | 0.659 | 0.673 | |
| round early (R128-R64) | 646 | -0.0208 ±0.0083 | -0.0085 ±0.0032 | -2.5 | 0.710 | 0.723 | |
| round late (QF-F) | 245 | -0.0024 ±0.0114 | -0.0013 ±0.0051 | -0.2 | 0.641 | 0.637 | |
| round mid (R32-R16) | 825 | -0.0199 ±0.0079 | -0.0084 ±0.0033 | -2.5 | 0.628 | 0.648 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 320 | -0.0429 ±0.0105 | -0.0177 ±0.0044 | -4.1 | 0.703 | 0.728 | |
| month 2026-10 | 278 | -0.0439 ±0.0175 | -0.0160 ±0.0072 | -2.5 | 0.629 | 0.656 | |
| agree (<0.05) | 923 | -0.0010 ±0.0024 | -0.0008 ±0.0008 | -0.4 | 0.700 | 0.699 | |
| mild disagree (0.05-0.10) | 516 | -0.0098 ±0.0078 | -0.0044 ±0.0030 | -1.3 | 0.637 | 0.656 | |
| big disagree (>=0.1) | 299 | -0.0820 ±0.0253 | -0.0327 ±0.0107 | -3.2 | 0.570 | 0.622 | |
| tour: atp | 865 | -0.0117 ±0.0070 | -0.0049 ±0.0028 | -1.7 | 0.644 | 0.660 | |
| tour: wta | 873 | -0.0233 ±0.0075 | -0.0097 ±0.0031 | -3.1 | 0.674 | 0.686 | |

When they disagree by >= 0.1: model closer to the outcome in **115/299** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 19 | 0.068 | 0.158 |
| 0.1-0.2 | 110 | 0.152 | 0.191 |
| 0.2-0.3 | 158 | 0.250 | 0.259 |
| 0.3-0.4 | 231 | 0.352 | 0.372 |
| 0.4-0.5 | 297 | 0.451 | 0.481 |
| 0.5-0.6 | 265 | 0.551 | 0.543 |
| 0.6-0.7 | 252 | 0.647 | 0.615 |
| 0.7-0.8 | 207 | 0.752 | 0.778 |
| 0.8-0.9 | 137 | 0.845 | 0.781 |
| 0.9-1.0 | 62 | 0.932 | 0.919 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 44 | 0.058 | 0.091 |
| 0.1-0.2 | 92 | 0.154 | 0.163 |
| 0.2-0.3 | 184 | 0.253 | 0.261 |
| 0.3-0.4 | 227 | 0.353 | 0.396 |
| 0.4-0.5 | 250 | 0.445 | 0.464 |
| 0.5-0.6 | 245 | 0.555 | 0.527 |
| 0.6-0.7 | 259 | 0.649 | 0.633 |
| 0.7-0.8 | 223 | 0.748 | 0.744 |
| 0.8-0.9 | 142 | 0.846 | 0.831 |
| 0.9-1.0 | 72 | 0.934 | 0.944 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 360 | +0.0109 ±0.0102 | +0.0027 ±0.0035 | +1.1 | 0.736 | 0.731 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| top-20 involved | 617 | +0.0006 ±0.0078 | -0.0009 ±0.0029 | +0.1 | 0.724 | 0.724 | |
| pred_source: backtest | 937 | -0.0002 ±0.0067 | -0.0011 ±0.0027 | -0.0 | 0.658 | 0.666 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| round late (QF-F) | 245 | -0.0024 ±0.0114 | -0.0013 ±0.0051 | -0.2 | 0.641 | 0.637 | |
| kalshi favorite 0.8-0.9 | 233 | -0.0038 ±0.0152 | -0.0022 ±0.0053 | -0.3 | 0.828 | 0.833 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| someone outside top-50 | 1292 | -0.0181 ±0.0060 | -0.0077 ±0.0024 | -3.0 | 0.665 | 0.683 | |
| tour: wta | 873 | -0.0233 ±0.0075 | -0.0097 ±0.0031 | -3.1 | 0.674 | 0.686 | |
| big disagree (>=0.1) | 299 | -0.0820 ±0.0253 | -0.0327 ±0.0107 | -3.2 | 0.570 | 0.622 | |
| best rank 21-50 | 604 | -0.0305 ±0.0082 | -0.0123 ±0.0035 | -3.7 | 0.654 | 0.694 | |
| month 2026-09 | 320 | -0.0429 ±0.0105 | -0.0177 ±0.0044 | -4.1 | 0.703 | 0.728 | |
| no top-20 player | 1121 | -0.0276 ±0.0067 | -0.0109 ±0.0028 | -4.1 | 0.623 | 0.645 | |
| surface: Hard | 888 | -0.0322 ±0.0076 | -0.0123 ±0.0031 | -4.2 | 0.657 | 0.671 | |
| pred_source: live aligned | 801 | -0.0378 ±0.0079 | -0.0146 ±0.0033 | -4.8 | 0.659 | 0.680 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1738, mean |Δ|=0.0066, p95=0.0119, >0.05 in 47 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0660 (n=320, >0.05: 19) | 2026-10 p95=0.1434 (n=278, >0.05: 26)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1746, d_ll -0.0176 ±0.0051
- Unmatched qualifying markets: 660 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'Billie Jean King Cup Qualifiers Round': 42, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): AYNUR MOVLYAMOVA, Aishath Karin Saizan, Akasha Urhobo, Aleksandr Shevchenko, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Abualhaj, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Aylara Kakabayeva, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao
