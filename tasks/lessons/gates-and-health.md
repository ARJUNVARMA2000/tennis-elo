# Gates & health checks

Designing and placing the invariants in `health.py`; what a gate can and cannot see.

Indexed in [`../lessons.md`](../lessons.md).

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
