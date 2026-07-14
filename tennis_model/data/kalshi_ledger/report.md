# Model vs Kalshi — match-by-match scorecard

_Generated 2026-07-14T08:01:13Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1029 | 963 | 28 | 5 | 33 | 0 | 6 | 11 | 166 | 2026-05-03..2026-07-14 |
| wta | 1045 | 583 | 53 | 380 | 29 | 0 | 2 | 15 | 22 | 2026-05-02..2026-07-14 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1076 | 0.5959 | 0.5857 | -0.0102 ±0.0063 | -0.0044 ±0.0026 | 0.671 | 0.682 |
| atp | 526 | 0.5993 | 0.6043 | +0.0050 ±0.0093 | +0.0019 ±0.0038 | 0.675 | 0.681 |
| wta | 550 | 0.5925 | 0.5679 | -0.0246 ±0.0085 | -0.0104 ±0.0035 | 0.667 | 0.684 |
| pooled/live | 239 | 0.5713 | 0.5317 | -0.0396 ±0.0147 | -0.0130 ±0.0063 | 0.711 | 0.713 |
| pooled/backtest | 837 | 0.6029 | 0.6011 | -0.0017 ±0.0069 | -0.0019 ±0.0028 | 0.659 | 0.673 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live | 239 | -0.0396 ±0.0147 | -0.0130 ±0.0063 | -2.7 | 0.711 | 0.713 | |
| pred_source: backtest | 837 | -0.0017 ±0.0069 | -0.0019 ±0.0028 | -0.3 | 0.659 | 0.673 | |
| top-20 involved | 399 | -0.0004 ±0.0086 | -0.0004 ±0.0030 | -0.0 | 0.748 | 0.741 | |
| no top-20 player | 677 | -0.0159 ±0.0086 | -0.0068 ±0.0037 | -1.8 | 0.626 | 0.648 | |
| both inside top-50 | 241 | +0.0152 ±0.0111 | +0.0067 ±0.0048 | +1.4 | 0.683 | 0.658 | |
| someone outside top-50 | 835 | -0.0175 ±0.0074 | -0.0076 ±0.0030 | -2.3 | 0.668 | 0.689 | |
| best rank 1-10 | 235 | +0.0140 ±0.0120 | +0.0048 ±0.0037 | +1.2 | 0.749 | 0.745 | |
| best rank 11-20 | 164 | -0.0211 ±0.0117 | -0.0078 ±0.0050 | -1.8 | 0.747 | 0.735 | |
| best rank 21-50 | 372 | -0.0104 ±0.0100 | -0.0035 ±0.0043 | -1.0 | 0.648 | 0.669 | |
| best rank 51-100 | 260 | -0.0094 ±0.0155 | -0.0048 ±0.0066 | -0.6 | 0.594 | 0.612 | |
| best rank 100+ | 45 | -0.0983 ±0.0446 | -0.0451 ±0.0190 | -2.2 | 0.622 | 0.678 | ⚠ small n |
| kalshi favorite 0.5-0.6 | 302 | -0.0230 ±0.0109 | -0.0104 ±0.0051 | -2.1 | 0.488 | 0.540 | |
| kalshi favorite 0.6-0.7 | 290 | -0.0057 ±0.0107 | -0.0023 ±0.0050 | -0.5 | 0.641 | 0.634 | |
| kalshi favorite 0.7-0.8 | 248 | -0.0048 ±0.0120 | -0.0017 ±0.0049 | -0.4 | 0.732 | 0.734 | |
| kalshi favorite 0.8-0.9 | 159 | +0.0011 ±0.0195 | -0.0003 ±0.0072 | +0.1 | 0.843 | 0.836 | |
| kalshi favorite 0.9-1.0 | 77 | -0.0169 ±0.0345 | -0.0059 ±0.0087 | -0.5 | 0.948 | 0.935 | |
| surface: Hard | 1 | +0.0660 ±0.0000 | +0.0282 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| surface: Clay | 522 | +0.0008 ±0.0087 | -0.0014 ±0.0034 | +0.1 | 0.670 | 0.687 | |
| surface: Grass | 553 | -0.0206 ±0.0090 | -0.0073 ±0.0039 | -2.3 | 0.671 | 0.677 | |
| tier: atp250 | 240 | -0.0008 ±0.0147 | -0.0021 ±0.0061 | -0.1 | 0.633 | 0.654 | |
| tier: atp500 | 181 | -0.0148 ±0.0103 | -0.0071 ±0.0046 | -1.4 | 0.608 | 0.622 | |
| tier: grand_slam | 476 | -0.0187 ±0.0107 | -0.0074 ±0.0042 | -1.8 | 0.711 | 0.720 | |
| tier: masters | 179 | +0.0046 ±0.0116 | +0.0032 ±0.0051 | +0.4 | 0.679 | 0.682 | |
| round early (R128-R64) | 506 | -0.0197 ±0.0101 | -0.0073 ±0.0041 | -1.9 | 0.712 | 0.722 | |
| round late (QF-F) | 119 | +0.0052 ±0.0132 | +0.0016 ±0.0057 | +0.4 | 0.664 | 0.639 | |
| round mid (R32-R16) | 429 | -0.0034 ±0.0096 | -0.0027 ±0.0040 | -0.4 | 0.633 | 0.654 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 493 | +0.0035 ±0.0090 | -0.0001 ±0.0035 | +0.4 | 0.677 | 0.687 | |
| month 2026-06 | 439 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.640 | 0.662 | |
| month 2026-07 | 144 | -0.0124 ±0.0164 | -0.0008 ±0.0070 | -0.8 | 0.743 | 0.729 | |
| agree (<0.05) | 526 | +0.0004 ±0.0033 | -0.0005 ±0.0010 | +0.1 | 0.711 | 0.708 | |
| mild disagree (0.05-0.10) | 328 | -0.0065 ±0.0099 | -0.0039 ±0.0038 | -0.7 | 0.623 | 0.662 | |
| big disagree (>=0.1) | 222 | -0.0406 ±0.0257 | -0.0144 ±0.0109 | -1.6 | 0.646 | 0.651 | |
| tour: atp | 526 | +0.0050 ±0.0093 | +0.0019 ±0.0038 | +0.5 | 0.675 | 0.681 | |
| tour: wta | 550 | -0.0246 ±0.0085 | -0.0104 ±0.0035 | -2.9 | 0.667 | 0.684 | |

When they disagree by >= 0.1: model closer to the outcome in **80/222** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 10 | 0.064 | 0.100 |
| 0.1-0.2 | 59 | 0.154 | 0.119 |
| 0.2-0.3 | 91 | 0.250 | 0.198 |
| 0.3-0.4 | 152 | 0.352 | 0.329 |
| 0.4-0.5 | 181 | 0.451 | 0.486 |
| 0.5-0.6 | 185 | 0.551 | 0.551 |
| 0.6-0.7 | 162 | 0.645 | 0.648 |
| 0.7-0.8 | 139 | 0.748 | 0.741 |
| 0.8-0.9 | 75 | 0.845 | 0.840 |
| 0.9-1.0 | 22 | 0.926 | 0.909 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 30 | 0.062 | 0.067 |
| 0.1-0.2 | 67 | 0.153 | 0.119 |
| 0.2-0.3 | 104 | 0.254 | 0.279 |
| 0.3-0.4 | 130 | 0.353 | 0.346 |
| 0.4-0.5 | 162 | 0.444 | 0.457 |
| 0.5-0.6 | 142 | 0.557 | 0.528 |
| 0.6-0.7 | 158 | 0.650 | 0.627 |
| 0.7-0.8 | 144 | 0.747 | 0.743 |
| 0.8-0.9 | 92 | 0.844 | 0.804 |
| 0.9-1.0 | 47 | 0.939 | 0.936 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| both inside top-50 | 241 | +0.0152 ±0.0111 | +0.0067 ±0.0048 | +1.4 | 0.683 | 0.658 | |
| best rank 1-10 | 235 | +0.0140 ±0.0120 | +0.0048 ±0.0037 | +1.2 | 0.749 | 0.745 | |
| tour: atp | 526 | +0.0050 ±0.0093 | +0.0019 ±0.0038 | +0.5 | 0.675 | 0.681 | |
| tier: masters | 179 | +0.0046 ±0.0116 | +0.0032 ±0.0051 | +0.4 | 0.679 | 0.682 | |
| round late (QF-F) | 119 | +0.0052 ±0.0132 | +0.0016 ±0.0057 | +0.4 | 0.664 | 0.639 | |
| month 2026-05 | 493 | +0.0035 ±0.0090 | -0.0001 ±0.0035 | +0.4 | 0.677 | 0.687 | |
| agree (<0.05) | 526 | +0.0004 ±0.0033 | -0.0005 ±0.0010 | +0.1 | 0.711 | 0.708 | |
| surface: Clay | 522 | +0.0008 ±0.0087 | -0.0014 ±0.0034 | +0.1 | 0.670 | 0.687 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| round early (R128-R64) | 506 | -0.0197 ±0.0101 | -0.0073 ±0.0041 | -1.9 | 0.712 | 0.722 | |
| kalshi favorite 0.5-0.6 | 302 | -0.0230 ±0.0109 | -0.0104 ±0.0051 | -2.1 | 0.488 | 0.540 | |
| best rank 100+ | 45 | -0.0983 ±0.0446 | -0.0451 ±0.0190 | -2.2 | 0.622 | 0.678 | ⚠ small n |
| surface: Grass | 553 | -0.0206 ±0.0090 | -0.0073 ±0.0039 | -2.3 | 0.671 | 0.677 | |
| someone outside top-50 | 835 | -0.0175 ±0.0074 | -0.0076 ±0.0030 | -2.3 | 0.668 | 0.689 | |
| month 2026-06 | 439 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.640 | 0.662 | |
| pred_source: live | 239 | -0.0396 ±0.0147 | -0.0130 ±0.0063 | -2.7 | 0.711 | 0.713 | |
| tour: wta | 550 | -0.0246 ±0.0085 | -0.0104 ±0.0035 | -2.9 | 0.667 | 0.684 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1076, mean |Δ|=0.0016, p95=0.0086, >0.05 in 0 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0090 (n=493, >0.05: 0) | 2026-06 p95=0.0085 (n=439, >0.05: 0) | 2026-07 p95=0.0094 (n=144, >0.05: 0)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1076, d_ll -0.0102 ±0.0063 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 317 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'ATP Hamburg': 1, 'ATP Mallorca': 1, 'ATP Stuttgart': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Arantxa Rus, Ashlyn Krueger, Ayana Akli, Bianca Andreescu, Cadence Brace, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Casper Ruud, Celine Naef, Chloe Paquet, Claire Liu, Daphnee Mpetshi Perricard, Darja Semenistaja, Darja Vidmanova, Despina Papamichail, Dominika Salkova, Ekaterine Gorgodze, Eleejah Inisan, Elena Pridankina, Elizabeth Mandlik, Elizara Yaneva, Elvina Kalieva, Eva Guerrero Alvarez, Frances Tiafoe
