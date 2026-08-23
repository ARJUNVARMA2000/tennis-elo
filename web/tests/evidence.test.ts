import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import PredictionEvidence, { evidenceFactLine } from "@/components/PredictionEvidence";
import { matrixEvidence, orientEvidence, type PredictionEvidenceData } from "@/lib/evidence";
import type { MatrixShard } from "@/lib/matrix";

describe("model evidence orientation", () => {
  it("flips signed values and A/B facts without changing the supported player", () => {
    const source: PredictionEvidenceData = {
      schema: "evidence-v1",
      playerA: "A",
      playerB: "B",
      probabilityA: 0.7,
      signals: [{
        key: "rest",
        available: true,
        supports: "A",
        impactPp: 4.2,
        facts: { daysSinceA: 2, daysSinceB: 5, gap: 3 },
      }],
    };
    const flipped = orientEvidence(source, true);
    expect(flipped).toMatchObject({ playerA: "B", playerB: "A", probabilityA: 0.3 });
    expect(flipped.signals[0]).toMatchObject({
      supports: "A", impactPp: -4.2,
      facts: { daysSinceA: 5, daysSinceB: 2, gap: -3 },
    });
    expect(source.signals[0].impactPp).toBe(4.2);
  });

  it("decodes packed upper-triangle basis points in either player orientation", () => {
    const shard = {
      players: ["A", "B", "C"],
      evidence: {
        schema: "evidence-v1",
        encoding: "upper-triangle-bps-v1",
        // pair order: A-B, A-C, B-C
        effects: Object.fromEntries([
          "surfaceElo", "serveReturn", "form", "rest", "home", "h2h", "style",
        ].map((key) => [key, key === "surfaceElo" ? [250, -100, 50] : [0, 0, 0]])),
        available: { h2h: [1, 0, 0], style: [0, 0, 1] },
        homeAvailable: false,
      },
    } as unknown as MatrixShard;
    expect(matrixEvidence(shard, 0, 1)?.signals[0]).toMatchObject({
      key: "surfaceElo", impactPp: 2.5, supports: "A",
    });
    expect(matrixEvidence(shard, 1, 0)?.signals[0]).toMatchObject({
      key: "surfaceElo", impactPp: -2.5, supports: "A",
    });
  });
});

describe("model evidence context cards", () => {
  it("uses useful fallback facts when an arbitrary matrix matchup has no detailed facts", () => {
    expect(evidenceFactLine({
      key: "surfaceElo", available: true, supports: "A", impactPp: 2.5,
    }, "A", "B")).toBe("Surface-adjusted rating comparison.");
    expect(evidenceFactLine({
      key: "rest", available: true, supports: null, impactPp: 0,
    }, "A", "B")).toBe("Rest and recent workload signal.");
  });

  it("renders indexed, text-labelled support, neutral and unavailable states", () => {
    const evidence: PredictionEvidenceData = {
      schema: "evidence-v1",
      playerA: "A",
      playerB: "B",
      signals: [
        { key: "surfaceElo", available: true, supports: "A", impactPp: 4.2 },
        { key: "form", available: true, supports: null, impactPp: 0.01 },
        { key: "h2h", available: false, supports: null, impactPp: 0 },
      ],
    };
    const html = renderToStaticMarkup(createElement(PredictionEvidence, {
      evidence,
      components: { eloBlend: 0.61, pointModel: 0.57, combiner: 0.64 },
    }));

    expect(html).toContain('data-model-evidence="context-cards-v2"');
    expect(html).toContain('data-evidence-signal="surfaceElo"');
    expect(html).toContain('data-signal-state="player-a"');
    expect(html).toContain("Supports A");
    expect(html).toContain("+4.2 pp");
    expect(html).toContain('data-signal-state="neutral"');
    expect(html).toContain("Near neutral");
    expect(html).toContain('data-signal-state="unavailable"');
    expect(html).toContain("Unavailable");
    expect(html).toContain("not a causal explanation");
  });
});
