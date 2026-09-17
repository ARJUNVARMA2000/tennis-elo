# ATP statistics alternatives — September 11, 2026

**A free official US Open fallback is technically feasible and worth implementing
next.** This round retrieved 11 ended matches with detailed numeric statistics:
eight men's main-draw matches from September 7–9 and three earlier qualifying matches.
The three qualifying matches join uniquely to retained TML rows by event ID, ATP
player IDs, round and score; all three agree exactly on the service-point totals used
by the current model. No feed was integrated and no production data or model changed.

This is source qualification, not a new historical predictive-performance experiment.
It does not establish that a new feed improves log loss or that it was available before
past forecasts. The TML outage remains unresolved; an event-specific fallback would not
replace its complete historical, Challenger and qualifying coverage.

## Ranked alternatives

| Source | Actually checked | Assessment |
|---|---|---|
| **Official US Open JSON** | 11/11 match requests returned usable detailed statistics; 8 recent main-draw records pass identity and point/set arithmetic; three qualifying overlaps agree on core point totals | Best immediate pilot for the current event; free/account-free retrieval demonstrated |
| **Official ATP match pages** | Current results and Zverev–van de Zandschulp statistics loaded in the browser; exact point counts visible; ordinary HTTP access returned 403 | Promising broader source, but unattended transport and coverage remain unproven |
| **TennisData.app** | Free season-download page and its conventions inspected; one download attempt; no CSV available for column inspection through this tool | Promising bulk candidate requiring a real sample and access/reliability validation |
| **Live Tennis API** | Current provider pricing: free tier is scores/fixtures; completed history starts at $9.99/month, detailed live serve statistics advertised at $99.99/month | Possible paid route, not a demonstrated free statistics replacement; no account or sample |
| **Existing ESPN / Tennis-Data.co.uk sources** | Existing adapters already provide results and odds; previous ESPN audit found empty scoreboard statistics; current Tennis-Data connection probe failed | Keep their existing roles; no new serve-statistics replacement demonstrated |

Primary references: [official US Open configuration](https://www.usopen.org/en_US/json/gen/config_web.json),
[one retrieved complete-match feed](https://www.usopen.org/en_US/scores/feeds/2026/matches/complete/1501.json),
[official ATP match page](https://www.atptour.com/en/scores/match-stats/archive/2026/560/ms004),
[TennisData.app downloads](https://tennisdata.app/downloads/), and
[Live Tennis API pricing](https://livetennisapi.com/pricing).
Prices and coverage promises are provider documentation, not measured service guarantees.

TennisData.app advertises ATP/WTA main-tour and Challenger seasons 2021–2026, stable IDs,
home/away orientation and multiple daily updates. The initial browser security check
completed automatically; after clicking ATP 2026 Download CSV, a human-verification
checkbox appeared. No CAPTCHA was solved, no account created and no CSV contents
verified. Its public match pages can show serve-point fractions; that does not prove
those columns exist in the free CSV or that its underlying data is independent.

## What the model actually needs

The production serve/return walk reads `svpt`, `1stWon` and `2ndWon` for each player,
using `1stWon + 2ndWon` as total service points won. `valid_stat_mask` requires all six
values to be finite, nonnegative and bounded by positive service-point counts.
The broader canonical raw schema has nine statistics per player; the model currently
does not use the first-serve-in count, double faults or service-game count as independent
features. Therefore equality of the six raw fields and equality of the totals that
drive the model are different claims. We established only the latter across sources.

Code inspected at integration branch `1c1131e` (functional source remains `d75b7ef`):
`tennis_model/src/tennis_model/points/serve_return.py`, `points/serve_prior.py`,
`data/results.py`, `data/download.py`, `data/wta_stats.py` and `data/live.py`.
The root checkout is documentation-only and must not be used for implementation.

## Executed official-source assessment

Private evidence: `.research/2026-09-11-atp-source-alternatives/`.
The source configuration was re-fetched and matched the earlier retained configuration
hash. Published day-list URLs supplied the current match IDs; no name guessing or
endpoint grid was used. Initial curl requests failed HTTP/2 transport, while the same
public URLs succeeded with Python's standard HTTPS client and normal certificate
verification. A legacy statistics route in the published configuration returned 404;
the current `scoringData.matchStat.path` route worked:

`https://www.usopen.org/en_US/scores/feeds/2026/matches/complete/<matchId>.json`

`analyze.py` processed **every** men's singles record in the three chosen completed-day
lists. Seven ended normally and one by retirement. It checked listing/detail identity,
winner orientation, status, positive/integer/bounded point counts, first+second totals,
opponent return-point complements and whole-match versus summed-set statistics.

| Official match ID | Winner — opponent | Status | Winner serve points won/played | Opponent serve points won/played |
|---|---|---|---:|---:|
|1404|Blockx — Cerundolo|Completed|86/138|81/132|
|1401|Zverev — Darderi|Completed|64/82|60/104|
|1403|Khachanov — Tien|Completed|105/168|94/155|
|1402|Van de Zandschulp — Gea|Completed|115/199|124/210|
|1503|Tiafoe — Michelsen|Completed|108/181|100/162|
|1504|Shelton — Alcaraz|Completed|103/158|109/175|
|1502|Khachanov — Blockx|Retired|51/66|45/74|
|1501|Zverev — Van de Zandschulp|Completed|58/86|43/79|

None of these eight rows exists in the retained main TML file examined here. That file
has **zero** US Open main-draw rows with event ID `2026-560`; the separate lower file
has 112 US Open qualifying rows. Thus a recent aggregate ATP statistics date is not proof
that the ongoing main event has statistics. This census concerns the local retained
inputs whose hashes are recorded; this round did not download the current private CI
cache or infer its exact contents from a public health maximum.

For an actual overlap check, `compare-qualifying.py` selected the **first three** MQ
records in the published August 28 final-qualifying-day list before retrieving their
statistics: 11316 Sakamoto–Nishikori, 11304 Rodionov–Fearnley and 11314 Wendelken–Gaubas.
All three match the retained winner/loser IDs, event, round and game scores. Both players'
service points played and total service points won match exactly in all three.

However, **none matches all 18 raw fields**: first/second-serve splits differ in all
three, and Fearnley's double faults differ 9 versus 10 in one. The official ATP browser
page for 1501 likewise agrees with US Open on 58/86 and 43/79, but differs on the first/second
split and shows implausible zero service-game counts. These discrepancies are retained,
not averaged away. Their underlying cause is unresolved; one provider must not silently
overwrite existing valid statistics. Cross-publication agreement is not proof that the
providers have independent upstreams.

## Recommended implementation sequence

1. **Add a narrowly scoped US Open acquisition adapter in a new integration worktree.**
   Start from the current accepted source plus the already validated WTA integration,
   preserving all completed evidence. Discover the edition/config and published day
   lists, fetch only ended match IDs missing trusted stats, cache bounded responses,
   and retain acquisition time, URL, hash and source status. The initial batch may cover
   the current US Open main draw; qualify the full event before calling coverage complete.
2. **Normalize with explicit provenance and join to existing results.** Use edition,
   event identity and real ATP player IDs, round and score. The completed-day feed uses
   `MS/MQ`, while the complete main-match payload observed here uses `B`; derive admission
   from the positively identified listing and validate both participants. Keep qualifying
   state admission separate from the main fitting population. Use the established ESPN
   event mapping (`espnId`, not event name) for product joins. Missing metadata cannot be
   invented to create a fresh independent match row.
3. **Enrich only verified missing statistics initially.** Preserve existing valid TML
   rows and all historical input bytes. Map service points from `serve_stats.match`:
   `t_p`, `f_srv_p`, `f_srv_p_w`, `s_srv_p_w`; validate against `t_p_w`, `base_stats`,
   opponent complements and set sums. Keep source-specific splits and discrepancies
   explicit. Reject malformed or contradictory rows instead of guessing from rounded
   percentages. Preserve retired/walkover states and the current model's eligibility
   rules. A missing count is not zero.
4. **Verify semantics before publication.** Add meaningful fixture tests for reversed
   winners, terminal/retired/live states, wrong-event/tour/player identities, missing or
   impossible stats, duplicate/correction handling and failed-download retention.
   Replay a wider event sample, compare all available overlapping core totals, and audit
   missing-stat coverage by event. Extend the existing pre-upload health gate for any
   new published failure class; retain accurate source freshness and acquisition status.
   Do not backdate a newly collected receipt into a historical availability claim.
5. **Rebuild and verify the actual outputs.** Use normal full state rebuild, saved-query
   parity, quick/recovery and both release gates; preserve the accepted ATP/WTA model
   contracts and population. Historical predictive improvement is not established by
   data-source arithmetic. Any later feature or population change still needs its full
   arbiter. Revisit the WTA release readiness decision using the measured current data
   coverage; the TML strict download will still report its outage until that source
   recovers or an explicitly validated replacement policy is implemented.

Steps 1–2 can be prepared together after the mapping is fixed; steps 3–5 depend on their
results. Broader ATP transport research and obtaining a TennisData.app CSV sample are
independent follow-ups. No parallel agents were used or requested. A full-tour ATP
replacement needs separate main/Challenger/qualifying coverage and reliability evidence;
the 11-match event sample is insufficient for that claim.

## Review and durable state

A1–A4 source assessment is complete. Eleven official detail requests succeeded; eight
recent rows passed the full offline arithmetic assessment and three older rows passed
core-total overlap comparison. The response bodies, failed attempts, drivers and
structured observations are inventoried in `2026-09-11-atp-source-alternatives-result.json`.
No production tests were rerun because no production code changed. No data/model files,
source credentials, accounts, purchases, provider messages, merges, pushes or deployments
were created or changed. Existing implementation head `1c1131e` stayed clean.

The next authorized implementation would be the event-scoped adapter above, rather than
waiting indefinitely for TML or assuming every advertised free feed supplies model-ready
statistics. A real TennisData.app sample and unattended access remain unverified.
