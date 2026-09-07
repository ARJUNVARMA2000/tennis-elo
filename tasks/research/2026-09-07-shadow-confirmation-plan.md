# Fresh-data confirmation — exact next implementation plan

Status: **design only; no registration, forecast, collector or automation is active.**
The fixed WTA shadow now has an offline saved format. This document follows the
September 7 implementation at `250693c` and the September 6 selected-candidate verdict.
The original future-data phase still needs real elapsed time and trustworthy new inputs.

## Objective and limits

Compare two fixed artifacts on newly observed WTA main-draw singles matches. The primary
measurement is incumbent-minus-candidate log loss on the exact same completed matches.
The reference remains the repaired 42-column model. The candidate remains sigma0=1,
q=0.0001, the fixed 43-column five-bag model, with threshold-32 state selection.
No tuning, alternate setting selection or retrospective relabeling is part of the pilot.

The proposed first pilot is **30 calendar days, minimum 200 eligible settled pairs**.
The horizon is the endpoint; the count reports adequacy, not permission to keep running
until a positive result. If fewer than 200 pairs settle, report insufficient pilot
coverage. A fixed reporting grace period of seven days permits already captured matches
to settle; it admits no new forecasts. Do not stop early on a favorable score.
This is primarily a capture/reliability check and an initial fresh effect estimate.

The historical paired SD is approximately 0.015995, calculated from 15,628 validation
pairs and their naive SE. If both the effect and independent-match variance persisted,
a 200-pair pilot would have SE about 0.001131, much larger than the
observed gain of 0.000240. Approximately 17,063 independent pairs would make
1.96 SE as small as that gain; a conventional two-sided 5% / 80%-power normal
approximation gives about 34,863. These are sensitivity calculations, not target
sample guarantees: selection optimism, event/player dependence and distribution change
can make them misleading. Another hour of fitting cannot create this fresh evidence.

## Implement in this order

1. **Freeze the exact runner contract before editing.** Read `PROSPECTIVE.md`,
   `tennis_model/src/tennis_model/eval/prospective.py`, the new `model/shadow_artifact.py`,
   and the latest todo/research reviews. Existing `register`, `_models` and capture
   paths load both arms through the production loader, so they intentionally reject the
   new `.shadow` format. Do not patch around the loader or hand-edit a registration.
   Work in a fresh checkout; keep the completed experiment and its evaluator immutable.
2. **Add an explicitly typed artifact adapter in a separately scoped runner change.**
   The incumbent role uses the strict production loader; the candidate role uses
   `DynamicShadowPredictor.load` with caller-pinned provenance and the experiment's
   trusted root. Registration records format, payload/envelope file identities,
   artifact ID, training time, runtime, source contract and all provenance hashes.
   It must validate and copy actual files before publishing the registration receipt.
   The root is exclusive; failed registration remains visible and cannot capture.
   Default production-only registration must remain exact and reject unknown formats.
3. **Handle the source-version boundary explicitly.** The shadow contract hashes the
   package source. Adding runner code inside that package changes this identity.
   Finish and test the runner, commit and freeze it, then rebuild the fixed shadow from
   the same sealed inputs in the new checkout. Assert exact probabilities against the
   accepted September 7 artifact in its original runtime. This is a version migration,
   not another search. Never disable source validation or silently rewrite an envelope.
4. **Preserve every capture/grade rule.** The first paired receipt wins on retries.
   Both arms finish at least five minutes before a defensible lower bound on play;
   independent source observations are at most ten minutes old. Timestamps come from
   the local clock after inference and cannot be supplied retroactively. Match identity
   is event ID, season, round and unordered canonical player pair. Reject missing/
   ambiguous identity, unknown entrants in either selected state, uncertain timing,
   already-started matches, differing contexts and changed artifacts. Preserve source
   observations and exclusions even when no pair is eligible. Actual results need
   independent actual-start/finish evidence; retirements, walkovers, cancellations and
   withdrawals are excluded from the primary loss. Pending is not a loss or a win.
5. **Add meaningful negative and integration tests before activation.** Test each
   wrong-format role, missing/mismatched candidate provenance, mutated frozen bytes,
   damaged Gaussian state, duplicate identities, post-start capture, clock boundary,
   failed registration, retry preservation, and a real mixed-format capture/grade
   roundtrip. Prove the default runner still rejects a shadow in its old interface.
   Use real distinct fitted test artifacts, not production forecasts or fake timestamps
   presented as observations. The existing synthetic tests must retain their assertions.
6. **Register a real future interval and arrange capture only after the runner passes.**
   Copy the accepted pair into a new private experiment root. Record the actual start
   time, 30-day endpoint, seven-day settlement grace period, hypothesis, sample rule,
   population and exact artifact IDs/hashes before the first observation. Keep both
   fitted states fixed for this pilot; it evaluates fixed models, not daily retraining.
   A separate decision is needed for daily state/model updates. Verify the schedule
   acquisition source and execution cadence before activation; neither exists for this
   mixed-format pilot yet. No scheduled task has been created by this plan.
7. **Publish the endpoint evidence without changing the adoption gate.** Report paired
   log loss and Brier, winner accuracy, sample size, capture/settlement/exclusion counts,
   model staleness, naive paired SE and week/event uncertainty when identities suffice.
   Retain unsuccessful and underfilled pilots. No automatic adoption follows the target
   count, horizon or a positive pilot mean. The existing retrospective gate has already
   passed; fresh evidence and a simplicity decision remain separate requirements.

## Dependencies and work that can overlap

The artifact adapter/registration boundary must precede mixed-format capture/grade
tests. Capture transport review and a source-observation inventory can be done
independently of adapter implementation. Endpoint-report design can proceed independently
using clearly labeled synthetic receipts. Actual activation waits for the entire tested,
versioned runner and verified saved pair. No agents are authorized by this plan alone.

Production integration of the factual population/foundation repairs can be reviewed
separately from uncertainty adoption. It needs the current Git merge review, applicable
full pipeline and integrity gates, regenerated web data mirror, deliberate production
push and post-deploy verification. None of those release actions was taken in the
September 7 offline serving assessment.
