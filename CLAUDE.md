# Tennis Elo — project notes

Read `tasks/lessons.md` before any non-trivial work. New lessons about this codebase go there (committed), not auto-memory.

## Map
- `tennis_model/` — Python pipeline, src-layout (run with `PYTHONPATH=src` from `tennis_model/`). Elo: `src/tennis_model/ratings/`; point model: `points/`; combiner: `model/train.py`; per-tour tuned constants: `src/tennis_model/config.py` (`*_PARAM_OVERRIDES`).
- `web/` — Next.js app (dev server :3001, config in `.claude/launch.json`); reads JSON mirrored to `web/public/data/`.
- `tasks/` — `todo.md` (active checklist), `lessons.md`, `tuning-results-*.md` (experiment logs).
- CI — `test.yml`: pytest + ruff, eslint + vitest + build, every push. `refresh.yml`: daily FULL retrain, hourly QUICK live-score refresh.
- Architecture and how-to-run: root `README.md` and `tennis_model/README.md` — don't duplicate them here.

## Everyday commands (bash)
```bash
cd tennis_model && PYTHONPATH=src python -m pytest -q     # Python tests
cd tennis_model && PYTHONPATH=src python -m tennis_model.pipeline --tour all --backtest   # full retrain (slow)
cd web && npm test && npm run lint                        # web tests + lint
```

## Hard rules
- The web JSON ships through a pre-deploy integrity gate: `PYTHONPATH=src python -m tennis_model.data.health --gate` (wired into `refresh.yml` before build/deploy, both full and quick). It fails the deploy on internally-inconsistent output — impossible odds, `aliveCount>drawSize`, a live event naming a champion, a non-standard-size "real" draw, placeholder-name leaks, missing/corrupt required JSON. Keep it green. When the user catches a NEW "shipped-wrong" class, the fix isn't just the bug — add the invariant to `health.py`'s `output_problems()` (+ a `test_health.py` case) so the gate catches it next time instead of the user.
- Model changes are adopted only via the full walk-forward arbiter gate (paired d±SE; tune 2010–19 / val 2020+). Component-level sweep wins are NOT adoption.
- Every walk-time feature ships with its prediction-time state mirror + parity test in the same commit, or is recorded venue/context-free.
- Pin Python deps from the last successful CI run's install log, never local `pip freeze` — cross-version pickle compatibility is the constraint.
- After changing web deps: `npm install --package-lock-only`, then verify with `npm ci` (Windows-generated lockfiles can miss Linux optional deps).
- WTA API rate-limits (429s after ~2k calls): backfill one year at a time; CI incremental refresh is safe.
- Before finalizing any doc/plan that cites repo facts (metrics, features, file lists), re-run `git log` and reconcile with what exploration saw.

## Git & deploy
- Direct `git push origin master` is allowed and auto-approved (allow-listed in `.claude/settings.json`) — no per-push approval needed. It triggers the production deploy (`refresh.yml`) and bypasses PR review, so push master deliberately: typically after a `research → master` merge with tests passing. Force-push to master (`git push --force origin master`) stays denied as a history-safety backstop.
