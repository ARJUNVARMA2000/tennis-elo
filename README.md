# DEUCE — Tennis Forecast Engine (ATP + WTA)

[![refresh](https://github.com/ARJUNVARMA2000/tennis-elo/actions/workflows/refresh.yml/badge.svg)](https://github.com/ARJUNVARMA2000/tennis-elo/actions/workflows/refresh.yml)
[![tests](https://github.com/ARJUNVARMA2000/tennis-elo/actions/workflows/test.yml/badge.svg)](https://github.com/ARJUNVARMA2000/tennis-elo/actions/workflows/test.yml)
[![live site](https://img.shields.io/badge/live-deuce--forecast.web.app-828fff)](https://deuce-forecast.web.app/)

DEUCE is a production forecasting system for men's and women's professional tennis. It combines
a leakage-free machine-learning pipeline, a resilient multi-source data platform, and a full-stack
web product that turns live tour data into calibrated match, set-score, and tournament forecasts.

**[Open the live app](https://deuce-forecast.web.app/)** ·
**[View the model scorecard](https://deuce-forecast.web.app/scorecard/)** ·
**[Read the methodology](https://deuce-forecast.web.app/method/)**

## At a glance

| | |
|---|---|
| **Product** | Live ATP/WTA scores and forecasts, real tournament brackets, exact what-if scenarios, player dossiers, rankings, and model-vs-market reporting |
| **Model** | 42-feature hybrid: surface Elo + opponent-adjusted serve/return Markov model + context and Match Charting style, fused by a five-seed XGBoost ensemble and Platt calibration |
| **Evidence** | Retrospective annual walk-forward evaluation; corrected 2010–2026 Brier of 0.1963 ATP and 0.2042 WTA, with explicit date-availability limits |
| **Operations** | Hourly data refresh and deployment, daily retraining, weekly recoverable data snapshots, two deployment gates, deduplicated alerts, and an independent liveness watchdog |
| **Stack** | Python, pandas, NumPy, scikit-learn, XGBoost, Next.js 16, React 19, TypeScript, GitHub Actions, and Firebase Hosting |

## Product

- **Live decision surface:** one Match Center combines browser-polled ESPN scores, scheduled model
  calls, completed point-in-time forecasts, evidence behind each call, and a ranked watchlist.
- **Real-draw forecasting:** every connected ATP/WTA bracket can show the actual draw, an exact
  probability path, or a shareable scenario with forced results. Confirmed results are immutable;
  what-if choices never enter model evaluation.
- **Player intelligence:** official-rank and Elo boards, overall and surface ratings, player
  dossiers, forecast performance versus expectation, H2H, recent form, style radars, and a
  serve/return strength map.
- **Model accountability:** walk-forward calibration, a durable live forecast log, and paired
  comparisons with bookmaker closing lines and Kalshi snapshots are published alongside the
  forecasts—not kept in an offline notebook.

## Screenshots

| Slam forecast | Rankings | Playing-style radar |
|---|---|---|
| ![Home — round-by-round slam forecast](docs/home.png) | ![Rankings — Elo board with official live ranks](docs/rankings.png) | ![Playing style — 10-axis radar comparison](docs/style.png) |

## Measured performance

The model combines surface Elo, opponent-adjusted serving and returning, playing style,
and match context. A five-seed boosted-tree ensemble is calibrated in both player
orientations; the final probability averages those orientations so reversing the players
returns the complementary probability.

The corrected retrospective evaluation covers **46,205 ATP and 42,425 WTA matches** in
annual folds from 2010–2026 (2026 is partial), measured on 2026-09-11 UTC after refreshing
the recovery inputs. Market odds are evaluation-only. Exact historical publication times
are not reconstructed; the walk uses verified dates where available and recorded event/round
order otherwise. See the [release measurements](tasks/research/2026-09-10-general-release.md).

| Model (walk-forward 2010–2026) | ATP accuracy | ATP Brier | WTA accuracy | WTA Brier |
|---|---:|---:|---:|---:|
| Surface Elo + cross-surface transfer | 0.682 | 0.2009 | 0.664 | 0.2098 |
| Serve/return point model | 0.669 | 0.2057 | 0.650 | 0.2131 |
| XGBoost combiner (five-seed ensemble) | 0.692 | 0.1963 | 0.677 | 0.2042 |

These figures replace the July headline metrics, which used an asymmetric evaluation path
with the known winner first. Those old numbers are not a valid before/after comparison.
Bookmaker studies also use different populations; the live Scorecard compares market and
model forecasts on matched rows instead.

ATP includes Challenger and qualifying results in rating history while keeping those rows
out of combiner training. WTA keeps separate main-only and qualifying/125-enriched histories,
selecting the enriched history only when either player has fewer than 32 prior main-draw
matches. The existing tuned parameters and selection policy are unchanged by this release.

### How a model change ships

Every candidate constant, feature, or training change must pass the same protocol:

1. Tune on 2010–2019 without looking ahead.
2. Clear a paired per-match difference ± standard-error gate on 2020+.
3. Survive the full walk-forward arbiter with the combiner retrained.
4. Ship its prediction-time state mirror and parity test if it changes walk-time features.
5. Record the result—including rejected experiments—in the research ledger.

Component-level wins are not enough. An event-speed serve baseline, for example, passed its own
component gate in every fold but was rejected when the retrained combiner absorbed it. The
[`research program`](tasks/research/PROGRAM.md) defines the standing protocol, and every attempt is
recorded in the machine-readable [`research ledger`](tasks/research/ledger.tsv).

An optional [`prospective comparison workflow`](tasks/research/PROSPECTIVE.md) freezes an
incumbent and candidate before collecting future paired forecasts. It preserves source and
timing evidence, excludes calls that cannot be proved pre-match, and supplements the arbiter
without changing production predictions or automatically adopting a candidate.

## Architecture

```text
historical + current match data
      │
      ├─ surface Elo
      │    overall + per-surface ratings, cross-surface transfer, dynamic K, margin of victory
      │
      ├─ serve/return point model
      │    opponent-adjusted skill walk → point → game → tiebreak → set → match Markov chain
      │
      └─ context and style
           rest, workload, form, H2H, hand, rank, age, home advantage, Match Charting profile
                              │
                 42-feature XGBoost ensemble (5 fits)
                              │
                       Platt calibration
                              │
              calibrated P(A wins) + set-score distribution
                        ┌─────┴─────┐
                match products   tournament products
                                  ├─ exact propagation through released draws
                                  └─ Monte Carlo simulation for hypothetical fields
```

The system records every feature before its match in one chronological pass. Winner-oriented rows
are randomly sign-flipped during training, so the model cannot learn that the first player is the
winner. The production ensemble averages five deterministically seeded fits; exact dependency pins
protect the serialized model from cross-version drift.

## Data engineering

No single free source is both current and complete. Jeff Sackmann's canonical repositories went
private in 2026, several mirrors froze, and current WTA serve statistics have no maintained bulk
feed. DEUCE therefore merges sources by role and keeps the last validated file when an upstream
fails:

- **Full-schema history:** `Tennismylife/TML-Database` for ATP plus a snapshot-backed WTA archive.
- **Current serve statistics:** daily ATP files from
  [stats.tennismylife.org](https://stats.tennismylife.org); WTA match statistics scraped from the
  first-party wtatennis.com API, including a snapshot-preserved backfill.
- **Lower-tier evidence:** ATP Challenger and qualifying rows feed rating, point, and context state
  from the 2005 warm-up boundary onward, while the combiner still trains and scores on main draws.
  First-party WTA qualifying/125 rows feed a separate secondary state from 2016 onward. A frozen
  main-draw-experience gate uses it only for cold-start matchups; the main-only state is preserved
  for established players and the combiner still trains solely on main draws.
- **Fresh results:** `LuckyLoser91/TennisCourtLog` provides a weekly results overlay; ESPN supplies
  hourly scores, completed results, schedules, and the current event frontier.
- **Rankings, style, and market benchmarks:** live-tennis.eu supplies display-only official ranks;
  the Match Charting Project supplies tactical profiles; Tennis-Data and Kalshi are evaluation-only.
- **Complete draws:** official ATP/WTA main-draw PDFs are preferred. Wikipedia is the complete-draw
  fallback, and ESPN's day-by-day order of play is retained as an explicitly partial frontier.

### Identity and draw integrity

Names are not treated as stable identifiers. Events join on ESPN's `espnId`; sponsor-title and city
aliases are attached to that identity only after calendar and shared-player evidence agrees. An
official draw must overlap the ESPN calendar and match at least 75% of the live field before it can
attach. Player-name canonicalization is implemented in both Python and TypeScript and pinned to one
shared fixture so the model and UI cannot disagree about who a player is.

A separate weekly proposer scans for unresolved identities, sends only deterministic candidates to
a search-enabled model for adjudication, rejects anything contradicted by the match record, and can
open a PR. It never runs in the hourly pipeline, cannot merge its own proposal, and adds no LLM
client to the production dependency set.

## Production operations

```text
hourly at :17 UTC                    daily at 06:00 UTC
ESPN/live draws + rankings           validated source downloads
reuse saved predictor                full rating walk + retrain + backtest
             └──────────────┬──────────────┘
                            ▼
                  pre-deploy output gate
                            ▼
               static Next.js build → Firebase
                            ▼
                    live deploy verifier

Monday full run → rolling raw-data release snapshot
daily watchdog  → alert if refresh.yml has no success within 26 hours
```

The workflow is deliberately failure-aware:

- **Validated, atomic acquisition:** schema or payload failures do not overwrite the last good
  source file. A failed full download does not discard usable data or prevent a retrain; it is
  escalated after the best-effort deploy so the failure remains visible.
- **Pre-deploy integrity gate:** typed `output_findings()` block internally inconsistent artifacts before
  Firebase sees them—missing JSON, impossible draw geometry, placeholder identities, incoherent
  probabilities, or broken cross-file contracts leave the previous good deploy live.
- **Accepted artifact releases:** cached predictors are verified against exact-byte/runtime/configuration
  envelopes before deserialization. Each all-tour run seals one exact ATP+WTA public-data manifest;
  only the gate-accepted release is published, and single-tour/debug runs cannot mutate the live tree.
- **Post-deploy serving gate:** the live verifier checks every route, canonical and crawl metadata,
  cache policy, MIME types, trailing-slash and 404 behavior, the exact freshly generated health
  stamp, every declared release byte/hash/MIME and index edge, known-private/omitted-path 404s,
  event coverage, shard generations, and page-level UI contracts.
- **Actionable monitoring:** every actionable data finding has a stable fingerprint and its own
  independently recoverable GitHub issue—including findings that block before deploy. Serving and
  pipeline failures retain their mode-keyed incident owners. Standing failures suppress repeated
  hourly alerts, leave a daily full-run heartbeat, and close automatically on recovery. A separate
  watchdog covers the failure mode where the refresh workflow itself stops running.
- **Recoverable state:** data and trained artifacts are cached after every run, including late red
  runs; a rolling weekly release snapshot can bootstrap the historical archive if the cache or an
  upstream disappears.
- **Honest source health:** source cadence is interpreted by contract. A missing or invalid Match
  Charting download is actionable, while the age of its volunteer batch data is shown as a coverage
  note rather than misreported as an outage.

Both deployment gates are executable specifications with focused tests:
[`tennis_model/src/tennis_model/data/health.py`](tennis_model/src/tennis_model/data/health.py),
[`tennis_model/tests/test_health.py`](tennis_model/tests/test_health.py),
[`web/scripts/verify-deploy.mjs`](web/scripts/verify-deploy.mjs), and
[`web/tests/verify-deploy.test.ts`](web/tests/verify-deploy.test.ts).

## Engineering quality

- **CI on every code change:** Python and TypeScript tests, Ruff, ESLint, a full TypeScript check
  including test files, and a production static-export build.
- **Deterministic model artifacts:** explicit random seeds, a fixed five-fit ensemble, parity locks,
  and dependencies pinned to the versions used by the production pickles.
- **Point-in-time evaluation:** forecasts are appended before play, graded after results arrive, and
  persisted outside the evictable runtime cache. Bookmaker and Kalshi data never influence a call.
- **Cross-runtime contracts:** identity, bracket math, scenario propagation, artifact schemas, and
  output generations are checked across the Python producer and TypeScript consumer.
- **Web quality:** responsive navigation, keyboard-accessible ARIA controls, screen-reader live-score
  labels, non-color indicators, canonical URLs, structured metadata, and immutable caching only for
  content-hashed assets.

## Repository layout

```text
tennis_model/                  Python model and data pipeline
  src/tennis_model/data/      acquisition, normalization, identity, draws, health
  src/tennis_model/ratings/   chronological overall and surface Elo walks
  src/tennis_model/points/    opponent-adjusted serve/return model and Markov math
  src/tennis_model/model/     features, training, prediction, export, watch ranking
  src/tennis_model/sim/       exact bracket propagation and Monte Carlo simulation
  src/tennis_model/eval/      backtests, tuning, market comparison, forecast ledger
web/                          Next.js 16 / React 19 static application
.github/workflows/            CI, hourly/daily refresh, watchdog, identity proposer
tasks/                        experiment logs, research ledger, decisions, and lessons
```

The model package has a deeper module and methodology guide in
[`tennis_model/README.md`](tennis_model/README.md).

## Run locally

The recovery snapshot preserves WTA serving statistics and adopted qualifying/125 history
that current downloads cannot reconstruct. Restore it before refreshing current sources.

```bash
# Model and data pipeline
cd tennis_model
gh release download data-archive --pattern 'raw-archive.tar.gz' -O /tmp/raw-archive.tar.gz
PYTHONPATH=src uv run --with-requirements requirements.txt \
  python -m tennis_model.data.raw_archive restore /tmp/raw-archive.tar.gz

PYTHONPATH=src uv run --with-requirements requirements.txt \
  python -m tennis_model.data.download --kind all
PYTHONPATH=src uv run --with-requirements requirements.txt \
  python -m tennis_model.pipeline --tour all --backtest

# Ad-hoc calibrated prediction
PYTHONPATH=src uv run --with-requirements requirements.txt \
  python -m tennis_model.cli predict "Jannik Sinner" "Carlos Alcaraz" --surface Hard --bo 5

# Web application (reads the JSON mirrored into web/public/data)
cd ../web
npm ci
npm run dev
```

Run the verification suites from their package roots:

```bash
cd tennis_model && PYTHONPATH=src uv run --with-requirements requirements.txt pytest -q
cd ../web && npm test && npm run lint && npx tsc --noEmit && npm run build
```

## Current limitations

- WTA qualifying and 125-level history begins in 2016, so the adopted gate improves cold-start
  players rather than providing the long warm-up that ATP Challenger history does. Established
  matchups deliberately stay on the main-only state.
- Hypothetical-field simulations use current ratings. A historically faithful tournament
  simulation would require reconstructing every player's rating state at the event date.
- Match Charting is a volunteer, batch-updated dataset. Its age describes tactical-feature coverage,
  not source transport health; missing profiles degrade to neutral style features.
