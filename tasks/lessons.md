# Lessons — index

One line per lesson. Read the topic file for the area you are touching; do not read them
all. Full entries live in `lessons/<topic>.md` — grep the lead line to find one.

New lesson → append the entry to the matching topic file and add its lead line here.

## Data sources & freshness — [`lessons/data-sources.md`](lessons/data-sources.md)

- One mistyped date in an upstream row can empty a whole tour, because the date-relative windows anchor on the dataset's MAX date, not on today. (2026-07-25)
- A transport that answers 200 with the WRONG BYTES must not end a fallback chain — and a retry cannot fix a payload the source is serving on purpose. (2026-07-24)
- A freshness gate on a REDUNDANT source needs a load-bearing predicate — an unfixable upstream freeze otherwise stands red forever. (2026-07-10)
- Verify a source's naming convention per file, not per format. (2026-07-02)
- Both tours' `fresh` files live in ONE repo, so one bad minute reds the daily retrain. (2026-07-21)
- Label rows by what they ARE, not by which directory they arrived in. (2026-07-25)
- The release snapshot is load-bearing data that `download` cannot reproduce. (2026-07-25)
- An incomplete source moves only `n`, and nothing was watching `n`. (2026-07-25)

## Draws, rounds & live events — [`lessons/draws-and-live-events.md`](lessons/draws-and-live-events.md)

- A name-set invariant must exclude the slots that don't name anyone. (2026-07-24)
- A gate invariant that compares two DERIVED quantities must derive both sides exactly as the code that produced them — and be validated against messy real draw states, not one clean snapshot. (2026-07-13)
- A completed-event projection must filter the ratings frame to main-draw ROUNDS before constructing its field. (2026-07-11)
- Live-event surface has ONE authoritative source (Wikipedia's main article) and must be fixed at the loader source, not the prediction points. (2026-07-08)
- ESPN can't give a full draw at release — Wikipedia can; three traps when adding it. (2026-07-08)
- Live tournament reach-odds must be seated on the ACTUAL draw, not a rating re-seed. (2026-07-08)
- A live feed's round label is draw-relative — resolve it against draw size, not the label/number alone. (2026-07-08)

## Gates & health checks — [`lessons/gates-and-health.md`](lessons/gates-and-health.md)

- Validate a gate invariant against the full tour CALENDAR, not the events in flight the week it ships. (2026-07-10)
- Python `json.dump` emits a bare `NaN`, which the browser's strict `JSON.parse` REJECTS — one non-finite float blanks a whole page, and every Python-side check passes it. (2026-07-09)
- A correctness check that runs AFTER deploy can't stop a wrong deploy — gate before, on every mode. (2026-07-09)
- Two timestamps that look like one: "when was this written" vs "when was this trained". (2026-07-25)

## CI, alerts & deploy — [`lessons/ci-and-deploy.md`](lessons/ci-and-deploy.md)

- An alert must never report the failure of its own transport as the thing it monitors. (2026-07-24)
- A static host's DEFAULT cache is a staleness bug for an hourly-refreshed site — and `firebase.json` cannot document its own reasoning, because it must stay strict JSON. (2026-07-16)
- Retiring a host is not the same as taking it down: GitHub Pages serves its LAST build forever. (2026-07-16)
- A "successful" static-hosting deploy proves the upload returned 200, NOT that the live URL serves correct/fresh content — verify the live artifact post-deploy, with propagation-lag tolerance built in. (2026-07-17)
- CI dedup/state must not live in an artifact that only persists on success when the mechanism itself reds the job. (2026-07-10)
- Pin dependencies to the environment that owns the production artifacts, not the dev machine. (2026-07-02)
- A lockfile regenerated on one OS can be incomplete for another. (2026-07-02)
- `cancel-in-progress: true` on the deploy concurrency group silently drops changes. (2026-07-09)
- An `if: always()` alert step must distinguish `skipped` from `failure`. (2026-07-21)
- Inline workflow `run:` shell is untestable, and that is where the false alarm hid. (2026-07-21)
- Never key a decision off *which* cron GitHub says fired. (2026-07-25)
- A `run:` block is `bash -e`, so the second command is conditional on the first. (2026-07-25)
- GitHub drops scheduled slots; claim the work, don't match the clock. (2026-07-27)

## Web app — [`lessons/web.md`](lessons/web.md)

- Next 16/Turbopack drops SOME same-line spaces after JSX interpolations — put {" "} between any expression/element and following prose, and verify the RENDERED text. (2026-07-10)
- A URL↔state bridge must apply URL→state only on NAVIGATION, and a client "redirect page" must hard-navigate. (2026-07-09)
- A Δ-metric card must compute the sign its own caption promises — and match its neighbours' convention. (2026-07-09)
- Public method-page copy hardcodes tuned constants and cadences — re-verify it after adoptions. (2026-07-09)
- A new data-backed web page is a 6-part contract; miss one and it silently half-works. (2026-07-08)

## Model & research — [`lessons/model-research.md`](lessons/model-research.md)

- A frozen-field policy needs a VALIDITY predicate, not a kind check — and every "who quotes when" race is a leak vector. (2026-07-09)
- Odds-source coverage can silently truncate an eval window — census the books per era, don't trust the frame. (2026-07-09)
- A combiner feature that adds no new state is a pre-paid loss: budget a ~0.0003 LL capacity toll for any new column. (2026-07-06)
- The tuning feature cache is regime/schema-keyed, not param-keyed. (2026-07-06)
- A data-ingestion experiment is two experiments; separate them or the gate measures the wrong thing. (2026-07-05)
- Re-read the git tip immediately before finalizing any plan or doc built from exploration. (2026-07-05)
- Never include the current estimate in the residual it learns from. (2026-07-02)
- A feature that walks can't be adopted unless the pickled state can replay it. (2026-07-02)
- An API field's semantics can mutate over an object's lifecycle — validate on the SETTLED objects you'll actually score, not the live ones you explored. (2026-07-07)
- Duplicated construction sites drift: production shipped WTA pickles with fp=None. (2026-07-09)
