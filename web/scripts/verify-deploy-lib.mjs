// Pure, side-effect-free helpers for the post-deploy suite (verify-deploy.mjs).
// Kept in their own module so web/tests/verify-deploy.test.ts can unit-test them without
// importing the runnable (which would fire real network checks on import).

/**
 * Retry a rejected async operation a bounded number of times. HTTP responses are values, so
 * callers still fail 4xx/5xx immediately under their own serving-contract checks; this only
 * absorbs transport failures such as an aborted Firebase edge request.
 *
 * @template T
 * @param {() => Promise<T>} operation
 * @param {{attempts?: number, delayMs?: number, label?: string, sleep?: (ms: number) => Promise<void>}} options
 * @returns {Promise<T>}
 */
export async function retryRejected(operation, options = {}) {
  const attempts = Math.max(1, Math.trunc(Number(options.attempts) || 1));
  const delayMs = Math.max(0, Number(options.delayMs) || 0);
  const label = options.label || "operation";
  const sleep = options.sleep || ((ms) => new Promise((resolve) => setTimeout(resolve, ms)));
  let lastError;

  for (let attempt = 1; attempt <= attempts; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error;
      if (attempt < attempts) await sleep(delayMs);
    }
  }

  const detail = lastError?.message || String(lastError);
  throw new Error(`${label} failed after ${attempts} attempt${attempts === 1 ? "" : "s"}: ${detail}`,
    { cause: lastError });
}

/**
 * Fetch with a per-attempt timeout and bounded retries for rejected requests. Dependency
 * injection keeps the abort/recovery behavior deterministic under unit test.
 *
 * @param {string} url
 * @param {RequestInit} fetchOptions
 * @param {{attempts?: number, delayMs?: number, timeoutMs?: number, fetchImpl?: typeof fetch, sleep?: (ms: number) => Promise<void>}} retryOptions
 * @returns {Promise<Response>}
 */
export async function fetchWithRetry(url, fetchOptions = {}, retryOptions = {}) {
  const timeoutMs = Math.max(1, Number(retryOptions.timeoutMs) || 30000);
  const fetchImpl = retryOptions.fetchImpl || fetch;
  return retryRejected(async () => {
    const ac = new AbortController();
    const timer = setTimeout(() => ac.abort(), timeoutMs);
    try {
      return await fetchImpl(url, { ...fetchOptions, signal: ac.signal });
    } finally {
      clearTimeout(timer);
    }
  }, {
    attempts: retryOptions.attempts,
    delayMs: retryOptions.delayMs,
    label: `GET ${url}`,
    sleep: retryOptions.sleep,
  });
}

/**
 * Parse a Cache-Control header value into the flags the suite cares about.
 * @param {string|null|undefined} value
 * @returns {{immutable: boolean, mustRevalidate: boolean, noCache: boolean, noStore: boolean, maxAge: number|null}}
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
    noCache: tokens.includes("no-cache"),
    noStore: tokens.includes("no-store"),
    maxAge: Number.isFinite(maxAge) ? maxAge : null,
  };
}

/**
 * Mutable HTML/data must not be stored in either browsers or Firebase's CDN. A zero-age stored
 * response still creates a cache key and forces revalidation, which can itself become stuck.
 * @param {string|null|undefined} value
 */
export function mutableCacheControlOk(value) {
  const cc = parseCacheControl(value);
  return cc.noCache && cc.noStore;
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

/** Validate shard indexes before the verifier follows their references.
 * @param {object} matrix
 * @param {object} profiles
 * @param {object|null} scenarios
 */
export function artifactIndexRefs(matrix, profiles, scenarios = null) {
  const problems = [];
  const files = [];
  const safe = (value) => typeof value === "string"
    && /^[a-z0-9-]+\.json$/i.test(value)
    && !value.includes("..");
  if (!matrix || typeof matrix !== "object" || !matrix.generation) {
    problems.push("matrix-index generation missing");
  }
  for (const byFormat of Object.values(matrix?.surfaces || {})) {
    for (const file of Object.values(byFormat || {})) {
      if (!safe(file)) problems.push(`unsafe matrix shard reference ${String(file)}`);
      else files.push({ file, generation: matrix.generation, kind: "matrix" });
    }
  }
  if (!profiles || typeof profiles !== "object" || !profiles.generation) {
    problems.push("profile-index generation missing");
  }
  for (const profile of profiles?.profiles || []) {
    const file = profile?.file;
    if (!profile?.name || !safe(file)) problems.push(`invalid profile shard reference ${String(file)}`);
    else files.push({ file, generation: profiles.generation, kind: "profile", name: profile.name });
  }
  if (scenarios !== null) {
    if (!scenarios || typeof scenarios !== "object" || scenarios.schemaVersion !== 1 || !scenarios.generation) {
      problems.push("scenario-index schema/generation missing");
    }
    for (const event of scenarios?.events || []) {
      const file = event?.file;
      if (!event?.name || !safe(file)) problems.push(`invalid scenario shard reference ${String(file)}`);
      else files.push({ file, generation: scenarios.generation, kind: "scenario", name: event.name });
    }
  }
  if (!files.some((ref) => ref.kind === "matrix")) problems.push("matrix-index has no shards");
  if (!files.some((ref) => ref.kind === "profile")) problems.push("profile-index has no shards");
  const names = files.map((ref) => ref.file);
  if (new Set(names).size !== names.length) problems.push("duplicate shard reference");
  return { problems, files };
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
    'data-profile-contract="fail-closed-links+single-radar+mobile-contained+expectation-v3"',
  );
}

/**
 * The match-center route emits this marker only when eligible upcoming cards opt into the
 * shared whole-card Playing Style drill-in. The live gate catches an old route bundle after
 * deploy, while source/unit tests pin the rated-roster guard that keeps unavailable pairs plain.
 * @param {string} html
 */
export function hasMatchCenterContract(html) {
  return String(html || "").includes(
    'data-match-center-contract="upcoming-style-links+forecast-history+watch+evidence+live-dedupe-v4"',
  );
}

/** Both live-score surfaces emit this only when their scheduled rows share the browser-polled
 * live state and exclude exact event/player-pair overlaps. Checking both routes prevents a
 * partial deploy from repairing the match center while leaving the overview stale.
 * @param {string} html
 */
export function hasLiveScheduleContract(html) {
  return String(html || "").includes(
    'data-live-schedule-contract="exact-event-unordered-pair-v1"',
  );
}

/** Static route marker for the seven-group, explicitly non-causal model explanation. */
export function hasPredictionExplanationContract(html) {
  return String(html || "").includes(
    'data-prediction-explanation-contract="grouped-evidence-not-causation-v2"',
  );
}

/** Static route marker for the three-view exact bracket lab. */
export function hasBracketLabContract(html) {
  return String(html || "").includes(
    'data-bracket-lab-contract="actual+forecast+scenario-exact-v1"',
  );
}

/** Compact live-artifact arithmetic checks, complementary to the deep pre-upload gate. */
export function performanceArtifactProblems(performance) {
  if (!performance || typeof performance !== "object" || !Number.isInteger(performance.window)
      || !Array.isArray(performance.players)) return ["performance.json malformed"];
  const problems = [];
  const names = new Set();
  for (const row of performance.players) {
    if (!row?.name || names.has(row.name)) problems.push(`duplicate/missing performance player ${row?.name}`);
    names.add(row?.name);
    if (!Number.isInteger(row?.n) || row.n < 0 || row.n > performance.window
        || !Number.isInteger(row?.wins) || row.wins < 0 || row.wins > row.n
        || typeof row?.expectedWins !== "number" || row.expectedWins < 0 || row.expectedWins > row.n
        || typeof row?.delta !== "number" || Math.abs(row.delta - (row.wins - row.expectedWins)) > .002) {
      problems.push(`inconsistent performance summary ${row?.name}`);
    }
  }
  return problems;
}

/**
 * Validate the emitted global CSS contract that keeps the document element as the sole vertical
 * scroller. A body `overflow-x` scroll container plus body-level vertical overscroll containment
 * swallows wheel/trackpad deltas before they can chain to the document.
 *
 * @param {string|null|undefined} css
 * @returns {string[]}
 */
export function scrollShellProblems(css) {
  const compact = String(css || "")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/\s+/g, "")
    .toLowerCase();
  const blocks = (selector) => [
    ...compact.matchAll(new RegExp(`(?:^|[{}])${selector}\\{([^}]*)\\}`, "g")),
  ].map((match) => match[1]);
  const html = blocks("html");
  const body = blocks("body");
  const problems = [];

  if (!html.some((rule) => /(?:^|;)overflow-x:clip(?:;|$)/.test(rule))) {
    problems.push("html is missing overflow-x: clip");
  }
  if (body.some((rule) => /(?:^|;)overflow(?:-x)?:(hidden|auto|scroll)(?:;|$)/.test(rule))) {
    problems.push("body creates an overflow scroll container");
  }
  if (body.some((rule) => /(?:^|;)overscroll-behavior-y:(none|contain)(?:;|$)/.test(rule))) {
    problems.push("body blocks vertical overscroll chaining");
  }
  for (const rule of body) {
    const shorthand = rule.match(/(?:^|;)overscroll-behavior:([^;]+)(?:;|$)/)?.[1];
    if (!shorthand) continue;
    const values = shorthand.split(/\s+/);
    const vertical = values[1] ?? values[0];
    if (vertical === "none" || vertical === "contain") {
      problems.push("body blocks vertical overscroll chaining");
      break;
    }
  }
  return [...new Set(problems)];
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
 * Validate canonicals only for successfully fetched route HTML. Unavailable pages already fail
 * the route-serving check; treating their absent bodies as absent tags creates a second, false
 * diagnosis that obscures the transport failure.
 *
 * @param {Map<string, string>} routeHtml
 * @param {string} origin
 * @param {string[]} routes
 * @returns {{problems: string[], unavailable: string[]}}
 */
export function canonicalRouteProblems(routeHtml, origin, routes) {
  const problems = [];
  const unavailable = [];
  for (const route of routes) {
    if (!routeHtml.has(route)) {
      unavailable.push(route);
      continue;
    }
    const canonical = extractCanonical(routeHtml.get(route));
    const expected = new URL(route, origin).href;
    if (canonical !== expected) {
      problems.push(`${route} -> ${canonical || "missing"} (expected ${expected})`);
    }
  }
  return { problems, unavailable };
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
