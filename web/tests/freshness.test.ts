import { describe, expect, it } from "vitest";
import { rel } from "@/components/Freshness";

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
