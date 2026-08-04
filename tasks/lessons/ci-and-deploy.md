# CI, alerts & deploy

Workflows, alert branches, cron, concurrency, hosting and serving, dependency pinning.

Indexed in [`../lessons.md`](../lessons.md).

- **A pre-push verification set must include the workflow's exact linter, not only tests and the
  domain gate; otherwise CI becomes the first place formatting is exercised.** (2026-08-04,
  WTA data-health release) All 514 tests, the real-data replay, and `health --gate` passed, but
  the first production push stopped at Ruff because two new test imports violated `I001`.
  Nothing deployed—the workflow gate worked—but the release incurred a needless failed run and
  corrective commit. `git diff --check` cannot substitute for a language-aware import/style
  check. Before a direct-to-master deploy, mirror the workflow's complete cheap gate locally:
  repository-wide `ruff check .`, the full test suite, and the domain integrity gate. When CI
  still finds something, reproduce the exact reported command before patching and rerun all
  three; a passing formatter on only the named files can miss a second violation elsewhere.

- **An alert must never report the failure of its own transport as the thing it monitors.**
  (2026-07-24, run 30106835566) Everything real passed — integrity gate green, 0 output
  problems on both tours, deploy succeeded, live verification OK — and the run still went
  red, twice, because `EXISTING=$(gh issue list ...)` ran unguarded under `bash -e` and the
  GitHub API returned `504 Gateway Timeout`. A GitHub API outage is not a data problem and
  not a broken site; reported as either, it is the same false-alarm class as the
  skipped-verification bug `41a3341` fixed, arriving through the transport instead of the
  outcome. Note the neighbouring `gh issue comment`/`close` calls already had `|| true` — it
  was only the *read* that was unguarded, which is easy to miss because it looks like plain
  data plumbing rather than alert logic. Fix shape: retry the read, then degrade it to
  **UNKNOWN** and let each branch decide — healthy + unknown stays GREEN (worst case a
  recovered issue closes an hour later); failing + unknown goes RED but files nothing,
  because we cannot tell "no issue yet" from "already open" and guessing opens a duplicate
  thread every hour. Keep the backoff env-tunable (`GH_RETRY_SLEEP`, like `FRESH_TRIES`) so
  tests exercise the retry path instantly. **How to apply:** for any alerting step, ask
  "what does this do when the *alerting* API is down?" — the answer must never be "declare
  the monitored thing broken", and it must be pinned by a test that stubs the API failing.
  This is also why the last inline alert block moved to `.github/scripts/`: the bug lived in
  the one branch no test could reach.

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

- **`cancel-in-progress: true` on the deploy concurrency group silently drops changes.**
  (2026-07-09) The `pages` group cancelled any in-flight deploy when a scheduled refresh or a
  concurrent push arrived, so the run carrying a change was killed mid-flight and never shipped —
  repeatedly misread as a "transient Pages hiccup" and worked around with manual re-dispatch
  (~100 turns burned across sessions). Set `cancel-in-progress: false` (GitHub's own Pages-deploy
  default): the in-progress run finishes; GitHub queues only the latest superseding run and skips
  intermediate ones. Rule: a deploy job's concurrency group must never cancel in-progress.

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

- **Inline workflow `run:` shell is untestable, and that is where the false alarm hid.**
  (2026-07-21) The deploy-health branch logic (dedup, mode throttling, skipped-vs-failed) lived
  as a 30-line `run: |` block in refresh.yml, reachable by nothing. Fix: move it to
  `.github/scripts/report-deploy-health.sh` and call it with `run: bash .github/scripts/...`,
  then drive the real script from pytest with a stubbed `gh` on PATH, asserting exit code AND
  the exact `gh` subcommands (`test_workflow_alerts.py`). Extracting beat the alternative of
  parsing the YAML at test time, which needed a PyYAML dep CI does not install and would test a
  copy rather than the artifact CI runs. Two things earn their keep: a test asserting the
  workflow still *calls* the script (else it drifts out of use while the suite stays green),
  and `.gitattributes` pinning `*.sh` to LF (this repo is developed on Windows with autocrlf on;
  a CRLF shebang fails on the Linux runner). Rule: if shell decides whether a human gets paged,
  it belongs in a file with tests. See [[future-proof-no-quick-fixes]].

- **Never key a decision off *which* cron GitHub says fired.**
  (2026-07-25) `Decide mode` compared `github.event.schedule` to the literal `"0 6 * * *"` to
  pick the daily FULL retrain. GitHub attributed the run occupying that slot to the *hourly*
  cron string instead — `[ "17 0-5,7-23 * * *" = "0 6 * * *" ]` — so the full branch never
  fired on 07-21..07-25 and the model was retrained only when a human dispatched it by hand.
  Scheduled delivery is delayed and re-attributed under load (the affected runs landed
  06:30-06:43, never at :00), so the cron string is not a stable identity. Read the clock
  instead: a scheduled run landing in the intended hour IS the daily job, however GitHub
  labelled it. Two further rules fell out. First, the tempting "retrain whenever the model is
  older than N hours" is worse, not better: a persistently failing full run would be retried
  every hour, and because a red full run blocks the deploy, the site would freeze instead of
  coasting on quick refreshes — keep the *mechanism* (which run retrains) separate from the
  *detection* (has retraining stopped), which is the model-age watchdog's job. Second, this is
  the second inline-`run:`-block regression in a week; the CLAUDE.md rule about testable shell
  is not just about alerting — any shell that decides something expensive or load-bearing
  belongs in `.github/scripts/` with a case in `test_workflow_alerts.py`. See the
  "Inline workflow `run:` shell is untestable" entry above and [[future-proof-no-quick-fixes]].

- **A `run:` block is `bash -e`, so the second command is conditional on the first.**
  (2026-07-25) `Full refresh` was one block: `download --strict` then `pipeline --backtest`.
  Nobody wrote "skip the retrain if a download fails", but that is exactly what it meant, and
  it cost five days of frozen ratings when the fresh mirror moved to LFS. Two general rules
  fell out of hardening it. First, **put the expensive irreplaceable work in its own step**:
  anything sharing a block with it can veto it, and anything running before it in the same
  function can too (`walk_forward` ran before `train_final`, so a crash in a pure-metrics
  artifact discarded a completed 283k-match walk — best-effort it, like every other reporting
  artifact). Second, **`actions/cache` does not save on a red job**, so with a single cache
  step every failure downstream of the model write silently throws the model away and the next
  run restores the old one — split `cache/restore` + `cache/save` with `if: always()` whenever
  a job produces expensive state you would rather keep than recompute (and key on
  `run_attempt`, because "Re-run failed jobs" reuses `run_id` and save errors on a dup key).
  The pattern for "non-fatal but must not be missed" is already in this repo: let the step
  continue, then red the run in a trailing step AFTER the deploy and the alerts have run.
  See [[future-proof-no-quick-fixes]].

- **GitHub drops scheduled slots; claim the work, don't match the clock.**
  (2026-07-27) Keying the daily retrain to "did this run land in hour 06" missed on its first
  day: GitHub delivered scheduled runs at 04:02, 07:05 and 08:03 and nothing at all in hour 06,
  so the equality never matched and the model went 35h stale. Delayed delivery was the failure
  I designed for; *dropped* delivery was not, and it is just as common. The durable shape is
  "the first run at or after T each day, claimed via a marker so it happens once" — it does not
  care when the trigger actually arrives. Two supporting notes: write the claim BEFORE doing the
  work, so a crash cannot retry every hour for the rest of the day (the cache must save on red
  runs for this to hold — see the entry above); and `10#` your hour comparisons, because
  `[ 08 -ge 06 ]` is invalid octal and dies under `set -e` in exactly the late window such a fix
  exists to cover. The meta-lesson is worse than the bug: I documented this residual when I
  shipped the clock version, judged the watchdog an adequate backstop, and moved on. Detection
  is not a substitute for a mechanism that works — if you can name the case that defeats your
  fix, fix it or verify it is actually rare, don't file it under "accepted".
  See [[future-proof-no-quick-fixes]].

- **Append-only task history still needs explicit completion state: check finished items before
  adding the review.** (2026-07-30) “Append-only” means preserve the plan and its evidence; it
  does not mean leave completed checkboxes open. When a round finishes, mark every completed
  item `[x]`, then append the dated review. Otherwise the durable log presents finished work as
  an active backlog and makes the live tail ambiguous.
