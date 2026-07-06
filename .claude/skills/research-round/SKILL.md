---
name: research-round
description: Run an autonomous model-research round (autoresearch loop) — bounded tuning experiments gated by the walk-forward arbiter, logged to the research ledger. Use when the user asks to run a research round, an autoresearch round, or overnight model tuning. Args: a wall-clock budget like "8h" (default), an experiment cap like "5 experiments", or "smoke" (single 5-minute harness check).
---

# Research round launcher

This skill only launches the loop. ALL rules live in `tasks/research/PROGRAM.md` —
read it in full before the first experiment, along with `tasks/lessons.md`, the tail
of `tasks/research/ledger.tsv`, and `tasks/research/ideas.md`. Do not duplicate or
paraphrase the program's rules from memory; the file is the authority.

## Arguments

- `8h` / `30m` — wall-clock budget (default 8h).
- `N experiments` — stop after N ledger rows instead.
- `smoke` — harness check: exactly ONE Tier-1 experiment
  (`--tour atp --group elo --trials 30 --tag _smoke`, ~5 min), one ledger row,
  then stop. Expected honest verdict: REJECT (the Elo plateau is triple-confirmed).

## Preconditions (abort the round if any fails)

1. Working tree clean (`git status --porcelain` — untracked scratch is tolerable,
   modified tracked files are not).
2. Incumbent suite green: `cd tennis_model && PYTHONPATH=src python -m pytest -q`.
3. Record `git rev-parse HEAD` as the round's base sha.
4. Create/checkout the round branch: `git checkout -b research/YYYY-MM-DD` (today's
   date; if it exists, check it out and RESUME from the ledger tail — the ledger is
   append-only, so re-entry is idempotent).

## Run

Follow `tasks/research/PROGRAM.md`: the loop, the tiers, the gate parsing, the git
protocol, the stop conditions, the end-of-round consolidation. Within its invariants,
do not pause to ask the user.

For overnight resilience the user can wrap this skill in a loop
(`/loop /research-round 8h`); because preconditions re-check on entry and the ledger
is the resume point, a re-invoked session continues where the last one stopped.
