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
};

export type EventGroup = { event: string; surface: string; matches: Upcoming[] };

/** Group scheduled matches by tournament, preserving input order — the pipeline already
    sorts rows soonest-first, so both the event order and the matches within each event
    come out in playing order. */
export function groupByEvent(rows: Upcoming[]): EventGroup[] {
  const groups: EventGroup[] = [];
  const byEvent = new Map<string, EventGroup>();
  for (const r of rows) {
    let g = byEvent.get(r.event);
    if (!g) {
      g = { event: r.event, surface: r.surface, matches: [] };
      byEvent.set(r.event, g);
      groups.push(g);
    }
    g.matches.push(r);
  }
  return groups;
}
