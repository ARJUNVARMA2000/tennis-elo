import { describe, expect, it } from "vitest";
import { calibrationInterval } from "@/lib/calibration";

describe("descriptive calibration intervals", () => {
  it("retains uncertainty at zero and one, and narrows with more evidence", () => {
    expect(calibrationInterval(0, 10)![1]).toBeCloseTo(0.277533, 5);
    expect(calibrationInterval(1, 10)![0]).toBeCloseTo(0.722467, 5);
    const small = calibrationInterval(0.5, 10)!;
    const large = calibrationInterval(0.5, 1000)!;
    expect(small[0]).toBeLessThan(large[0]);
    expect(small[1]).toBeGreaterThan(large[1]);
    expect(large[0] + large[1]).toBeCloseTo(1);
  });
  it("withholds intervals for empty or malformed bins", () => {
    for (const [rate, n] of [[0.5, 0], [0.5, -1], [0.5, 2.5], [NaN, 20], [1.01, 20], [-0.1, 20]]) {
      expect(calibrationInterval(rate, n)).toBeNull();
    }
  });
});
