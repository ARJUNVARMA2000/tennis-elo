# Historical signal round — a WTA candidate passes the historical gate

Completed numerical verification **2026-09-08T16:11:42.753152+00:00**. This is a new bounded round,
authorized by the user's request to try more mechanisms. The earlier absence/cap trials
remain closed; their failures did not exhaust model research.

**Decision:** advance the fixed WTA recent-surface-history candidate to saved-predictor
implementation and serving assessment. Keep the corrected 42-column incumbent artifact
as the reference until that implementation is accepted. No production model was changed.
ATP fails its own historical gate; ranking trend is a tune-qualified, unvalidated runner-up.

## What we tried, what improved, and what failed

Positive ΔLL means lower loss than the incumbent. ± values are one paired match SE,
not 95% confidence intervals. All three WTA trials used the same **26,794** tuning matches
from 2010–2019, annual expanding folds, five bags, prior-season Platt calibration and
threshold32 state selection. Each independently added one antisymmetric feature.

| Experiment | Tune ΔLL ± SE | Tune accuracy change | Positive tune years | Result |
|---|---:|---:|---:|---|
| Opponent-adjusted recent form | +0.000230527 ± 0.000114560 | −0.0261pp | 5/10 | Fails fixed yearly-consistency rule; no validation |
| Recent current-surface experience | **+0.000697431 ± 0.000208347** | −0.0187pp | **8/10** | Selected; **passes WTA historical arbiter** |
| Ranking-points trajectory | +0.000392500 ± 0.000121949 | −0.0448pp | 8/10 | Qualified runner-up; lower tune gain, no validation |

All three improved pooled tune log loss and Brier score. None improved pooled tune
winner-pick accuracy. These are probability-quality experiments; the net tune accuracy
changes were −7, −5 and −12 correct predictions respectively. The first candidate's
positive average does not override its failed preregistered year check.

Selection required positive pooled ΔLL, at least six positive years, and positive
2010–14 and 2015–19 halves. Largest qualifying gain wins. Surface gained +0.000573485
and +0.000822474 in the two halves. Ranking trend gained +0.000478442 and +0.000305798.
The surface choice was recorded before any new candidate validation was viewed.
No combination, alternative window or runner-up validation was tried.

## Locked finalist on later years

| Tour / window | Matches | Incumbent LL | Candidate LL | ΔLL ± SE | Accuracy change | Decision |
|---|---:|---:|---:|---:|---:|---|
| WTA, 2020 onward | 15,628 | 0.597198487 | 0.596665727 | **+0.000532760 ± 0.000311990** | +0.0256pp | Historical gate passes |
| ATP, 2010–2019 | 28,357 | 0.562589486 | 0.562637187 | −0.000047701 ± 0.000267304 | −0.0282pp | Tune gate fails |
| ATP, 2020 onward | 17,838 | 0.592020595 | 0.591562951 | +0.000457643 ± 0.000265613 | −0.0392pp | Cannot override failed ATP tune gate |

WTA later-year gains occur in **5/7** years: 2021 and 2023–2026. The 2026 season is
partial. Validation accuracy changes from 67.3727% to 67.3983% (four net extra correct);
Brier improves from 0.206109726 to 0.205891698. Across the full 42,422 WTA rows,
ΔLL is +0.000636767 ± 0.000174718; full-window accuracy is essentially unchanged
(−0.0024pp). The full window includes the tuning sample and is not independent confirmation.

WTA's validation **95% week-block bootstrap interval is [−0.000132157, +0.001177076]**.
It includes zero: the positive result passes the existing gate, but does not establish
a large or certain improvement. The formal unchanged gate is tune ΔLL > 0 and
validation ΔLL > −validation naive SE. WTA tune week95 is [+0.000255384, +0.001140870].
Form's tune week95 is approximately [−0.000000341, +0.000469166]; ranking trend's is
[+0.000135582, +0.000650957]. All use 2,000 fixed-seed bootstrap replicates.

Validation event-block uncertainty is unavailable because event identity is missing
on some retained rows; no synthetic event IDs were substituted. Week blocks do not
eliminate repeated-player dependence or repeated-search selection effects. Later years
have previous research exposure and are validation, not an untouched holdout.

## Error evidence and novelty

Before any candidate fit, three fixed histories were checked against saved tune residuals:
recent form had a same-sign residual association in 6/10 years, recent surface experience
9/10, and ranking trend 7/10. Nonzero coverage was 26,209 / 20,971 / 23,564 matches.
Those diagnostic associations motivated experiments; they were not performance claims.
The [registered shortlist](2026-09-08-historical-signal-shortlist.md) contains definitions,
thresholds and comparisons with earlier rejected mechanisms.

The surface feature is `log1p(A completed matches on today's surface in the preceding
60 days) − log1p(B count)`. It adds recent exposure history, distinct from the rejected
career surface-count confidence gate. It is mirrored in a serialized, read-only query
state and follows the incumbent's pre-row retrospective chronology, including earlier
ordered rows on a shared recorded date. That chronology does not prove live availability.

## Implementation and verification

Source and tests were frozen at **755342d**, based on accepted historical-errors
**c658c71**. Later ledger commits through **fd33d89** contain results only. New external
modules are `tennis_model/research/historical_signals.py` and `signal_combiner.py`, with
`tests/test_historical_signals.py`. No production feature/config/evaluator file changed.

- **74 focused tests passed in 1.14s**, including **17 new**; lint passed. No full-suite claim.
- Six fresh real-prefix serialized queries matched exactly, across both WTA state routes
  and cutoffs 2009/2015/2018. The selected-state mapping was independently checked.
- The adapter with no added feature reproduced every incumbent tuning probability
  bit-for-bit. The later-year surface run also reproduced its selected tune predictions exactly.
- All **696** earlier run files, both saved reference models and sixteen accepted
  checkouts were preserved; **388** inherited program/web/workflow files were unchanged.
- **37** new retained run files make **733** for the next preservation check. Frozen
  input files were read in place; a new derived feature/state cache is retained.
- Large external inventories were last fully checked at 2026-09-08 01:58:44 UTC,
  not rehashed in this round. No acquisition, dependency change, live collection or deployment.

A diagnostic JSON write initially failed on a NumPy integer after the CSV/cache/parity
work completed. The partial JSON is retained, and the valid summary was recovered from
that completed CSV without altering definitions. A fresh explicit parity receipt then
passed before model trials. This was an output-serialization failure, not a model result.

Read the [comparison CSV](2026-09-08-historical-signal-comparison.csv),
[year table](2026-09-08-historical-signal-years.csv),
[diagnostics](2026-09-08-historical-signal-diagnostics.csv),
[manifest](2026-09-08-historical-signal-result.json) and
[exact next implementation steps](2026-09-08-historical-signal-next.md).
