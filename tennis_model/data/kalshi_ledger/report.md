# Model vs Kalshi — match-by-match scorecard

_Generated 2026-07-31T07:31:47Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 1244 | 1189 | 6 | 7 | 42 | 0 | 8 | 14 | 42 | 2026-05-03..2026-08-01 |
| wta | 1253 | 725 | 9 | 487 | 32 | 0 | 3 | 15 | 22 | 2026-05-02..2026-08-01 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1365 | 0.6020 | 0.5924 | -0.0096 ±0.0057 | -0.0042 ±0.0024 | 0.668 | 0.684 |
| atp | 679 | 0.6046 | 0.6141 | +0.0095 ±0.0081 | +0.0036 ±0.0033 | 0.669 | 0.679 |
| wta | 686 | 0.5995 | 0.5709 | -0.0286 ±0.0081 | -0.0119 ±0.0034 | 0.668 | 0.688 |
| pooled/live | 504 | 0.6029 | 0.5805 | -0.0224 ±0.0100 | -0.0081 ±0.0042 | 0.677 | 0.697 |
| pooled/backtest | 861 | 0.6015 | 0.5994 | -0.0022 ±0.0069 | -0.0019 ±0.0028 | 0.663 | 0.675 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live | 504 | -0.0224 ±0.0100 | -0.0081 ±0.0042 | -2.2 | 0.677 | 0.697 | |
| pred_source: backtest | 861 | -0.0022 ±0.0069 | -0.0019 ±0.0028 | -0.3 | 0.663 | 0.675 | |
| top-20 involved | 440 | +0.0006 ±0.0086 | -0.0000 ±0.0031 | +0.1 | 0.742 | 0.738 | |
| no top-20 player | 925 | -0.0145 ±0.0074 | -0.0062 ±0.0032 | -2.0 | 0.633 | 0.658 | |
| both inside top-50 | 275 | +0.0167 ±0.0105 | +0.0075 ±0.0046 | +1.6 | 0.675 | 0.660 | |
| someone outside top-50 | 1090 | -0.0163 ±0.0067 | -0.0071 ±0.0027 | -2.4 | 0.667 | 0.689 | |
| best rank 1-10 | 245 | +0.0134 ±0.0116 | +0.0045 ±0.0035 | +1.2 | 0.755 | 0.751 | |
| best rank 11-20 | 195 | -0.0155 ±0.0130 | -0.0057 ±0.0053 | -1.2 | 0.726 | 0.721 | |
| best rank 21-50 | 471 | -0.0075 ±0.0085 | -0.0021 ±0.0037 | -0.9 | 0.652 | 0.667 | |
| best rank 51-100 | 376 | -0.0087 ±0.0125 | -0.0048 ±0.0053 | -0.7 | 0.616 | 0.641 | |
| best rank 100+ | 78 | -0.0845 ±0.0371 | -0.0376 ±0.0157 | -2.3 | 0.603 | 0.686 | |
| kalshi favorite 0.5-0.6 | 387 | -0.0241 ±0.0103 | -0.0108 ±0.0047 | -2.4 | 0.516 | 0.568 | |
| kalshi favorite 0.6-0.7 | 395 | -0.0031 ±0.0097 | -0.0011 ±0.0045 | -0.3 | 0.623 | 0.625 | |
| kalshi favorite 0.7-0.8 | 307 | -0.0026 ±0.0109 | -0.0011 ±0.0044 | -0.2 | 0.741 | 0.743 | |
| kalshi favorite 0.8-0.9 | 193 | -0.0008 ±0.0185 | -0.0013 ±0.0067 | -0.0 | 0.829 | 0.829 | |
| kalshi favorite 0.9-1.0 | 83 | -0.0198 ±0.0320 | -0.0063 ±0.0081 | -0.6 | 0.952 | 0.940 | |
| surface: Hard | 85 | -0.0271 ±0.0351 | -0.0123 ±0.0141 | -0.8 | 0.624 | 0.647 | |
| surface: Clay | 695 | +0.0022 ±0.0073 | -0.0003 ±0.0029 | +0.3 | 0.669 | 0.690 | |
| surface: Grass | 585 | -0.0212 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.681 | |
| tier: atp250 | 522 | -0.0044 ±0.0101 | -0.0027 ±0.0042 | -0.4 | 0.646 | 0.670 | |
| tier: atp500 | 184 | -0.0139 ±0.0102 | -0.0067 ±0.0046 | -1.4 | 0.614 | 0.628 | |
| tier: grand_slam | 476 | -0.0187 ±0.0107 | -0.0074 ±0.0042 | -1.8 | 0.711 | 0.720 | |
| tier: masters | 183 | +0.0032 ±0.0114 | +0.0026 ±0.0051 | +0.3 | 0.675 | 0.683 | |
| round early (R128-R64) | 509 | -0.0196 ±0.0101 | -0.0072 ±0.0040 | -1.9 | 0.712 | 0.722 | |
| round late (QF-F) | 175 | -0.0007 ±0.0117 | -0.0014 ±0.0050 | -0.1 | 0.634 | 0.640 | |
| round mid (R32-R16) | 659 | -0.0045 ±0.0084 | -0.0026 ±0.0035 | -0.5 | 0.649 | 0.670 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 439 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.640 | 0.662 | |
| month 2026-07 | 427 | -0.0089 ±0.0107 | -0.0023 ±0.0045 | -0.8 | 0.686 | 0.700 | |
| agree (<0.05) | 646 | +0.0014 ±0.0028 | -0.0000 ±0.0009 | +0.5 | 0.697 | 0.700 | |
| mild disagree (0.05-0.10) | 421 | -0.0033 ±0.0086 | -0.0022 ±0.0033 | -0.4 | 0.647 | 0.672 | |
| big disagree (>=0.1) | 298 | -0.0426 ±0.0224 | -0.0161 ±0.0095 | -1.9 | 0.636 | 0.663 | |
| tour: atp | 679 | +0.0095 ±0.0081 | +0.0036 ±0.0033 | +1.2 | 0.669 | 0.679 | |
| tour: wta | 686 | -0.0286 ±0.0081 | -0.0119 ±0.0034 | -3.5 | 0.668 | 0.688 | |

When they disagree by >= 0.1: model closer to the outcome in **114/298** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 12 | 0.067 | 0.083 |
| 0.1-0.2 | 77 | 0.158 | 0.143 |
| 0.2-0.3 | 123 | 0.251 | 0.211 |
| 0.3-0.4 | 193 | 0.352 | 0.337 |
| 0.4-0.5 | 232 | 0.449 | 0.483 |
| 0.5-0.6 | 224 | 0.550 | 0.576 |
| 0.6-0.7 | 210 | 0.645 | 0.624 |
| 0.7-0.8 | 171 | 0.747 | 0.737 |
| 0.8-0.9 | 97 | 0.844 | 0.835 |
| 0.9-1.0 | 26 | 0.927 | 0.885 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 32 | 0.062 | 0.062 |
| 0.1-0.2 | 81 | 0.152 | 0.123 |
| 0.2-0.3 | 135 | 0.253 | 0.259 |
| 0.3-0.4 | 178 | 0.352 | 0.365 |
| 0.4-0.5 | 204 | 0.442 | 0.436 |
| 0.5-0.6 | 185 | 0.558 | 0.568 |
| 0.6-0.7 | 215 | 0.650 | 0.623 |
| 0.7-0.8 | 172 | 0.746 | 0.744 |
| 0.8-0.9 | 112 | 0.844 | 0.795 |
| 0.9-1.0 | 51 | 0.938 | 0.941 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| both inside top-50 | 275 | +0.0167 ±0.0105 | +0.0075 ±0.0046 | +1.6 | 0.675 | 0.660 | |
| tour: atp | 679 | +0.0095 ±0.0081 | +0.0036 ±0.0033 | +1.2 | 0.669 | 0.679 | |
| best rank 1-10 | 245 | +0.0134 ±0.0116 | +0.0045 ±0.0035 | +1.2 | 0.755 | 0.751 | |
| agree (<0.05) | 646 | +0.0014 ±0.0028 | -0.0000 ±0.0009 | +0.5 | 0.697 | 0.700 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 695 | +0.0022 ±0.0073 | -0.0003 ±0.0029 | +0.3 | 0.669 | 0.690 | |
| tier: masters | 183 | +0.0032 ±0.0114 | +0.0026 ±0.0051 | +0.3 | 0.675 | 0.683 | |
| top-20 involved | 440 | +0.0006 ±0.0086 | -0.0000 ±0.0031 | +0.1 | 0.742 | 0.738 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| no top-20 player | 925 | -0.0145 ±0.0074 | -0.0062 ±0.0032 | -2.0 | 0.633 | 0.658 | |
| pred_source: live | 504 | -0.0224 ±0.0100 | -0.0081 ±0.0042 | -2.2 | 0.677 | 0.697 | |
| best rank 100+ | 78 | -0.0845 ±0.0371 | -0.0376 ±0.0157 | -2.3 | 0.603 | 0.686 | |
| kalshi favorite 0.5-0.6 | 387 | -0.0241 ±0.0103 | -0.0108 ±0.0047 | -2.4 | 0.516 | 0.568 | |
| month 2026-06 | 439 | -0.0247 ±0.0103 | -0.0105 ±0.0044 | -2.4 | 0.640 | 0.662 | |
| surface: Grass | 585 | -0.0212 ±0.0088 | -0.0077 ±0.0038 | -2.4 | 0.674 | 0.681 | |
| someone outside top-50 | 1090 | -0.0163 ±0.0067 | -0.0071 ±0.0027 | -2.4 | 0.667 | 0.689 | |
| tour: wta | 686 | -0.0286 ±0.0081 | -0.0119 ±0.0034 | -3.5 | 0.668 | 0.688 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1365, mean |Δ|=0.0017, p95=0.0086, >0.05 in 2 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0085 (n=439, >0.05: 0) | 2026-07 p95=0.0079 (n=427, >0.05: 1)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1365, d_ll -0.0096 ±0.0057 — vacuous by construction: matched retired rows never carry p_model (the backtest OOS frame is completed-only), so this can equal the headline; it detects nothing until a live-forecast retirement lands.
- Unmatched qualifying markets: 397 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'WTA Memphis': 8, 'WTA Washington': 7, 'WTA Iasi': 6, 'WTA Hamburg': 6, 'ATP Hamburg': 1, 'ATP Los Cabos': 1, 'ATP Washington': 1}
- Unmatched Kalshi names, main draw (40): Abdullah Shelbayh, Alexander Shevchenko, Aliaksandra Sasnovich, Alice Rame, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Andrea Lazaro Garcia, Anhelina Kalinina, Ankita Raina, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao, Carole Monnet, Carolyn Ansari, Casper Ruud, Celine Naef, Chloe Paquet, Claire Liu, Clervie Ngounoue, Dalma Galfi, Daphnee Mpetshi Perricard, Daria Kasatkina, Darja Semenistaja
