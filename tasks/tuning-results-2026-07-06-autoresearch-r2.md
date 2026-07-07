# Tuning results — 2026-07-06 (autoresearch round R2: widened-layoff probe + ideation fan-out harvest)

Second round under `tasks/research/PROGRAM.md` (ledger ids R2-*). Branch
`research/2026-07-06` fast-forwarded to base `cf241f8`; started 22:10 EDT, budget 8 h.
Protocol unchanged: tune 2010–2019 / validation 2020+; Tier-1 component sweeps screen,
the full bagged arbiter (`_verdict`, per-year paired-d table) decides. Data frozen; no
downloads. Incumbent at round start: ATP 0.6958 acc / 0.5700 LL / 0.1947 Brier,
WTA 0.6836 / (post-fp1) / 0.2015.

## Round-zero ideation fan-out

Backlog held one OPEN idea (fp3) → the <2-OPEN trigger fired. Three read-only scouts
(data gaps / feature families / methodology) proposed 18 candidates; triage against
the do-not-retry table and rejection docs kept 8 (appended to `ideas.md` as items
6–13: eloSx, sconf, mty, h2hr, tierw, seedf, retd, pooled) and discarded 9:

- **sr_form_trend** (serve-skill 30-day trend) — new rolling state + high WTA noise
  risk for a speculative mechanism; simplicity bias.
- **h2h_surface_ratio** — monotone recombination of columns already in the frame;
  XGB gains nothing new to split on.
- **srv_pts_asymmetry** — subsumed by log_min_srv_pts + exp_diff.
- **convex Elo/combiner blend** — adjacent to rejected LR raw-blend (W3b); scout's
  own EV estimate straddles zero; adds a production component.
- **Brier-aligned early stopping** — sub-gate-threshold EV; requires full hyperparam
  re-tune to compare fairly, so cost ≫ plausible gain.
- **missingness indicators** — redundant with experience/count features already in
  the frame; "is_newcomer by another name".
- **UNFINISHED-GAMES depth** — strictly weaker variant of retd (kept as item 12).
- **TIEBREAK-POINTS clutch** — ultra-sparse (~30% of matches), noisy, weak main
  effect at best.
- **SURFACE-SERVE-BASELINE re-enable** — do-not-retry (E3, 4th ATP component-pass /
  arbiter-veto); the A5 shift does not reopen it (scout concurred: BLOCKED).

One scout premise was corrected during triage: the combiner window is already
expanding-from-1991 (`train.py:240`), so "rolling→expanding" is moot; the salvaged
knob is the `min_train_year` floor (ideas.md item 8, mty).

## Experiments

(filled as the round proceeds; every experiment gets a verdict entry)
