# Model vs Kalshi — match-by-match scorecard

_Generated 2026-10-28T10:26:11Z. Positive d = model better than Kalshi (paired per-match; SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at 08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own start timestamps mutate on settled markets and cannot be trusted), from 1-min candlesticks; markets with spread > 0.10 excluded. Do not compare these numbers to the closing-line scorecard (market.json): different price time, different match mix. Live model forecasts are the latest saved snapshot at or before that quote; legacy first-sighting-only rows remain in coverage but are excluded from scoring._

## Coverage

| tour | events | matched | pending | unmatched | cancelled | ambiguous | walkovers | retirements | no price | range |
|---|---|---|---|---|---|---|---|---|---|---|
| atp | 2287 | 2188 | 15 | 15 | 69 | 0 | 15 | 27 | 51 | 2026-05-03..2026-10-28 |
| wta | 2435 | 1456 | 24 | 882 | 73 | 0 | 10 | 22 | 34 | 2026-05-02..2026-10-29 |

## Headline (scored set)

| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE | acc model | acc kalshi |
|---|---|---|---|---|---|---|---|
| pooled | 1755 | 0.6090 | 0.5911 | -0.0179 ±0.0051 | -0.0075 ±0.0021 | 0.660 | 0.675 |
| atp | 878 | 0.6199 | 0.6088 | -0.0110 ±0.0069 | -0.0047 ±0.0028 | 0.646 | 0.663 |
| wta | 877 | 0.5980 | 0.5733 | -0.0248 ±0.0075 | -0.0102 ±0.0031 | 0.674 | 0.686 |
| pooled/live_aligned | 818 | 0.6119 | 0.5738 | -0.0381 ±0.0078 | -0.0148 ±0.0033 | 0.661 | 0.685 |
| pooled/backtest | 937 | 0.6064 | 0.6061 | -0.0002 ±0.0067 | -0.0011 ±0.0027 | 0.658 | 0.666 |

## Segments (pooled)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| pred_source: live aligned | 818 | -0.0381 ±0.0078 | -0.0148 ±0.0033 | -4.9 | 0.661 | 0.685 | |
| pred_source: backtest | 937 | -0.0002 ±0.0067 | -0.0011 ±0.0027 | -0.0 | 0.658 | 0.666 | |
| top-20 involved | 627 | +0.0016 ±0.0077 | -0.0005 ±0.0029 | +0.2 | 0.726 | 0.726 | |
| no top-20 player | 1128 | -0.0287 ±0.0067 | -0.0113 ±0.0028 | -4.3 | 0.623 | 0.646 | |
| both inside top-50 | 452 | -0.0149 ±0.0099 | -0.0058 ±0.0042 | -1.5 | 0.643 | 0.647 | |
| someone outside top-50 | 1303 | -0.0190 ±0.0060 | -0.0080 ±0.0024 | -3.2 | 0.666 | 0.685 | |
| best rank 1-10 | 366 | +0.0121 ±0.0100 | +0.0031 ±0.0034 | +1.2 | 0.740 | 0.735 | |
| best rank 11-20 | 261 | -0.0132 ±0.0121 | -0.0057 ±0.0049 | -1.1 | 0.707 | 0.715 | |
| best rank 21-50 | 607 | -0.0304 ±0.0082 | -0.0123 ±0.0035 | -3.7 | 0.654 | 0.695 | |
| best rank 51-100 | 425 | -0.0227 ±0.0113 | -0.0087 ±0.0048 | -2.0 | 0.587 | 0.589 | |
| best rank 100+ | 96 | -0.0446 ±0.0314 | -0.0166 ±0.0134 | -1.4 | 0.583 | 0.589 | |
| kalshi favorite 0.5-0.6 | 495 | -0.0272 ±0.0086 | -0.0126 ±0.0040 | -3.2 | 0.498 | 0.536 | |
| kalshi favorite 0.6-0.7 | 494 | -0.0112 ±0.0088 | -0.0044 ±0.0039 | -1.3 | 0.613 | 0.617 | |
| kalshi favorite 0.7-0.8 | 409 | -0.0100 ±0.0106 | -0.0038 ±0.0043 | -0.9 | 0.735 | 0.743 | |
| kalshi favorite 0.8-0.9 | 237 | -0.0029 ±0.0149 | -0.0019 ±0.0052 | -0.2 | 0.831 | 0.835 | |
| kalshi favorite 0.9-1.0 | 120 | -0.0630 ±0.0289 | -0.0223 ±0.0090 | -2.2 | 0.925 | 0.933 | |
| surface: Hard | 905 | -0.0325 ±0.0075 | -0.0125 ±0.0031 | -4.3 | 0.659 | 0.675 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| surface: Grass | 328 | -0.0090 ±0.0111 | -0.0042 ±0.0048 | -0.8 | 0.640 | 0.655 | |
| tier: atp250 | 647 | -0.0267 ±0.0094 | -0.0106 ±0.0039 | -2.8 | 0.612 | 0.634 | |
| tier: atp500 | 273 | -0.0147 ±0.0114 | -0.0062 ±0.0051 | -1.3 | 0.637 | 0.647 | |
| tier: challenger | 1 | +0.1138 ±0.0000 | +0.0539 ±0.0000 | +0.0 | 1.000 | 1.000 | ⚠ small n |
| tier: grand_slam | 510 | -0.0092 ±0.0091 | -0.0053 ±0.0034 | -1.0 | 0.732 | 0.743 | |
| tier: masters | 324 | -0.0171 ±0.0108 | -0.0058 ±0.0046 | -1.6 | 0.659 | 0.673 | |
| round early (R128-R64) | 646 | -0.0208 ±0.0083 | -0.0085 ±0.0032 | -2.5 | 0.710 | 0.723 | |
| round late (QF-F) | 245 | -0.0024 ±0.0114 | -0.0013 ±0.0051 | -0.2 | 0.641 | 0.637 | |
| round mid (R32-R16) | 842 | -0.0205 ±0.0078 | -0.0087 ±0.0033 | -2.6 | 0.631 | 0.653 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| month 2026-06 | 338 | -0.0071 ±0.0108 | -0.0039 ±0.0046 | -0.7 | 0.630 | 0.648 | |
| month 2026-07 | 27 | -0.0308 ±0.0600 | -0.0055 ±0.0250 | -0.5 | 0.778 | 0.741 | ⚠ small n |
| month 2026-08 | 276 | -0.0103 ±0.0104 | -0.0038 ±0.0044 | -1.0 | 0.627 | 0.621 | |
| month 2026-09 | 320 | -0.0429 ±0.0105 | -0.0177 ±0.0044 | -4.1 | 0.703 | 0.728 | |
| month 2026-10 | 295 | -0.0444 ±0.0168 | -0.0163 ±0.0069 | -2.6 | 0.637 | 0.669 | |
| agree (<0.05) | 929 | -0.0008 ±0.0024 | -0.0007 ±0.0008 | -0.3 | 0.702 | 0.701 | |
| mild disagree (0.05-0.10) | 519 | -0.0090 ±0.0077 | -0.0041 ±0.0030 | -1.2 | 0.637 | 0.656 | |
| big disagree (>=0.1) | 307 | -0.0845 ±0.0248 | -0.0337 ±0.0105 | -3.4 | 0.572 | 0.629 | |
| tour: atp | 878 | -0.0110 ±0.0069 | -0.0047 ±0.0028 | -1.6 | 0.646 | 0.663 | |
| tour: wta | 877 | -0.0248 ±0.0075 | -0.0102 ±0.0031 | -3.3 | 0.674 | 0.686 | |

When they disagree by >= 0.1: model closer to the outcome in **117/307** matches.

## Calibration (A = alphabetical player, outcome-independent)

### Model

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 20 | 0.069 | 0.150 |
| 0.1-0.2 | 111 | 0.152 | 0.189 |
| 0.2-0.3 | 159 | 0.250 | 0.258 |
| 0.3-0.4 | 233 | 0.353 | 0.373 |
| 0.4-0.5 | 298 | 0.451 | 0.483 |
| 0.5-0.6 | 266 | 0.552 | 0.541 |
| 0.6-0.7 | 253 | 0.647 | 0.617 |
| 0.7-0.8 | 210 | 0.751 | 0.781 |
| 0.8-0.9 | 142 | 0.845 | 0.782 |
| 0.9-1.0 | 63 | 0.932 | 0.921 |

### Kalshi

| bin | n | pred | actual |
|---|---|---|---|
| 0.0-0.1 | 45 | 0.058 | 0.089 |
| 0.1-0.2 | 93 | 0.154 | 0.161 |
| 0.2-0.3 | 185 | 0.253 | 0.259 |
| 0.3-0.4 | 228 | 0.353 | 0.399 |
| 0.4-0.5 | 252 | 0.445 | 0.460 |
| 0.5-0.6 | 247 | 0.555 | 0.526 |
| 0.6-0.7 | 262 | 0.649 | 0.637 |
| 0.7-0.8 | 224 | 0.748 | 0.746 |
| 0.8-0.9 | 145 | 0.846 | 0.834 |
| 0.9-1.0 | 74 | 0.933 | 0.946 |

## Where we win / where we lose (by t, n >= 10)

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| best rank 1-10 | 366 | +0.0121 ±0.0100 | +0.0031 ±0.0034 | +1.2 | 0.740 | 0.735 | |
| month 2026-05 | 499 | +0.0030 ±0.0089 | -0.0003 ±0.0035 | +0.3 | 0.677 | 0.688 | |
| surface: Clay | 522 | +0.0019 ±0.0087 | -0.0009 ±0.0034 | +0.2 | 0.674 | 0.687 | |
| top-20 involved | 627 | +0.0016 ±0.0077 | -0.0005 ±0.0029 | +0.2 | 0.726 | 0.726 | |
| pred_source: backtest | 937 | -0.0002 ±0.0067 | -0.0011 ±0.0027 | -0.0 | 0.658 | 0.666 | |
| round other/qual | 22 | -0.0056 ±0.0318 | -0.0022 ±0.0151 | -0.2 | 0.500 | 0.545 | ⚠ small n |
| kalshi favorite 0.8-0.9 | 237 | -0.0029 ±0.0149 | -0.0019 ±0.0052 | -0.2 | 0.831 | 0.835 | |
| round late (QF-F) | 245 | -0.0024 ±0.0114 | -0.0013 ±0.0051 | -0.2 | 0.641 | 0.637 | |

…worst:

| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |
|---|---|---|---|---|---|---|---|
| someone outside top-50 | 1303 | -0.0190 ±0.0060 | -0.0080 ±0.0024 | -3.2 | 0.666 | 0.685 | |
| tour: wta | 877 | -0.0248 ±0.0075 | -0.0102 ±0.0031 | -3.3 | 0.674 | 0.686 | |
| big disagree (>=0.1) | 307 | -0.0845 ±0.0248 | -0.0337 ±0.0105 | -3.4 | 0.572 | 0.629 | |
| best rank 21-50 | 607 | -0.0304 ±0.0082 | -0.0123 ±0.0035 | -3.7 | 0.654 | 0.695 | |
| month 2026-09 | 320 | -0.0429 ±0.0105 | -0.0177 ±0.0044 | -4.1 | 0.703 | 0.728 | |
| no top-20 player | 1128 | -0.0287 ±0.0067 | -0.0113 ±0.0028 | -4.3 | 0.623 | 0.646 | |
| surface: Hard | 905 | -0.0325 ±0.0075 | -0.0125 ±0.0031 | -4.3 | 0.659 | 0.675 | |
| pred_source: live aligned | 818 | -0.0381 ±0.0078 | -0.0148 ±0.0033 | -4.9 | 0.661 | 0.685 | |

## QA / leak sentinel

- T-5 vs T-30 price divergence: n=1755, mean |Δ|=0.0066, p95=0.0124, >0.05 in 49 rows (systemic divergence ⇒ early starts leaking in-play info ⇒ flip LEAD_MIN to 30).
- T-5 vs T-30 by month (a month-local p95 spike = in-play prints the pooled stats hide): 2026-05 p95=0.0091 (n=499, >0.05: 1) | 2026-06 p95=0.0087 (n=338, >0.05: 0) | 2026-07 p95=0.0088 (n=27, >0.05: 0) | 2026-08 p95=0.0086 (n=276, >0.05: 1) | 2026-09 p95=0.0660 (n=320, >0.05: 19) | 2026-10 p95=0.1407 (n=295, >0.05: 28)
- Scored quotes stamped after their 08:00 anchor: 0 (must be 0 — requoter + health gate enforce; >0 means the pending-race freeze escaped again).
- Our winner vs Kalshi settlement disagreements: 0 (join bugs surface here; these rows are auto-healed, so a persistent nonzero means healing failed).
- Sensitivity incl. retirements: n=1763, d_ll -0.0180 ±0.0051
- Unmatched qualifying markets: 684 (structural — no qualifying results source for that tour/era).
- Unmatched by event (clusters = structural gaps, singletons = alias candidates): {'French Open': 65, 'US Open': 57, 'Billie Jean King Cup Qualifiers Round': 56, 'WTA Memphis': 9, 'WTA Washington': 8, 'WTA Hamburg': 6, 'WTA Iasi': 5, 'ATP Los Cabos': 1}
- Unmatched Kalshi names, main draw (40): AYNUR MOVLYAMOVA, Aishath Karin Saizan, Akasha Urhobo, Aleksandr Shevchenko, Alexander Bublik, Alexandra Eala, Alexandra Shubladze, Aliaksandra Sasnovich, Alice Rame, Alice Tubello, Alina Charaeva, Alina Korneeva, Aliona Falei, Amandine Monnot, Ana Sofia Sanchez, Anastasia Gasanova, Anastasiia Sobolieva, Andrea Lazaro Garcia, Angela Fita Boluda, Anhelina Kalinina, Ankita Raina, Anna Abualhaj, Anna Frey, Anna Siskova, Anna-Lena Friedsam, Annika Penickova, Anouk Koevermans, Aoi Ito, Aran Teixido Garcia, Arantxa Rus, Ashlyn Krueger, Astra Sharma, Ayana Akli, Aylara Kakabayeva, Bella Payne, Bianca Andreescu, Cadence Brace, Camila Soares, Carol Young Suh Lee, Carol Zhao
