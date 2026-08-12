import { describe, expect, it } from "vitest";
import { filterResults, resultCounts } from "@/lib/results";

const rows = [
  { id: 1, upset: false },
  { id: 2, upset: true },
  { id: 3, upset: false },
];

describe("results filters", () => {
  it("reports mutually consistent counts", () => {
    expect(resultCounts(rows)).toEqual({ all: 3, called: 2, upsets: 1 });
  });

  it("filters called matches and upsets without changing the input", () => {
    expect(filterResults(rows, "called").map((row) => row.id)).toEqual([1, 3]);
    expect(filterResults(rows, "upsets").map((row) => row.id)).toEqual([2]);
    expect(rows).toHaveLength(3);
  });
});
