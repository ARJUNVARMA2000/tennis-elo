export const TENNIS_ABSTRACT_SCHEMA = "tennis-abstract-benchmark-v1" as const;
export const TENNIS_ABSTRACT_DELTA_DIRECTION =
  "tennisAbstract-minus-deuce; positive favors DEUCE" as const;

export type BenchmarkTour = "atp" | "wta";

export type BenchmarkStatus = "accruing" | "complete" | "unavailable";

export type BenchmarkMetricValues = {
  logloss: number | null;
  brier: number | null;
};

export type BenchmarkScores = BenchmarkMetricValues & {
  n: number;
};

export type PairedBenchmarkScores = {
  n: number;
  direction: typeof TENNIS_ABSTRACT_DELTA_DIRECTION;
  loglossDelta: number | null;
  seLogloss: number | null;
  brierDelta: number | null;
  seBrier: number | null;
};

export type ReachStageComparison = {
  stage: string;
  resolved: number;
  n: number;
  eligible: number;
  graded: number;
  pending: number;
  excluded: number;
  deuce: BenchmarkScores;
  tennisAbstract: BenchmarkScores;
  paired: PairedBenchmarkScores;
  exclusionReasons: Record<string, number>;
};

export type ReachAggregateComparison = {
  deuce: BenchmarkScores;
  tennisAbstract: BenchmarkScores;
  paired: PairedBenchmarkScores;
};

/** Tolerated legacy/internal state; canonical public reports omit an unscored aggregate. */
export type UnscoredReachAggregate = {
  status: "pending" | "unavailable";
  reason?: string;
};

export type TennisAbstractBenchmark = {
  schema: typeof TENNIS_ABSTRACT_SCHEMA;
  benchmark: {
    id: "tennis-abstract";
    name: "Tennis Abstract";
    tour: BenchmarkTour;
    event: string;
    season: number;
    espnId: string;
  };
  status: BenchmarkStatus;
  source: {
    name: string;
    url: string;
    capturedAt: string;
    lastModified?: string;
  };
  capture: {
    captureLocalDate: "2026-08-30";
    classification: "first-post-start-capture";
    eligibleMatchProof: string;
    eventTimezone: "America/New_York";
  };
  matchComparison: {
    eligible: number;
    graded: number;
    pending: number;
    excluded: number;
    deuce: BenchmarkScores;
    tennisAbstract: BenchmarkScores;
    paired: PairedBenchmarkScores;
    byRound?: unknown[];
    exclusionReasons?: Record<string, number>;
  };
  reachComparison?: {
    fieldSize: 128;
    fieldAligned: true;
    stages: ReachStageComparison[];
    exclusionReasons: Record<string, number>;
    macro?: ReachAggregateComparison;
    champion?: ReachAggregateComparison | UnscoredReachAggregate;
  };
  caveats: string[];
};

export type DeltaVerdict = "deuce" | "tennis-abstract" | "even" | "unavailable";

const finite = (value: unknown): value is number =>
  typeof value === "number" && Number.isFinite(value);

const count = (value: unknown): value is number =>
  finite(value) && Number.isInteger(value) && value >= 0;

const nullableFinite = (value: unknown): value is number | null => value === null || finite(value);

const record = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const metricValues = (value: unknown): value is BenchmarkMetricValues =>
  record(value) && nullableFinite(value.logloss) && nullableFinite(value.brier);

const scores = (value: unknown): value is BenchmarkScores => {
  if (!record(value)) return false;
  const n = value.n;
  if (!count(n) || !metricValues(value)) return false;
  return n === 0
    ? value.logloss === null && value.brier === null
    : finite(value.logloss) && value.logloss >= 0
      && finite(value.brier) && value.brier >= 0 && value.brier <= 1;
};

const pairedBase = (value: unknown, n: number): value is Record<string, unknown> =>
  record(value) && value.n === n && value.direction === TENNIS_ABSTRACT_DELTA_DIRECTION;

const pairedMatchScores = (value: unknown, n: number): value is PairedBenchmarkScores => {
  if (!pairedBase(value, n)) return false;
  const deltas = [value.loglossDelta, value.brierDelta];
  const standardErrors = [value.seLogloss, value.seBrier];
  if (n === 0) return [...deltas, ...standardErrors].every((item) => item === null);
  if (!deltas.every(finite)) return false;
  if (n === 1) return standardErrors.every((item) => item === null);
  return standardErrors.every((item) => finite(item) && item >= 0);
};

const pairedReachScores = (value: unknown, n: number): value is PairedBenchmarkScores => {
  if (!pairedBase(value, n)) return false;
  const deltas = [value.loglossDelta, value.brierDelta];
  if (value.seLogloss !== null || value.seBrier !== null) return false;
  return n === 0 ? deltas.every((item) => item === null) : deltas.every(finite);
};

/** Champion-distribution Brier is multiclass and may legitimately exceed binary Brier's 1. */
const aggregateScores = (value: unknown): value is BenchmarkScores =>
  record(value) && count(value.n) && value.n > 0
  && finite(value.logloss) && value.logloss >= 0
  && finite(value.brier) && value.brier >= 0 && value.brier <= 2;

export const isScoredReachAggregate = (value: unknown): value is ReachAggregateComparison => {
  if (!record(value) || !aggregateScores(value.deuce)
      || !aggregateScores(value.tennisAbstract)) return false;
  return value.deuce.n === value.tennisAbstract.n
    && pairedReachScores(value.paired, value.deuce.n);
};

const unscoredAggregate = (value: unknown): value is UnscoredReachAggregate =>
  record(value) && (value.status === "pending" || value.status === "unavailable")
  && (value.reason === undefined || typeof value.reason === "string");

const countMap = (value: unknown): value is Record<string, number> =>
  record(value) && Object.values(value).every(count);

const reachStage = (value: unknown): value is ReachStageComparison =>
  record(value) && typeof value.stage === "string" && value.n === 128
  && count(value.resolved) && count(value.eligible) && count(value.graded)
  && count(value.pending) && count(value.excluded)
  && value.resolved === value.graded
  && value.eligible === 128 && value.excluded === 0
  && value.pending === value.n - value.graded
  && scores(value.deuce) && value.deuce.n === value.graded
  && scores(value.tennisAbstract) && value.tennisAbstract.n === value.graded
  && pairedReachScores(value.paired, value.graded)
  && countMap(value.exclusionReasons) && Object.keys(value.exclusionReasons).length === 0;

const validTimestamp = (value: unknown): value is string =>
  typeof value === "string" && Number.isFinite(Date.parse(value));

const lifecycleStatus = (
  match: TennisAbstractBenchmark["matchComparison"],
  stages: ReachStageComparison[] = [],
): BenchmarkStatus => {
  const pending = match.pending + stages.reduce((total, stage) => total + stage.pending, 0);
  if (pending > 0) return "accruing";
  const graded = match.graded + stages.reduce((total, stage) => total + stage.graded, 0);
  return graded > 0 ? "complete" : "unavailable";
};

/**
 * Keep the optional artifact fail-soft in the browser. Release validation remains the
 * authoritative schema gate; this guard merely prevents an old or partial payload from
 * taking down /track, and deliberately allows unknown additive fields.
 */
export function isTennisAbstractBenchmark(
  value: unknown,
  expectedTour?: BenchmarkTour,
): value is TennisAbstractBenchmark {
  if (!record(value) || value.schema !== TENNIS_ABSTRACT_SCHEMA) return false;
  if (!record(value.benchmark) || value.benchmark.id !== "tennis-abstract"
      || value.benchmark.name !== "Tennis Abstract"
      || (value.benchmark.tour !== "atp" && value.benchmark.tour !== "wta")
      || (expectedTour !== undefined && value.benchmark.tour !== expectedTour)
      || value.benchmark.event !== "US Open"
      || value.benchmark.season !== 2026 || value.benchmark.espnId !== "189-2026") return false;
  if (value.status !== "accruing" && value.status !== "complete" && value.status !== "unavailable") return false;
  const expectedSourceUrl = value.benchmark.tour === "atp"
    ? "https://www.tennisabstract.com/current/2026USOpenMenForecast.html"
    : "https://www.tennisabstract.com/current/2026USOpenWomenForecast.html";
  if (!record(value.source) || value.source.name !== "Tennis Abstract"
      || value.source.url !== expectedSourceUrl || !validTimestamp(value.source.capturedAt)) return false;
  if (!record(value.capture) || value.capture.captureLocalDate !== "2026-08-30"
      || value.capture.classification !== "first-post-start-capture"
      || typeof value.capture.eligibleMatchProof !== "string"
      || !value.capture.eligibleMatchProof.trim()
      || value.capture.eventTimezone !== "America/New_York") return false;
  if (!record(value.matchComparison)) return false;
  const match = value.matchComparison;
  const { eligible, graded, pending, excluded } = match;
  if (!count(eligible) || !count(graded) || !count(pending) || !count(excluded)
      || eligible !== graded + pending || eligible + excluded !== 64) return false;
  if (!scores(match.deuce) || !scores(match.tennisAbstract) || !record(match.paired)) return false;
  if (match.deuce.n !== match.graded || match.tennisAbstract.n !== match.graded
      || !pairedMatchScores(match.paired, match.graded)) return false;
  if (!Array.isArray(value.caveats) || !value.caveats.length
      || !value.caveats.every((item) => typeof item === "string" && item.trim())) return false;
  if (value.source.lastModified !== undefined && !validTimestamp(value.source.lastModified)) return false;
  if (value.reachComparison === undefined) {
    return value.status === lifecycleStatus(match as TennisAbstractBenchmark["matchComparison"]);
  }
  if (!record(value.reachComparison) || !Array.isArray(value.reachComparison.stages)
      || value.reachComparison.fieldSize !== 128 || value.reachComparison.fieldAligned !== true
      || !countMap(value.reachComparison.exclusionReasons)
      || Object.keys(value.reachComparison.exclusionReasons).length !== 0
      || !value.reachComparison.stages.every(reachStage)) return false;
  const expectedStages = ["R64", "R32", "R16", "QF", "SF", "F", "W"];
  if (value.reachComparison.stages.length !== expectedStages.length
      || value.reachComparison.stages.some((stage, index) => stage.stage !== expectedStages[index])) return false;
  if (value.reachComparison.stages.some((stage, index, stages) => (
    index > 0 && stages[index - 1].resolved < stage.resolved
  ))) return false;
  if (value.status !== lifecycleStatus(
    match as TennisAbstractBenchmark["matchComparison"],
    value.reachComparison.stages as ReachStageComparison[],
  )) return false;
  return (value.reachComparison.macro === undefined || isScoredReachAggregate(value.reachComparison.macro))
    && (value.reachComparison.champion === undefined
      || isScoredReachAggregate(value.reachComparison.champion)
      || unscoredAggregate(value.reachComparison.champion));
}

export function formatBenchmarkMetric(value: number | null | undefined, digits = 4): string {
  return finite(value) ? value.toFixed(digits) : "—";
}

/** Signed external-minus-DEUCE delta. Positive therefore means DEUCE had the lower score. */
export function formatBenchmarkDelta(value: number | null | undefined, digits = 4): string {
  if (!finite(value)) return "—";
  const rounded = Number(value.toFixed(digits));
  if (rounded === 0) return (0).toFixed(digits);
  return `${rounded > 0 ? "+" : "−"}${Math.abs(rounded).toFixed(digits)}`;
}

/** Verdict at the same precision shown to the reader, preserving the external-minus-DEUCE sign. */
export function deltaVerdict(
  value: number | null | undefined,
  digits = 4,
): DeltaVerdict {
  if (!finite(value)) return "unavailable";
  const rounded = Number(value.toFixed(digits));
  return rounded > 0 ? "deuce" : rounded < 0 ? "tennis-abstract" : "even";
}

/** Compute the displayed external-minus-DEUCE delta from two lower-is-better scores. */
export function externalMinusDeuce(
  external: number | null | undefined,
  deuce: number | null | undefined,
): number | null {
  return finite(external) && finite(deuce) ? external - deuce : null;
}

export function safeBenchmarkSourceUrl(value: string | null | undefined): string | null {
  if (!value) return null;
  try {
    const parsed = new URL(value);
    if ((parsed.protocol !== "https:" && parsed.protocol !== "http:")
        || parsed.username || parsed.password) return null;
    return parsed.toString();
  } catch {
    return null;
  }
}

export function benchmarkSourceLabel(value: string | null | undefined): string {
  return value?.trim() || "Tennis Abstract";
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function formatBenchmarkTimestamp(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return "—";
  const day = String(date.getUTCDate()).padStart(2, "0");
  const hour = String(date.getUTCHours()).padStart(2, "0");
  const minute = String(date.getUTCMinutes()).padStart(2, "0");
  return `${MONTHS[date.getUTCMonth()]} ${day}, ${date.getUTCFullYear()} · ${hour}:${minute} UTC`;
}

const STAGE_LABELS: Record<string, string> = {
  r128: "Round of 128",
  roundof128: "Round of 128",
  r64: "Round of 64",
  roundof64: "Round of 64",
  r32: "Round of 32",
  roundof32: "Round of 32",
  r16: "Round of 16",
  roundof16: "Round of 16",
  qf: "Quarterfinals",
  sf: "Semifinals",
  f: "Final",
  champion: "Champion",
  winner: "Champion",
  w: "Champion",
};

export function benchmarkStageLabel(value: string): string {
  const normalized = value.trim().toLowerCase().replace(/[\s_-]+/g, "");
  return STAGE_LABELS[normalized] ?? value;
}

export function formatExclusionReason(value: string): string {
  const words = value
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replace(/[._-]+/g, " ")
    .trim()
    .toLowerCase();
  return words ? words.charAt(0).toUpperCase() + words.slice(1) : "Other";
}
