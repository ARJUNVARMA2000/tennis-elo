import { nameKey } from "@/lib/live";
import type { Tour } from "@/lib/tour";

export const followingStorageKey = (tour: Tour) => `deuce:following:v1:${tour}`;

export function parseFollowing(raw: string | null): string[] {
  try {
    const value: unknown = JSON.parse(raw ?? "[]");
    if (!Array.isArray(value)) return [];
    const seen = new Set<string>();
    return value.filter((name): name is string => {
      if (typeof name !== "string" || !name.trim() || name.length > 150) return false;
      const key = nameKey(name);
      if (!key || seen.has(key)) return false;
      seen.add(key);
      return true;
    }).slice(0, 500);
  } catch { return []; }
}

export function followsPlayer(names: readonly string[], player: string): boolean {
  const key = nameKey(player);
  return !!key && names.some((name) => nameKey(name) === key);
}

export function toggleFollowing(names: readonly string[], player: string): string[] {
  if (followsPlayer(names, player)) return names.filter((name) => nameKey(name) !== nameKey(player));
  return parseFollowing(JSON.stringify([...names, player]));
}
