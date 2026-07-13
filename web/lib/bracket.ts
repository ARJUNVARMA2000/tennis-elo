/** Pure helpers for the /bracket explorer (node-testable, no React/DOM).

    A full slam draw is 7 rounds × up to 64 first-round matches — far too tall to render
    as one grid. We slice the early rounds into 16-slot SECTIONS (a printed draw's
    quarters/eighths) selected by chips, and render the rounds where the sections converge
    (QF onward) as a separate "final rounds" mini-tree. Each column then holds at most 8
    match cards, and equal-height flex columns give the classic bracket connectors with no
    per-match grid math. */

export type ProbSource = "logged" | "model" | null;

export type BracketMatch = {
  a: string | null;
  b: string | null;
  seedA: number | null;
  seedB: number | null;
  p: number | null;
  probSource: ProbSource;
  winner: "a" | "b" | null;
  score: string | null;
  upset: boolean | null;
};

export type BracketRound = { round: string; matches: BracketMatch[] };

export type BracketEvent = {
  name: string;
  surface: string;
  level: string;
  bestOf: number;
  start: string;
  end: string;
  status: "live" | "upcoming" | "completed";
  drawSize: number;
  bracketSize: number;
  champion: string | null;
  runnerUp: string | null;
  wikiUrl: string | null;
  rounds: BracketRound[];
};

/** Minimal shape of tournaments.json needed for the reach-odds join (no duplication of
    the projection into brackets.json — the two are matched client-side by event name). */
export type TournamentLite = {
  name: string;
  projection?: { name: string; reach?: Record<string, number> }[];
};

export const SECTION_SLOTS = 16;

const norm = (s: string) => s.trim().toLowerCase();

export function isPlaceholder(name: string | null): boolean {
  return !!name && /^(qualifier|lucky loser)\b/i.test(name.trim());
}

export function isRealSlot(name: string | null): name is string {
  return !!name && name.trim() !== "" && !isPlaceholder(name);
}

/** What to render in a slot: a real name, "Qualifier" for a placeholder, or "Bye"
    (round 0) / "TBD" (a later round whose feeder isn't decided). */
export function sideLabel(name: string | null, roundIndex: number): string {
  if (isRealSlot(name)) return name;
  if (isPlaceholder(name)) return "Qualifier";
  return roundIndex === 0 ? "Bye" : "TBD";
}

/** Number of 16-slot sections in the draw (1 for a draw of ≤16 — rendered whole). */
export function sectionCount(bracketSize: number): number {
  return Math.max(1, Math.floor(bracketSize / SECTION_SLOTS));
}

/** How many leading rounds live inside a section before the sections converge into the
    shared final rounds. A single-section draw (≤16) shows all of its rounds. */
export function sectionRoundCount(bracketSize: number, nRounds: number): number {
  return sectionCount(bracketSize) > 1 ? Math.min(nRounds, 4) : nRounds;
}

/** The [start, start+count) match slice a section occupies at a given round depth. Round 0
    is 8 matches/section, halving each round (8,4,2,1). */
export function sectionMatchRange(section: number, roundIndex: number): { start: number; count: number } {
  const count = Math.max(1, (SECTION_SLOTS / 2) >> roundIndex);
  return { start: section * count, count };
}

export type BracketColumn = {
  round: string;
  roundIndex: number;
  matches: { m: BracketMatch; idx: number }[];
  finals: boolean;
};

/** Columns for one section: the section's slice of each leading round. */
export function sectionColumns(ev: BracketEvent, section: number): BracketColumn[] {
  const secRounds = sectionRoundCount(ev.bracketSize, ev.rounds.length);
  const cols: BracketColumn[] = [];
  for (let r = 0; r < secRounds && r < ev.rounds.length; r++) {
    const { start, count } = sectionMatchRange(section, r);
    const matches = ev.rounds[r].matches
      .slice(start, start + count)
      .map((m, i) => ({ m, idx: start + i }));
    cols.push({ round: ev.rounds[r].round, roundIndex: r, matches, finals: false });
  }
  return cols;
}

/** The shared closing rounds (QF/SF/F for a slam) — empty when the whole draw already
    fits in one section. */
export function finalsColumns(ev: BracketEvent): BracketColumn[] {
  if (sectionCount(ev.bracketSize) <= 1) return [];
  const secRounds = sectionRoundCount(ev.bracketSize, ev.rounds.length);
  const cols: BracketColumn[] = [];
  for (let r = secRounds; r < ev.rounds.length; r++) {
    cols.push({
      round: ev.rounds[r].round,
      roundIndex: r,
      matches: ev.rounds[r].matches.map((m, i) => ({ m, idx: i })),
      finals: true,
    });
  }
  return cols;
}

/** Section labels for the chip row ("Section 1"…). */
export function sectionLabels(bracketSize: number): string[] {
  return Array.from({ length: sectionCount(bracketSize) }, (_, i) => `Section ${i + 1}`);
}

/** Resolve the ?e= event param to an index; unknown/absent falls back to the first event
    (build order is live → upcoming → completed, so index 0 is the most relevant). */
export function resolveEventIndex(events: BracketEvent[], eParam: string | null): number {
  if (!eParam) return 0;
  const i = events.findIndex((e) => norm(e.name) === norm(eParam));
  return i >= 0 ? i : 0;
}

export type ReachMap = Record<string, Record<string, number>>;

/** Per-player reach odds for an event, joined from tournaments.json by name. */
export function reachFor(tournaments: TournamentLite[] | null, eventName: string): ReachMap {
  const t = tournaments?.find((x) => norm(x.name) === norm(eventName));
  const out: ReachMap = {};
  for (const p of t?.projection ?? []) if (p.reach) out[p.name] = p.reach;
  return out;
}

/** The leading title contenders (champion odds, desc) for the event header strip. */
export function titleContenders(
  tournaments: TournamentLite[] | null,
  eventName: string,
  n = 3,
): { name: string; p: number }[] {
  const t = tournaments?.find((x) => norm(x.name) === norm(eventName));
  return [...(t?.projection ?? [])]
    .map((p) => ({ name: p.name, p: p.reach?.Champion ?? 0 }))
    .filter((x) => x.p > 0)
    .sort((a, b) => b.p - a.p)
    .slice(0, n);
}
