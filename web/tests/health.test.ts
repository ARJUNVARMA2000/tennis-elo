import { describe, expect, it } from "vitest";
import {
  type CheckRow, type HealthReport,
  checkTone, checkStatusLabel, driftTone, driftLabel, overall, fmtValue, fmtLimit,
} from "@/lib/health";

const row = (over: Partial<CheckRow> = {}): CheckRow => ({
  key: "fresh", label: "Results overlay (fresh)", value: 3, limit: 14, unit: "d",
  date: null, ok: true, note: null, problem: null, ...over,
});

const report = (over: Partial<HealthReport> = {}): HealthReport => ({
  generated: "2026-07-10",
  generatedAt: "2026-07-10T18:00:00Z",
  ok: true,
  tours: {
    atp: {
      matches: 283000, date_max: "2026-07-10",
      checks: [row()], problems: [],
      output: { matches: 283000, forecast_lines: 120, forecast_max_as_of: "2026-07-10", problems: [] },
    },
  },
  ...over,
});

describe("checkTone / checkStatusLabel", () => {
  it("clean pass is green 'ok'", () => {
    expect(checkTone(row())).toBe("ok");
    expect(checkStatusLabel(row())).toBe("ok");
  });

  it("passing with a note (shadowed source) is amber 'covered'", () => {
    const r = row({ note: "frozen upstream, but shadowed" });
    expect(checkTone(r)).toBe("warn");
    expect(checkStatusLabel(r)).toBe("covered");
  });

  it("failing is red 'fail' even with a note", () => {
    const r = row({ ok: false, problem: "atp: stale", note: "x" });
    expect(checkTone(r)).toBe("fail");
    expect(checkStatusLabel(r)).toBe("fail");
  });
});

describe("driftTone / driftLabel", () => {
  it("maps the three sentinel statuses", () => {
    expect(driftTone("ok")).toBe("ok");
    expect(driftTone("drift")).toBe("warn");
    expect(driftTone("insufficient")).toBe("muted");
    expect(driftTone(undefined)).toBe("muted");
  });

  it("labels carry the sample size", () => {
    expect(driftLabel({ status: "ok", n: 181, d: 0.007, t: 0.27 })).toBe("calibrated (n=181)");
    expect(driftLabel({ status: "insufficient", n: 114, d: null, t: null })).toBe("arming (n=114)");
    expect(driftLabel({ status: "drift", n: 400, d: 0.06, t: 3.2 })).toBe("drift — re-tune advised");
    expect(driftLabel(undefined)).toBe("no data");
  });
});

describe("overall", () => {
  it("all clean -> ok with zero counts", () => {
    expect(overall(report())).toEqual({ tone: "ok", problems: 0, noted: 0 });
  });

  it("a noted (shadowed) row degrades to warn without problems", () => {
    const r = report();
    r.tours.atp.checks = [row({ note: "shadowed" })];
    expect(overall(r)).toEqual({ tone: "warn", problems: 0, noted: 1 });
  });

  it("sentinel problems win over notes and count across source + output", () => {
    const r = report({ ok: false });
    r.tours.atp.checks = [row({ ok: false, problem: "atp: stale", note: "x" })];
    r.tours.atp.problems = ["atp: stale"];
    r.tours.atp.output.problems = ["atp: meta.json missing"];
    expect(overall(r)).toEqual({ tone: "fail", problems: 2, noted: 0 });
  });
});

describe("fmtValue / fmtLimit", () => {
  it("ages render with the day unit and a max limit", () => {
    expect(fmtValue(row({ value: 19 }))).toBe("19d");
    expect(fmtLimit(row())).toBe("≤ 14d");
  });

  it("coverage fractions render as percentages with a min limit", () => {
    expect(fmtValue(row({ value: 0.9717, unit: "frac" }))).toBe("97%");
    expect(fmtLimit(row({ limit: 0.6, unit: "frac" }))).toBe("≥ 60%");
  });

  it("missing values are an em dash", () => {
    expect(fmtValue(row({ value: null }))).toBe("—");
  });
});
