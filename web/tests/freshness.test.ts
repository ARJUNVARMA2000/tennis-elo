import { describe, expect, it } from "vitest";
import { AGING_H, STALE_H, rel, staleness } from "@/components/Freshness";

// `rel` is a pure function; the component's "use client" directive is inert
// under node vitest, so importing it here is safe.

const NOW = Date.parse("2026-07-01T12:00:00Z");
const minsAgo = (m: number) => new Date(NOW - m * 60_000).toISOString();

describe("rel", () => {
  it("clamps anything under a minute to '<1m ago'", () => {
    expect(rel(minsAgo(0), NOW)).toBe("<1m ago");
    expect(rel(new Date(NOW - 30_000).toISOString(), NOW)).toBe("<1m ago");
  });

  it("uses minutes below an hour", () => {
    expect(rel(minsAgo(59), NOW)).toBe("59m ago");
  });

  it("uses hours from 1h up to 47h", () => {
    expect(rel(minsAgo(60), NOW)).toBe("1h ago");
    expect(rel(minsAgo(47 * 60), NOW)).toBe("47h ago");
  });

  it("switches to days at 48h", () => {
    expect(rel(minsAgo(48 * 60), NOW)).toBe("2d ago");
  });

  it("returns null for an unparseable timestamp", () => {
    expect(rel("not-a-date", NOW)).toBeNull();
  });

  it("clamps future timestamps to '<1m ago'", () => {
    expect(rel(new Date(NOW + 5 * 60_000).toISOString(), NOW)).toBe("<1m ago");
  });
});

describe("staleness", () => {
  it("is fresh below the aging threshold", () => {
    expect(staleness(minsAgo(0), NOW)).toBe("fresh");
    expect(staleness(minsAgo(AGING_H * 60 - 1), NOW)).toBe("fresh");
  });

  it("ages once several hourly refreshes are missed", () => {
    expect(staleness(minsAgo(AGING_H * 60), NOW)).toBe("aging");
    expect(staleness(minsAgo(STALE_H * 60 - 1), NOW)).toBe("aging");
  });

  it("is stale once the daily full run is missed", () => {
    expect(staleness(minsAgo(STALE_H * 60), NOW)).toBe("stale");
    expect(staleness(minsAgo(72 * 60), NOW)).toBe("stale");
  });

  it("returns null for an unparseable timestamp", () => {
    expect(staleness("not-a-date", NOW)).toBeNull();
  });
});
