import { describe, it, expect } from "vitest";
import {
  type BracketEvent,
  drawSourceLabel,
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
  type TournamentLite,
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
    champion: null, runnerUp: null,
    drawSource: "wikipedia", drawSourceId: "test",
    drawSourceUrl: "https://en.wikipedia.org/wiki/Test", rounds, ...extra,
  };
}

describe("slot labels", () => {
  it("labels first-party and fallback draw provenance explicitly", () => {
    expect(drawSourceLabel("atp")).toBe("ATP official draw");
    expect(drawSourceLabel("wta")).toBe("WTA official draw");
    expect(drawSourceLabel("wikipedia")).toBe("Wikipedia fallback draw");
  });

  it("classifies real / placeholder / bye / tbd", () => {
    expect(isRealSlot("Jannik Sinner")).toBe(true);
    expect(isRealSlot(null)).toBe(false);
    for (const placeholder of [
      "Qualifier 7", "Lucky Loser 2", "Wildcard 3", "Alternate 1", "Unresolved 4",
      "Qualifier/Wildcard 3", "Qualifier/Alternate 1", "Qualifier/Unresolved 4",
      "Q/LL", "Qualifier (8)", "TBD opponent", "TBA - player", "Bye",
    ]) {
      expect(isPlaceholder(placeholder)).toBe(true);
      expect(isRealSlot(placeholder)).toBe(false);
    }
    expect(isPlaceholder("Jannik Sinner")).toBe(false);
    expect(isPlaceholder("Qualifier Smith")).toBe(false);
    expect(isRealSlot("Qualifier Smith")).toBe(true);
  });

  it("sideLabel preserves unresolved roles and uses null geometry by round", () => {
    expect(sideLabel(null, 0)).toBe("Bye");
    expect(sideLabel(null, 3)).toBe("TBD");
    expect(sideLabel("Qualifier 12", 0)).toBe("Qualifier");
    expect(sideLabel("Lucky Loser 2", 0)).toBe("Lucky Loser");
    expect(sideLabel("Qualifier/Wildcard 1", 0)).toBe("Wildcard");
    expect(sideLabel("Qualifier/Alternate 4", 0)).toBe("Alternate");
    expect(sideLabel("Qualifier/Unresolved 3", 0)).toBe("Unresolved");
    expect(sideLabel("Carlos Alcaraz", 2)).toBe("Carlos Alcaraz");
  });

  it("keeps serialized roles safe under the pre-Round-3 browser policy", () => {
    const legacyPlaceholder = (name: string) => /^(qualifier|lucky loser)\b/i.test(name.trim());
    const serialized = [
      ["Qualifier 3", "Qualifier"],
      ["Lucky Loser 3", "Lucky Loser"],
      ["Qualifier/Wildcard 3", "Wildcard"],
      ["Qualifier/Alternate 3", "Alternate"],
      ["Qualifier/Unresolved 3", "Unresolved"],
    ] as const;

    for (const [slot, label] of serialized) {
      expect(legacyPlaceholder(slot)).toBe(true);
      expect(isRealSlot(slot)).toBe(false);
      expect(sideLabel(slot, 0)).toBe(label);
    }
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

  it("prefers stable provider identity for shareable event URLs", () => {
    const identified = [mkEvent(32, "Sponsor Title", { espnId: "401234" })];
    expect(resolveEventIndex(identified, "401234")).toBe(0);
  });

  it("joins reach odds + title contenders from tournaments.json by name", () => {
    const tournaments: TournamentLite[] = [{
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
