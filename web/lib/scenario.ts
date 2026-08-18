import type { BracketRound } from "@/lib/bracket";
import { isRealSlot } from "@/lib/bracket";

export type ScenarioCandidate = { name: string; p: number };
export type ScenarioNode = {
  key: string;
  roundIndex: number;
  round: string;
  matchIndex: number;
  status: "confirmed" | "forced" | "projected";
  winner: string | null;
  candidates: ScenarioCandidate[];
};
export type ScenarioResult = {
  nodes: { round: string; matches: ScenarioNode[] }[];
  reach: Record<string, Record<string, number>>;
  champion: ScenarioCandidate[];
};

export type ScenarioArtifact = {
  schemaVersion: 1;
  generation: string;
  event: {
    name: string;
    espnId: string | null;
    surface: string;
    bestOf: number;
    status: string;
    bracketSize: number;
  };
  players: string[];
  matrices: Record<"eloBlend" | "pointModel" | "combiner", number[][]>;
  rounds: BracketRound[];
  base: ScenarioResult;
};

type Distribution = Record<string, number>;

function confirmedWinner(match: BracketRound["matches"][number]): string | null {
  return match.winner === "a" ? match.a : match.winner === "b" ? match.b : null;
}

function combine(
  left: Distribution,
  right: Distribution,
  players: string[],
  matrix: number[][],
  fixed?: string | null,
): Distribution {
  if (fixed) return { [fixed]: 1 };
  if (!Object.keys(left).length) return { ...right };
  if (!Object.keys(right).length) return { ...left };
  const index = new Map(players.map((name, i) => [name, i]));
  const out: Distribution = {};
  for (const [a, pLeft] of Object.entries(left)) {
    for (const [b, pRight] of Object.entries(right)) {
      const joint = pLeft * pRight;
      if (a === b) {
        out[a] = (out[a] ?? 0) + joint;
        continue;
      }
      const ia = index.get(a);
      const ib = index.get(b);
      const p = ia == null || ib == null ? 0.5 : (matrix[ia]?.[ib] ?? 0.5);
      out[a] = (out[a] ?? 0) + joint * p;
      out[b] = (out[b] ?? 0) + joint * (1 - p);
    }
  }
  const total = Object.values(out).reduce((sum, value) => sum + value, 0);
  if (total > 0) for (const name of Object.keys(out)) out[name] /= total;
  return out;
}

export function exactScenario(
  rounds: BracketRound[],
  players: string[],
  matrix: number[][],
  forced: Record<string, string> = {},
  eventId?: string | null,
): ScenarioResult {
  if (!rounds.length) return { nodes: [], reach: {}, champion: [] };
  let current: Distribution[] = rounds[0].matches.flatMap((match) => [
    isRealSlot(match.a) ? { [match.a]: 1 } : {},
    isRealSlot(match.b) ? { [match.b]: 1 } : {},
  ]);
  const reach: ScenarioResult["reach"] = Object.fromEntries(
    players.map((name) => [name, { Entry: 1 }]),
  );
  const nodes: ScenarioResult["nodes"] = [];

  rounds.forEach((round, roundIndex) => {
    const next: Distribution[] = [];
    const matches = round.matches.map((match, matchIndex): ScenarioNode => {
      const legacyKey = `${roundIndex}:${matchIndex}`;
      const key = eventId ? `${eventId}:r${roundIndex}:m${matchIndex}` : legacyKey;
      const confirmed = confirmedWinner(match);
      // Only a factual, currently named unresolved matchup is editable. A projected
      // downstream pairing may become certain after another pick, but it is not yet a
      // real scheduled match and cannot be locked honestly.
      const lockable = !confirmed && isRealSlot(match.a) && isRealSlot(match.b);
      const requested = forced[key] ?? forced[legacyKey] ?? null;
      const selected = confirmed ?? (lockable && (requested === match.a || requested === match.b)
        ? requested : null);
      const dist = combine(
        current[2 * matchIndex] ?? {},
        current[2 * matchIndex + 1] ?? {},
        players,
        matrix,
        selected,
      );
      next.push(dist);
      return {
        key,
        roundIndex,
        round: round.round,
        matchIndex,
        status: confirmed ? "confirmed" : selected ? "forced" : "projected",
        winner: selected,
        candidates: Object.entries(dist)
          .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
          .map(([name, p]) => ({ name, p: Math.round(p * 1_000_000) / 1_000_000 })),
      };
    });
    const nextLabel = rounds[roundIndex + 1]?.round ?? "Champion";
    next.forEach((dist) => Object.entries(dist).forEach(([name, p]) => {
      (reach[name] ??= { Entry: 1 })[nextLabel] = Math.round(p * 1_000_000) / 1_000_000;
    }));
    nodes.push({ round: round.round, matches });
    current = next;
  });

  return { nodes, reach, champion: nodes.at(-1)?.matches[0]?.candidates ?? [] };
}

export function encodeScenario(forced: Record<string, string>): string | null {
  // Object insertion order records pick order, which makes "undo latest" deterministic
  // while remaining a compact, fully shareable URL representation.
  const rows = Object.entries(forced);
  return rows.length
    ? rows.map(([key, name]) => `${key}~${encodeURIComponent(name)}`).join(",")
    : null;
}

export function decodeScenario(value: string | null): Record<string, string> {
  const out: Record<string, string> = {};
  for (const token of value?.split(",") ?? []) {
    const split = token.indexOf("~");
    if (split < 1) continue;
    try {
      out[token.slice(0, split)] = decodeURIComponent(token.slice(split + 1));
    } catch { /* malformed share state is ignored */ }
  }
  return out;
}

export function titleSwings(base: ScenarioResult, scenario: ScenarioResult, n = 4) {
  const before = new Map(base.champion.map((row) => [row.name, row.p]));
  const after = new Map(scenario.champion.map((row) => [row.name, row.p]));
  return [...new Set([...before.keys(), ...after.keys()])]
    .map((name) => ({ name, before: before.get(name) ?? 0, after: after.get(name) ?? 0,
      delta: (after.get(name) ?? 0) - (before.get(name) ?? 0) }))
    .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))
    .slice(0, n);
}
