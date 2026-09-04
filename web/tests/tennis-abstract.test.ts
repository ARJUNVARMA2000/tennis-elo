import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { TennisAbstractFallback, TennisAbstractSection } from "@/app/track/page";
import {
  TENNIS_ABSTRACT_DELTA_DIRECTION,
  benchmarkSourceLabel,
  benchmarkStageLabel,
  deltaVerdict,
  externalMinusDeuce,
  formatBenchmarkDelta,
  formatBenchmarkMetric,
  formatBenchmarkTimestamp,
  formatExclusionReason,
  isScoredReachAggregate,
  isTennisAbstractBenchmark,
  safeBenchmarkSourceUrl,
} from "@/lib/tennis-abstract";

const stages = ["R64", "R32", "R16", "QF", "SF", "F", "W"];
const reachStage = (stage: string, resolved = 4) => ({
  stage,
  resolved,
  n: 128,
  eligible: 128,
  graded: resolved,
  pending: 128 - resolved,
  excluded: 0,
  deuce: {
    n: resolved,
    logloss: resolved ? 0.2 : null,
    brier: resolved ? 0.06 : null,
  },
  tennisAbstract: {
    n: resolved,
    logloss: resolved ? 0.21 : null,
    brier: resolved ? 0.07 : null,
  },
  paired: {
    n: resolved,
    direction: TENNIS_ABSTRACT_DELTA_DIRECTION,
    loglossDelta: resolved ? 0.01 : null,
    seLogloss: null,
    brierDelta: resolved ? 0.01 : null,
    seBrier: null,
  },
  exclusionReasons: {},
});

const artifact = {
  schema: "tennis-abstract-benchmark-v1",
  benchmark: {
    id: "tennis-abstract",
    name: "Tennis Abstract",
    tour: "atp",
    event: "US Open",
    season: 2026,
    espnId: "189-2026",
  },
  status: "accruing",
  source: {
    name: "Tennis Abstract",
    url: "https://www.tennisabstract.com/current/2026USOpenMenForecast.html",
    capturedAt: "2026-08-31T00:55:00Z",
  },
  capture: {
    captureLocalDate: "2026-08-30",
    classification: "first-post-start-capture",
    eligibleMatchProof: "saved scheduledDate is strictly after captureLocalDate",
    eventTimezone: "America/New_York",
  },
  matchComparison: {
    eligible: 60,
    graded: 2,
    pending: 58,
    excluded: 4,
    deuce: { n: 2, logloss: 0.51, brier: 0.17 },
    tennisAbstract: { n: 2, logloss: 0.54, brier: 0.18 },
    paired: {
      n: 2,
      direction: TENNIS_ABSTRACT_DELTA_DIRECTION,
      loglossDelta: 0.03,
      seLogloss: 0.01,
      brierDelta: 0.01,
      seBrier: 0.005,
    },
  },
  reachComparison: {
    fieldSize: 128,
    fieldAligned: true,
    stages: stages.map((stage) => reachStage(stage)),
    exclusionReasons: {},
  },
  caveats: ["First capture followed the start of play."],
  additiveFutureField: { allowed: true },
};

describe("Tennis Abstract benchmark payload", () => {
  it("accepts the exact v1 identity and additive fields", () => {
    expect(isTennisAbstractBenchmark(artifact, "atp")).toBe(true);
    expect(isTennisAbstractBenchmark(artifact, "wta")).toBe(false);
    expect(isTennisAbstractBenchmark({ ...artifact, schema: "benchmark-v2" })).toBe(false);
    expect(isTennisAbstractBenchmark({
      ...artifact,
      benchmark: { ...artifact.benchmark, season: 2027 },
    })).toBe(false);
    expect(isTennisAbstractBenchmark({
      ...artifact,
      capture: { ...artifact.capture, classification: "pre-tournament" },
    })).toBe(false);
  });

  it("rejects count, score, lifecycle, and ordered-stage contradictions", () => {
    expect(isTennisAbstractBenchmark({
      ...artifact,
      matchComparison: { ...artifact.matchComparison, eligible: 61 },
    })).toBe(false);
    expect(isTennisAbstractBenchmark({
      ...artifact,
      matchComparison: {
        ...artifact.matchComparison,
        deuce: { ...artifact.matchComparison.deuce, n: 1 },
      },
    })).toBe(false);
    expect(isTennisAbstractBenchmark({ ...artifact, status: "complete" })).toBe(false);
    expect(isTennisAbstractBenchmark({ ...artifact, status: "unavailable" })).toBe(false);
    expect(isTennisAbstractBenchmark({
      ...artifact,
      reachComparison: { stages: [{ ...artifact.reachComparison.stages[0], n: "128" }] },
    })).toBe(false);
    expect(isTennisAbstractBenchmark({
      ...artifact,
      reachComparison: {
        ...artifact.reachComparison,
        stages: [...artifact.reachComparison.stages].reverse(),
      },
    })).toBe(false);
    expect(isTennisAbstractBenchmark({
      ...artifact,
      reachComparison: {
        ...artifact.reachComparison,
        stages: artifact.reachComparison.stages.map((stage, index) => (
          index === 1 ? reachStage(stage.stage, 5) : stage
        )),
      },
    })).toBe(false);
  });

  it("accepts only honest match-only accruing, complete, and unavailable lifecycles", () => {
    const zero = { n: 0, logloss: null, brier: null };
    const zeroPaired = {
      n: 0,
      direction: TENNIS_ABSTRACT_DELTA_DIRECTION,
      loglossDelta: null,
      seLogloss: null,
      brierDelta: null,
      seBrier: null,
    };
    const accruing = {
      ...artifact,
      matchComparison: {
        ...artifact.matchComparison,
        graded: 0,
        pending: 60,
        deuce: zero,
        tennisAbstract: zero,
        paired: zeroPaired,
      },
      reachComparison: undefined,
    };
    expect(isTennisAbstractBenchmark(accruing)).toBe(true);
    expect(isTennisAbstractBenchmark({ ...accruing, status: "complete" })).toBe(false);

    const complete = {
      ...artifact,
      status: "complete",
      matchComparison: {
        ...artifact.matchComparison,
        eligible: 2,
        graded: 2,
        pending: 0,
        excluded: 62,
      },
      reachComparison: undefined,
    };
    expect(isTennisAbstractBenchmark(complete)).toBe(true);

    const unavailable = {
      ...accruing,
      status: "unavailable",
      matchComparison: {
        ...accruing.matchComparison,
        eligible: 0,
        pending: 0,
        excluded: 64,
      },
    };
    expect(isTennisAbstractBenchmark(unavailable)).toBe(true);
    expect(isTennisAbstractBenchmark({ ...unavailable, status: "complete" })).toBe(false);
  });

  it("accepts scored reach aggregates with no naive SE, including multiclass Brier", () => {
    expect(isScoredReachAggregate({
      deuce: { n: 1, logloss: 2.3, brier: 1.2 },
      tennisAbstract: { n: 1, logloss: 2.1, brier: 1.1 },
      paired: {
        n: 1,
        direction: TENNIS_ABSTRACT_DELTA_DIRECTION,
        loglossDelta: -0.2,
        seLogloss: null,
        brierDelta: -0.1,
        seBrier: null,
      },
    })).toBe(true);
    expect(isTennisAbstractBenchmark({
      ...artifact,
      reachComparison: { ...artifact.reachComparison, champion: { status: "pending" } },
    })).toBe(true);
    expect(isScoredReachAggregate({ status: "pending" })).toBe(false);
  });

  it("renders coverage before scores with attribution, direction, and limitations", () => {
    expect(isTennisAbstractBenchmark(artifact)).toBe(true);
    if (!isTennisAbstractBenchmark(artifact)) throw new Error("invalid benchmark fixture");
    const html = renderToStaticMarkup(createElement(TennisAbstractSection, { data: artifact }));

    expect(html.indexOf("Paired match coverage")).toBeLessThan(html.indexOf("Match forecasts"));
    expect(html).toContain("match. Log-loss");
    expect(html).toContain("Tennis Abstract − DEUCE");
    expect(html).toContain("positive value means DEUCE did better");
    expect(html).toContain("Round of 64");
    expect(html).toContain("4/128");
    expect(html).toContain('href="https://www.tennisabstract.com/current/2026USOpenMenForecast.html"');
    expect(html).toContain('target="_blank" rel="noopener noreferrer"');
    expect(html).toContain("one tournament and a descriptive comparison");
    expect(html).toContain('role="region" aria-label="Full-field reach forecast scores" tabindex="0"');
  });

  it("renders an honest accruing state before any eligible match is graded", () => {
    const zero = { n: 0, logloss: null, brier: null };
    const accruing = {
      ...artifact,
      matchComparison: {
        ...artifact.matchComparison,
        graded: 0,
        pending: 60,
        deuce: zero,
        tennisAbstract: zero,
        paired: {
          n: 0,
          direction: TENNIS_ABSTRACT_DELTA_DIRECTION,
          loglossDelta: null,
          seLogloss: null,
          brierDelta: null,
          seBrier: null,
        },
      },
      reachComparison: undefined,
    };
    expect(isTennisAbstractBenchmark(accruing)).toBe(true);
    if (!isTennisAbstractBenchmark(accruing)) throw new Error("invalid accruing fixture");
    const html = renderToStaticMarkup(createElement(TennisAbstractSection, { data: accruing }));

    expect(html).toContain("This comparison is accruing");
    expect(html).toContain('data-tennis-abstract-benchmark="accruing"');
    expect(html).not.toContain(">Match forecasts</th>");
  });

  it("renders the benchmark fallback only after ordinary Track data is unavailable", () => {
    expect(isTennisAbstractBenchmark(artifact)).toBe(true);
    if (!isTennisAbstractBenchmark(artifact)) throw new Error("invalid benchmark fixture");
    const fallback = renderToStaticMarkup(createElement(TennisAbstractFallback, {
      benchmark: artifact,
      ordinaryTrackReady: false,
      trackLoading: false,
    }));
    expect(fallback).toContain("US Open: DEUCE vs Tennis Abstract");
    expect(renderToStaticMarkup(createElement(TennisAbstractFallback, {
      benchmark: artifact,
      ordinaryTrackReady: true,
      trackLoading: false,
    }))).toBe("");
    expect(renderToStaticMarkup(createElement(TennisAbstractFallback, {
      benchmark: artifact,
      ordinaryTrackReady: false,
      trackLoading: true,
    }))).toBe("");
  });
});

describe("benchmark score formatting", () => {
  it("prints finite metrics and signed external-minus-DEUCE deltas", () => {
    expect(formatBenchmarkMetric(0.61234)).toBe("0.6123");
    expect(formatBenchmarkMetric(null)).toBe("—");
    expect(formatBenchmarkMetric(Number.NaN)).toBe("—");
    expect(formatBenchmarkDelta(0.01234)).toBe("+0.0123");
    expect(formatBenchmarkDelta(-0.01234)).toBe("−0.0123");
    expect(formatBenchmarkDelta(0.000001)).toBe("0.0000");
  });

  it("keeps the verdict consistent with the displayed delta convention", () => {
    expect(externalMinusDeuce(0.62, 0.60)).toBeCloseTo(0.02);
    expect(deltaVerdict(0.02)).toBe("deuce");
    expect(deltaVerdict(-0.02)).toBe("tennis-abstract");
    expect(deltaVerdict(0.000001)).toBe("even");
    expect(deltaVerdict(null)).toBe("unavailable");
  });
});

describe("benchmark attribution and labels", () => {
  it("allows only credential-free web source links and has a named fallback", () => {
    expect(safeBenchmarkSourceUrl("https://example.com/forecast"))
      .toBe("https://example.com/forecast");
    expect(safeBenchmarkSourceUrl("javascript:alert(1)")).toBeNull();
    expect(safeBenchmarkSourceUrl("https://user:secret@example.com/forecast")).toBeNull();
    expect(safeBenchmarkSourceUrl("/forecast")).toBeNull();
    expect(benchmarkSourceLabel("  Forecast Lab  ")).toBe("Forecast Lab");
    expect(benchmarkSourceLabel(" ")).toBe("Tennis Abstract");
  });

  it("formats capture timing, stages, and machine exclusion keys for readers", () => {
    expect(formatBenchmarkTimestamp("2026-08-31T00:55:00Z"))
      .toBe("Aug 31, 2026 · 00:55 UTC");
    expect(formatBenchmarkTimestamp("not-a-date")).toBe("—");
    expect(benchmarkStageLabel("R16")).toBe("Round of 16");
    expect(benchmarkStageLabel("Champion")).toBe("Champion");
    expect(formatExclusionReason("started_before_capture")).toBe("Started before capture");
  });
});
