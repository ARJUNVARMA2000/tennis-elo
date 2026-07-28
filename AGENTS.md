# Tennis Elo — project notes

`tasks/lessons.md` is a one-line index of every mistake this repo has already made. Skim it and
read the `tasks/lessons/<topic>.md` file for what you're touching — not all of them. New lessons
go there (committed, so Codex sees them too), not auto-memory.

## Gotchas
- `tennis_model/` is src-layout: run everything from that directory with `PYTHONPATH=src`.
- Per-tour tuned constants live in `src/tennis_model/config.py` (`*_PARAM_OVERRIDES`), not next
  to the code that consumes them.
- `web/` reads JSON mirrored into `web/public/data/`, so a pipeline output change is invisible to
  the app until that mirror is regenerated. Dev server on :3001.
- `tasks/todo.md` and `tasks/lessons/*.md` are append-only logs, not checklists. The live round is
  at the *tail* of `todo.md`. Don't read either whole.
- **Events join on `espnId`, never on their name.** `data/events.py` holds the registry; an
  event's `names` list is its alias table, because ESPN's sponsor titles churn mid-tournament
  and the archive uses city names instead ("Nordea Open" vs "Bastad" share nothing). The id is
  a HINT on match rows, not a key — the archive predates it, so take the modal non-null value
  per event. Where no id exists, join on evidence (date overlap + shared real players), never
  on string similarity.
- Architecture, metrics, how to run it: root `README.md` and `tennis_model/README.md`.

## Everyday commands (bash)
```bash
cd tennis_model && PYTHONPATH=src python -m pytest -q     # Python tests
cd tennis_model && PYTHONPATH=src python -m tennis_model.pipeline --tour all --backtest   # full retrain (slow)
cd web && npm test && npm run lint                        # web tests + lint
```

## Hard rules
- **Two gates guard what ships, and a new failure class extends one of them.** Pre-upload data
  integrity: `output_problems()` in `tennis_model/src/tennis_model/data/health.py` (`--gate`,
  wired into `refresh.yml` on both full and quick). Post-deploy live serving:
  `web/scripts/verify-deploy.mjs` (`npm run verify:deploy`), alerted via a dedup'd
  `deploy-health` issue. Those two functions and their tests (`tennis_model/tests/test_health.py`,
  `web/tests/verify-deploy.test.ts`) are the spec — read them instead of trusting a prose summary
  here. When something wrong reaches the user, the fix is the bug **and** a new invariant plus a
  test in whichever gate should have caught it.
- CI alert logic lives in `.github/scripts/*.sh`, never inline in a workflow `run:` block, so
  `tennis_model/tests/test_workflow_alerts.py` can run it under `bash` with a stubbed `gh` and
  assert the exact `gh` subcommands. New alert branch → a case there. `.gitattributes` pins
  `*.sh` to LF; CRLF breaks the Linux runner.
- Model changes are adopted only via the full walk-forward arbiter gate (paired d±SE; tune
  2010–19 / val 2020+). Component-level sweep wins are NOT adoption.
- Every walk-time feature ships with its prediction-time state mirror + parity test in the same
  commit, or is recorded venue/context-free.
- Pin Python deps from the last successful CI run's install log, never local `pip freeze` —
  cross-version pickle compatibility is the constraint.
- After changing web deps: `npm install --package-lock-only`, then verify with `npm ci`
  (Windows-generated lockfiles can miss Linux optional deps).
- WTA API rate-limits (429s after ~2k calls): backfill one year at a time; CI incremental
  refresh is safe.
- Before finalizing any doc or plan that cites repo facts (metrics, features, file lists), re-run
  `git log` and reconcile with what exploration saw.

## Git & deploy
`git push origin master` **is** the production deploy (`refresh.yml`) and there is no PR review in
front of it, so push deliberately — typically after a `research → master` merge with tests green.
