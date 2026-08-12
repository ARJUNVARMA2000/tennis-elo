import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";
import {
  parseCacheControl,
  expectedMimeFor,
  contentTypeOk,
  extractHashedAsset,
  isAbsoluteOnOrigin,
  freshnessOk,
  healthArtifactOk,
  extractOgImage,
  extractCanonical,
  extractGoogleSiteVerification,
  sitemapCoverageProblems,
  coverageProblems,
  hasProfileContract,
  canonicalRouteProblems,
  fetchWithRetry,
  mutableCacheControlOk,
} from "@/scripts/verify-deploy-lib.mjs";

describe("fetchWithRetry", () => {
  it("recovers from a transient aborted request", async () => {
    let calls = 0;
    const sleeps: number[] = [];
    const response = await fetchWithRetry("https://example.com/schedule/", {}, {
      attempts: 2,
      delayMs: 7,
      timeoutMs: 100,
      fetchImpl: async () => {
        calls += 1;
        if (calls === 1) throw new DOMException("This operation was aborted", "AbortError");
        return new Response("ok");
      },
      sleep: async (ms) => { sleeps.push(ms); },
    });

    expect(await response.text()).toBe("ok");
    expect(calls).toBe(2);
    expect(sleeps).toEqual([7]);
  });

  it("reports the URL and attempt count when retries are exhausted", async () => {
    let calls = 0;
    await expect(fetchWithRetry("https://example.com/schedule/", {}, {
      attempts: 2,
      timeoutMs: 100,
      fetchImpl: async () => {
        calls += 1;
        throw new DOMException("This operation was aborted", "AbortError");
      },
      sleep: async () => {},
    })).rejects.toThrow(
      "GET https://example.com/schedule/ failed after 2 attempts: This operation was aborted",
    );
    expect(calls).toBe(2);
  });
});

describe("parseCacheControl", () => {
  it("flags immutable + long max-age (hashed static assets)", () => {
    const cc = parseCacheControl("public, max-age=31536000, immutable");
    expect(cc.immutable).toBe(true);
    expect(cc.mustRevalidate).toBe(false);
    expect(cc.noCache).toBe(false);
    expect(cc.noStore).toBe(false);
    expect(cc.maxAge).toBe(31536000);
  });
  it("flags no-cache + no-store (mutable data + HTML)", () => {
    const cc = parseCacheControl("no-cache, no-store");
    expect(cc.noCache).toBe(true);
    expect(cc.noStore).toBe(true);
    expect(cc.immutable).toBe(false);
    expect(cc.maxAge).toBeNull();
  });
  it("is case- and whitespace-insensitive and tolerates null", () => {
    expect(parseCacheControl("  PUBLIC,  IMMUTABLE ").immutable).toBe(true);
    expect(parseCacheControl(null)).toEqual({
      immutable: false,
      mustRevalidate: false,
      noCache: false,
      noStore: false,
      maxAge: null,
    });
  });
});

describe("mutableCacheControlOk", () => {
  it("requires the documented non-storage pair", () => {
    expect(mutableCacheControlOk("no-cache, no-store")).toBe(true);
    expect(mutableCacheControlOk("no-store")).toBe(false);
    expect(mutableCacheControlOk("no-cache")).toBe(false);
  });

  it("rejects the zero-age stored policy that produced stuck CDN keys", () => {
    expect(mutableCacheControlOk("public, max-age=0, must-revalidate")).toBe(false);
  });
});

describe("Firebase Hosting cache configuration", () => {
  it("does not store mutable content and keeps only hashed assets immutable", () => {
    const config = JSON.parse(readFileSync(new URL("../../firebase.json", import.meta.url), "utf8"));
    const rules = config.hosting.headers;
    expect(rules).toEqual([
      {
        source: "**",
        headers: [{ key: "Cache-Control", value: "no-cache, no-store" }],
      },
      {
        source: "/_next/static/**",
        headers: [{ key: "Cache-Control", value: "public, max-age=31536000, immutable" }],
      },
    ]);
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

describe("healthArtifactOk", () => {
  it("accepts a fresh artifact even when data health has advisory findings", () => {
    expect(healthArtifactOk({ generatedAt: "2026-07-17T20:12:17Z", ok: false },
      "2026-07-17T20:12:17Z")).toBe(true);
  });
  it("rejects missing or stale artifact stamps", () => {
    expect(healthArtifactOk({ ok: true }, "2026-07-17T20:12:17Z")).toBe(false);
    expect(healthArtifactOk({ generatedAt: "old", ok: true },
      "2026-07-17T20:12:17Z")).toBe(false);
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

describe("extractCanonical", () => {
  it("handles both attribute orders", () => {
    expect(
      extractCanonical(`<link rel="canonical" href="https://example.com/method/"/>`),
    ).toBe("https://example.com/method/");
    expect(
      extractCanonical(`<link href="https://example.com/method/" rel="canonical"/>`),
    ).toBe("https://example.com/method/");
  });

  it("returns null when no canonical exists", () => {
    expect(extractCanonical(`<link rel="icon" href="/icon.svg"/>`)).toBeNull();
  });
});

describe("canonicalRouteProblems", () => {
  const origin = "https://example.com";

  it("does not fabricate missing-tag failures for route HTML that was unavailable", () => {
    const html = new Map([
      ["/", `<link rel="canonical" href="${origin}/"/>`],
    ]);
    expect(canonicalRouteProblems(html, origin, ["/", "/schedule/", "/method/"])).toEqual({
      problems: [],
      unavailable: ["/schedule/", "/method/"],
    });
  });

  it("still fails a genuine missing or incorrect canonical in available HTML", () => {
    const html = new Map([
      ["/schedule/", "<title>Schedule</title>"],
      ["/method/", `<link rel="canonical" href="${origin}/wrong/"/>`],
    ]);
    const result = canonicalRouteProblems(html, origin, ["/schedule/", "/method/"]);
    expect(result.unavailable).toEqual([]);
    expect(result.problems).toEqual([
      `/schedule/ -> missing (expected ${origin}/schedule/)`,
      `/method/ -> ${origin}/wrong/ (expected ${origin}/method/)`,
    ]);
  });
});

describe("extractGoogleSiteVerification", () => {
  it("handles both attribute orders", () => {
    expect(
      extractGoogleSiteVerification(
        `<meta name="google-site-verification" content="verification-token"/>`,
      ),
    ).toBe("verification-token");
    expect(
      extractGoogleSiteVerification(
        `<meta content="verification-token" name="google-site-verification"/>`,
      ),
    ).toBe("verification-token");
  });

  it("returns null when the verification tag is absent", () => {
    expect(extractGoogleSiteVerification(`<meta name="description" content="DEUCE"/>`)).toBeNull();
  });
});

describe("sitemapCoverageProblems", () => {
  const origin = "https://deuce-forecast.web.app";
  const routes = ["/", "/rankings/", "/method/"];

  it("accepts the exact canonical route set", () => {
    const xml = `<?xml version="1.0"?><urlset>
      <url><loc>${origin}/</loc></url>
      <url><loc>${origin}/rankings/</loc></url>
      <url><loc>${origin}/method/</loc></url>
    </urlset>`;
    expect(sitemapCoverageProblems(xml, origin, routes)).toEqual([]);
  });

  it("reports missing, duplicate, off-origin, and unexpected URLs", () => {
    const xml = `<urlset>
      <url><loc>${origin}/</loc></url>
      <url><loc>${origin}/</loc></url>
      <url><loc>https://old.example/rankings/</loc></url>
      <url><loc>${origin}/health/</loc></url>
    </urlset>`;
    const problems = sitemapCoverageProblems(xml, origin, routes).join("; ");
    expect(problems).toContain("duplicate /");
    expect(problems).toContain("off-origin https://old.example/rankings/");
    expect(problems).toContain("unexpected /health/");
    expect(problems).toContain("missing /rankings/");
    expect(problems).toContain("missing /method/");
  });
});

describe("coverageProblems", () => {
  const health = {
    eventCoverage: {
      atp: {
        expectedKeys: ["espn:1-2026", "espn:2-2026"],
        shippedKeys: ["espn:1-2026", "espn:2-2026", "card:recent"],
      },
    },
  };

  it("accepts the exact freshly-built tournament membership", () => {
    const cards = [
      { name: "One", coverageKey: "espn:1-2026" },
      { name: "Two", coverageKey: "espn:2-2026" },
      { name: "Recent", coverageKey: "card:recent" },
    ];
    expect(coverageProblems(health, "atp", cards)).toEqual([]);
  });

  it("reports a missing begun event, a duplicate, and a stale extra card", () => {
    const cards = [
      { name: "One", coverageKey: "espn:1-2026" },
      { name: "One Again", coverageKey: "espn:1-2026" },
      { name: "Stale", coverageKey: "card:stale" },
    ];
    const problems = coverageProblems(health, "atp", cards).join("; ");
    expect(problems).toContain("missing expected espn:2-2026");
    expect(problems).toContain("duplicate espn:1-2026");
    expect(problems).toContain("membership differs");
  });
});

describe("hasProfileContract", () => {
  it("requires the deployed player page to advertise fail-closed links and the dossier radar", () => {
    expect(hasProfileContract(
      `<main><div data-profile-contract="fail-closed-links+single-radar-v1"></div></main>`,
    )).toBe(true);
    expect(hasProfileContract(`<main><div class="profiles"></div></main>`)).toBe(false);
    expect(hasProfileContract(
      `<div data-profile-contract="fail-open-links+single-radar-v1"></div>`,
    )).toBe(false);
  });
});
