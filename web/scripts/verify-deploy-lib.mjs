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
