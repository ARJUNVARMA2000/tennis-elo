import { createElement as h } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import Dropdown, { filterOptions, moveActive, typeAheadIndex, type DropdownOption } from "@/components/Dropdown";

// The vitest environment is node (no jsdom/testing-library in the dependency
// tree), so interaction behavior is covered through the exported pure logic
// the component's handlers delegate to, plus SSR markup for the ARIA contract.

const opts = (...labels: string[]): DropdownOption[] => labels.map((l) => ({ value: l.toLowerCase(), label: l }));

describe("filterOptions (search filters options)", () => {
  const players = opts("Jannik Sinner", "Carlos Alcaraz", "Novak Djokovic");

  it("returns everything for an empty or whitespace query", () => {
    expect(filterOptions(players, "")).toHaveLength(3);
    expect(filterOptions(players, "   ")).toHaveLength(3);
  });

  it("matches case-insensitive substrings of the label", () => {
    expect(filterOptions(players, "sin").map((o) => o.label)).toEqual(["Jannik Sinner"]);
    expect(filterOptions(players, "ALCA").map((o) => o.label)).toEqual(["Carlos Alcaraz"]);
    expect(filterOptions(players, "ov").map((o) => o.label)).toEqual(["Novak Djokovic"]);
  });

  it("returns [] when nothing matches", () => {
    expect(filterOptions(players, "zzz")).toEqual([]);
  });
});

describe("moveActive (arrow-key navigation moves the highlighted option)", () => {
  it("ArrowDown from no highlight lands on the first option", () => {
    expect(moveActive(5, -1, "ArrowDown")).toBe(0);
  });

  it("ArrowDown steps forward and clamps at the end", () => {
    expect(moveActive(5, 1, "ArrowDown")).toBe(2);
    expect(moveActive(5, 4, "ArrowDown")).toBe(4);
  });

  it("ArrowUp from no highlight lands on the last option", () => {
    expect(moveActive(5, -1, "ArrowUp")).toBe(4);
  });

  it("ArrowUp steps back and clamps at the start", () => {
    expect(moveActive(5, 3, "ArrowUp")).toBe(2);
    expect(moveActive(5, 0, "ArrowUp")).toBe(0);
  });

  it("Home/End jump to the edges", () => {
    expect(moveActive(5, 3, "Home")).toBe(0);
    expect(moveActive(5, 1, "End")).toBe(4);
  });

  it("is -1 for an empty list regardless of key", () => {
    for (const k of ["ArrowDown", "ArrowUp", "Home", "End"]) expect(moveActive(0, 2, k)).toBe(-1);
  });

  it("ignores unrelated keys", () => {
    expect(moveActive(5, 2, "PageDown")).toBe(2);
  });
});

describe("typeAheadIndex (printable chars jump to a matching option)", () => {
  const labels = ["Alcaraz", "Brooksby", "Auger-Aliassime", "Bautista Agut"];

  it("finds the next prefix match scanning forward from `from`", () => {
    expect(typeAheadIndex(labels, "a", 0)).toBe(0);
    expect(typeAheadIndex(labels, "a", 1)).toBe(2); // skips Brooksby, lands on Auger
  });

  it("wraps past the end of the list", () => {
    expect(typeAheadIndex(labels, "a", 3)).toBe(0); // Bautista doesn't prefix-match "a"; wraps to Alcaraz
    expect(typeAheadIndex(labels, "b", 2)).toBe(3); // forward hit before wrapping
  });

  it("is case-insensitive and supports multi-char buffers", () => {
    expect(typeAheadIndex(labels, "AU", 0)).toBe(2);
    expect(typeAheadIndex(labels, "bau", 0)).toBe(3);
  });

  it("returns -1 for no match or empty buffer", () => {
    expect(typeAheadIndex(labels, "z", 0)).toBe(-1);
    expect(typeAheadIndex(labels, "", 0)).toBe(-1);
    expect(typeAheadIndex([], "a", 0)).toBe(-1);
  });
});

describe("Dropdown SSR markup (ARIA contract while closed)", () => {
  const players = opts("Jannik Sinner", "Carlos Alcaraz");

  it("renders a listbox trigger with the selected label", () => {
    const html = renderToStaticMarkup(
      h(Dropdown, { value: "jannik sinner", onChange: () => {}, options: players, label: "Player A" }),
    );
    expect(html).toContain('aria-haspopup="listbox"');
    expect(html).toContain('aria-expanded="false"');
    expect(html).toContain('aria-label="Player A"');
    expect(html).toContain("Jannik Sinner");
    expect(html).not.toContain('role="listbox"'); // panel closed until clicked
  });

  it("falls back to the placeholder when no option matches the value", () => {
    const html = renderToStaticMarkup(
      h(Dropdown, { value: "nobody", onChange: () => {}, options: players, placeholder: "Pick a player…" }),
    );
    expect(html).toContain("Pick a player…");
  });
});
