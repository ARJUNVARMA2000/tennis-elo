import type { Tour } from "@/lib/tour";

/** Pure URL-state helpers (node-testable). Policy: the ATP default is elided from
    URLs (`?tour=` appears only for wta) so default links stay clean; player deep
    links carry the FULL display name — profiles.json is keyed by it, and
    encodeURIComponent/useSearchParams round-trip spaces + diacritics losslessly.
    Hrefs are emitted in trailing-slash form (next.config trailingSlash: true) so
    direct loads on GitHub Pages don't bounce through a 301 that can drop state. */

export function resolveTour(param: string | null, saved: string | null): Tour {
  if (param === "atp" || param === "wta") return param;
  if (saved === "atp" || saved === "wta") return saved;
  return "atp";
}

/** Set (or delete, when value is null) one key in a search string, preserving the
    rest. Accepts "" | "?a=b" | "a=b"; returns "" or "?...". */
export function setSearchParam(search: string, key: string, value: string | null): string {
  const sp = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
  if (value === null) sp.delete(key);
  else sp.set(key, value);
  const s = sp.toString();
  return s ? `?${s}` : "";
}

/** Merge the active tour into a search string (wta explicit, atp elided). */
export function setSearchTour(search: string, tour: Tour): string {
  return setSearchParam(search, "tour", tour === "wta" ? "wta" : null);
}

/** Append the active tour to any internal href (nav links, cross-links). */
export function withTour(href: string, tour: Tour): string {
  if (tour !== "wta") return href;
  const [path, search] = href.split("?");
  return `${path}${setSearchTour(search ?? "", tour)}`;
}

/** Deep link to a player's profile page. */
export function playerHref(name: string, tour: Tour): string {
  return `/player/${setSearchTour(setSearchParam("", "p", name), tour)}`;
}

/** Deep link to a two-player page (/style/ or /predict/). */
export function pairHref(base: "/style/" | "/predict/", a: string, b: string, tour: Tour): string {
  return `${base}${setSearchTour(setSearchParam(setSearchParam("", "a", a), "b", b), tour)}`;
}
