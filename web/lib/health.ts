/** Types + pure helpers for the (hidden) /health operations page. The report shape is
    written by tennis_model data/health.py `main()` and mirrored to /data/health.json —
    every verdict (ok / covered / fail, limits, relaxations) is decided server-side in
    `source_checks()`; this module only maps verdicts to presentation. */

export type CheckRow = {
  key: string;
  label: string;
  value: number | null;
  limit: number;
  unit: string; // "d" (age, max) | "frac" (coverage, min)
  date: string | null;
  ok: boolean;
  note: string | null; // over-limit but deliberately not alarmed (shadowed redundancy)
  problem: string | null;
};

export type TourReport = {
  matches: number;
  date_max: string | null;
  checks: CheckRow[];
  problems: string[];
  output: {
    matches: number | null;
    forecast_lines: number | null;
    forecast_max_as_of: string | null;
    problems: string[];
  };
};

export type HealthReport = {
  generated: string;
  generatedAt?: string;
  ok: boolean;
  problems_changed?: boolean;
  tours: Record<string, TourReport>;
};

export type Drift = {
  status: "ok" | "drift" | "insufficient";
  n: number | null;
  d: number | null;
  t: number | null;
};

export type Tone = "ok" | "warn" | "fail" | "muted";

export const TONE_COLOR: Record<Tone, string> = {
  ok: "var(--color-win)",
  warn: "var(--color-champ)",
  fail: "var(--color-loss)",
  muted: "var(--color-faint)",
};

export const REPO = "ARJUNVARMA2000/tennis-elo";

/** A failing row is red; a passing row carrying a note (e.g. a frozen-but-shadowed
    source) is amber; a clean pass is green. */
export function checkTone(row: Pick<CheckRow, "ok" | "note">): Tone {
  return !row.ok ? "fail" : row.note ? "warn" : "ok";
}

export function checkStatusLabel(row: Pick<CheckRow, "ok" | "note">): string {
  return !row.ok ? "fail" : row.note ? "covered" : "ok";
}

export function driftTone(status: Drift["status"] | undefined): Tone {
  return status === "drift" ? "warn" : status === "ok" ? "ok" : "muted";
}

export function driftLabel(d: Drift | undefined): string {
  if (!d) return "no data";
  if (d.status === "drift") return "drift — re-tune advised";
  if (d.status === "ok") return `calibrated (n=${d.n ?? "?"})`;
  return `arming (n=${d.n ?? 0})`;
}

/** Page-level verdict: fail if the sentinel found problems; warn if everything passes
    but a source is running on redundancy (noted rows); ok otherwise. */
export function overall(report: HealthReport): { tone: Tone; problems: number; noted: number } {
  const tours = Object.values(report.tours);
  const problems = tours.reduce((n, t) => n + t.problems.length + t.output.problems.length, 0);
  const noted = tours.reduce((n, t) => n + t.checks.filter((c) => c.ok && c.note).length, 0);
  return { tone: !report.ok ? "fail" : noted ? "warn" : "ok", problems, noted };
}

/** "19d" for ages, "97%" for coverage fractions, em dash for missing. */
export function fmtValue(row: Pick<CheckRow, "value" | "unit">): string {
  if (row.value == null) return "—";
  return row.unit === "frac" ? `${Math.round(row.value * 100)}%` : `${row.value}${row.unit}`;
}

/** Ages are maxima ("≤ 14d"); coverage is a minimum ("≥ 60%"). */
export function fmtLimit(row: Pick<CheckRow, "limit" | "unit">): string {
  return row.unit === "frac" ? `≥ ${Math.round(row.limit * 100)}%` : `≤ ${row.limit}${row.unit}`;
}
