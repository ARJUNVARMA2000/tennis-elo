# ATP recent form and odds-source repair — November 15–16, 2026

The user approved implementation, historical research and deployment. Release checks
and production observations are appended below when complete.

The bounded ATP round selected `recent_surprise_diff`: for each player, sum the
pre-match Elo outcome residuals of their last ten completed matches within 90 days,
divide by `5 + n`, then take the difference. Every row is emitted before its result
updates state. The feature uses the existing adopted ATP lower-tier history.

| Candidate | Tune d ± SE, log loss | Stability | Decision |
| --- | --- | --- | --- |
| ATP-RESIDUAL-90 | +0.0001838 ± 0.0000865 | Both halves positive; 9/10 positive years | Selected |
| ATP-RANK-TRAJECTORY | +0.0000769 ± 0.0000730 | First half negative | Rejected before validation |

Positive d means the candidate has lower paired log loss. Selection used only
2010–19; `selection.json` froze the finalist before viewing its 2020+ results.
The full five-seed production arbiter paired all 46,684 decisions: tuning n=28,357,
validation n=18,327, validation **+0.0001624 ± 0.0001034 SE**. This passes the existing
`d_tune > 0 && d_val > -SE` gate. Per-year and block uncertainty, including negative
2022 performance and intervals spanning zero, remain in `arbiter-result.json`.
The effect is modest and does not demonstrate future live drift recovery.

Production now uses 43 features/schema6 for ATP, with strict saved-state policy
validation and inference parity tests. The WTA feature contract is unchanged.
`production-parity.json` confirms all 42 common features plus the new signal are
bit-identical to the evaluated frame over 153,990 main-history rows. Saved-prefix
queries and resumed walks also match exactly at three historical cutoffs. NumPy
scalar accumulation preserves the evaluated arithmetic across Python versions.

`audit_drift.py` replays immutable first sightings against a frozen current result
frame and reports confidence, surface, tier, horizon, year and predictor-cohort slices.
Tier is reconstructed from unambiguous result date/player-pair/event identity;
result dates are not independent first-serve timing evidence. The source refresh differs from the prior deployment;
this is a diagnostic replay rather than a claim to reproduce its exact 647 rows.
A demonstrated bug allowed a forecast with a known ESPN event ID to settle against
a result from a different known event. The grader now leaves such rows pending and
publishes event-identity proof checked by the pre-upload gate. No forecasts, losses,
model versions or monitor thresholds are rewritten to obtain recovery.

Odds recovery adds the [Valuebetennis CC BY 4.0 seasonal data](https://www.valuebetennis.com/en/donnees.htm)
as an explicitly attributed, evaluation-only Pinnacle supplement. Source documentation
defines the quotes as the last recorded before the match; it does not guarantee
equivalence to other providers' closing snapshots. Intake excludes qualifying,
lower categories, invalid outcomes/prices and ambiguous identities. Exact canonical
full names, date and surface corroborate joins; legacy valid quotes retain priority.
Content-addressed acquisition and a final atomic receipt preserve the last good
generation on failure. Both receipt and source bytes bind stage provenance. Raw odds
are already covered by the release recovery archive. Public output/UI carry credit
and the provider census. Staleness thresholds remain unchanged.

## Reproduction and retained evidence

Registrations, the frozen selection, reference identity, full arbiter and production
parity receipts are committed here. `tools/*.py.txt` retain the exact executed
research drivers (including their input hashes and original local paths), rather
than silently rewriting them after the experiment. Copy them back to `.py` at the
registered paths to replay. The original isolated runtime used the 42-feature model
code from commit `3979e33`; use that reference checkout and pinned requirements for
the historical comparison. `production_parity.py.txt` uses the integrated model.
Frozen raw inputs, feature frames, OOS predictions and fitted research state remain
under `.research/2026-11-15-remaining-warnings/`, including a hash-verified durable
copy of `atp-current.pkl`. The original registered result-frame path is
`/tmp/deuce-remaining-warnings/atp-current.pkl`; restore that path from the durable
copy when replaying the exact scripts. Large binary data is not committed.
The later forecast-ledger-only commit `fbc0306` is reconciled before release.

## Release review

Pending final checks and production verification.


Production promotion approved under the existing user authorization. Required branch
CI [43905449360](https://github.com/ARJUNVARMA2000/tennis-elo/actions/runs/43905449360)
passed at tested commit `c2659f3`: Python3.12 2,155 passed/one skipped; web tests,
lint, TypeScript, static build and browser checks passed. Local Python3.13 passed
2,156 tests. The promotion changes documentation only from that tested application
tree. A full refresh is required to rebuild the ATP saved predictor and both market
scorecards. Production verification remains pending; this is not a recovery claim.


The final join replay against the qualified candidate is retained in
`odds-atp-candidate-replay.json`: 31,316 matched decisions, 30,547 Tennis-Data plus
769 Valuebetennis, coverage through November 13 against OOS through November 15.
It uses the frozen odds source snapshot, not the newer production acquisition.
The recent 616-match model/market comparison remains worse for the model in log
loss (0.6195 vs 0.6103); source recovery is not a claim of a betting advantage.
The original `odds-atp-replay.json` remains as the earlier join assessment.

Follow-up commit `28ce67a` fixes the provider-only label to name only the source
actually used. Its [CI run 43908591398](https://github.com/ARJUNVARMA2000/tennis-elo/actions/runs/43908591398)
passed Python and all web checks; 20 focused odds tests also passed locally.
The added tier diagnostic leaves the monitor and graded sample unchanged.


Timeline repair `5860c3a` passed [required CI 43911355831](https://github.com/ARJUNVARMA2000/tennis-elo/actions/runs/43911355831), including all Python and web checks. The focused migration/health run passed
211 tests. The first full candidate 43906413969 completed both retrains and current
market acquisition (ATP 20,286 matched, WTA 18,702; both through November 15) but
was never published: the separate forecast-timeline gate rejected valid ATP schema6
observations. The gate now derives current schema from the producer and retains
strict generation checks. A standard full retry preserves market/accuracy lineage;
a quick parentless bootstrap would omit those optional outputs.

Reproducibility check: research and CI use identical pinned NumPy2.5.0, pandas3.0.3,
XGBoost3.3.0 and scikit-learn1.9.0. Research ran Python3.13.14 on macOS; production
rebuilds on Python3.12.16/Linux. No model pickle is copied between these runtimes.
Production verification is still pending.
