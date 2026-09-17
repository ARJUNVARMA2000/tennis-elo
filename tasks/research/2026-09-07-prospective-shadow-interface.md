# Mixed-format runner — pre-implementation contract

Version: `prospective-shadow-v1`, WTA main-draw singles, fixed artifacts. The old
`eval/prospective.py`, walk-forward evaluator and all preexisting tests remain exact.
The new module is `eval/prospective_shadow.py`; no production importer or scheduler.

Registration requires an explicit research trusted root, an ordinary incumbent pickle
and envelope, a candidate `.shadow`, and all five caller-pinned provenance hashes.
Validate source artifacts, copy their exact bytes into an exclusive directory, reload
and validate the copies, then publish registration last. Record formats, artifact IDs,
training times, file hashes, runtime, full contracts and model state cutoffs. A failed
directory remains for diagnosis; it has no usable registration. No permissive loading.

The registered policy is 30 days, 200 minimum settled pairs, seven additional days for
result intake. These values are fixed in this version. Require source identification
and a written acquisition/timing/cadence description at registration, pinned HTTPS hosts
for schedules/results, and label evidence `live` or `synthetic-qa`. No timestamp override
exists in the API or CLI. A QA label cannot be upgraded after registration.

Capture uses the same factual-context schema as PROSPECTIVE.md, WTA best-of-three only,
event-ID/season/round/unordered-player identity and selected-state eligibility. Preserve
all bounded structurally valid source observations, including exclusions. Schedule age
must remain at most ten minutes through inference. Both predictions must finish more
than five minutes before the defensible earliest start; the lower bound must fall
before capture closes. Recheck local time after inference. First receipt wins.

Results are ingested only before the fixed settlement deadline. Repeated observations
are idempotent and all retained batches contribute to reporting. Pending observations
cannot erase terminal facts. Completed evidence can gain missing timing, but differing
terminal statuses, winners or supplied actual timestamps mark that match conflicted
and exclude it, retaining all evidence. Missing or invalid completion timing is excluded;
actual start must also corroborate the forecast's five-minute margin and lower bound.
Unknown statuses remain pending; retired/walkover/withdrawn/cancelled are excluded.

Receipt reads/writes are bounded, digest checked and confined through descriptor-based
no-symlink filesystem helpers. A process lock serializes operations on each experiment.
Capture summaries persist retry/exclusion counts. Reports revalidate models and all
evidence links. At/after settlement close, report publishes a create-only endpoint
receipt; subsequent reads reproduce it and cannot accept further result evidence.
Report paired loss/Brier with naive SE, winner accuracy (ties count half), week/event
bootstrap uncertainty, capture/settlement counts, fixed-state staleness and coverage.
Count adequacy is separate from time. No automatic adoption or early-stop rule.

Testing precedes source freeze. The full source hash changes when adding this module;
rebuild the fixed shadow using identical sealed inputs only after the code commit.
Compare exact forecasts and fitted outputs against the accepted artifact loaded in its
protected original runtime. Keep both versions. Synthetic end-to-end QA is engineering
evidence only. Live activation still requires a source/cadence implementation validated
against actual scheduled and settled objects, and real future time.
