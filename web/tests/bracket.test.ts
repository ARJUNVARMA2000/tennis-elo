import { describe, it, expect } from "vitest";
import {
  type BracketEvent,
  finalsColumns,
  isPlaceholder,
  isRealSlot,
  reachFor,
  resolveEventIndex,
  sectionColumns,
  sectionCount,
  sectionLabels,
  sectionMatchRange,
  sectionRoundCount,
  sideLabel,
  titleContenders,
} from "@/lib/bracket";

const RLABEL = { 128: "R128", 64: "R64", 32: "R32", 16: "R16", 8: "QF", 4: "SF", 2: "F" } as Record<number, string>;

/** Synthesize a structurally valid event of a given power-of-two size (all pending). */
function mkEvent(size: number, name = "Test", extra: Partial<BracketEvent> = {}): BracketEvent {
  const rounds = [];
  for (let players = size; players >= 2; players /= 2) {
    rounds.push({
      round: RLABEL[players],
      matches: Array.from({ length: players / 2 }, () => ({
        a: null, b: null, seedA: null, seedB: null,
        p: null, probSource: null, winner: null, score: null, upset: null,
      })),
    });
  }
  return {
    name, surface: "Hard", level: "Grand Slam", bestOf: 5, start: "2026-06-29",
    end: "2026-07-12", status: "live", drawSize: size, bracketSize: size,
    champion: null, runnerUp: null, wikiUrl: null, rounds, ...extra,
  };
}

describe("slot labels", () => {
  it("classifies real / placeholder / bye / tbd", () => {
    expect(isRealSlot("Jannik Sinner")).toBe(true);
    expect(isRealSlot(null)).toBe(false);
    expect(isPlaceholder("Qualifier 7")).toBe(true);
    expect(isPlaceholder("Lucky Loser")).toBe(true);
    expect(isPlaceholder("Jannik Sinner")).toBe(false);
  });

  it("sideLabel: bye only in round 0, TBD later, Qualifier collapses the number", () => {
    expect(sideLabel(null, 0)).toBe("Bye");
    expect(sideLabel(null, 3)).toBe("TBD");
    expect(sideLabel("Qualifier 12", 0)).toBe("Qualifier");
    expect(sideLabel("Carlos Alcaraz", 2)).toBe("Carlos Alcaraz");
  });
});

describe("section layout", () => {
  it("counts sections by 16-slot blocks", () => {
    expect(sectionCount(128)).toBe(8);
    expect(sectionCount(32)).toBe(2);
    expect(sectionCount(16)).toBe(1);
    expect(sectionCount(8)).toBe(1); // small draw -> whole
  });

  it("labels sections 1..n", () => {
    expect(sectionLabels(32)).toEqual(["Section 1", "Section 2"]);
    expect(sectionLabels(16)).toEqual(["Section 1"]);
  });

  it("section round count caps at 4 for big draws, all rounds for small", () => {
    expect(sectionRoundCount(128, 7)).toBe(4); // R128..R16 in a section
    expect(sectionRoundCount(16, 4)).toBe(4);  // whole draw
    expect(sectionRoundCount(8, 3)).toBe(3);
  });

  it("match ranges halve each round and tile the draw", () => {
    expect(sectionMatchRange(0, 0)).toEqual({ start: 0, count: 8 });
    expect(sectionMatchRange(1, 0)).toEqual({ start: 8, count: 8 });
    expect(sectionMatchRange(0, 1)).toEqual({ start: 0, count: 4 });
    expect(sectionMatchRange(1, 3)).toEqual({ start: 1, count: 1 });
  });

  it("128-draw: 8 sections of 4 columns + a 3-round finals tree, covering every match once", () => {
    const ev = mkEvent(128);
    const secCols = sectionColumns(ev, 0);
    expect(secCols.map((c) => c.round)).toEqual(["R128", "R64", "R32", "R16"]);
    expect(secCols[0].matches.length).toBe(8);
    const finals = finalsColumns(ev);
    expect(finals.map((c) => c.round)).toEqual(["QF", "SF", "F"]);

    // union of all section matches at round 0 == every first-round match, once
    const seen = new Set<number>();
    for (let s = 0; s < sectionCount(128); s++)
      for (const { idx } of sectionColumns(ev, s)[0].matches) {
        expect(seen.has(idx)).toBe(false);
        seen.add(idx);
      }
    expect(seen.size).toBe(64);
  });

  it("small draw renders whole, no finals split", () => {
    const ev = mkEvent(16);
    expect(sectionColumns(ev, 0).map((c) => c.round)).toEqual(["R16", "QF", "SF", "F"]);
    expect(finalsColumns(ev)).toEqual([]);
  });
});

describe("event + reach resolution", () => {
  const events = [mkEvent(128, "Wimbledon"), mkEvent(32, "Newport")];

  it("resolves ?e= by name, falls back to first on miss/absent", () => {
    expect(resolveEventIndex(events, "Newport")).toBe(1);
    expect(resolveEventIndex(events, "newport")).toBe(1); // case-insensitive
    expect(resolveEventIndex(events, "Nonexistent")).toBe(0);
    expect(resolveEventIndex(events, null)).toBe(0);
  });

  it("joins reach odds + title contenders from tournaments.json by name", () => {
    const tournaments = [{
      name: "Wimbledon",
      projection: [
        { name: "Sinner", reach: { SF: 0.7, F: 0.55, Champion: 0.4 } },
        { name: "Alcaraz", reach: { SF: 0.6, F: 0.45, Champion: 0.35 } },
        { name: "Zverev", reach: { Champion: 0.1 } },
      ],
    }];
    expect(reachFor(tournaments, "Wimbledon").Sinner.Champion).toBe(0.4);
    expect(reachFor(tournaments, "Missing")).toEqual({});
    const top = titleContenders(tournaments, "Wimbledon", 2);
    expect(top.map((t) => t.name)).toEqual(["Sinner", "Alcaraz"]);
    expect(top[0].p).toBe(0.4);
  });
});
