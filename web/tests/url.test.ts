import { describe, expect, it } from "vitest";
import { pairHref, playerHref, resolveTour, setSearchParam, setSearchTour, withTour } from "@/lib/url";

describe("resolveTour", () => {
  it("prefers a valid URL param over the saved preference", () => {
    expect(resolveTour("wta", "atp")).toBe("wta");
    expect(resolveTour("atp", "wta")).toBe("atp");
  });
  it("falls back to the saved preference, then atp", () => {
    expect(resolveTour(null, "wta")).toBe("wta");
    expect(resolveTour(null, null)).toBe("atp");
  });
  it("ignores invalid values at both levels", () => {
    expect(resolveTour("challenger", "junk")).toBe("atp");
    expect(resolveTour("", "wta")).toBe("wta");
  });
});

describe("setSearchParam / setSearchTour", () => {
  it("preserves unrelated params and accepts both ?-prefixed and bare strings", () => {
    expect(setSearchParam("?p=Iga+Swiatek", "sort", "elo")).toBe("?p=Iga+Swiatek&sort=elo");
    expect(setSearchParam("p=Iga+Swiatek", "sort", "elo")).toBe("?p=Iga+Swiatek&sort=elo");
  });
  it("deletes a key when value is null, collapsing to the empty string", () => {
    expect(setSearchParam("?tour=wta", "tour", null)).toBe("");
    expect(setSearchParam("?tour=wta&p=X", "tour", null)).toBe("?p=X");
  });
  it("elides the atp default and sets wta explicitly", () => {
    expect(setSearchTour("", "wta")).toBe("?tour=wta");
    expect(setSearchTour("?tour=wta", "atp")).toBe("");
    expect(setSearchTour("?p=X&tour=wta", "atp")).toBe("?p=X");
  });
});

describe("withTour", () => {
  it("appends ?tour=wta only for wta and preserves existing queries", () => {
    expect(withTour("/rankings", "atp")).toBe("/rankings");
    expect(withTour("/rankings", "wta")).toBe("/rankings?tour=wta");
    expect(withTour("/player/?p=X", "wta")).toBe("/player/?p=X&tour=wta");
  });
});

describe("playerHref / pairHref", () => {
  it("round-trips multi-word and diacritic names through URLSearchParams", () => {
    for (const name of ["Félix Auger-Aliassime", "Juan Martin del Potro", "Björn Borg"]) {
      const href = playerHref(name, "atp");
      expect(href.startsWith("/player/?")).toBe(true);
      const sp = new URLSearchParams(href.split("?")[1]);
      expect(sp.get("p")).toBe(name);
    }
  });
  it("carries the tour param only for wta", () => {
    expect(playerHref("Iga Swiatek", "wta")).toContain("tour=wta");
    expect(playerHref("Jannik Sinner", "atp")).not.toContain("tour=");
  });
  it("builds two-player links for style and predict", () => {
    const href = pairHref("/style/", "Aryna Sabalenka", "Iga Swiatek", "wta");
    const sp = new URLSearchParams(href.split("?")[1]);
    expect(href.startsWith("/style/?")).toBe(true);
    expect(sp.get("a")).toBe("Aryna Sabalenka");
    expect(sp.get("b")).toBe("Iga Swiatek");
    expect(sp.get("tour")).toBe("wta");
  });
});
