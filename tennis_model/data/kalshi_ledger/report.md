# Model vs Kalshi — match-by-match scorecard

_Generated 2026-07-17T08:07:40Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1066 | 1015 | 11 | 6 | 34 | 0 | 6 | 11 | 165 | 2026-05-03..2026-07-17 |
| wta | 1069 | 614 | 12 | 414 | 29 | 0 | 2 | 15 | 22 | 2026-05-02..2026-07-17 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1158 | 0.5941 | 0.5852 | -0.0090 ±0.0060 | -0.0039 ±0.0025 | 0.673 | 0.686 |
| atp | 577 | 0.5976 | 0.6034 | +0.0058 ±0.0087 | +0.0022 ±0.0036 | 0.674 | 0.685 |
| wta | 581 | 0.5907 | 0.5671 | -0.0236 ±0.0083 | -0.0099 ±0.0034 | 0.671 | 0.687 |
| pooled/live | 318 | 0.5716 | 0.5430 | -0.0286 ±0.0121 | -0.0094 ±0.0052 | 0.708 | 0.722 |
| pooled/backtest | 840 | 0.6027 | 0.6011 | -0.0015 ±0.0069 | -0.0018 ±0.0028 | 0.660 | 0.672 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live | 318 | -0.0286 ±0.0121 | -0.0094 ±0.0052 | -2.4 | 0.708 | 0.722 | |
| pred_source: backtest | 840 | -0.0015 ±0.0069 | -0.0018 ±0.0028 | -0.2 | 0.660 | 0.672 | |
| top-20 involved | 405 | +0.0007 ±0.0085 | +0.0001 ±0.0030 | +0.1 | 0.747 | 0.737 | |
| no top-20 player | 753 | -0.0142 ±0.0080 | -0.0061 ±0.0035 | -1.8 | 0.633 | 0.658 | |
| both inside top-50 | 242 | +0.0171 ±0.0112 | +0.0076 ±0.0049 | +1.5 | 0.684 | 0.655 | |
| someone outside top-50 | 916 | -0.0158 ±0.0070 | -0.0069 ±0.0029 | -2.3 | 0.670 | 0.694 | |
| best rank 1-10 | 236 | +0.0132 ±0.0120 | +0.0044 ±0.0037 | +1.1 | 0.746 | 0.742 | |
| best rank 11-20 | 169 | -0.0166 ±0.0118 | -0.0059 ±0.0051 | -1.4 | 0.749 | 0.731 | |
| best rank 21-50 | 394 | -0.0100 ±0.0096 | -0.0033 ±0.0042 | -1.0 | 0.655 | 0.673 | |
| best rank 51-100 | 299 | -0.0085 ±0.0140 | -0.0044 ±0.0060 | -0.6 | 0.607 | 0.635 | |
| best rank 100+ | 60 | -0.0697 ±0.0362 | -0.0326 ±0.0156 | -1.9 | 0.617 | 0.675 | |
| kalshi favorite 0.5-0.6 | 329 | -0.0186 ±0.0103 | -0.0083 ±0.0048 | -1.8 | 0.509 | 0.553 | |
| kalshi favorite 0.6-0.7 | 319 | -0.0049 ±0.0103 | -0.0021 ±0.0048 | -0.5 | 0.630 | 0.633 | |
| kalshi favorite 0.7-0.8 | 261 | -0.0022 ±0.0115 | -0.0008 ±0.0047 | -0.2 | 0.741 | 0.743 | |
| kalshi favorite 0.8-0.9 | 168 | -0.0033 ±0.0191 | -0.0022 ±0.0071 | -0.2 | 0.833 | 0.833 | |
| kalshi favorite 0.9-1.0 | 81 | -0.0192 ±0.0328 | -0.0061 ±0.0083 | -0.6 | 0.951 | 0.938 | |
| surface: Hard | 2 | -0.0075 ±0.0735 | +0.0067 ±0.0215 | -0.1 | 1.000 | 1.000 | ⚠ small n |
| surface: Clay | 588 | +0.0027 ±0.0080 | -0.0004 ±0.0032 | +0.3 | 0.672 | 0.690 | |
| surface: Grass | 568 | -0.0211 ±0.0090 | -0.0075 ±0.0038 | -2.3 | 0.673 | 0.680 | |
| tier: atp250 | 322 | +0.0011 ±0.0120 | -0.0008 ±0.0051 | +0.1 | 0.649 | 0.674 | |
| tier: atp500 | 181 | -0.0148 ±0.0103 | -0.0071 ±0.0046 | -1.4 | 0.608 | 0.622 | |
| tier: grand_slam | 476 | -0.0187 ±0.0107 | -0.0074 ±0.0042 | -1.8 | 0.711 | 0.720 | |
| tier: masters | 179 | +0.0046 ±0.0116 | +0.0032 ±0.0051 | +0.4 | 0.679 | 0.682 | |
| round early (R128-R64) | 506 | -0.0197 ±0.0101 | -0.0073 ±0.0041 | -1.9 | 0.712 | 0.722 | |
| round late (QF-F) | 123 | -0.0011 ±0.0132 | -0.0013 ±0.0058 | -0.1 | 0.642 | 0.634 | |
| round mid (R32-R16) | 507 | -0.0003 ±0.0086 | -0.0012 ±0.0037 | -0.0 | 0.648 | 0.668 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 493 | +0.0035 ±0.0090 | -0.0001 ±0.0035 | +0.4 | 0.677 | 0.687 | |
| month 2026-06 | 439 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.640 | 0.662 | |
| month 2026-07 | 226 | -0.0055 ±0.0127 | +0.0005 ±0.0055 | -0.4 | 0.726 | 0.730 | |
| agree (<0.05) | 564 | +0.0005 ±0.0031 | -0.0004 ±0.0010 | +0.2 | 0.709 | 0.708 | |
| mild disagree (0.05-0.10) | 351 | -0.0049 ±0.0094 | -0.0031 ±0.0036 | -0.5 | 0.631 | 0.670 | |
| big disagree (>=0.1) | 243 | -0.0368 ±0.0242 | -0.0131 ±0.0104 | -1.5 | 0.648 | 0.656 | |
| tour: atp | 577 | +0.0058 ±0.0087 | +0.0022 ±0.0036 | +0.7 | 0.674 | 0.685 | |
| tour: wta | 581 | -0.0236 ±0.0083 | -0.0099 ±0.0034 | -2.9 | 0.671 | 0.687 | |

When they disagree by >= 0.1: model closer to the outcome in **92/243** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 11 | 0.067 | 0.091 |
| 0.1-0.2 | 63 | 0.155 | 0.111 |
| 0.2-0.3 | 103 | 0.248 | 0.204 |
| 0.3-0.4 | 161 | 0.351 | 0.323 |
| 0.4-0.5 | 201 | 0.450 | 0.483 |
| 0.5-0.6 | 196 | 0.551 | 0.556 |
| 0.6-0.7 | 172 | 0.646 | 0.645 |
| 0.7-0.8 | 145 | 0.749 | 0.738 |
| 0.8-0.9 | 84 | 0.846 | 0.845 |
| 0.9-1.0 | 22 | 0.926 | 0.909 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 32 | 0.062 | 0.062 |
| 0.1-0.2 | 70 | 0.154 | 0.129 |
| 0.2-0.3 | 111 | 0.253 | 0.261 |
| 0.3-0.4 | 146 | 0.353 | 0.342 |
| 0.4-0.5 | 175 | 0.443 | 0.446 |
| 0.5-0.6 | 156 | 0.558 | 0.545 |
| 0.6-0.7 | 171 | 0.650 | 0.620 |
| 0.7-0.8 | 150 | 0.747 | 0.747 |
| 0.8-0.9 | 98 | 0.843 | 0.806 |
| 0.9-1.0 | 49 | 0.939 | 0.939 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| both inside top-50 | 242 | +0.0171 ±0.0112 | +0.0076 ±0.0049 | +1.5 | 0.684 | 0.655 | |
| best rank 1-10 | 236 | +0.0132 ±0.0120 | +0.0044 ±0.0037 | +1.1 | 0.746 | 0.742 | |
| tour: atp | 577 | +0.0058 ±0.0087 | +0.0022 ±0.0036 | +0.7 | 0.674 | 0.685 | |
| tier: masters | 179 | +0.0046 ±0.0116 | +0.0032 ±0.0051 | +0.4 | 0.679 | 0.682 | |
| month 2026-05 | 493 | +0.0035 ±0.0090 | -0.0001 ±0.0035 | +0.4 | 0.677 | 0.687 | |
| surface: Clay | 588 | +0.0027 ±0.0080 | -0.0004 ±0.0032 | +0.3 | 0.672 | 0.690 | |
| agree (<0.05) | 564 | +0.0005 ±0.0031 | -0.0004 ±0.0010 | +0.2 | 0.709 | 0.708 | |
| tier: atp250 | 322 | +0.0011 ±0.0120 | -0.0008 ±0.0051 | +0.1 | 0.649 | 0.674 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| kalshi favorite 0.5-0.6 | 329 | -0.0186 ±0.0103 | -0.0083 ±0.0048 | -1.8 | 0.509 | 0.553 | |
| best rank 100+ | 60 | -0.0697 ±0.0362 | -0.0326 ±0.0156 | -1.9 | 0.617 | 0.675 | |
| round early (R128-R64) | 506 | -0.0197 ±0.0101 | -0.0073 ±0.0041 | -1.9 | 0.712 | 0.722 | |
| someone outside top-50 | 916 | -0.0158 ±0.0070 | -0.0069 ±0.0029 | -2.3 | 0.670 | 0.694 | |
| surface: Grass | 568 | -0.0211 ±0.0090 | -0.0075 ±0.0038 | -2.3 | 0.673 | 0.680 | |
| pred_source: live | 318 | -0.0286 ±0.0121 | -0.0094 ±0.0052 | -2.4 | 0.708 | 0.722 | |
| month 2026-06 | 439 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.640 | 0.662 | |
| tour: wta | 581 | -0.0236 ±0.0083 | -0.0099 ±0.0034 | -2.9 | 0.671 | 0.687 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1158, mean |Δ|=0.0015, p95=0.0086, >0.05 in 0 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0090 (n=493, >0.05: 0) | 2026-06 p95=0.0085 (n=439, >0.05: 0) | 2026-07 p95=0.0071 (n=226, >0.05: 0)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1158, d_ll -0.0090 ±0.0060 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 350 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'ATP Gstaad': 1, 'ATP Hamburg': 1, 'ATP Mallorca': 1, 'ATP Stuttgart': 1, 'WTA Iasi': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Arantxa Rus, Ashlyn Krueger, Ayana Akli, Bianca Andreescu, Cadence Brace, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Casper Ruud, Celine Naef, Chloe Paquet, Claire Liu, Dalma Galfi, Daphnee Mpetshi Perricard, Darja Semenistaja, Darja Vidmanova, Despina Papamichail, Dominika Salkova, Ekaterine Gorgodze, Eleejah Inisan, Elena Pridankina, Elizabeth Mandlik, Elizara Yaneva, Elvina Kalieva, Eva Guerrero Alvarez
