import { readFileSync } from "node:fs";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { Card } from "@/app/page";
import { byTournamentPriority, drawCaveat, emptyProjectionNote, heat, heroEvent, pct, percentileScaler, RECENT_PRESTIGE_MS, scoreDist, SURFACE_BLEND, tournamentDrawLabel, tournamentView } from "@/lib/ui";

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

describe("coverage fallback copy", () => {
  it("describes a known completed final without pretending its draw is pending", () => {
    const final = { status: "completed", drawSize: null, champion: "A Champion" };
    expect(tournamentDrawLabel(final)).toBe("final recorded");
    expect(emptyProjectionNote(final)).toContain("final result is recorded");
  });

  it("keeps the pending copy for a begun event whose field is still unavailable", () => {
    const live = { status: "live", drawSize: null, champion: null };
    expect(tournamentDrawLabel(live)).toBe("draw pending");
    expect(emptyProjectionNote(live)).toContain("once the draw is settled");
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

  it("never gives the hero to a completed event", () => {
    expect(heroEvent([slam("completed", "2026-07-11")], NOW)).toBeUndefined();
  });

  it("keeps a completed prestige event in recents for exactly seven days", () => {
    const end = new Date("2026-07-11T00:00").getTime();
    const event = slam("completed", "2026-07-11");
    expect(tournamentView([event], end + RECENT_PRESTIGE_MS).recent).toEqual([event]);
    expect(tournamentView([event], end + RECENT_PRESTIGE_MS + 1).recent).toEqual([]);
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

  it("orders current tournaments before completed ones, then uses prestige within each status", () => {
    const ordered = byTournamentPriority([
      { level: "Grand Slam", name: "Wimbledon", status: "completed" },
      { level: "ATP 500", name: "Upcoming Five Hundred", status: "upcoming" },
      { level: "ATP 250", name: "Live Two Fifty", status: "live" },
      { level: "ATP 500", name: "Live Five Hundred", status: "live" },
      { level: "Masters 1000", name: "Done Thousand", status: "completed" },
    ]);
    expect(ordered.map((t) => t.name)).toEqual([
      "Live Five Hundred",
      "Live Two Fifty",
      "Upcoming Five Hundred",
      "Wimbledon",
      "Done Thousand",
    ]);
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

  it("drops ordinary completed events but keeps a recent completed prestige event", () => {
    const view = tournamentView([
      { level: "Masters 1000", name: "A Thousand", status: "live", end: "2026-08-03" },
      { level: "ATP 500", name: "Done Five Hundred", status: "completed", end: "2026-07-10" },
      { level: "Grand Slam", name: "Done Slam", status: "completed", end: "2026-07-10" },
    ], NOW);
    expect(view.other).toEqual([]);
    expect(view.recent.map((t) => t.name)).toEqual(["Done Slam"]);
  });

  it("keeps live play primary over an upcoming 1000 draw", () => {
    const view = tournamentView([
      { level: "ATP 500", name: "Live Five Hundred", status: "live", end: "2026-08-03" },
      { level: "Masters 1000", name: "Toronto", status: "upcoming", end: "2026-08-14" },
      { level: "ATP 250", name: "Estoril", status: "completed", end: "2026-07-26" },
      { level: "Masters 1000", name: "Done Thousand", status: "completed", end: "2026-07-28" },
    ], new Date("2026-08-01T12:00").getTime());
    expect(view.hero).toBeUndefined();
    expect(view.grid.map((t) => t.name)).toEqual(["Live Five Hundred"]);
    expect(view.upcoming.map((t) => t.name)).toEqual(["Toronto"]);
    expect(view.recent.map((t) => t.name)).toEqual(["Done Thousand"]);
  });

  it("allows an upcoming 1000 hero only when nothing is live", () => {
    const view = tournamentView([
      { level: "Masters 1000", name: "Toronto", status: "upcoming", end: "2026-08-14" },
      { level: "ATP 250", name: "Future 250", status: "upcoming", end: "2026-08-10" },
    ], NOW);
    expect(view.hero?.name).toBe("Toronto");
    expect(view.other.map((t) => t.name)).toEqual(["Future 250"]);
    expect(view.upcoming).toEqual([]);
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

describe("tournament grid card", () => {
  const field = (count: number) => Array.from({ length: count }, (_, i) => ({
    name: `Seed ${String(i + 1).padStart(2, "0")}`,
    champion: (count - i) / 100,
    final: (count - i) / 80,
    sf: (count - i) / 60,
    reach: { R16: 1, QF: 0.75, SF: 0.5, F: 0.3, Champion: (count - i) / 100 },
  }));

  const cardTournament = (count: number) => ({
    name: "Field Visibility Open", surface: "Hard", level: "ATP 250", bestOf: 3,
    start: "2026-07-25", end: "2026-08-02", status: "live" as const,
    drawStatus: "real" as const, drawSize: count, aliveCount: count,
    champion: null, runnerUp: null, modelFavorite: "Seed 01", favoritePicked: false,
    projection: field(count),
  });

  it("shows 16 players by default on detailed and compact cards", () => {
    for (const compact of [false, true]) {
      const html = renderToStaticMarkup(createElement(Card, {
        t: cardTournament(18), compact,
      }));
      expect(html).toContain("Seed 16");
      expect(html).not.toContain("Seed 17");
      expect(html).toContain("show all projected (18)");
    }
  });

  it("shows every remaining player and no expansion control below 16", () => {
    const html = renderToStaticMarkup(createElement(Card, { t: cardTournament(7) }));
    expect(html).toContain("Seed 07");
    expect(html).not.toContain("show all projected");
  });

  it("links profile-backed names and leaves unavailable names plain in detailed and compact cards", () => {
    const profileRoster = new Set(["Seed 01"]);
    for (const compact of [false, true]) {
      const html = renderToStaticMarkup(createElement(Card, {
        t: cardTournament(2), compact, profileRoster,
      }));
      expect(html).toMatch(/href="[^"]*p=Seed\+01/);
      expect(html).not.toMatch(/href="[^"]*p=Seed\+02/);
      expect(html).toContain("Seed 02");
    }
  });

  it("renders round-by-round reach columns for every active card, regardless of tier", () => {
    const tournament = {
      name: "Mubadala DC Open", surface: "Hard", level: "ATP 500", bestOf: 3,
      start: "2026-07-25", end: "2026-08-02", status: "live" as const,
      drawStatus: "real" as const, drawSize: 48, aliveCount: 16,
      champion: null, runnerUp: null, modelFavorite: "Player One", favoritePicked: false,
      projection: [
        { name: "Player One", champion: 0.25, final: 0.4, sf: 0.6,
          reach: { R16: 0.9, QF: 0.75, SF: 0.6, F: 0.4, Champion: 0.25 } },
        { name: "Player Two", champion: 0.18, final: 0.31, sf: 0.5,
          reach: { R16: 0.82, QF: 0.66, SF: 0.5, F: 0.31, Champion: 0.18 } },
      ],
    };
    const html = renderToStaticMarkup(createElement(Card, { t: tournament }));
    expect(html).toContain("R16");
    expect(html).toContain("QF");
    expect(html).toContain("SF");
    expect(html).toContain("Win");

    const smallHtml = renderToStaticMarkup(createElement(Card, {
      t: { ...tournament, name: "Generali Open", level: "ATP 250" },
    }));
    expect(smallHtml).toContain("R16");
    expect(smallHtml).toContain("QF");
  });

  it("starts a large-draw forecast at its earliest available round", () => {
    const tournament = {
      name: "Toronto", surface: "Hard", level: "Masters 1000", bestOf: 3,
      start: "2026-08-02", end: "2026-08-14", status: "upcoming" as const,
      drawStatus: "real" as const, drawSize: 96, aliveCount: 96,
      champion: null, runnerUp: null, modelFavorite: "Player One", favoritePicked: false,
      projection: [
        { name: "Player One", champion: 0.25, final: 0.4, sf: 0.6,
          reach: { R128: 1, R64: 0.95, R32: 0.82, R16: 0.7, QF: 0.6,
            SF: 0.5, F: 0.4, Champion: 0.25 } },
      ],
    };
    const html = renderToStaticMarkup(createElement(Card, { t: tournament }));
    for (const round of ["R128", "R64", "R32", "R16", "QF", "SF", "Win"])
      expect(html).toContain(round);
  });

  it("keeps a concurrent lower-tier event compact beneath a hero", () => {
    const tournament = {
      name: "Generali Open", surface: "Clay", level: "ATP 250", bestOf: 3,
      start: "2026-07-25", end: "2026-08-02", status: "live" as const,
      drawStatus: "real" as const, drawSize: 28, aliveCount: 16,
      champion: null, runnerUp: null, modelFavorite: "Player One", favoritePicked: false,
      projection: [
        { name: "Player One", champion: 0.25, final: 0.4, sf: 0.6,
          reach: { R16: 0.9, QF: 0.75, SF: 0.6, F: 0.4, Champion: 0.25 } },
      ],
    };
    const html = renderToStaticMarkup(createElement(Card, { t: tournament, compact: true }));
    expect(html).toContain("Title odds from here");
    expect(html).not.toContain("R16");
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
