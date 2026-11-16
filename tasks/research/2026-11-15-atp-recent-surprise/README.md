# ATP recent form and odds-source repair — November 15–16, 2026

Status: **deployed and independently verified on November 16, 2026**. The user
approved implementation, historical research and deployment. Both odds warnings
are closed; the historical ATP drift advisory remains visible pending new evidence.

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

The complete release and final quick refresh passed their publication and serving
checks. The final verification and remaining advisory are recorded below.


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


## Final production review — November 16, 2026

- Required final [CI 43913989612](https://github.com/ARJUNVARMA2000/tennis-elo/actions/runs/43913989612):
  2,165 Python tests passed, one skipped; 375 web tests, lint, TypeScript, static
  build and browser checks passed. The final odds checks passed 22 tests locally.
- [Full production retry 43912569501](https://github.com/ARJUNVARMA2000/tennis-elo/actions/runs/43912569501)
  passed source acquisition, both retrains, the pre-upload gate, publication and all
  22 live checks. Its only failed step was the full-mode health reporter for the
  preserved ATP drift advisory. The 70 MB recovery snapshot was uploaded.
- [Final quick refresh 43915628131](https://github.com/ARJUNVARMA2000/tennis-elo/actions/runs/43915628131)
  completed **green**, preserving both rebuilt predictor IDs and training timestamps.
  Full and quick releases also passed independent 22/22 serving checks: 452 exact
  public artifacts, 414 referenced shards, and 18 known private/absent paths.
- Final release `3d4af4e8-586a-435a-8d21-076c4b9f311c` is generated at `2026-11-16T17:16:19Z` and carries accepted
  full parent `c93f11c7-f216-4546-9ecd-3cbb8ad36df1`.

| Tour | Predictor artifact | Trained UTC | Features/schema | Matched odds | Last matched / OOS end | Providers |
| --- | --- | --- | --- | --- | --- | --- |
| ATP | `946c1a49-3fab-446b-a7de-3427b8f6c507` | 2026-11-16T17:01:20Z | 43 / 6 | 20,286 | 2026-11-15 / 2026-11-16 | Tennis-Data 19,370; Valuebetennis 916 |
| WTA | `8398343d-7785-4a1a-aa98-d0faf1b0a892` | 2026-11-16T17:07:21Z | 43 / 6 | 18,702 | 2026-11-15 / 2026-11-15 | Tennis-Data 18,004; Valuebetennis 698 |

The attribution, acquisition receipts, unchanged predictor identities and live
contract checks are retained in `production-full-verification.json` and
`production-quick-verification.json`. The grading proof covers all 1,032 ATP and
1,051 WTA graded decisions with zero contradictory known event IDs.

Odds alerts [#181](https://github.com/ARJUNVARMA2000/tennis-elo/issues/181) and
[#176](https://github.com/ARJUNVARMA2000/tennis-elo/issues/176) closed automatically,
as did all nine rollout schema alerts (#202–210). Exact transitions are retained in
`production-issue-transitions.json`.

Remaining condition: [ATP drift #170](https://github.com/ARJUNVARMA2000/tennis-elo/issues/170)
is still open: 621 graded matches in the 90-day window, realized log loss 0.6259
versus expected 0.5719, d=0.0540, SE=0.0198, t=2.73. This remains evidence about
historical immutable forecasts. The newly adopted improvement passed the historical
arbiter; recovery requires new forecast results. Thresholds, forecast probabilities,
model version and history were not reset to clear it.
