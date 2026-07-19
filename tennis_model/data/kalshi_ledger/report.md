# Model vs Kalshi — match-by-match scorecard

_Generated 2026-07-19T08:12:29Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1115 | 1032 | 42 | 6 | 35 | 0 | 7 | 11 | 183 | 2026-05-03..2026-07-19 |
| wta | 1116 | 624 | 45 | 418 | 29 | 0 | 2 | 15 | 45 | 2026-05-02..2026-07-20 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1183 | 0.5947 | 0.5859 | -0.0087 ±0.0059 | -0.0037 ±0.0024 | 0.675 | 0.687 |
| atp | 592 | 0.5986 | 0.6047 | +0.0061 ±0.0086 | +0.0024 ±0.0035 | 0.676 | 0.686 |
| wta | 591 | 0.5908 | 0.5672 | -0.0236 ±0.0082 | -0.0099 ±0.0034 | 0.673 | 0.689 |
| pooled/live | 342 | 0.5749 | 0.5484 | -0.0265 ±0.0115 | -0.0086 ±0.0050 | 0.711 | 0.724 |
| pooled/backtest | 841 | 0.6027 | 0.6012 | -0.0015 ±0.0069 | -0.0018 ±0.0028 | 0.660 | 0.672 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live | 342 | -0.0265 ±0.0115 | -0.0086 ±0.0050 | -2.3 | 0.711 | 0.724 | |
| pred_source: backtest | 841 | -0.0015 ±0.0069 | -0.0018 ±0.0028 | -0.2 | 0.660 | 0.672 | |
| top-20 involved | 410 | +0.0001 ±0.0085 | -0.0001 ±0.0030 | +0.0 | 0.745 | 0.735 | |
| no top-20 player | 773 | -0.0134 ±0.0079 | -0.0057 ±0.0034 | -1.7 | 0.637 | 0.662 | |
| both inside top-50 | 249 | +0.0160 ±0.0110 | +0.0073 ±0.0048 | +1.4 | 0.689 | 0.661 | |
| someone outside top-50 | 934 | -0.0153 ±0.0069 | -0.0067 ±0.0028 | -2.2 | 0.671 | 0.694 | |
| best rank 1-10 | 236 | +0.0132 ±0.0120 | +0.0044 ±0.0037 | +1.1 | 0.746 | 0.742 | |
| best rank 11-20 | 174 | -0.0177 ±0.0117 | -0.0062 ±0.0050 | -1.5 | 0.744 | 0.727 | |
| best rank 21-50 | 405 | -0.0091 ±0.0093 | -0.0029 ±0.0041 | -1.0 | 0.662 | 0.679 | |
| best rank 51-100 | 308 | -0.0081 ±0.0138 | -0.0042 ±0.0059 | -0.6 | 0.609 | 0.636 | |
| best rank 100+ | 60 | -0.0697 ±0.0362 | -0.0326 ±0.0156 | -1.9 | 0.617 | 0.675 | |
| kalshi favorite 0.5-0.6 | 338 | -0.0167 ±0.0101 | -0.0074 ±0.0047 | -1.7 | 0.519 | 0.562 | |
| kalshi favorite 0.6-0.7 | 328 | -0.0050 ±0.0103 | -0.0022 ±0.0048 | -0.5 | 0.631 | 0.634 | |
| kalshi favorite 0.7-0.8 | 268 | -0.0035 ±0.0113 | -0.0013 ±0.0046 | -0.3 | 0.741 | 0.743 | |
| kalshi favorite 0.8-0.9 | 168 | -0.0033 ±0.0191 | -0.0022 ±0.0071 | -0.2 | 0.833 | 0.833 | |
| kalshi favorite 0.9-1.0 | 81 | -0.0192 ±0.0328 | -0.0061 ±0.0083 | -0.6 | 0.951 | 0.938 | |
| surface: Hard | 3 | +0.0041 ±0.0440 | +0.0090 ±0.0126 | +0.1 | 1.000 | 1.000 | ⚠ small n |
| surface: Clay | 607 | +0.0029 ±0.0079 | -0.0002 ±0.0031 | +0.4 | 0.674 | 0.691 | |
| surface: Grass | 573 | -0.0211 ±0.0089 | -0.0075 ±0.0038 | -2.4 | 0.674 | 0.682 | |
| tier: atp250 | 347 | +0.0012 ±0.0114 | -0.0005 ±0.0049 | +0.1 | 0.657 | 0.680 | |
| tier: atp500 | 181 | -0.0148 ±0.0103 | -0.0071 ±0.0046 | -1.4 | 0.608 | 0.622 | |
| tier: grand_slam | 476 | -0.0187 ±0.0107 | -0.0074 ±0.0042 | -1.8 | 0.711 | 0.720 | |
| tier: masters | 179 | +0.0046 ±0.0116 | +0.0032 ±0.0051 | +0.4 | 0.679 | 0.682 | |
| round early (R128-R64) | 506 | -0.0197 ±0.0101 | -0.0073 ±0.0041 | -1.9 | 0.712 | 0.722 | |
| round late (QF-F) | 146 | -0.0054 ±0.0120 | -0.0028 ±0.0052 | -0.4 | 0.664 | 0.664 | |
| round mid (R32-R16) | 509 | +0.0011 ±0.0087 | -0.0005 ±0.0037 | +0.1 | 0.647 | 0.665 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 493 | +0.0035 ±0.0090 | -0.0001 ±0.0035 | +0.4 | 0.677 | 0.687 | |
| month 2026-06 | 439 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.640 | 0.662 | |
| month 2026-07 | 251 | -0.0048 ±0.0119 | +0.0008 ±0.0052 | -0.4 | 0.729 | 0.733 | |
| agree (<0.05) | 574 | +0.0007 ±0.0031 | -0.0003 ±0.0010 | +0.2 | 0.711 | 0.710 | |
| mild disagree (0.05-0.10) | 362 | -0.0048 ±0.0093 | -0.0029 ±0.0035 | -0.5 | 0.634 | 0.671 | |
| big disagree (>=0.1) | 247 | -0.0364 ±0.0239 | -0.0130 ±0.0103 | -1.5 | 0.650 | 0.658 | |
| tour: atp | 592 | +0.0061 ±0.0086 | +0.0024 ±0.0035 | +0.7 | 0.676 | 0.686 | |
| tour: wta | 591 | -0.0236 ±0.0082 | -0.0099 ±0.0034 | -2.9 | 0.673 | 0.689 | |

When they disagree by >= 0.1: model closer to the outcome in **93/247** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 11 | 0.067 | 0.091 |
| 0.1-0.2 | 64 | 0.155 | 0.109 |
| 0.2-0.3 | 104 | 0.249 | 0.202 |
| 0.3-0.4 | 166 | 0.351 | 0.313 |
| 0.4-0.5 | 206 | 0.450 | 0.481 |
| 0.5-0.6 | 200 | 0.551 | 0.565 |
| 0.6-0.7 | 177 | 0.646 | 0.644 |
| 0.7-0.8 | 148 | 0.749 | 0.736 |
| 0.8-0.9 | 85 | 0.846 | 0.835 |
| 0.9-1.0 | 22 | 0.926 | 0.909 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 32 | 0.062 | 0.062 |
| 0.1-0.2 | 70 | 0.154 | 0.129 |
| 0.2-0.3 | 114 | 0.253 | 0.254 |
| 0.3-0.4 | 151 | 0.352 | 0.338 |
| 0.4-0.5 | 179 | 0.443 | 0.441 |
| 0.5-0.6 | 161 | 0.558 | 0.559 |
| 0.6-0.7 | 175 | 0.649 | 0.617 |
| 0.7-0.8 | 154 | 0.747 | 0.740 |
| 0.8-0.9 | 98 | 0.843 | 0.806 |
| 0.9-1.0 | 49 | 0.939 | 0.939 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| both inside top-50 | 249 | +0.0160 ±0.0110 | +0.0073 ±0.0048 | +1.4 | 0.689 | 0.661 | |
| best rank 1-10 | 236 | +0.0132 ±0.0120 | +0.0044 ±0.0037 | +1.1 | 0.746 | 0.742 | |
| tour: atp | 592 | +0.0061 ±0.0086 | +0.0024 ±0.0035 | +0.7 | 0.676 | 0.686 | |
| tier: masters | 179 | +0.0046 ±0.0116 | +0.0032 ±0.0051 | +0.4 | 0.679 | 0.682 | |
| month 2026-05 | 493 | +0.0035 ±0.0090 | -0.0001 ±0.0035 | +0.4 | 0.677 | 0.687 | |
| surface: Clay | 607 | +0.0029 ±0.0079 | -0.0002 ±0.0031 | +0.4 | 0.674 | 0.691 | |
| agree (<0.05) | 574 | +0.0007 ±0.0031 | -0.0003 ±0.0010 | +0.2 | 0.711 | 0.710 | |
| round mid (R32-R16) | 509 | +0.0011 ±0.0087 | -0.0005 ±0.0037 | +0.1 | 0.647 | 0.665 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| tier: grand_slam | 476 | -0.0187 ±0.0107 | -0.0074 ±0.0042 | -1.8 | 0.711 | 0.720 | |
| best rank 100+ | 60 | -0.0697 ±0.0362 | -0.0326 ±0.0156 | -1.9 | 0.617 | 0.675 | |
| round early (R128-R64) | 506 | -0.0197 ±0.0101 | -0.0073 ±0.0041 | -1.9 | 0.712 | 0.722 | |
| someone outside top-50 | 934 | -0.0153 ±0.0069 | -0.0067 ±0.0028 | -2.2 | 0.671 | 0.694 | |
| pred_source: live | 342 | -0.0265 ±0.0115 | -0.0086 ±0.0050 | -2.3 | 0.711 | 0.724 | |
| surface: Grass | 573 | -0.0211 ±0.0089 | -0.0075 ±0.0038 | -2.4 | 0.674 | 0.682 | |
| month 2026-06 | 439 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.640 | 0.662 | |
| tour: wta | 591 | -0.0236 ±0.0082 | -0.0099 ±0.0034 | -2.9 | 0.673 | 0.689 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1183, mean |Δ|=0.0015, p95=0.0086, >0.05 in 0 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0090 (n=493, >0.05: 0) | 2026-06 p95=0.0085 (n=439, >0.05: 0) | 2026-07 p95=0.0082 (n=251, >0.05: 0)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1183, d_ll -0.0087 ±0.0059 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 350 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'WTA Iasi': 5, 'ATP Hamburg': 1, 'ATP Gstaad': 1, 'ATP Stuttgart': 1, 'ATP Mallorca': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Arantxa Rus, Ashlyn Krueger, Ayana Akli, Bianca Andreescu, Cadence Brace, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Casper Ruud, Celine Naef, Chloe Paquet, Claire Liu, Dalma Galfi, Daphnee Mpetshi Perricard, Darja Semenistaja, Darja Vidmanova, Despina Papamichail, Dominika Salkova, Ekaterine Gorgodze, Eleejah Inisan, Elena Pridankina, Elizabeth Mandlik, Elizara Yaneva, Elsa Jacquemot, Elvina Kalieva
