# Model vs Kalshi — match-by-match scorecard

_Generated 2026-07-09T09:40:26Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the Pinnacle closing-odds scorecard (market.json): different price time, different match mix._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 956 | 917 | 2 | 5 | 32 | 0 | 6 | 9 | 14 | 2026-05-03..2026-07-10 |
| wta | 976 | 571 | 2 | 378 | 25 | 0 | 2 | 15 | 16 | 2026-05-02..2026-07-09 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1054 | 0.5966 | 0.5827 | -0.0139 ±0.0068 | -0.0057 ±0.0028 | 0.671 | 0.682 |
| atp | 519 | 0.6001 | 0.5986 | -0.0015 ±0.0102 | -0.0003 ±0.0041 | 0.674 | 0.684 |
| wta | 535 | 0.5933 | 0.5673 | -0.0260 ±0.0090 | -0.0108 ±0.0037 | 0.667 | 0.680 |
| pooled/live | 216 | 0.5692 | 0.5199 | -0.0492 ±0.0181 | -0.0162 ±0.0077 | 0.718 | 0.715 |
| pooled/backtest | 838 | 0.6037 | 0.5989 | -0.0048 ±0.0071 | -0.0029 ±0.0029 | 0.659 | 0.674 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live | 216 | -0.0492 ±0.0181 | -0.0162 ±0.0077 | -2.7 | 0.718 | 0.715 | |
| pred_source: backtest | 838 | -0.0048 ±0.0071 | -0.0029 ±0.0029 | -0.7 | 0.659 | 0.674 | |
| top-20 involved | 395 | -0.0063 ±0.0101 | -0.0026 ±0.0037 | -0.6 | 0.746 | 0.743 | |
| no top-20 player | 659 | -0.0184 ±0.0090 | -0.0075 ±0.0038 | -2.0 | 0.626 | 0.646 | |
| both inside top-50 | 238 | +0.0079 ±0.0141 | +0.0035 ±0.0060 | +0.6 | 0.679 | 0.662 | |
| someone outside top-50 | 816 | -0.0203 ±0.0077 | -0.0083 ±0.0031 | -2.6 | 0.669 | 0.688 | |
| best rank 1-10 | 229 | +0.0132 ±0.0143 | +0.0045 ±0.0048 | +0.9 | 0.747 | 0.742 | |
| best rank 11-20 | 166 | -0.0333 ±0.0134 | -0.0124 ±0.0056 | -2.5 | 0.744 | 0.744 | |
| best rank 21-50 | 368 | -0.0181 ±0.0106 | -0.0062 ±0.0046 | -1.7 | 0.649 | 0.674 | |
| best rank 51-100 | 251 | -0.0105 ±0.0163 | -0.0054 ±0.0069 | -0.6 | 0.584 | 0.602 | |
| best rank 100+ | 40 | -0.0716 ±0.0475 | -0.0321 ±0.0198 | -1.5 | 0.675 | 0.662 | ⚠ small n |
| kalshi favorite 0.5-0.6 | 292 | -0.0256 ±0.0116 | -0.0114 ±0.0054 | -2.2 | 0.485 | 0.531 | |
| kalshi favorite 0.6-0.7 | 284 | -0.0057 ±0.0108 | -0.0023 ±0.0050 | -0.5 | 0.641 | 0.634 | |
| kalshi favorite 0.7-0.8 | 241 | -0.0051 ±0.0129 | -0.0019 ±0.0053 | -0.4 | 0.737 | 0.739 | |
| kalshi favorite 0.8-0.9 | 152 | +0.0096 ±0.0217 | +0.0031 ±0.0081 | +0.4 | 0.842 | 0.829 | |
| kalshi favorite 0.9-1.0 | 85 | -0.0685 ±0.0371 | -0.0233 ±0.0110 | -1.8 | 0.918 | 0.941 | |
| surface: Clay | 516 | -0.0032 ±0.0093 | -0.0024 ±0.0036 | -0.3 | 0.672 | 0.687 | |
| surface: Grass | 538 | -0.0242 ±0.0099 | -0.0087 ±0.0042 | -2.4 | 0.669 | 0.678 | |
| tier: atp250 | 221 | +0.0062 ±0.0153 | +0.0013 ±0.0064 | +0.4 | 0.633 | 0.638 | |
| tier: atp500 | 183 | -0.0182 ±0.0105 | -0.0084 ±0.0046 | -1.7 | 0.607 | 0.626 | |
| tier: grand_slam | 467 | -0.0231 ±0.0116 | -0.0092 ±0.0046 | -2.0 | 0.712 | 0.723 | |
| tier: masters | 183 | -0.0103 ±0.0141 | -0.0023 ±0.0060 | -0.7 | 0.675 | 0.689 | |
| round early (R128-R64) | 507 | -0.0232 ±0.0107 | -0.0086 ±0.0043 | -2.2 | 0.713 | 0.725 | |
| round late (QF-F) | 116 | -0.0020 ±0.0167 | -0.0016 ±0.0071 | -0.1 | 0.655 | 0.647 | |
| round mid (R32-R16) | 409 | -0.0062 ±0.0103 | -0.0034 ±0.0043 | -0.6 | 0.632 | 0.647 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | -0.0033 ±0.0095 | -0.0024 ±0.0037 | -0.3 | 0.677 | 0.690 | |
| month 2026-06 | 438 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.639 | 0.661 | |
| month 2026-07 | 117 | -0.0188 ±0.0249 | -0.0016 ±0.0104 | -0.8 | 0.761 | 0.726 | |
| agree (<0.05) | 509 | +0.0008 ±0.0033 | -0.0004 ±0.0010 | +0.3 | 0.709 | 0.706 | |
| mild disagree (0.05-0.10) | 310 | -0.0088 ±0.0101 | -0.0047 ±0.0038 | -0.9 | 0.627 | 0.665 | |
| big disagree (>=0.1) | 235 | -0.0526 ±0.0263 | -0.0182 ±0.0111 | -2.0 | 0.645 | 0.653 | |
| tour: atp | 519 | -0.0015 ±0.0102 | -0.0003 ±0.0041 | -0.1 | 0.674 | 0.684 | |
| tour: wta | 535 | -0.0260 ±0.0090 | -0.0108 ±0.0037 | -2.9 | 0.667 | 0.680 | |

When they disagree by >= 0.1: model closer to the outcome in **83/235** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 10 | 0.064 | 0.100 |
| 0.1-0.2 | 59 | 0.155 | 0.102 |
| 0.2-0.3 | 91 | 0.250 | 0.198 |
| 0.3-0.4 | 146 | 0.352 | 0.329 |
| 0.4-0.5 | 180 | 0.450 | 0.483 |
| 0.5-0.6 | 182 | 0.551 | 0.555 |
| 0.6-0.7 | 160 | 0.645 | 0.644 |
| 0.7-0.8 | 133 | 0.748 | 0.737 |
| 0.8-0.9 | 72 | 0.845 | 0.833 |
| 0.9-1.0 | 21 | 0.927 | 0.905 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 35 | 0.055 | 0.057 |
| 0.1-0.2 | 67 | 0.153 | 0.149 |
| 0.2-0.3 | 102 | 0.253 | 0.275 |
| 0.3-0.4 | 127 | 0.352 | 0.346 |
| 0.4-0.5 | 153 | 0.443 | 0.451 |
| 0.5-0.6 | 141 | 0.557 | 0.504 |
| 0.6-0.7 | 155 | 0.650 | 0.626 |
| 0.7-0.8 | 139 | 0.746 | 0.748 |
| 0.8-0.9 | 85 | 0.843 | 0.812 |
| 0.9-1.0 | 50 | 0.945 | 0.940 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 229 | +0.0132 ±0.0143 | +0.0045 ±0.0048 | +0.9 | 0.747 | 0.742 | |
| both inside top-50 | 238 | +0.0079 ±0.0141 | +0.0035 ±0.0060 | +0.6 | 0.679 | 0.662 | |
| kalshi favorite 0.8-0.9 | 152 | +0.0096 ±0.0217 | +0.0031 ±0.0081 | +0.4 | 0.842 | 0.829 | |
| tier: atp250 | 221 | +0.0062 ±0.0153 | +0.0013 ±0.0064 | +0.4 | 0.633 | 0.638 | |
| agree (<0.05) | 509 | +0.0008 ±0.0033 | -0.0004 ±0.0010 | +0.3 | 0.709 | 0.706 | |
| round late (QF-F) | 116 | -0.0020 ±0.0167 | -0.0016 ±0.0071 | -0.1 | 0.655 | 0.647 | |
| tour: atp | 519 | -0.0015 ±0.0102 | -0.0003 ±0.0041 | -0.1 | 0.674 | 0.684 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| round early (R128-R64) | 507 | -0.0232 ±0.0107 | -0.0086 ±0.0043 | -2.2 | 0.713 | 0.725 | |
| kalshi favorite 0.5-0.6 | 292 | -0.0256 ±0.0116 | -0.0114 ±0.0054 | -2.2 | 0.485 | 0.531 | |
| month 2026-06 | 438 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.639 | 0.661 | |
| surface: Grass | 538 | -0.0242 ±0.0099 | -0.0087 ±0.0042 | -2.4 | 0.669 | 0.678 | |
| best rank 11-20 | 166 | -0.0333 ±0.0134 | -0.0124 ±0.0056 | -2.5 | 0.744 | 0.744 | |
| someone outside top-50 | 816 | -0.0203 ±0.0077 | -0.0083 ±0.0031 | -2.6 | 0.669 | 0.688 | |
| pred_source: live | 216 | -0.0492 ±0.0181 | -0.0162 ±0.0077 | -2.7 | 0.718 | 0.715 | |
| tour: wta | 535 | -0.0260 ±0.0090 | -0.0108 ±0.0037 | -2.9 | 0.667 | 0.680 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1054, mean |Δ|=0.0035, p95=0.0100, >0.05 in 12 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- Our winner vs Kalshi settlement disagreements: 1 (join bugs surface here).
- Sensitivity incl. retirements: n=1054, d_ll -0.0139 ±0.0068
- Unmatched qualifying markets: 315 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'ATP Mallorca': 1, 'ATP Stuttgart': 1, 'Wimbledon': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Arantxa Rus, Ashlyn Krueger, Ayana Akli, Bianca Andreescu, Cadence Brace, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Casper Ruud, Celine Naef, Chloe Paquet, Claire Liu, Daphnee Mpetshi Perricard, Darja Semenistaja, Darja Vidmanova, Despina Papamichail, Dominika Salkova, Ekaterine Gorgodze, Eleejah Inisan, Elena Pridankina, Elizabeth Mandlik, Elizara Yaneva, Elvina Kalieva, Eva Guerrero Alvarez, Frances Tiafoe
