export const pct = (x: number, d = 0) =>
  x == null || isNaN(x) ? "—" : `${(x * 100).toFixed(d)}%`;

/** Honest caveat for a tournament card when its odds are NOT running on the real released
    draw. `drawStatus` comes from the backend (sim/tournaments): "real"/"final" (the actual
    bracket — no caveat), "partial" (some of the current round posted, the rest projected),
    "seeded" (draw not released — the field is seeded by rating). Returns null when there is
    nothing to flag, so a normal real-draw card is unchanged. */
export function drawCaveat(t: { status: string; drawStatus?: string }):
  { label: string; note: string } | null {
  if (t.status === "completed") return null;
  if (t.drawStatus === "partial")
    return {
      label: "Draw incomplete",
      note: "The full draw isn’t posted yet — later matchups are a model projection, not the official bracket.",
    };
  if (t.drawStatus === "seeded")
    return {
      label: "Projected draw",
      note: "The draw hasn’t been released — these odds seed the field by rating, not the actual bracket.",
    };
  return null; // "real" / "final" / legacy undefined -> the actual draw, no caveat
}

export const SURFACES = ["Hard", "Clay", "Grass"] as const;
export type Surface = (typeof SURFACES)[number];

export const surfaceColor = (s: string) =>
  ({ Hard: "var(--color-hard)", Clay: "var(--color-clay)", Grass: "var(--color-grass)" } as Record<string, string>)[s] ||
  "var(--color-muted)";

export const eloKey = (s: string) =>
  ({ Hard: "eloHard", Clay: "eloClay", Grass: "eloGrass" } as Record<string, string>)[s] || "elo";

/** Surface-blend weight per tour — mirrors tennis_model config.py ELO_PARAM_OVERRIDES[tour].surface_blend
    (ATP 0.63, WTA 0.62; BLEND_N50 = 0, so the blend is a fixed linear mix). The exported surface Elo already
    carries cross-surface transfer, so this reproduces the model's own `elo.blended()` rating exactly. Keep in
    sync with config.py if the blend is ever retuned. */
export const SURFACE_BLEND: Record<string, number> = { atp: 0.63, wta: 0.62 };

/** The rating the model actually predicts with on a surface: (1 − b)·overall + b·surface.
    Unlike raw surface Elo (heavily shrunk, low spread), this tracks overall class — so it lines up
    with who the model favours. */
export const blendedElo = (overall: number, surfaceElo: number, tour: string): number =>
  Math.round((1 - (SURFACE_BLEND[tour] ?? 0.5)) * overall + (SURFACE_BLEND[tour] ?? 0.5) * surfaceElo);

const SLAM_NAMES = ["wimbledon", "roland garros", "french open", "us open", "australian open"];

/** Tournament tier/prestige from the `level` string, with the four majors pinned by name so a
    mislabeled slam (ATP Wimbledon currently exports level "Q") still ranks first. `rank` sorts
    ascending (0 = Grand Slam = most prestigious); `short` is a compact category chip
    (GS / 1000 / 500 / 250); `full` is a display name that repairs the slam mislabel. */
export function tournamentTier(level: string = "", eventName: string = ""): { rank: number; short: string; full: string } {
  const l = String(level).toLowerCase();
  const ev = eventName.toLowerCase();
  if (l.includes("grand") || SLAM_NAMES.some((s) => ev.includes(s))) return { rank: 0, short: "GS", full: "Grand Slam" };
  if (l.includes("final")) return { rank: 1, short: "Finals", full: level || "Tour Finals" };
  if (l.includes("1000")) return { rank: 2, short: "1000", full: level };
  if (l.includes("olympic")) return { rank: 2, short: "Oly", full: "Olympics" };
  if (l.endsWith("500")) return { rank: 3, short: "500", full: level };
  if (l.endsWith("250")) return { rank: 4, short: "250", full: level };
  if (l.includes("cup")) return { rank: 5, short: "Cup", full: level };
  if (l.endsWith("125")) return { rank: 6, short: "125", full: level };
  return { rank: 7, short: "Tour", full: level && l !== "q" ? level : "Tour" };
}

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

/** Row shape the explorer reads from players.json. The enrichment fields
    (heightCm, per-surface pcts, form90, winRate10) are optional — snapshots built
    before the export enrichment lack the keys entirely. */
export type ExplorerPlayer = {
  name: string; eloRank: number; elo: number;
  eloHard: number; eloClay: number; eloGrass: number;
  servePct: number; returnPct: number;
  age: number | null; matches: number; rankPoints: number | null; country: string | null;
  aggression?: number | null; serveDom?: number | null;
  heightCm?: number | null; form90?: number | null; winRate10?: number | null;
  servePctHard?: number | null; servePctClay?: number | null; servePctGrass?: number | null;
  returnPctHard?: number | null; returnPctClay?: number | null; returnPctGrass?: number | null;
};

export type ExplorerAxis = {
  key: string;                                        // stable URL id (?x=/&y=/&sort=)
  label: string;
  fmt: (v: number) => string;                         // ticks, tooltip and table cells
  get: (p: ExplorerPlayer, tour: string) => number | null;   // null-safe accessor
};

const num = (v: unknown): number | null => (typeof v === "number" && isFinite(v) ? v : null);
const signedInt = (v: number) => (v >= 0 ? "+" : "") + Math.round(v);

/** Every plottable/sortable per-player attribute. Surface ratings are exposed
    BLENDED only (via blendedElo) — raw surface Elo is heavily shrunk and would
    contradict what the rankings board shows. */
export const EXPLORER_AXES: ExplorerAxis[] = [
  { key: "elo", label: "Elo rating", fmt: eloFmt, get: (p) => num(p.elo) },
  { key: "eloHardBlend", label: "Hard rating (blended)", fmt: eloFmt, get: (p, t) => (num(p.elo) == null || num(p.eloHard) == null ? null : blendedElo(p.elo, p.eloHard, t)) },
  { key: "eloClayBlend", label: "Clay rating (blended)", fmt: eloFmt, get: (p, t) => (num(p.elo) == null || num(p.eloClay) == null ? null : blendedElo(p.elo, p.eloClay, t)) },
  { key: "eloGrassBlend", label: "Grass rating (blended)", fmt: eloFmt, get: (p, t) => (num(p.elo) == null || num(p.eloGrass) == null ? null : blendedElo(p.elo, p.eloGrass, t)) },
  { key: "servePct", label: "Serve points won", fmt: (v) => pct(v, 1), get: (p) => num(p.servePct) },
  { key: "returnPct", label: "Return points won", fmt: (v) => pct(v, 1), get: (p) => num(p.returnPct) },
  { key: "servePctHard", label: "Serve % · Hard", fmt: (v) => pct(v, 1), get: (p) => num(p.servePctHard) },
  { key: "servePctClay", label: "Serve % · Clay", fmt: (v) => pct(v, 1), get: (p) => num(p.servePctClay) },
  { key: "servePctGrass", label: "Serve % · Grass", fmt: (v) => pct(v, 1), get: (p) => num(p.servePctGrass) },
  { key: "returnPctHard", label: "Return % · Hard", fmt: (v) => pct(v, 1), get: (p) => num(p.returnPctHard) },
  { key: "returnPctClay", label: "Return % · Clay", fmt: (v) => pct(v, 1), get: (p) => num(p.returnPctClay) },
  { key: "returnPctGrass", label: "Return % · Grass", fmt: (v) => pct(v, 1), get: (p) => num(p.returnPctGrass) },
  { key: "form90", label: "Form (90-day Elo Δ)", fmt: signedInt, get: (p) => num(p.form90) },
  { key: "winRate10", label: "Last-10 win rate", fmt: (v) => pct(v, 0), get: (p) => num(p.winRate10) },
  { key: "age", label: "Age", fmt: (v) => String(Math.round(v)), get: (p) => num(p.age) },
  { key: "heightCm", label: "Height (cm)", fmt: (v) => String(Math.round(v)), get: (p) => num(p.heightCm) },
  { key: "matches", label: "Career matches", fmt: (v) => String(Math.round(v)), get: (p) => num(p.matches) },
  { key: "rankPoints", label: "Ranking points", fmt: (v) => String(Math.round(v)), get: (p) => num(p.rankPoints) },
  { key: "aggression", label: "Aggression (style)", fmt: styleFmt, get: (p) => num(p.aggression) },
  { key: "serveDom", label: "Serve dominance (style)", fmt: styleFmt, get: (p) => num(p.serveDom) },
];

export const EXPLORER_PRESETS: { label: string; x: string; y: string }[] = [
  { label: "Serve vs return", x: "servePct", y: "returnPct" },
  { label: "Age vs rating", x: "age", y: "elo" },
  { label: "Height vs serve", x: "heightCm", y: "servePct" },
  { label: "Clay vs grass rating", x: "eloClayBlend", y: "eloGrassBlend" },
];

/** Axes with enough data to be worth offering (≥3 non-null values in the field) —
    auto-hides enrichment axes when the served snapshot predates them. */
export function availableAxes(players: ExplorerPlayer[], tour: string): ExplorerAxis[] {
  return EXPLORER_AXES.filter(
    (a) => players.reduce((n, p) => n + (a.get(p, tour) != null ? 1 : 0), 0) >= 3,
  );
}

/** Players with BOTH axis values, as scatter points; `missing` counts the dropped. */
export function plottable<T extends ExplorerPlayer>(
  players: T[], xAxis: ExplorerAxis, yAxis: ExplorerAxis, tour: string,
): { points: { p: T; x: number; y: number }[]; missing: number } {
  const points: { p: T; x: number; y: number }[] = [];
  for (const p of players) {
    const x = xAxis.get(p, tour), y = yAxis.get(p, tour);
    if (x != null && y != null) points.push({ p, x, y });
  }
  return { points, missing: players.length - points.length };
}

/** Sort a field by one axis; players missing the value go LAST in either direction. */
export function sortByAxis<T extends ExplorerPlayer>(
  players: T[], axis: ExplorerAxis, dir: "asc" | "desc", tour: string,
): T[] {
  const sign = dir === "asc" ? 1 : -1;
  return [...players].sort((a, b) => {
    const va = axis.get(a, tour), vb = axis.get(b, tour);
    if (va == null && vb == null) return 0;
    if (va == null) return 1;
    if (vb == null) return -1;
    return sign * (va - vb);
  });
}

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
