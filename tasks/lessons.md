# Lessons — index

One line per lesson. Read the topic file for the area you are touching; do not read them
all. Full entries live in `lessons/<topic>.md` — grep the lead line to find one.

New lesson → append the entry to the matching topic file and add its lead line here.

## Data sources & freshness — [`lessons/data-sources.md`](lessons/data-sources.md)

- A keyless upstream can start rejecting your client by its User-Agent alone, and a best-effort fetch that swallows EVERY query reports the outage as an empty week. (2026-08-06)
- One mistyped date in an upstream row can empty a whole tour, because the date-relative windows anchor on the dataset's MAX date, not on today. (2026-07-25)
- A transport that answers 200 with the WRONG BYTES must not end a fallback chain — and a retry cannot fix a payload the source is serving on purpose. (2026-07-24)
- A freshness gate on a REDUNDANT source needs a load-bearing predicate — an unfixable upstream freeze otherwise stands red forever. (2026-07-10)
- Verify a source's naming convention per file, not per format. (2026-07-02)
- Both tours' `fresh` files live in ONE repo, so one bad minute reds the daily retrain. (2026-07-21)
- Label rows by what they ARE, not by which directory they arrived in. (2026-07-25)
- The release snapshot is load-bearing data that `download` cannot reproduce. (2026-07-25)
- An incomplete source moves only `n`, and nothing was watching `n`. (2026-07-25)
- Canonicalising names WITHIN a key group cannot merge variants that change the key — a dropped surname ships one player as two. (2026-07-27)
- A rolling overlay must enforce the model's population policy by stable identity before merge, and intentional population changes need an explicit version boundary. (2026-08-03)

## Draws, rounds & live events — [`lessons/draws-and-live-events.md`](lessons/draws-and-live-events.md)

- A resolver that is "correct under both readings" will silently absorb the OTHER bug it happens to fix — make it name what it did, and read that output. (2026-08-08)
- A player who leaves without losing exits in TWO ways (lucky-loser replacement vs walkover); the wrong one invents a match and erases a real one. (2026-08-07)
- Metadata aliases and draw locators are different namespaces: one title may find the event
  article while a different provider ID/title locates its bracket. (2026-07-29)
- Date overlap plus a token or a few shared players may rank source candidates, but only
  near-complete field evidence may attach an official draw to an event. (2026-07-29)
- Put the model between two deterministic layers, and let the cheap one run first — the scan that enumerates candidates is most of the value. (2026-07-28)
- "It never changes once released" is a claim about the FINAL state; a cache keyed on it must also check the state it was captured in. (2026-07-27)
- Display names are for display; joins use the event ID; the name history IS the alias table. Where no id exists, join on evidence, never on string similarity. (2026-07-28)
- Three bugs kept every HARD-COURT surface unresolved (wikilink pipe, one-word target) and a month guess with no provenance recycled itself as fact. (2026-07-27)
- A name-set invariant must exclude the slots that don't name anyone. (2026-07-24)
- A gate invariant that compares two DERIVED quantities must derive both sides exactly as the code that produced them — and be validated against messy real draw states, not one clean snapshot. (2026-07-13)
- A completed-event projection must filter the ratings frame to main-draw ROUNDS before constructing its field. (2026-07-11)
- Live-event surface has ONE authoritative source (Wikipedia's main article) and must be fixed at the loader source, not the prediction points. (2026-07-08)
- ESPN can't give a full draw at release — Wikipedia can; three traps when adding it. (2026-07-08)
- Live tournament reach-odds must be seated on the ACTUAL draw, not a rating re-seed. (2026-07-08)
- A live feed's round label is draw-relative — resolve it against draw size, not the label/number alone. (2026-07-08)

## Gates & health checks — [`lessons/gates-and-health.md`](lessons/gates-and-health.md)

- A recency timestamp needs provenance; a tournament-start stamp is not a last-match date, so carry the basis into the card and exempt only proven start-date feeds. (2026-08-08)
- A recency gate reads a MAX, so one corrupt future row disables it permanently — and sanitising at ingest blinds the paired corruption check. (2026-08-07)
- Freshness that only a per-EVENT check can see must not be left to a tour-wide aggregate — and when you write the limit down, check it against the sentence you justified it with. (2026-08-06)
- A model-population exclusion must not erase factual event lifecycle evidence; preserve an exact
  complementary event view and join it only at factual event consumers. (2026-08-04)
- A repair that runs only on the slow path is not an invariant: enforce safety after the
  fast path's frozen-field merge, across the whole retained artifact. (2026-07-29)
- Validating every item that EXISTS cannot detect an item that vanished — derive expected
  membership independently, then carry the same keys through build, UI, and live serving. (2026-07-28)
- A fallback that preserves membership must also preserve settled facts already present in its
  evidence, or a projector failure becomes a false missing-result incident. (2026-07-28)
- Validate a gate invariant against the full tour CALENDAR, not the events in flight the week it ships. (2026-07-10)
- Python `json.dump` emits a bare `NaN`, which the browser's strict `JSON.parse` REJECTS — one non-finite float blanks a whole page, and every Python-side check passes it. (2026-07-09)
- A correctness check that runs AFTER deploy can't stop a wrong deploy — gate before, on every mode. (2026-07-09)
- Two timestamps that look like one: "when was this written" vs "when was this trained". (2026-07-25)
- A flag derived from a value the producer then ROUNDS will eventually contradict the number it ships beside — the producer must move, because the gate only ever sees the rounded one. (2026-07-27)
- A normaliser must be self-enforcing against the vocabulary its gate checks, and a tour tag matched as a bare substring finds "men" inside "tournaMENts". (2026-07-27)
- A function-local import makes monkeypatching the CALLING module a silent no-op — the test then exercises the real thing (one silently hit the live API). (2026-07-28)
- An advisory that fires on live data reds the post-deploy sentinel even when the gate passes — budget for fixing what it finds in the same push. (2026-07-28)

## CI, alerts & deploy — [`lessons/ci-and-deploy.md`](lessons/ci-and-deploy.md)

- `tee` masks a failed verifier unless the workflow uses `pipefail`; test the pipeline's exit-status contract, not only the logged output. (2026-08-08)
- A pre-push verification set must include the workflow's exact linter, not only tests and the
  domain gate; otherwise CI becomes the first place formatting is exercised. (2026-08-04)
- Append-only task history still needs explicit completion state: check finished items before
  adding the review. (2026-07-30)
- An alert must never report the failure of its own transport as the thing it monitors. (2026-07-24)
- A static host's DEFAULT cache is a staleness bug for an hourly-refreshed site — and `firebase.json` cannot document its own reasoning, because it must stay strict JSON. (2026-07-16)
- Retiring a host is not the same as taking it down: GitHub Pages serves its LAST build forever. (2026-07-16)
- A "successful" static-hosting deploy proves the upload returned 200, NOT that the live URL serves correct/fresh content — verify the live artifact post-deploy, with propagation-lag tolerance built in. (2026-07-17)
- CI dedup/state must not live in an artifact that only persists on success when the mechanism itself reds the job. (2026-07-10)
- Pin dependencies to the environment that owns the production artifacts, not the dev machine. (2026-07-02)
- A lockfile regenerated on one OS can be incomplete for another. (2026-07-02)
- `cancel-in-progress: true` on the deploy concurrency group silently drops changes. (2026-07-09)
- An `if: always()` alert step must distinguish `skipped` from `failure`. (2026-07-21)
- Inline workflow `run:` shell is untestable, and that is where the false alarm hid. (2026-07-21)
- Never key a decision off *which* cron GitHub says fired. (2026-07-25)
- A `run:` block is `bash -e`, so the second command is conditional on the first. (2026-07-25)
- GitHub drops scheduled slots; claim the work, don't match the clock. (2026-07-27)

## Web app — [`lessons/web.md`](lessons/web.md)

- A hero may change emphasis, never event membership — reserve single-event layouts for truly
  dominant weeks and put the complete, counted alternative-event disclosure above the fold. (2026-07-28)
- Next 16/Turbopack drops SOME same-line spaces after JSX interpolations — put {" "} between any expression/element and following prose, and verify the RENDERED text. (2026-07-10)
- A URL↔state bridge must apply URL→state only on NAVIGATION, and a client "redirect page" must hard-navigate. (2026-07-09)
- A Δ-metric card must compute the sign its own caption promises — and match its neighbours' convention. (2026-07-09)
- Public method-page copy hardcodes tuned constants and cadences — re-verify it after adoptions. (2026-07-09)
- A new data-backed web page is a 6-part contract; miss one and it silently half-works. (2026-07-08)

## Model & research — [`lessons/model-research.md`](lessons/model-research.md)

- A frozen-field policy needs a VALIDITY predicate, not a kind check — and every "who quotes when" race is a leak vector. (2026-07-09)
- Odds-source coverage can silently truncate an eval window — census the books per era, don't trust the frame. (2026-07-09)
- A combiner feature that adds no new state is a pre-paid loss: budget a ~0.0003 LL capacity toll for any new column. (2026-07-06)
- The tuning feature cache is regime/schema-keyed, not param-keyed. (2026-07-06)
- A data-ingestion experiment is two experiments; separate them or the gate measures the wrong thing. (2026-07-05)
- Re-read the git tip immediately before finalizing any plan or doc built from exploration. (2026-07-05)
- Never include the current estimate in the residual it learns from. (2026-07-02)
- A feature that walks can't be adopted unless the pickled state can replay it. (2026-07-02)
- An API field's semantics can mutate over an object's lifecycle — validate on the SETTLED objects you'll actually score, not the live ones you explored. (2026-07-07)
- Duplicated construction sites drift: production shipped WTA pickles with fp=None. (2026-07-09)
- Widening a helper's return arity is invisible to tests that cover the helper and its caller separately — rebuild the real artefact and assert on types. (2026-07-27)

## Round G additions (2026-07-29)

- Draw identity without a stable event ID requires a shared real match; date overlap and
  shared players alone fused Wimbledon into Nordea Open. See
  [`lessons/draws-and-live-events.md`](lessons/draws-and-live-events.md).
- Card content must not be fused to hero layout; reach odds belong to reusable card content
  while hero eligibility controls emphasis only. See [`lessons/web.md`](lessons/web.md).

## Round H addition (2026-07-29)

- A current board ranks lifecycle before prestige; tier is a tie-breaker, not a freshness
  signal. See [`lessons/web.md`](lessons/web.md).

## Round I addition (2026-07-29)

- Peer active events get equal detail; a marquee hero instead makes its visible supporting
  events compact beneath it. See [`lessons/web.md`](lessons/web.md).

## Round P addition (2026-07-31)

- Repeated unresolved provider labels identify distinct draw seats; number them before
  set-backed consumers collapse the field. See
  [`lessons/draws-and-live-events.md`](lessons/draws-and-live-events.md).

## Round R addition (2026-08-01)

- Partition lifecycle before hero selection: live play owns the page, upcoming draws wait, and
  only recent prestige results linger. See [`lessons/web.md`](lessons/web.md).

## Round T addition (2026-08-01)

- Keep primary ordering separate from information depth: future top-tier draws retain their full
  forecast below live play. See [`lessons/web.md`](lessons/web.md).

## Deployment verifier addition (2026-08-11)

- A dependent check must distinguish unavailable input from invalid input; otherwise one
  transport failure cascades into fabricated diagnoses. See
  [`lessons/ci-and-deploy.md`](lessons/ci-and-deploy.md).

## Firebase cache addition (2026-08-12)

- Zero-age revalidation still stores CDN entries; mutable content that must always be fresh can
  require `no-cache, no-store` to avoid stuck cache keys. See
  [`lessons/ci-and-deploy.md`](lessons/ci-and-deploy.md).

## Official draw identity addition (2026-08-12)

- Shared fields plus a boundary date overlap can still join adjacent events; require substantial
  calendar agreement and revalidate retained attachments. See
  [`lessons/draws-and-live-events.md`](lessons/draws-and-live-events.md).

## Provider placeholder vocabulary addition (2026-08-13)

- Normalize semantic placeholder variants before numbering them; an unrecognized repeated label
  becomes one fake player in set-backed consumers. See
  [`lessons/draws-and-live-events.md`](lessons/draws-and-live-events.md).

## Active official-draw revision addition (2026-08-14)

- Settled geometry does not make an active official draw immutable; field drift must refresh the
  whole provider artifact because withdrawals can re-seat several slots. See
  [`lessons/draws-and-live-events.md`](lessons/draws-and-live-events.md).

## Browser scroll-chain addition (2026-08-15)

- Axis-only body overflow plus body overscroll containment can trap wheel input before the root;
  verify scrolling behavior and body width, not CSS substrings. See [`lessons/web.md`](lessons/web.md).

## Live result integrity addition (2026-08-17)

- A green health artifact proves only its existing invariants: compare live artifacts with an
  independent current source, infer bye-heavy rounds from every stage, and treat UTC instants as
  venue-local dates. See [`lessons/draws-and-live-events.md`](lessons/draws-and-live-events.md),
  [`lessons/data-sources.md`](lessons/data-sources.md), and
  [`lessons/gates-and-health.md`](lessons/gates-and-health.md).

## Population-baseline addition (2026-08-17)

- Canonical identity changes alter the historical match population, so advance the explicit
  population version in the same commit; a predictor rebuild alone does not reset the health
  baseline. See [`lessons/gates-and-health.md`](lessons/gates-and-health.md).

## WTA lower-state research addition (2026-08-17)

- Lower-tier role is population evidence and must survive source-preference dedup even while state
  admission is disabled. State-only A/Bs must also freeze any full-frame priors and prove exact
  prediction parity before the first intervention row. See
  [`lessons/data-sources.md`](lessons/data-sources.md) and
  [`lessons/model-research.md`](lessons/model-research.md).

## Live/scheduled state addition (2026-08-19)

- Browser-polled live scores and hourly scheduled forecasts must share lifecycle state; exclude an
  overlap only on stable event id plus the unordered normalized player pair. See
  [`lessons/web.md`](lessons/web.md).

## Source-cadence gate addition (2026-08-19)

- Unscheduled content age describes coverage, not transport availability; detect source breakage
  from validated download results and preserve the last good input atomically. See
  [`lessons/gates-and-health.md`](lessons/gates-and-health.md).

## Portfolio documentation addition (2026-08-20)

- A portfolio README should make operational depth legible, not secondary: retain concrete data,
  deployment, monitoring, and reproducibility details while improving hierarchy. See
  [`lessons/documentation.md`](lessons/documentation.md).

## Gated-state model addition (2026-08-22)

- A row-level feature gate does not protect its baseline arm if the shared combiner is retrained on
  gated rows; protection must cover the fitted model and calibration too, with exact protected-row
  probability parity. See [model research](lessons/model-research.md).

## Generic draw-anchor addition (2026-08-23)

- An all-generic event name cannot safely seed Wikipedia draw search: require an exact event
  locator, revalidate active cached identity, prevent rejected-current-row retention, and gate the
  raw cache for duplicate sources. See [draws and live events](lessons/draws-and-live-events.md).

## Blocked-deploy state addition (2026-08-23)

- A pre-deploy gate can stop publication after an earlier append-only writer has persisted the bad
  identity; fix the producer, retain the gate, and bridge the durable identity from exact evidence.
  See [`lessons/gates-and-health.md`](lessons/gates-and-health.md).

## Query-only URL transition addition (2026-08-24)

- A state control's URL mirror must survive the reverse transition without reusing the framework's
  internal history marker; browser-test A -> B -> A and assert active control, rendered data, and
  copied URL after settling. See [`lessons/web.md`](lessons/web.md).

## Participant-contract additions (2026-08-24)

- A serialized participant vocabulary must be migrated and parity-tested in every runtime that
  consumes it. See [`lessons/draws-and-live-events.md`](lessons/draws-and-live-events.md).
- Resolve ambiguous provider nulls before normalization and never use an equally partial field as
  proof of completeness. See [`lessons/draws-and-live-events.md`](lessons/draws-and-live-events.md).

## Stage-observability additions (2026-08-24)

- Keep detailed stage errors private and public incident revisions stable across identical retries.
  See [`lessons/gates-and-health.md`](lessons/gates-and-health.md).
- Give observability artifacts explicit rollout, missing, malformed, and incomplete-state semantics.
  See [`lessons/gates-and-health.md`](lessons/gates-and-health.md).
- Make private artifacts ineligible for the previous mirror and bind degradation evidence to the
  exact generation that rewrote its source. See
  [`lessons/gates-and-health.md`](lessons/gates-and-health.md).

## Rollback and browser-fixture additions (2026-08-24)

- Serialize warmed caches so both current and rollback readers remain fail-closed. See
  [`lessons/draws-and-live-events.md`](lessons/draws-and-live-events.md).
- Gate fixture identities explicitly so the general browser verifier remains usable with real data.
  See [`lessons/web.md`](lessons/web.md).

## Artifact-integrity additions (2026-08-24)

- Validate exact bytes, runtime, dependencies, configuration, and concrete fitted/state structure
  around—not merely after—pickle deserialization. See
  [`lessons/model-research.md`](lessons/model-research.md).
- Treat the trusted root—not a leaf-level no-follow flag—as the filesystem boundary: reject
  symlinks and non-directories in every parent component before predictor reads or writes. See
  [`lessons/model-research.md`](lessons/model-research.md).
- Close separately atomic payload/envelope crash windows with a durable pending marker, and treat
  release acceptance/manifest files as revocable validity pointers. See
  [`lessons/gates-and-health.md`](lessons/gates-and-health.md).
- Apply that same component-by-component trust check to public release publication, including on
  platforms without `O_NOFOLLOW`, before any read, replace, prune, or deserialization. See
  [`lessons/gates-and-health.md`](lessons/gates-and-health.md).
- Harden the complete lineage I/O inventory—not only ordinary artifact writers—including validity
  pointers, removals, carry/mirror compatibility paths, and alias-aware root-overlap checks. A
  fallback may run only after every stale proof is durably revoked. See
  [`lessons/gates-and-health.md`](lessons/gates-and-health.md).
- Keep fallback through observed legacy, full-bootstrap, and quick-carry production states; a failed
  shadow publication must revoke stale proof before exact fallback. See
  [`lessons/ci-and-deploy.md`](lessons/ci-and-deploy.md).
- After those observations, replace the compatibility path with one flag-free enforcement commit;
  do not maintain an unexercised dormant strict contract beside shadow mode. See
  [`lessons/ci-and-deploy.md`](lessons/ci-and-deploy.md).

## Round 4 enforcement additions (2026-08-24)

- Include predictor generation in retry identity even when presentation collapses observations into
  hourly buckets. See [`lessons/gates-and-health.md`](lessons/gates-and-health.md).
- Bind source, destination, and tour directory descriptors for the complete release transaction,
  including cleanup and postvalidation. See
  [`lessons/gates-and-health.md`](lessons/gates-and-health.md).
- Revoke the all-tour acceptance pointers before any single-tour/debug mutation, and keep that path
  non-publishing. See [`lessons/gates-and-health.md`](lessons/gates-and-health.md).
- Pair exhaustive positive manifest verification with bounded exact-404 probes for known private and
  omitted optional paths. See [`lessons/ci-and-deploy.md`](lessons/ci-and-deploy.md).
- Treat a current same-event scheduled matchup as positive draw-replacement evidence only when exact
  opponent continuity identifies one unique vacated slot. See
  [`lessons/draws-and-live-events.md`](lessons/draws-and-live-events.md).
- Establish the descriptor-validated release root before every mutation entry point, including a
  cold single-tour/debug revocation. See
  [`lessons/gates-and-health.md`](lessons/gates-and-health.md).

## US Open draw readiness (2026-08-28)

- Keep explicit qualifying provenance out of main-draw lifecycle evidence, and preserve provider
  metadata that controls match format across saved-ID refreshes. See
  [`lessons/draws-and-live-events.md`](lessons/draws-and-live-events.md).
- Gate live status on exported main-draw evidence and apply the documented Grand Slam qualifying
  window to upcoming-transition health. See
  [`lessons/gates-and-health.md`](lessons/gates-and-health.md).
- Publish one contextual probability across bracket and schedule views, and use `espnId` for every
  event link and client-side artifact join. See [`lessons/web.md`](lessons/web.md).

## Selected-state eligibility addition (2026-08-29)

- Forecast eligibility must follow the predictor state bundle the adopted gate actually selects;
  current-season lower-state acquisition and broader population adoption are separate decisions.
  See [`lessons/model-research.md`](lessons/model-research.md).

## Product publication addition (2026-09-04)

- A finished static preview needs both the new UI and a current accepted data snapshot; carry
  push authorization through live checks. See [`lessons/web.md`](lessons/web.md).
- Exercise benchmark gates with producer-generated settled reports, not only pending fixtures.
  See [`lessons/web.md`](lessons/web.md).
