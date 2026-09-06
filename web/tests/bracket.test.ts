import { describe, it, expect } from "vitest";
import {
  type BracketEvent,
  currentRoundIndex,
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
  visibleBracketSize,
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

describe("tournament progress", () => {
  function finishThrough(ev: BracketEvent, count: number) {
    ev.rounds.slice(0, count).forEach((round) => round.matches.forEach((match, i) => {
      match.a = `Player ${i}`;
      match.winner = "a";
    }));
  }

  it("starts an unplayed draw at the opening round, including unresolved entrants", () => {
    const ev = mkEvent(128, "Open", { status: "upcoming" });
    ev.rounds[0].matches[0].a = "Qualifier 1";
    expect(currentRoundIndex(ev.rounds)).toBe(0);
    expect(currentRoundIndex([])).toBe(0);
  });

  it("shows all eight R16 matches together after the first three rounds finish", () => {
    const ev = mkEvent(128);
    finishThrough(ev, 3);
    const start = currentRoundIndex(ev.rounds);
    expect(start).toBe(3);
    expect(sectionCount(visibleBracketSize(ev, start))).toBe(1);
    const cols = sectionColumns(ev, 7, start); // stale selection clamps to the whole draw
    expect(cols.map((col) => col.round)).toEqual(["R16", "QF", "SF", "F"]);
    expect(cols.map((col) => col.matches.length)).toEqual([8, 4, 2, 1]);
    expect(cols[0].roundIndex).toBe(3);
    expect(cols[0].matches[7]).toEqual({ m: ev.rounds[3].matches[7], idx: 7 });
    expect(finalsColumns(ev, start)).toEqual([]);
    expect(sectionColumns(ev, 0)[0].round).toBe("R128"); // full history remains available
  });

  it("waits for the entire round, even if a different section has completed the next round", () => {
    const ev = mkEvent(128);
    finishThrough(ev, 4);
    ev.rounds[2].matches[15].winner = null;
    expect(currentRoundIndex(ev.rounds)).toBe(2);
    expect(sectionColumns(ev, 1, 2)[0].matches.at(-1)?.idx).toBe(15);
  });

  it("accepts confirmed byes and walkovers without requiring a score", () => {
    const ev = mkEvent(32);
    finishThrough(ev, 1);
    expect(ev.rounds[0].matches.every((match) => !match.score)).toBe(true);
    expect(currentRoundIndex(ev.rounds)).toBe(1);
    ev.rounds[0].matches[0].winner = null; // a missing result is not an inferred bye
    ev.rounds[0].matches[0].b = "Qualifier/Unresolved 1";
    expect(currentRoundIndex(ev.rounds)).toBe(0);
  });

  it.each([2, 4, 8, 16, 32, 64, 128])("preserves every match at every progression stage of a %i-slot draw", (size) => {
    const ev = mkEvent(size);
    for (let start = 0; start < ev.rounds.length; start++) {
      finishThrough(ev, start);
      expect(currentRoundIndex(ev.rounds)).toBe(start);
      const columns = finalsColumns(ev, start);
      for (let section = 0; section < sectionCount(visibleBracketSize(ev, start)); section++) {
        columns.push(...sectionColumns(ev, section, start));
      }
      const actual = columns.flatMap((col) => col.matches.map(({ m, idx }) => {
        expect(m).toBe(ev.rounds[col.roundIndex].matches[idx]);
        return `${col.roundIndex}:${idx}`;
      })).sort();
      const expected = ev.rounds.slice(start).flatMap((round, i) => round.matches.map((_, j) => `${start + i}:${j}`)).sort();
      expect(actual).toEqual(expected);
    }
    finishThrough(ev, ev.rounds.length);
    const final = currentRoundIndex(ev.rounds);
    expect(sectionColumns(ev, 0, final).map((col) => col.round)).toEqual(["F"]);
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

  it("joins reach odds + title contenders by stable event identity", () => {
    const tournaments: TournamentLite[] = [{
      name: "Sponsor-renamed Wimbledon", espnId: "188-2026",
      projection: [
        { name: "Sinner", reach: { SF: 0.7, F: 0.55, Champion: 0.4 } },
        { name: "Alcaraz", reach: { SF: 0.6, F: 0.45, Champion: 0.35 } },
        { name: "Zverev", reach: { Champion: 0.1 } },
      ],
    }];
    const event = { name: "Wimbledon", espnId: "188-2026" };
    expect(reachFor(tournaments, event).Sinner.Champion).toBe(0.4);
    expect(reachFor(tournaments, { name: "Wimbledon", espnId: "999-2026" })).toEqual({});
    const top = titleContenders(tournaments, event, 2);
    expect(top.map((t) => t.name)).toEqual(["Sinner", "Alcaraz"]);
    expect(top[0].p).toBe(0.4);
  });

  it("keeps a name fallback only for genuinely id-less legacy artifacts", () => {
    const tournaments: TournamentLite[] = [{
      name: "Wimbledon", projection: [{ name: "Sinner", reach: { Champion: 0.4 } }],
    }];
    expect(reachFor(tournaments, { name: "wimbledon" }).Sinner.Champion).toBe(0.4);
  });
});
