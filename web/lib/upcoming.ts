import { orientEvidence, type PredictionEvidenceData } from "./evidence";

/** One scheduled match with the model's current win probability, as written by the
    pipeline's build_upcoming (mirrored to /data/<tour>/upcoming.json). pA = P(playerA wins). */
export type ForecastPoint = {
  asOf?: string;
  p: number;
  modelVersion?: string | null;
  firstSighting?: boolean;
  components?: {
    eloBlend?: number;
    pointModel?: number;
    combiner?: number;
  };
  evidence?: PredictionEvidenceData;
};

export type ForecastHistory = {
  first: number;
  current: number;
  delta: number;
  firstAsOf?: string;
  latestAsOf?: string;
  snapshots: number;
  timeline?: ForecastPoint[];
};

export type Upcoming = {
  event: string;
  espnId?: string | null;
  date: string;
  round: string;
  surface: string;
  bestOf: number;
  playerA: string;
  playerB: string;
  pA: number;
  level?: string;
  components?: {
    eloBlend: number;
    pointModel: number;
    combiner: number;
  } | null;
  evidence?: PredictionEvidenceData | null;
  forecast?: ForecastHistory | null;
  watch?: {
    schema: "watch-v1";
    score: number;
    weights: Record<string, number>;
    factors: Record<
      "closeness" | "quality" | "styleContrast" | "stakes" | "titleLeverage",
      { score: number; available: boolean; detail?: unknown }
    >;
    coverage: number;
  };
  watchRank?: number;
};

/** Orient a stored history to the player shown first without mutating source data. */
export function orientForecast(forecast: ForecastHistory, flip: boolean): ForecastHistory {
  if (!flip) return forecast;
  const invert = (value: number) => Math.round((1 - value) * 1_000_000) / 1_000_000;
  return {
    ...forecast,
    first: invert(forecast.first),
    current: invert(forecast.current),
    delta: -forecast.delta,
    timeline: forecast.timeline?.map((point) => ({
      ...point,
      p: invert(point.p),
      components: point.components && Object.fromEntries(
        Object.entries(point.components).map(([key, value]) => [key, value == null ? value : invert(value)]),
      ),
      evidence: point.evidence ? orientEvidence(point.evidence, true) : undefined,
    })),
  };
}

import { tournamentTier } from "./ui";

export type EventGroup = { event: string; surface: string; level?: string; matches: Upcoming[] };

const TOURNAMENT_CARD_MATCH_LIMIT = 3;

/** Scheduled matches belonging to one live tournament card. Identity is deliberately exact:
    sponsor titles and familiar city labels can differ even within one refresh, so display names
    are never a join key. Rows without the stable provider identity stay on /schedule rather than
    risking attachment to the wrong card. The producer already orders rows soonest-first. */
export function matchesForTournament(
  tournament: { name: string; status: string; espnId?: string | null },
  rows: Upcoming[],
  limit = TOURNAMENT_CARD_MATCH_LIMIT,
): Upcoming[] {
  const eventId = String(tournament.espnId ?? "").trim();
  if (tournament.status !== "live" || !eventId) return [];
  return rows
    .filter((row) => String(row.espnId ?? "").trim() === eventId)
    .slice(0, Math.max(0, limit));
}

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

/** Whether BOTH players of a scheduled match are in the rated roster (players.json —
    built from the same top-N list as profiles.json, so membership here guarantees the
    /style page can resolve them). Gates the card's style-matchup drill-in: a link for a
    qualifier without a profile would silently fall back to /style's default pair. */
export function hasMatchupProfiles(m: Upcoming, roster: ReadonlySet<string>): boolean {
  return roster.has(m.playerA) && roster.has(m.playerB);
}

/** The scheduled matchup closest to 50/50, preserving producer order on ties. */
export function closestUpcomingMatch(rows: Upcoming[]): Upcoming | undefined {
  return rows.reduce<Upcoming | undefined>((best, row) => {
    if (!best) return row;
    return Math.abs(row.pA - 0.5) < Math.abs(best.pA - 0.5) ? row : best;
  }, undefined);
}

/** Product-ranked view without mutating the chronology-preserving schedule payload. */
export function worthWatching(rows: Upcoming[], limit = 5): Upcoming[] {
  return rows
    .filter((row) => row.watch && typeof row.watchRank === "number")
    .sort((a, b) => (a.watchRank ?? Infinity) - (b.watchRank ?? Infinity))
    .slice(0, Math.max(0, limit));
}

/** UI-only filtering within one upcoming payload; this is not an event join. */
export function filterUpcoming(rows: Upcoming[], surface: string, event: string): Upcoming[] {
  return rows.filter((match) =>
    (surface === "All" || match.surface === surface) && (event === "all" || match.event === event)
  );
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
