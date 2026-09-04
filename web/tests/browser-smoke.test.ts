import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { getBrowserSmokeTourIdentities } from "../scripts/browser-smoke-fixture.mjs";
import { isTennisAbstractBenchmark } from "@/lib/tennis-abstract";

const root = resolve(fileURLToPath(new URL("..", import.meta.url)));

describe("real-browser CI smoke", () => {
  it("keeps fixture identity assertions out of default and generic offline verification", () => {
    const verifier = readFileSync(join(root, "scripts/verify.mjs"), "utf8");

    expect(verifier).not.toContain("Atlas Ace");
    expect(verifier).not.toContain("Willow Ace");
    expect(verifier).toContain("getBrowserSmokeTourIdentities(process.env)");
    expect(verifier).toContain("presentName === null || body.includes(presentName)");
    expect(getBrowserSmokeTourIdentities({})).toBeNull();
    expect(getBrowserSmokeTourIdentities({ VERIFY_OFFLINE: "1" })).toBeNull();
    expect(getBrowserSmokeTourIdentities({ VERIFY_FIXTURE_DATA: "1" })).toBeNull();
    expect(getBrowserSmokeTourIdentities({
      VERIFY_OFFLINE: "1",
      VERIFY_FIXTURE_DATA: "1",
    })).toEqual({
      atp: { present: "Atlas Ace", absent: "Willow Ace" },
      wta: { present: "Willow Ace", absent: "Atlas Ace" },
    });
  });

  it("builds a deterministic two-tour fixture and refuses to replace it", () => {
    const scratch = mkdtempSync(join(tmpdir(), "deuce-browser-smoke-"));
    const target = join(scratch, "data");
    try {
      execFileSync(process.execPath, [join(root, "scripts/prepare-browser-smoke.mjs"), target]);
      for (const tour of ["atp", "wta"]) {
        const profiles = JSON.parse(readFileSync(join(target, tour, "profile-index.json"), "utf8"));
        const kalshi = JSON.parse(readFileSync(join(target, tour, "kalshi.json"), "utf8"));
        const benchmark = JSON.parse(
          readFileSync(join(target, tour, "tennis-abstract.json"), "utf8"),
        );
        expect(profiles.profiles).toHaveLength(2);
        expect(kalshi.segments.length).toBeGreaterThan(0);
        expect(isTennisAbstractBenchmark(benchmark, tour as "atp" | "wta")).toBe(true);
        expect(benchmark.matchComparison.pending).toBe(1);
        expect(benchmark.matchComparison.eligible + benchmark.matchComparison.excluded).toBe(64);
        expect(benchmark.reachComparison.stages.map((stage: { stage: string }) => stage.stage))
          .toEqual(["R64", "R32", "R16", "QF", "SF", "F", "W"]);
      }
      expect(() => execFileSync(
        process.execPath,
        [join(root, "scripts/prepare-browser-smoke.mjs"), target],
        { stdio: "pipe" },
      )).toThrow();
    } finally {
      rmSync(scratch, { recursive: true, force: true });
    }
  });

  it("keeps the narrow browser gate and its negative controls wired into CI", () => {
    const workflow = readFileSync(resolve(root, "../.github/workflows/test.yml"), "utf8");
    const runner = readFileSync(join(root, "scripts/run-browser-smoke.mjs"), "utf8");
    const verifier = readFileSync(join(root, "scripts/verify.mjs"), "utf8");

    expect(workflow).toContain("playwright-core install --with-deps chromium");
    expect(workflow).toContain("npm run test:browser");
    expect(runner).toContain(
      'VERIFY_ROUTES: process.env.VERIFY_ROUTES || "/scorecard/,/player/,/track/"',
    );
    expect(runner).toContain('VERIFY_OFFLINE: "1"');
    expect(runner).toContain('VERIFY_FIXTURE_DATA: "1"');
    expect(runner).toContain('VERIFY_ASSERT_NEGATIVE_CONTROLS: "1"');
    expect(runner).toContain("BROWSER_SMOKE_TIMEOUT_MS");
    expect(workflow).toContain("timeout-minutes: 30");
    expect(verifier).toContain("vertical negative control no longer traps wheel input");
    expect(verifier).toContain("horizontal negative control still accepts wheel input");
    expect(verifier).toContain('route === "/scorecard/" && !geometry.canScroll');
    expect(verifier).toContain('route === "/track/" && FIXTURE_TOUR_IDENTITIES');
    expect(verifier).toContain('name: "US Open: DEUCE vs Tennis Abstract"');
    expect(verifier).toContain('data-tennis-abstract-benchmark="accruing"');
    expect(verifier).toContain('2026USOpenWomenForecast.html');
    expect(verifier).toContain('name: "Full-field reach forecast scores"');
    expect(verifier).toContain('page.keyboard.press("ArrowRight")');
    expect(verifier).toContain('page.getByRole("button", { name: /^wta$/i })');
    expect(verifier).toContain('body.includes(presentName)');
    expect(verifier).toContain('url.hash === "#profile"');
    expect(verifier).toContain("saved WTA preference");
    expect(verifier).toContain('page.route("**/*"');
  });
});
