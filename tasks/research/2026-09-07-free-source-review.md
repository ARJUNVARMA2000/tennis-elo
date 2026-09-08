# Free-source and scraping findings

**Free public schedule scraping is feasible and demonstrated.** Six account-free HTTP
reads retrieved US Open schedule data and official orders of play. The retained sample
contains 132 schedule rows across two days, including six WTA singles matches. A private
extractor produced six source-linked schedule observations. No subscription is needed
for these observed public endpoints. They are not a qualified actual-start producer.

The user requested free alternatives or scraping. This phase answers that request with
real samples, a working extraction recipe and a provider comparison. It does not repeat
the previous 18-read point-timestamp investigation, add a generic timing framework,
change fitted models or activate a collector.

## What was actually scraped

Research root `R`:
`/Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation`.
Checkout `R/worktrees/free-source`, branch `codex/model-free-source`, from
`2e50cb560bb7ba394eae83883b76db9ad06ecff6`. Private runs: `R/runs/free-source`.

The retained application configuration and bundle establish the endpoint construction:

- Day catalogue:
  `https://www.usopen.org/en_US/scores/feeds/2026/schedule/scheduleDays.json`.
  Its `eventDays[].feedUrl` supplies each actual released day's JSON URL.
- Selected days: `schedule16.json` and `schedule17.json` in that same directory,
  corresponding to September 7 and 8, not tournament days 16 and 17 of the main draw.
- The bundle concatenates the configured PDF prefix, `tournDay`, and `.pdf`.
  This yielded official `schedulePDF16.pdf` and `schedulePDF17.pdf` under
  `https://www.usopen.org/en_US/scores/2026/schedule/pdf/`.
- The sixth read, the event schedule HTML page, returned only the application shell.
  It supplied no extractable schedule or timezone text. No retries or alternate-host
  bypasses were attempted.

All six returned HTTP 200, with exact raw bytes and request/receive metadata preserved.
Requests occurred 2026-09-08 02:54:19–02:57:23 UTC (September 7 locally), bounded at
20 seconds / 8 MiB each, without accounts, credentials, redirects or retries. These
counts exclude web search and documentation reads. The
[result JSON](2026-09-07-free-source-result.json) contains all receipts, counts and hashes.

`R/tools/free-source-probe.py` is the bounded acquisition driver.
`R/tools/free-source-analyze.py` reads those retained bytes, verifies their hashes and
extracts WTA singles to `R/runs/free-source/schedule-observations.json`. This private
proof of concept is not a production scraper or an evaluator intake adapter. Both
drivers are fingerprinted in the result. Output files are exclusive; reproduce with a
copied driver and a fresh output path, never by overwriting accepted evidence.

## Exact sample and time semantics

| Date in the published order | All rows | WTA singles | WTA explicit not-before | WTA first-session match |
|---|---:|---:|---:|---:|
| September 7 | 72 | 4 | 1 | 3 |
| September 8 | 60 | 2 | 0 | 2 |

The 72-row day includes one intentional blank. Juniors, doubles and wheelchair categories
were kept in the census and excluded from the six-row WTA singles extraction.

The concrete not-before example is **Osaka–Rybakina**, US Open match `2408`, September 7,
Louis Armstrong, third match, published **2:30 PM**. Under the explicit New York venue
timezone this is `2026-09-07T18:30:00Z`. The PDF's first page places that exact label
above this matchup. The observation was acquired after that time, so it is not evidence
that any forecast was captured before this match.

September 8's two WTA quarterfinals are first matches in separate Arthur Ashe sessions:
`2501`, Sabalenka–Noskova, 11:30 AM; `2502`, Pegula–Navarro, 7:00 PM. Both were observed
before their published times, but neither is explicitly labelled not-before. The
extractor keeps `first-match-session-start` separate from `explicit-not-before`.
No forecast was produced; an early schedule receipt alone is not paired forecast evidence.

Every selected WTA row carries edition, provider match ID, player IDs, round, court,
session, order, original timing text, observation time, source URL and raw hash.
`actualStartVerified` remains false. No ESPN event join or prediction-context donation
was attempted from only these six match witnesses.

The date and timezone mapping was checked against the PDF headings and all 33 court/
session start epochs and printed clocks using `America/New_York`. The day catalogue's
`epoch` is **not a safe match-date anchor**: day 17's value resolves to September 7,
while its heading and every court start identify September 8. The extractor uses the
explicit edition, displayed date and corroborating court clocks, and records the conflict.
Neither catalogue epoch nor document `epoch` becomes an actual-start timestamp.

All four pages of the two PDFs were rendered with Poppler and visually inspected.
The plain text extraction contained encoded glyphs, so it was not used to validate
names or timing-label placement. The two sources agree on printed schedule meaning;
they are the same publisher and are not independent observations of physical play.
`releaseTime` is only a time-of-day string; this sample does not establish original
publication time, complete revision history, postponement behavior or start-clock accuracy.

## Other free alternatives checked

| Source | What the current evidence supports | Decision for this task |
|---|---|---|
| Official US Open JSON + PDF | Account-free schedule retrieval and six real WTA schedule observations tested here | Best concrete free addition; develop schedule/revision collection first |
| Existing WTA / ESPN adapters | Already used in DEUCE; prior preserved sample supplies identity/results/completion bounds, but no qualified actual starts | Reuse existing adapters; do not build duplicate scrapers |
| Live Tennis API | Provider documents $0, no-card signup, 100 requests/day for live/upcoming scores and fixtures; events and historical listings are outside the free tier | Possible additional scoreboard, not a free match-event substitute; documentation only, no account/sample |
| Tennis API via RapidAPI | Provider documents free/paid tiers and requires a RapidAPI key; exact free quota and required endpoint access were not established | Unqualified secondary lead, no integration or signup |
| Bzzoiro / BSD | Current tennis documentation requires a $5/month Sports Addon plus an account token | Exclude from the free shortlist despite older promotional posts |
| Sofascore | Provider FAQ says it does not supply data API endpoints because of provider agreements | Do not depend on unofficial endpoint lists as an offered free API |

Primary references checked September 8 UTC:
[Live Tennis API](https://docs.livetennisapi.com/reference.html),
[Tennis API](https://docs.tennis-api.com/),
[BSD tennis access](https://sports.bzzoiro.com/docs/tennis/),
[Sofascore FAQ](https://sofascore.helpscoutdocs.com/article/129-sports-data-api-availability).
Live Tennis API's fixture `start_time` is explicitly scheduled time. Its free plan is
therefore useful for a score display but does not establish the missing actual-start
lower bound. No provider's marketing or sample schema was counted as a real observation.

DEUCE already has historical/fresh archive and official scraper paths in `config.py`
and `data/download.py`; more copies of those same rows are not new model evidence.
Attempts to inspect the canonical Sackmann pages through the web tool failed, and
Tennis-Data returned a gateway error. We did not verify a new downloadable historical
source this phase and did not infer permanent source unavailability from tool failures.

## Decision, verification and remaining work

Proceed with the **free official schedule route** for collection engineering. The six-row
proof of concept establishes access and field mapping. It does not establish the live
timing contract, reliability across revisions or full-tour coverage. An explicit
not-before label could support a lower bound conditional on tournament compliance;
that assumption must remain visible and cannot silently replace the primary independent
start-evidence requirement. First-session times need their own justified treatment.

At 03:00:46 UTC the offline extraction and preservation assertions passed: all 500
prior run files, all 91 frozen package files, both model payloads (within that manifest),
and 354 tracked files under `tennis_model`, `web`, `.github` remain exact. Nine completed
research checkouts remain clean. No additional training copy exists. Full training/
snapshot inventories were last checked at 01:58:44 UTC in the earlier phase and were
not rehashed here. No implementation tests were rerun; no program or test files changed.

F0/F1 are complete. F2 produced a private sample extractor, while production/evaluator
integration remains conditional and unimplemented. F3 records these findings and the
[implementation handoff](2026-09-07-free-source-next.md). No new model fit, performance
score, live registration, unattended collector, account, purchase, provider message,
production merge/push or deployment. The incumbent/candidate decision is unchanged.
