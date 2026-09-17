# Phase 0 interface decisions — model foundation

Decision status: **fixed for the first implementation pass; not implemented yet.**
The user authorized Phase 0 preparation. These contracts let later workers implement
independently without changing the incumbent or selecting parameters in this phase.
They do not amend `PROGRAM.md` or authorize a model adoption.

Code/evidence base: `d95afc6` preparation commit, model code unchanged from `f4a221b` /
`e170298`. Private snapshot manifest:
`8636748e1012a1fa1f5a31ea0cdd52f414acfaa78ca5123931e24d1c86473cb9`.
Workspace locations, verification and final state are recorded in the Phase 0 review.

## D1 — one calibrated pair-probability function

Proposed new `model/probability.py`, owned by A. Export one batch primitive:

```python
paired_probability(clf, calibrator, forward_features, reverse_features=None) -> np.ndarray
```

- Both frames have the exact ordered `FEATURES` schema and identical row count. If
  reverse rows are omitted, negate only `ANTISYM`, retain `SYMMETRIC`, and validate
  that the two sets partition the current feature list without overlap.
- Evaluate both directions through the same fitted classifier and calibrator, then
  return `0.5 * (calibrated_forward + 1 - calibrated_reverse)` in float64.
- Explicit reverse frames support end-to-end tests that independently build features
  from swapped players. They must represent the same context and row pairing.
- Do not fit a calibrator, mutate frames/state, select another model or choose a
  different WTA bundle inside this primitive. Reject non-finite/malformed inputs;
  use the same declared numerical clipping convention across consumers.
- Every scalar, batch, evidence, neutralized-evidence and walk-forward consumer uses
  this operation. Component Elo/point probabilities retain their existing mathematics;
  the combined component uses this shared function.
- Do not change training orientation, XGB settings or calibration families during the
  consistency repair. A symmetry-aware recalibration is a separately declared candidate.

Required invariants: direct A/B complement within `1e-12`, matrix permutation, scalar/
batch/evidence parity, stable same-context WTA routing, and an independent asymmetric
fixture exercising actual entry points. A matrix filled by complements is insufficient.

Integration owner: coordinator for `model/train.py`, shared parts of `model/predict.py`,
`pipeline.py`, artifact contracts, schema increments and output audit/gate wiring.

## D2 — temporal style evidence and a saved immutable profile snapshot

Owner B, proposed new temporal types in `data/charting.py` or a small sibling module.

Logical input record:

```text
chart_match_id, canonical_player_key, played_at_or_date, available_at (if proven),
availability_basis, source_identity, per-match sufficient statistics
```

Logical operations:

```python
style_before(cutoff, evidence_policy) -> StyleSnapshot
StyleSnapshot.profile(player_key) -> values_and_counts
```

- Index chart rows by chart match ID, join metadata explicitly and reject ambiguous
  identities. Preserve the current eight style definitions initially.
- A historical snapshot uses only admitted records strictly before the cutoff. The
  target match and its counts cannot contribute to its profile or `has_style` threshold.
- Date-only evidence is processed in batches: query before the day's batch, then admit
  the batch afterward. Do not manufacture within-day order from file order.
- Keep played date and publication/observation date distinct. When historical publication
  dates are unavailable, permit an explicitly named retrospective played-date policy,
  report that limitation, and never label it fully verified real-time availability.
  A future prospective path uses actual observation receipts.
- Store definitions/version, canonical identity version, cutoff, availability policy,
  source fingerprint, counts and exact profile values in the predictor-owned snapshot.
  The snapshot has no method that downloads or consults global current chart files.
- Generic forecasts use that saved snapshot. Advancing the forecast date cannot admit
  new charts into an already fitted artifact. A new training generation may create a new
  snapshot through the normal builder.
- Main/enriched WTA bundles use the same admitted chart evidence for the same cutoff;
  lower-tier admission does not silently change style availability.

Test current-row exclusion, future-chart append/change/delete invariance, missing/duplicate
metadata, count-threshold crossing, prefix-to-serialized parity, and prediction stability
after the global chart cache changes. Coordinator updates exact artifact class/field
checks rather than loosening validation for a new object.

## D3 — chronological serve priors with explicit sufficient statistics

Owner B. **Choose chronological priors, not a pre-1991 fitted fixed prior.** Preparation
found no pre-1991 WTA stats; the cached complete ATP enriched frame has only 62 such
matches (9,002 serve points), all Hard. This does not support a shared per-tour,
per-surface fixed warm-up recipe. The normal-loader replay confirmed these row counts.

Logical state, separate from each player's decayed accumulators:

```text
ServePriorState:
  total_service_points, total_service_points_won
  points_by_surface, won_by_surface
  initialization_probability = 0.62
  last_admitted_cutoff, observation_policy_version, population_policy_id
```

Use the existing data-independent fallback `0.62` only while no prior service-point
evidence exists. Once prior eligible points exist, global prior is prior won/played;
each surface uses its own ratio when nonempty, otherwise the prior global ratio. No
new tunable pseudo-count or smoothing parameter enters this correctness pass. Preserve
the existing player/surface shrinkage constants, decay parameters and feature schema.

Logical API:

```python
prior = prior_state.before(cutoff)  # query must not consume the current observation
prior_state.observe(eligible_completed_observation)  # after the applicable batch
```

Rules:

1. Share one chronology/admission policy between historical feature generation and saved
   state. Record the prior used for each diagnostic row before consuming its outcome.
2. Model-level admission masks are explicit. ATP incumbent may use its admitted main+
   lower state rows; a state-only A/B holds the prior-update population identical across
   arms. WTA main/enriched arms share main-draw-only prior updates at each cutoff.
3. A match needs finite valid denominators/numerators, a declared result eligibility
   policy and an admissible information time. Future or unknown-time evidence cannot
   enter just because the file is available today. The B3 date-basis audit must resolve
   tournament-start versus played/available dates before this policy is called temporally
   valid. Use a conservative proven bound or exclude unresolved observations; do not
   invent event-end times. Record loss of eligible evidence explicitly.
4. Batch observations with indistinguishable availability times so row order does not
   determine their pre-match priors. Player walks retain their declared chronology;
   any additional look-ahead found there becomes a named prerequisite repair.
5. The current `gsw/grw/ssw/srw` store absolute opponent-adjusted sums, not raw residual
   sums. Preserve that representation: historical observations retain the opponent
   adjustment applied at their observation time. Recompute relative skill from those
   sums using the queried baseline. Do not subtract a baseline a second time, rescale
   old counts merely because the prior changes, or treat old adjusted sums as unadjusted
   point counts. Prior-state totals use the actual, unadjusted point counts.
6. Derive and test this estimator algebra before integration. A synthetic fixed-prior
   case must reduce to existing formulas; changing the baseline must not add fictitious
   evidence or create player updates. Historical opponent adjustment is an approximation
   retained for this correction, not a joint latent-model fit.
7. Serialize prior counts, policy and cutoff. Prediction is read-only: querying several
   matchups or changing their order cannot advance shared prior state.

If implementation cannot satisfy these invariants, record the failed derivation and revise
the decision explicitly before evaluating candidates. Do not fall back to a full-frame
average. This phase makes the interface/policy choice; implementation proof is phase 1B.

## D4 — outcome-independent evaluation with the existing time split

Coordinator owns evaluation and training glue; A supplies the probability primitive.

- Retain tune 2010–2019, validation 2020+, five bags and the full paired arbiter. Record
  the actual frozen data-through date; show partial 2026 separately.
- Canonical order is lexicographic order of `names.name_key` applied to the frozen
  canonical player identity. Bind that mapping to the alias/population version. Resolve
  equal keys from distinct identities as an error, never by winner/loser position.
- For the uncorrected legacy arm, construct that orientation before consulting the
  outcome, predict once, and convert the result to probability of the eventual winner
  afterward. Keep the old winner-first score under a separate legacy label.
- Corrected forecasts use D1 and should be independent of canonical ordering. Report
  both-direction average loss as an additional diagnostic; do not transform the legacy
  arm into the corrected average and then claim to compare different behaviors.
- Calibration and fitting splits stay unchanged in this repair. Different calibration
  or update schedules are later hypotheses after a baseline exists.
- Use unique row keys including event/round/source identity where available; assert
  paired equality. `snapshotRow` is an audit index, not a cross-dataset join key.
- Keep naive d±SE and per-year results. Add predeclared event/week uncertainty and slices
  in phase 1D before freezing the evaluator; those additions do not replace the standing
  gate without an explicit reviewed methodology change.
- Reproduce WTA with its threshold-32 dual-state walk, not a main-only feature call.

No evaluator code or PROGRAM policy changed during Phase 0. Methodology maintenance must
be completed/reviewed before the numerical research round; invalid legacy information is
not an adoption target that the corrected model must beat.

## D5 — versioned cache and audit identities

Coordinator is sole owner of version increments, serialized contracts and shared receipts.
Workers propose interfaces/tests; they do not independently increment the same schema.

Feature-cache identity must include:

- ordered feature definitions, all feature-affecting parameters and source code identity;
- temporal style/prior policies and their initialization, availability and cutoff semantics;
- alias/population policy and WTA routing threshold;
- normalized source content fingerprints, source manifest and explicit as-of clock basis;
- Python/model dependency identity and the serialized state/schema version.

Use canonical, finite JSON to derive logical hashes. Relative source paths and contents
identify data; absolute workspace paths belong in audit metadata, not the logical content
identity. Existing normalized cache fingerprints include absolute paths and UTC day, so
they legitimately change after copying a workspace. Validate them through the normal
loader; compare frame-value/row-key hashes separately to establish equal data.

The snapshot preserves two one-row main caches as found. They are not a complete main
population and are not authoritative evidence. Fresh normal-loader reconstructions in
an isolated root must replace/reject them normally. Do not patch fingerprints to reuse
an incompatible copied cache.

Proposed private prediction audit receipt (`schema` name finalized by coordinator):

```text
schema, predictor_artifact_id, inference_schema, source_generation,
context_fingerprint, probe_definition_version, declared_pair_count,
direct_exchange_max_error, scalar_batch_max_error, permutation_max_error,
observed_at, evidence_digest
```

Generate evidence from independent actual calls, bind it to the exact saved predictor
and context, and reject missing/stale/empty/malformed receipts after its declared rollout.
Use typed health findings and both full/quick paths. Existing public matrix-complement
checks remain useful but cannot substitute for the direct-call witness. Keep private
receipts out of release mirroring, and extend lineage/serving tests where needed.

## Ownership and next integration boundary

| Lane | Own work | Shared changes submitted to coordinator |
|---|---|---|
| A | `model/probability.py`, focused exchange fixtures and consumer audit | `predict.py` common sections, `train.py`, export/evidence/gate glue |
| B | temporal charting module/state, `points/serve_return.py`, prefix fixtures | `features.py` shared assembly, predictor construction, schema/artifact validation |
| C | read-only data/source census and acquisition proposal | ingestion/identity changes are proposed for later review, not made in phase 1C |
| Coordinator | protocol, integration, config/schema, task log, manifests and acceptance | owns all merge order and the final frozen evaluator |

No workers have started Phase 1. The prepared branches are available for those lanes
once that scope is authorized. Before delegation, read the Phase 0 review, verify the
snapshot hash and current branch state, and allocate only the named files/outputs.
