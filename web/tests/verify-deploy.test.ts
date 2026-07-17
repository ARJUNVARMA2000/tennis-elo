import { describe, expect, it } from "vitest";
import {
  parseCacheControl,
  expectedMimeFor,
  contentTypeOk,
  extractHashedAsset,
  isAbsoluteOnOrigin,
  freshnessOk,
  extractOgImage,
} from "@/scripts/verify-deploy-lib.mjs";

describe("parseCacheControl", () => {
  it("flags immutable + long max-age (hashed static assets)", () => {
    const cc = parseCacheControl("public, max-age=31536000, immutable");
    expect(cc.immutable).toBe(true);
    expect(cc.mustRevalidate).toBe(false);
    expect(cc.maxAge).toBe(31536000);
  });
  it("flags must-revalidate (data + HTML)", () => {
    const cc = parseCacheControl("public, max-age=0, must-revalidate");
    expect(cc.mustRevalidate).toBe(true);
    expect(cc.immutable).toBe(false);
    expect(cc.maxAge).toBe(0);
  });
  it("is case- and whitespace-insensitive and tolerates null", () => {
    expect(parseCacheControl("  PUBLIC,  IMMUTABLE ").immutable).toBe(true);
    expect(parseCacheControl(null)).toEqual({ immutable: false, mustRevalidate: false, maxAge: null });
  });
});

describe("expectedMimeFor", () => {
  it("maps extensions, stripping query/hash", () => {
    expect(expectedMimeFor("/_next/static/x.js")).toBe("javascript");
    expect(expectedMimeFor("/x.mjs")).toBe("javascript");
    expect(expectedMimeFor("/_next/static/x.css?v=1")).toBe("css");
    expect(expectedMimeFor("/data/health.json")).toBe("json");
  });
  it("treats routes (and trailing-slash paths) as html", () => {
    expect(expectedMimeFor("/")).toBe("html");
    expect(expectedMimeFor("/method/")).toBe("html");
  });
});

describe("contentTypeOk", () => {
  it("accepts either javascript spelling but rejects html fall-through", () => {
    expect(contentTypeOk("text/javascript; charset=utf-8", "/a.js")).toBe(true);
    expect(contentTypeOk("application/javascript", "/a.js")).toBe(true);
    // the classic Firebase misconfig: a static asset served as the SPA index
    expect(contentTypeOk("text/html; charset=utf-8", "/a.js")).toBe(false);
  });
  it("checks css and json", () => {
    expect(contentTypeOk("text/css", "/a.css")).toBe(true);
    expect(contentTypeOk("application/json", "/data/health.json")).toBe(true);
    expect(contentTypeOk("text/html", "/data/health.json")).toBe(false);
  });
});

describe("extractHashedAsset", () => {
  const html = `<link rel="stylesheet" href="/_next/static/chunks/3aeqklwtw9sws.css"/>` +
    `<script src="/_next/static/chunks/10qk6v6416kh8.js"></script>`;
  it("finds the first js and css under /_next/static", () => {
    expect(extractHashedAsset(html, "js")).toBe("/_next/static/chunks/10qk6v6416kh8.js");
    expect(extractHashedAsset(html, "css")).toBe("/_next/static/chunks/3aeqklwtw9sws.css");
  });
  it("returns null when absent or html is empty", () => {
    expect(extractHashedAsset("<p>no assets</p>", "js")).toBeNull();
    expect(extractHashedAsset("", "css")).toBeNull();
  });
});

describe("isAbsoluteOnOrigin", () => {
  const origin = "https://deuce-forecast.web.app";
  it("accepts absolute URLs on the origin", () => {
    expect(isAbsoluteOnOrigin("https://deuce-forecast.web.app/og.png", origin)).toBe(true);
    expect(isAbsoluteOnOrigin(origin, origin)).toBe(true);
  });
  it("rejects root-relative and other-origin (catches a SITE_URL regression)", () => {
    expect(isAbsoluteOnOrigin("/og.png", origin)).toBe(false);
    expect(isAbsoluteOnOrigin("https://arjunvarma2000.github.io/tennis-elo/og.png", origin)).toBe(false);
    expect(isAbsoluteOnOrigin("", origin)).toBe(false);
  });
});

describe("freshnessOk", () => {
  it("requires an exact match when an expected stamp is supplied", () => {
    expect(freshnessOk("2026-07-17T20:12:17Z", "2026-07-17T20:12:17Z")).toBe(true);
    expect(freshnessOk("2026-07-17T19:00:00Z", "2026-07-17T20:12:17Z")).toBe(false);
  });
  it("falls back to a presence check when no expected stamp is given", () => {
    expect(freshnessOk("2026-07-17T20:12:17Z", "")).toBe(true);
    expect(freshnessOk("", "")).toBe(false);
    expect(freshnessOk(null, undefined)).toBe(false);
  });
});

describe("extractOgImage", () => {
  it("handles both attribute orders", () => {
    expect(
      extractOgImage(`<meta property="og:image" content="https://x/og.png"/>`),
    ).toBe("https://x/og.png");
    expect(
      extractOgImage(`<meta content="https://x/og.png" property="og:image"/>`),
    ).toBe("https://x/og.png");
  });
  it("returns null when there is no og:image", () => {
    expect(extractOgImage(`<meta name="twitter:card" content="summary"/>`)).toBeNull();
  });
});
