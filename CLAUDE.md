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
- Model changes are adopted only via the full walk-forward arbiter gate (paired d±SE; tune 2010–19 / val 2020+). Component-level sweep wins are NOT adoption.
- Every walk-time feature ships with its prediction-time state mirror + parity test in the same commit, or is recorded venue/context-free.
- Pin Python deps from the last successful CI run's install log, never local `pip freeze` — cross-version pickle compatibility is the constraint.
- After changing web deps: `npm install --package-lock-only`, then verify with `npm ci` (Windows-generated lockfiles can miss Linux optional deps).
- WTA API rate-limits (429s after ~2k calls): backfill one year at a time; CI incremental refresh is safe.
- Before finalizing any doc/plan that cites repo facts (metrics, features, file lists), re-run `git log` and reconcile with what exploration saw.
