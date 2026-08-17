# Data sources & freshness

Downloads, transports, upstream schema drift, row labelling, what the release snapshot holds.

Indexed in [`../lessons.md`](../lessons.md).

- **One mistyped date in an upstream row can empty a whole tour, because the date-relative
  windows anchor on the dataset's MAX date, not on today.** (2026-07-25, WTA export shipped 2
  players) Restoring the fresh overlay (below) immediately surfaced the next failure: the WTA
  file carried the Iasi final as `2029/7/20` instead of `2026/7/20`. `elo.last_date` jumped
  three years, so `_active()`'s `last_date - ACTIVE_DAYS(550)` cutoff landed in 2028 and left
  exactly the two players in that one row "active" — `rankings/wta: matched 2/2 exported
  players` against ATP's 193/200. `build_draws` then padded a 2-player field to a 2-slot
  bracket, whose only round labels are `F`/`Champion`, and died on `r.SF`
  (`AttributeError: 'Pandas' object has no attribute 'SF'`). One bad cell, 1 of 1611 rows,
  killed the retrain. Verified on the real file: dropping that row moves the active-player
  count from **2 to 261**. Two guards, deliberately with different thresholds — dropping rows
  is destructive so ingest is permissive (`MAX_FUTURE_MATCH_DAYS = 60`, clearing the live
  overlay's real 12-day-forward scheduled rows by 5x), while merely reporting is cheap so the
  health check is tighter (`HEALTH_MAX_FUTURE_DATE_DAYS = 14`). **Why the existing gates were
  blind:** `result_age_days = (now - res_max).days` goes NEGATIVE for a future date and sails
  under its `max_result` ceiling — every staleness check in the file was one-sided, testing
  only "too old". Also note `res_max` is completed-only, and this row was a `RET`, so the
  check had to hang off `date_max` to see it at all. **How to apply:** for any age/recency
  gate, ask what happens at the OTHER end of the range — a one-sided bound on a quantity that
  can go both ways is a silent hole; and when a fix unblocks a path that has been dark for
  days, expect the next latent failure immediately behind it and re-run to completion rather
  than declaring the fix good at the layer you changed.

- **A transport that answers 200 with the WRONG BYTES must not end a fallback chain — and a
  retry cannot fix a payload the source is serving on purpose.** (2026-07-24, fresh overlay
  went dark for 5 days) `LuckyLoser91/TennisCourtLog` added `*.csv filter=lfs` on 2026-07-19.
  `raw.githubusercontent.com` kept returning **200**, but with a ~131-byte Git-LFS *pointer*
  instead of the CSV — and the `gh` contents API returns the pointer too, so BOTH GitHub
  transports went blind at once. `download_year` was `_via_https(...) or _via_gh(...)`, and
  that `or` only falls through on a `None`: a truthy-but-wrong payload silently skipped the
  fallback. Every daily full retrain failed from 07-20 to 07-24 (runs 29728318112 /
  29812819613 / 29902577724 / 29990249105 / 30077588939) with `STRICT: 2 critical download
  failure(s)`, while the site kept looking healthy because the hourly QUICK refresh
  regenerates from the saved model and never downloads year files — so the model silently
  went 5 days stale behind a green-looking dashboard. Fixes: iterate transports as
  *candidate payloads* and schema-validate each independently (a 200-with-HTML-error-page
  had the same latent bug), and resolve LFS via
  `media.githubusercontent.com/media/{repo}/{ref}/{path}`. **Why the retry didn't save it:**
  the backoff added in `6945d07` cited run 29812819613 as a transient that "self-healed an
  hour later untouched" — it had not. The run that looked like the recovery was a *quick*
  refresh, which never exercises the download path. The premise was false, so the mitigation
  was aimed at the wrong failure class. **How to apply:** (1) when a fallback chain exists,
  branch on *payload validity*, never on the truthiness of the first response; (2) before
  citing a run as evidence that a failure is transient, confirm that the "recovered" run
  actually ran the failing step — compare modes, not just conclusions; (3) when only the
  slow/daily path is broken, ask what the fast path is silently NOT doing (here: retraining).

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
  calendar-validation lesson in [`gates-and-health.md`](gates-and-health.md).

- **Verify a source's naming convention per file, not per format.** (2026-07-02)
  "XXX vs YYY" tie names are host-first in the ATP Davis Cup file but carry NO
  venue order in the WTA Fed Cup file (single-venue weeks; arbitrary/winner-first
  ordering) — the same regex, trusted uniformly, silently mislabeled ~8% of WTA
  training rows with a flag that partially encoded outcomes. Rule: before deriving
  a feature from a naming convention, verify it against known ground truth in EACH
  source file it will touch (a handful of known-venue rows per file suffices).

- **Both tours' `fresh` files live in ONE repo, so one bad minute reds the daily retrain.**
  (2026-07-21) `download_year` fetched with `_via_https(retries=1)` — which is *zero* retries,
  the loop runs once and never sleeps — leaning entirely on the `_via_gh` fallback. When both
  transports missed in the same instant (run 29812819613), `atp/fresh` and `wta/fresh` both
  failed [2025, 2026] and `--strict` killed the full retrain, while `historical` (47 files, a
  *different* repo) sailed through. The simultaneity was the tell: FRESH_SOURCE points both
  tours at `LuckyLoser91/TennisCourtLog`, so that repo blipping fails everything at once —
  it reads like a network outage but is one upstream. Fix: retry the failed years at the
  `download()` level with exponential backoff, bounded by BOTH a round count and a wall-clock
  budget — the budget is what stops a genuinely dead 47-year archive from costing three full
  passes of 30s timeouts. Rules: a retry with no time budget is a hang waiting to happen; and
  `retries=1` reads like "retry once" but means "don't retry" — count attempts, not retries.

- **Label rows by what they ARE, not by which directory they arrived in.**
  (2026-07-25) A5 adopted "challengers feed the rating walks, never the combiner", implemented
  as `_read_lower` stamping `draw_level` on the files it reads out of `lower_dir`. That made
  the invariant a property of the READER, so the moment the same kind of row arrived through a
  different door it silently became main draw — the ATP serve-stats source ships
  `<year>_challenger.csv` into `stats_dir`, and because the stats overlay outranks the lower
  overlay in the dedup preference, its unlabelled copy beat the correctly-stamped one. Result:
  42k of the 72k rows the ATP combiner scored as main draw for 2016-26 were Challengers, and
  the walk-forward quietly gave back the entire A5 gain (acc 0.6832 -> 0.6571) with every test
  green. Fix: derive from content (`tourney_level`) first, let an explicit stamp win, default
  last. Two rules. First, when a filter encodes an adopted MODEL decision, it needs a test on a
  production-shaped frame — `main_rows` had none, so nothing noticed the population it filtered
  had doubled. Second, a headline metric regressing is a symptom worth chasing to a cause: the
  numbers had been wrong in the shipped README for weeks and were read as "docs are stale"
  rather than "the model changed". Compare `n`, not just the metric — the row count doubling
  was the tell, and it was visible the whole time. See [[future-proof-no-quick-fixes]].

- **The release snapshot is load-bearing data that `download` cannot reproduce.**
  (2026-07-25) Measuring the README's walk-forward locally, I ran `download --kind all` and
  assumed that was the dataset. It is not: the scraped WTA serve-stats backfill
  (`stats/2024+`) exists only in the `data-archive` release asset — no free bulk source
  carries WTA serve stats since mid-2024 — and CI restores it on a cache miss before
  downloading on top. Without it WTA 2024 holds 1,214 matches instead of 2,119, and every
  local metric is quietly measured on less data than production has. I nearly committed those
  numbers to the README. What caught it was the **row count, not the metric**: the README said
  42,513 WTA and my run said 41,174, and n is the thing you can sanity-check against a prior
  reference when the metric itself looks plausible. That is the same tell that would have
  caught the challenger contamination weeks earlier. Rules: when a repo bootstraps from a
  snapshot in CI, a local run is NOT equivalent to CI unless it bootstraps too — put that in
  the Usage section, not in tribal memory; and before publishing any measured number, diff the
  population size against whatever reference you are replacing, because a metric computed on
  the wrong rows looks exactly like a metric computed on the right ones.
  See [[future-proof-no-quick-fixes]].

- **An incomplete source moves only `n`, and nothing was watching `n`.**
  (2026-07-25) Two separate wrong-numbers incidents in one day shared a signature: the data
  was present, parseable and self-consistent, just the wrong ROWS. Challenger matches doubled
  the ATP combiner's population; a local checkout missing the release-snapshot backfill
  halved WTA 2024. Every metric stayed plausible, every test stayed green, and the health
  gate never saw it — the gate validates shipped JSON, not the population the model was fit
  on. Both times a human caught it by comparing `n` against an older reference. So watch the
  population: `results.thin_seasons` flags any completed season under 60% of the recent
  median at load time, which is early enough to stop a measurement before it is published.
  Two design notes worth keeping. It excludes 2020 explicitly — COVID is a real, permanent
  shortfall, and a check that cries wolf on a known anomaly trains you to ignore it. And it
  WARNS rather than raises: a genuinely truncated upstream is sometimes the truth, and
  refusing to load would take the site down over a data-quality issue the operator may
  already know about. See [[future-proof-no-quick-fixes]].

- **Canonicalising names WITHIN a key group cannot merge variants that change the key —
  a dropped surname ships one player as two.** (2026-07-27, Umag) `results._canonicalize_names`
  folds accents and punctuation, so `Félix Auger-Aliassime` and `Felix Auger Aliassime` share a
  `_name_key` and collapse. `Daniel Merida` (archive) and `Daniel Merida Aguilar` (live feed)
  do not: the extra surname changes the key itself, so the pass that exists to unify spellings
  structurally cannot see them as the same person. Umag exported `drawSize` 29 for a 28-draw,
  `aliveCount` 2 on a completed event (the loser identity never cancelled the winner one), and
  **split the champion's retrospective title odds across both entities** — the visible defect
  the health advisory only hinted at. Fix: an explicit `config.PLAYER_ALIASES` applied before
  the per-key vote (so frequency/source preference runs on merged counts). **Why:** the
  tempting general rule — "one name's surname tokens are a prefix of the other's" — merges
  genuine relatives (the Zverevs, the Bryans); there is no safe automatic bridge here.
  **How to apply:** treat the alias table as the escape hatch for what keying cannot reach, add
  an entry when the gate flags one, and pair it with an invariant that does not depend on names
  being clean (a completed event's alive count is 1 *by definition*, not by set subtraction) —
  so the next unbridged variant degrades one number instead of publishing a contradictory card.

- **A rolling overlay must enforce the model's population policy by stable identity before
  merge, and intentional population changes need an explicit version boundary.** (2026-08-03)
  ESPN's WTA scoreboard mixes tour events with WTA 125s, while `INCLUDE_WTA_125=False`
  because no 125 source covers the arbiter's tune window. The live overlay bypassed that
  decision: its 14-day sweep temporarily added lower-tier results, then the UTC rollover from
  August 2 to 3 dropped the July 19 query and five 31-match events together. The exported
  population fell 128,827 -> 128,703 even though every source was parseable and current.
  Filtering by event name would repeat the repo's largest identity bug, so the tier cache is
  resolved through the registry's append-only aliases to `espnId`; WTA 125 and unclassified
  live rows are withheld from model state but remain identity hints until stable-source
  duplicates inherit the id, preserving board joins. The export now audits WTA-125 and
  excluded counts, and the pre-deploy gate requires the model count to be zero. Finally,
  monotonic `meta.matches` cannot compare two intentionally different populations: stamp a
  required `matchPopulationVersion`, reset the baseline only across that explicit boundary,
  then resume ordinary comparison on the next run. Never weaken the drop threshold to make a
  migration green; version the population and keep the invariant intact.
  The version must also ride inside `predictor.pkl`: cleaning the current frame is not enough
  when a quick refresh can reuse ratings already walked over the old rows. Reject legacy or
  mismatched predictor versions, rebuild them, export the model's own version separately, and
  require model/data version parity in the deploy gate so stale state cannot be relabelled clean.

- **A keyless upstream can start rejecting your client by its User-Agent alone, and a
  best-effort fetch that swallows EVERY query reports the outage as an empty week.**
  (2026-08-04..07, ATP board showed Zverev alive at 21% to win Toronto for three days after
  he lost) ESPN's `site.api.espn.com` edge began 403-ing anything sending a custom
  User-Agent; the overlay sent `Mozilla/5.0 tennis_model`, so all 28 scoreboard queries
  failed on every refresh. `fetch_events()` caught each one with `except Exception: continue`
  — right for one malformed day, catastrophic for all of them — and returned `[]`.
  `download_live()` then printed `no completed matches found`, the exact line a genuinely
  idle day prints, and its `if not df.empty:` write guard left the last good `live.csv` in
  place. Thirteen consecutive green refresh runs. **Two things hid the blast radius:** it hit
  BOTH tours, but WTA has its own daily stats scraper that kept `date_max` current, so only
  ATP visibly froze and it read like an ATP-specific source problem rather than a transport
  one. And the tour-wide `results` freshness check is a 5-day limit over an aggregate
  dominated by FINISHED events, so one stalled tournament never moved it — ATP sat at 3 days
  and reported `ok: true`. **The probe that found it:** the same URL returns 200 with curl's
  default UA and 403 with any custom one, and the sibling host `site.web.api.espn.com` serves
  the identical payload under every UA. **How to apply:** tolerating a single failed query is
  correct, but tolerating *all* of them is how a transport outage disguises itself as
  no-news — count the failures and raise when none succeeded, so an empty result always means
  the source answered and had nothing. When a source dies, check every tour/feed it serves
  before believing it is scoped to the one you noticed; a redundant path on the other tour
  will happily mask a shared outage.

- **Normalize verified identity variants at the earliest shared feed boundary, not only in the
  result merge.** (2026-08-17, Cincinnati) Family-name-first ESPN spellings and Catherine/Caty
  variants split WTA ratings; fixing only completed results would then remove the duplicate rating
  keys that raw upcoming rows still needed, making those matchups disappear from forecasts.
  **How to apply:** keep aliases explicit and falsifiable, then apply them to ESPN results, fields
  and upcoming players through the common athlete parser. General token reordering remains unsafe.

- **A provider round is part of match identity until stronger one-to-one result evidence proves
  the providers disagree.** (2026-08-17, Cincinnati) Keeping `round` in the ordinary de-dup key
  correctly preserves real rematches, but also preserved one WTA result twice when the stable
  feed called it R64 and ESPN called it R32. **How to apply:** bridge conflicting metadata only
  when ordered canonical players, local date and games-only score agree, exactly one row exists
  per source, and exactly one ESPN row supplies a stable event id. Then retain the stat-bearing
  row while copying the live id/round. Any repeated source row makes the bucket ambiguous and
  must remain separate for the output gate or a human to resolve. Carry that stable id into the
  completed fixture too, and make the pre-deploy gate independently compare its player pair and
  round with the shipped bracket; auto-repair without an independent check is still guessing.
