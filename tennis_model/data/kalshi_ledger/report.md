# Model vs Kalshi — match-by-match scorecard

_Generated 2026-07-10T09:22:57Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 956 | 915 | 2 | 6 | 33 | 0 | 6 | 9 | 157 | 2026-05-03..2026-07-10 |
| wta | 976 | 571 | 0 | 380 | 25 | 0 | 2 | 15 | 13 | 2026-05-02..2026-07-09 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1053 | 0.5968 | 0.5883 | -0.0085 ±0.0064 | -0.0037 ±0.0026 | 0.670 | 0.678 |
| atp | 514 | 0.6007 | 0.6071 | +0.0064 ±0.0095 | +0.0025 ±0.0038 | 0.675 | 0.677 |
| wta | 539 | 0.5931 | 0.5703 | -0.0227 ±0.0085 | -0.0096 ±0.0035 | 0.666 | 0.679 |
| pooled/live | 221 | 0.5699 | 0.5322 | -0.0377 ±0.0154 | -0.0116 ±0.0066 | 0.715 | 0.704 |
| pooled/backtest | 832 | 0.6040 | 0.6032 | -0.0008 ±0.0069 | -0.0016 ±0.0028 | 0.659 | 0.671 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live | 221 | -0.0377 ±0.0154 | -0.0116 ±0.0066 | -2.5 | 0.715 | 0.704 | |
| pred_source: backtest | 832 | -0.0008 ±0.0069 | -0.0016 ±0.0028 | -0.1 | 0.659 | 0.671 | |
| top-20 involved | 396 | -0.0003 ±0.0086 | -0.0004 ±0.0030 | -0.0 | 0.746 | 0.739 | |
| no top-20 player | 657 | -0.0135 ±0.0088 | -0.0057 ±0.0038 | -1.5 | 0.625 | 0.642 | |
| both inside top-50 | 239 | +0.0155 ±0.0112 | +0.0068 ±0.0049 | +1.4 | 0.680 | 0.655 | |
| someone outside top-50 | 814 | -0.0156 ±0.0075 | -0.0067 ±0.0030 | -2.1 | 0.668 | 0.685 | |
| best rank 1-10 | 232 | +0.0145 ±0.0121 | +0.0049 ±0.0037 | +1.2 | 0.746 | 0.741 | |
| best rank 11-20 | 164 | -0.0211 ±0.0117 | -0.0078 ±0.0050 | -1.8 | 0.747 | 0.735 | |
| best rank 21-50 | 366 | -0.0111 ±0.0100 | -0.0037 ±0.0044 | -1.1 | 0.648 | 0.669 | |
| best rank 51-100 | 251 | -0.0077 ±0.0160 | -0.0043 ±0.0068 | -0.5 | 0.584 | 0.598 | |
| best rank 100+ | 40 | -0.0716 ±0.0475 | -0.0321 ±0.0198 | -1.5 | 0.675 | 0.662 | ⚠ small n |
| kalshi favorite 0.5-0.6 | 296 | -0.0207 ±0.0110 | -0.0093 ±0.0051 | -1.9 | 0.492 | 0.534 | |
| kalshi favorite 0.6-0.7 | 287 | -0.0036 ±0.0106 | -0.0013 ±0.0050 | -0.3 | 0.641 | 0.631 | |
| kalshi favorite 0.7-0.8 | 241 | -0.0030 ±0.0123 | -0.0010 ±0.0051 | -0.2 | 0.728 | 0.730 | |
| kalshi favorite 0.8-0.9 | 154 | -0.0006 ±0.0199 | -0.0008 ±0.0073 | -0.0 | 0.844 | 0.838 | |
| kalshi favorite 0.9-1.0 | 75 | -0.0135 ±0.0352 | -0.0052 ±0.0089 | -0.4 | 0.947 | 0.933 | |
| surface: Clay | 510 | +0.0034 ±0.0088 | -0.0002 ±0.0034 | +0.4 | 0.673 | 0.683 | |
| surface: Grass | 543 | -0.0197 ±0.0091 | -0.0069 ±0.0039 | -2.2 | 0.669 | 0.673 | |
| tier: atp250 | 220 | +0.0077 ±0.0153 | +0.0017 ±0.0064 | +0.5 | 0.632 | 0.636 | |
| tier: atp500 | 181 | -0.0148 ±0.0103 | -0.0071 ±0.0046 | -1.4 | 0.608 | 0.622 | |
| tier: grand_slam | 473 | -0.0186 ±0.0107 | -0.0074 ±0.0042 | -1.7 | 0.709 | 0.718 | |
| tier: masters | 179 | +0.0046 ±0.0116 | +0.0032 ±0.0051 | +0.4 | 0.679 | 0.682 | |
| round early (R128-R64) | 505 | -0.0197 ±0.0101 | -0.0073 ±0.0041 | -1.9 | 0.712 | 0.722 | |
| round late (QF-F) | 117 | +0.0055 ±0.0134 | +0.0017 ±0.0058 | +0.4 | 0.658 | 0.632 | |
| round mid (R32-R16) | 409 | +0.0010 ±0.0097 | -0.0008 ±0.0040 | +0.1 | 0.632 | 0.644 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 493 | +0.0035 ±0.0090 | -0.0001 ±0.0035 | +0.4 | 0.677 | 0.687 | |
| month 2026-06 | 438 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.639 | 0.661 | |
| month 2026-07 | 122 | +0.0009 ±0.0174 | +0.0062 ±0.0073 | +0.1 | 0.754 | 0.705 | |
| agree (<0.05) | 515 | +0.0007 ±0.0033 | -0.0005 ±0.0010 | +0.2 | 0.707 | 0.704 | |
| mild disagree (0.05-0.10) | 322 | -0.0069 ±0.0099 | -0.0038 ±0.0038 | -0.7 | 0.626 | 0.661 | |
| big disagree (>=0.1) | 216 | -0.0330 ±0.0261 | -0.0111 ±0.0111 | -1.3 | 0.650 | 0.641 | |
| tour: atp | 514 | +0.0064 ±0.0095 | +0.0025 ±0.0038 | +0.7 | 0.675 | 0.677 | |
| tour: wta | 539 | -0.0227 ±0.0085 | -0.0096 ±0.0035 | -2.7 | 0.666 | 0.679 | |

When they disagree by >= 0.1: model closer to the outcome in **80/216** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 10 | 0.064 | 0.100 |
| 0.1-0.2 | 58 | 0.154 | 0.103 |
| 0.2-0.3 | 90 | 0.249 | 0.200 |
| 0.3-0.4 | 146 | 0.352 | 0.322 |
| 0.4-0.5 | 180 | 0.450 | 0.483 |
| 0.5-0.6 | 183 | 0.551 | 0.552 |
| 0.6-0.7 | 160 | 0.645 | 0.644 |
| 0.7-0.8 | 133 | 0.748 | 0.737 |
| 0.8-0.9 | 72 | 0.845 | 0.833 |
| 0.9-1.0 | 21 | 0.927 | 0.905 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 30 | 0.062 | 0.067 |
| 0.1-0.2 | 67 | 0.153 | 0.119 |
| 0.2-0.3 | 101 | 0.254 | 0.277 |
| 0.3-0.4 | 129 | 0.353 | 0.349 |
| 0.4-0.5 | 159 | 0.444 | 0.459 |
| 0.5-0.6 | 139 | 0.557 | 0.518 |
| 0.6-0.7 | 156 | 0.650 | 0.622 |
| 0.7-0.8 | 140 | 0.746 | 0.736 |
| 0.8-0.9 | 87 | 0.843 | 0.805 |
| 0.9-1.0 | 45 | 0.939 | 0.933 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| both inside top-50 | 239 | +0.0155 ±0.0112 | +0.0068 ±0.0049 | +1.4 | 0.680 | 0.655 | |
| best rank 1-10 | 232 | +0.0145 ±0.0121 | +0.0049 ±0.0037 | +1.2 | 0.746 | 0.741 | |
| tour: atp | 514 | +0.0064 ±0.0095 | +0.0025 ±0.0038 | +0.7 | 0.675 | 0.677 | |
| tier: atp250 | 220 | +0.0077 ±0.0153 | +0.0017 ±0.0064 | +0.5 | 0.632 | 0.636 | |
| round late (QF-F) | 117 | +0.0055 ±0.0134 | +0.0017 ±0.0058 | +0.4 | 0.658 | 0.632 | |
| tier: masters | 179 | +0.0046 ±0.0116 | +0.0032 ±0.0051 | +0.4 | 0.679 | 0.682 | |
| month 2026-05 | 493 | +0.0035 ±0.0090 | -0.0001 ±0.0035 | +0.4 | 0.677 | 0.687 | |
| surface: Clay | 510 | +0.0034 ±0.0088 | -0.0002 ±0.0034 | +0.4 | 0.673 | 0.683 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 11-20 | 164 | -0.0211 ±0.0117 | -0.0078 ±0.0050 | -1.8 | 0.747 | 0.735 | |
| kalshi favorite 0.5-0.6 | 296 | -0.0207 ±0.0110 | -0.0093 ±0.0051 | -1.9 | 0.492 | 0.534 | |
| round early (R128-R64) | 505 | -0.0197 ±0.0101 | -0.0073 ±0.0041 | -1.9 | 0.712 | 0.722 | |
| someone outside top-50 | 814 | -0.0156 ±0.0075 | -0.0067 ±0.0030 | -2.1 | 0.668 | 0.685 | |
| surface: Grass | 543 | -0.0197 ±0.0091 | -0.0069 ±0.0039 | -2.2 | 0.669 | 0.673 | |
| month 2026-06 | 438 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.639 | 0.661 | |
| pred_source: live | 221 | -0.0377 ±0.0154 | -0.0116 ±0.0066 | -2.5 | 0.715 | 0.704 | |
| tour: wta | 539 | -0.0227 ±0.0085 | -0.0096 ±0.0035 | -2.7 | 0.666 | 0.679 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1053, mean |Δ|=0.0016, p95=0.0086, >0.05 in 0 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0090 (n=493, >0.05: 0) | 2026-06 p95=0.0085 (n=438, >0.05: 0) | 2026-07 p95=0.0072 (n=122, >0.05: 0)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1053, d_ll -0.0085 ±0.0064 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 317 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'ATP Hamburg': 1, 'ATP Mallorca': 1, 'ATP Stuttgart': 1, 'Wimbledon': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Arantxa Rus, Ashlyn Krueger, Ayana Akli, Bianca Andreescu, Cadence Brace, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Casper Ruud, Celine Naef, Chloe Paquet, Claire Liu, Daphnee Mpetshi Perricard, Darja Semenistaja, Darja Vidmanova, Despina Papamichail, Dominika Salkova, Ekaterine Gorgodze, Eleejah Inisan, Elena Pridankina, Elizabeth Mandlik, Elizara Yaneva, Elvina Kalieva, Eva Guerrero Alvarez, Frances Tiafoe
