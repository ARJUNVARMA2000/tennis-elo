import { describe, it, expect } from "vitest";
import { byTournamentTier, groupByEvent, upcomingCard, type Upcoming } from "@/lib/upcoming";

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

describe("byTournamentTier", () => {
  const row = (event: string, level: string | undefined, a: string): Upcoming => ({
    event, date: "2026-07-09", round: "R64", surface: "Grass", bestOf: 3,
    playerA: a, playerB: "opp", pA: 0.6, level,
  });

  it("leads with the marquee event, so a live slam surfaces over same-week 125s", () => {
    // Mirrors the real upcoming.json order (soonest-first): the concurrent WTA 125s land before
    // the two Wimbledon SFs, which would otherwise be buried past the 6-card "Up next" cutoff.
    const rows = [
      row("Grand Est Open 88", "W125", "Selekhmeteva"),
      row("Nordea Open", "W125", "Badosa"),
      row("Cerity Partners Hall of Fame Open", "W125", "Rogers"),
      row("Wimbledon", "Q", "Gauff"),   // slam is pinned by name even with a mislabeled "Q" level
      row("Wimbledon", "Q", "Noskova"),
    ];
    const ordered = byTournamentTier(rows);
    expect(ordered.slice(0, 2).map((r) => r.event)).toEqual(["Wimbledon", "Wimbledon"]);
    expect(ordered.slice(0, 2).map((r) => r.playerA)).toEqual(["Gauff", "Noskova"]); // stable
  });

  it("orders by tier (1000 → 500 → 250) and stays soonest-first within a tier", () => {
    const rows = [
      row("Bastad", "ATP 250", "a"),
      row("Hamburg", "ATP 500", "b"),
      row("Canada", "ATP 1000", "c"),
      row("Hamburg", "ATP 500", "d"),   // a later 500 match — must stay after "b" (stable sort)
    ];
    const ordered = byTournamentTier(rows);
    expect(ordered.map((r) => r.event)).toEqual(["Canada", "Hamburg", "Hamburg", "Bastad"]);
    expect(ordered.map((r) => r.playerA)).toEqual(["c", "b", "d", "a"]);
  });

  it("does not mutate the input array", () => {
    const rows = [row("Bastad", "ATP 250", "a"), row("Wimbledon", "Q", "b")];
    const before = [...rows];
    byTournamentTier(rows);
    expect(rows).toEqual(before);
  });

  it("returns [] for no rows", () => {
    expect(byTournamentTier([])).toEqual([]);
  });
});

describe("upcomingCard", () => {
  it("puts player A on top (highlighted) when they are the favourite", () => {
    const c = upcomingCard(mk("Wimbledon", "SF", "Alcaraz", "Sinner", 0.75, "Grass"));
    expect(c.top).toEqual({ name: "Alcaraz", prob: 0.75, won: true });
    expect(c.bottom).toEqual({ name: "Sinner", prob: 0.25, won: false });
    expect(c.surface).toBe("Grass");
    expect(c.meta).toBe("SF · 2026-07-10");
  });

  it("puts player B on top when pA < 0.5 (B is the favourite)", () => {
    const c = upcomingCard(mk("Wimbledon", "SF", "Alcaraz", "Sinner", 0.25));
    expect(c.top).toEqual({ name: "Sinner", prob: 0.75, won: true });
    expect(c.bottom).toEqual({ name: "Alcaraz", prob: 0.25, won: false });
  });

  it("treats an exact 50/50 as player A favoured (deterministic tie-break)", () => {
    const c = upcomingCard(mk("X", "F", "P1", "P2", 0.5));
    expect(c.top.name).toBe("P1");
    expect(c.top.won).toBe(true);
  });

  it("the two sides always sum to 1 (real pA values included)", () => {
    for (const p of [0.02, 0.5, 0.6518, 0.99]) {
      const c = upcomingCard(mk("X", "R64", "A", "B", p));
      expect(c.top.prob + c.bottom.prob).toBeCloseTo(1, 12);
      expect(c.top.won).toBe(true);
      expect(c.bottom.won).toBe(false);
    }
  });

  it("prepends the tournament name to the meta only when showEvent is set", () => {
    const m = mk("Wimbledon", "SF", "Alcaraz", "Sinner", 0.75, "Grass");
    // /schedule board (grouped under an event header): no event in the meta.
    expect(upcomingCard(m).meta).toBe("SF · 2026-07-10");
    // home "Up next" (flat, cross-tournament grid): event · round · date.
    expect(upcomingCard(m, { showEvent: true }).meta).toBe("Wimbledon · SF · 2026-07-10");
  });
});
