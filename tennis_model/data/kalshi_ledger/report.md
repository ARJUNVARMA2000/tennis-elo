# Model vs Kalshi — match-by-match scorecard

_Generated 2026-07-18T07:41:52Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1088 | 1027 | 21 | 6 | 34 | 0 | 7 | 11 | 178 | 2026-05-03..2026-07-18 |
| wta | 1085 | 621 | 19 | 416 | 29 | 0 | 2 | 15 | 30 | 2026-05-02..2026-07-18 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1175 | 0.5958 | 0.5870 | -0.0087 ±0.0060 | -0.0037 ±0.0025 | 0.672 | 0.685 |
| atp | 587 | 0.6003 | 0.6064 | +0.0061 ±0.0086 | +0.0024 ±0.0035 | 0.673 | 0.683 |
| wta | 588 | 0.5913 | 0.5677 | -0.0236 ±0.0082 | -0.0099 ±0.0034 | 0.672 | 0.687 |
| pooled/live | 334 | 0.5783 | 0.5513 | -0.0270 ±0.0118 | -0.0087 ±0.0051 | 0.704 | 0.717 |
| pooled/backtest | 841 | 0.6027 | 0.6012 | -0.0015 ±0.0069 | -0.0018 ±0.0028 | 0.660 | 0.672 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live | 334 | -0.0270 ±0.0118 | -0.0087 ±0.0051 | -2.3 | 0.704 | 0.717 | |
| pred_source: backtest | 841 | -0.0015 ±0.0069 | -0.0018 ±0.0028 | -0.2 | 0.660 | 0.672 | |
| top-20 involved | 409 | +0.0005 ±0.0085 | +0.0001 ±0.0030 | +0.1 | 0.744 | 0.735 | |
| no top-20 player | 766 | -0.0137 ±0.0079 | -0.0058 ±0.0034 | -1.7 | 0.634 | 0.659 | |
| both inside top-50 | 246 | +0.0165 ±0.0111 | +0.0076 ±0.0049 | +1.5 | 0.685 | 0.657 | |
| someone outside top-50 | 929 | -0.0154 ±0.0069 | -0.0067 ±0.0028 | -2.2 | 0.669 | 0.693 | |
| best rank 1-10 | 236 | +0.0132 ±0.0120 | +0.0044 ±0.0037 | +1.1 | 0.746 | 0.742 | |
| best rank 11-20 | 173 | -0.0168 ±0.0117 | -0.0058 ±0.0050 | -1.4 | 0.743 | 0.725 | |
| best rank 21-50 | 401 | -0.0093 ±0.0094 | -0.0030 ±0.0041 | -1.0 | 0.658 | 0.676 | |
| best rank 51-100 | 305 | -0.0084 ±0.0139 | -0.0043 ±0.0059 | -0.6 | 0.605 | 0.633 | |
| best rank 100+ | 60 | -0.0697 ±0.0362 | -0.0326 ±0.0156 | -1.9 | 0.617 | 0.675 | |
| kalshi favorite 0.5-0.6 | 335 | -0.0171 ±0.0102 | -0.0076 ±0.0048 | -1.7 | 0.515 | 0.558 | |
| kalshi favorite 0.6-0.7 | 325 | -0.0045 ±0.0103 | -0.0019 ±0.0048 | -0.4 | 0.628 | 0.631 | |
| kalshi favorite 0.7-0.8 | 266 | -0.0036 ±0.0114 | -0.0013 ±0.0047 | -0.3 | 0.739 | 0.741 | |
| kalshi favorite 0.8-0.9 | 168 | -0.0033 ±0.0191 | -0.0022 ±0.0071 | -0.2 | 0.833 | 0.833 | |
| kalshi favorite 0.9-1.0 | 81 | -0.0192 ±0.0328 | -0.0061 ±0.0083 | -0.6 | 0.951 | 0.938 | |
| surface: Hard | 3 | +0.0041 ±0.0440 | +0.0090 ±0.0126 | +0.1 | 1.000 | 1.000 | ⚠ small n |
| surface: Clay | 601 | +0.0030 ±0.0080 | -0.0002 ±0.0032 | +0.4 | 0.671 | 0.688 | |
| surface: Grass | 571 | -0.0211 ±0.0090 | -0.0076 ±0.0038 | -2.4 | 0.673 | 0.680 | |
| tier: atp250 | 339 | +0.0014 ±0.0117 | -0.0004 ±0.0050 | +0.1 | 0.649 | 0.673 | |
| tier: atp500 | 181 | -0.0148 ±0.0103 | -0.0071 ±0.0046 | -1.4 | 0.608 | 0.622 | |
| tier: grand_slam | 476 | -0.0187 ±0.0107 | -0.0074 ±0.0042 | -1.8 | 0.711 | 0.720 | |
| tier: masters | 179 | +0.0046 ±0.0116 | +0.0032 ±0.0051 | +0.4 | 0.679 | 0.682 | |
| round early (R128-R64) | 506 | -0.0197 ±0.0101 | -0.0073 ±0.0041 | -1.9 | 0.712 | 0.722 | |
| round late (QF-F) | 138 | -0.0053 ±0.0126 | -0.0027 ±0.0054 | -0.4 | 0.645 | 0.645 | |
| round mid (R32-R16) | 509 | +0.0011 ±0.0087 | -0.0005 ±0.0037 | +0.1 | 0.647 | 0.665 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 493 | +0.0035 ±0.0090 | -0.0001 ±0.0035 | +0.4 | 0.677 | 0.687 | |
| month 2026-06 | 439 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.640 | 0.662 | |
| month 2026-07 | 243 | -0.0047 ±0.0122 | +0.0009 ±0.0053 | -0.4 | 0.720 | 0.724 | |
| agree (<0.05) | 570 | +0.0007 ±0.0031 | -0.0003 ±0.0010 | +0.2 | 0.709 | 0.708 | |
| mild disagree (0.05-0.10) | 359 | -0.0051 ±0.0093 | -0.0030 ±0.0036 | -0.6 | 0.631 | 0.669 | |
| big disagree (>=0.1) | 246 | -0.0358 ±0.0240 | -0.0127 ±0.0103 | -1.5 | 0.648 | 0.657 | |
| tour: atp | 587 | +0.0061 ±0.0086 | +0.0024 ±0.0035 | +0.7 | 0.673 | 0.683 | |
| tour: wta | 588 | -0.0236 ±0.0082 | -0.0099 ±0.0034 | -2.9 | 0.672 | 0.687 | |

When they disagree by >= 0.1: model closer to the outcome in **93/246** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 11 | 0.067 | 0.091 |
| 0.1-0.2 | 63 | 0.155 | 0.111 |
| 0.2-0.3 | 104 | 0.249 | 0.202 |
| 0.3-0.4 | 164 | 0.352 | 0.317 |
| 0.4-0.5 | 203 | 0.450 | 0.488 |
| 0.5-0.6 | 199 | 0.550 | 0.563 |
| 0.6-0.7 | 177 | 0.646 | 0.644 |
| 0.7-0.8 | 147 | 0.749 | 0.735 |
| 0.8-0.9 | 85 | 0.846 | 0.835 |
| 0.9-1.0 | 22 | 0.926 | 0.909 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 32 | 0.062 | 0.062 |
| 0.1-0.2 | 70 | 0.154 | 0.129 |
| 0.2-0.3 | 113 | 0.254 | 0.257 |
| 0.3-0.4 | 148 | 0.353 | 0.345 |
| 0.4-0.5 | 177 | 0.443 | 0.446 |
| 0.5-0.6 | 160 | 0.558 | 0.556 |
| 0.6-0.7 | 175 | 0.649 | 0.617 |
| 0.7-0.8 | 153 | 0.747 | 0.739 |
| 0.8-0.9 | 98 | 0.843 | 0.806 |
| 0.9-1.0 | 49 | 0.939 | 0.939 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| both inside top-50 | 246 | +0.0165 ±0.0111 | +0.0076 ±0.0049 | +1.5 | 0.685 | 0.657 | |
| best rank 1-10 | 236 | +0.0132 ±0.0120 | +0.0044 ±0.0037 | +1.1 | 0.746 | 0.742 | |
| tour: atp | 587 | +0.0061 ±0.0086 | +0.0024 ±0.0035 | +0.7 | 0.673 | 0.683 | |
| tier: masters | 179 | +0.0046 ±0.0116 | +0.0032 ±0.0051 | +0.4 | 0.679 | 0.682 | |
| month 2026-05 | 493 | +0.0035 ±0.0090 | -0.0001 ±0.0035 | +0.4 | 0.677 | 0.687 | |
| surface: Clay | 601 | +0.0030 ±0.0080 | -0.0002 ±0.0032 | +0.4 | 0.671 | 0.688 | |
| agree (<0.05) | 570 | +0.0007 ±0.0031 | -0.0003 ±0.0010 | +0.2 | 0.709 | 0.708 | |
| round mid (R32-R16) | 509 | +0.0011 ±0.0087 | -0.0005 ±0.0037 | +0.1 | 0.647 | 0.665 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| tier: grand_slam | 476 | -0.0187 ±0.0107 | -0.0074 ±0.0042 | -1.8 | 0.711 | 0.720 | |
| best rank 100+ | 60 | -0.0697 ±0.0362 | -0.0326 ±0.0156 | -1.9 | 0.617 | 0.675 | |
| round early (R128-R64) | 506 | -0.0197 ±0.0101 | -0.0073 ±0.0041 | -1.9 | 0.712 | 0.722 | |
| someone outside top-50 | 929 | -0.0154 ±0.0069 | -0.0067 ±0.0028 | -2.2 | 0.669 | 0.693 | |
| pred_source: live | 334 | -0.0270 ±0.0118 | -0.0087 ±0.0051 | -2.3 | 0.704 | 0.717 | |
| surface: Grass | 571 | -0.0211 ±0.0090 | -0.0076 ±0.0038 | -2.4 | 0.673 | 0.680 | |
| month 2026-06 | 439 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.640 | 0.662 | |
| tour: wta | 588 | -0.0236 ±0.0082 | -0.0099 ±0.0034 | -2.9 | 0.672 | 0.687 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1175, mean |Δ|=0.0015, p95=0.0086, >0.05 in 0 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0090 (n=493, >0.05: 0) | 2026-06 p95=0.0085 (n=439, >0.05: 0) | 2026-07 p95=0.0074 (n=243, >0.05: 0)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1175, d_ll -0.0087 ±0.0060 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 350 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'WTA Iasi': 3, 'ATP Hamburg': 1, 'ATP Gstaad': 1, 'ATP Stuttgart': 1, 'ATP Mallorca': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Arantxa Rus, Ashlyn Krueger, Ayana Akli, Bianca Andreescu, Cadence Brace, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Casper Ruud, Celine Naef, Chloe Paquet, Claire Liu, Dalma Galfi, Daphnee Mpetshi Perricard, Darja Semenistaja, Darja Vidmanova, Despina Papamichail, Dominika Salkova, Ekaterine Gorgodze, Eleejah Inisan, Elena Pridankina, Elizabeth Mandlik, Elizara Yaneva, Elsa Jacquemot, Elvina Kalieva
