export const pct = (x: number, d = 0) =>
  x == null || isNaN(x) ? "—" : `${(x * 100).toFixed(d)}%`;

export const SURFACES = ["Hard", "Clay", "Grass"] as const;
export type Surface = (typeof SURFACES)[number];

export const surfaceColor = (s: string) =>
  ({ Hard: "var(--color-hard)", Clay: "var(--color-clay)", Grass: "var(--color-grass)" } as Record<string, string>)[s] ||
  "var(--color-muted)";

export const eloKey = (s: string) =>
  ({ Hard: "eloHard", Clay: "eloClay", Grass: "eloGrass" } as Record<string, string>)[s] || "elo";

/** Heat color for a probability 0..1 — single-hue indigo luminance ramp.
    Returns hex so callers can append alpha digits (e.g. `${heat(p)}22`). */
export function heat(p: number): string {
  const stops: [number, [number, number, number]][] = [
    [0, [27, 29, 36]],
    [0.35, [57, 64, 110]],
    [0.6, [94, 106, 210]],
    [0.85, [130, 143, 255]],
    [1, [199, 205, 255]],
  ];
  let a = stops[0], b = stops[stops.length - 1];
  for (let i = 0; i < stops.length - 1; i++) {
    if (p >= stops[i][0] && p <= stops[i + 1][0]) { a = stops[i]; b = stops[i + 1]; break; }
  }
  const t = (p - a[0]) / (b[0] - a[0] || 1);
  const c = a[1].map((v, i) => Math.round(v + (b[1][i] - v) * t));
  return `#${c.map((v) => v.toString(16).padStart(2, "0")).join("")}`;
}

export type AgeDirection = "under" | "over";
export type AgeFilter = { dir: AgeDirection; value: number } | null;

export const AGE_MIN = 15;
export const AGE_MAX = 45;

/** Parse the age-control state into a filter. Mode "all" or an empty/non-numeric
    input mean no filter; decimals floor; out-of-range clamps to [AGE_MIN, AGE_MAX]. */
export function parseAgeFilter(mode: string, raw: string): AgeFilter {
  if (mode !== "under" && mode !== "over") return null;
  if (!raw.trim()) return null;
  const n = Math.floor(Number(raw));
  if (!Number.isFinite(n)) return null;
  return { dir: mode, value: Math.min(AGE_MAX, Math.max(AGE_MIN, n)) };
}

/** True when a player passes the age filter. No filter passes everyone; unknown ages
    never pass an active filter. Strict comparisons: Under 23 = age < 23, Over 30 = age > 30. */
export function passesAgeFilter(age: number | null | undefined, filter: AgeFilter): boolean {
  if (filter == null) return true;
  if (age == null) return false;
  return filter.dir === "under" ? age < filter.value : age > filter.value;
}

/** Rankings table rows: age-filter first, then sort by `key` descending, then top-100
    — so the board shows the top-100 of the filtered age group. */
export function rankRows<T extends { age: number | null }>(data: T[], key: string, filter: AgeFilter): T[] {
  return data
    .filter((p) => passesAgeFilter(p.age, filter))
    .sort((a, b) => Number((b as unknown as Record<string, unknown>)[key]) - Number((a as unknown as Record<string, unknown>)[key]))
    .slice(0, 100);
}

export const initials = (name: string) =>
  name.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();

/** Human labels for the Match Charting Project style features (shared by the player & style pages). */
export const STYLE_LABEL: Record<string, string> = {
  style_serve_dom: "Serve dominance", style_placement: "Serve variety", style_net: "Net frequency",
  style_snv: "Serve & volley", style_aggression: "Aggression", style_fhbh: "Forehand bias",
  style_return_depth: "Return depth", style_bp_clutch: "Break-point clutch",
};

export type RadarAxis = {
  key: string;
  label: string;
  source: "style" | "top"; // read profile.style[key] vs profile[key]
  fmt: (v: number) => string; // format the raw value for the readout
};

const styleFmt = (v: number) => (v * 100).toFixed(0);
const clutchFmt = (v: number) => (v >= 0 ? "+" : "") + (v * 100).toFixed(0);
const eloFmt = (v: number) => String(Math.round(v));

/**
 * The 13 radar axes in circle order: serve cluster → rally → return → surface skill.
 * Style features come from profile.style; skill stats are top-level profile fields.
 */
export const RADAR_AXES: RadarAxis[] = [
  { key: "servePct", label: "Serve %", source: "top", fmt: (v) => pct(v, 0) },
  { key: "style_serve_dom", label: "Serve dom.", source: "style", fmt: styleFmt },
  { key: "style_placement", label: "Serve variety", source: "style", fmt: styleFmt },
  { key: "style_snv", label: "Serve & volley", source: "style", fmt: styleFmt },
  { key: "style_net", label: "Net freq.", source: "style", fmt: styleFmt },
  { key: "style_fhbh", label: "Forehand bias", source: "style", fmt: styleFmt },
  { key: "style_aggression", label: "Aggression", source: "style", fmt: styleFmt },
  { key: "style_bp_clutch", label: "BP clutch", source: "style", fmt: clutchFmt },
  { key: "returnPct", label: "Return %", source: "top", fmt: (v) => pct(v, 0) },
  { key: "style_return_depth", label: "Return depth", source: "style", fmt: styleFmt },
  { key: "eloHard", label: "Hard Elo", source: "top", fmt: eloFmt },
  { key: "eloClay", label: "Clay Elo", source: "top", fmt: eloFmt },
  { key: "eloGrass", label: "Grass Elo", source: "top", fmt: eloFmt },
];

/**
 * Build a mid-rank percentile scaler in [0,1] from a population of values.
 * pct(v) = (#below + 0.5·#equal) / n — robust to outliers and ties. Nulls excluded by caller.
 */
export function percentileScaler(values: number[]): (v: number) => number {
  const n = values.length;
  return (v: number) => {
    if (!n) return 0;
    let lt = 0, eq = 0;
    for (const x of values) { if (x < v) lt++; else if (x === v) eq++; }
    return (lt + 0.5 * eq) / n;
  };
}

const comb = (n: number, k: number) => {
  let r = 1;
  for (let i = 0; i < k; i++) r = (r * (n - i)) / (i + 1);
  return r;
};
const matchFromSet = (sa: number, need: number) => {
  let p = 0;
  for (let j = 0; j < need; j++) p += comb(need - 1 + j, j) * sa ** need * (1 - sa) ** j;
  return p;
};

/** Set-score distribution consistent with a combiner match win prob (JS port of markov). */
export function scoreDist(pMatch: number, bestOf: number): { label: string; p: number; a: boolean }[] {
  const need = Math.floor(bestOf / 2) + 1;
  let lo = 1e-4, hi = 1 - 1e-4;
  for (let i = 0; i < 50; i++) {
    const mid = (lo + hi) / 2;
    if (matchFromSet(mid, need) < pMatch) lo = mid; else hi = mid;
  }
  const sa = (lo + hi) / 2, sb = 1 - sa;
  const out: { label: string; p: number; a: boolean }[] = [];
  for (let j = 0; j < need; j++) {
    out.push({ label: `${need}-${j}`, p: comb(need - 1 + j, j) * sa ** need * sb ** j, a: true });
    out.push({ label: `${j}-${need}`, p: comb(need - 1 + j, j) * sb ** need * sa ** j, a: false });
  }
  return out.sort((x, y) => y.p - x.p);
}
