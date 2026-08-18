import { describe, expect, it } from "vitest";
import type { BracketRound } from "@/lib/bracket";
import { decodeScenario, encodeScenario, exactScenario, titleSwings } from "@/lib/scenario";

const rounds: BracketRound[] = [
  { round: "SF", matches: [
    { a: "A", b: "B", seedA: null, seedB: null, p: 0.6, probSource: "logged", winner: "a", score: "6-4 6-4", upset: false },
    { a: "C", b: "D", seedA: null, seedB: null, p: 0.7, probSource: "model", winner: null, score: null, upset: null },
  ] },
  { round: "F", matches: [
    { a: "A", b: null, seedA: null, seedB: null, p: null, probSource: null, winner: null, score: null, upset: null },
  ] },
];
const players = ["A", "B", "C", "D"];
const matrix = [
  [0.5, 0.6, 0.6, 0.6],
  [0.4, 0.5, 0.5, 0.5],
  [0.4, 0.5, 0.5, 0.7],
  [0.4, 0.5, 0.3, 0.5],
];

describe("exact bracket scenarios", () => {
  it("matches the server propagation and conditions confirmed results", () => {
    expect(exactScenario(rounds, players, matrix).champion).toEqual([
      { name: "A", p: 0.6 }, { name: "C", p: 0.28 }, { name: "D", p: 0.12 },
    ]);
  });

  it("forces an open match, preserves history, and reports title impact", () => {
    const base = exactScenario(rounds, players, matrix);
    const scenario = exactScenario(rounds, players, matrix, { "0:0": "B", "0:1": "D" });
    expect(scenario.champion).toEqual([{ name: "A", p: 0.6 }, { name: "D", p: 0.4 }]);
    expect(titleSwings(base, scenario).find((row) => row.name === "D"))
      .toMatchObject({ name: "D", delta: 0.28 });
  });

  it("uses stable event match IDs and ignores locks on projected future pairings", () => {
    const scenario = exactScenario(rounds, players, matrix, {
      "event-9:r0:m1": "D",
      "event-9:r1:m0": "D",
    }, "event-9");
    expect(scenario.nodes[0].matches[1]).toMatchObject({
      key: "event-9:r0:m1", roundIndex: 0, status: "forced", winner: "D",
    });
    // The source final has one TBD side, so a URL cannot manufacture a fixed winner.
    expect(scenario.nodes[1].matches[0].status).toBe("projected");
  });

  it("round-trips share state with punctuation safely", () => {
    const picks = { "event-9:r0:m1": "A. Player", "event-9:r2:m0": "Renée Test" };
    expect(decodeScenario(encodeScenario(picks))).toEqual(picks);
  });
});
