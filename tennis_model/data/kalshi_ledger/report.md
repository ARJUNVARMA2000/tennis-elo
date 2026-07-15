# Model vs Kalshi — match-by-match scorecard

_Generated 2026-07-15T08:04:44Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1050 | 988 | 23 | 5 | 34 | 0 | 6 | 11 | 176 | 2026-05-03..2026-07-15 |
| wta | 1057 | 600 | 39 | 389 | 29 | 0 | 2 | 15 | 26 | 2026-05-02..2026-07-15 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1117 | 0.5945 | 0.5854 | -0.0091 ±0.0062 | -0.0039 ±0.0025 | 0.673 | 0.684 |
| atp | 550 | 0.5954 | 0.6011 | +0.0057 ±0.0090 | +0.0022 ±0.0037 | 0.678 | 0.685 |
| wta | 567 | 0.5936 | 0.5702 | -0.0234 ±0.0084 | -0.0099 ±0.0035 | 0.668 | 0.683 |
| pooled/live | 278 | 0.5681 | 0.5361 | -0.0320 ±0.0133 | -0.0104 ±0.0057 | 0.716 | 0.721 |
| pooled/backtest | 839 | 0.6032 | 0.6018 | -0.0014 ±0.0069 | -0.0018 ±0.0028 | 0.659 | 0.672 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live | 278 | -0.0320 ±0.0133 | -0.0104 ±0.0057 | -2.4 | 0.716 | 0.721 | |
| pred_source: backtest | 839 | -0.0014 ±0.0069 | -0.0018 ±0.0028 | -0.2 | 0.659 | 0.672 | |
| top-20 involved | 399 | -0.0004 ±0.0086 | -0.0004 ±0.0030 | -0.0 | 0.748 | 0.741 | |
| no top-20 player | 718 | -0.0138 ±0.0083 | -0.0059 ±0.0036 | -1.7 | 0.632 | 0.653 | |
| both inside top-50 | 241 | +0.0152 ±0.0111 | +0.0067 ±0.0048 | +1.4 | 0.683 | 0.658 | |
| someone outside top-50 | 876 | -0.0157 ±0.0072 | -0.0069 ±0.0029 | -2.2 | 0.671 | 0.691 | |
| best rank 1-10 | 235 | +0.0140 ±0.0120 | +0.0048 ±0.0037 | +1.2 | 0.749 | 0.745 | |
| best rank 11-20 | 164 | -0.0211 ±0.0117 | -0.0078 ±0.0050 | -1.8 | 0.747 | 0.735 | |
| best rank 21-50 | 379 | -0.0097 ±0.0098 | -0.0031 ±0.0043 | -1.0 | 0.652 | 0.670 | |
| best rank 51-100 | 283 | -0.0096 ±0.0146 | -0.0048 ±0.0062 | -0.7 | 0.610 | 0.629 | |
| best rank 100+ | 56 | -0.0636 ±0.0385 | -0.0302 ±0.0165 | -1.7 | 0.607 | 0.652 | |
| kalshi favorite 0.5-0.6 | 317 | -0.0187 ±0.0106 | -0.0083 ±0.0050 | -1.8 | 0.503 | 0.546 | |
| kalshi favorite 0.6-0.7 | 301 | -0.0048 ±0.0105 | -0.0020 ±0.0049 | -0.5 | 0.638 | 0.635 | |
| kalshi favorite 0.7-0.8 | 255 | -0.0037 ±0.0117 | -0.0013 ±0.0048 | -0.3 | 0.735 | 0.737 | |
| kalshi favorite 0.8-0.9 | 166 | -0.0026 ±0.0193 | -0.0020 ±0.0071 | -0.1 | 0.837 | 0.837 | |
| kalshi favorite 0.9-1.0 | 78 | -0.0175 ±0.0340 | -0.0059 ±0.0086 | -0.5 | 0.949 | 0.936 | |
| surface: Hard | 1 | +0.0660 ±0.0000 | +0.0282 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| surface: Clay | 555 | +0.0022 ±0.0083 | -0.0007 ±0.0033 | +0.3 | 0.674 | 0.689 | |
| surface: Grass | 561 | -0.0203 ±0.0091 | -0.0072 ±0.0039 | -2.2 | 0.672 | 0.678 | |
| tier: atp250 | 281 | +0.0022 ±0.0133 | -0.0005 ±0.0056 | +0.2 | 0.648 | 0.665 | |
| tier: atp500 | 181 | -0.0148 ±0.0103 | -0.0071 ±0.0046 | -1.4 | 0.608 | 0.622 | |
| tier: grand_slam | 476 | -0.0187 ±0.0107 | -0.0074 ±0.0042 | -1.8 | 0.711 | 0.720 | |
| tier: masters | 179 | +0.0046 ±0.0116 | +0.0032 ±0.0051 | +0.4 | 0.679 | 0.682 | |
| round early (R128-R64) | 506 | -0.0197 ±0.0101 | -0.0073 ±0.0041 | -1.9 | 0.712 | 0.722 | |
| round late (QF-F) | 119 | +0.0052 ±0.0132 | +0.0016 ±0.0057 | +0.4 | 0.664 | 0.639 | |
| round mid (R32-R16) | 470 | -0.0014 ±0.0091 | -0.0017 ±0.0038 | -0.1 | 0.641 | 0.661 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 493 | +0.0035 ±0.0090 | -0.0001 ±0.0035 | +0.4 | 0.677 | 0.687 | |
| month 2026-06 | 439 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.640 | 0.662 | |
| month 2026-07 | 185 | -0.0053 ±0.0143 | +0.0013 ±0.0062 | -0.4 | 0.741 | 0.730 | |
| agree (<0.05) | 547 | +0.0006 ±0.0032 | -0.0004 ±0.0010 | +0.2 | 0.713 | 0.712 | |
| mild disagree (0.05-0.10) | 337 | -0.0054 ±0.0097 | -0.0034 ±0.0037 | -0.6 | 0.625 | 0.662 | |
| big disagree (>=0.1) | 233 | -0.0371 ±0.0249 | -0.0129 ±0.0107 | -1.5 | 0.650 | 0.650 | |
| tour: atp | 550 | +0.0057 ±0.0090 | +0.0022 ±0.0037 | +0.6 | 0.678 | 0.685 | |
| tour: wta | 567 | -0.0234 ±0.0084 | -0.0099 ±0.0035 | -2.8 | 0.668 | 0.683 | |

When they disagree by >= 0.1: model closer to the outcome in **87/233** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 11 | 0.067 | 0.091 |
| 0.1-0.2 | 60 | 0.155 | 0.117 |
| 0.2-0.3 | 96 | 0.249 | 0.198 |
| 0.3-0.4 | 156 | 0.353 | 0.327 |
| 0.4-0.5 | 193 | 0.450 | 0.482 |
| 0.5-0.6 | 189 | 0.551 | 0.556 |
| 0.6-0.7 | 169 | 0.646 | 0.651 |
| 0.7-0.8 | 141 | 0.748 | 0.738 |
| 0.8-0.9 | 80 | 0.845 | 0.850 |
| 0.9-1.0 | 22 | 0.926 | 0.909 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 31 | 0.062 | 0.065 |
| 0.1-0.2 | 69 | 0.154 | 0.130 |
| 0.2-0.3 | 108 | 0.254 | 0.269 |
| 0.3-0.4 | 134 | 0.353 | 0.343 |
| 0.4-0.5 | 168 | 0.443 | 0.452 |
| 0.5-0.6 | 151 | 0.558 | 0.536 |
| 0.6-0.7 | 165 | 0.650 | 0.624 |
| 0.7-0.8 | 147 | 0.747 | 0.741 |
| 0.8-0.9 | 97 | 0.844 | 0.814 |
| 0.9-1.0 | 47 | 0.939 | 0.936 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| both inside top-50 | 241 | +0.0152 ±0.0111 | +0.0067 ±0.0048 | +1.4 | 0.683 | 0.658 | |
| best rank 1-10 | 235 | +0.0140 ±0.0120 | +0.0048 ±0.0037 | +1.2 | 0.749 | 0.745 | |
| tour: atp | 550 | +0.0057 ±0.0090 | +0.0022 ±0.0037 | +0.6 | 0.678 | 0.685 | |
| tier: masters | 179 | +0.0046 ±0.0116 | +0.0032 ±0.0051 | +0.4 | 0.679 | 0.682 | |
| round late (QF-F) | 119 | +0.0052 ±0.0132 | +0.0016 ±0.0057 | +0.4 | 0.664 | 0.639 | |
| month 2026-05 | 493 | +0.0035 ±0.0090 | -0.0001 ±0.0035 | +0.4 | 0.677 | 0.687 | |
| surface: Clay | 555 | +0.0022 ±0.0083 | -0.0007 ±0.0033 | +0.3 | 0.674 | 0.689 | |
| agree (<0.05) | 547 | +0.0006 ±0.0032 | -0.0004 ±0.0010 | +0.2 | 0.713 | 0.712 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| kalshi favorite 0.5-0.6 | 317 | -0.0187 ±0.0106 | -0.0083 ±0.0050 | -1.8 | 0.503 | 0.546 | |
| best rank 11-20 | 164 | -0.0211 ±0.0117 | -0.0078 ±0.0050 | -1.8 | 0.747 | 0.735 | |
| round early (R128-R64) | 506 | -0.0197 ±0.0101 | -0.0073 ±0.0041 | -1.9 | 0.712 | 0.722 | |
| someone outside top-50 | 876 | -0.0157 ±0.0072 | -0.0069 ±0.0029 | -2.2 | 0.671 | 0.691 | |
| surface: Grass | 561 | -0.0203 ±0.0091 | -0.0072 ±0.0039 | -2.2 | 0.672 | 0.678 | |
| month 2026-06 | 439 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.640 | 0.662 | |
| pred_source: live | 278 | -0.0320 ±0.0133 | -0.0104 ±0.0057 | -2.4 | 0.716 | 0.721 | |
| tour: wta | 567 | -0.0234 ±0.0084 | -0.0099 ±0.0035 | -2.8 | 0.668 | 0.683 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1117, mean |Δ|=0.0015, p95=0.0086, >0.05 in 0 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0090 (n=493, >0.05: 0) | 2026-06 p95=0.0085 (n=439, >0.05: 0) | 2026-07 p95=0.0071 (n=185, >0.05: 0)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1117, d_ll -0.0091 ±0.0062 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 326 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'ATP Hamburg': 1, 'ATP Mallorca': 1, 'ATP Stuttgart': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Arantxa Rus, Ashlyn Krueger, Ayana Akli, Bianca Andreescu, Cadence Brace, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Casper Ruud, Celine Naef, Chloe Paquet, Claire Liu, Daphnee Mpetshi Perricard, Darja Semenistaja, Darja Vidmanova, Despina Papamichail, Dominika Salkova, Ekaterine Gorgodze, Eleejah Inisan, Elena Pridankina, Elizabeth Mandlik, Elizara Yaneva, Elvina Kalieva, Eva Guerrero Alvarez, Frances Tiafoe
