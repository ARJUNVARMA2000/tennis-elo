# Draws, rounds & live events

Bracket construction, round resolution, projections, live feeds and surfaces.

Indexed in [`../lessons.md`](../lessons.md).

- **A name-set invariant must exclude the slots that don't name anyone.** (2026-07-24, issue
  #9) The "one event under two names" check intersected the two events' `projection` name
  sets, but unresolved draw slots are `Qualifier 1..N`, numbered *per draw* — so any two
  concurrent events with open qualifying "share" a dozen identical strings that are not
  players. Washington ('Mubadala Citi DC Open', WTA 500) and Memphis (WTA 250) run the same
  week with completely different fields (Pegula/Svitolina vs Alexandrova/Golubic) and were
  reported as one renamed event on **20 shared placeholders and 0 shared players**. Fixed by
  filtering through `sim.bracket.is_real`, the same predicate the draw machinery uses to fill
  those slots. Second-order trap worth keeping: removing the placeholders also removed the
  *counts*, so the `>=3 shared` threshold alone then let a genuine rename through on the day
  a draw drops with only 2 names in it — hence the added containment rule (one real field
  wholly inside the other, both >=2 names), which is the same impossibility at small size.
  Extends the drawSize/placeholder lesson below: this is the third invariant in this file
  broken by `Qualifier N` slots, so treat "does this comparison count placeholders?" as a
  standing checklist item for any new draw-shape or field-overlap gate.

- **A gate invariant that compares two DERIVED quantities must derive both sides exactly as
  the code that produced them — and be validated against messy real draw states, not one clean
  snapshot.** (2026-07-13, /bracket export) Two blocking false-positives shipped because the
  bracket invariants were only exercised against a fully-resolved live Wimbledon: (1) the
  champion cross-check compared on casefold, but `champion` is the results `winner_name` while
  the bracket slot is the elo-canonical spelling — a diacritic (Nosková vs Noskova) is the SAME
  player; compare on `_name_key` (accent/punct-insensitive), the exact key `bracket_rounds`
  used to assign the winner. (2) the drawSize check counted only non-placeholder players, but
  tournaments.json `drawSize` = `len(field_pool)` counts every non-null slot INCLUDING
  unresolved `Qualifier N` placeholders — an early-captured draw frozen by the first-capture
  wiki cache (Gstaad: 2 named + 26 qualifiers = 28) then reads "2 round-0 players but drawSize
  28" and blocks the whole deploy. **Why:** synthetic tests and a single in-flight event never
  exercise the frozen/placeholder/bye/accent/sponsor-name states real draws pass through; the
  same Gstaad 28-draw that broke the power-of-two check on 2026-07-10 broke this one too.
  **How to apply:** before landing a blocking invariant that compares counts or names, (a)
  compute BOTH sides with the identical predicate/key as their source, and (b) enumerate the
  draw states across the calendar — early-frozen placeholder draws, byes, qualifiers, accented
  names, sponsor vs archive event names — and confirm each is legal. Extends the "validate a
  gate invariant against the full tour CALENDAR" lesson in
  [`gates-and-health.md`](gates-and-health.md).

- **A completed-event projection must filter the ratings frame to main-draw ROUNDS before
  constructing its field.** (2026-07-11, Wimbledon final deployment failure) The live path
  used Wikipedia's 128-slot bracket and worked all fortnight; the instant the final appeared,
  the completed path unioned every player in the event group, including ratings-only qualifying
  rows. More than 128 names padded to an impossible 256-slot bracket and crashed before the
  pre-deploy gate. The first fix filtered `draw_level == "main"`, but production still failed:
  legacy/source Q1/Q2 rows can be default-labelled `main`. Rule: event completion may change the
  projection mode, never the population; filter both provenance AND recognized knockout rounds
  (`R128`..`F`), and when the authoritative Wikipedia draw exists, retain its population after
  completion instead of reverting to the noisier results union. Gate any shipped `drawSize > 128`.

- **Live-event surface has ONE authoritative source (Wikipedia's main article) and must be
  fixed at the loader source, not the prediction points.** (2026-07-08, surface backfill) ESPN
  carries no surface, so it's re-derived as archive-by-name -> `_MONTH_SURFACE` (July="Grass").
  New/sponsor-renamed clay events miss the archive ("Nordea Open" is archived as city "Bastad" —
  zero shared substring; "Grand Est Open 88" is brand-new) and were mislabeled Grass. Three
  non-obvious traps fixing it: (1) **The `surface` infobox lives ONLY on the main tournament
  article ("2026 Swedish Open"), never the "– Singles" draw sub-article `draws_wiki.fetch_draw`
  reads** — surface capture is a SEPARATE resolution (own `event_surface` + `wiki_surface.json`
  cache), and it works by sponsor name even when the gendered singles draw doesn't resolve. (2)
  **Don't gate `event_surface` on the infobox NAME** (`"infobox tennis"`): Grand Slam articles use
  a differently-named infobox, so that gate returns None for Wimbledon even though `surface=[[Grass
  court…` parses fine — a parseable `surface=[[…court]]` field IS the tennis-tournament signal;
  bound wrong-event risk with year-in-title + a distinctive body anchor instead. (3) **Correct
  `surface_b` at the SOURCE in `results.clean` (wiki tier between the archive backfill and the
  month fallback), not only in the prediction helpers** — `project_tournament` reads `surface_b`
  directly, and once an event goes live the ESPN rows carry month-guessed Grass with no provenance,
  which `event_attrs`/`_archive_attrs` return as if authoritative, so a prediction-only fix silently
  regresses to Grass mid-tournament. `resolve_surface` (archive -> wiki cache -> month) lives in a
  leaf `data/surface.py` importing only config, so the offline loader stays network-free. Builds on
  the [[future-proof-no-quick-fixes]] no-hardcoded-table rule.

- **ESPN can't give a full draw at release — Wikipedia can; three traps when adding it.**
  (2026-07-08, `data/draws_wiki.py`) ESPN's scoreboard AND core API fill a pre-created
  bracket with real names only via the daily order-of-play (R1 slots are `"Bye"`/athlete
  `id:0` until then), so no ESPN endpoint carries a complete draw at release — draw
  acquisition needs a separate source. Wikipedia's MediaWiki API posts the complete ORDERED
  draw the day it's released (verified down to ATP-250). Traps: (1) **Parse `-Compact-`
  section templates in document order** — the full draw is split across `{N}TeamBracket-
  Compact-Tennis{3|5}[-Byes]` section templates (8×16 for a slam) plus small non-compact
  summary brackets you MUST ignore; concatenating the compact sections' first round in doc
  order rebuilds the real bracket (which pins every downstream half — the thing ESPN's
  `match_num`-less feed can't). (2) **Byes are sparse in RD1** — a seed with a bye has NO
  `RD1-team` leaf; it rides in `RD2-team{k}` (both leaves of match k absent → seat that RD2
  seed against a None). (3) **Title resolution MUST gate on year + a distinctive anchor
  token + exact tour/gender** — a naive "`<year> <event> singles`" search silently resolves
  to LAST year's draw (not posted yet → falls through) or the WRONG tour's draw of a combined
  event (e.g. Winston-Salem→Australian Open, ATP Eastbourne→Women's singles). Consume it
  order-preserving: `sim/draws.advance_slots` collapses the wiki bracket by ESPN eliminations
  keeping adjacency — do NOT round-trip through `live_draw` (it strength-seeds units and
  re-loses the downstream halves). Builds on [[future-proof-no-quick-fixes]] and the live-draw
  lesson below.

- **Live tournament reach-odds must be seated on the ACTUAL draw, not a rating
  re-seed.** (2026-07-08) The live scorecard showed Sinner 97% + Djokovic 55% to
  reach the same final while they actually met in the SF (must sum to 100%). Cause:
  `project_field` → `standard_seed_draw` re-seeded survivors into a synthetic
  1v4/2v3 bracket. Field-strength dominates *champion* odds on a full draw, so this
  looked harmless — but it makes the round-by-round SF/F reach table nonsense, most
  visibly once the draw is small and the real pairings are known. The real matchups
  were already on disk: `data/live.parse_upcoming` writes them to `upcoming.csv`
  (and `eval/track` reads it), the projector just never opened the file. Fix:
  `sim/draws.live_draw` seats survivors by their real current-round matchups (pairs
  adjacent; already-advanced players get a bye into the next round), seeding only
  the genuinely-unknown downstream pairings; completed events keep full-field
  seeding (that path is a deliberate pre-tournament hypothetical). Rule: any
  live/forecast surface that shows per-round structure must consume the real draw
  from `upcoming.csv`; a "sums to >100% across two players who face each other" is
  the canary. See [[plans-adapt-to-landed-code]].

- **A live feed's round label is draw-relative — resolve it against draw size, not
  the label/number alone.** (2026-07-08) ESPN's tennis scoreboard tags main-draw
  rounds "Round 1".."Round 4" with numeric `round.id` 1-4 (start-anchored,
  left-aligned) and always QF/SF/F = ids 5/6/7. So "Round 1" is R128 at a 128-draw
  Slam but R32 at a 32-draw event — the number alone is meaningless. The old
  name-only `_round_label` matched none of "Round N" and fell through to a generic
  `return "R64"`, so every Slam R128/R32/R16 match shipped as R64 (Wimbledon
  fixtures showed 120 matches as "R64"). Fix: `_draw_size` per event grouping =
  `next_pow2(2 x opening-round match count)` (the opening round ships complete when
  the draw drops, and pow2-rounding absorbs byes), then map numbered id `r` to
  `draw >> (r-1)`; QF/SF/F stay name-anchored; `_round_label` kept only as an
  id-less fallback. Rules: (1) map live rounds against draw size, computed per
  event, never from the bare round label; (2) anchor the named rounds (QF/SF/F) by
  their fixed marker, not by counting — the numbered-round<->QF id gap is not
  constant across draw sizes; (3) any keyword round map needs its fallback proven
  against the SOURCE's real vocabulary (ESPN sends "Round 4", not the
  documented-looking "Round of 16"/"4th Round").

- **"It never changes once released" is a claim about the artifact's FINAL state; a cache
  keyed on it must also check the state it was captured IN.** (2026-07-27, Palermo/Generali
  Open) `download_wiki_draws` skipped any event whose cached entry had slots — "a draw doesn't
  change once released". True of a resolved draw, false of one captured before qualifying
  finishes: those slots read `Qualifier 6`, Wikipedia replaces them later, and the cache never
  looked again. `project_tournament` treats the cached draw as the authoritative main-draw
  population (deliberately — discarding it at completion once recreated a 133-player
  Wimbledon), so the frozen placeholders became a field no results row could ever match:
  `alive = field_pool - eliminated` subtracted nothing and Palermo shipped **32 of 32 alive on
  a finished event**, with `modelFavorite 'Qualifier 6'`. The article was fine the whole time —
  a local capture of the same two articles taken days later had 0 placeholders and correct
  accents. **Why:** the idempotence claim was about Wikipedia's content, but the cache key was
  "do we have bytes", and those are only the same question once the content has settled.
  **How to apply:** when skipping work because "this input is immutable", gate the skip on a
  predicate that says the input REACHED its final state (`_draw_is_settled`), not merely that
  it exists; borrow the predicate from whatever already judges that (`sim.bracket.is_real`,
  which `health.py` uses for the same purpose) so ingestion and gate cannot drift; and keep the
  stale copy when the re-fetch fails, so a refresh attempt can't lose data you already had.

- **Three separate bugs kept every HARD-COURT event surface-less, and a guessed value with
  no provenance recycled itself as fact.** (2026-07-27, DC Open priced on grass Elo) The
  2026-07-08 fix made Wikipedia's main-article infobox the authoritative live surface. It
  worked for clay and grass and silently failed for hard courts, for two independent parsing
  reasons: (1) `_SURFACE_FIELD_RE` captured `[^\n|]*`, stopping at the wikilink pipe, so only
  the link TARGET was ever read — fine for `[[Clay court|Clay]]`, useless for Memphis's
  `[[Tennis court#outdoor courts|Hard]]` where the surface is in the DISPLAY text; (2) even
  reading the target, `\b(Hard|Clay|Grass)\b` cannot match inside the ONE-word `[[Hardcourt|
  Hard (outdoor)]]`. So the cache had every clay/grass event and no hard-court event, and
  `MONTH_SURFACE[July]="Grass"` answered instead — for a hard-court swing. The third bug made
  it permanent: `clean()` stamped the month guess into `surface_b` with no provenance, and
  `_archive_attrs`/`event_attrs` read that column back as "the archive value", which
  short-circuits the Wikipedia tier in `resolve_surface`. A guess proving itself.
  **Why:** the unit tests only ever exercised `[[Clay court|Clay]]`-shaped input, so two of
  the three real-world spellings were never seen; and the failure is silent by construction —
  `_download_wiki_surfaces` deliberately never caches a miss, so a parse bug looks exactly
  like "not published yet" forever. **How to apply:** when parsing a wikilink, never assume
  which side of the pipe holds the value — read the whole field to end of line (as
  `_parse_category` already did) and search it; verify a parser against the REAL articles for
  each value it must return, not one representative sample (three fetches would have caught
  all of this); and when a resolution chain has a guessing tier, stamp WHICH tier answered,
  because any consumer that feeds the result back in as authoritative turns the guess into a
  fixed point. Also note the two chains had drifted apart — the pre-start path matched the
  cache by containment, the live path exactly — so one event could legitimately change
  surface the day it started (Memphis: Hard while upcoming, Grass on day one). Two code paths
  answering the same question must share one function.

- **Display names are for display; joins use the event ID; the name history IS the alias
  table.** (2026-07-28, the whole Track B) Nineteen seams in this codebase joined two sources
  on an event-NAME string, and that was the single largest bug family in its history: the
  duplicate Bad Homburg card with the finalists swapped, tier regressions to "Tour", clay
  events shipped as Grass because the archive says "Bastad" where ESPN says "Nordea Open"
  (zero shared substring), and the DC Open losing its bracket outright when ESPN dropped
  "Citi" from its title mid-tournament. The fix was in the data the whole time — ESPN gives
  every event a stable id, `parse_event_meta` had always extracted it, and it was used once
  to dedup a fetch and then thrown away. **Four things that were not obvious while building
  it:** (1) a rename that INSERTS a word mid-title ("Mubadala Citi DC Open" ->
  "Mubadala DC Open") defeats every containment rule, so name resolution must REFUSE rather
  than guess — what recovers the orphaned cache entry is the espnId stamped inside it, which
  makes `EventResolver(extra=...)` load-bearing rather than a convenience. (2) The id is a
  HINT, never a key: the archive predates it, the merge prefers stat-bearing archive rows, so
  the row that SURVIVES a dedup usually has no id — take the modal non-null value per event.
  (3) Worse, the id was being lost in the very step that proved two records were the same
  event; dedup keys ignore `tourney_name` (that is how a match reported twice collapses at
  all) and drop the ESPN row, so the identity must be propagated across a match's rows BEFORE
  the dedup picks a survivor. (4) Merging must happen BEFORE projection, not by deduping
  cards afterwards — dedup only hid the fragment, one of the two projections was still built
  on half an event. **How to apply:** when two sources describe the same thing, find the
  stable id one of them already emits and plumb it end to end; where no id exists, join on
  EVIDENCE (date overlap plus shared real participants), never on string similarity; and make
  the producer collapse exactly what the gate would flag as a split.

- **Put the model between two deterministic layers, and let the cheap one run first.**
  (2026-07-28, `data/alias_proposer.py`) The three hand-kept identity tables in `config.py`
  were all populated reactively — an entry got added days after the mismatch had already
  shipped to the board. The instinct was "ask an LLM with search to spot these", and the
  design that actually works puts the model in the middle rather than at the front:
  a deterministic scan GENERATES the candidates, the model ADJUDICATES only those, a
  deterministic falsifier DISCARDS what the data refutes, and a human merges the PR.
  Containment is the load-bearing rule — `falsify` rejects any proposal whose subject was
  not one of the questions asked — because it means a hallucinated pair cannot enter the
  system even if the model is completely confident. The domain rule that outranks any search
  result: **two names that have ever met each other across a net are two people.**
  **The part that was genuinely surprising:** the deterministic half found a live production
  bug on its first run, before a single token was spent. Diego Dedura had 36 matches under
  one spelling and 3 under "Diego Dedura-Palomero", and Stuttgart 2026-06-09 carried BOTH
  ("James Duckworth d. Diego Dedura" and "James Duckworth d. Diego Dedura-Palomero" are one
  match written twice) — two Elo histories for one player, plus a phantom duplicate row. A
  token-subset scan over the last 180 days surfaces that in milliseconds; the LLM was never
  needed for it, and would have been asked only about the genuinely ambiguous leftovers.
  **How to apply:** before reaching for a model, write the scan that enumerates the
  candidates — it is usually most of the value, it is free, it is testable, and whatever it
  cannot decide is a much smaller and better-posed question to spend an API call on. Then
  make the model's answer falsifiable against data you already hold, and keep the adopt step
  human. Never let a bot merge into a branch whose push IS the production deploy.

- **Date overlap plus shared players does not identify one event; require a shared real
  match when no stable event ID exists.** (2026-07-29, Wimbledon fused into Nordea Open)
  Two concurrent WTA events overlapped by five days and shared nine players but shared zero
  main-draw match pairs. The projector treated that as a sponsor rename, merged both result
  groups, and manufactured a 152-player Wimbledon field. This differed from the independent
  coverage resolver, which already required match evidence. Event IDs remain the decisive
  path when both sides carry one; for id-less records, date overlap only bounds the search
  and shared participants only raise suspicion. A shared knockout pair is the minimum
  positive evidence that two differently named groups describe the same event. Build that
  evidence from the same main-draw rows used to construct the field, and regression-test both
  directions: the false concurrent-event merge stays split while a genuine renamed event
  with a shared match still coalesces.

- **Metadata aliases and draw locators are different namespaces.** (2026-07-29, Mifel draw
  reported unavailable after play began) `WIKI_TITLE_OVERRIDES` correctly mapped Mifel's
  sponsor title to the `Los Cabos Open` main article for surface and tier metadata. Reusing
  that alias as the draw locator nevertheless failed, because the ordered bracket lived at
  `2026 Los Cabos Open – Singles`; the main article was never evidence that a draw did not
  exist. The official ATP artifact had another identity again: tournament id `7480` and
  `posting/2026/7480/mds.pdf`. **How to apply:** keep event identity (`espnId`), metadata
  aliases, and provider artifact IDs in separate fields and resolution paths. A mapping that
  answers one resource type must not silently become the locator for another. Provider IDs
  locate evidence; they never replace the canonical event key.

- **Date overlap plus a token or a few shared players may rank source candidates, but only
  near-complete field evidence may attach an official draw to an event.** (2026-07-29,
  adjacent ATP events cross-attached during rate limiting) The first official-source pass
  accepted two real shared players, which let Kitzbuhel's PDF attach to DC and Umag's PDF
  attach to Estoril when the preferred lookup failed. Every individual fact was plausible:
  the calendars overlapped, names were real, and tour/year matched. The event identity was
  still false. The repaired contract requires the unique strongest candidate to reconcile at
  least 75% of the live event field, with provider dates overlapping the ESPN calendar; name
  tokens only order the bounded attempts. PDF geometry, entrant/byes consistency, source URL,
  and tour/date provenance are gated independently. **How to apply:** sparse overlap is good
  enough to generate candidates, never to attach a complete external artifact. Require
  evidence proportional to what the artifact claims to cover, and regression-test adjacent
  same-tour events that share players.

- **An unresolved provider label identifies a slot type, not a reusable entrant identity.**
  (2026-07-31, Toronto deploy gate) The ATP PDF correctly described a 96-entrant draw, but
  printed the same bare `Qualifier` label in every one of its 16 open qualifying seats. The
  parser preserved those duplicate strings; the projector then built its authoritative field
  with a set, collapsing 16 distinct seats into one and exporting an impossible 81-player
  population beside a 96-entrant bracket. The pre-deploy gate caught the population/geometry
  contradiction and kept the last good site live. **How to apply:** normalize unresolved
  source labels to unique seat identities (`Qualifier 1..N`) at ingestion, before any set,
  map, simulation, or cache consumer sees them. Keep true byes as null, and regression-test
  entrant cardinality against bracket geometry using the provider's messy pre-qualifying state.
