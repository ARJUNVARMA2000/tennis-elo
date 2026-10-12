# Model vs Kalshi — match-by-match scorecard

_Generated 2026-10-12T07:50:29Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 2090 | 2003 | 11 | 14 | 62 | 0 | 12 | 22 | 46 | 2026-05-03..2026-10-13 |
| wta | 2164 | 1316 | 46 | 743 | 59 | 0 | 10 | 15 | 35 | 2026-05-02..2026-10-13 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1566 | 0.6020 | 0.5859 | -0.0161 ±0.0052 | -0.0069 ±0.0021 | 0.665 | 0.680 |
| atp | 763 | 0.6161 | 0.6065 | -0.0096 ±0.0073 | -0.0043 ±0.0029 | 0.653 | 0.669 |
| wta | 803 | 0.5887 | 0.5663 | -0.0223 ±0.0075 | -0.0094 ±0.0031 | 0.677 | 0.690 |
| pooled/live_aligned | 632 | 0.5969 | 0.5558 | -0.0411 ±0.0084 | -0.0162 ±0.0034 | 0.676 | 0.699 |
| pooled/backtest | 934 | 0.6055 | 0.6062 | +0.0008 ±0.0066 | -0.0007 ±0.0027 | 0.658 | 0.666 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 632 | -0.0411 ±0.0084 | -0.0162 ±0.0034 | -4.9 | 0.676 | 0.699 | |
| pred_source: backtest | 934 | +0.0008 ±0.0066 | -0.0007 ±0.0027 | +0.1 | 0.658 | 0.666 | |
| top-20 involved | 553 | -0.0011 ±0.0082 | -0.0023 ±0.0030 | -0.1 | 0.728 | 0.733 | |
| no top-20 player | 1013 | -0.0244 ±0.0067 | -0.0095 ±0.0028 | -3.6 | 0.631 | 0.651 | |
| both inside top-50 | 392 | -0.0191 ±0.0105 | -0.0085 ±0.0044 | -1.8 | 0.654 | 0.665 | |
| someone outside top-50 | 1174 | -0.0151 ±0.0060 | -0.0064 ±0.0024 | -2.5 | 0.669 | 0.685 | |
| best rank 1-10 | 332 | +0.0130 ±0.0103 | +0.0025 ±0.0035 | +1.3 | 0.744 | 0.744 | |
| best rank 11-20 | 221 | -0.0223 ±0.0134 | -0.0094 ±0.0054 | -1.7 | 0.704 | 0.717 | |
| best rank 21-50 | 539 | -0.0272 ±0.0082 | -0.0110 ±0.0035 | -3.3 | 0.657 | 0.698 | |
| best rank 51-100 | 386 | -0.0177 ±0.0112 | -0.0066 ±0.0047 | -1.6 | 0.602 | 0.595 | |
| best rank 100+ | 88 | -0.0357 ±0.0320 | -0.0128 ±0.0136 | -1.1 | 0.602 | 0.608 | |
| kalshi favorite 0.5-0.6 | 447 | -0.0244 ±0.0086 | -0.0113 ±0.0040 | -2.8 | 0.502 | 0.540 | |
| kalshi favorite 0.6-0.7 | 432 | -0.0126 ±0.0092 | -0.0048 ±0.0041 | -1.4 | 0.618 | 0.620 | |
| kalshi favorite 0.7-0.8 | 360 | -0.0068 ±0.0098 | -0.0028 ±0.0040 | -0.7 | 0.743 | 0.750 | |
| kalshi favorite 0.8-0.9 | 216 | -0.0007 ±0.0161 | -0.0010 ±0.0056 | -0.0 | 0.833 | 0.838 | |
| kalshi favorite 0.9-1.0 | 111 | -0.0575 ±0.0308 | -0.0222 ±0.0097 | -1.9 | 0.928 | 0.937 | |
| surface: Hard | 716 | -0.0325 ±0.0080 | -0.0126 ±0.0033 | -4.1 | 0.670 | 0.686 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 515 | -0.0235 ±0.0103 | -0.0094 ±0.0042 | -2.3 | 0.616 | 0.633 | |
| tier: atp500 | 250 | -0.0149 ±0.0103 | -0.0067 ±0.0046 | -1.4 | 0.628 | 0.642 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 290 | -0.0167 ±0.0111 | -0.0058 ±0.0048 | -1.5 | 0.667 | 0.683 | |
| round early (R128-R64) | 631 | -0.0212 ±0.0085 | -0.0085 ±0.0033 | -2.5 | 0.711 | 0.723 | |
| round late (QF-F) | 207 | -0.0088 ±0.0112 | -0.0046 ±0.0050 | -0.8 | 0.638 | 0.647 | |
| round mid (R32-R16) | 706 | -0.0141 ±0.0081 | -0.0063 ±0.0033 | -1.7 | 0.638 | 0.655 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 319 | -0.0405 ±0.0103 | -0.0168 ±0.0043 | -3.9 | 0.705 | 0.730 | |
| month 2026-10 | 107 | -0.0723 ±0.0318 | -0.0270 ±0.0126 | -2.3 | 0.673 | 0.724 | |
| agree (<0.05) | 845 | +0.0006 ±0.0024 | -0.0003 ±0.0008 | +0.3 | 0.710 | 0.708 | |
| mild disagree (0.05-0.10) | 462 | -0.0099 ±0.0083 | -0.0045 ±0.0032 | -1.2 | 0.629 | 0.653 | |
| big disagree (>=0.1) | 259 | -0.0820 ±0.0264 | -0.0329 ±0.0111 | -3.1 | 0.585 | 0.637 | |
| tour: atp | 763 | -0.0096 ±0.0073 | -0.0043 ±0.0029 | -1.3 | 0.653 | 0.669 | |
| tour: wta | 803 | -0.0223 ±0.0075 | -0.0094 ±0.0031 | -3.0 | 0.677 | 0.690 | |

When they disagree by >= 0.1: model closer to the outcome in **98/259** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 17 | 0.066 | 0.176 |
| 0.1-0.2 | 94 | 0.152 | 0.149 |
| 0.2-0.3 | 142 | 0.250 | 0.261 |
| 0.3-0.4 | 200 | 0.354 | 0.365 |
| 0.4-0.5 | 268 | 0.451 | 0.463 |
| 0.5-0.6 | 244 | 0.552 | 0.537 |
| 0.6-0.7 | 232 | 0.647 | 0.616 |
| 0.7-0.8 | 190 | 0.751 | 0.774 |
| 0.8-0.9 | 121 | 0.846 | 0.802 |
| 0.9-1.0 | 58 | 0.931 | 0.931 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 43 | 0.058 | 0.093 |
| 0.1-0.2 | 85 | 0.154 | 0.153 |
| 0.2-0.3 | 161 | 0.255 | 0.255 |
| 0.3-0.4 | 193 | 0.354 | 0.378 |
| 0.4-0.5 | 229 | 0.444 | 0.454 |
| 0.5-0.6 | 222 | 0.555 | 0.527 |
| 0.6-0.7 | 235 | 0.649 | 0.626 |
| 0.7-0.8 | 199 | 0.749 | 0.754 |
| 0.8-0.9 | 132 | 0.846 | 0.833 |
| 0.9-1.0 | 67 | 0.934 | 0.955 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 332 | +0.0130 ±0.0103 | +0.0025 ±0.0035 | +1.3 | 0.744 | 0.744 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| agree (<0.05) | 845 | +0.0006 ±0.0024 | -0.0003 ±0.0008 | +0.3 | 0.710 | 0.708 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 934 | +0.0008 ±0.0066 | -0.0007 ±0.0027 | +0.1 | 0.658 | 0.666 | |
| kalshi favorite 0.8-0.9 | 216 | -0.0007 ±0.0161 | -0.0010 ±0.0056 | -0.0 | 0.833 | 0.838 | |
| top-20 involved | 553 | -0.0011 ±0.0082 | -0.0023 ±0.0030 | -0.1 | 0.728 | 0.733 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| kalshi favorite 0.5-0.6 | 447 | -0.0244 ±0.0086 | -0.0113 ±0.0040 | -2.8 | 0.502 | 0.540 | |
| tour: wta | 803 | -0.0223 ±0.0075 | -0.0094 ±0.0031 | -3.0 | 0.677 | 0.690 | |
| big disagree (>=0.1) | 259 | -0.0820 ±0.0264 | -0.0329 ±0.0111 | -3.1 | 0.585 | 0.637 | |
| best rank 21-50 | 539 | -0.0272 ±0.0082 | -0.0110 ±0.0035 | -3.3 | 0.657 | 0.698 | |
| no top-20 player | 1013 | -0.0244 ±0.0067 | -0.0095 ±0.0028 | -3.6 | 0.631 | 0.651 | |
| month 2026-09 | 319 | -0.0405 ±0.0103 | -0.0168 ±0.0043 | -3.9 | 0.705 | 0.730 | |
| surface: Hard | 716 | -0.0325 ±0.0080 | -0.0126 ±0.0033 | -4.1 | 0.670 | 0.686 | |
| pred_source: live aligned | 632 | -0.0411 ±0.0084 | -0.0162 ±0.0034 | -4.9 | 0.676 | 0.699 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1566, mean |Δ|=0.0056, p95=0.0100, >0.05 in 32 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0666 (n=319, >0.05: 19) | 2026-10 p95=0.1929 (n=107, >0.05: 11)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1566, d_ll -0.0161 ±0.0052 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 598 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'WTA Seoul': 3, 'ATP Cincinnati': 1}
- Unmatched Kalshi names, main draw (40): Akasha Urhobo, Aleksandr Shevchenko, Alevtina Ibragimova, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari
