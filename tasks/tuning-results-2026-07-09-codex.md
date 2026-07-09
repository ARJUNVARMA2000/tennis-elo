# Tuning results — 2026-07-09 (autonomous research round R3)

Base `605ff12b6f588b0b458dea7b37f735b217001000`; branch
`research/2026-07-09-codex`. Started 18:44 EDT and ended 19:48 EDT (1h04m of the
default 8h budget). Data was frozen, no dependencies or evaluator files changed,
and nothing was pushed. The initial incumbent suite passed (226 pytest tests).

Protocol: tune 2010–19 / validation 2020+, paired per-match log loss; full bagged
walk-forward arbiter decides adoption. Every candidate below was scored on identical
row sets with a zero-column or rebuilt-frame control as appropriate.

## Round-zero triage

- `seedf` is **BLOCKED**: historical seeds exist, but the scheduled-match contract
  contains no seeds. The Wikipedia draw cache would require a separate data-identity
  and missingness experiment before it can satisfy prediction parity.
- `retd` is **DECLINED** at Tier 0. The proposed late-retirement injury mechanism
  lacks its required direction: next-match win rates are WTA 53.4% after early vs
  54.0% after late retirements; ATP 50.6% vs 53.1%. It would only reopen the already
  rejected `ret_recent` family with more state.
- Self-generated `mcp-shortwin` is **DECLINED**. Two-player charting coverage jumps
  from 22.9% in WTA tune to 68.4% in validation, a star-biased regime shift that
  makes the proposed two-column feature inadmissible.

## Experiments

**R3-001 — REJECT: 3-year rolling H2H difference (`h2hr`, both tours).**
The candidate maintained dated pair outcomes, globally pruned stale pairs in the
saved state, and passed the actual upcoming-match date into the inference mirror.
It is genuinely new state, but requires both tours. WTA narrowly passed its local
gate (d_tune **+0.00021±0.00008**, d_val **+0.00005±0.00010**, 10/17 years
positive). ATP rejected (d_tune **−0.00004±0.00006**, d_val
**−0.00014±0.00007**, 6/17 positive). The complete feature was reset.

**R3-002 / R3-003 — REJECT: WTA rate-conditioned low-sample serve prior (`srrp`).**
This was deliberately distinct from the closed E1 combiner feature block: decayed
ace/DF/first-in rate state supplied only a small prior for the existing
opponent-adjusted SPW estimate, disappearing as direct service-point evidence grew;
no combiner columns were added. A five-strength component sweep plateaued at 0.25:
d_tune **+0.00009±0.00004**, d_val **+0.00005±0.00005**, 6/7 validation years
positive. The full WTA arbiter vetoed it: d_tune **+0.00004±0.00007**, d_val
**−0.00043±0.00010**, 8/17 years positive; 2022 alone was −0.00147 (t=−6.1).
This is the component-pass/combiner-veto pattern, so the code was reset.

**R3-004 — REJECT: raw ordinal-rank difference (`rankord`, WTA-first,
self-generated).** Historical WTA pair coverage was 96.5%, and the existing live
official rankings cache covered all current upcoming players, with latest historical
rank as a fallback. Yet the full WTA arbiter failed: d_tune **+0.00017±0.00012**,
d_val **−0.00024±0.00014**, 11/17 years positive. The conspicuous tripwire is
2024/25 at −2.9/−3.0 SE. ATP was not run: the WTA-targeted arm already failed its
gate. The feature and prediction mirror were reset.

## Decisions and stop condition

**No adoption.** All trial code was reverted; the production feature schema and
point model remain the incumbent. Saved OOS frames remain in ignored
`data/output/tuning/` for re-derivation.

Stop condition 3 applies: the backlog is exhausted after `seedf` became blocked and
the listed experiments closed, and two consecutive self-generated ideas failed
(`mcp-shortwin` declined on a coverage-regime safety check; `rankord` rejected by
the full arbiter). No production rebuild is warranted because nothing was adopted.

## Final ledger delta

| id | verdict | tune d±SE | validation d±SE |
|---|---|---:|---:|
| R3-001-wta | REJECT (tour-agnostic ATP veto) | +0.00021±0.00008 | +0.00005±0.00010 |
| R3-001-atp | REJECT | −0.00004±0.00006 | −0.00014±0.00007 |
| R3-002 | PASS-comp | +0.00009±0.00004 | +0.00005±0.00005 |
| R3-003-wta | REJECT | +0.00004±0.00007 | −0.00043±0.00010 |
| R3-004-wta | REJECT | +0.00017±0.00012 | −0.00024±0.00014 |
