# PROGRAM.md — the standing program for autonomous research rounds

Adapted from [karpathy/autoresearch](https://github.com/karpathy/autoresearch) to this
repo's three-stage gate protocol. An agent running a research round follows this file.
It is **read-only during a round** — changes to it are their own reviewed commits,
made between rounds, never mid-round.

## Mission

Improve the model's walk-forward performance under the established adoption gate,
autonomously, one bounded experiment at a time. Within the invariants below, do not
pause to ask the human — the stop conditions bound the run.

Baseline at harness creation (walk-forward 2010–2026, adopted set @ `5c4d012`):

| tour | acc | log-loss | Brier | vs bookmaker anchor (~0.690 acc / 0.196 Brier) |
|------|-----|----------|-------|------------------------------------------------|
| ATP combiner | 0.6958 | 0.5700 | 0.1947 | ahead on both axes |
| WTA combiner | 0.6829 | 0.5878 | 0.2018 | +0.0059 Brier gap — the open target |

These numbers drift as adoptions land. Before citing a baseline anywhere, re-run
`git log` and re-derive from the current tip (lessons.md: stale-metrics lesson).

## Invariants

Read-only during a round:

- **`src/tennis_model/eval/`** — the measuring instrument (tune.py, ab_data.py,
  metrics.py, backtest.py, compare.py). Never modify the ruler mid-experiment.
- **The gate definition**: `TUNE_YEARS=(2010, 2019)`, `VAL_START=2020`, gate
  inequality `d_tune > 0 AND d_val > -1·SE`, both tours for tour-agnostic changes.
- **Existing test assertions** — you may ADD tests; never edit or weaken an existing
  assertion or threshold.
- **Network**: no data downloads mid-round (WTA API rate-limits; data is frozen for
  the round). Record the feature-cache build times in the results doc.
- **Dependencies**: no installs, upgrades, or pins (cross-version pickle
  compatibility is a hard constraint; see CLAUDE.md).
- `.github/`, `web/`, this file, `CLAUDE.md`. `tasks/lessons.md` is append-only.

Git: no `push`, no `git clean` (any flags — the gitignored `data/output/` caches and
study DBs would be destroyed), no force-operations, no amending commits that predate
the round, no committing scratch drivers.

**Simplicity bias** (karpathy): all else equal, simpler is better. A formal gate pass
that buys +0.0005 with ugly permanent complexity is a **DECLINED** — this repo has
used that verdict before (LR raw-blend; top-5-under-bagging probes) and it is an
honest outcome, not a failure.

Modifiable:

- `config.py` — the override dicts (`ELO_/SR_/XGB_/FEAT_PARAM_OVERRIDES`), `N_BAG`,
  feature constants.
- `ratings/`, `points/`, `model/` code — under the parity rule: every walk-time
  signal ships its prediction-time state mirror + parity test **in the same commit**,
  or is recorded venue/context-free (CLAUDE.md hard rule).
- `tasks/research/ledger.tsv` (append-only), `tasks/research/ideas.md` (append +
  status edits), the round results doc, `tasks/todo.md`, `tasks/lessons.md` (append).

## The loop

1. Pick the highest-priority OPEN idea in `ideas.md` (never anything on its
   do-not-retry list).
2. Run `date`; append a ledger row (id, tier, hypothesis, declared budget, clock
   start) **before** starting.
3. Run the tier (commands below). If the declared budget is exceeded by ~50% with no
   gate-relevant signal, verdict `TIMEOUT` and move on.
4. Parse the gate output (stable formats quoted below). Decide the verdict.
5. Keep (adoption path) or revert (`git reset --hard HEAD~1` for committed attempts;
   pure sweeps have nothing to revert).
6. Run `date`; fill in the ledger row (metrics, verdict, clock end), update the
   idea's status, commit the ledger change, loop.

**Clock discipline (R1 lesson): elapsed time is MEASURED, never estimated.** Every
stop-condition evaluation begins with `date` and compares against the recorded round
start. R1 declared a premature wall-clock stop from accumulated duration guesses
that were 5× off — durations in this file are calibration hints, not clocks.

## Tiers

**Tier 0 — probe** (seconds–2 min). Bit-identity checks, baseline reproduction,
reading study DBs. Not ledgered; goes in the parent experiment's notes.

**Tier 1 — component sweep** (budget 30–60 min). One hypothesis, one tour, one fresh
`--tag` (a reused tag RESUMES the old study — that is for continuation only):

```bash
cd tennis_model
export PYTHONIOENCODING=utf-8   # keeps ± readable in captured Windows output
PYTHONPATH=src python -m tennis_model.eval.tune --tour wta --group xgb --trials 12 --tag _r1a
PYTHONPATH=src python -m tennis_model.eval.tune --tour wta --group xgb --validate --top 5 --tag _r1a
```

Per-trial costs MEASURED in R1 on this machine (recalibrate from ledger clock
columns as rounds accumulate): `elo`/`point` ~5–10 s; `feat` ~50–60 s (20 trials +
validate ≈ 20–25 min); `xgb` ~25–35 s (12 trials + validate ≈ 8–10 min incl. frame
build). `--validate` output (stable, parse these lines — `val-yrs` is the per-year
tripwire, added after R1):

```
[wta/xgb] baseline: tune=0.57078  val=0.58950
  #145: tune=0.56993  val=0.58792  d_tune=+0.00145±0.00034  d_val=+0.00046±0.00041  gate=PASS
    val-yrs: 5/7 pos, worst 2024 -0.00130 (t=-2.5)
```

A formal `gate=PASS` with a val-negative `val-yrs` majority is the tune-overfit
signature (4 ATP precedents) — do not spend a Tier-2 on it without a reason.

Best possible Tier-1 outcome is **PASS-comp**. A component pass is NOT adoption —
this repo has four ATP precedents of component-pass → arbiter-veto.

**Tour-parallelism (measured 2026-07-06, feat group / XGB n_jobs=0 worst case: atp
solo 332 s, wta solo 181 s, concurrent pair 417 s = 1.26× the slower solo, ~19%
wall-clock saved).** The two tours of ONE hypothesis MAY run concurrently at Tier 1 —
a modest win, not a doubling. Never run two different hypotheses concurrently, and
Tier-2 arbiters stay strictly sequential: verdict order matters, since an adoption
changes the incumbent every later experiment is measured against.

**Tier 2 — paired arbiter A/B** (budget ~15 min per tour; measured ~7–8 min in R1
for both bagged arms including frame builds). Entry: a Tier-1 pass, or a
code/data change a fixed-frame sweep cannot express. The ONLY tier that can grant
ADOPT. Run BOTH tours when the change is tour-agnostic. Drive it with a scratch
script (scratchpad only, never committed) on `eval/ab_data.py`'s primitives — this is
the canonical shape (see `ab_data.run()` for the data-side variant with `_align`):

```python
from tennis_model.model.features import build_feature_frame, main_rows
from tennis_model.model.train import walk_forward, xgb_params_for
from tennis_model.eval.ab_data import _verdict
feat = main_rows(build_feature_frame(tour="atp"))
base = walk_forward(feat, xgb_overrides=xgb_params_for("atp"))
arm  = walk_forward(feat, xgb_overrides=candidate_params)      # the candidate
_verdict(base, arm)   # same frame -> rows positionally paired; else use _align first
```

`_verdict` prints the windows table, the **per-year paired-d table**, and the final
`GATE:` line. Read the per-year tripwire (lessons.md): a real improvement lifts
(nearly) every year — `17/17 positive` was the A5 signature; bidirectional
many-SE flapping = training-distribution artifact → run the **ratings-only variant**
(a data experiment is two experiments). Save both OOS frames to
`data/output/tuning/` (gitignored) so every verdict stays re-derivable.

**Tier 3 — adoption** (budget ~15 min). Edit `config.py` (or keep the code arm), then:

```bash
cd tennis_model && PYTHONPATH=src python -m pytest -q && ruff check .
```

Both green required. Adoption commit includes the parity mirror + tests. The
production rebuild (`PYTHONPATH=src python -m tennis_model.pipeline --tour all
--backtest`) runs ONCE at round end for the final adopted set, not per adoption.

## Git protocol

- A round runs on `research/YYYY-MM-DD`, cut from `master`. Record the base sha in
  the results-doc header. The user reviews and merges; never push.
- Tier 1 touches no tracked files (candidate params live in the study DB and are
  applied programmatically).
- Tier 2 attempts that change tracked files: commit BEFORE the arbiter run, message
  `exp RN-NNN: <hypothesis>`. On REJECT → `git reset --hard HEAD~1` (safe here:
  `data/output/` is gitignored, caches and studies survive), then append + commit the
  ledger row. On ADOPT → follow-up commit with tests and docs; the pair of commits is
  the adoption.
- The ledger is committed after EVERY experiment — it is the resume point if the
  session dies.

## Ledger — `tasks/research/ledger.tsv`

Append-only, tab-separated, one row per experiment:

```
id  date  tier  tour  group  hypothesis  change  budget_min  d_tune  se_tune  d_val  se_val  yrs_pos  verdict  git  clock  notes
```

- `id` = `R<round>-<seq>`; Tier-2 tour pairs share the seq with `-atp`/`-wta` suffix.
- `d_*`/`se_*`: Tier 1 rows carry component numbers, Tier 2 rows arbiter numbers (the
  tier column disambiguates). `-` where not applicable.
- `yrs_pos` (Tier 2 only): e.g. `17/17`, or `9/17 max0.035` when flapping.
- `verdict` ∈ `PASS-comp | REJECT | ADOPT | DECLINED | TIMEOUT | CRASH | SKIP | BASELINE`.
- `git`: adoption sha, `reverted:<sha>`, or `-`.
- `clock`: measured `HH:MM-HH:MM` local (start stamped at step 2, end at step 6) —
  the source of truth for elapsed time and for recalibrating the tier cost table.

## Stop conditions (earliest wins)

1. Wall-clock budget expires (default 8 h). Finish the in-flight experiment — never
   abandon a half-run arbiter verdict.
2. Plateau: 5 consecutive Tier-2 `REJECT`/`DECLINED` verdicts.
3. `ideas.md` exhausted AND 2 consecutive self-generated ideas rejected.
4. Safety: the incumbent test suite fails, the baseline stops reproducing, or the
   same experiment crashes twice.

## End-of-round consolidation (always runs, even on a safety stop)

1. If anything was adopted: production rebuild + final walk-forward table.
2. Results doc `tasks/tuning-results-YYYY-MM-DD-autoresearch.md` in the established
   format — hypothesis, config, d±SE per window, per-year note, verdict for EVERY
   experiment including rejections, final table.
3. Mirror the outcome into `tasks/todo.md`; append anything methodological to
   `tasks/lessons.md`.
4. Leave the branch for user review. Never push.

## Idea generation

Consult `ideas.md` first. When self-generating: prefer the WTA anchor gap — ATP
already clears the anchor. Respect the do-not-retry list: Elo geometry is a
triple-confirmed plateau (`xsurf` → `_ablend` → `_home` sweeps found identical
optima) — do not re-sweep a confirmed plateau unless the space itself changed (e.g. a
new data regime like A5). Ideas that need downloads are user-supervised only — mark
them `BLOCKED`, do not run them.

**Round zero — ideation fan-out (R1 lesson: ideas, not compute, are the binding
constraint).** At round start — and again whenever fewer than 2 OPEN ideas remain —
fan out 2–3 parallel read-only subagents with distinct lenses before continuing the
loop: (a) data gaps — coverage holes, unexploited columns, ingestible sources already
on disk; (b) feature families — signals the combiner doesn't see, each costed with
its parity-mirror burden; (c) methodology — calibration, weighting, ensembling angles
not yet in the rejection docs. Each subagent proposes candidates with a mechanism
hypothesis and rough tier cost. The ROUND AGENT then triages against ideas.md's
do-not-retry table and the tuning-results docs, appends survivors to ideas.md with
rationale (download-dependent ones marked `BLOCKED`), and discards the rest with a
one-line reason in the round results doc. Subagents propose; only the round agent
writes files or runs experiments.
