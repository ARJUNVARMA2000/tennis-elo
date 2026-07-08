import { describe, it, expect } from "vitest";
import { groupByEvent, type Upcoming } from "@/lib/upcoming";

const mk = (event: string, round: string, a: string, b: string, pA: number, surface = "Hard"): Upcoming => ({
  event,
  date: "2026-07-10",
  round,
  surface,
  bestOf: 3,
  playerA: a,
  playerB: b,
  pA,
});

describe("groupByEvent", () => {
  it("groups matches under their tournament, preserving order", () => {
    const rows = [
      mk("Wimbledon", "SF", "Alcaraz", "Djokovic", 0.7, "Grass"),
      mk("Wimbledon", "SF", "Sinner", "Zverev", 0.6, "Grass"),
      mk("Bastad", "F", "Ruud", "Borges", 0.65, "Clay"),
    ];
    const groups = groupByEvent(rows);
    expect(groups.map((g) => g.event)).toEqual(["Wimbledon", "Bastad"]);
    expect(groups[0].matches).toHaveLength(2);
    expect(groups[0].surface).toBe("Grass");
    expect(groups[1].matches[0].playerA).toBe("Ruud");
  });

  it("re-groups interleaved events without losing matches", () => {
    const rows = [
      mk("A", "R32", "p1", "p2", 0.5),
      mk("B", "R32", "p3", "p4", 0.5),
      mk("A", "R32", "p5", "p6", 0.5),
    ];
    const groups = groupByEvent(rows);
    expect(groups.map((g) => g.event)).toEqual(["A", "B"]);
    expect(groups[0].matches).toHaveLength(2);
    expect(groups.flatMap((g) => g.matches)).toHaveLength(3);
  });

  it("returns [] for no rows", () => {
    expect(groupByEvent([])).toEqual([]);
  });
});
