# Model vs Kalshi — match-by-match scorecard

_Generated 2026-07-16T08:09:02Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1057 | 1004 | 13 | 6 | 34 | 0 | 6 | 11 | 163 | 2026-05-03..2026-07-16 |
| wta | 1061 | 608 | 17 | 407 | 29 | 0 | 2 | 15 | 18 | 2026-05-02..2026-07-16 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1141 | 0.5949 | 0.5868 | -0.0081 ±0.0061 | -0.0035 ±0.0025 | 0.674 | 0.684 |
| atp | 566 | 0.5980 | 0.6044 | +0.0064 ±0.0088 | +0.0025 ±0.0036 | 0.677 | 0.684 |
| wta | 575 | 0.5919 | 0.5695 | -0.0225 ±0.0083 | -0.0094 ±0.0035 | 0.671 | 0.685 |
| pooled/live | 301 | 0.5733 | 0.5467 | -0.0266 ±0.0126 | -0.0082 ±0.0054 | 0.714 | 0.719 |
| pooled/backtest | 840 | 0.6027 | 0.6011 | -0.0015 ±0.0069 | -0.0018 ±0.0028 | 0.660 | 0.672 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live | 301 | -0.0266 ±0.0126 | -0.0082 ±0.0054 | -2.1 | 0.714 | 0.719 | |
| pred_source: backtest | 840 | -0.0015 ±0.0069 | -0.0018 ±0.0028 | -0.2 | 0.660 | 0.672 | |
| top-20 involved | 402 | +0.0003 ±0.0086 | -0.0000 ±0.0030 | +0.0 | 0.748 | 0.738 | |
| no top-20 player | 739 | -0.0127 ±0.0081 | -0.0054 ±0.0035 | -1.6 | 0.634 | 0.656 | |
| both inside top-50 | 242 | +0.0171 ±0.0112 | +0.0076 ±0.0049 | +1.5 | 0.684 | 0.655 | |
| someone outside top-50 | 899 | -0.0149 ±0.0071 | -0.0065 ±0.0029 | -2.1 | 0.671 | 0.692 | |
| best rank 1-10 | 236 | +0.0132 ±0.0120 | +0.0044 ±0.0037 | +1.1 | 0.746 | 0.742 | |
| best rank 11-20 | 166 | -0.0180 ±0.0119 | -0.0063 ±0.0052 | -1.5 | 0.750 | 0.732 | |
| best rank 21-50 | 389 | -0.0084 ±0.0096 | -0.0026 ±0.0042 | -0.9 | 0.656 | 0.674 | |
| best rank 51-100 | 291 | -0.0070 ±0.0143 | -0.0036 ±0.0061 | -0.5 | 0.610 | 0.629 | |
| best rank 100+ | 59 | -0.0701 ±0.0369 | -0.0329 ±0.0158 | -1.9 | 0.610 | 0.669 | |
| kalshi favorite 0.5-0.6 | 324 | -0.0173 ±0.0104 | -0.0077 ±0.0049 | -1.7 | 0.511 | 0.552 | |
| kalshi favorite 0.6-0.7 | 313 | -0.0029 ±0.0104 | -0.0012 ±0.0049 | -0.3 | 0.636 | 0.633 | |
| kalshi favorite 0.7-0.8 | 258 | -0.0032 ±0.0116 | -0.0011 ±0.0047 | -0.3 | 0.738 | 0.740 | |
| kalshi favorite 0.8-0.9 | 167 | -0.0030 ±0.0192 | -0.0021 ±0.0071 | -0.2 | 0.832 | 0.832 | |
| kalshi favorite 0.9-1.0 | 79 | -0.0183 ±0.0336 | -0.0060 ±0.0085 | -0.5 | 0.949 | 0.937 | |
| surface: Hard | 2 | -0.0075 ±0.0735 | +0.0067 ±0.0215 | -0.1 | 1.000 | 1.000 | ⚠ small n |
| surface: Clay | 575 | +0.0033 ±0.0082 | -0.0001 ±0.0032 | +0.4 | 0.673 | 0.688 | |
| surface: Grass | 564 | -0.0198 ±0.0090 | -0.0070 ±0.0038 | -2.2 | 0.674 | 0.680 | |
| tier: atp250 | 305 | +0.0047 ±0.0125 | +0.0008 ±0.0053 | +0.4 | 0.652 | 0.669 | |
| tier: atp500 | 181 | -0.0148 ±0.0103 | -0.0071 ±0.0046 | -1.4 | 0.608 | 0.622 | |
| tier: grand_slam | 476 | -0.0187 ±0.0107 | -0.0074 ±0.0042 | -1.8 | 0.711 | 0.720 | |
| tier: masters | 179 | +0.0046 ±0.0116 | +0.0032 ±0.0051 | +0.4 | 0.679 | 0.682 | |
| round early (R128-R64) | 506 | -0.0197 ±0.0101 | -0.0073 ±0.0041 | -1.9 | 0.712 | 0.722 | |
| round late (QF-F) | 119 | +0.0052 ±0.0132 | +0.0016 ±0.0057 | +0.4 | 0.664 | 0.639 | |
| round mid (R32-R16) | 494 | +0.0004 ±0.0088 | -0.0009 ±0.0037 | +0.0 | 0.645 | 0.663 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 493 | +0.0035 ±0.0090 | -0.0001 ±0.0035 | +0.4 | 0.677 | 0.687 | |
| month 2026-06 | 439 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.640 | 0.662 | |
| month 2026-07 | 209 | -0.0007 ±0.0132 | +0.0030 ±0.0057 | -0.1 | 0.737 | 0.727 | |
| agree (<0.05) | 558 | +0.0005 ±0.0031 | -0.0004 ±0.0010 | +0.2 | 0.710 | 0.709 | |
| mild disagree (0.05-0.10) | 344 | -0.0041 ±0.0095 | -0.0027 ±0.0037 | -0.4 | 0.629 | 0.666 | |
| big disagree (>=0.1) | 239 | -0.0342 ±0.0245 | -0.0117 ±0.0105 | -1.4 | 0.655 | 0.655 | |
| tour: atp | 566 | +0.0064 ±0.0088 | +0.0025 ±0.0036 | +0.7 | 0.677 | 0.684 | |
| tour: wta | 575 | -0.0225 ±0.0083 | -0.0094 ±0.0035 | -2.7 | 0.671 | 0.685 | |

When they disagree by >= 0.1: model closer to the outcome in **91/239** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 11 | 0.067 | 0.091 |
| 0.1-0.2 | 62 | 0.155 | 0.113 |
| 0.2-0.3 | 100 | 0.249 | 0.200 |
| 0.3-0.4 | 159 | 0.352 | 0.321 |
| 0.4-0.5 | 199 | 0.450 | 0.482 |
| 0.5-0.6 | 192 | 0.551 | 0.562 |
| 0.6-0.7 | 171 | 0.646 | 0.649 |
| 0.7-0.8 | 144 | 0.748 | 0.736 |
| 0.8-0.9 | 81 | 0.845 | 0.840 |
| 0.9-1.0 | 22 | 0.926 | 0.909 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 32 | 0.062 | 0.062 |
| 0.1-0.2 | 69 | 0.154 | 0.130 |
| 0.2-0.3 | 110 | 0.253 | 0.264 |
| 0.3-0.4 | 142 | 0.353 | 0.345 |
| 0.4-0.5 | 172 | 0.443 | 0.448 |
| 0.5-0.6 | 154 | 0.558 | 0.545 |
| 0.6-0.7 | 169 | 0.650 | 0.621 |
| 0.7-0.8 | 148 | 0.747 | 0.743 |
| 0.8-0.9 | 98 | 0.843 | 0.806 |
| 0.9-1.0 | 47 | 0.939 | 0.936 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| both inside top-50 | 242 | +0.0171 ±0.0112 | +0.0076 ±0.0049 | +1.5 | 0.684 | 0.655 | |
| best rank 1-10 | 236 | +0.0132 ±0.0120 | +0.0044 ±0.0037 | +1.1 | 0.746 | 0.742 | |
| tour: atp | 566 | +0.0064 ±0.0088 | +0.0025 ±0.0036 | +0.7 | 0.677 | 0.684 | |
| surface: Clay | 575 | +0.0033 ±0.0082 | -0.0001 ±0.0032 | +0.4 | 0.673 | 0.688 | |
| tier: masters | 179 | +0.0046 ±0.0116 | +0.0032 ±0.0051 | +0.4 | 0.679 | 0.682 | |
| round late (QF-F) | 119 | +0.0052 ±0.0132 | +0.0016 ±0.0057 | +0.4 | 0.664 | 0.639 | |
| month 2026-05 | 493 | +0.0035 ±0.0090 | -0.0001 ±0.0035 | +0.4 | 0.677 | 0.687 | |
| tier: atp250 | 305 | +0.0047 ±0.0125 | +0.0008 ±0.0053 | +0.4 | 0.652 | 0.669 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| tier: grand_slam | 476 | -0.0187 ±0.0107 | -0.0074 ±0.0042 | -1.8 | 0.711 | 0.720 | |
| best rank 100+ | 59 | -0.0701 ±0.0369 | -0.0329 ±0.0158 | -1.9 | 0.610 | 0.669 | |
| round early (R128-R64) | 506 | -0.0197 ±0.0101 | -0.0073 ±0.0041 | -1.9 | 0.712 | 0.722 | |
| someone outside top-50 | 899 | -0.0149 ±0.0071 | -0.0065 ±0.0029 | -2.1 | 0.671 | 0.692 | |
| pred_source: live | 301 | -0.0266 ±0.0126 | -0.0082 ±0.0054 | -2.1 | 0.714 | 0.719 | |
| surface: Grass | 564 | -0.0198 ±0.0090 | -0.0070 ±0.0038 | -2.2 | 0.674 | 0.680 | |
| month 2026-06 | 439 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.640 | 0.662 | |
| tour: wta | 575 | -0.0225 ±0.0083 | -0.0094 ±0.0035 | -2.7 | 0.671 | 0.685 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1141, mean |Δ|=0.0016, p95=0.0086, >0.05 in 0 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0090 (n=493, >0.05: 0) | 2026-06 p95=0.0085 (n=439, >0.05: 0) | 2026-07 p95=0.0083 (n=209, >0.05: 0)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1141, d_ll -0.0081 ±0.0061 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 344 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'ATP Gstaad': 1, 'ATP Hamburg': 1, 'ATP Mallorca': 1, 'ATP Stuttgart': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Arantxa Rus, Ashlyn Krueger, Ayana Akli, Bianca Andreescu, Cadence Brace, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Casper Ruud, Celine Naef, Chloe Paquet, Claire Liu, Daphnee Mpetshi Perricard, Darja Semenistaja, Darja Vidmanova, Despina Papamichail, Dominika Salkova, Ekaterine Gorgodze, Eleejah Inisan, Elena Pridankina, Elizabeth Mandlik, Elizara Yaneva, Elvina Kalieva, Eva Guerrero Alvarez, Frances Tiafoe
