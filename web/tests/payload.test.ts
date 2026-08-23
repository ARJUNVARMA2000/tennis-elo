import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = (path: string) => readFileSync(new URL(`../${path}`, import.meta.url), "utf8");

describe("generation-aware payload loading", () => {
  it("deduplicates in-flight JSON requests and invalidates a tour when meta advances", () => {
    const tour = source("lib/tour.tsx");
    expect(tour).toContain("const jsonCache = new Map");
    expect(tour).toContain("if (cached?.promise) return cached.promise");
    expect(tour).toContain("previous !== generation");
    expect(tour).toContain("invalidateTour(tour, url)");
  });

  it("loads one matrix context and one selected player dossier instead of monoliths", () => {
    const matrix = source("lib/matrix.ts");
    const predictor = source("app/predict/page.tsx");
    const player = source("app/player/page.tsx");
    const style = source("app/style/page.tsx");
    expect(matrix).toContain('useData<MatrixIndex>("matrix-index.json")');
    expect(predictor).toContain("useMatrixShard(surface, bo)");
    expect(player).toContain('useData<ProfileIndex>("profile-index.json")');
    expect(player).toContain("selectedSummary?.file");
    expect(style).toContain('useData<ProfileIndex>("profile-index.json")');
    expect([predictor, player, style].join("\n")).not.toMatch(/useData<[^>]+>\("(?:matrix|profiles)\.json"\)/);
  });

  it("keeps the home upcoming payload small and lazy-loads event evidence", () => {
    const upcoming = source("lib/upcoming.ts");
    const home = source("app/page.tsx");
    const schedule = source("app/schedule/page.tsx");
    const matches = source("app/matches/page.tsx");
    const predict = source("app/predict/page.tsx");
    const why = source("components/PredictionWhy.tsx");
    expect(upcoming).toContain('useData<UpcomingIndex>("upcoming-index.json")');
    expect(upcoming).toContain("useDataFiles<UpcomingEventShard>");
    expect(upcoming).toContain("ref?.evidenceFile");
    expect(home).toContain("useUpcomingHighlights()");
    expect(schedule).toContain("useUpcomingEvents()");
    expect(matches).toContain('useUpcomingEvents(tab === "upcoming")');
    expect(predict).toContain("useUpcomingDetail(scheduled");
    expect(why).toContain("onToggle=");
    expect([upcoming, home, schedule, matches, predict].join("\n")).not.toContain("upcoming.json");
  });
});

describe("match center contract", () => {
  it("ships keyboard tabs, all three match states, and tournament filters", () => {
    const matches = source("app/matches/page.tsx");
    const live = source("components/LiveTicker.tsx");
    const why = source("components/PredictionWhy.tsx");
    expect(matches).toContain('const TABS = ["live", "upcoming", "final"]');
    expect(matches).toContain('role="tablist"');
    expect(matches).toContain('role="tabpanel"');
    expect(matches).toContain('keyboardEvent.key !== "ArrowLeft"');
    expect(matches).toContain('label="Tournament filter"');
    expect(live).toContain('aria-label="Live tournament filter"');
    expect(live).toContain("ESPN scores · pre-match model odds · refreshes every minute");
    expect(live).toContain("pre-match win probability");
    expect(live).not.toContain("ESPN scores · model win odds");
    expect(matches).toContain('note="frozen first-sighting call"');
    expect(matches).toContain("<ForecastTimeline");
    expect(matches).toContain("matchup={hasMatchupProfiles(match, roster)}");
    expect(matches).toContain("excludeLiveMatches(upcomingState.data ?? [], live.matches)");
    expect(matches).toContain('data-live-schedule-contract="exact-event-unordered-pair-v1"');
    expect(matches).toContain("<PredictionWhy match={match} />");
    expect(why).toContain("Model evidence");
    expect(why).toContain("<ForecastTimeline");
  });
});
