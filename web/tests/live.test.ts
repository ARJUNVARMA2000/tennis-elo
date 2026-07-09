import { readFileSync } from "node:fs";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  fetchLiveMatches,
  matchContext,
  nameKey,
  winProb,
  type Matrix,
  type PlayerRow,
  type TournamentInfo,
} from "@/lib/live";

/* ------------------------------------------------------------------ */
/* nameKey                                                             */
/* ------------------------------------------------------------------ */

describe("nameKey", () => {
  // Shared fixture, also run by pytest against the Python reference
  // implementation (tennis_model/src/tennis_model/data/names.py) — a
  // cross-language parity tripwire: if either port drifts, one side fails.
  const cases: { name: string; key: string }[] = JSON.parse(
    readFileSync(new URL("../../tennis_model/tests/fixtures/name_key_cases.json", import.meta.url), "utf-8"),
  );

  it.each(cases)("nameKey($name) → $key", ({ name, key }) => {
    expect(nameKey(name)).toBe(key);
  });

  it("joins accented and plain spellings to the same key", () => {
    expect(nameKey("Félix Auger-Aliassime")).toBe(nameKey("Felix Auger Aliassime"));
  });
});

/* ------------------------------------------------------------------ */
/* matchContext                                                        */
/* ------------------------------------------------------------------ */

describe("matchContext", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  const madrid: TournamentInfo = {
    name: "Madrid Open",
    surface: "Clay",
    bestOf: 3,
    level: "1000",
    status: "live",
  };

  it("joins a sponsored ESPN event name to the live tournament by substring", () => {
    expect(matchContext("Mutua Madrid Open pres. by X", [madrid])).toEqual({
      surface: "Clay",
      bestOf: 3,
    });
  });

  it("falls back to best-of-3 when the tournament reports bestOf 0", () => {
    expect(matchContext("Mutua Madrid Open pres. by X", [{ ...madrid, bestOf: 0 }])).toEqual({
      surface: "Clay",
      bestOf: 3,
    });
  });

  it("skips non-live tournaments", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 9, 15)); // October → Hard fallback
    expect(matchContext("Mutua Madrid Open pres. by X", [{ ...madrid, status: "done" }])).toEqual({
      surface: "Hard",
      bestOf: 3,
    });
  });

  it("skips tournament names shorter than 5 characters", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 9, 15));
    // "Open" is a substring of the event but too short to be a safe join key
    expect(
      matchContext("Mutua Madrid Open pres. by X", [{ ...madrid, name: "Open" }]),
    ).toEqual({ surface: "Hard", bestOf: 3 });
  });

  it.each([
    [new Date(2026, 3, 10), "Clay"], // April
    [new Date(2026, 6, 10), "Grass"], // July
    [new Date(2026, 9, 10), "Hard"], // October
  ])("month fallback: %s → %s", (date, surface) => {
    vi.useFakeTimers();
    vi.setSystemTime(date);
    expect(matchContext("Some Unknown Cup", [])).toEqual({ surface, bestOf: 3 });
  });

  it("uses the month fallback when tournaments is null", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 3, 10));
    expect(matchContext("Some Unknown Cup", null)).toEqual({ surface: "Clay", bestOf: 3 });
  });
});

/* ------------------------------------------------------------------ */
/* winProb                                                             */
/* ------------------------------------------------------------------ */

describe("winProb", () => {
  // Accented spellings in the grid; callers pass ESPN's plain spellings.
  const matrix: Matrix = {
    players: ["Félix Auger-Aliassime", "Iga Świątek"],
    formats: [3, 5],
    surfaces: {
      Hard: { "3": [[0.5, 0.62], [0.38, 0.5]] },
      Clay: { "3": [[0.5, null as unknown as number], [0.44, 0.5]] },
    },
  };

  const players: PlayerRow[] = [
    { name: "Felix Auger Aliassime", elo: 2000, eloHard: 2100 },
    { name: "Iga Swiatek", elo: 1900, eloHard: 1900 },
  ];

  it("tier 1: hits the matrix across accent-mismatched spellings", () => {
    expect(winProb("Felix Auger Aliassime", "Iga Swiatek", "Hard", 3, null, matrix, "wta")).toEqual({
      p: 0.62,
      source: "matrix",
    });
  });

  it("falls through to Elo when the grid cell is non-numeric", () => {
    const r = winProb("Felix Auger Aliassime", "Iga Swiatek", "Clay", 3, players, matrix, "wta");
    expect(r.source).toBe("elo");
    expect(r.p).not.toBeNull();
  });

  it("tier 2: surface-blended Elo via the canonical per-tour blend (WTA 0.62)", () => {
    // ra = .38·2000 + .62·2100 = 2062, rb = 1900 → Δ = 162
    const r = winProb("Felix Auger Aliassime", "Iga Swiatek", "Hard", 3, players, null, "wta");
    expect(r.source).toBe("elo");
    expect(r.p).toBeCloseTo(1 / (1 + Math.pow(10, -162 / 400)), 6);
  });

  it("tier 2: uses the ATP blend weight when tour is atp (0.63)", () => {
    // ra = .37·2000 + .63·2100 = 2063, rb = 1900 → Δ = 163
    const r = winProb("Felix Auger Aliassime", "Iga Swiatek", "Hard", 3, players, null, "atp");
    expect(r.source).toBe("elo");
    expect(r.p).toBeCloseTo(1 / (1 + Math.pow(10, -163 / 400)), 6);
  });

  it("blends elo with itself when the surface rating is missing", () => {
    const bare: PlayerRow[] = [
      { name: "Felix Auger Aliassime", elo: 2000 }, // no eloHard → ra = 2000
      { name: "Iga Swiatek", elo: 1900 },
    ];
    const r = winProb("Felix Auger Aliassime", "Iga Swiatek", "Hard", 3, bare, null, "wta");
    expect(r.p).toBeCloseTo(1 / (1 + Math.pow(10, -100 / 400)), 6);
  });

  it("returns nulls for unknown players", () => {
    expect(winProb("Nobody Atall", "Iga Swiatek", "Hard", 3, players, matrix, "wta")).toEqual({
      p: null,
      source: null,
    });
  });

  it("returns null when the same player is on both sides (regression)", () => {
    expect(
      winProb("Iga Swiatek", "Iga Świątek", "Hard", 3, players, matrix, "wta"),
    ).toEqual({ p: null, source: null });
  });
});

/* ------------------------------------------------------------------ */
/* fetchLiveMatches                                                    */
/* ------------------------------------------------------------------ */

describe("fetchLiveMatches", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  const comp = (id: number, over: Record<string, unknown> = {}) => ({
    id,
    status: { type: { state: "in", shortDetail: "Set 2" } },
    round: { displayName: "3rd Round" },
    competitors: [
      { athlete: { displayName: "Carlos Alcaraz" }, linescores: [{ value: 6.0 }, { value: 3 }] },
      { athlete: { displayName: "Taylor Fritz" }, linescores: [{ value: 4.0 }] },
    ],
    ...over,
  });

  const payload = {
    events: [
      {
        name: "The Championships, Wimbledon presented by Sponsor",
        shortName: "Wimbledon",
        groupings: [
          {
            grouping: { slug: "mens-singles" },
            competitions: [
              comp(101),
              comp(101), // duplicate competition id → deduped
              comp(102, { status: { type: { state: "post", shortDetail: "Final" } } }), // finished
              comp(103, { round: { displayName: "Qualifying 1st Round" } }), // qualies
            ],
          },
          {
            grouping: { slug: "mens-doubles" },
            competitions: [comp(104)], // wrong slug → skipped
          },
        ],
      },
    ],
  };

  it("keeps only in-progress, non-qualifying singles, deduped by id", async () => {
    const fetchMock = vi.fn(async () => ({ ok: true, json: async () => payload }));
    vi.stubGlobal("fetch", fetchMock);

    const out = await fetchLiveMatches("atp");
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/atp/scoreboard"), expect.anything());
    expect(out).toHaveLength(1);
    const m = out[0];
    expect(m.id).toBe("101");
    expect(m.event).toBe("Wimbledon"); // shortName preferred over name
    expect(m.round).toBe("3rd Round");
    expect(m.detail).toBe("Set 2");
    expect(m.a).toBe("Carlos Alcaraz");
    expect(m.b).toBe("Taylor Fritz");
    // linescores: 6.0 coerced to 6, missing second set for B coerced to 0
    expect(m.sets).toEqual([
      [6, 4],
      [3, 0],
    ]);
  });

  it("rejects on an HTTP error response", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false, status: 503 })));
    await expect(fetchLiveMatches("wta")).rejects.toThrow("espn 503");
  });
});
