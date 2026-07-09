import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { drawCaveat, heat, pct, percentileScaler, scoreDist, SURFACE_BLEND } from "@/lib/ui";

const sum = (xs: number[]) => xs.reduce((a, b) => a + b, 0);

describe("SURFACE_BLEND", () => {
  // Shared fixture, also run by pytest against config.py ELO_PARAM_OVERRIDES
  // (tennis_model/tests/test_elo.py) — the cross-language tripwire that keeps this
  // hardcoded mirror of the tuned per-tour blend from drifting after a retune.
  it("mirrors the model's tuned per-tour surface_blend (shared fixture)", () => {
    const pinned = JSON.parse(
      readFileSync(new URL("../../tennis_model/tests/fixtures/model_constants.json", import.meta.url), "utf-8"),
    ).surface_blend;
    expect(SURFACE_BLEND).toEqual(pinned);
  });
});

describe("drawCaveat", () => {
  it("flags a seeded (unreleased) or partial live draw, but not a real one", () => {
    expect(drawCaveat({ status: "live", drawStatus: "real" })).toBeNull();
    expect(drawCaveat({ status: "upcoming", drawStatus: "real" })).toBeNull();
    expect(drawCaveat({ status: "live", drawStatus: "seeded" })?.label).toBe("Projected draw");
    expect(drawCaveat({ status: "live", drawStatus: "partial" })?.label).toBe("Draw incomplete");
  });

  it("never caveats a completed event or legacy JSON without drawStatus", () => {
    expect(drawCaveat({ status: "completed", drawStatus: "final" })).toBeNull();
    expect(drawCaveat({ status: "completed", drawStatus: "seeded" })).toBeNull(); // completed wins
    expect(drawCaveat({ status: "live" })).toBeNull(); // stale JSON -> unchanged UI
  });
});

describe("scoreDist", () => {
  it.each([
    [0.7, 3],
    [0.65, 5],
  ])("distribution for pMatch=%d bestOf=%d is consistent", (p, bestOf) => {
    const dist = scoreDist(p, bestOf);
    expect(dist).toHaveLength(bestOf + 1); // need + need outcomes
    expect(sum(dist.map((d) => d.p))).toBeCloseTo(1, 6);
    // A-labelled outcomes must recombine to the match win probability
    expect(sum(dist.filter((d) => d.a).map((d) => d.p))).toBeCloseTo(p, 5);
  });

  it("labels bo3 outcomes with 2-x set scores, sorted by probability", () => {
    const dist = scoreDist(0.7, 3);
    expect(new Set(dist.map((d) => d.label))).toEqual(new Set(["2-0", "2-1", "0-2", "1-2"]));
    for (let i = 1; i < dist.length; i++) expect(dist[i - 1].p).toBeGreaterThanOrEqual(dist[i].p);
  });
});

describe("pct", () => {
  it("renders NaN as an em dash", () => {
    expect(pct(NaN)).toBe("—");
  });

  it("formats probabilities as percentages", () => {
    expect(pct(0.123, 1)).toBe("12.3%");
    expect(pct(1)).toBe("100%");
  });
});

describe("heat", () => {
  it("returns the exact ramp endpoints as 6-digit hex", () => {
    expect(heat(0)).toBe("#1b1d24");
    expect(heat(1)).toBe("#c7cdff");
  });

  it("returns a valid hex color across the range", () => {
    for (const p of [0, 0.2, 0.35, 0.5, 0.6, 0.85, 1]) {
      expect(heat(p)).toMatch(/^#[0-9a-f]{6}$/);
    }
  });
});

describe("percentileScaler", () => {
  it("gives ties the mid-rank: (#below + 0.5·#equal) / n", () => {
    const scale = percentileScaler([1, 2, 2, 3]);
    expect(scale(2)).toBeCloseTo((1 + 0.5 * 2) / 4, 10); // 0.5
    expect(scale(1)).toBeCloseTo(0.5 / 4, 10);
    expect(scale(3)).toBeCloseTo(3.5 / 4, 10);
    expect(scale(0)).toBe(0); // below everything
    expect(scale(4)).toBe(1); // above everything
  });

  it("returns 0 for an empty population", () => {
    expect(percentileScaler([])(5)).toBe(0);
  });
});
