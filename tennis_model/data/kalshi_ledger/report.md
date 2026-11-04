# Model vs Kalshi — match-by-match scorecard

_Generated 2026-11-04T07:11:12Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 2375 | 2273 | 14 | 16 | 72 | 0 | 15 | 31 | 60 | 2026-05-03..2026-11-04 |
| wta | 2524 | 1512 | 23 | 910 | 79 | 0 | 12 | 23 | 44 | 2026-05-02..2026-11-05 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1853 | 0.6118 | 0.5903 | -0.0215 ±0.0051 | -0.0087 ±0.0021 | 0.659 | 0.675 |
| atp | 934 | 0.6212 | 0.6100 | -0.0113 ±0.0067 | -0.0047 ±0.0027 | 0.645 | 0.664 |
| wta | 919 | 0.6022 | 0.5703 | -0.0319 ±0.0077 | -0.0128 ±0.0032 | 0.674 | 0.686 |
| pooled/live_aligned | 915 | 0.6179 | 0.5747 | -0.0432 ±0.0077 | -0.0164 ±0.0031 | 0.659 | 0.683 |
| pooled/backtest | 938 | 0.6059 | 0.6056 | -0.0003 ±0.0066 | -0.0011 ±0.0027 | 0.659 | 0.667 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 915 | -0.0432 ±0.0077 | -0.0164 ±0.0031 | -5.6 | 0.659 | 0.683 | |
| pred_source: backtest | 938 | -0.0003 ±0.0066 | -0.0011 ±0.0027 | -0.1 | 0.659 | 0.667 | |
| top-20 involved | 668 | +0.0006 ±0.0076 | -0.0006 ±0.0028 | +0.1 | 0.725 | 0.727 | |
| no top-20 player | 1185 | -0.0339 ±0.0067 | -0.0133 ±0.0028 | -5.1 | 0.622 | 0.646 | |
| both inside top-50 | 489 | -0.0153 ±0.0095 | -0.0058 ±0.0040 | -1.6 | 0.637 | 0.645 | |
| someone outside top-50 | 1364 | -0.0237 ±0.0060 | -0.0097 ±0.0024 | -3.9 | 0.667 | 0.685 | |
| best rank 1-10 | 386 | +0.0106 ±0.0099 | +0.0029 ±0.0033 | +1.1 | 0.741 | 0.738 | |
| best rank 11-20 | 282 | -0.0131 ±0.0119 | -0.0053 ±0.0047 | -1.1 | 0.704 | 0.711 | |
| best rank 21-50 | 627 | -0.0319 ±0.0081 | -0.0128 ±0.0035 | -4.0 | 0.651 | 0.692 | |
| best rank 51-100 | 450 | -0.0318 ±0.0116 | -0.0123 ±0.0048 | -2.7 | 0.592 | 0.599 | |
| best rank 100+ | 108 | -0.0543 ±0.0296 | -0.0197 ±0.0126 | -1.8 | 0.574 | 0.569 | |
| kalshi favorite 0.5-0.6 | 514 | -0.0259 ±0.0085 | -0.0120 ±0.0039 | -3.1 | 0.503 | 0.540 | |
| kalshi favorite 0.6-0.7 | 526 | -0.0122 ±0.0085 | -0.0048 ±0.0038 | -1.4 | 0.610 | 0.612 | |
| kalshi favorite 0.7-0.8 | 435 | -0.0162 ±0.0108 | -0.0058 ±0.0043 | -1.5 | 0.728 | 0.738 | |
| kalshi favorite 0.8-0.9 | 250 | -0.0040 ±0.0142 | -0.0023 ±0.0050 | -0.3 | 0.836 | 0.840 | |
| kalshi favorite 0.9-1.0 | 128 | -0.0940 ±0.0304 | -0.0336 ±0.0100 | -3.1 | 0.906 | 0.938 | |
| surface: Hard | 1003 | -0.0377 ±0.0074 | -0.0142 ±0.0030 | -5.1 | 0.657 | 0.675 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 740 | -0.0333 ±0.0091 | -0.0128 ±0.0037 | -3.7 | 0.614 | 0.636 | |
| tier: atp500 | 278 | -0.0183 ±0.0117 | -0.0074 ±0.0051 | -1.6 | 0.644 | 0.653 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 324 | -0.0171 ±0.0108 | -0.0058 ±0.0046 | -1.6 | 0.659 | 0.673 | |
| round early (R128-R64) | 664 | -0.0206 ±0.0081 | -0.0084 ±0.0032 | -2.5 | 0.709 | 0.723 | |
| round late (QF-F) | 268 | -0.0110 ±0.0126 | -0.0046 ±0.0054 | -0.9 | 0.642 | 0.642 | |
| round mid (R32-R16) | 899 | -0.0257 ±0.0078 | -0.0102 ±0.0032 | -3.3 | 0.631 | 0.652 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 320 | -0.0429 ±0.0105 | -0.0177 ±0.0044 | -4.1 | 0.703 | 0.728 | |
| month 2026-10 | 346 | -0.0523 ±0.0162 | -0.0189 ±0.0065 | -3.2 | 0.639 | 0.669 | |
| month 2026-11 | 47 | -0.0719 ±0.0293 | -0.0267 ±0.0117 | -2.5 | 0.638 | 0.681 | ⚠ small n |
| agree (<0.05) | 968 | -0.0010 ±0.0024 | -0.0008 ±0.0008 | -0.4 | 0.697 | 0.696 | |
| mild disagree (0.05-0.10) | 550 | -0.0082 ±0.0075 | -0.0036 ±0.0029 | -1.1 | 0.643 | 0.661 | |
| big disagree (>=0.1) | 335 | -0.1027 ±0.0240 | -0.0399 ±0.0100 | -4.3 | 0.575 | 0.636 | |
| tour: atp | 934 | -0.0113 ±0.0067 | -0.0047 ±0.0027 | -1.7 | 0.645 | 0.664 | |
| tour: wta | 919 | -0.0319 ±0.0077 | -0.0128 ±0.0032 | -4.2 | 0.674 | 0.686 | |

When they disagree by >= 0.1: model closer to the outcome in **125/335** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 21 | 0.071 | 0.190 |
| 0.1-0.2 | 119 | 0.152 | 0.176 |
| 0.2-0.3 | 170 | 0.250 | 0.253 |
| 0.3-0.4 | 250 | 0.352 | 0.380 |
| 0.4-0.5 | 313 | 0.451 | 0.479 |
| 0.5-0.6 | 277 | 0.551 | 0.545 |
| 0.6-0.7 | 264 | 0.647 | 0.610 |
| 0.7-0.8 | 221 | 0.751 | 0.774 |
| 0.8-0.9 | 151 | 0.845 | 0.775 |
| 0.9-1.0 | 67 | 0.931 | 0.910 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 49 | 0.055 | 0.082 |
| 0.1-0.2 | 101 | 0.155 | 0.158 |
| 0.2-0.3 | 197 | 0.252 | 0.264 |
| 0.3-0.4 | 245 | 0.353 | 0.400 |
| 0.4-0.5 | 260 | 0.445 | 0.454 |
| 0.5-0.6 | 258 | 0.554 | 0.527 |
| 0.6-0.7 | 277 | 0.649 | 0.628 |
| 0.7-0.8 | 238 | 0.748 | 0.739 |
| 0.8-0.9 | 150 | 0.847 | 0.840 |
| 0.9-1.0 | 78 | 0.936 | 0.949 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 386 | +0.0106 ±0.0099 | +0.0029 ±0.0033 | +1.1 | 0.741 | 0.738 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| top-20 involved | 668 | +0.0006 ±0.0076 | -0.0006 ±0.0028 | +0.1 | 0.725 | 0.727 | |
| pred_source: backtest | 938 | -0.0003 ±0.0066 | -0.0011 ±0.0027 | -0.1 | 0.659 | 0.667 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| kalshi favorite 0.8-0.9 | 250 | -0.0040 ±0.0142 | -0.0023 ±0.0050 | -0.3 | 0.836 | 0.840 | |
| agree (<0.05) | 968 | -0.0010 ±0.0024 | -0.0008 ±0.0008 | -0.4 | 0.697 | 0.696 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| someone outside top-50 | 1364 | -0.0237 ±0.0060 | -0.0097 ±0.0024 | -3.9 | 0.667 | 0.685 | |
| best rank 21-50 | 627 | -0.0319 ±0.0081 | -0.0128 ±0.0035 | -4.0 | 0.651 | 0.692 | |
| month 2026-09 | 320 | -0.0429 ±0.0105 | -0.0177 ±0.0044 | -4.1 | 0.703 | 0.728 | |
| tour: wta | 919 | -0.0319 ±0.0077 | -0.0128 ±0.0032 | -4.2 | 0.674 | 0.686 | |
| big disagree (>=0.1) | 335 | -0.1027 ±0.0240 | -0.0399 ±0.0100 | -4.3 | 0.575 | 0.636 | |
| no top-20 player | 1185 | -0.0339 ±0.0067 | -0.0133 ±0.0028 | -5.1 | 0.622 | 0.646 | |
| surface: Hard | 1003 | -0.0377 ±0.0074 | -0.0142 ±0.0030 | -5.1 | 0.657 | 0.675 | |
| pred_source: live aligned | 915 | -0.0432 ±0.0077 | -0.0164 ±0.0031 | -5.6 | 0.659 | 0.683 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1853, mean |Δ|=0.0066, p95=0.0124, >0.05 in 52 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0660 (n=320, >0.05: 19) | 2026-10 p95=0.1324 (n=346, >0.05: 29) | 2026-11 p95=0.0070 (n=47, >0.05: 2)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1866, d_ll -0.0216 ±0.0051
- Unmatched qualifying markets: 712 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'Billie Jean King Cup Qualifiers Round': 56, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): AYNUR MOVLYAMOVA, Aishath Karin Saizan, Akasha Urhobo, Aleksandr Shevchenko, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Abualhaj, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Aylara Kakabayeva, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao
