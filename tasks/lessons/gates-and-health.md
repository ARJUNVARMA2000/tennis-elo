# Gates & health checks

Designing and placing the invariants in `health.py`; what a gate can and cannot see.

Indexed in [`../lessons.md`](../lessons.md).

- **A model-population exclusion must not erase factual event lifecycle evidence; preserve an
  exact complementary event view and join it only at factual event consumers.** (2026-08-04,
  WTA 125 cards stuck upcoming) The model correctly withheld ESPN's WTA 125 results to enforce
  `INCLUDE_WTA_125=False`, then the exporter passed that same filtered dataframe to tournament
  projection and independent coverage. The rating policy consequently hid settled facts from
  the board: started events remained upcoming and completed finals had no champion. The existing
  health invariant caught the bad artifacts; weakening it would have hidden the producer bug.
  The durable split is an exact post-dedup complementary partition carried beside the eligible
  model frame, cleaned into an event-facing view only where cards and coverage are built. Never
  re-read the raw source independently at each consumer: that bypasses source priority,
  de-duplication, inherited stable IDs, and policy audit counts. Test both halves together—the
  excluded row is absent from model state and the same row's final completes the event card—then
  rebuild real artifacts to prove profiles, fixtures, and model counts did not absorb it.

- **Validating every item that EXISTS cannot detect an item that vanished — derive expected
  membership independently, then carry the same keys through build, UI, and live serving.**
  (2026-07-28, begun-event coverage) `output_problems()` had extensive structural checks for
  every tournament card and still could not detect one missing event: if the projector caught
  an exception, applied its top-player filter, or stopped at its 14-event cap, the remaining
  cards were internally valid and the gate passed. The fix is an independent manifest built
  from pre-projection facts (real knockout results or begun real-player matchups), with one
  explicit key carried into every card. The pre-upload gate checks expected key -> exactly one
  card; the UI partition proves it preserves the payload set; `health.json` carries the built
  membership so the post-deploy verifier can compare the actual live payload. An important
  identity trap appeared on the first real census: broad event calendars overlap and players
  can move after an early loss, so date overlap plus two shared names merged Wimbledon into the
  following week's events. For id-less cross-source evidence, require the same real matchup on
  overlapping source-observed dates; calendar dates enrich display/retention but never prove a
  join. Search remains downstream of the deterministic failure and cannot define membership.

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

- **Two timestamps that look like one: "when was this written" vs "when was this trained".**
  (2026-07-25) The daily retrain was dead for five days and nothing noticed, because
  `HEALTH_MAX_BUILD_AGE_DAYS` watches `meta.lastUpdated` — which `build_meta` stamps with
  `now()` on EVERY export, including the hourly quick refresh that deliberately reuses the
  saved `predictor.pkl`. So the freshest possible build stamp sat on top of an ever-older
  model, and the check could not fire even in principle. Only the daily full run's own red
  revealed it, and only because someone read the log. Fix: export `modelTrainedAt` alongside
  `lastUpdated`, stamped in `TennisPredictor.__init__` so it rides inside the pickle (a file
  mtime would be laundered by the `actions/cache` restore that hands the quick run its
  model), and flag it ADVISORY — a stale model still forecasts, so blocking the deploy would
  only strand the site on an older build. Rules: when a fast path and a slow path both write
  the same artifact, a freshness check on that artifact measures the FAST path and tells you
  nothing about the slow one — give the slow path its own stamp; and a staleness check is
  only real if a *human* is reached, so verify it lands in the existing alert flow (here:
  output problems fold into `health.json ok`, which is what `report-data-health.sh` reads).
  See [[future-proof-no-quick-fixes]] and the fp=None entry in
  [`model-research.md`](model-research.md) — the stamp is derived in the constructor for the
  same reason.

- **A flag derived from a value the producer then ROUNDS will eventually contradict the number
  it ships beside — and the gate, which sees only the file, is right to block.** (2026-07-27,
  16h of frozen deploys) `build_fixtures` wrote `"modelProb": round(p, 3)` but
  `"upset": bool(p < 0.5)` off the full-precision `p`. Any winner priced in `[0.4995, 0.5)`
  ships as `modelProb 0.5` with `upset true`; `output_problems` re-derives the flag as
  `modelProb < 0.5`, disagrees, and BLOCKS. Every scheduled run from 07:54Z on died there —
  including one whose 30-minute full retrain had already succeeded, so production served a
  two-day-old model while a fresh one sat in the cache. The gate was not wrong and needed no
  tolerance: a card reading "50.0%" next to an UPSET badge is wrong on its face. Note the
  asymmetry that forces the fix's direction — the producer can see both the raw and the
  rounded value, the gate can only ever see the rounded one, so the PRODUCER must move.
  `sim/bracket.py` had the identical latent bug at 4dp (and on the `1.0 - p` orientation for
  slot b), fixed in the same commit before it could fire. **Why:** this is the rounding case
  of the existing "derive both sides exactly as the code that produced them" rule in
  [`draws-and-live-events.md`](draws-and-live-events.md) — there the two sides used different
  *keys*, here they use different *precisions*, and precision is invisible in a diff.
  **How to apply:** when a payload carries both a number and a flag about that number, compute
  the flag from the rounded value being serialised, in the same expression the gate uses — make
  the invariant true by construction rather than true in practice. Grep for the shape
  `round(x, n)` and `x <` in one dict literal. Test the boundary explicitly: a unit test on
  clean 0.7/0.3 inputs passes forever and proves nothing.

- **A normaliser must be self-enforcing against the vocabulary its own gate checks, and a
  tour tag matched as a bare substring finds "men" inside "tournaMENts".** (2026-07-27, the
  ATP board shipping Generali Open as "WTA 125") Three sources speak three tier dialects —
  archive letter codes ("C", "G"), Wikipedia display prose ("ATP 250 series", "ATP Tour
  Masters 1000"), curated bare numbers ("250") — and all three reached cards verbatim, so one
  board carried "ATP 250 series", "ATP 250" and "C" as if they were different tiers. The
  cross-tour leak had two causes: `_parse_category` returned a LONE link unconditionally (an
  ATP lookup landing on the WTA article of a combined event took its tier), and its tour tags
  were plain substrings, so `("atp", "men")` matched `[[WTA 125 tournaments|WTA 125]]`
  outright. Fixes: word-boundary tags (`\bmen\b` correctly declines "women" AND
  "tournaments"), return None unless a link is ours or unambiguously neutral, and one
  `normalize_level` at the single `resolve_level` choke point. **Why the normaliser needs its
  own guard:** the first version turned a bare "125" into "ATP 125" — a tier that does not
  exist — which the gate would then reject as a string the normaliser itself produced. It now
  returns None for anything outside `LEVEL_VOCAB[tour]`, so "gate accepts what the producer
  emits" is true by construction rather than by agreement — the same shape as the upset-flag
  fix. **How to apply:** when a value must belong to a closed set, validate INSIDE the
  producer against that set, never just at the gate; match tour/gender tags on word
  boundaries; and treat "already resolved — keep it" in any cache as the first-capture trap it
  is (a category cached before the tour gate existed would have pinned the wrong tour's tier
  forever, exactly like the frozen draws in [`draws-and-live-events.md`](draws-and-live-events.md)).
  Related: [[future-proof-no-quick-fixes]].

- **An advisory that fires on live data turns the post-deploy sentinel red even when the gate
  passes — which is the check working, provided the finding is actionable.** (2026-07-28) A2
  added an advisory for an event whose tier never resolved. The very next deploy passed the
  gate and shipped, then the "Report data health" step filed issue #11 and reddened the job,
  because `health.json ok` is false whenever ANY problem exists — advisory or not. The single
  finding was real: "Mifel Tennis Open by Telcel Oppo" shares no distinctive token with its
  article ("Los Cabos Open"), so the anchor-gated title search could not bridge it and the
  event had no draw, no surface and no tier — it had been shipping as a generic "ATP Tour"
  card unnoticed. Fix was the two escape hatches that already exist for exactly this:
  `WIKI_TITLE_OVERRIDES` (which also unlocked its surface, Hard) and `EVENT_TIER_FALLBACK`
  (the article omits `category` entirely, same shape as Nordea Open). **How to apply:** budget
  for this when adding an advisory — it costs a red sentinel and an issue on the next run, so
  either fix what it finds in the same push or expect to. And distinguish the two failure
  surfaces before reacting: a red `refresh` run whose GATE lines are all warnings did NOT
  block a deploy; read which STEP failed before assuming the site is frozen.

- **A function-local import makes `monkeypatch.setattr(module, name, ...)` a SILENT no-op, and
  the test then quietly exercises the real thing.** (2026-07-28, three times in one session)
  This repo imports lazily inside functions all over — `load_upcoming` does
  `from ..data.draws_wiki import wiki_upcoming_rows`, `download_wiki_draws` does
  `from .live import fetch_events`, `build_tournaments` does `from ..eval.track import ...` —
  which is correct (it keeps the offline loaders importable without the network modules). But
  a lazy import re-resolves the name from ITS OWN module at call time, so patching the
  attribute on the *calling* module changes nothing at all. Both failures were invisible: one
  test asserted a tautology against an empty overlay and passed, and one silently called the
  live ESPN API on every run (giveaway: the file took 8.65s instead of 0.13s). **How to
  apply:** patch the module the name is imported FROM, never the one it is used in; and treat
  test wall-clock as a signal — a "fully offline" file that takes seconds is doing I/O, and a
  test that passes when you revert the fix is not a weak test, it is not a test. Both traps
  were caught only by the failing-first check ("N failed" ≠ the N I expected), which is the
  cheapest real verification in this repo.

- **A fallback that preserves membership must also preserve settled facts already present in
  its evidence, or a projector failure becomes a false missing-result incident.** (2026-07-28)
  The independent coverage manifest correctly restored three completed events that the
  projector could not safely simulate, but its presence-only shell discarded the `F` result
  already in the same rows. Production therefore deployed and passed exact-membership
  verification, then the unchanged completed-event health invariant correctly reddened the
  run because Wimbledon and Nordea appeared to have no champion. **How to apply:** degradation
  paths may omit derived projections, never source facts. Carry one non-conflicting final
  winner/runner-up through the independent manifest and into the fallback card; if sources
  conflict, preserve neither and let health report it rather than choosing. Test the fallback
  with a final-only group—the exact shape that makes the normal projector return no card.

- **A repair that runs only on the slow path is not an invariant: enforce safety after the
  fast path's frozen-field merge, across the whole retained artifact.** (2026-07-29, 36
  occurrence-time Kalshi candles re-entered the scorecard) The daily ledger requoter already
  did the correct thing: if it could not obtain the result day's 08:00 UTC candle, it degraded
  the row to `price_kind=none`. The new hourly path intentionally skipped historical network
  re-quotes, rebuilt the row from the occurrence-anchored snapshot cache, and resurrected the
  unsafe candle on its very next upsert. The frozen-field policy made the asymmetry worse: it
  protected a prior candle, but a prior `none` did not block the fresh candle. The health gate
  correctly stopped deployment. **Fix:** every upsert now validates the FINAL row after frozen
  fields merge, neutralizes unsafe completed-match prices without I/O, and scans the entire
  retained ledger so a bad committed row heals even when its snapshot has disappeared. A daily
  run can still replace the neutralized row with a validated morning quote. **How to apply:** a
  slow repair and a fast writer sharing one artifact need the same post-merge validity seam;
  sanitizing only the fresh input misses frozen state, while sanitizing only rows rebuilt this
  run misses retained history. Test all three transitions: degrade, fast refresh, later upgrade.

- **Freshness that only a per-EVENT check can see must not be left to a tour-wide aggregate —
  and when you write the limit down, check it against the sentence you justified it with.**
  (2026-08-06) The stale-live check existed and had the right idea: its own commit
  (`772e5d4`) argued "tour weeks run Mon-Sun, so a genuine in-progress event is never 3 days
  idle". But it shipped as `HEALTH_MAX_LIVE_EVENT_AGE_DAYS = 3` and fires ABOVE the limit, so
  it tolerated exactly the 3 idle days the rationale called impossible and would not have
  fired until day 4. Toronto stalled at 3 days and every gate stayed green. It also asserted a
  cause it could not observe — "its final never arrived, so it is stuck 'live'" — which is
  only one of the two ways a live card goes quiet; the other is a results feed that went blind
  mid-draw, and the message sent a reader looking in the wrong place. **How to apply:** a
  limit and the reasoning next to it are a single claim — write the boundary case out
  (`> 3` tolerates 3) and make sure the number encodes the sentence. And a gate message should
  state what was OBSERVED plus the possible causes, never pick one; the gate sees a date, not
  a reason. Prefer tightening an existing invariant to adding a second one with the same
  predicate and a different threshold.

- **A recency gate reads a MAX, so one corrupt future row disables it permanently — and
  sanitising the population at ingest is what stops the paired corruption check from ever
  seeing the cause.** (2026-08-07) WTA's fresh-overlay gate reported `fresh_age_days = -1078`
  against a 14-day limit and passed, every hour, for three weeks: the overlay still carried
  the Iasi final as `2029/7/20`, the same row as the 2026-07-25 incident, and `now - max` is
  negative forever while it is there. The `future_dates` check written in response to that
  very incident could not catch it either — it hangs off the MERGED `date_max`, which
  `_drop_impossible_dates` has already cleaned, so it structurally cannot see a bad row in a
  source file. Two checks, one blind because the quantity is signed and the other blind
  because it reads downstream of the filter. **How to apply:** a gate over `max(dates)` is
  only as trustworthy as the worst row in the file, so filter to credible rows for the AGE
  signal and report the excluded rows as their own problem — otherwise fixing the age just
  buries the corruption. And when a guard drops bad data at ingest, the check that was meant
  to catch that same class must read the RAW source, not the guarded output.
