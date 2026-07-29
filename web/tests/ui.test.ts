import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { drawCaveat, heat, heroEvent, pct, percentileScaler, scoreDist, SLAM_HERO_LINGER_MS, SURFACE_BLEND, tournamentView } from "@/lib/ui";

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
    expect(drawCaveat({ status: "live", drawStatus: "unavailable" })?.label)
      .toBe("Event confirmed · draw pending");
  });

  it("never caveats a completed event or legacy JSON without drawStatus", () => {
    expect(drawCaveat({ status: "completed", drawStatus: "final" })).toBeNull();
    expect(drawCaveat({ status: "completed", drawStatus: "seeded" })).toBeNull(); // completed wins
    expect(drawCaveat({ status: "live" })).toBeNull(); // stale JSON -> unchanged UI
  });
});

describe("heroEvent", () => {
  const slam = (status: string, end: string, name = "Wimbledon") =>
    ({ level: "Grand Slam", name, status, end });
  const NOW = new Date("2026-07-12T12:00").getTime(); // day after a 2026-07-11 final

  it("picks a live or upcoming Grand Slam over lesser events", () => {
    const grid = [
      { level: "WTA 125", name: "Grand Est Open 88", status: "live", end: "2026-07-11" },
      slam("live", "2026-07-13"),
    ];
    expect(heroEvent(grid, NOW)?.name).toBe("Wimbledon");
  });

  it("keeps a just-finished Slam within the ~48h linger, then drops it", () => {
    expect(heroEvent([slam("completed", "2026-07-11")], NOW)).toBeDefined();        // ~1 day out
    const stale = new Date("2026-07-14T12:00").getTime();                           // ~3 days out
    expect(heroEvent([slam("completed", "2026-07-11")], stale)).toBeUndefined();
  });

  it("honours the exact linger boundary", () => {
    const end = new Date("2026-07-11T00:00").getTime();
    expect(heroEvent([slam("completed", "2026-07-11")], end + SLAM_HERO_LINGER_MS)).toBeDefined();
    expect(heroEvent([slam("completed", "2026-07-11")], end + SLAM_HERO_LINGER_MS + 1)).toBeUndefined();
  });

  // Regression: promoting the DC Open to the single-event hero reused the Slam layout and
  // hid its concurrent ATP 250 behind "show other recent events". A 500-and-below week is a
  // multi-event board; the cards themselves remain ordered by prestige.
  it("keeps a live 500 and concurrent 250 in the prestige-ordered multi-event layout", () => {
    const grid = [
      { level: "ATP 250", name: "Generali Open", status: "live", end: "2026-07-26" },
      { level: "ATP 500", name: "Mubadala DC Open", status: "live", end: "2026-08-03" },
    ];
    const view = tournamentView(grid, NOW);
    expect(view.hero).toBeUndefined();
    expect(view.grid.map((t) => t.name)).toEqual(["Mubadala DC Open", "Generali Open"]);
    expect(view.other).toEqual([]);
  });

  it("gives a 1000 the hero and keeps every lesser event in the prestige-ordered disclosure", () => {
    const grid = [
      { level: "ATP 250", name: "Two Fifty", status: "live", end: "2026-08-03" },
      { level: "ATP 500", name: "Five Hundred", status: "live", end: "2026-08-03" },
      { level: "Masters 1000", name: "A Thousand", status: "live", end: "2026-08-03" },
    ];
    const view = tournamentView(grid, NOW);
    expect(view.hero?.name).toBe("A Thousand");
    expect(view.grid).toEqual([]);
    expect(view.other.map((t) => t.name)).toEqual(["Five Hundred", "Two Fifty"]);
  });

  it("prefers a live hero over a completed event of equal tier", () => {
    const sameTier = [
      { level: "Masters 1000", name: "Done Open", status: "completed", end: "2026-07-11" },
      { level: "Masters 1000", name: "Live Open", status: "live", end: "2026-08-03" },
    ];
    expect(heroEvent(sameTier, NOW)?.name).toBe("Live Open");
  });

  it("does not drop completed events from a focused week's disclosure", () => {
    const view = tournamentView([
      { level: "Masters 1000", name: "A Thousand", status: "live", end: "2026-08-03" },
      { level: "ATP 500", name: "Done Five Hundred", status: "completed", end: "2026-07-20" },
    ], NOW);
    expect(view.other.map((t) => t.name)).toEqual(["Done Five Hundred"]);
  });

  it("preserves every coverage key across hero, grid, and other", () => {
    const payload = [
      { coverageKey: "espn:1000", level: "Masters 1000", name: "A Thousand", status: "live", end: "2026-08-03" },
      { coverageKey: "espn:500", level: "ATP 500", name: "Five Hundred", status: "live", end: "2026-08-03" },
      { coverageKey: "espn:250", level: "ATP 250", name: "Two Fifty", status: "live", end: "2026-08-03" },
    ];
    const view = tournamentView(payload, NOW);
    const rendered = [view.hero, ...view.grid, ...view.other]
      .filter((event): event is (typeof payload)[number] => Boolean(event))
      .map((event) => event.coverageKey)
      .sort();
    expect(rendered).toEqual(payload.map((event) => event.coverageKey).sort());
  });

  it("hands the page back to the grid for tiers below 1000, and for a finished non-Slam", () => {
    expect(heroEvent([{ level: "ATP 500", name: "Medium", status: "live", end: "2026-08-03" }],
                     NOW)).toBeUndefined();
    expect(heroEvent([{ level: "ATP 250", name: "Small", status: "live", end: "2026-08-03" }],
                     NOW)).toBeUndefined();
    expect(heroEvent([{ level: "WTA 125", name: "Tiny", status: "live", end: "2026-08-03" }],
                     NOW)).toBeUndefined();
    // a wrapped-up 500 does not sit stale at the top the way a just-crowned Slam does
    expect(heroEvent([{ level: "WTA 500", name: "Bad Homburg", status: "completed",
                        end: "2026-07-11" }], NOW)).toBeUndefined();
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
