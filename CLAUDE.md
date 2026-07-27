@./AGENTS.md

# Claude Code only

The project rules live in `AGENTS.md` (imported above) so that Codex reads them too — it does not
read `CLAUDE.md`. Put shared rules there, not here.

- `/code-review` on the working diff before pushing master; `/simplify` for quality-only passes.
- The `research-round` skill runs an autonomous tuning round; its rules live in
  `tasks/research/PROGRAM.md`, which is the authority — don't paraphrase them from memory.
