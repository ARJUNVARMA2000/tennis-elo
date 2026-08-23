import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import PredictionSummary, { summarizePrediction } from "@/components/PredictionSummary";

describe("prediction summary", () => {
  it("orients the favorite and reports distance from an even matchup", () => {
    expect(summarizePrediction(0.65, "Arthur Fils", "Frances Tiafoe")).toMatchObject({
      favorite: "Arthur Fils",
      other: "Frances Tiafoe",
      winProbability: 0.65,
      edgePp: 15,
      favoriteIsA: true,
      isEven: false,
    });
    expect(summarizePrediction(0.35, "Arthur Fils", "Frances Tiafoe")).toMatchObject({
      favorite: "Frances Tiafoe",
      other: "Arthur Fils",
      winProbability: 0.65,
      edgePp: 15,
      favoriteIsA: false,
      isEven: false,
    });
    expect(summarizePrediction(0.5, "Arthur Fils", "Frances Tiafoe")).toMatchObject({
      favorite: "Arthur Fils",
      winProbability: 0.5,
      edgePp: 0,
      isEven: true,
    });
    expect(summarizePrediction(0.4996, "Arthur Fils", "Frances Tiafoe")).toMatchObject({
      favorite: "Arthur Fils",
      favoriteIsA: true,
      isEven: true,
    });
  });

  it("renders an honest meter and existing DEUCE drill-ins", () => {
    const html = renderToStaticMarkup(createElement(PredictionSummary, {
      probabilityA: 0.65,
      playerA: "Arthur Fils",
      playerB: "Frances Tiafoe",
      surface: "Hard",
      bestOf: 3,
      tour: "atp",
    }));

    expect(html).toContain('data-prediction-summary="recommendation-card-adaptation-v1"');
    expect(html).toContain("Arthur Fils is favored");
    expect(html).toContain('role="meter"');
    expect(html).toContain('aria-valuenow="15"');
    expect(html).toContain("not an edge over a betting market");
    expect(html).toMatch(/href="\/player\/?\?p=Arthur(?:\+|%20)Fils"/);
    expect(html).toMatch(/href="\/style\/?\?a=Arthur(?:\+|%20)Fils&amp;b=Frances(?:\+|%20)Tiafoe"/);
  });
});
