# Model vs Kalshi — match-by-match scorecard

_Generated 2026-07-25T16:10:27Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1175 | 1109 | 22 | 6 | 38 | 0 | 7 | 12 | 179 | 2026-05-03..2026-07-26 |
| wta | 1189 | 679 | 21 | 457 | 32 | 0 | 2 | 15 | 30 | 2026-05-02..2026-07-25 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1290 | 0.5972 | 0.5872 | -0.0100 ±0.0058 | -0.0041 ±0.0024 | 0.674 | 0.687 |
| atp | 644 | 0.6042 | 0.6102 | +0.0060 ±0.0081 | +0.0024 ±0.0033 | 0.669 | 0.682 |
| wta | 646 | 0.5902 | 0.5643 | -0.0259 ±0.0081 | -0.0106 ±0.0034 | 0.678 | 0.692 |
| pooled/live | 441 | 0.5913 | 0.5634 | -0.0278 ±0.0103 | -0.0093 ±0.0044 | 0.694 | 0.711 |
| pooled/backtest | 849 | 0.6002 | 0.5996 | -0.0007 ±0.0069 | -0.0014 ±0.0028 | 0.663 | 0.674 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live | 441 | -0.0278 ±0.0103 | -0.0093 ±0.0044 | -2.7 | 0.694 | 0.711 | |
| pred_source: backtest | 849 | -0.0007 ±0.0069 | -0.0014 ±0.0028 | -0.1 | 0.663 | 0.674 | |
| top-20 involved | 418 | -0.0003 ±0.0085 | -0.0005 ±0.0030 | -0.0 | 0.740 | 0.733 | |
| no top-20 player | 872 | -0.0146 ±0.0075 | -0.0059 ±0.0032 | -1.9 | 0.642 | 0.665 | |
| both inside top-50 | 256 | +0.0145 ±0.0108 | +0.0066 ±0.0047 | +1.3 | 0.686 | 0.666 | |
| someone outside top-50 | 1034 | -0.0160 ±0.0067 | -0.0068 ±0.0027 | -2.4 | 0.671 | 0.692 | |
| best rank 1-10 | 236 | +0.0132 ±0.0120 | +0.0044 ±0.0037 | +1.1 | 0.746 | 0.742 | |
| best rank 11-20 | 182 | -0.0178 ±0.0119 | -0.0068 ±0.0050 | -1.5 | 0.734 | 0.723 | |
| best rank 21-50 | 443 | -0.0086 ±0.0088 | -0.0023 ±0.0038 | -1.0 | 0.664 | 0.679 | |
| best rank 51-100 | 354 | -0.0079 ±0.0123 | -0.0039 ±0.0053 | -0.6 | 0.623 | 0.644 | |
| best rank 100+ | 75 | -0.0815 ±0.0382 | -0.0360 ±0.0161 | -2.1 | 0.600 | 0.673 | |
| kalshi favorite 0.5-0.6 | 364 | -0.0207 ±0.0102 | -0.0091 ±0.0047 | -2.0 | 0.518 | 0.566 | |
| kalshi favorite 0.6-0.7 | 371 | +0.0001 ±0.0098 | +0.0001 ±0.0045 | +0.0 | 0.631 | 0.631 | |
| kalshi favorite 0.7-0.8 | 288 | -0.0066 ±0.0111 | -0.0026 ±0.0045 | -0.6 | 0.741 | 0.743 | |
| kalshi favorite 0.8-0.9 | 184 | -0.0097 ±0.0183 | -0.0040 ±0.0067 | -0.5 | 0.837 | 0.837 | |
| kalshi favorite 0.9-1.0 | 83 | -0.0198 ±0.0320 | -0.0063 ±0.0081 | -0.6 | 0.952 | 0.940 | |
| surface: Hard | 32 | -0.0832 ±0.0602 | -0.0291 ±0.0248 | -1.4 | 0.719 | 0.688 | ⚠ small n |
| surface: Clay | 684 | +0.0027 ±0.0074 | -0.0001 ±0.0029 | +0.4 | 0.671 | 0.691 | |
| surface: Grass | 574 | -0.0209 ±0.0089 | -0.0075 ±0.0038 | -2.4 | 0.674 | 0.682 | |
| tier: atp250 | 454 | -0.0047 ±0.0103 | -0.0023 ±0.0043 | -0.5 | 0.659 | 0.681 | |
| tier: atp500 | 181 | -0.0148 ±0.0103 | -0.0071 ±0.0046 | -1.4 | 0.608 | 0.622 | |
| tier: grand_slam | 476 | -0.0187 ±0.0107 | -0.0074 ±0.0042 | -1.8 | 0.711 | 0.720 | |
| tier: masters | 179 | +0.0046 ±0.0116 | +0.0032 ±0.0051 | +0.4 | 0.679 | 0.682 | |
| round early (R128-R64) | 506 | -0.0197 ±0.0101 | -0.0073 ±0.0041 | -1.9 | 0.712 | 0.722 | |
| round late (QF-F) | 168 | -0.0002 ±0.0118 | -0.0010 ±0.0050 | -0.0 | 0.655 | 0.655 | |
| round mid (R32-R16) | 594 | -0.0046 ±0.0084 | -0.0023 ±0.0035 | -0.5 | 0.652 | 0.671 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 493 | +0.0035 ±0.0090 | -0.0001 ±0.0035 | +0.4 | 0.677 | 0.687 | |
| month 2026-06 | 439 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.640 | 0.662 | |
| month 2026-07 | 358 | -0.0104 ±0.0109 | -0.0019 ±0.0046 | -1.0 | 0.709 | 0.718 | |
| agree (<0.05) | 616 | +0.0017 ±0.0029 | +0.0002 ±0.0009 | +0.6 | 0.703 | 0.705 | |
| mild disagree (0.05-0.10) | 400 | -0.0057 ±0.0088 | -0.0028 ±0.0034 | -0.6 | 0.641 | 0.672 | |
| big disagree (>=0.1) | 274 | -0.0425 ±0.0230 | -0.0156 ±0.0098 | -1.8 | 0.655 | 0.666 | |
| tour: atp | 644 | +0.0060 ±0.0081 | +0.0024 ±0.0033 | +0.7 | 0.669 | 0.682 | |
| tour: wta | 646 | -0.0259 ±0.0081 | -0.0106 ±0.0034 | -3.2 | 0.678 | 0.692 | |

When they disagree by >= 0.1: model closer to the outcome in **102/274** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 12 | 0.067 | 0.083 |
| 0.1-0.2 | 71 | 0.156 | 0.127 |
| 0.2-0.3 | 112 | 0.249 | 0.196 |
| 0.3-0.4 | 184 | 0.352 | 0.315 |
| 0.4-0.5 | 222 | 0.449 | 0.473 |
| 0.5-0.6 | 213 | 0.550 | 0.563 |
| 0.6-0.7 | 197 | 0.645 | 0.635 |
| 0.7-0.8 | 163 | 0.747 | 0.730 |
| 0.8-0.9 | 92 | 0.844 | 0.848 |
| 0.9-1.0 | 24 | 0.927 | 0.875 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 32 | 0.062 | 0.062 |
| 0.1-0.2 | 78 | 0.153 | 0.115 |
| 0.2-0.3 | 123 | 0.254 | 0.252 |
| 0.3-0.4 | 169 | 0.353 | 0.343 |
| 0.4-0.5 | 192 | 0.442 | 0.432 |
| 0.5-0.6 | 174 | 0.557 | 0.557 |
| 0.6-0.7 | 200 | 0.651 | 0.615 |
| 0.7-0.8 | 165 | 0.747 | 0.739 |
| 0.8-0.9 | 106 | 0.844 | 0.802 |
| 0.9-1.0 | 51 | 0.938 | 0.941 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| both inside top-50 | 256 | +0.0145 ±0.0108 | +0.0066 ±0.0047 | +1.3 | 0.686 | 0.666 | |
| best rank 1-10 | 236 | +0.0132 ±0.0120 | +0.0044 ±0.0037 | +1.1 | 0.746 | 0.742 | |
| tour: atp | 644 | +0.0060 ±0.0081 | +0.0024 ±0.0033 | +0.7 | 0.669 | 0.682 | |
| agree (<0.05) | 616 | +0.0017 ±0.0029 | +0.0002 ±0.0009 | +0.6 | 0.703 | 0.705 | |
| tier: masters | 179 | +0.0046 ±0.0116 | +0.0032 ±0.0051 | +0.4 | 0.679 | 0.682 | |
| month 2026-05 | 493 | +0.0035 ±0.0090 | -0.0001 ±0.0035 | +0.4 | 0.677 | 0.687 | |
| surface: Clay | 684 | +0.0027 ±0.0074 | -0.0001 ±0.0029 | +0.4 | 0.671 | 0.691 | |
| kalshi favorite 0.6-0.7 | 371 | +0.0001 ±0.0098 | +0.0001 ±0.0045 | +0.0 | 0.631 | 0.631 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| round early (R128-R64) | 506 | -0.0197 ±0.0101 | -0.0073 ±0.0041 | -1.9 | 0.712 | 0.722 | |
| kalshi favorite 0.5-0.6 | 364 | -0.0207 ±0.0102 | -0.0091 ±0.0047 | -2.0 | 0.518 | 0.566 | |
| best rank 100+ | 75 | -0.0815 ±0.0382 | -0.0360 ±0.0161 | -2.1 | 0.600 | 0.673 | |
| surface: Grass | 574 | -0.0209 ±0.0089 | -0.0075 ±0.0038 | -2.4 | 0.674 | 0.682 | |
| someone outside top-50 | 1034 | -0.0160 ±0.0067 | -0.0068 ±0.0027 | -2.4 | 0.671 | 0.692 | |
| month 2026-06 | 439 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.640 | 0.662 | |
| pred_source: live | 441 | -0.0278 ±0.0103 | -0.0093 ±0.0044 | -2.7 | 0.694 | 0.711 | |
| tour: wta | 646 | -0.0259 ±0.0081 | -0.0106 ±0.0034 | -3.2 | 0.678 | 0.692 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1290, mean |Δ|=0.0015, p95=0.0086, >0.05 in 0 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0090 (n=493, >0.05: 0) | 2026-06 p95=0.0085 (n=439, >0.05: 0) | 2026-07 p95=0.0075 (n=358, >0.05: 0)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1290, d_ll -0.0100 ±0.0058 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 386 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'WTA Iasi': 6, 'WTA Hamburg': 2, 'ATP Mallorca': 1, 'ATP Kitzbuhel': 1, 'ATP Hamburg': 1, 'ATP Stuttgart': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Arantxa Rus, Ashlyn Krueger, Ayana Akli, Bianca Andreescu, Cadence Brace, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Casper Ruud, Celine Naef, Chloe Paquet, Claire Liu, Dalma Galfi, Daphnee Mpetshi Perricard, Darja Semenistaja, Darja Vidmanova, Despina Papamichail, Dominika Salkova, Ekaterine Gorgodze, Eleejah Inisan, Elena Pridankina, Elizabeth Mandlik, Elizara Yaneva, Elvina Kalieva, Eva Guerrero Alvarez
