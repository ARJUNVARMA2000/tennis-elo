@./AGENTS.md

# Claude Code only

The project rules live in `AGENTS.md` (imported above) so that Codex reads them too — it does not
read `CLAUDE.md`. Put shared rules there, not here.

- `/code-review` on the working diff before pushing master; `/simplify` for quality-only passes.
- The `research-round` skill runs an autonomous tuning round against the arbiter gate.
- `.claude/settings.json` holds the committed permission allow-list (read-only inspection plus the
  test/lint/build gates run unprompted; `git push origin master` is allow-listed, force-push denied).
- `.claude/launch.json` defines the `web` dev server on :3001 for the preview tools.
