import { describe, expect, it } from "vitest";

import { NAV_GROUPS, NAV_ITEMS, sectionForPath } from "@/lib/navigation";

describe("forecast discovery navigation", () => {
  it("keeps old destinations searchable within their consolidated section", () => {
    expect(NAV_GROUPS.find((group) => group.label === "Matches")?.href).toBe("/matches");
    for (const path of ["/schedule", "/results"]) {
      expect(sectionForPath(`${path}/`)?.label).toBe("Matches");
      expect(NAV_ITEMS.some((item) => item.href === path)).toBe(true);
    }
    for (const path of ["/accuracy", "/track", "/scorecard"]) expect(sectionForPath(path)?.label).toBe("Performance");
    expect(sectionForPath("/player/")).toBeUndefined();
    expect(new Set(NAV_ITEMS.map((item) => item.href)).size).toBe(NAV_ITEMS.length);
  });
  it("homes Brackets under Forecasts rather than Matches", () => {
    const matches = NAV_GROUPS.find((group) => group.label === "Matches");
    const forecasts = NAV_GROUPS.find((group) => group.label === "Forecasts");

    expect(matches?.items?.map((item) => item.label) ?? []).not.toContain("Brackets");
    expect(forecasts?.items?.[0]).toMatchObject({
      href: "/bracket",
      label: "Brackets",
    });
    expect(forecasts?.items?.[0].desc).toContain("what-if scenarios");
  });
});
