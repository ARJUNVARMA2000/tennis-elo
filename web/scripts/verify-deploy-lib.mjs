// Pure, side-effect-free helpers for the post-deploy suite (verify-deploy.mjs).
// Kept in their own module so web/tests/verify-deploy.test.ts can unit-test them without
// importing the runnable (which would fire real network checks on import).

/**
 * Parse a Cache-Control header value into the flags the suite cares about.
 * @param {string|null|undefined} value
 * @returns {{immutable: boolean, mustRevalidate: boolean, maxAge: number|null}}
 */
export function parseCacheControl(value) {
  const tokens = String(value || "")
    .toLowerCase()
    .split(",")
    .map((t) => t.trim());
  const maxAgeTok = tokens.find((t) => t.startsWith("max-age="));
  const maxAge = maxAgeTok ? Number(maxAgeTok.slice("max-age=".length)) : null;
  return {
    immutable: tokens.includes("immutable"),
    mustRevalidate: tokens.includes("must-revalidate"),
    maxAge: Number.isFinite(maxAge) ? maxAge : null,
  };
}

/**
 * The substring a correct Content-Type should contain for a given path. Deliberately loose
 * (substring, not exact) so `text/javascript` and `application/javascript` both pass — the
 * failure we actually guard against is a static asset falling through to `text/html`.
 * @param {string} path
 * @returns {"javascript"|"css"|"json"|"html"}
 */
export function expectedMimeFor(path) {
  const clean = String(path).split(/[?#]/)[0];
  if (clean.endsWith(".js") || clean.endsWith(".mjs")) return "javascript";
  if (clean.endsWith(".css")) return "css";
  if (clean.endsWith(".json")) return "json";
  return "html";
}

/**
 * True if `actual` Content-Type is right for `path`.
 * @param {string|null|undefined} actual
 * @param {string} path
 */
export function contentTypeOk(actual, path) {
  return String(actual || "").toLowerCase().includes(expectedMimeFor(path));
}

/**
 * First content-hashed asset of the given extension referenced in a page's HTML, or null.
 * Next emits these under /_next/static/…; they're the only files safe to cache immutably.
 * @param {string} html
 * @param {"js"|"css"} ext
 * @returns {string|null}
 */
export function extractHashedAsset(html, ext) {
  const re = new RegExp(`/_next/static/[^"'()\\s]+\\.${ext}\\b`);
  const m = String(html || "").match(re);
  return m ? m[0] : null;
}

/**
 * True if `url` is an absolute URL on `origin` (e.g. og:image must not be root-relative or
 * point at a stale host after a SITE_URL change).
 * @param {string} url
 * @param {string} origin  e.g. "https://deuce-forecast.web.app"
 */
export function isAbsoluteOnOrigin(url, origin) {
  if (typeof url !== "string" || !url) return false;
  return url === origin || url.startsWith(origin + "/");
}

/**
 * Freshness verdict for the live health.json stamp. When an expected value is supplied
 * (CI passes the just-built artifact's generatedAt), require an exact match; otherwise just
 * require a non-empty stamp (best-effort for ad-hoc local runs).
 * @param {string|null|undefined} live
 * @param {string|null|undefined} expected
 */
export function freshnessOk(live, expected) {
  if (!expected) return Boolean(live);
  return live === expected;
}

/**
 * True when the deployed health artifact has a usable freshness stamp. `ok` is deliberately
 * not part of this contract: it also carries advisory data findings that do not mean the
 * deployed files are stale or incorrectly served.
 * @param {object|null|undefined} health
 * @param {string|null|undefined} expected
 */
export function healthArtifactOk(health, expected) {
  return Boolean(health && typeof health === "object" && !Array.isArray(health)
    && freshnessOk(health.generatedAt, expected));
}

/**
 * Compare one live tournaments.json payload with the membership recorded by the same
 * freshly-built health.json. Expected keys must occur exactly once; the complete shipped
 * multiset must also match so a CDN mix of old/new per-tour files cannot pass.
 * @param {object} health
 * @param {string} tour
 * @param {Array<object>} tournaments
 * @returns {string[]}
 */
export function coverageProblems(health, tour, tournaments) {
  const summary = health?.eventCoverage?.[tour];
  if (!summary || !Array.isArray(summary.expectedKeys) || !Array.isArray(summary.shippedKeys)) {
    return [`${tour}: health.json eventCoverage summary missing/malformed`];
  }
  if (!Array.isArray(tournaments)) return [`${tour}: tournaments.json is not an array`];

  const keys = tournaments.map((card) => card?.coverageKey).filter(Boolean).map(String);
  const counts = new Map();
  for (const key of keys) counts.set(key, (counts.get(key) || 0) + 1);
  const problems = [];
  const unnamed = tournaments.length - keys.length;
  if (unnamed) problems.push(`${tour}: ${unnamed} card(s) missing coverageKey`);
  for (const key of summary.expectedKeys.map(String)) {
    const count = counts.get(key) || 0;
    if (count === 0) problems.push(`${tour}: missing expected ${key}`);
    else if (count > 1) problems.push(`${tour}: duplicate ${key} (${count} cards)`);
  }
  const expectedMembership = [...summary.shippedKeys].map(String).sort();
  const actualMembership = [...keys].sort();
  if (JSON.stringify(actualMembership) !== JSON.stringify(expectedMembership)) {
    problems.push(`${tour}: tournament membership differs from freshly built health.json`);
  }
  return problems;
}

/**
 * The player route emits this marker only when its UI contract includes both parts of the
 * user-facing repair: unavailable profile names fail closed, and dossiers contain the shared
 * single-player radar. The live gate catches a stale/partial deploy serving the old route.
 * @param {string} html
 */
export function hasProfileContract(html) {
  return String(html || "").includes(
    'data-profile-contract="fail-closed-links+single-radar-v1"',
  );
}

/**
 * Pull the og:image content value out of a page's HTML (order-insensitive on attributes).
 * @param {string} html
 * @returns {string|null}
 */
export function extractOgImage(html) {
  const s = String(html || "");
  // property before content
  let m = s.match(/<meta[^>]+property=["']og:image["'][^>]*\scontent=["']([^"']+)["']/i);
  if (m) return m[1];
  // content before property
  m = s.match(/<meta[^>]+content=["']([^"']+)["'][^>]*\sproperty=["']og:image["']/i);
  return m ? m[1] : null;
}

/**
 * Pull the canonical URL out of a page's HTML (order-insensitive on attributes).
 * @param {string} html
 * @returns {string|null}
 */
export function extractCanonical(html) {
  const s = String(html || "");
  let m = s.match(/<link[^>]+rel=["']canonical["'][^>]*\shref=["']([^"']+)["']/i);
  if (m) return m[1];
  m = s.match(/<link[^>]+href=["']([^"']+)["'][^>]*\srel=["']canonical["']/i);
  return m ? m[1] : null;
}

/**
 * Pull the Google Search Console ownership token from a page's HTML.
 * @param {string} html
 * @returns {string|null}
 */
export function extractGoogleSiteVerification(html) {
  const s = String(html || "");
  let m = s.match(
    /<meta[^>]+name=["']google-site-verification["'][^>]*\scontent=["']([^"']+)["']/i,
  );
  if (m) return m[1];
  m = s.match(
    /<meta[^>]+content=["']([^"']+)["'][^>]*\sname=["']google-site-verification["']/i,
  );
  return m ? m[1] : null;
}

/**
 * Compare a sitemap's absolute URLs with the complete intended route inventory.
 * @param {string} xml
 * @param {string} origin
 * @param {string[]} expectedRoutes
 * @returns {string[]}
 */
export function sitemapCoverageProblems(xml, origin, expectedRoutes) {
  const locations = [...String(xml || "").matchAll(/<loc>\s*([^<]+?)\s*<\/loc>/gi)]
    .map((match) => match[1]);
  const expected = new Set(expectedRoutes);
  const counts = new Map();
  const problems = [];

  for (const location of locations) {
    let parsed;
    try {
      parsed = new URL(location);
    } catch {
      problems.push(`malformed ${location}`);
      continue;
    }
    if (parsed.origin !== origin) {
      problems.push(`off-origin ${location}`);
      continue;
    }
    const route = parsed.pathname;
    counts.set(route, (counts.get(route) || 0) + 1);
    if (!expected.has(route)) problems.push(`unexpected ${route}`);
  }

  for (const route of expectedRoutes) {
    const count = counts.get(route) || 0;
    if (count === 0) problems.push(`missing ${route}`);
    else if (count > 1) problems.push(`duplicate ${route}`);
  }
  return problems;
}
