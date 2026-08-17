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
    expect(matches).toContain('note="frozen pre-match call"');
    expect(matches).toContain("<PredictionWhy match={match} />");
    expect(why).toContain("not causal/SHAP attribution");
  });
});
