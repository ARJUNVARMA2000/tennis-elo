/** One scheduled match with the model's current win probability, as written by the
    pipeline's build_upcoming (mirrored to /data/<tour>/upcoming.json). pA = P(playerA wins). */
export type Upcoming = {
  event: string;
  date: string;
  round: string;
  surface: string;
  bestOf: number;
  playerA: string;
  playerB: string;
  pA: number;
  level?: string;
};

import { tournamentTier } from "./ui";

export type EventGroup = { event: string; surface: string; level?: string; matches: Upcoming[] };

/** Order scheduled matches by tournament prestige (Grand Slam → 1000 → 500 → …), the same tier
    sort the /schedule board and the home tournament cards use. The rows already ship soonest-first
    and Array.sort is stable, so this preserves soonest-first *within* each tier. Used by the home
    "Up next" teaser so the marquee event leads — e.g. during Wimbledon its SF cards surface ahead
    of a concurrent 125's opening round, instead of being buried past the fold by date alone. */
export function byTournamentTier(rows: Upcoming[]): Upcoming[] {
  return [...rows].sort(
    (a, b) => tournamentTier(a.level, a.event).rank - tournamentTier(b.level, b.event).rank,
  );
}

/** One side of a projection card: a player, their model win probability, and whether
    they're the highlighted side (the favourite, for an unplayed match). Structurally
    matches the `CallSide` that `CallCard` consumes. */
export type CardSide = { name: string; prob: number; won: boolean };

/** The `CallCard tone="projection"` props for one scheduled match: favourite on top
    (highlighted), underdog below, with the two probabilities summing to 1. Reused by
    both the standalone /schedule board and the home "Up next" grid so the two surfaces
    can never drift. */
export type UpcomingCard = { surface: string; meta: string; top: CardSide; bottom: CardSide };

/** `showEvent` prepends the tournament name to the meta line ("event · round · date", the
    same convention the Feed and Track "recent calls" cards use). The home "Up next" grid is a
    flat, cross-tournament list, so it needs the event for context; the /schedule board leaves
    it off because each card already sits under its tournament's section header. */
export function upcomingCard(m: Upcoming, opts?: { showEvent?: boolean }): UpcomingCard {
  const aFav = m.pA >= 0.5;
  const meta = opts?.showEvent ? `${m.event} · ${m.round} · ${m.date}` : `${m.round} · ${m.date}`;
  return {
    surface: m.surface,
    meta,
    top: { name: aFav ? m.playerA : m.playerB, prob: aFav ? m.pA : 1 - m.pA, won: true },
    bottom: { name: aFav ? m.playerB : m.playerA, prob: aFav ? 1 - m.pA : m.pA, won: false },
  };
}

/** Group scheduled matches by tournament, preserving input order — the pipeline already
    sorts rows soonest-first, so both the event order and the matches within each event
    come out in playing order. */
export function groupByEvent(rows: Upcoming[]): EventGroup[] {
  const groups: EventGroup[] = [];
  const byEvent = new Map<string, EventGroup>();
  for (const r of rows) {
    let g = byEvent.get(r.event);
    if (!g) {
      g = { event: r.event, surface: r.surface, level: r.level, matches: [] };
      byEvent.set(r.event, g);
      groups.push(g);
    }
    g.matches.push(r);
  }
  return groups;
}
