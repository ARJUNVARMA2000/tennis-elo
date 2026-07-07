# Model vs Kalshi — match-by-match scorecard

_Generated 2026-07-07T23:53:47Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the Pinnacle closing-odds scorecard (market.json): different price time, different match mix._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 955 | 890 | 20 | 13 | 32 | 0 | 6 | 9 | 32 | 2026-05-03..2026-07-10 |
| wta | 975 | 542 | 20 | 387 | 25 | 1 | 2 | 15 | 50 | 2026-05-02..2026-07-09 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 973 | 0.5981 | 0.5869 | -0.0113 ±0.0067 | -0.0048 ±0.0027 | 0.668 | 0.679 |
| atp | 485 | 0.6013 | 0.6002 | -0.0011 ±0.0102 | -0.0005 ±0.0041 | 0.676 | 0.689 |
| wta | 488 | 0.5950 | 0.5736 | -0.0214 ±0.0087 | -0.0092 ±0.0035 | 0.660 | 0.670 |
| pooled/live | 162 | 0.5573 | 0.5009 | -0.0564 ±0.0189 | -0.0195 ±0.0082 | 0.722 | 0.731 |
| pooled/backtest | 811 | 0.6063 | 0.6040 | -0.0023 ±0.0071 | -0.0019 ±0.0028 | 0.657 | 0.669 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live | 162 | -0.0564 ±0.0189 | -0.0195 ±0.0082 | -3.0 | 0.722 | 0.731 | |
| pred_source: backtest | 811 | -0.0023 ±0.0071 | -0.0019 ±0.0028 | -0.3 | 0.657 | 0.669 | |
| top-20 involved | 346 | -0.0074 ±0.0100 | -0.0034 ±0.0034 | -0.7 | 0.741 | 0.744 | |
| no top-20 player | 627 | -0.0134 ±0.0088 | -0.0057 ±0.0038 | -1.5 | 0.628 | 0.644 | |
| both inside top-50 | 203 | +0.0073 ±0.0134 | +0.0037 ±0.0057 | +0.5 | 0.677 | 0.667 | |
| someone outside top-50 | 770 | -0.0162 ±0.0077 | -0.0071 ±0.0031 | -2.1 | 0.666 | 0.682 | |
| best rank 1-10 | 195 | +0.0107 ±0.0139 | +0.0028 ±0.0040 | +0.8 | 0.749 | 0.749 | |
| best rank 11-20 | 151 | -0.0307 ±0.0141 | -0.0113 ±0.0059 | -2.2 | 0.732 | 0.738 | |
| best rank 21-50 | 351 | -0.0187 ±0.0103 | -0.0070 ±0.0045 | -1.8 | 0.652 | 0.681 | |
| best rank 51-100 | 239 | -0.0021 ±0.0161 | -0.0020 ±0.0068 | -0.1 | 0.584 | 0.590 | |
| best rank 100+ | 37 | -0.0373 ±0.0463 | -0.0176 ±0.0191 | -0.8 | 0.676 | 0.635 | ⚠ small n |
| kalshi favorite 0.5-0.6 | 271 | -0.0237 ±0.0110 | -0.0109 ±0.0052 | -2.1 | 0.478 | 0.535 | |
| kalshi favorite 0.6-0.7 | 267 | -0.0019 ±0.0108 | -0.0004 ±0.0050 | -0.2 | 0.644 | 0.625 | |
| kalshi favorite 0.7-0.8 | 224 | -0.0043 ±0.0119 | -0.0021 ±0.0050 | -0.4 | 0.739 | 0.741 | |
| kalshi favorite 0.8-0.9 | 140 | +0.0027 ±0.0217 | +0.0004 ±0.0080 | +0.1 | 0.843 | 0.836 | |
| kalshi favorite 0.9-1.0 | 71 | -0.0486 ±0.0424 | -0.0177 ±0.0122 | -1.1 | 0.915 | 0.930 | |
| surface: Clay | 490 | +0.0011 ±0.0091 | -0.0007 ±0.0035 | +0.1 | 0.671 | 0.681 | |
| surface: Grass | 483 | -0.0238 ±0.0098 | -0.0090 ±0.0042 | -2.4 | 0.665 | 0.678 | |
| tier: atp250 | 221 | +0.0062 ±0.0153 | +0.0013 ±0.0064 | +0.4 | 0.633 | 0.638 | |
| tier: atp500 | 182 | -0.0166 ±0.0104 | -0.0075 ±0.0046 | -1.6 | 0.610 | 0.624 | |
| tier: grand_slam | 387 | -0.0192 ±0.0118 | -0.0083 ±0.0046 | -1.6 | 0.712 | 0.725 | |
| tier: masters | 183 | -0.0103 ±0.0141 | -0.0023 ±0.0060 | -0.7 | 0.675 | 0.689 | |
| round early (R128-R64) | 456 | -0.0223 ±0.0106 | -0.0085 ±0.0042 | -2.1 | 0.714 | 0.727 | |
| round late (QF-F) | 108 | -0.0104 ±0.0161 | -0.0052 ±0.0067 | -0.6 | 0.657 | 0.648 | |
| round mid (R32-R16) | 387 | +0.0012 ±0.0102 | -0.0006 ±0.0042 | +0.1 | 0.627 | 0.640 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 473 | +0.0011 ±0.0094 | -0.0006 ±0.0035 | +0.1 | 0.677 | 0.684 | |
| month 2026-06 | 437 | -0.0254 ±0.0103 | -0.0108 ±0.0044 | -2.5 | 0.638 | 0.660 | |
| month 2026-07 | 63 | -0.0064 ±0.0254 | +0.0047 ±0.0113 | -0.3 | 0.810 | 0.778 | |
| agree (<0.05) | 471 | +0.0002 ±0.0035 | -0.0009 ±0.0011 | +0.1 | 0.703 | 0.702 | |
| mild disagree (0.05-0.10) | 299 | -0.0076 ±0.0104 | -0.0044 ±0.0039 | -0.7 | 0.620 | 0.662 | |
| big disagree (>=0.1) | 203 | -0.0433 ±0.0270 | -0.0147 ±0.0114 | -1.6 | 0.658 | 0.653 | |
| tour: atp | 485 | -0.0011 ±0.0102 | -0.0005 ±0.0041 | -0.1 | 0.676 | 0.689 | |
| tour: wta | 488 | -0.0214 ±0.0087 | -0.0092 ±0.0035 | -2.5 | 0.660 | 0.670 | |

When they disagree by >= 0.1: model closer to the outcome in **71/203** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 8 | 0.065 | 0.125 |
| 0.1-0.2 | 55 | 0.154 | 0.109 |
| 0.2-0.3 | 82 | 0.249 | 0.207 |
| 0.3-0.4 | 135 | 0.351 | 0.348 |
| 0.4-0.5 | 166 | 0.450 | 0.482 |
| 0.5-0.6 | 168 | 0.552 | 0.554 |
| 0.6-0.7 | 152 | 0.645 | 0.651 |
| 0.7-0.8 | 128 | 0.748 | 0.750 |
| 0.8-0.9 | 62 | 0.843 | 0.839 |
| 0.9-1.0 | 17 | 0.928 | 0.882 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 29 | 0.057 | 0.069 |
| 0.1-0.2 | 60 | 0.153 | 0.133 |
| 0.2-0.3 | 92 | 0.253 | 0.272 |
| 0.3-0.4 | 116 | 0.352 | 0.362 |
| 0.4-0.5 | 140 | 0.443 | 0.457 |
| 0.5-0.6 | 133 | 0.556 | 0.519 |
| 0.6-0.7 | 149 | 0.651 | 0.624 |
| 0.7-0.8 | 132 | 0.746 | 0.750 |
| 0.8-0.9 | 80 | 0.844 | 0.812 |
| 0.9-1.0 | 42 | 0.944 | 0.929 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 195 | +0.0107 ±0.0139 | +0.0028 ±0.0040 | +0.8 | 0.749 | 0.749 | |
| both inside top-50 | 203 | +0.0073 ±0.0134 | +0.0037 ±0.0057 | +0.5 | 0.677 | 0.667 | |
| tier: atp250 | 221 | +0.0062 ±0.0153 | +0.0013 ±0.0064 | +0.4 | 0.633 | 0.638 | |
| kalshi favorite 0.8-0.9 | 140 | +0.0027 ±0.0217 | +0.0004 ±0.0080 | +0.1 | 0.843 | 0.836 | |
| surface: Clay | 490 | +0.0011 ±0.0091 | -0.0007 ±0.0035 | +0.1 | 0.671 | 0.681 | |
| month 2026-05 | 473 | +0.0011 ±0.0094 | -0.0006 ±0.0035 | +0.1 | 0.677 | 0.684 | |
| round mid (R32-R16) | 387 | +0.0012 ±0.0102 | -0.0006 ±0.0042 | +0.1 | 0.627 | 0.640 | |
| agree (<0.05) | 471 | +0.0002 ±0.0035 | -0.0009 ±0.0011 | +0.1 | 0.703 | 0.702 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| round early (R128-R64) | 456 | -0.0223 ±0.0106 | -0.0085 ±0.0042 | -2.1 | 0.714 | 0.727 | |
| someone outside top-50 | 770 | -0.0162 ±0.0077 | -0.0071 ±0.0031 | -2.1 | 0.666 | 0.682 | |
| kalshi favorite 0.5-0.6 | 271 | -0.0237 ±0.0110 | -0.0109 ±0.0052 | -2.1 | 0.478 | 0.535 | |
| best rank 11-20 | 151 | -0.0307 ±0.0141 | -0.0113 ±0.0059 | -2.2 | 0.732 | 0.738 | |
| surface: Grass | 483 | -0.0238 ±0.0098 | -0.0090 ±0.0042 | -2.4 | 0.665 | 0.678 | |
| month 2026-06 | 437 | -0.0254 ±0.0103 | -0.0108 ±0.0044 | -2.5 | 0.638 | 0.660 | |
| tour: wta | 488 | -0.0214 ±0.0087 | -0.0092 ±0.0035 | -2.5 | 0.660 | 0.670 | |
| pred_source: live | 162 | -0.0564 ±0.0189 | -0.0195 ±0.0082 | -3.0 | 0.722 | 0.731 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=973, mean |Δ|=0.0016, p95=0.0086, >0.05 in 0 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here).
- Sensitivity incl. retirements: n=973, d_ll -0.0113 ±0.0067
- Unmatched qualifying markets: 315 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'Wimbledon': 18, 'ATP Stuttgart': 1, 'ATP Mallorca': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alejandro Davidovich Fokina, Alexander Shevchenko, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Anna Kalinskaya, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Arantxa Rus, Arthur Rinderknech, Aryna Sabalenka, Ashlyn Krueger, Ayana Akli, Barbora Krejcikova, Belinda Bencic, Bianca Andreescu, Cadence Brace, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Casper Ruud, Caty McNally, Celine Naef, Chloe Paquet, Claire Liu, Coco Gauff, Daniil Medvedev, Daphnee Mpetshi Perricard, Daria Kasatkina, Darja Semenistaja, Darja Vidmanova
