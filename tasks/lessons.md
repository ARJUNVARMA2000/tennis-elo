# Lessons

- **A static host's DEFAULT cache is a staleness bug for an hourly-refreshed site — and
  `firebase.json` cannot document its own reasoning, because it must stay strict JSON.**
  (2026-07-16, github.io → Firebase Hosting) Firebase Hosting caches static content in the
  browser for **1 hour by default**. This site redeploys hourly with fresh live scores, so
  shipping `firebase.json` without explicit headers would have served hour-stale odds as live
  — the exact failure class the pre-deploy gate exists to prevent, arriving through the host
  rather than the pipeline. Hence `**` → `max-age=0, must-revalidate` and only the
  content-hashed `/_next/static/**` → `immutable`. Two traps behind this: (1) Firebase's
  header `source` globs match the **request URL path, not the resolved file**, so with
  `trailingSlash: true` a `**/*.html` rule matches NOTHING (routes are `/method/`, and the
  Next 16 RSC payloads `__next.*.txt` carry data too); (2) **header precedence is
  last-match-wins in practice, even though the docs say first-match** — a known discrepancy
  (firebase-tools#9467). Verified live on 2026-07-16: with the specific `/_next/static/**` rule
  listed FIRST and the `**` catch-all second, the hashed chunks came back `must-revalidate`
  (the catch-all's value) — the second rule won. Fix: order **catch-all first, most-specific
  last**, so `**` blankets everything must-revalidate and `/_next/static/**` then overrides the
  hashed assets to `immutable`. Confirm with `curl -I` on a real `/_next/static/...` asset after
  every deploy — a bad order is silent (safe/stale-free either way, so tests never catch it) and
  only shows up as lost cache headroom, which for a free-tier host is lost bandwidth budget. **Why:** the docs show `//` comments inside
  `firebase.json`, but firebase-tools `JSON.parse`s it and the evidence that comments survive
  is ambiguous — a deploy-gating file is not the place to gamble, so the config is strict JSON
  and the "why" lives here. **How to apply:** when moving hosts, treat the new host's default
  `Cache-Control` as a first-class correctness input, not a perf knob — assert the shipped
  headers with `curl -I` post-deploy rather than trusting the config; and when a config format
  can't hold a comment, put the reasoning in this file and point at it from the caller
  (`refresh.yml`'s deploy step), never nowhere.

- **Retiring a host is not the same as taking it down: GitHub Pages serves its LAST build
  forever.** (2026-07-16, same migration) Simply pointing `refresh.yml` at Firebase would have
  left `arjunvarma2000.github.io/tennis-elo/` serving a frozen, permanently-stale forecast site
  with no pipeline behind it and nothing to alert on it — worse than a 404, because it still
  looks live. Fix: a one-shot dispatch-only `pages-redirect.yml` that replaces the build with a
  redirect stub, where **`404.html` does the real work** — Pages serves it for every unmatched
  path, so it rewrites `/tennis-elo/<route>/` onto the new origin in JS and old deep links
  survive; `index.html` alone would only have caught the bare root. Ordering is load-bearing:
  the new host must be verified live BEFORE the redirect ships, or the old URL forwards to a
  dead site. **How to apply:** when decommissioning any deploy target, ask "what does the old
  URL serve tomorrow if I do nothing?" — for a CDN/static host the answer is usually "the last
  good build, indefinitely", which for a data site means stale-as-live.

- **A "successful" static-hosting deploy proves the upload returned 200, NOT that the live URL
  serves correct/fresh content — verify the live artifact post-deploy, with propagation-lag
  tolerance built in.** (2026-07-17, Firebase deploy test suite) The pre-deploy `health.py --gate`
  structurally can't see Firebase-serving failures (stale CDN content after a green deploy,
  cache-header/MIME/trailingSlash/404/basePath regressions) because it validates local JSON
  before upload — the exact class the reference project hits "consistently." Answer:
  `web/scripts/verify-deploy.mjs`, a fetch-based suite run post-deploy against the live URL,
  asserting routes + the cache-header split + MIME (not falling through to `text/html`) +
  `/method`→301→`/method/` + real 404 + og:image-on-origin + **the live `health.json`
  `generatedAt` == the just-built one** (the load-bearing "deploy green but CDN serving old
  content" catch), alerted via a dedup'd `deploy-health` issue mirroring the data-health step.
  Two design rules learned: (1) **the freshness check MUST retry/backoff (~60-90s)** — Firebase
  edge propagation lags the deploy by seconds, so a single-shot freshness assert flakes on every
  run; make the window env-tunable (`FRESH_TRIES`) so CI can widen and tests can shorten it.
  (2) **Prove a test suite BITES, not just passes** — before trusting it, run negative controls
  (wrong `EXPECT_GENERATED_AT` → freshness FAIL; bad `--base` → routes FAIL). A suite only ever
  seen passing on a good deploy might be asserting nothing. Split pure helpers into a
  side-effect-free module so unit tests import them without firing network checks.

- **A gate invariant that compares two DERIVED quantities must derive both sides exactly as
  the code that produced them — and be validated against messy real draw states, not one clean
  snapshot.** (2026-07-13, /bracket export) Two blocking false-positives shipped because the
  bracket invariants were only exercised against a fully-resolved live Wimbledon: (1) the
  champion cross-check compared on casefold, but `champion` is the results `winner_name` while
  the bracket slot is the elo-canonical spelling — a diacritic (Nosková vs Noskova) is the SAME
  player; compare on `_name_key` (accent/punct-insensitive), the exact key `bracket_rounds`
  used to assign the winner. (2) the drawSize check counted only non-placeholder players, but
  tournaments.json `drawSize` = `len(field_pool)` counts every non-null slot INCLUDING
  unresolved `Qualifier N` placeholders — an early-captured draw frozen by the first-capture
  wiki cache (Gstaad: 2 named + 26 qualifiers = 28) then reads "2 round-0 players but drawSize
  28" and blocks the whole deploy. **Why:** synthetic tests and a single in-flight event never
  exercise the frozen/placeholder/bye/accent/sponsor-name states real draws pass through; the
  same Gstaad 28-draw that broke the power-of-two check on 2026-07-10 broke this one too.
  **How to apply:** before landing a blocking invariant that compares counts or names, (a)
  compute BOTH sides with the identical predicate/key as their source, and (b) enumerate the
  draw states across the calendar — early-frozen placeholder draws, byes, qualifiers, accented
  names, sponsor vs archive event names — and confirm each is legal. Extends the "validate a
  gate invariant against the full tour CALENDAR" lesson below.

- **A completed-event projection must filter the ratings frame to main-draw ROUNDS before
  constructing its field.** (2026-07-11, Wimbledon final deployment failure) The live path
  used Wikipedia's 128-slot bracket and worked all fortnight; the instant the final appeared,
  the completed path unioned every player in the event group, including ratings-only qualifying
  rows. More than 128 names padded to an impossible 256-slot bracket and crashed before the
  pre-deploy gate. The first fix filtered `draw_level == "main"`, but production still failed:
  legacy/source Q1/Q2 rows can be default-labelled `main`. Rule: event completion may change the
  projection mode, never the population; filter both provenance AND recognized knockout rounds
  (`R128`..`F`), and when the authoritative Wikipedia draw exists, retain its population after
  completion instead of reverting to the noisier results union. Gate any shipped `drawSize > 128`.

- **A freshness gate on a REDUNDANT source needs a load-bearing predicate — an
  unfixable upstream freeze otherwise stands red forever.** (2026-07-10, fresh overlay)
  TennisCourtLog froze its ATP results file on 2026-06-22 (repo still auto-commits
  draws/WTA; the file didn't move; no maintained replacement mirror exists on GitHub)
  while the TML stats overlay covered every missed event with full stats+ranks — the
  merged frame lost NOTHING, yet the 14d fresh gate opened a data-health issue no local
  action could clear, and a standing red masks the next real problem. Two latent
  calendar false-trips in the same family: a completed-events-only weekly source
  legitimately exceeds 14d during every slam fortnight (WTA fresh would have tripped
  ~Jul 12 mid-Wimbledon), and ATP stats rows are anchored on tournament START dates so
  a slam parks stats_age at ~15d (the 12d gate would have tripped the same Sunday —
  raised to 16). Fix shape: enforce the fresh gate only when the stats overlay is ALSO
  stale (`stats_current` shadow predicate in health.problems()) — data-driven, no
  per-tour hardcoding; both-frozen still alarms twice, and if the primary source ever
  dies the shadow evaporates automatically. Rule: before adding a per-source age gate,
  ask "what would we DO if it fired alone?" — if the answer is nothing (redundant
  layer, healthy siblings), gate the conjunction that is actionable. Extends the
  calendar-validation lesson below.

- **CI dedup/state must not live in an artifact that only persists on success when the
  mechanism itself reds the job.** (2026-07-10) The hourly sentinel dedup'd on
  `problems_changed`, computed against the prev `health.json` carried in the Actions
  data cache — but `actions/cache` saves only when the job SUCCEEDS, and the dedup's
  own `exit 1` made the job fail, so the "already reported" state never persisted and
  every hourly run re-redded as "new" (runs 29116327911/29116722923). **Why:** the
  post-step cache save is skipped on failure; any alert-once design whose alert reds
  the run cannot key off cache-carried state. **How to apply:** key alert-once behavior
  off state that survives a red run (an open GitHub issue, a committed file), and let
  the standing-failure path exit 0 so the cache resumes carrying run-over-run state.

- **Validate a gate invariant against the full tour CALENDAR, not the events in flight
  the week it ships.** (2026-07-10) The "real draw must be a power of two" gate check
  shipped 2026-07-08 during Wimbledon (128 — passes) and blocked the first deploy that
  saw a standard ATP-250 bye-draw (Gstaad, 28 entrants in a 32-bracket) two days later.
  **Why:** tour draws are 28/48/56/96 as often as they are powers of two — byes are the
  norm outside slams; an invariant tested only against this week's data is overfit to
  this week. **How to apply:** before landing a blocking invariant on event structure,
  enumerate the legitimate value set across the whole season (slams, Masters, 500s,
  250s, both tours) and encode that set, keeping the failure signature (129, 29, 27)
  outside it; a gate false-positive silently freezes deploys until someone reads CI.

- **Next 16/Turbopack drops SOME same-line spaces after JSX interpolations — put {" "}
  between any expression/element and following prose, and verify the RENDERED text.**
  (2026-07-10, /method detail sections) `value for the {tour.toUpperCase()} tour` rendered
  "ATPtour", `<Num v={e.inactDays} /> days` rendered "400days", `×<Num v={e.xsurf} /> of the`
  rendered "0.27of the" — while byte-identical patterns in the SAME file (`{fmt(x)} rounds`,
  `<Num v={c.nBag} /> seed-varied`) kept their space, so the compiler behavior is not
  predictable per-pattern and source inspection proves nothing. Two rules: (1) after any
  `{expr}`/`<El />` followed by a space + word, write the space as explicit {" "} (an
  expression the compiler can't collapse); (2) screenshots and substring checks both miss
  this ("40rounds against" contains "rounds against") — scan the rendered DOM for glue,
  e.g. innerHTML `/[A-Za-z0-9)]<!-- -->[a-z]{2}/` (React's SSR comment markers sit exactly
  at interpolation boundaries) plus an innerText `\d(days|rounds|…)` word-glue regex.

- **A URL↔state bridge must apply URL→state only on NAVIGATION, and a client
  "redirect page" must hard-navigate.** (2026-07-09, tour-in-URL + /upcoming→/results;
  both caught by Playwright E2E, invisible to unit tests/build.) (1) An effect that
  reconciles `useSearchParams` with context state fires on BOTH kinds of change; on a
  toggle it runs with the state updated but the params still stale (router.replace
  hasn't landed), and "param ≠ state ⇒ apply param" silently reverts the user's click.
  Fix shape: ref-track the previous search string and apply URL→state only when it
  actually changed (`lib/tour.tsx` TourUrlBridge); state→URL canonicalization can stay
  unconditional. (2) A moved-route stub using `router.replace` races any other
  mount-time `router.replace` (here: the tour bridge) and the last one wins — the
  redirect just doesn't happen. A legacy URL is semantically a 301: use base-path-aware
  `window.location.replace` and no soft-nav can clobber it.

- **A frozen-field policy needs a VALIDITY predicate, not a kind check — and every
  "who quotes when" race is a leak vector.** (2026-07-09, Kalshi ledger audit: 25
  rows/tour scored in-play Wimbledon prints, 6 ATP rows scored the SETTLED book, one
  market scored an 18-day-old result of the same pair; net effect: ATP headline
  −0.0015→+0.0064, WTA −0.0260→−0.0226, and the whole ATP fav-0.9+ "anomaly" was the
  leak.) The traps, each now pinned by a test + a blocking health invariant:
  (1) *Pending-race freeze*: hourly snapshots freeze an occurrence-anchored (T-5)
  candle; a row written pending then matched later skipped the 08:00 re-anchor because
  the skip set asked "is a candle frozen?" not "is the frozen quote valid for THIS
  row's result_date?" (`_scoring_quote_ok`). The requoter is the only writer allowed to
  override a frozen price (`_requoted` mark) — and it must use the match identity that
  SURVIVES the merge (frozen prior first), else a transient results-source gap strands
  the bad quote. (2) *`include_latest_before_start` is a leak vector*: when a result
  source dates a match day+1, the 08:00 window is empty and the API's synthetic carry
  imports the settled book (0.995 on the winner, "confirmed" 6/6). A carry candle at/
  before the window start with an extreme mid is a settled print, never a line — reject
  at selection (`EXTREME_CARRY_MID`). (3) *A wide join window admits stale rematches*:
  a market listed before its match binds the pair's previous result if it's the only
  in-window candidate, and `_FROZEN_MATCH` locks it forever. Durable fix is layered:
  one result row = one ticker (claims), far-forward candidates must agree with the
  market's parsed tournament (the tiebreaker becomes a validator), Kalshi's own
  settlement contradicting the join is an auto-veto, and healing unfreezes only
  OBJECTIVELY wrong rows (settlement disagreement, double-claim) so archive-dated
  joins stay stable. (4) *Pooled QA hides month-local leaks*: the t30 sentinel's
  pooled p95 (0.010) looked clean while July-only p95 was 0.208 — slice sentinels by
  month/anchor-class; and a sensitivity line that can never fire (retirements: all
  such rows lack p_model by construction) must say so itself.

- **Odds-source coverage can silently truncate an eval window — census the books per era,
  don't trust the frame.** (2026-07-09, market.json) tennis-data stopped carrying Pinnacle
  (PSW/PSL) after 2026-01-13 (ATP 71/1466 rows in 2026, WTA 101/1422, none later), and
  `eval/compare.py` picked ONE book frame-wide ("ps" if the column exists anywhere) then
  `dropna` — so the "2020+ validation" closing-line card gained its last row mid-January and
  sat frozen for ~6 months while rendering next to a May–July Kalshi card. Fix shape: (1)
  coalesce the line PER ROW (ps→b365→avg, same de-vig) and export a per-year `sources.byYear`
  census + derived honest `label` that the UI renders verbatim; (2) export `oosEnd` vs
  `lastMatchedDate` and flag a >60d gap in `health.py` (ADVISORY, not gate-blocking — odds
  are a benchmark, never a deploy dependency); (3) an era-matched `recent` block (trailing
  90d paired Δ±SE) so a 2-month market window is never eyeballed against a 6.5-year average.
  Rules: an eval joined to an external source must state IN ITS PAYLOAD which source backed
  each era — a benchmark labeled "Pinnacle" must fail loudly the day Pinnacle vanishes; and
  benchmark labels in page copy derive from that payload, never hardcoded.

- **A Δ-metric card must compute the sign its own caption promises — and match its
  neighbours' convention.** (2026-07-09, /scorecard) The "Vs Pinnacle (Δ log-loss)" hero
  computed `model − market` while the page header promised "positive Δ means the model was
  sharper" and the adjacent Kalshi card + forest plot used `market − model` — so the card
  showed +0.0018/+0.0097, silently claiming a win over Pinnacle's close that the data
  contradicts. Same audit: its sub cited the full matched n (17,761) for a metric scored
  only on the 2020+ validation slice (10,042), and the eyebrow said "Ten years" over the
  same slice. Rule: every signed comparison surface states one convention, derives its
  n/window labels from the same payload slice it renders (`stack.val`, `stack.fit.valStart`),
  and gets checked against the neighbouring cards' sign at review.

- **Public method-page copy hardcodes tuned constants and cadences — re-verify it after
  adoptions.** (2026-07-09) `/method` still said "blended ~50/50" and "weekly refresh" while
  config.py carried surface_blend 0.63/0.62 and refresh.yml ran hourly QUICK + daily FULL; the
  page text was last touched 2026-07-01 and a week of adoptions invalidated four of its six
  sections (blend ratio, 6-vs-8 style dims, combiner input list, cadence). Rule: any adoption
  that changes a headline fact (blend weights, feature families, style dimensions, refresh
  cadence) includes a pass over `web/app/method/page.tsx` STEPS; phrase tuned values as
  "currently about X" so they read as snapshots, not spec.

- **Live-event surface has ONE authoritative source (Wikipedia's main article) and must be
  fixed at the loader source, not the prediction points.** (2026-07-08, surface backfill) ESPN
  carries no surface, so it's re-derived as archive-by-name -> `_MONTH_SURFACE` (July="Grass").
  New/sponsor-renamed clay events miss the archive ("Nordea Open" is archived as city "Bastad" —
  zero shared substring; "Grand Est Open 88" is brand-new) and were mislabeled Grass. Three
  non-obvious traps fixing it: (1) **The `surface` infobox lives ONLY on the main tournament
  article ("2026 Swedish Open"), never the "– Singles" draw sub-article `draws_wiki.fetch_draw`
  reads** — surface capture is a SEPARATE resolution (own `event_surface` + `wiki_surface.json`
  cache), and it works by sponsor name even when the gendered singles draw doesn't resolve. (2)
  **Don't gate `event_surface` on the infobox NAME** (`"infobox tennis"`): Grand Slam articles use
  a differently-named infobox, so that gate returns None for Wimbledon even though `surface=[[Grass
  court…` parses fine — a parseable `surface=[[…court]]` field IS the tennis-tournament signal;
  bound wrong-event risk with year-in-title + a distinctive body anchor instead. (3) **Correct
  `surface_b` at the SOURCE in `results.clean` (wiki tier between the archive backfill and the
  month fallback), not only in the prediction helpers** — `project_tournament` reads `surface_b`
  directly, and once an event goes live the ESPN rows carry month-guessed Grass with no provenance,
  which `event_attrs`/`_archive_attrs` return as if authoritative, so a prediction-only fix silently
  regresses to Grass mid-tournament. `resolve_surface` (archive -> wiki cache -> month) lives in a
  leaf `data/surface.py` importing only config, so the offline loader stays network-free. Builds on
  the [[future-proof-no-quick-fixes]] no-hardcoded-table rule.

- **ESPN can't give a full draw at release — Wikipedia can; three traps when adding it.**
  (2026-07-08, `data/draws_wiki.py`) ESPN's scoreboard AND core API fill a pre-created
  bracket with real names only via the daily order-of-play (R1 slots are `"Bye"`/athlete
  `id:0` until then), so no ESPN endpoint carries a complete draw at release — draw
  acquisition needs a separate source. Wikipedia's MediaWiki API posts the complete ORDERED
  draw the day it's released (verified down to ATP-250). Traps: (1) **Parse `-Compact-`
  section templates in document order** — the full draw is split across `{N}TeamBracket-
  Compact-Tennis{3|5}[-Byes]` section templates (8×16 for a slam) plus small non-compact
  summary brackets you MUST ignore; concatenating the compact sections' first round in doc
  order rebuilds the real bracket (which pins every downstream half — the thing ESPN's
  `match_num`-less feed can't). (2) **Byes are sparse in RD1** — a seed with a bye has NO
  `RD1-team` leaf; it rides in `RD2-team{k}` (both leaves of match k absent → seat that RD2
  seed against a None). (3) **Title resolution MUST gate on year + a distinctive anchor
  token + exact tour/gender** — a naive "`<year> <event> singles`" search silently resolves
  to LAST year's draw (not posted yet → falls through) or the WRONG tour's draw of a combined
  event (e.g. Winston-Salem→Australian Open, ATP Eastbourne→Women's singles). Consume it
  order-preserving: `sim/draws.advance_slots` collapses the wiki bracket by ESPN eliminations
  keeping adjacency — do NOT round-trip through `live_draw` (it strength-seeds units and
  re-loses the downstream halves). Builds on [[future-proof-no-quick-fixes]] and the live-draw
  lesson below.

- **A new data-backed web page is a 6-part contract; miss one and it silently
  half-works.** (2026-07-08, /schedule) (1) add a `build_*` in `model/export.py` +
  a `_write(tour, "X.json", ...)` line in `export_all` — it's auto-mirrored to
  `web/public/data/<tour>/` by `pipeline._mirror` and regenerated on full AND
  `--quick` runs; it's overwrite-only output (like fixtures.json), so NO refresh.yml
  persistence step (that's only for append-only state like forecast_log). (2)
  `web/public/data/` is gitignored + machine-generated, so generate the JSON locally
  from the saved model (`TennisPredictor.load(tour)` + `load_matches(tour)` + the
  builder) or the dev page hangs on `<Loading/>`. (3) `page.tsx` is `"use client"` +
  `useData<T>("X.json")` — the global tour context auto-switches ATP/WTA, the page
  does nothing. (4) client pages can't export `metadata`, so add a sibling server
  `layout.tsx` (`export const metadata = pageMetadata(slug)`) AND a `PAGE_META` entry
  in `web/lib/seo.ts`. (5) a `Nav.tsx` GROUPS item — `isActive` uses
  `path.startsWith`, so a slug that prefixes another (`/predictions` vs `/predict`)
  double-highlights; pick a non-prefix slug. (6) handle empty/missing data
  (`useData` sets `data=null`/`error`) with an explicit empty state. Reuse `CallCard`
  (two players + prob bars, `tone` for result vs projection), `pct`, `surfaceColor`.
  See [[future-proof-no-quick-fixes]].

- **Live tournament reach-odds must be seated on the ACTUAL draw, not a rating
  re-seed.** (2026-07-08) The live scorecard showed Sinner 97% + Djokovic 55% to
  reach the same final while they actually met in the SF (must sum to 100%). Cause:
  `project_field` → `standard_seed_draw` re-seeded survivors into a synthetic
  1v4/2v3 bracket. Field-strength dominates *champion* odds on a full draw, so this
  looked harmless — but it makes the round-by-round SF/F reach table nonsense, most
  visibly once the draw is small and the real pairings are known. The real matchups
  were already on disk: `data/live.parse_upcoming` writes them to `upcoming.csv`
  (and `eval/track` reads it), the projector just never opened the file. Fix:
  `sim/draws.live_draw` seats survivors by their real current-round matchups (pairs
  adjacent; already-advanced players get a bye into the next round), seeding only
  the genuinely-unknown downstream pairings; completed events keep full-field
  seeding (that path is a deliberate pre-tournament hypothetical). Rule: any
  live/forecast surface that shows per-round structure must consume the real draw
  from `upcoming.csv`; a "sums to >100% across two players who face each other" is
  the canary. See [[plans-adapt-to-landed-code]].

- **A combiner feature that adds no new state is a pre-paid loss: budget a
  ~0.0003 LL capacity toll for any new column.** (2026-07-06, round R2) Adding
  `elo_osgap_diff` — pure algebra of two columns already in the frame — measured
  d_val −0.00038 (ATP) / −0.00032 (WTA) with no compensating tune gain; the
  E1 box-score rejection had the same shape. Even the genuinely-new-state
  surface-count gate lost more to the toll + overfit than its signal was worth.
  Rule: when costing a feature idea, its expected validation signal must clear
  the toll, not zero; pure recombinations of existing columns never qualify
  (trees already approximate them), so spend those Tier-2 slots elsewhere.

- **The tuning feature cache is regime/schema-keyed, not param-keyed.** (2026-07-06)
  After adopting new FeatureParams (fp1), the cached `_features_wta*.pkl` still
  carried pre-adoption feature values; the next `group=xgb` sweep would have tuned
  the combiner against a stale frame and measured deltas off a phantom baseline.
  Production is immune (the pipeline builds frames fresh each run) — only
  `load_or_build_features` consumers are exposed. Rule: after adopting any parameter
  that changes recorded feature values, delete `_features_{tour}*.pkl` before the
  next cache-reading sweep; frame-building groups (feat/elo/point) are immune
  because they rebuild per trial.

- **A data-ingestion experiment is two experiments; separate them or the gate
  measures the wrong thing.** (2026-07-05) Ingesting challengers "fully" (rows in
  the walks AND the combiner) produced +0.0087 tune LL but failed validation with
  ±0.03 per-year swings — the challenger-dominated row mix destabilized fold
  training and prior-season calibration. The ratings-only variant (walks see the
  rows, combiner never does) passed at 7.6 SE with 17/17 years positive and was
  adopted. Rules: (1) score both arms on the IDENTICAL main-draw eval set — new
  rows must never enter the scored set or d measures eval drift, not model
  quality; (2) when a data addition shifts the training distribution, always run
  a ratings-only / states-only variant before concluding anything from the full
  variant; (3) per-year paired d is the instability tripwire — a real prior
  improvement lifts every year a little (17/17 positive), a distribution artifact
  flaps year-to-year at ±10 SE in both directions.

- **Re-read the git tip immediately before finalizing any plan or doc built from
  exploration.** (2026-07-05) A README-refresh plan was drafted from subagent
  exploration of the repo state, but three commits (including an adopted model
  change that moved the headline Brier numbers) landed between exploration and
  the final plan — the plan quoted stale metrics until the user said "check the
  latest commits". Rule: exploration results have a timestamp; before writing
  conclusions that cite repo facts (metrics, features, file lists), run
  `git log` again and diff against the commits the exploration actually saw.

- **Verify a source's naming convention per file, not per format.** (2026-07-02)
  "XXX vs YYY" tie names are host-first in the ATP Davis Cup file but carry NO
  venue order in the WTA Fed Cup file (single-venue weeks; arbitrary/winner-first
  ordering) — the same regex, trusted uniformly, silently mislabeled ~8% of WTA
  training rows with a flag that partially encoded outcomes. Rule: before deriving
  a feature from a naming convention, verify it against known ground truth in EACH
  source file it will touch (a handful of known-venue rows per file suffices).

- **Never include the current estimate in the residual it learns from.** (2026-07-02)
  The event-speed accumulator measured residuals against an expectation that
  already contained the current offset — the fixed point of that recursion is
  HALF the true effect, independent of the shrinkage constant. Rule: residual
  accumulators learn against the estimate-free expectation; write a unit test
  that pins the exact converged value, not just the direction.

- **A feature that walks can't be adopted unless the pickled state can replay
  it.** (2026-07-02) Two of today's knobs (event offsets, Elo home bonus) baked
  venue effects into recorded training features while the saved state had no way
  to reproduce them at inference — a parity break invisible to the walk-forward
  arbiter (both sides come from the same pass) that only bites production. Rule:
  every new walk-time signal needs its prediction-time mirror (state method +
  parity test) in the same commit, or must be recorded venue/context-free.

- **Pin dependencies to the environment that owns the production artifacts, not the
  dev machine.** (2026-07-02) Pinning requirements.txt from a local `pip freeze`
  downgraded CI (sklearn 1.9.0 → 1.5.2) under a cached predictor.pkl pickled at
  1.9.0 — the quick deploy crashed on unpickle (`LogisticRegression` lost
  `multi_class`). Rule: before pinning, read the versions out of the last
  successful CI run's install log; upgrade local to match, never the reverse.
  Cross-version pickle compatibility is the constraint, not "what my venv has".

- **A lockfile regenerated on one OS can be incomplete for another.** (2026-07-02)
  `npm install` on Windows wrote a package-lock.json missing Linux-side optional
  native deps (@emnapi/*); CI's `npm ci` refuses it. Rule: after adding a dep, run
  `npm install --package-lock-only` (computes the full cross-platform ideal tree)
  and verify with `npm ci` before committing the lockfile.

- **An API field's semantics can mutate over an object's lifecycle — validate on
  the SETTLED objects you'll actually score, not the live ones you explored.**
  (2026-07-07) Kalshi's `occurrence_datetime` looked like a clean scheduled-start
  on open markets, but it is a draw-time placeholder for smaller events (actual
  play trailed it by 3–7 days for ~215/955 ATP events) AND on settled markets it
  drifts to ~the determination time (close_time lands seconds after it) — so
  "quote at T−5 before occurrence" silently scored final in-play prices for part
  of the set. The pre-registered leak sentinel (a second quote 30 min earlier,
  p95 |Δ| = 0.23) is what caught it. Rules: (1) join windows against market
  timestamps must tolerate play up to ~a week later (ledger uses −8..+21 vs
  result dates); (2) anchor scoring quotes only to timestamps YOU own — the
  ledger uses 08:00 UTC on the result row's date, provably pre-match for this
  era's event footprint and immune to upstream mutation; (3) always ship a
  cheap redundant-measurement sentinel with any external price/time source.

- **A live feed's round label is draw-relative — resolve it against draw size, not
  the label/number alone.** (2026-07-08) ESPN's tennis scoreboard tags main-draw
  rounds "Round 1".."Round 4" with numeric `round.id` 1-4 (start-anchored,
  left-aligned) and always QF/SF/F = ids 5/6/7. So "Round 1" is R128 at a 128-draw
  Slam but R32 at a 32-draw event — the number alone is meaningless. The old
  name-only `_round_label` matched none of "Round N" and fell through to a generic
  `return "R64"`, so every Slam R128/R32/R16 match shipped as R64 (Wimbledon
  fixtures showed 120 matches as "R64"). Fix: `_draw_size` per event grouping =
  `next_pow2(2 x opening-round match count)` (the opening round ships complete when
  the draw drops, and pow2-rounding absorbs byes), then map numbered id `r` to
  `draw >> (r-1)`; QF/SF/F stay name-anchored; `_round_label` kept only as an
  id-less fallback. Rules: (1) map live rounds against draw size, computed per
  event, never from the bare round label; (2) anchor the named rounds (QF/SF/F) by
  their fixed marker, not by counting — the numbered-round<->QF id gap is not
  constant across draw sizes; (3) any keyword round map needs its fallback proven
  against the SOURCE's real vocabulary (ESPN sends "Round 4", not the
  documented-looking "Round of 16"/"4th Round").

- **Python `json.dump` emits a bare `NaN`, which the browser's strict `JSON.parse`
  REJECTS — one non-finite float blanks a whole page, and every Python-side check
  passes it.** (2026-07-09, WTA /player + /style) A scoreless WTA match left
  `"score": NaN` in `profiles.json`. Python's `json.load` accepts `NaN`/`Infinity` by
  default, so a local `python -c json.load` AND the health gate (reading with plain
  `json.loads`) both saw a valid file — but the frontend `useData` → `r.json()` threw
  on the invalid token, leaving `data` null so the page rendered a blank body between
  header and footer (looks "not loading", not errored). ATP was clean only by luck (no
  scoreless top-200 recent match). Three-part durable fix: (1) sanitise at the single
  write seam `export._write` — `_finite()` recursively maps non-finite floats → `None`
  (`null`), so no field/file/builder can ship the token (`build_fixtures` carried the
  same latent `"score": r.score`); (2) the gate now parses web JSON with
  `json.loads(..., parse_constant=<raise>)` in `health.py:read_outputs`, so a NaN file
  lands in `corrupt` → "present but unparseable", mirroring the browser; (3) both pages
  degrade to an explicit empty state on `!data`, never a blank body. Rules: emit web
  JSON only through a seam that strips non-finite floats; NEVER validate shipped JSON
  with Python's lenient `json.load` — use a browser-equivalent STRICT parser, since the
  two disagree exactly on NaN/Infinity. Extends the health-gate "catch the shipped-wrong
  class, not just the bug" rule. See [[future-proof-no-quick-fixes]].

- **A correctness check that runs AFTER deploy can't stop a wrong deploy — gate before, on
  every mode.** (2026-07-09, cross-session retrospective) `data/health.py` already encoded the
  right invariants (reach-odds monotonic, `aliveCount<=drawSize`, real draw a power of two, a
  live event can't name a champion, placeholder leaks, matrix antisymmetry), but `refresh.yml`
  ran it `if mode==full` and LAST — after `deploy-pages`, without `--strict`. So a wrong build
  (e.g. the live-draw pairing bug: two same-half survivors both ~100% to reach the final)
  shipped, and every quick/push deploy skipped the check entirely; the USER was the gate. Fix: a
  `--gate` mode (produced-output integrity ONLY, `prev=None` so source freshness / run-over-run
  deltas stay best-effort; never writes health.json) wired BEFORE build/deploy on BOTH full and
  quick, with `_gate_blocks()` splitting provably-wrong (block) from thin/quirky-feed (advisory,
  e.g. a naming split or a quiet week) so the gate can't freeze the site over cosmetics. A
  failure keeps the last good deploy live — stale-but-correct beats fresh-wrong. Rule: when the
  user catches a "shipped-wrong" class, the durable fix is a new `output_problems()` invariant +
  `test_health.py` case, not just patching the one bug. See [[future-proof-no-quick-fixes]].

- **`cancel-in-progress: true` on the deploy concurrency group silently drops changes.**
  (2026-07-09) The `pages` group cancelled any in-flight deploy when a scheduled refresh or a
  concurrent push arrived, so the run carrying a change was killed mid-flight and never shipped —
  repeatedly misread as a "transient Pages hiccup" and worked around with manual re-dispatch
  (~100 turns burned across sessions). Set `cancel-in-progress: false` (GitHub's own Pages-deploy
  default): the in-progress run finishes; GitHub queues only the latest superseding run and skips
  intermediate ones. Rule: a deploy job's concurrency group must never cancel in-progress.

- **Duplicated construction sites drift: production shipped WTA pickles with fp=None.**
  (2026-07-09) `fit_predictor()` passed `fp=feat_params_for(tour)` to `TennisPredictor`, but
  `pipeline.build_tour` reimplemented the same construction inline and omitted it — so every
  shipped `predictor.pkl` carried `fp=None` and inference fell back to config defaults (WTA:
  layoff 360→120d, peak age 24→26.5) while the combiner was trained on tuned frames. Invisible
  to the walk-forward arbiter (it scores frames, never a `TennisPredictor`) and to the health
  gate (the JSON stays self-consistent — just built from the wrong thresholds). Fix: derive the
  invariant IN the constructor (`fp = fp if fp is not None else feat_params_for(tour)`) so no
  call site can forget it, and drop the redundant explicit arg — leaving it would re-signal that
  callers must remember. `_predictor_current` (quick-path guard) now also compares the pickle's
  `_fp` to the tour's current config and rebuilds on drift, healing shipped-bad pickles within
  an hour. Rules: derive invariants in the constructor, not at call sites; a staleness guard
  must check every config a pickle bakes in (schema AND params), not just the crash-prone part.

- **An `if: always()` alert step must distinguish `skipped` from `failure`.**
  (2026-07-21) `Report deploy health` branched on `if [ "$OUTCOME" = "success" ]` and treated
  everything else as a live-serving failure. But a step outcome is `skipped`/`cancelled`, not
  `failure`, whenever an upstream step dies — so when the `--strict` data download failed in run
  29812819613, the deploy never happened, `verifydeploy` was skipped, and the alert filed a
  "the deploy may be serving stale/broken content" issue (#8) against a site that was serving
  fine. Worse, it pointed diagnosis at Firebase instead of the download step that actually broke,
  and shipped an empty log block ("no verify-deploy.log captured") because the verifier never ran
  to write one. Fix: an explicit guard — only `success` (recovery) and `failure` (alert) touch the
  issue; anything else exits 0 without even querying `gh`, leaving an open issue standing since
  recovery we never verified can't be claimed. Rules: with `if: always()`, enumerate the outcomes
  you handle and no-op the rest — never let `!= success` mean "broken"; and an alert must name the
  thing it actually observed, or it costs more diagnosis time than it saves.
