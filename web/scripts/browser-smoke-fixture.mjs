// One contract shared by the fixture writer and the assertions that are only meaningful
// against that fixture. Normal `npm run verify` must never depend on these identities.
export const BROWSER_SMOKE_PLAYER_NAMES = Object.freeze({
  atp: Object.freeze(["Atlas Ace", "Atlas Bravo"]),
  wta: Object.freeze(["Willow Ace", "Willow Bravo"]),
});

/** A full 128-slot draw progressed to R16, with equal odds among the 16 survivors. */
export function browserSmokeBracket(tour, generation) {
  const players = Array.from({ length: 128 }, (_, i) => `${BROWSER_SMOKE_PLAYER_NAMES[tour][0]} ${i + 1}`);
  const labels = ["R128", "R64", "R32", "R16", "QF", "SF", "F"];
  let seats = players.map((name) => [{ name, p: 1 }]);
  const rounds = [];
  const nodes = [];
  const reach = Object.fromEntries(players.map((name) => [name, { Entry: 1 }]));
  labels.forEach((round, r) => {
    const matches = [];
    const forecasts = [];
    const next = [];
    for (let m = 0; m < seats.length / 2; m++) {
      const left = seats[m * 2];
      const right = seats[m * 2 + 1];
      const settled = r < 3;
      const candidates = settled ? left : [...left, ...right].map((row) => ({ ...row, p: row.p / 2 }));
      matches.push({ a: left.length === 1 ? left[0].name : null,
        b: right.length === 1 ? right[0].name : null,
        seedA: null, seedB: null, p: r <= 3 ? 0.5 : null, probSource: r <= 3 ? "logged" : null,
        winner: settled ? "a" : null, score: settled ? "6-4 6-4" : null, upset: false });
      // Mirror the published Python base-node shape, which omits roundIndex.
      forecasts.push({ key: `smoke-draw-2026:r${r}:m${m}`, round, matchIndex: m,
        status: settled ? "confirmed" : "projected", winner: settled ? left[0].name : null, candidates });
      candidates.forEach(({ name, p }) => { reach[name][labels[r + 1] || "Champion"] = p; });
      next.push(candidates);
    }
    rounds.push({ round, matches });
    nodes.push({ round, matches: forecasts });
    seats = next;
  });
  const event = { name: "Progress Open", espnId: "smoke-draw-2026", surface: "Hard", bestOf: 3,
    level: "Grand Slam", status: "live", start: "2026-08-24", end: "2026-09-13",
    bracketSize: 128, drawSize: 128, champion: null, runnerUp: null,
    drawSource: "atp", drawSourceId: "smoke", drawSourceUrl: "", rounds,
    scenario: { file: "scenario-smoke-draw.json", generation } };
  const matrix = players.map(() => players.map(() => 0.5));
  return {
    "brackets.json": [event],
    "scenario-smoke-draw.json": { schemaVersion: 1, generation, event, players, rounds,
      matrices: { eloBlend: matrix, pointModel: matrix, combiner: matrix },
      base: { nodes, reach, champion: seats[0] } },
  };
}

/** @param {Record<string, string | undefined>} [env] */
export function getBrowserSmokeTourIdentities(env = process.env) {
  if (env.VERIFY_OFFLINE !== "1" || env.VERIFY_FIXTURE_DATA !== "1") return null;
  return Object.freeze({
    atp: Object.freeze({
      present: BROWSER_SMOKE_PLAYER_NAMES.atp[0],
      absent: BROWSER_SMOKE_PLAYER_NAMES.wta[0],
    }),
    wta: Object.freeze({
      present: BROWSER_SMOKE_PLAYER_NAMES.wta[0],
      absent: BROWSER_SMOKE_PLAYER_NAMES.atp[0],
    }),
  });
}
