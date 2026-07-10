import { describe, expect, it } from "vitest";
import { niceTicks } from "@/components/ScatterChart";

describe("niceTicks", () => {
  it("produces round fractional ticks for a serve-pct-sized span", () => {
    const t = niceTicks(0.55, 0.75);
    expect(t.length).toBeGreaterThanOrEqual(3);
    expect(t[0]).toBeGreaterThanOrEqual(0.55);
    expect(t[t.length - 1]).toBeLessThanOrEqual(0.75 + 1e-9);
    // steps are uniform and round (0.05 for this span)
    const steps = t.slice(1).map((v, i) => Number((v - t[i]).toFixed(10)));
    expect(new Set(steps).size).toBe(1);
    expect(steps[0]).toBeCloseTo(0.05, 10);
  });

  it("produces round integer ticks for an Elo-sized span", () => {
    const t = niceTicks(1712, 2135);
    expect(t.every((v) => v % 100 === 0)).toBe(true);
    expect(t[0]).toBeGreaterThanOrEqual(1712);
    expect(t[t.length - 1]).toBeLessThanOrEqual(2135);
  });

  it("survives a degenerate min==max domain", () => {
    const t = niceTicks(0.6, 0.6);
    expect(Array.isArray(t)).toBe(true);
    expect(t.every((v) => Number.isFinite(v))).toBe(true);
  });
});
