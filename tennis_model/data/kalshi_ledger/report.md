# Model vs Kalshi — match-by-match scorecard

_Generated 2026-10-13T08:25:02Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 2094 | 2013 | 6 | 13 | 62 | 0 | 12 | 22 | 48 | 2026-05-03..2026-10-14 |
| wta | 2173 | 1325 | 42 | 743 | 63 | 0 | 10 | 15 | 37 | 2026-05-02..2026-10-14 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1580 | 0.6050 | 0.5884 | -0.0166 ±0.0052 | -0.0070 ±0.0021 | 0.664 | 0.679 |
| atp | 771 | 0.6203 | 0.6100 | -0.0103 ±0.0073 | -0.0044 ±0.0029 | 0.651 | 0.667 |
| wta | 809 | 0.5904 | 0.5678 | -0.0226 ±0.0074 | -0.0095 ±0.0031 | 0.676 | 0.690 |
| pooled/live_aligned | 644 | 0.6046 | 0.5630 | -0.0416 ±0.0083 | -0.0161 ±0.0034 | 0.671 | 0.696 |
| pooled/backtest | 936 | 0.6053 | 0.6059 | +0.0006 ±0.0066 | -0.0008 ±0.0027 | 0.659 | 0.667 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 644 | -0.0416 ±0.0083 | -0.0161 ±0.0034 | -5.0 | 0.671 | 0.696 | |
| pred_source: backtest | 936 | +0.0006 ±0.0066 | -0.0008 ±0.0027 | +0.1 | 0.659 | 0.667 | |
| top-20 involved | 560 | -0.0018 ±0.0082 | -0.0022 ±0.0030 | -0.2 | 0.722 | 0.728 | |
| no top-20 player | 1020 | -0.0247 ±0.0067 | -0.0097 ±0.0028 | -3.7 | 0.632 | 0.652 | |
| both inside top-50 | 399 | -0.0202 ±0.0104 | -0.0084 ±0.0044 | -1.9 | 0.648 | 0.658 | |
| someone outside top-50 | 1181 | -0.0154 ±0.0060 | -0.0065 ±0.0024 | -2.6 | 0.669 | 0.686 | |
| best rank 1-10 | 335 | +0.0107 ±0.0104 | +0.0021 ±0.0034 | +1.0 | 0.740 | 0.740 | |
| best rank 11-20 | 225 | -0.0206 ±0.0132 | -0.0087 ±0.0053 | -1.6 | 0.696 | 0.709 | |
| best rank 21-50 | 546 | -0.0278 ±0.0081 | -0.0113 ±0.0035 | -3.4 | 0.658 | 0.700 | |
| best rank 51-100 | 386 | -0.0177 ±0.0112 | -0.0066 ±0.0047 | -1.6 | 0.602 | 0.595 | |
| best rank 100+ | 88 | -0.0357 ±0.0320 | -0.0128 ±0.0136 | -1.1 | 0.602 | 0.608 | |
| kalshi favorite 0.5-0.6 | 453 | -0.0245 ±0.0085 | -0.0115 ±0.0040 | -2.9 | 0.502 | 0.542 | |
| kalshi favorite 0.6-0.7 | 435 | -0.0124 ±0.0092 | -0.0048 ±0.0041 | -1.4 | 0.618 | 0.621 | |
| kalshi favorite 0.7-0.8 | 363 | -0.0073 ±0.0098 | -0.0030 ±0.0040 | -0.8 | 0.740 | 0.747 | |
| kalshi favorite 0.8-0.9 | 217 | -0.0003 ±0.0160 | -0.0009 ±0.0056 | -0.0 | 0.834 | 0.839 | |
| kalshi favorite 0.9-1.0 | 112 | -0.0624 ±0.0309 | -0.0227 ±0.0096 | -2.0 | 0.920 | 0.929 | |
| surface: Hard | 730 | -0.0332 ±0.0079 | -0.0127 ±0.0032 | -4.2 | 0.667 | 0.684 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 523 | -0.0244 ±0.0103 | -0.0094 ±0.0042 | -2.4 | 0.614 | 0.631 | |
| tier: atp500 | 250 | -0.0149 ±0.0103 | -0.0067 ±0.0046 | -1.4 | 0.628 | 0.642 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 296 | -0.0175 ±0.0110 | -0.0063 ±0.0047 | -1.6 | 0.664 | 0.682 | |
| round early (R128-R64) | 639 | -0.0217 ±0.0084 | -0.0088 ±0.0033 | -2.6 | 0.710 | 0.723 | |
| round late (QF-F) | 207 | -0.0088 ±0.0112 | -0.0046 ±0.0050 | -0.8 | 0.638 | 0.647 | |
| round mid (R32-R16) | 712 | -0.0147 ±0.0081 | -0.0063 ±0.0033 | -1.8 | 0.636 | 0.652 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 319 | -0.0405 ±0.0103 | -0.0168 ±0.0043 | -3.9 | 0.705 | 0.730 | |
| month 2026-10 | 121 | -0.0720 ±0.0287 | -0.0258 ±0.0112 | -2.5 | 0.653 | 0.707 | |
| agree (<0.05) | 853 | -0.0003 ±0.0025 | -0.0005 ±0.0008 | -0.1 | 0.707 | 0.705 | |
| mild disagree (0.05-0.10) | 467 | -0.0095 ±0.0083 | -0.0043 ±0.0032 | -1.2 | 0.631 | 0.654 | |
| big disagree (>=0.1) | 260 | -0.0826 ±0.0263 | -0.0332 ±0.0110 | -3.1 | 0.583 | 0.638 | |
| tour: atp | 771 | -0.0103 ±0.0073 | -0.0044 ±0.0029 | -1.4 | 0.651 | 0.667 | |
| tour: wta | 809 | -0.0226 ±0.0074 | -0.0095 ±0.0031 | -3.0 | 0.676 | 0.690 | |

When they disagree by >= 0.1: model closer to the outcome in **98/260** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 18 | 0.067 | 0.167 |
| 0.1-0.2 | 94 | 0.152 | 0.149 |
| 0.2-0.3 | 142 | 0.250 | 0.261 |
| 0.3-0.4 | 202 | 0.354 | 0.366 |
| 0.4-0.5 | 270 | 0.451 | 0.463 |
| 0.5-0.6 | 246 | 0.551 | 0.537 |
| 0.6-0.7 | 236 | 0.647 | 0.619 |
| 0.7-0.8 | 191 | 0.752 | 0.770 |
| 0.8-0.9 | 122 | 0.846 | 0.795 |
| 0.9-1.0 | 59 | 0.932 | 0.915 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 43 | 0.058 | 0.093 |
| 0.1-0.2 | 86 | 0.154 | 0.151 |
| 0.2-0.3 | 161 | 0.255 | 0.255 |
| 0.3-0.4 | 195 | 0.354 | 0.379 |
| 0.4-0.5 | 232 | 0.444 | 0.453 |
| 0.5-0.6 | 225 | 0.555 | 0.529 |
| 0.6-0.7 | 236 | 0.649 | 0.627 |
| 0.7-0.8 | 202 | 0.749 | 0.748 |
| 0.8-0.9 | 132 | 0.846 | 0.833 |
| 0.9-1.0 | 68 | 0.934 | 0.941 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 335 | +0.0107 ±0.0104 | +0.0021 ±0.0034 | +1.0 | 0.740 | 0.740 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| pred_source: backtest | 936 | +0.0006 ±0.0066 | -0.0008 ±0.0027 | +0.1 | 0.659 | 0.667 | |
| kalshi favorite 0.8-0.9 | 217 | -0.0003 ±0.0160 | -0.0009 ±0.0056 | -0.0 | 0.834 | 0.839 | |
| agree (<0.05) | 853 | -0.0003 ±0.0025 | -0.0005 ±0.0008 | -0.1 | 0.707 | 0.705 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| top-20 involved | 560 | -0.0018 ±0.0082 | -0.0022 ±0.0030 | -0.2 | 0.722 | 0.728 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| kalshi favorite 0.5-0.6 | 453 | -0.0245 ±0.0085 | -0.0115 ±0.0040 | -2.9 | 0.502 | 0.542 | |
| tour: wta | 809 | -0.0226 ±0.0074 | -0.0095 ±0.0031 | -3.0 | 0.676 | 0.690 | |
| big disagree (>=0.1) | 260 | -0.0826 ±0.0263 | -0.0332 ±0.0110 | -3.1 | 0.583 | 0.638 | |
| best rank 21-50 | 546 | -0.0278 ±0.0081 | -0.0113 ±0.0035 | -3.4 | 0.658 | 0.700 | |
| no top-20 player | 1020 | -0.0247 ±0.0067 | -0.0097 ±0.0028 | -3.7 | 0.632 | 0.652 | |
| month 2026-09 | 319 | -0.0405 ±0.0103 | -0.0168 ±0.0043 | -3.9 | 0.705 | 0.730 | |
| surface: Hard | 730 | -0.0332 ±0.0079 | -0.0127 ±0.0032 | -4.2 | 0.667 | 0.684 | |
| pred_source: live aligned | 644 | -0.0416 ±0.0083 | -0.0161 ±0.0034 | -5.0 | 0.671 | 0.696 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1580, mean |Δ|=0.0057, p95=0.0100, >0.05 in 34 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0666 (n=319, >0.05: 19) | 2026-10 p95=0.2100 (n=121, >0.05: 13)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1580, d_ll -0.0166 ±0.0052 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 598 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'WTA Seoul': 3, 'ATP Chengdu': 1}
- Unmatched Kalshi names, main draw (40): Akasha Urhobo, Aleksandr Shevchenko, Alevtina Ibragimova, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari
