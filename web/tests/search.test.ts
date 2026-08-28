import { describe, expect, it } from "vitest";
import { commandResults } from "@/lib/search";

const players = [
  { name: "Jannik Sinner", eloRank: 1 },
  { name: "Carlos Alcaraz", eloRank: 2 },
  { name: "Félix Auger-Aliassime", eloRank: 9 },
];
const brackets = [
  { name: "Cincinnati", espnId: "718-2026", status: "upcoming", surface: "Hard" },
  { name: "Montreal", espnId: "421-2026", status: "live", surface: "Hard" },
];

describe("commandResults", () => {
  it("shows a small set of useful routes before the user types", () => {
    const results = commandResults("", "atp", players, brackets);
    expect(results.length).toBeGreaterThan(2);
    expect(results.every((result) => result.kind === "page")).toBe(true);
    expect(results.some((result) => result.label === "Schedule")).toBe(true);
  });

  it("finds pages, players and current brackets", () => {
    expect(commandResults("rank", "atp", players, brackets)[0].label).toBe("Rankings");
    expect(commandResults("sinner", "atp", players, brackets)[0]).toMatchObject({
      kind: "player", label: "Jannik Sinner",
    });
    expect(commandResults("cinc", "atp", players, brackets)[0]).toMatchObject({
      kind: "tournament", label: "Cincinnati",
    });
    const params = new URLSearchParams(
      commandResults("cinc", "atp", players, brackets)[0].href.split("?")[1],
    );
    expect(params.get("e")).toBe("718-2026");
  });

  it("is accent-insensitive and preserves the active tour in links", () => {
    const result = commandResults("felix", "wta", players, brackets)[0];
    expect(result.label).toBe("Félix Auger-Aliassime");
    expect(new URLSearchParams(result.href.split("?")[1]).get("tour")).toBe("wta");
  });

  it("turns a two-player query into a direct predictor action", () => {
    const result = commandResults("Sinner vs Alcaraz", "atp", players, brackets)[0];
    expect(result.kind).toBe("prediction");
    const params = new URLSearchParams(result.href.split("?")[1]);
    expect(params.get("a")).toBe("Jannik Sinner");
    expect(params.get("b")).toBe("Carlos Alcaraz");
  });
});
