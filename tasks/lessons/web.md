# Web app

Next.js rendering, URL/state, page contracts, public copy.

Indexed in [`../lessons.md`](../lessons.md).

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
