import type { Tour } from "@/lib/tour";
import { NAV_ITEMS } from "@/lib/navigation";
import { pairHref, playerHref, setSearchParam, setSearchTour, withTour } from "@/lib/url";

export type SearchPlayer = { name: string; eloRank?: number | null };
export type SearchBracket = {
  name: string;
  espnId?: string | null;
  status?: string;
  surface?: string;
};
export type CommandResult = {
  key: string;
  kind: "page" | "player" | "tournament" | "prediction";
  label: string;
  desc: string;
  href: string;
};

const normalize = (value: string) =>
  value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();

function matchScore(label: string, query: string): number | null {
  const value = normalize(label);
  if (!query) return 4;
  if (value === query) return 0;
  if (value.startsWith(query)) return 1;
  if (value.split(/\s+/).some((word) => word.startsWith(query))) return 2;
  if (value.includes(query)) return 3;
  return null;
}

function resolvePlayerSide(raw: string, players: SearchPlayer[]): SearchPlayer | null {
  const query = normalize(raw);
  if (!query) return null;
  const ranked = players
    .map((player) => ({ player, score: matchScore(player.name, query) }))
    .filter((entry): entry is { player: SearchPlayer; score: number } => entry.score != null)
    .sort((a, b) => a.score - b.score || (a.player.eloRank ?? 9999) - (b.player.eloRank ?? 9999));
  return ranked[0]?.player ?? null;
}

/** Pure command-palette search across routes and the active tour's exported data. */
export function commandResults(
  rawQuery: string,
  tour: Tour,
  players: SearchPlayer[] = [],
  brackets: SearchBracket[] = [],
  limit = 9,
): CommandResult[] {
  const query = normalize(rawQuery);
  const results: Array<CommandResult & { score: number; rank: number }> = [];

  const versus = rawQuery.trim().split(/\s+vs\.?\s+/i);
  if (versus.length === 2) {
    const a = resolvePlayerSide(versus[0], players);
    const b = resolvePlayerSide(versus[1], players);
    if (a && b && a.name !== b.name) {
      results.push({
        key: `prediction:${a.name}:${b.name}`,
        kind: "prediction",
        label: `${a.name} vs ${b.name}`,
        desc: "Open this matchup in the predictor",
        href: pairHref("/predict/", a.name, b.name, tour),
        score: -1,
        rank: 0,
      });
    }
  }

  for (const [rank, page] of NAV_ITEMS.entries()) {
    const score = matchScore(`${page.label} ${page.desc}`, query);
    if (score == null || (!query && rank > 5)) continue;
    results.push({
      key: `page:${page.href}`,
      kind: "page",
      label: page.label,
      desc: page.desc,
      href: withTour(page.href, tour),
      score,
      rank,
    });
  }

  if (query) {
    for (const [rank, player] of players.entries()) {
      const score = matchScore(player.name, query);
      if (score == null) continue;
      results.push({
        key: `player:${player.name}`,
        kind: "player",
        label: player.name,
        desc: player.eloRank ? `Player profile · Elo #${player.eloRank}` : "Player profile",
        href: playerHref(player.name, tour),
        score,
        rank,
      });
    }

    for (const [rank, bracket] of brackets.entries()) {
      const score = matchScore(bracket.name, query);
      if (score == null) continue;
      const eventKey = bracket.espnId || bracket.name;
      const search = setSearchTour(setSearchParam("", "e", eventKey), tour);
      results.push({
        key: `tournament:${eventKey}`,
        kind: "tournament",
        label: bracket.name,
        desc: [bracket.surface, bracket.status, "bracket"].filter(Boolean).join(" · "),
        href: `/bracket/${search}`,
        score,
        rank,
      });
    }
  }

  const kindRank: Record<CommandResult["kind"], number> = {
    prediction: 0,
    page: 1,
    player: 2,
    tournament: 3,
  };
  return results
    .sort((a, b) => a.score - b.score || kindRank[a.kind] - kindRank[b.kind] || a.rank - b.rank)
    .slice(0, Math.max(0, limit))
    .map(({ score: _score, rank: _rank, ...result }) => result);
}
