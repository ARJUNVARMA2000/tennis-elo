import { describe, expect, it } from "vitest";

import { NAV_GROUPS } from "@/lib/navigation";

describe("forecast discovery navigation", () => {
  it("homes Brackets under Forecasts rather than Matches", () => {
    const matches = NAV_GROUPS.find((group) => group.label === "Matches");
    const forecasts = NAV_GROUPS.find((group) => group.label === "Forecasts");

    expect(matches?.items?.map((item) => item.label)).not.toContain("Brackets");
    expect(forecasts?.items?.[0]).toMatchObject({
      href: "/bracket",
      label: "Brackets",
    });
    expect(forecasts?.items?.[0].desc).toContain("what-if scenarios");
  });
});
