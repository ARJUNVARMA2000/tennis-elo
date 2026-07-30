# Model vs Kalshi — match-by-match scorecard

_Generated 2026-07-30T07:00:30Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1237 | 1176 | 13 | 6 | 42 | 0 | 8 | 14 | 42 | 2026-05-03..2026-07-31 |
| wta | 1245 | 718 | 9 | 486 | 32 | 0 | 3 | 15 | 19 | 2026-05-02..2026-07-30 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1352 | 0.6025 | 0.5929 | -0.0096 ±0.0058 | -0.0041 ±0.0024 | 0.667 | 0.683 |
| atp | 672 | 0.6044 | 0.6140 | +0.0096 ±0.0082 | +0.0037 ±0.0033 | 0.668 | 0.680 |
| wta | 680 | 0.6006 | 0.5721 | -0.0286 ±0.0081 | -0.0119 ±0.0034 | 0.666 | 0.687 |
| pooled/live | 491 | 0.6042 | 0.5816 | -0.0226 ±0.0102 | -0.0081 ±0.0043 | 0.674 | 0.698 |
| pooled/backtest | 861 | 0.6015 | 0.5994 | -0.0022 ±0.0069 | -0.0019 ±0.0028 | 0.663 | 0.675 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live | 491 | -0.0226 ±0.0102 | -0.0081 ±0.0043 | -2.2 | 0.674 | 0.698 | |
| pred_source: backtest | 861 | -0.0022 ±0.0069 | -0.0019 ±0.0028 | -0.3 | 0.663 | 0.675 | |
| top-20 involved | 433 | +0.0005 ±0.0088 | +0.0000 ±0.0031 | +0.1 | 0.740 | 0.736 | |
| no top-20 player | 919 | -0.0143 ±0.0074 | -0.0061 ±0.0032 | -1.9 | 0.633 | 0.659 | |
| both inside top-50 | 269 | +0.0169 ±0.0107 | +0.0075 ±0.0047 | +1.6 | 0.671 | 0.660 | |
| someone outside top-50 | 1083 | -0.0161 ±0.0067 | -0.0070 ±0.0027 | -2.4 | 0.666 | 0.689 | |
| best rank 1-10 | 241 | +0.0132 ±0.0117 | +0.0046 ±0.0036 | +1.1 | 0.751 | 0.747 | |
| best rank 11-20 | 192 | -0.0155 ±0.0132 | -0.0057 ±0.0054 | -1.2 | 0.727 | 0.721 | |
| best rank 21-50 | 468 | -0.0074 ±0.0085 | -0.0021 ±0.0037 | -0.9 | 0.652 | 0.669 | |
| best rank 51-100 | 373 | -0.0083 ±0.0125 | -0.0046 ±0.0053 | -0.7 | 0.615 | 0.641 | |
| best rank 100+ | 78 | -0.0845 ±0.0371 | -0.0376 ±0.0157 | -2.3 | 0.603 | 0.686 | |
| kalshi favorite 0.5-0.6 | 382 | -0.0240 ±0.0103 | -0.0107 ±0.0048 | -2.3 | 0.514 | 0.571 | |
| kalshi favorite 0.6-0.7 | 393 | -0.0033 ±0.0098 | -0.0012 ±0.0045 | -0.3 | 0.621 | 0.623 | |
| kalshi favorite 0.7-0.8 | 304 | -0.0017 ±0.0110 | -0.0008 ±0.0044 | -0.2 | 0.742 | 0.743 | |
| kalshi favorite 0.8-0.9 | 190 | -0.0016 ±0.0188 | -0.0014 ±0.0068 | -0.1 | 0.826 | 0.826 | |
| kalshi favorite 0.9-1.0 | 83 | -0.0198 ±0.0320 | -0.0063 ±0.0081 | -0.6 | 0.952 | 0.940 | |
| surface: Hard | 72 | -0.0290 ±0.0406 | -0.0129 ±0.0162 | -0.7 | 0.597 | 0.639 | |
| surface: Clay | 695 | +0.0022 ±0.0073 | -0.0003 ±0.0029 | +0.3 | 0.669 | 0.690 | |
| surface: Grass | 585 | -0.0212 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.681 | |
| tier: atp250 | 509 | -0.0041 ±0.0103 | -0.0026 ±0.0043 | -0.4 | 0.642 | 0.670 | |
| tier: atp500 | 184 | -0.0139 ±0.0102 | -0.0067 ±0.0046 | -1.4 | 0.614 | 0.628 | |
| tier: grand_slam | 476 | -0.0187 ±0.0107 | -0.0074 ±0.0042 | -1.8 | 0.711 | 0.720 | |
| tier: masters | 183 | +0.0032 ±0.0114 | +0.0026 ±0.0051 | +0.3 | 0.675 | 0.683 | |
| round early (R128-R64) | 509 | -0.0196 ±0.0101 | -0.0072 ±0.0040 | -1.9 | 0.712 | 0.722 | |
| round late (QF-F) | 175 | -0.0007 ±0.0117 | -0.0014 ±0.0050 | -0.1 | 0.634 | 0.640 | |
| round mid (R32-R16) | 646 | -0.0042 ±0.0085 | -0.0025 ±0.0035 | -0.5 | 0.646 | 0.670 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 439 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.640 | 0.662 | |
| month 2026-07 | 414 | -0.0086 ±0.0110 | -0.0021 ±0.0046 | -0.8 | 0.684 | 0.700 | |
| agree (<0.05) | 639 | +0.0017 ±0.0029 | +0.0001 ±0.0009 | +0.6 | 0.696 | 0.700 | |
| mild disagree (0.05-0.10) | 417 | -0.0040 ±0.0087 | -0.0025 ±0.0033 | -0.5 | 0.644 | 0.671 | |
| big disagree (>=0.1) | 296 | -0.0418 ±0.0225 | -0.0157 ±0.0096 | -1.9 | 0.637 | 0.664 | |
| tour: atp | 672 | +0.0096 ±0.0082 | +0.0037 ±0.0033 | +1.2 | 0.668 | 0.680 | |
| tour: wta | 680 | -0.0286 ±0.0081 | -0.0119 ±0.0034 | -3.5 | 0.666 | 0.687 | |

When they disagree by >= 0.1: model closer to the outcome in **113/296** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 12 | 0.067 | 0.083 |
| 0.1-0.2 | 76 | 0.157 | 0.132 |
| 0.2-0.3 | 122 | 0.251 | 0.205 |
| 0.3-0.4 | 193 | 0.352 | 0.337 |
| 0.4-0.5 | 230 | 0.449 | 0.483 |
| 0.5-0.6 | 222 | 0.550 | 0.572 |
| 0.6-0.7 | 208 | 0.645 | 0.620 |
| 0.7-0.8 | 169 | 0.747 | 0.734 |
| 0.8-0.9 | 96 | 0.844 | 0.833 |
| 0.9-1.0 | 24 | 0.927 | 0.875 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 32 | 0.062 | 0.062 |
| 0.1-0.2 | 81 | 0.152 | 0.123 |
| 0.2-0.3 | 134 | 0.253 | 0.254 |
| 0.3-0.4 | 178 | 0.352 | 0.365 |
| 0.4-0.5 | 200 | 0.442 | 0.430 |
| 0.5-0.6 | 184 | 0.558 | 0.565 |
| 0.6-0.7 | 213 | 0.650 | 0.620 |
| 0.7-0.8 | 170 | 0.747 | 0.741 |
| 0.8-0.9 | 109 | 0.844 | 0.789 |
| 0.9-1.0 | 51 | 0.938 | 0.941 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| both inside top-50 | 269 | +0.0169 ±0.0107 | +0.0075 ±0.0047 | +1.6 | 0.671 | 0.660 | |
| tour: atp | 672 | +0.0096 ±0.0082 | +0.0037 ±0.0033 | +1.2 | 0.668 | 0.680 | |
| best rank 1-10 | 241 | +0.0132 ±0.0117 | +0.0046 ±0.0036 | +1.1 | 0.751 | 0.747 | |
| agree (<0.05) | 639 | +0.0017 ±0.0029 | +0.0001 ±0.0009 | +0.6 | 0.696 | 0.700 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 695 | +0.0022 ±0.0073 | -0.0003 ±0.0029 | +0.3 | 0.669 | 0.690 | |
| tier: masters | 183 | +0.0032 ±0.0114 | +0.0026 ±0.0051 | +0.3 | 0.675 | 0.683 | |
| top-20 involved | 433 | +0.0005 ±0.0088 | +0.0000 ±0.0031 | +0.1 | 0.740 | 0.736 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| round early (R128-R64) | 509 | -0.0196 ±0.0101 | -0.0072 ±0.0040 | -1.9 | 0.712 | 0.722 | |
| pred_source: live | 491 | -0.0226 ±0.0102 | -0.0081 ±0.0043 | -2.2 | 0.674 | 0.698 | |
| best rank 100+ | 78 | -0.0845 ±0.0371 | -0.0376 ±0.0157 | -2.3 | 0.603 | 0.686 | |
| kalshi favorite 0.5-0.6 | 382 | -0.0240 ±0.0103 | -0.0107 ±0.0048 | -2.3 | 0.514 | 0.571 | |
| month 2026-06 | 439 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.640 | 0.662 | |
| surface: Grass | 585 | -0.0212 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.681 | |
| someone outside top-50 | 1083 | -0.0161 ±0.0067 | -0.0070 ±0.0027 | -2.4 | 0.666 | 0.689 | |
| tour: wta | 680 | -0.0286 ±0.0081 | -0.0119 ±0.0034 | -3.5 | 0.666 | 0.687 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1352, mean |Δ|=0.0017, p95=0.0086, >0.05 in 2 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0085 (n=439, >0.05: 0) | 2026-07 p95=0.0079 (n=414, >0.05: 1)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1352, d_ll -0.0096 ±0.0058 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 397 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'WTA Memphis': 7, 'WTA Washington': 7, 'WTA Hamburg': 6, 'WTA Iasi': 6, 'ATP Hamburg': 1, 'ATP Stuttgart': 1, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Carolyn Ansari, Casper Ruud, Celine Naef, Chloe Paquet, Claire Liu, Clervie Ngounoue, Dalma Galfi, Daphnee Mpetshi Perricard, Daria Kasatkina, Darja Semenistaja
