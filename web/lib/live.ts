import type { Tour } from "@/lib/tour";
import { blendedElo } from "@/lib/ui";

/* Client-side ESPN live scores — mirrors the parsing rules of
   tennis_model/src/tennis_model/data/live.py (same endpoint, same
   grouping-slug filter, same qualifying skip), but keeps IN-PROGRESS
   matches instead of completed ones. */

const SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/tennis";

/** TS port of tennis_model results.py:_name_key — the canonical join key
    between ESPN display names and the model's player names. */
export function nameKey(name: string): string {
  return name
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[-.'`]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export type RawLiveMatch = {
  id: string;
  event: string; // ESPN event name (may carry a sponsor title)
  round: string; // e.g. "3rd Round"
  detail: string; // e.g. "Set 2"
  a: string;
  b: string;
  sets: [number, number][]; // per-set games, [a, b], current set last
};

export type TournamentInfo = {
  name: string;
  surface: string;
  bestOf: number;
  level: string;
  status: string;
};

export type PlayerRow = {
  name: string;
  elo: number;
  eloHard?: number;
  eloClay?: number;
  eloGrass?: number;
};

export type Matrix = {
  players: string[];
  formats: number[];
  surfaces: Record<string, Record<string, number[][]>>;
};

/** In-progress singles matches for a tour. Throws on network/HTTP failure —
    the caller hides the ticker. */
export async function fetchLiveMatches(tour: Tour, signal?: AbortSignal): Promise<RawLiveMatch[]> {
  const res = await fetch(`${SCOREBOARD}/${tour}/scoreboard?limit=300`, { signal });
  if (!res.ok) throw new Error(`espn ${res.status}`);
  const data = await res.json();
  const slug = tour === "atp" ? "mens-singles" : "womens-singles";
  const out: RawLiveMatch[] = [];
  const seen = new Set<string>();
  for (const ev of data?.events ?? []) {
    const evName: string = ev?.shortName || ev?.name || "";
    for (const grp of ev?.groupings ?? []) {
      if ((grp?.grouping?.slug ?? "") !== slug) continue;
      for (const comp of grp?.competitions ?? []) {
        const st = comp?.status?.type;
        if (st?.state !== "in") continue;
        const round: string = comp?.round?.displayName || "";
        if (round.toLowerCase().includes("qualif")) continue;
        const cs = comp?.competitors ?? [];
        const an = cs[0]?.athlete?.displayName;
        const bn = cs[1]?.athlete?.displayName;
        if (!an || !bn) continue;
        const id = String(comp?.id ?? `${evName}:${an}:${bn}`);
        if (seen.has(id)) continue;
        seen.add(id);
        const la = cs[0]?.linescores ?? [];
        const lb = cs[1]?.linescores ?? [];
        const sets: [number, number][] = [];
        for (let k = 0; k < Math.max(la.length, lb.length); k++) {
          const ga = Number(la[k]?.value);
          const gb = Number(lb[k]?.value);
          sets.push([isFinite(ga) ? Math.round(ga) : 0, isFinite(gb) ? Math.round(gb) : 0]);
        }
        out.push({ id, event: evName, round, detail: st?.shortDetail || "", a: an, b: bn, sets });
      }
    }
  }
  return out;
}

/** Surface fallback by calendar month (port of results.py:_MONTH_SURFACE). */
function monthSurface(d: Date = new Date()): string {
  const m = d.getMonth() + 1;
  if (m === 4 || m === 5) return "Clay";
  if (m === 6 || m === 7) return "Grass";
  return "Hard";
}

/** Surface + best-of for an ESPN event. ESPN omits both, so join to the live
    tournaments.json entry by de-sponsored substring containment. */
export function matchContext(
  eventName: string,
  tournaments: TournamentInfo[] | null,
): { surface: string; bestOf: number } {
  const ev = eventName.toLowerCase();
  const t = (tournaments || []).find(
    (t) => t.status === "live" && t.name.length >= 5 && ev.includes(t.name.toLowerCase()),
  );
  if (t) return { surface: t.surface, bestOf: t.bestOf || 3 };
  return { surface: monthSurface(), bestOf: 3 };
}

const SURF_KEY: Record<string, "eloHard" | "eloClay" | "eloGrass"> = {
  Hard: "eloHard",
  Clay: "eloClay",
  Grass: "eloGrass",
};

/** matrix.players.map(nameKey) is O(players) string work — cache it per matrix
    object (winProb runs per card per render). */
const matrixKeys = new WeakMap<Matrix, string[]>();
function keysFor(matrix: Matrix): string[] {
  let keys = matrixKeys.get(matrix);
  if (!keys) {
    keys = matrix.players.map(nameKey);
    matrixKeys.set(matrix, keys);
  }
  return keys;
}

/** Model P(A beats B): the precomputed combiner matrix when both players are
    in the top-120 grid, else the model's surface-blended Elo via the canonical
    per-tour blend (ui.ts SURFACE_BLEND, RATING_SCALE=400), else null. */
export function winProb(
  a: string,
  b: string,
  surface: string,
  bestOf: number,
  players: PlayerRow[] | null,
  matrix: Matrix | null,
  tour: Tour,
): { p: number | null; source: "matrix" | "elo" | null } {
  const ka = nameKey(a);
  const kb = nameKey(b);

  if (matrix) {
    const keys = keysFor(matrix);
    const i = keys.indexOf(ka);
    const j = keys.indexOf(kb);
    if (i >= 0 && j >= 0 && i !== j) {
      const surf = matrix.surfaces[surface] || matrix.surfaces.Hard;
      const grid = surf?.[String(bestOf)] || surf?.["3"];
      const p = grid?.[i]?.[j];
      if (typeof p === "number") return { p, source: "matrix" };
    }
  }

  if (players) {
    const key = SURF_KEY[surface] || "eloHard";
    let pa: PlayerRow | undefined;
    let pb: PlayerRow | undefined;
    for (const pl of players) {
      const k = nameKey(pl.name);
      if (k === ka) pa = pl;
      else if (k === kb) pb = pl;
      if (pa && pb) break;
    }
    if (pa && pb) {
      const ra = blendedElo(pa.elo, pa[key] ?? pa.elo, tour);
      const rb = blendedElo(pb.elo, pb[key] ?? pb.elo, tour);
      return { p: 1 / (1 + Math.pow(10, -(ra - rb) / 400)), source: "elo" };
    }
  }

  return { p: null, source: null };
}
