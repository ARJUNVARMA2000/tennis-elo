# Web app

Next.js rendering, URL/state, page contracts, public copy.

Indexed in [`../lessons.md`](../lessons.md).

- **A hero may change emphasis, never event membership — reserve single-event layouts for
  truly dominant weeks and put the complete, counted alternative-event disclosure above the
  fold.** (2026-07-28, ATP 500 hid its concurrent ATP 250) The 500-level hero change reused a
  Slam-only page branch whose membership rule was “hero plus everything else collapsed below
  the long forecast and Up Next.” The ATP 250 remained correct in `tournaments.json` but looked
  missing to the user. Do not derive visibility as an accidental side effect of feature
  selection. One pure view contract must sort every event by prestige and partition without
  loss: 1000-and-above may take the hero, with every remainder named by an above-the-fold
  disclosure; 500-and-below stays a complete multi-card grid. Pin both simultaneous-tier cases
  in tests and verify the disclosure closed and open in the rendered page.

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

- **Card content must not be fused to hero layout.** (2026-07-29, reach odds disappeared
  from every live event) Round-by-round reach data existed on every tournament projection,
  but only the single hero renderer knew how to display it. Tightening hero eligibility to
  protect concurrent events therefore removed the feature from the whole board during a
  500-level week. Hero selection should decide emphasis and page composition only. Extract
  reusable content primitives first, then apply the content rule independently at the card
  tier where it belongs; here 500-and-above cards share the same reach rows as the Slam hero,
  while `HERO_MAX_TIER_RANK` remains a pure layout threshold. Pin both halves in tests: a 500
  card emits reach columns, a 250 keeps its compact title-odds bars, and hero/concurrency
  membership assertions remain unchanged.

- **A current board must rank lifecycle before prestige.** (2026-07-29, completed Wimbledon
  above live DC Open) Prestige is a useful tie-breaker inside a comparable cohort, but it is
  not a freshness signal. Sorting the whole recent-event payload by tier alone made a finished
  Slam look current long after its explicit hero linger expired. For a current-events surface,
  group by lifecycle first (`live → upcoming → completed`), then rank by prestige, and preserve
  producer order for equal status/tier so recency remains stable. Pin the contract with one
  mixed-status regression; same-status tests alone cannot expose the stale-event promotion.

- **Card detail follows lifecycle within a layout, while the hero controls supporting-event
  density.** (2026-07-29, live Mifel had less information than live DC Open) If peer active
  events share the grid, each gets the same available round-by-round reach data regardless of
  tier. During a Grand Slam/1000 hero week, keep the marquee event full-width and render every
  concurrent lower-tier event visibly after it as a compact title-odds card. Do not hide those
  cards in a disclosure or let tier suppress useful data during an ordinary multi-event week.

- **Partition lifecycle before choosing a hero; prestige only compares events in the same
  cohort.** (2026-08-01, upcoming Toronto draw displaced live Washington) Sorting the payload
  live-first did not protect the page because hero selection independently filtered for 1000+
  events, allowing an upcoming draw to become the main surface while matches were live. Build
  explicit cohorts first: live events own the primary surface; upcoming events are compact while
  anything is live and may earn a hero only when the live cohort is empty. Ordinary completed
  events leave the current page immediately; completed Grand Slams, Finals, 1000s, and Olympics
  remain compact for seven days, never as the hero. Test the mixed lifecycle payload, not each
  status in isolation.

- **Primary ordering and information depth are separate decisions.** (2026-08-01, Toronto lost
  its useful forecast when live play took priority) Keeping a live event first does not require
  reducing the next marquee draw to a title-only card. While anything is live, upcoming Grand
  Slams, Tour Finals, 1000s, and Olympics follow the live surface with the complete hero-style
  round-by-round table; only lower-tier upcoming events stay compact. Encode this as a tier rule,
  never a one-off tournament-name exception, so the same presentation applies to future events.

- **Axis-only overflow on `body` can create a hidden scroll container; body overscroll containment
  then swallows document wheel input.** (2026-08-15, every long route stopped responding to
  wheel/trackpad gestures) `overflow-x: hidden` makes the body's computed `overflow-y` become
  `auto`. The body grew to its content instead of owning the vertical scroll range, but
  `overscroll-behavior: none` stopped the wheel delta from chaining to the root scroller. Keep
  viewport clipping/overscroll policy on `html`, leave body out of the scroll-container chain, and
  exercise real wheel input in browser verification; CSS substring assertions encoded the broken
  combination as an invariant. At narrow widths, also assert both root and body scroll widths —
  root clipping can hide an over-wide grid child without making the clipped content reachable.

- **Two independently refreshed lifecycle surfaces need one shared state, and their join still
  requires stable event identity.** (2026-08-19, a live Cincinnati match also appeared under
  “Next up” with stale pre-match odds) The live ticker polled ESPN every minute inside its own
  component while the surrounding page rendered an hourly `upcoming.json`; neither could see the
  other's state. Preserve ESPN's event id in the browser parser, lift the poll so both consumers
  share it, and exclude only the same `espnId` plus the same unordered normalized player pair.
  Player names alone are insufficient because the event registry's identity contract still
  applies. Pin the pure overlap predicate and both deployed route markers: a component-level live
  badge and a scheduled card can each be correct while their combined page is contradictory.

- **A query-only URL mirror must survive the reverse transition, not just the first toggle.**
  (2026-08-24, WTA -> ATP left `?tour=wta` shareably attached to an ATP page) The context state
  and saved preference both changed, but a second `router.replace` that removed the default-tour
  query was lost while the prior replacement settled. Unit tests of the query helper and one-way
  component behavior stayed green because neither exercised two real client transitions. When a
  control already owns the local state, mirror its canonical query synchronously through the
  framework-observed History API. Do not pass the framework's own internal history marker (that
  deliberately suppresses observation), and preserve the browser pathname/base path plus hash.
  Browser-test both directions and, after pending work settles, assert active control, rendered
  dataset, and URL all agree after A -> B -> A; any one of the three can pass while a copied link or
  visible page is still wrong.

- **Fixture-specific browser assertions need an explicit fixture capability, not a shared verifier
  assumption.** (2026-08-24, Round 3 browser-smoke review) The CI smoke strengthened the general
  verifier by hard-coding its synthetic ATP/WTA player names, so an ordinary developer verification
  against real generated data failed the same route. **How to apply:** keep generic state, URL,
  accessibility, and geometry checks active everywhere; enable synthetic identity assertions only
  when the runner explicitly declares both offline mode and fixture data. Share fixture identities
  between writer and assertion code, declare which fixture routes are intentionally long instead
  of requiring incidental content height everywhere, and include a negative control proving
  default verification contains no fixture-name dependency.
