# Offline WTA shadow contract — implementation registration

Base: `777a38e235755754e6175b294b47f48a70e90b31`; branch `codex/model-dynamic-shadow`.
User's continued instruction authorizes this offline implementation. Read the live todo.
This contract is recorded before source edits and real shadow fitting.

- `TennisPredictor.feature_columns` and `_combiner_probability(frame)` are the only
  shared dispatch hooks; the defaults retain exactly the ordered 42 columns and paired
  calibrated probability. Every scalar, component, evidence and matrix path uses them.
- `DynamicShadowPredictor` is an explicit WTA subclass. Its schema is the registered
  ordered 43 columns. It adds `dynamic_main`, `dynamic_lower`, `shadow_provenance` fields;
  it uses the identical main-count threshold-32 selector, selected bundle's default date,
  and a nondestructive dynamic-state view. Earlier-than-saved-state queries fail.
- Production config is unchanged. `DYNAMIC_SHADOW_PARAM_OVERRIDES` records the already
  selected WTA sigma0=1, q=0.0001 without activating it. No new parameter or tree selection.
- `build_shadow_inputs(main, enriched)` rebuilds both existing state bundles and both
  dynamic walks from explicit input frames, returning main-only fit features plus
  threshold-selected scoring features. `fit_shadow_predictor` uses the ordinary final
  split (completed main 1991+, last 365 days for calibration, existing final seed), the
  registered five-bag fitter, and all final states. All source identity checks stay active.
- Shadow persistence uses one private `.shadow` file: fixed magic, bounded JSON header
  length, strict header, then exact pickle bytes. Header includes runtime/libraries,
  production base contract, 43-column/state schemas, selected parameters, observation
  semantics and caller-pinned provenance. Required provenance names are
  `referenceFreeze`, `candidateFreeze`, `selection`, `mainInput`, `enrichedInput`;
  all values are SHA-256 digests. Loading requires the expected provenance explicitly.
- Before unpickling: validate header shape/types, runtime/configuration/provenance,
  payload length/hash. Afterward: exact predictor fields/class, five fitted boosters,
  calibration, all ordinary states, both concrete Gaussian states, covariance/parameter/
  player/cutoff consistency. Missing state never becomes an implicit cold state.
  Ordinary loaders retain their exact production type/schema requirements.
- Reuse artifact filesystem primitives for bounded reads and descriptor-relative atomic
  writes; a single-file format avoids a new split payload/envelope crash window. Require
  explicit research destination and trusted root; reject production-root destinations.
- Existing seven evidence groups retain their meaning as conditional sensitivities of
  the actual combiner with the dynamic signal held fixed. This is not a new public UI.

Acceptance is exact frozen OOS reproduction, serialized historical all-feature parity,
all shared prediction routes, default ATP/WTA parity, strict corruption/path tests and
full tests/lint. Measure latency and storage rather than assuming the new state is cheap.
The candidate's past validation score is already known; these are implementation checks,
not additional performance evidence. No collector, production merge/push or deployment.
