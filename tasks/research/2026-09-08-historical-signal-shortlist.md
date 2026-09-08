# Historical signal round — registered shortlist

2026-09-08. User authorized further historical predictive experiments. Three candidates
meet the fixed diagnostic coverage/sign-consistency rule, one setting each, independently
against the corrected 42-column WTA incumbent. Selection never uses new 2020+ scores.

| ID | New history | Nonzero tune rows | Residual-moment sign consistent years |
|---|---|---:|---:|
| SIGNAL-01 | Last 10 completed results within 90 days, adjusted for pre-match Elo probability; sum residual / (5+n) | 26,209 | 6/10 |
| SIGNAL-02 | log1p current-surface completed matches within 60 days, player difference | 20,971 | 9/10 |
| SIGNAL-03 | Change in log ranking points vs latest valid observed snapshot 90–365 days old, player difference; missing pair neutral | 23,564 | 7/10 |

Moment E[x*(y-p)] and naive SE: form 0.0003402 ± 0.0003518; surface 0.0103860 ±
0.0020217; ranking trend 0.0036123 ± 0.0013369. Units differ, so these are diagnostic
associations, not comparable effect sizes or model-performance gains. Form is weak.
The surface association is the clearest. All are exploratory, reused tune data.

Novelty: form tracks past opponent-adjusted outcome surprises, distinct from the existing
raw win fraction and K/margin-weighted Elo movement and the discarded serve-skill trend.
Recent surface exposure is a time-window history, not the rejected career-surface-count
confidence gate or adaptive surface Elo blend. Ranking trajectory uses historical points,
not the rejected current ordinal rank. These introduce state rather than algebraically
recombining current feature columns. No earlier closed grid is reopened.

Pre-row emission follows the incumbent retrospective chronology, including earlier
ordered rows sharing a recorded date. It does not establish physical match-time
availability. A query mirror accepts explicit pre-match ranking metadata and rejects
backdated state queries. No production predictor is integrated in this experiment.

Trial protocol: 43 columns per candidate, otherwise identical main fitting population,
threshold32 selected state, five bags, annual expanding folds and previous-season Platt
calibration. First run the new adapter with zero extra columns and require bit-identical
incumbent tune probabilities. Preserve state/query/orientation/parity tests before fits.
Choose at most one candidate with positive pooled tune gain, at least 6/10 positive years,
and positive gains in both 2010–14 and 2015–19. Largest gain wins; exact tie fixed ID order.
Run only that finalist through the frozen full arbiter. ATP evaluated separately if WTA
survives. No combined feature model or adaptive variant within this round.

Diagnostic execution note: the first JSON summary write failed on a NumPy integer after
the complete CSV, prepared data and six real-prefix checks were produced. The partial
JSON is retained; the valid summary was recovered from that CSV without changing any
signal definition. A fresh explicit parity receipt is required before experiments.
