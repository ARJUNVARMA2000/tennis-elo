import { describe, expect, it } from "vitest";
import {
  availableAxes, blendedElo, EXPLORER_AXES, EXPLORER_PRESETS, plottable, sortByAxis,
  type ExplorerPlayer,
} from "@/lib/ui";

/** A pre-enrichment row (no heightCm / surface pcts / form90 / winRate10 keys). */
const legacy = (over: Partial<ExplorerPlayer> = {}): ExplorerPlayer => ({
  name: "P", eloRank: 1, elo: 2000, eloHard: 1980, eloClay: 1950, eloGrass: 1900,
  servePct: 0.68, returnPct: 0.41, age: 24, matches: 300, rankPoints: 5000, country: "USA",
  ...over,
});

const axis = (key: string) => {
  const a = EXPLORER_AXES.find((x) => x.key === key);
  if (!a) throw new Error(`missing axis ${key}`);
  return a;
};

describe("EXPLORER_AXES", () => {
  it("every accessor returns null (never NaN/undefined) on a legacy row's missing fields", () => {
    const p = legacy();
    for (const a of EXPLORER_AXES) {
      const v = a.get(p, "atp");
      expect(v === null || (typeof v === "number" && isFinite(v)), a.key).toBe(true);
    }
    expect(axis("heightCm").get(p, "atp")).toBeNull();
    expect(axis("winRate10").get(p, "atp")).toBeNull();
    expect(axis("servePctGrass").get(p, "atp")).toBeNull();
  });

  it("blended surface axes equal blendedElo (raw shrunk surface Elo is never exposed)", () => {
    const p = legacy();
    expect(axis("eloClayBlend").get(p, "atp")).toBe(blendedElo(p.elo, p.eloClay, "atp"));
    expect(axis("eloClayBlend").get(p, "wta")).toBe(blendedElo(p.elo, p.eloClay, "wta"));
    expect(EXPLORER_AXES.some((a) => a.key === "eloHard")).toBe(false);
  });

  it("every preset references registered axis keys", () => {
    for (const pr of EXPLORER_PRESETS) {
      expect(EXPLORER_AXES.some((a) => a.key === pr.x), pr.label).toBe(true);
      expect(EXPLORER_AXES.some((a) => a.key === pr.y), pr.label).toBe(true);
    }
  });
});

describe("availableAxes", () => {
  it("hides axes that are all-null in the field (pre-enrichment snapshot)", () => {
    const field = [legacy({ name: "A" }), legacy({ name: "B" }), legacy({ name: "C" }), legacy({ name: "D" })];
    const keys = availableAxes(field, "atp").map((a) => a.key);
    expect(keys).toContain("servePct");
    expect(keys).toContain("eloClayBlend");
    expect(keys).not.toContain("heightCm");
    expect(keys).not.toContain("winRate10");
  });

  it("surfaces an enrichment axis once enough players carry it", () => {
    const field = [
      legacy({ name: "A", heightCm: 185 }), legacy({ name: "B", heightCm: 190 }),
      legacy({ name: "C", heightCm: 178 }), legacy({ name: "D" }),
    ];
    expect(availableAxes(field, "atp").map((a) => a.key)).toContain("heightCm");
  });
});

describe("plottable", () => {
  it("drops players missing either axis and counts them", () => {
    const field = [
      legacy({ name: "A", heightCm: 185 }),
      legacy({ name: "B" }),                    // no height -> dropped
      legacy({ name: "C", heightCm: 178 }),
    ];
    const { points, missing } = plottable(field, axis("heightCm"), axis("servePct"), "atp");
    expect(points.map((d) => d.p.name)).toEqual(["A", "C"]);
    expect(missing).toBe(1);
  });
});

describe("sortByAxis", () => {
  const field = [
    legacy({ name: "Short", heightCm: 175 }),
    legacy({ name: "NoData" }),                 // null height
    legacy({ name: "Tall", heightCm: 198 }),
    legacy({ name: "Mid", heightCm: 185 }),
  ];
  it("sorts desc with nulls last", () => {
    expect(sortByAxis(field, axis("heightCm"), "desc", "atp").map((p) => p.name))
      .toEqual(["Tall", "Mid", "Short", "NoData"]);
  });
  it("sorts asc with nulls STILL last", () => {
    expect(sortByAxis(field, axis("heightCm"), "asc", "atp").map((p) => p.name))
      .toEqual(["Short", "Mid", "Tall", "NoData"]);
  });
});
