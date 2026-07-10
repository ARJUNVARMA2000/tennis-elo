import { describe, expect, it } from "vitest";
import { fmt, kAt } from "@/lib/method";

describe("fmt", () => {
  it("drops a trailing .0 from whole-number floats", () => {
    expect(fmt(145.0)).toBe("145");
    expect(fmt(400)).toBe("400");
    expect(fmt(2010)).toBe("2010");
  });

  it("keeps real decimals verbatim", () => {
    expect(fmt(0.21)).toBe("0.21");
    expect(fmt(0.63)).toBe("0.63");
    expect(fmt(1.28)).toBe("1.28");
  });

  it("strips accumulated float noise (the tier-anchor rescale)", () => {
    expect(fmt(0.8920000000000001)).toBe("0.892");
    expect(fmt(1.1379999999999999)).toBe("1.138");
  });

  it("never renders exponent notation for small hyperparameters", () => {
    expect(fmt(0.0005)).toBe("0.0005"); // WTA xgb gamma
    expect(fmt(5e-7)).toBe("0.0000005");
  });

  it("handles negatives and non-finite input", () => {
    expect(fmt(-0.5)).toBe("-0.5");
    expect(fmt(NaN)).toBe("—");
    expect(fmt(Infinity)).toBe("—");
  });
});

describe("kAt", () => {
  it("matches hand-computed dynamic-K values", () => {
    // shared defaults K = 250/(n+5)^0.4 (the FiveThirtyEight functional form)
    expect(kAt(250, 5, 0.4, 0)).toBe(Math.round((250 / Math.pow(5, 0.4)) * 10) / 10);
    expect(kAt(250, 5, 0.4, 95)).toBe(39.6); // 250/100^0.4 = 250/10^0.8 ≈ 39.62
    // ATP production curve K = 145/(n+5)^0.21
    expect(kAt(145, 5, 0.21, 10)).toBe(Math.round((145 / Math.pow(15, 0.21)) * 10) / 10);
  });

  it("is monotonically decreasing in career matches", () => {
    const ks = [0, 10, 100, 1000].map((n) => kAt(145, 5, 0.21, n));
    for (let i = 1; i < ks.length; i++) expect(ks[i]).toBeLessThan(ks[i - 1]);
  });
});
