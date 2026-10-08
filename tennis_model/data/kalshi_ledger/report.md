# Model vs Kalshi — match-by-match scorecard

_Generated 2026-10-08T09:47:37Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 2059 | 1955 | 30 | 12 | 62 | 0 | 11 | 22 | 63 | 2026-05-03..2026-10-09 |
| wta | 2106 | 1304 | 3 | 743 | 56 | 0 | 10 | 15 | 30 | 2026-05-02..2026-10-09 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1529 | 0.6014 | 0.5860 | -0.0155 ±0.0052 | -0.0067 ±0.0021 | 0.666 | 0.680 |
| atp | 732 | 0.6166 | 0.6079 | -0.0086 ±0.0073 | -0.0040 ±0.0029 | 0.652 | 0.668 |
| wta | 797 | 0.5875 | 0.5658 | -0.0217 ±0.0075 | -0.0091 ±0.0031 | 0.679 | 0.690 |
| pooled/live_aligned | 595 | 0.5951 | 0.5542 | -0.0409 ±0.0085 | -0.0162 ±0.0035 | 0.677 | 0.700 |
| pooled/backtest | 934 | 0.6055 | 0.6062 | +0.0008 ±0.0066 | -0.0007 ±0.0027 | 0.658 | 0.666 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 595 | -0.0409 ±0.0085 | -0.0162 ±0.0035 | -4.8 | 0.677 | 0.700 | |
| pred_source: backtest | 934 | +0.0008 ±0.0066 | -0.0007 ±0.0027 | +0.1 | 0.658 | 0.666 | |
| top-20 involved | 534 | +0.0007 ±0.0084 | -0.0015 ±0.0030 | +0.1 | 0.729 | 0.731 | |
| no top-20 player | 995 | -0.0241 ±0.0067 | -0.0095 ±0.0028 | -3.6 | 0.632 | 0.652 | |
| both inside top-50 | 373 | -0.0145 ±0.0106 | -0.0064 ±0.0045 | -1.4 | 0.661 | 0.664 | |
| someone outside top-50 | 1156 | -0.0158 ±0.0060 | -0.0068 ±0.0024 | -2.6 | 0.667 | 0.685 | |
| best rank 1-10 | 321 | +0.0155 ±0.0105 | +0.0035 ±0.0035 | +1.5 | 0.748 | 0.741 | |
| best rank 11-20 | 213 | -0.0216 ±0.0137 | -0.0090 ±0.0055 | -1.6 | 0.702 | 0.716 | |
| best rank 21-50 | 523 | -0.0263 ±0.0080 | -0.0109 ±0.0035 | -3.3 | 0.660 | 0.701 | |
| best rank 51-100 | 384 | -0.0185 ±0.0113 | -0.0069 ±0.0047 | -1.6 | 0.600 | 0.595 | |
| best rank 100+ | 88 | -0.0357 ±0.0320 | -0.0128 ±0.0136 | -1.1 | 0.602 | 0.608 | |
| kalshi favorite 0.5-0.6 | 436 | -0.0260 ±0.0087 | -0.0120 ±0.0041 | -3.0 | 0.499 | 0.539 | |
| kalshi favorite 0.6-0.7 | 422 | -0.0109 ±0.0094 | -0.0041 ±0.0042 | -1.2 | 0.618 | 0.621 | |
| kalshi favorite 0.7-0.8 | 353 | -0.0086 ±0.0098 | -0.0034 ±0.0039 | -0.9 | 0.744 | 0.748 | |
| kalshi favorite 0.8-0.9 | 209 | +0.0069 ±0.0155 | +0.0015 ±0.0055 | +0.4 | 0.842 | 0.842 | |
| kalshi favorite 0.9-1.0 | 109 | -0.0562 ±0.0313 | -0.0219 ±0.0099 | -1.8 | 0.927 | 0.936 | |
| surface: Hard | 679 | -0.0319 ±0.0081 | -0.0124 ±0.0033 | -4.0 | 0.672 | 0.686 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 484 | -0.0229 ±0.0105 | -0.0093 ±0.0043 | -2.2 | 0.612 | 0.629 | |
| tier: atp500 | 250 | -0.0149 ±0.0103 | -0.0067 ±0.0046 | -1.4 | 0.628 | 0.642 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 284 | -0.0149 ±0.0113 | -0.0051 ±0.0048 | -1.3 | 0.671 | 0.683 | |
| round early (R128-R64) | 605 | -0.0198 ±0.0085 | -0.0081 ±0.0033 | -2.3 | 0.712 | 0.725 | |
| round late (QF-F) | 201 | -0.0060 ±0.0113 | -0.0034 ±0.0050 | -0.5 | 0.642 | 0.647 | |
| round mid (R32-R16) | 701 | -0.0147 ±0.0081 | -0.0065 ±0.0034 | -1.8 | 0.638 | 0.654 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 319 | -0.0405 ±0.0103 | -0.0168 ±0.0043 | -3.9 | 0.705 | 0.730 | |
| month 2026-10 | 70 | -0.0873 ±0.0420 | -0.0325 ±0.0169 | -2.1 | 0.686 | 0.743 | |
| agree (<0.05) | 828 | +0.0003 ±0.0024 | -0.0005 ±0.0008 | +0.1 | 0.709 | 0.707 | |
| mild disagree (0.05-0.10) | 451 | -0.0088 ±0.0085 | -0.0038 ±0.0032 | -1.0 | 0.629 | 0.653 | |
| big disagree (>=0.1) | 250 | -0.0797 ±0.0266 | -0.0326 ±0.0112 | -3.0 | 0.590 | 0.636 | |
| tour: atp | 732 | -0.0086 ±0.0073 | -0.0040 ±0.0029 | -1.2 | 0.652 | 0.668 | |
| tour: wta | 797 | -0.0217 ±0.0075 | -0.0091 ±0.0031 | -2.9 | 0.679 | 0.690 | |

When they disagree by >= 0.1: model closer to the outcome in **94/250** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 17 | 0.066 | 0.176 |
| 0.1-0.2 | 93 | 0.153 | 0.151 |
| 0.2-0.3 | 136 | 0.251 | 0.257 |
| 0.3-0.4 | 196 | 0.353 | 0.362 |
| 0.4-0.5 | 262 | 0.451 | 0.466 |
| 0.5-0.6 | 239 | 0.552 | 0.536 |
| 0.6-0.7 | 226 | 0.647 | 0.624 |
| 0.7-0.8 | 188 | 0.751 | 0.771 |
| 0.8-0.9 | 120 | 0.846 | 0.800 |
| 0.9-1.0 | 52 | 0.932 | 0.942 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 43 | 0.058 | 0.093 |
| 0.1-0.2 | 83 | 0.153 | 0.145 |
| 0.2-0.3 | 156 | 0.255 | 0.263 |
| 0.3-0.4 | 189 | 0.354 | 0.381 |
| 0.4-0.5 | 222 | 0.444 | 0.450 |
| 0.5-0.6 | 218 | 0.556 | 0.523 |
| 0.6-0.7 | 229 | 0.650 | 0.629 |
| 0.7-0.8 | 197 | 0.749 | 0.756 |
| 0.8-0.9 | 127 | 0.846 | 0.835 |
| 0.9-1.0 | 65 | 0.935 | 0.954 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 321 | +0.0155 ±0.0105 | +0.0035 ±0.0035 | +1.5 | 0.748 | 0.741 | |
| kalshi favorite 0.8-0.9 | 209 | +0.0069 ±0.0155 | +0.0015 ±0.0055 | +0.4 | 0.842 | 0.842 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| agree (<0.05) | 828 | +0.0003 ±0.0024 | -0.0005 ±0.0008 | +0.1 | 0.709 | 0.707 | |
| pred_source: backtest | 934 | +0.0008 ±0.0066 | -0.0007 ±0.0027 | +0.1 | 0.658 | 0.666 | |
| top-20 involved | 534 | +0.0007 ±0.0084 | -0.0015 ±0.0030 | +0.1 | 0.729 | 0.731 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| tour: wta | 797 | -0.0217 ±0.0075 | -0.0091 ±0.0031 | -2.9 | 0.679 | 0.690 | |
| kalshi favorite 0.5-0.6 | 436 | -0.0260 ±0.0087 | -0.0120 ±0.0041 | -3.0 | 0.499 | 0.539 | |
| big disagree (>=0.1) | 250 | -0.0797 ±0.0266 | -0.0326 ±0.0112 | -3.0 | 0.590 | 0.636 | |
| best rank 21-50 | 523 | -0.0263 ±0.0080 | -0.0109 ±0.0035 | -3.3 | 0.660 | 0.701 | |
| no top-20 player | 995 | -0.0241 ±0.0067 | -0.0095 ±0.0028 | -3.6 | 0.632 | 0.652 | |
| month 2026-09 | 319 | -0.0405 ±0.0103 | -0.0168 ±0.0043 | -3.9 | 0.705 | 0.730 | |
| surface: Hard | 679 | -0.0319 ±0.0081 | -0.0124 ±0.0033 | -4.0 | 0.672 | 0.686 | |
| pred_source: live aligned | 595 | -0.0409 ±0.0085 | -0.0162 ±0.0035 | -4.8 | 0.677 | 0.700 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1529, mean |Δ|=0.0047, p95=0.0100, >0.05 in 26 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0666 (n=319, >0.05: 19) | 2026-10 p95=0.1435 (n=70, >0.05: 5)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1529, d_ll -0.0155 ±0.0052 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 597 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'WTA Seoul': 3, 'ATP Chengdu': 1}
- Unmatched Kalshi names, main draw (40): Akasha Urhobo, Aleksandr Shevchenko, Alevtina Ibragimova, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Caroline Dolehide, Carolyn Ansari
