import { describe, expect, it } from "vitest";
import { AGE_MAX, AGE_MIN, parseAgeFilter, passesAgeFilter, rankRows } from "@/lib/ui";

type Row = { name: string; age: number | null; elo: number; eloHard?: number };
const mk = (name: string, age: number | null, elo: number, eloHard = 0): Row => ({ name, age, elo, eloHard });

const under23 = { dir: "under" as const, value: 23 };

describe("parseAgeFilter", () => {
  it("returns no filter for 'all' mode regardless of the input", () => {
    expect(parseAgeFilter("all", "23")).toBeNull();
    expect(parseAgeFilter("all", "")).toBeNull();
  });

  it("returns no filter while the input is empty or non-numeric (mid-edit state)", () => {
    expect(parseAgeFilter("under", "")).toBeNull();
    expect(parseAgeFilter("under", "  ")).toBeNull();
    expect(parseAgeFilter("under", "abc")).toBeNull();
  });

  it("parses a direction + value", () => {
    expect(parseAgeFilter("under", "23")).toEqual({ dir: "under", value: 23 });
    expect(parseAgeFilter("over", "30")).toEqual({ dir: "over", value: 30 });
  });

  it("clamps out-of-range values and floors decimals", () => {
    expect(parseAgeFilter("under", "10")).toEqual({ dir: "under", value: AGE_MIN });
    expect(parseAgeFilter("over", "99")).toEqual({ dir: "over", value: AGE_MAX });
    expect(parseAgeFilter("under", "23.7")).toEqual({ dir: "under", value: 23 });
  });
});

describe("passesAgeFilter", () => {
  it("passes everyone (even unknown ages) when there is no filter", () => {
    expect(passesAgeFilter(31, null)).toBe(true);
    expect(passesAgeFilter(null, null)).toBe(true);
    expect(passesAgeFilter(undefined, null)).toBe(true);
  });

  it("excludes unknown ages under an active filter", () => {
    expect(passesAgeFilter(null, under23)).toBe(false);
    expect(passesAgeFilter(undefined, { dir: "over", value: 30 })).toBe(false);
  });

  it("is a strict less-than at the boundary (Under 23 means age < 23)", () => {
    expect(passesAgeFilter(22, under23)).toBe(true);
    expect(passesAgeFilter(23, under23)).toBe(false);
    expect(passesAgeFilter(24, under23)).toBe(false);
  });

  it("is a strict greater-than for 'over' (Over 30 means age > 30)", () => {
    expect(passesAgeFilter(31, { dir: "over", value: 30 })).toBe(true);
    expect(passesAgeFilter(30, { dir: "over", value: 30 })).toBe(false);
    expect(passesAgeFilter(29, { dir: "over", value: 30 })).toBe(false);
  });
});

describe("rankRows", () => {
  it("filters by age BEFORE slicing, so the table is the top-100 of the age group", () => {
    // 120 U23 players (elo 1000..1119) drowned out by 30 older, higher-rated players.
    const young = Array.from({ length: 120 }, (_, i) => mk(`Y${i}`, 20, 1000 + i));
    const old = Array.from({ length: 30 }, (_, i) => mk(`O${i}`, 30, 2000 + i));
    const rows = rankRows([...old, ...young], "elo", under23);

    expect(rows).toHaveLength(100); // still a full top-100 drawn from the group
    expect(rows.every((r) => r.age === 20)).toBe(true);
    expect(rows[0].elo).toBe(1119); // best of the age group leads
    expect(rows[99].elo).toBe(1020); // 100th of the age group, not of the whole field
  });

  it("supports the 'over' direction", () => {
    const rows = rankRows([mk("Vet", 35, 1500), mk("Kid", 19, 1600)], "elo", { dir: "over", value: 30 });
    expect(rows.map((r) => r.name)).toEqual(["Vet"]);
  });

  it("orders descending by the requested key", () => {
    const rows = rankRows([mk("A", 20, 1, 900), mk("B", 20, 2, 950), mk("C", 20, 3, 800)], "eloHard", null);
    expect(rows.map((r) => r.name)).toEqual(["B", "A", "C"]);
  });

  it("drops null-age players under a filter but keeps them for 'all ages'", () => {
    const data = [mk("Unknown", null, 1500), mk("Kid", 22, 1400)];
    expect(rankRows(data, "elo", under23).map((r) => r.name)).toEqual(["Kid"]);
    expect(rankRows(data, "elo", null).map((r) => r.name)).toEqual(["Unknown", "Kid"]);
  });

  it("does not mutate the input array", () => {
    const data = [mk("A", 20, 1), mk("B", 20, 2)];
    rankRows(data, "elo", null);
    expect(data.map((r) => r.name)).toEqual(["A", "B"]);
  });
});
