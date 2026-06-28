export const pct = (x: number, d = 0) =>
  x == null || isNaN(x) ? "—" : `${(x * 100).toFixed(d)}%`;

export const SURFACES = ["Hard", "Clay", "Grass"] as const;
export type Surface = (typeof SURFACES)[number];

export const surfaceColor = (s: string) =>
  ({ Hard: "var(--color-hard)", Clay: "var(--color-clay)", Grass: "var(--color-grass)" } as Record<string, string>)[s] ||
  "var(--color-muted)";

export const eloKey = (s: string) =>
  ({ Hard: "eloHard", Clay: "eloClay", Grass: "eloGrass" } as Record<string, string>)[s] || "elo";

/** Heat color for a probability 0..1 (ink → cyan → lime → gold). */
export function heat(p: number): string {
  const stops: [number, [number, number, number]][] = [
    [0, [17, 22, 31]],
    [0.35, [84, 160, 255]],
    [0.6, [120, 200, 90]],
    [0.85, [200, 255, 60]],
    [1, [255, 194, 75]],
  ];
  let a = stops[0], b = stops[stops.length - 1];
  for (let i = 0; i < stops.length - 1; i++) {
    if (p >= stops[i][0] && p <= stops[i + 1][0]) { a = stops[i]; b = stops[i + 1]; break; }
  }
  const t = (p - a[0]) / (b[0] - a[0] || 1);
  const c = a[1].map((v, i) => Math.round(v + (b[1][i] - v) * t));
  return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
}

export const initials = (name: string) =>
  name.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();

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
