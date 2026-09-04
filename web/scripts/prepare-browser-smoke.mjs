// Deterministic data for the pre-merge browser smoke. This writes only into an explicitly
// supplied empty directory (CI uses public/data in a clean checkout), so it can never replace
// a developer's machine-generated local data by accident.
import { mkdirSync, readdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { BROWSER_SMOKE_PLAYER_NAMES } from "./browser-smoke-fixture.mjs";

const target = resolve(process.argv[2] || "");
if (!process.argv[2]) throw new Error("usage: node scripts/prepare-browser-smoke.mjs <empty-data-dir>");
mkdirSync(target, { recursive: true });
if (readdirSync(target).length) throw new Error(`browser-smoke target is not empty: ${target}`);

const generation = "2026-08-24T00:00:00Z";
const benchmarkDeltaDirection = "tennisAbstract-minus-deuce; positive favors DEUCE";
const benchmarkStages = ["R64", "R32", "R16", "QF", "SF", "F", "W"];
const style = {
  style_serve_dom: 0.72,
  style_placement: 0.55,
  style_net: 0.24,
  style_snv: 0.12,
  style_aggression: 0.61,
  style_fhbh: 0.58,
  style_return_depth: 0.65,
  style_bp_clutch: 0.04,
};

function paired(n, dLl, se) {
  return {
    n,
    model: { n, acc: 0.68, logloss: 0.612, brier: 0.211 },
    kalshi: { n, acc: 0.66, logloss: 0.623, brier: 0.219 },
    d_ll: dLl,
    d_ll_se: se,
    d_brier: 0.008,
    d_brier_se: 0.006,
    d_acc: 0.02,
    t: dLl / se,
  };
}

function payloads(tour) {
  const names = BROWSER_SMOKE_PLAYER_NAMES[tour];
  const players = names.map((name, index) => ({
    name,
    eloRank: index + 1,
    elo: 1880 - index * 70,
    eloHard: 1900 - index * 60,
    eloClay: 1840 - index * 55,
    eloGrass: 1870 - index * 65,
    servePct: 0.66 - index * 0.03,
    returnPct: 0.42 + index * 0.02,
    rankPoints: 5200 - index * 800,
    matches: 180 - index * 20,
    hand: index ? "L" : "R",
  }));
  const summaries = players.map((player, index) => ({
    name: player.name,
    file: `profile-smoke-${index + 1}.json`,
    eloRank: player.eloRank,
    elo: player.elo,
    eloHard: player.eloHard,
    eloClay: player.eloClay,
    eloGrass: player.eloGrass,
    servePct: player.servePct,
    returnPct: player.returnPct,
    style: Object.fromEntries(Object.entries(style).map(([key, value]) => [key, value - index * 0.08])),
    performance: { n: 12, wins: 8 - index, expectedWins: 7.2 - index * 0.4, delta: 0.8 - index * 0.6 },
  }));
  const metrics = (n, acc, logloss, brier) => ({ n, acc, logloss, brier });
  const headline = paired(48, 0.011, 0.008);
  const upcoming = names.map((name, index) => ({
    matchId: `smoke-${tour}-${index}`, event: "Smoke Open", espnId: "smoke-2026",
    date: "2026-09-05", round: "R32", surface: "Hard", bestOf: 3,
    playerA: name, playerB: `Fixture Rival ${index + 1}`, pA: 0.6,
  }));
  return {
    "upcoming-index.json": { schema: "upcoming-v2", schemaVersion: 2, generation, count: 2,
      events: [{ name: "Smoke Open", espnId: "smoke-2026", surface: "Hard", count: 2,
        file: "upcoming-event-smoke.json", evidenceFile: "upcoming-evidence-smoke.json" }], highlights: upcoming },
    "upcoming-event-smoke.json": { schema: "upcoming-event-v1", generation, matches: upcoming },
    "upcoming-evidence-smoke.json": { schema: "upcoming-evidence-v1", generation, details: [] },
    "tournaments.json": [],
    "fixtures.json": [],
    "meta.json": {
      tour,
      lastUpdated: generation,
      modelTrainedAt: generation,
      matches: 240,
      players: players.length,
    },
    "players.json": players,
    "profile-index.json": { generation, profiles: summaries },
    ...Object.fromEntries(summaries.map((summary, index) => [summary.file, {
      generation,
      name: summary.name,
      history: [["2026-05-01", summary.elo - 35], ["2026-06-01", summary.elo - 12], ["2026-08-01", summary.elo]],
      recent: [
        { date: "2026-08-20", opp: names[1 - index], surface: "Hard", won: index === 0, score: "6-4 6-4", event: "Smoke Open" },
        { date: "2026-08-18", opp: "Fixture Rival", surface: "Hard", won: true, score: "7-6 6-3", event: "Smoke Open" },
      ],
      h2h: [{ opp: names[1 - index], w: index === 0 ? 3 : 1, l: index === 0 ? 1 : 3 }],
      performance: {
        name: summary.name,
        ...summary.performance,
        recent: [],
      },
    }])),
    "accuracy.json": {
      window: "2016-2026",
      n: 1200,
      models: {
        eloBlend: metrics(1200, 0.65, 0.628, 0.219),
        pointModel: metrics(1200, 0.66, 0.621, 0.215),
        combiner: metrics(1200, 0.68, 0.606, 0.208),
      },
      marketAnchor: { acc: 0.69, brier: 0.203 },
      calibration: [
        { bin: "50-60", n: 300, pred: 0.55, actual: 0.54 },
        { bin: "60-70", n: 260, pred: 0.65, actual: 0.66 },
        { bin: "70-80", n: 180, pred: 0.75, actual: 0.74 },
      ],
      bySurface: { Hard: 0.207, Clay: 0.211, Grass: 0.204 },
    },
    "track.json": {
      tour,
      lastUpdated: generation,
      matchForecasts: {
        logged: 96,
        graded: 84,
        pending: 12,
        overall: metrics(84, 0.69, 0.601, 0.205),
        calibration: [{ bin: "60-70", n: 12, pred: 0.65, actual: 0.67 }],
        bySurface: {},
        recent: [],
        byMonth: [
          { month: "2026-06", n: 24, acc: 0.67, logloss: 0.62, brier: 0.214 },
          { month: "2026-07", n: 30, acc: 0.70, logloss: 0.59, brier: 0.201 },
          { month: "2026-08", n: 30, acc: 0.70, logloss: 0.60, brier: 0.204 },
        ],
      },
      tournamentOdds: {
        events: 0,
        hitRate: null,
        championBrier: null,
        recent: [],
      },
    },
    "tennis-abstract.json": {
      schema: "tennis-abstract-benchmark-v1",
      benchmark: {
        id: "tennis-abstract",
        name: "Tennis Abstract",
        tour,
        event: "US Open",
        espnId: "189-2026",
        season: 2026,
      },
      status: "accruing",
      source: {
        name: "Tennis Abstract",
        url: tour === "atp"
          ? "https://www.tennisabstract.com/current/2026USOpenMenForecast.html"
          : "https://www.tennisabstract.com/current/2026USOpenWomenForecast.html",
        capturedAt: "2026-08-31T00:55:47.502Z",
      },
      capture: {
        captureLocalDate: "2026-08-30",
        classification: "first-post-start-capture",
        eligibleMatchProof: "saved scheduledDate is strictly after captureLocalDate",
        eventTimezone: "America/New_York",
      },
      matchComparison: {
        eligible: 1,
        graded: 0,
        pending: 1,
        excluded: 63,
        deuce: { n: 0, logloss: null, brier: null },
        tennisAbstract: { n: 0, logloss: null, brier: null },
        paired: {
          n: 0,
          direction: benchmarkDeltaDirection,
          loglossDelta: null,
          seLogloss: null,
          brierDelta: null,
          seBrier: null,
        },
        exclusionReasons: { prestart_timing_unproven: 63 },
      },
      reachComparison: {
        fieldSize: 128,
        fieldAligned: true,
        exclusionReasons: {},
        stages: benchmarkStages.map((stage) => ({
          stage,
          n: 128,
          resolved: 0,
          eligible: 128,
          graded: 0,
          pending: 128,
          excluded: 0,
          deuce: { n: 0, logloss: null, brier: null },
          tennisAbstract: { n: 0, logloss: null, brier: null },
          paired: {
            n: 0,
            direction: benchmarkDeltaDirection,
            loglossDelta: null,
            seLogloss: null,
            brierDelta: null,
            seBrier: null,
          },
          exclusionReasons: {},
        })),
      },
      caveats: [
        "This first capture was made after Day 1 began.",
        "One tournament is descriptive evidence, not a model-selection result.",
      ],
    },
    "market.json": {
      years: [2016, 2026],
      matched: 900,
      sources: { label: "fixture closing odds", byYear: {} },
      stack: {
        fit: { valStart: 2020, nVal: 500 },
        val: {
          model: metrics(500, 0.68, 0.606, 0.208),
          market: metrics(500, 0.69, 0.603, 0.205),
          stack: metrics(500, 0.69, 0.601, 0.204),
        },
      },
    },
    "kalshi.json": {
      tour,
      lastUpdated: generation,
      coverage: {
        events: 80,
        matched: 48,
        pending: 8,
        unmatched: 12,
        cancelled: 3,
        walkovers: 5,
        retirements: 4,
        date_range: ["2026-05-01", "2026-08-23"],
      },
      headline,
      segments: [
        { segment: "pred_source: live", ...paired(24, 0.014, 0.012) },
        { segment: "surface: hard", ...paired(28, 0.009, 0.010) },
        { segment: "best rank top-20", ...paired(18, -0.004, 0.014) },
        { segment: "round quarterfinal", ...paired(16, 0.018, 0.015) },
      ],
      calibration: {
        model: [{ bin: "50-60", n: 20, pred: 0.55, actual: 0.55 }, { bin: "60-70", n: 18, pred: 0.65, actual: 0.67 }],
        kalshi: [{ bin: "50-60", n: 20, pred: 0.55, actual: 0.50 }, { bin: "60-70", n: 18, pred: 0.65, actual: 0.61 }],
      },
      bestCalls: [],
      worstMisses: [],
      disagree: { n: 9, modelRight: 6 },
    },
  };
}

for (const tour of ["atp", "wta"]) {
  const dir = resolve(target, tour);
  mkdirSync(dir, { recursive: true });
  for (const [name, value] of Object.entries(payloads(tour))) {
    writeFileSync(resolve(dir, name), `${JSON.stringify(value, null, 2)}\n`);
  }
}

console.log(`browser-smoke fixture written to ${target}`);
