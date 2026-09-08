# Official draw identities — implementation and continuation review

The official schedule source can now be associated with the existing WTA/ESPN event
and match identities through a tested external audit. Implementation:
`aab6ed05d66bac514e5b6d3903cb7924b06b6aff` on `codex/model-official-link`, based on accepted
`70f5976cd9eb07ec5757674f5966c81b30c31477`. Git was reconciled before this review.

Read the [contract](2026-09-08-official-link-interface.md),
[result manifest](2026-09-08-official-link-result.json) and
[next-session instructions](2026-09-08-official-link-next.md).

## Actual observations

Exactly four HTTP reads were made: the current official catalogue/day-17 order, then
the official draw index and its WS draw. All succeeded without retries. The draw URLs
were derived from the retained official site configuration and the actual draw index.
No unofficial endpoint list, account, subscription or provider contact was used.

The schedule observation at **2026-09-08 04:31:11.178276 UTC** remains unchanged. The
combined history contains six WTA match identities and ten versions, with no observed
revision or gap. The catalogue lists days 18–22 as unreleased with null feed URLs.
The two current singles rows use session-start times, not explicit not-before labels.

The official WS draw was acquired at **2026-09-08 04:32:09.560676 UTC**. It has all 127
main-draw match slots: 120 labelled completed and seven pending. Four pending quarterfinals
have real players, while three semifinal/final slots are unresolved. The primary URLs
are [official draw index](https://www.usopen.org/en_US/scores/feeds/2026/draws/draws.json)
and [official WS draw](https://www.usopen.org/en_US/scores/feeds/2026/draws/WS.json);
the manifest pins the exact bytes because the live URLs will change.

## Identity evidence and exclusions

| Check | Actual result |
| --- | ---: |
| Official draw slots / slots with two real players | 127 / 124 |
| Completed results corroborated across official draw, WTA and ESPN | 119 |
| Strict match links with per-player number agreement | 100 |
| Matchups excluded for differing player numbers | 23 |
| Real official matchup absent from the older provider snapshot | 1 |
| Unresolved official future slots | 3 |
| Saved schedule versions successfully associated | 10 |

Event identity uses explicit edition plus broad agreement on canonical players, round,
winner and set games. It corroborates WTA event `905` and ESPN event `189-2026`; titles
are not join keys. Match links additionally require the official `wta`-prefixed number
to agree with the WTA PlayerID **for the same player**, including correct side alignment.

For 23 matchups, results and names agree but the numbers differ. For example, Venus
Williams is `wta230220` in the official draw and `18251` in the retained WTA match row.
The audit preserves both claims and excludes the affected link. It does not infer an
alias, declare which ID system is wrong or change `config.py` identity tables.

Of the 100 strict links, 96 have normal completed agreement, one has later official
completion against older live provider observations, and three are scheduled matchups.
The progression case is retained as a status difference, not labelled a terminal
contradiction. Conflicting completed outcomes, malformed terminal evidence and identity
replacements are explicit exclusions in tests and in the audit contract.

Every associated schedule retains its original receipt and observation time. Its separate
association-available time is no earlier than **04:32:09.560676 UTC**, the latest contributing
source observation. Old WTA/ESPN receipts remain around 00:26–00:27 UTC. This is a
retrospective association, not context available to a hypothetical earlier forecast.

## Timing and sample-size limits

The 2026 Grand Slam rulebook describes not-before orders, consultation over schedule
changes, and first serve as match commencement (printed pages 9, 17, 18). It does not
independently verify an API clock or establish that an observed match obeyed its schedule.
The primary actual-start premise remains unmet. [Official rules](https://www.itftennis.com/media/5986/grand-slam-rulebook-2026-f2.pdf).

There are only **seven pending women's singles slots** in this actual draw. Even perfect
collection of all seven cannot meet the existing 200-pair coverage threshold. A usable
30-day evaluation needs more tournament coverage, as well as qualified start evidence.
A future US Open order is not guaranteed to contain an explicit not-before singles row.
Do not keep repeating this unchanged overnight sample in hopes of creating those facts.

## Verification and preservation

The 29 new tests passed initially; the combined collector/source/bounds checks then passed
**175 tests in 5.32 seconds**. Ruff and whitespace checks passed. The real archive CLI
produced 100 links, 27 exclusions and ten associated schedule versions. Tests cover broad
and weak event overlap, names that change, side swaps, ID discrepancies, malformed or
duplicate slots, terminal contradictions, provider lag, tampered receipts and permanent
exclusion of a schedule identity conflict across reversion.

At **2026-09-08 04:43:42.247703 UTC**, preservation checks confirmed all 553 previous run
files, 91 frozen package files, both models and all 360 preexisting tracked files in the
program/web/workflow trees were unchanged. Eleven completed prior research checkouts
were clean. Only 33 inherited tracked data files exist here; there is no raw training
directory or new training-data copy. Full original training/snapshot inventories were
last verified at 01:58:44 UTC and were not rehashed this phase.

This phase adds 19 retained run files; next protection inventory is **572 files**.
The result pins both private driver hashes, source receipts, code/fixture hashes and all
run hashes. Development notes include a corrected exploratory set-score representation
comparison and one missing guessed receipt path; neither entered the accepted output.
The rule note's manually entered 04:30 timestamp is an approximate session marker, not
a measured source acquisition receipt; only its date/page references support this review.

No model/evaluator/collector code was changed: the addition is `usopen_identity.py`, its
tests and two small exact draw fixtures. No live producer, forecast, fit, account,
unattended cadence, production merge, push or deployment was created.

**Decision:** L0–L3 complete for this bounded continuation. Identity validation advanced
while later match progression was unavailable. The next work is actual later-stage
collection plus wider official tournament coverage and a justified timing premise;
the detailed handoff states the dependencies without promising automatic execution.
