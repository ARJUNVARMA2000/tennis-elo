# Historical error round — fixed shortlist

Current status: completed, no finalist. See [results](2026-09-08-historical-error-review.md). The text below records the pre-fit rationale.

Registered before fitting any new candidate. Read the private `runs/historical-errors/shortlist-registration.json` for exact clock, selection rule and bounds.

- HIST-01: neutralize rest/log-days/layoff pair features when one participant has no earlier recorded match. First appearance is not a known 365-day absence. One fixed variant. This replaces missing-value semantics, not a missingness flag or a layoff sweep.
- HIST-02/03: cap one player-match's serve and return evidence at 40/80 points while preserving point rates and chronological prior policy. This is player-state contribution weighting, not the rejected combiner tier/recency weighting or rate-prior family. Two fixed variants.

WTA screen, unchanged five-bag walk-forward, main-only fitting and threshold32 scored state. No new columns. For eligibility require positive tune gain,6/10 positive years, and positive pooled gain in both tune halves. Pick maximum tune gain; exact ties favor simpler implementation. At most one overall finalist. A selected tour-general mechanism must also face the unchanged ATP arbiter without tuning another setting. Reused 2020+ is validation, not independent confirmation.

The 26,794 incumbent tune probabilities have been reproduced bit-for-bit. Initial and refined diagnostics are recorded in CSVs. Underconfidence in first recorded appearances is descriptive evidence; the causal explanation is a hypothesis. The point-cap mechanism has weaker evidence and may simply discard useful information. Neither has been fitted yet.

Discarded before fitting: conditional calibration/temperature (closed calibration family), surface evidence/missingness flags (closed), serve-point-count asymmetry (explicit July6 discard), score-margin/latent strength models (closed), and another source/clock survey (outside this round). No third mechanism is invented.
