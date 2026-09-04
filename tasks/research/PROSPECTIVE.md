# Prospective candidate comparisons

Use `tennis_model.eval.prospective` to compare a frozen incumbent and a frozen candidate
on newly arriving matches. Registration fixes the hypothesis, capture horizon, target sample,
and exact predictor artifacts before the first observation. This supplements the full
walk-forward arbiter; it cannot adopt a model or alter production forecasts.

Both artifacts must load under the current strict predictor contract. This supports candidates
with compatible inference code and state schemas. A candidate requiring different code or a
different runtime needs a separately designed runner; do not bypass artifact validation.

From `tennis_model/`, register **real, distinct fitted artifacts** before collecting:

```bash
PYTHONPATH=src uv run python -m tennis_model.eval.prospective register \
  data/prospective/candidate-name --tour atp \
  --hypothesis 'State the expected improvement before observing results' \
  --incumbent data/output/atp/predictor.pkl \
  --candidate /absolute/path/to/candidate.pkl --days 30 --min-pairs 200
```

The supplied folder must not exist. Registration saves private frozen copies of both
predictors and their envelopes, then publishes the registration receipt. It never replaces
an experiment. A failed registration can leave an incomplete folder, which cannot capture
forecasts. Preserve the folder for diagnosis and use a new name when retrying.

## Capture

Provide a fresh, independently observed schedule JSON. The following is a **schema example**;
replace every example value with actual current source evidence:

```json
{
  "tour": "atp",
  "observedAt": "2026-09-04T12:00:00Z",
  "sourceUrl": "https://example.com/schedule",
  "matches": [{
    "espnId": "123-2026", "season": 2026, "round": "R32",
    "playerA": "Player A", "playerB": "Player B", "status": "scheduled",
    "earliestStartAt": "2026-09-04T16:00:00Z",
    "surface": "Hard", "bestOf": 3,
    "context": {
      "event": "Example Open", "as_of": "2026-09-04T16:00:00Z",
      "indoor": false, "tier_k": 1.0, "round_order": 3
    }
  }]
}
```

Use the exact canonical player names present in both artifacts. Event identity is `espnId`,
season, round, and unordered normalized player pair; sponsor names never join records.
Context must be the same verified context used to price the scheduled match.
`earliestStartAt` must be a defensible lower bound on play, not an estimated finish time or
a mutable provider timestamp whose meaning is unknown. If only the local match date is known,
use that day's midnight with its venue timezone offset and capture on the preceding day.
Missing evidence means no eligible forecast.

```bash
PYTHONPATH=src uv run python -m tennis_model.eval.prospective capture \
  data/prospective/candidate-name /absolute/path/to/schedule.json
```

The observation must be no more than ten minutes old. Both predictions must finish at least
five minutes before the lower bound on play. Capture timestamps come from the local clock
after inference; the CLI has no backdating option. Each arm uses its frozen state throughout
the registered horizon, so this measures two fixed artifacts, not two daily retraining policies.
Retries retain the first paired receipt. Unknown entrants, missing context, in-progress rows,
and uncertain timing are excluded and counted. Source observations are retained even when no
forecast is eligible. Changed frozen files or duplicate identities fail closed.

## Grade

Provide result JSON with `tour`, `observedAt`, `sourceUrl`, and a `matches` array. Each result
needs the same identity fields, plus `status`, `winner`, `actualStartedAt`, and `finishedAt`.
Use `completed` only for a normally completed match. Use `retired`, `walkover`, `withdrawn`,
or `cancelled` for those outcomes; they are excluded from primary paired scoring.
Unknown results stay pending. A completed match without actual-start evidence is excluded.

```bash
PYTHONPATH=src uv run python -m tennis_model.eval.prospective grade \
  data/prospective/candidate-name /absolute/path/to/results.json
```

The grader retains the result evidence and reports common-pair log loss and Brier,
incumbent-minus-candidate deltas, paired sample SE, pending counts, and exclusions. Positive
delta favors the candidate. Singleton SE is unavailable. Match SE is descriptive and does not
correct event/player dependence. The target count and horizon are reported separately;
neither means automatic adoption. Evaluate at the registered endpoint and retain unsuccessful
experiments too, rather than stopping when a favorable score appears.

No experiment or scheduled collector is enabled by installing this code. Once an actual
candidate is selected, register it and arrange capture using trustworthy schedule evidence.
Keep the complete experiment directory durable and private; it contains predictor binaries.
There is no public-data mirror or production pipeline dependency.
