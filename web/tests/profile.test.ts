import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { CallCard } from "@/components/bits";
import {
  buildRadarScalers,
  profileRadarSeries,
  resolveProfileSelection,
  type RadarProfile,
} from "@/lib/profile";
import { RADAR_AXES } from "@/lib/ui";

const profile = (name: string, offset: number): RadarProfile => ({
  name,
  servePct: 0.55 + offset,
  returnPct: 0.35 + offset,
  eloHard: 1500 + offset * 1000,
  eloClay: 1450 + offset * 1000,
  eloGrass: 1400 + offset * 1000,
  style: Object.fromEntries(
    RADAR_AXES.filter((axis) => axis.source === "style").map((axis, i) => [axis.key, i / 10 + offset]),
  ),
});

describe("profile selection", () => {
  it("never substitutes the top player for an invalid explicit ?p=", () => {
    const names = ["Jannik Sinner", "Carlos Alcaraz"];
    expect(resolveProfileSelection(names, "Cruz Hewitt", "Jannik Sinner")).toBe("");
    expect(resolveProfileSelection(names, "Carlos Alcaraz", "")).toBe("Carlos Alcaraz");
    expect(resolveProfileSelection(names, null, "")).toBe("Jannik Sinner");
  });
});

describe("profile-aware match-card links", () => {
  it("renders an unavailable player as plain text while keeping an available profile linked", () => {
    const html = renderToStaticMarkup(createElement(CallCard, {
      surface: "Hard",
      meta: "R32",
      top: { name: "Cruz Hewitt", prob: 0.25, won: false },
      bottom: { name: "Jannik Sinner", prob: 0.75, won: true },
      profileRoster: new Set(["Jannik Sinner"]),
    }));

    expect(html).toContain("Cruz Hewitt");
    expect(html).not.toMatch(/href="[^"]*Cruz\+Hewitt/);
    expect(html).toMatch(/href="[^"]*Jannik\+Sinner/);
  });
});

describe("single-player style radar", () => {
  it("builds one 13-axis percentile series from the same tour field as comparison", () => {
    const field = [profile("Lower", 0), profile("Jessica Pegula", 0.1), profile("Higher", 0.2)];
    const scalers = buildRadarScalers(field);
    const series = profileRadarSeries(field[1], scalers, "var(--color-accent)");

    expect(scalers).toHaveLength(13);
    expect(series).toHaveLength(1);
    expect(series[0].name).toBe("Jessica Pegula");
    expect(series[0].values).toHaveLength(13);
    expect(series[0].values.every((value) => value === 0.5)).toBe(true);
  });
});
