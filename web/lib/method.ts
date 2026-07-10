/** Types + pure helpers for the /method detail sections. The numbers all come from
    method.json (pipeline-exported effective production parameters — see
    tennis_model model/export.py build_method); nothing here hardcodes a tuned constant. */

export type MethodDoc = {
  tour: string;
  modelVersion: string;
  defaultRating: number;
  surfaces: string[];
  elo: {
    ratingScale: number; kScale: number; kOffset: number; kShape: number;
    surfaceKScale: number; surfaceKOffset: number; surfaceKShape: number;
    surfaceBlend: number; movFactor: number; movCap: number;
    skipWalkovers: boolean; retKMult: number;
    inactDays: number; inactBoost: number; bo5Scale: number;
    formDays: number; xsurf: number; blendN50: number; homeAdv: number;
  };
  tiers: { anchors: number[] | null; kMult: Record<string, number>; default: number };
  serveReturn: {
    formHalflifeDays: number; serveShrinkagePoints: number;
    surfaceServeShrinkage: number; eventShrinkage: number; pClip: number[];
  };
  context: { fatigueWindowDays: number; layoffDays: number; peakAge: number; winrateWindow: number };
  combiner: {
    algorithm: string; nBag: number; calibration: string; earlyStoppingRounds: number;
    xgb: Record<string, number>;
    featureCount: number;
    featureGroups: { antisymmetric: number; style: number; symmetric: number };
  };
  protocol: { backtestStartYear: number; tuneYears: number[]; valStartYear: number };
};

/** Display a JSON number inside a formula: strip float noise (0.8920000000000001 →
    "0.892"), drop a trailing ".0" (145.0 → "145"), and never use exponent notation
    (0.0005 stays "0.0005"). */
export function fmt(x: number): string {
  if (!isFinite(x)) return "—";
  const clean = Number(x.toPrecision(12)); // kill accumulated float noise
  let s = String(clean);
  if (s.includes("e") || s.includes("E")) {
    // small hyperparameters (e.g. gamma 5e-7) — expand and trim trailing zeros
    s = clean.toFixed(12).replace(/0+$/, "").replace(/\.$/, "");
  }
  return s;
}

/** The dynamic K-factor at n career (or surface) matches: scale / (n + offset)^shape.
    Rounded to 1 dp — powers the illustrative "K at n" table on /method. */
export function kAt(scale: number, offset: number, shape: number, n: number): number {
  return Math.round((scale / Math.pow(n + offset, shape)) * 10) / 10;
}
