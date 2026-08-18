// Post-deploy verification suite for the LIVE Firebase site — the serving-side analogue of
// the pre-deploy `health.py --gate` (which only sees local JSON). Catches the Firebase
// failure class that only shows up against the deployed URL: a "successful" deploy whose CDN
// still serves old content, a cache-header regression, MIME fall-through to index.html,
// trailingSlash/404 misbehaviour, or a SITE_URL/basePath regression baked into the HTML.
//
// Fetch-based — no browser, so it runs on any CI Node (the browser check stays in verify.mjs).
//
// Usage:
//   node scripts/verify-deploy.mjs [--base <url>] [--expect-generated-at <iso>]
//   VERIFY_BASE_URL=... EXPECT_GENERATED_AT=... npm run verify:deploy
// Exits non-zero if any check fails, so it can gate/alert in the workflow.
import { INDEXABLE_ROUTES, ROUTES } from "./routes.mjs";
import {
  parseCacheControl,
  contentTypeOk,
  extractHashedAsset,
  isAbsoluteOnOrigin,
  coverageProblems,
  extractOgImage,
  canonicalRouteProblems,
  extractGoogleSiteVerification,
  sitemapCoverageProblems,
  hasProfileContract,
  hasMatchCenterContract,
  hasPredictionExplanationContract,
  hasBracketLabContract,
  performanceArtifactProblems,
  scrollShellProblems,
  healthArtifactOk,
  artifactIndexRefs,
  fetchWithRetry,
  mutableCacheControlOk,
} from "./verify-deploy-lib.mjs";

// ---- config -----------------------------------------------------------------
function argVal(flag) {
  const i = process.argv.indexOf(flag);
  if (i >= 0 && process.argv[i + 1]) return process.argv[i + 1];
  const eq = process.argv.find((a) => a.startsWith(flag + "="));
  return eq ? eq.slice(flag.length + 1) : undefined;
}
const BASE = (argVal("--base") || process.env.VERIFY_BASE_URL || "https://deuce-forecast.web.app").replace(/\/$/, "");
const EXPECT_GENERATED_AT = argVal("--expect-generated-at") || process.env.EXPECT_GENERATED_AT || "";
const ORIGIN = new URL(BASE).origin;
const GOOGLE_SITE_VERIFICATION = "A9r3zgELsRVJ1tEyVaDH4heFNcEeDXIvZ_KzRH__eHQ";
// Freshness may lag deploy by a few seconds of CDN propagation; poll before failing.
// Overridable via env so CI can widen the window and tests can shorten it.
const FRESH_TRIES = Number(process.env.FRESH_TRIES) || (EXPECT_GENERATED_AT ? 12 : 1);
const FRESH_DELAY_MS = Number(process.env.FRESH_DELAY_MS) || 5000;
const FETCH_TRIES = Number(process.env.FETCH_TRIES) || 2;
const FETCH_RETRY_DELAY_MS = Number(process.env.FETCH_RETRY_DELAY_MS) || 500;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function fetchT(url, opts = {}, ms = 30000) {
  return fetchWithRetry(url, opts, {
    attempts: FETCH_TRIES,
    delayMs: FETCH_RETRY_DELAY_MS,
    timeoutMs: ms,
    sleep,
  });
}

// ---- check runner -----------------------------------------------------------
const results = [];
async function check(name, fn) {
  try {
    const detail = await fn();
    results.push({ name, ok: true, detail: detail || "" });
  } catch (err) {
    results.push({ name, ok: false, detail: err?.message || String(err) });
  }
}
function must(cond, msg) {
  if (!cond) throw new Error(msg);
}

// ---- checks -----------------------------------------------------------------
// Home page fetched once and reused (cache header + asset discovery + meta).
let homeHtml = "";
const routeHtml = new Map();

await check("routes 200 + text/html", async () => {
  const bad = [];
  for (const route of ROUTES) {
    const res = await fetchT(BASE + route);
    const ct = res.headers.get("content-type");
    const served = res.status === 200 && contentTypeOk(ct, route);
    if (!served) bad.push(`${route} -> ${res.status} ${ct}`);
    const html = await res.text();
    if (served) {
      routeHtml.set(route, html);
      if (route === "/") homeHtml = html;
    }
  }
  must(bad.length === 0, `bad routes: ${bad.join("; ")}`);
  return `${ROUTES.length} routes ok`;
});

await check("crawl discovery: robots.txt + sitemap.xml", async () => {
  const robotsRes = await fetchT(BASE + "/robots.txt");
  must(robotsRes.status === 200, `robots.txt -> ${robotsRes.status}`);
  must(
    String(robotsRes.headers.get("content-type") || "").includes("text/plain"),
    `robots.txt served as ${robotsRes.headers.get("content-type")}`,
  );
  const robots = await robotsRes.text();
  must(/^User-agent:\s*\*$/im.test(robots), "robots.txt missing User-agent: *");
  must(/^Allow:\s*\/$/im.test(robots), "robots.txt does not allow /");
  must(
    robots.includes(`Sitemap: ${ORIGIN}/sitemap.xml`),
    `robots.txt sitemap is not ${ORIGIN}/sitemap.xml`,
  );

  const sitemapRes = await fetchT(BASE + "/sitemap.xml");
  must(sitemapRes.status === 200, `sitemap.xml -> ${sitemapRes.status}`);
  const sitemapType = String(sitemapRes.headers.get("content-type") || "").toLowerCase();
  must(sitemapType.includes("xml"), `sitemap.xml served as ${sitemapType}`);
  const problems = sitemapCoverageProblems(await sitemapRes.text(), ORIGIN, INDEXABLE_ROUTES);
  must(problems.length === 0, problems.join("; "));
  return `${INDEXABLE_ROUTES.length} canonical URLs`;
});

await check("meta: every indexable route has a self-canonical URL", async () => {
  const { problems, unavailable } = canonicalRouteProblems(routeHtml, ORIGIN, INDEXABLE_ROUTES);
  must(problems.length === 0, problems.join("; "));
  const checked = INDEXABLE_ROUTES.length - unavailable.length;
  return unavailable.length
    ? `${checked} self-canonicals; ${unavailable.length} unavailable (covered by route check)`
    : `${checked} self-canonicals`;
});

await check("meta: Google Search Console ownership token", async () => {
  const token = extractGoogleSiteVerification(homeHtml);
  must(
    token === GOOGLE_SITE_VERIFICATION,
    `verification token was ${token || "missing"}`,
  );
  return "exact token present";
});

await check("trailingSlash: /method -> 301 /method/", async () => {
  const res = await fetchT(BASE + "/method", { redirect: "manual" });
  const loc = res.headers.get("location") || "";
  must(res.status >= 300 && res.status < 400, `expected 3xx, got ${res.status}`);
  must(loc.endsWith("/method/"), `Location was "${loc}"`);
  return `${res.status} -> ${loc}`;
});

await check("unknown path -> 404 page", async () => {
  const res = await fetchT(BASE + "/__deuce_no_such_path_" + Date.now() + "/");
  must(res.status === 404, `expected 404, got ${res.status}`);
  const body = (await res.text()).toLowerCase();
  must(body.includes("could not be found") || body.includes("404"), "404 body marker missing");
  return "404 served";
});

await check("cache-control: mutable content not stored, hashed static immutable", async () => {
  const dataRes = await fetchT(BASE + "/data/health.json");
  const dataCc = dataRes.headers.get("cache-control");
  must(mutableCacheControlOk(dataCc), `data/health.json can be stored (got "${dataCc}")`);

  const homeRes = await fetchT(BASE + "/");
  const homeCc = homeRes.headers.get("cache-control");
  must(mutableCacheControlOk(homeCc), `/ HTML can be stored (got "${homeCc}")`);

  const asset = extractHashedAsset(homeHtml, "js");
  must(asset, "no hashed /_next/static js asset found in home HTML");
  const assetRes = await fetchT(BASE + asset);
  const cc = parseCacheControl(assetRes.headers.get("cache-control"));
  must(cc.immutable, `hashed asset ${asset} not immutable (got "${assetRes.headers.get("cache-control")}")`);
  return "no-store/immutable split correct";
});

await check("MIME: js/css/json not falling through to html", async () => {
  const js = extractHashedAsset(homeHtml, "js");
  const css = extractHashedAsset(homeHtml, "css");
  must(js, "no js asset to MIME-check");
  const jsRes = await fetchT(BASE + js);
  must(contentTypeOk(jsRes.headers.get("content-type"), js), `js served as ${jsRes.headers.get("content-type")}`);
  if (css) {
    const cssRes = await fetchT(BASE + css);
    must(contentTypeOk(cssRes.headers.get("content-type"), css), `css served as ${cssRes.headers.get("content-type")}`);
  }
  const jsonRes = await fetchT(BASE + "/data/health.json");
  must(contentTypeOk(jsonRes.headers.get("content-type"), "/data/health.json"), `json served as ${jsonRes.headers.get("content-type")}`);
  return `js${css ? "/css" : ""}/json MIME ok`;
});

await check("scroll shell: wheel input reaches the document scroller", async () => {
  const css = extractHashedAsset(homeHtml, "css");
  must(css, "no hashed /_next/static css asset found in home HTML");
  const res = await fetchT(BASE + css, { cache: "no-store" });
  must(res.status === 200, `${css} -> ${res.status}`);
  const problems = scrollShellProblems(await res.text());
  must(problems.length === 0, problems.join("; "));
  return "root-owned vertical scroll contract";
});

await check(
  EXPECT_GENERATED_AT ? `freshness: live generatedAt == ${EXPECT_GENERATED_AT}` : "freshness: live health.json ok",
  async () => {
    let last = "";
    for (let i = 0; i < FRESH_TRIES; i++) {
      const res = await fetchT(BASE + "/data/health.json");
      const j = await res.json();
      last = j.generatedAt;
      if (healthArtifactOk(j, EXPECT_GENERATED_AT)) {
        return `generatedAt ${j.generatedAt} (serving contract ok; data ok=${j.ok})`;
      }
      if (i < FRESH_TRIES - 1) await sleep(FRESH_DELAY_MS);
    }
    throw new Error(`stale: live generatedAt "${last}" != expected "${EXPECT_GENERATED_AT}" after ${FRESH_TRIES} tries`);
  },
);

await check("coverage: every begun event is on the live site exactly once", async () => {
  let last = [];
  for (let i = 0; i < FRESH_TRIES; i++) {
    const healthRes = await fetchT(BASE + "/data/health.json", { cache: "no-store" });
    must(healthRes.status === 200, `health.json -> ${healthRes.status}`);
    const health = await healthRes.json();
    last = [];
    for (const tour of ["atp", "wta"]) {
      const path = `/data/${tour}/tournaments.json`;
      const res = await fetchT(BASE + path, { cache: "no-store" });
      if (res.status !== 200) {
        last.push(`${path} -> ${res.status}`);
        continue;
      }
      last.push(...coverageProblems(health, tour, await res.json()));
    }
    if (last.length === 0) {
      const n = ["atp", "wta"].reduce(
        (sum, tour) => sum + (health?.eventCoverage?.[tour]?.expectedKeys?.length || 0), 0,
      );
      return `${n} begun event(s), exact membership`;
    }
    if (i < FRESH_TRIES - 1) await sleep(FRESH_DELAY_MS);
  }
  throw new Error(last.join("; "));
});

await check("sharded artifacts: every index reference is served at one generation", async () => {
  let checked = 0;
  for (const tour of ["atp", "wta"]) {
    const matrixRes = await fetchT(BASE + `/data/${tour}/matrix-index.json`, { cache: "no-store" });
    const profileRes = await fetchT(BASE + `/data/${tour}/profile-index.json`, { cache: "no-store" });
    const scenarioRes = await fetchT(BASE + `/data/${tour}/scenario-index.json`, { cache: "no-store" });
    must(matrixRes.status === 200, `${tour}/matrix-index.json -> ${matrixRes.status}`);
    must(profileRes.status === 200, `${tour}/profile-index.json -> ${profileRes.status}`);
    must(scenarioRes.status === 200, `${tour}/scenario-index.json -> ${scenarioRes.status}`);
    const matrix = await matrixRes.json();
    const profiles = await profileRes.json();
    const scenarios = await scenarioRes.json();
    const { problems, files } = artifactIndexRefs(matrix, profiles, scenarios);
    must(problems.length === 0, `${tour}: ${problems.join("; ")}`);
    for (let start = 0; start < files.length; start += 24) {
      const batch = files.slice(start, start + 24);
      const responses = await Promise.all(batch.map(async (ref) => {
        const path = `/data/${tour}/${ref.file}`;
        const res = await fetchT(BASE + path, { cache: "no-store" });
        if (res.status !== 200) return `${path} -> ${res.status}`;
        if (!contentTypeOk(res.headers.get("content-type"), path)) {
          return `${path} served as ${res.headers.get("content-type")}`;
        }
        const payload = await res.json();
        if (payload?.generation !== ref.generation) return `${path} generation mismatch`;
        if (ref.kind === "profile" && payload?.name !== ref.name) return `${path} player mismatch`;
        if (ref.kind === "scenario" && payload?.event?.name !== ref.name) return `${path} event mismatch`;
        if (ref.kind === "matrix") {
          const components = Object.keys(payload?.components || {}).sort().join(",");
          if (components !== "combiner,eloBlend,pointModel") return `${path} component set ${components}`;
        }
        return "";
      }));
      const bad = responses.filter(Boolean);
      must(bad.length === 0, bad.join("; "));
      checked += batch.length;
    }
  }
  return `${checked} referenced shard(s)`;
});

await check("player profiles: fail-closed links + responsive dossier contract", async () => {
  const res = await fetchT(BASE + "/player/", { cache: "no-store" });
  must(res.status === 200, `/player/ -> ${res.status}`);
  const html = await res.text();
  must(hasProfileContract(html), "player profile contract marker missing (stale or partial deploy)");
  return "fail-closed-links+single-radar+mobile-contained+expectation-v3";
});

await check("match center: upcoming Playing Style drill-in contract", async () => {
  const html = routeHtml.get("/matches/");
  if (!html) return "route unavailable (covered by route check)";
  must(hasMatchCenterContract(html), "match-center contract marker missing (stale or partial deploy)");
  return "upcoming-style-links+forecast-history+watch+evidence-v3";
});

await check("prediction explanation: grouped evidence is explicitly non-causal", async () => {
  const html = routeHtml.get("/predict/");
  if (!html) return "route unavailable (covered by route check)";
  must(hasPredictionExplanationContract(html), "prediction-explanation contract marker missing (stale or partial deploy)");
  return "grouped-evidence-not-causation-v2";
});

await check("bracket lab: actual draw + exact forecast/scenario contract", async () => {
  const html = routeHtml.get("/bracket/");
  if (!html) return "route unavailable (covered by route check)";
  must(hasBracketLabContract(html), "bracket lab contract marker missing (stale or partial deploy)");
  return "actual+forecast+scenario-exact-v1";
});

await check("expectation artifacts: live summary arithmetic", async () => {
  const problems = [];
  for (const tour of ["atp", "wta"]) {
    const path = `/data/${tour}/performance.json`;
    const res = await fetchT(BASE + path, { cache: "no-store" });
    if (res.status !== 200) problems.push(`${path} -> ${res.status}`);
    else problems.push(...performanceArtifactProblems(await res.json()).map((problem) => `${tour}: ${problem}`));
  }
  must(problems.length === 0, problems.join("; "));
  return "ATP/WTA performance summaries consistent";
});

await check("meta: og:image absolute + on origin", async () => {
  const og = extractOgImage(homeHtml);
  must(og, "no og:image meta found");
  must(isAbsoluteOnOrigin(og, ORIGIN), `og:image "${og}" not absolute on ${ORIGIN}`);
  return og;
});

// ---- report -----------------------------------------------------------------
const failed = results.filter((r) => !r.ok);
console.log(`\nDeploy verification — ${BASE}\n`);
for (const r of results) console.log(`${r.ok ? "ok  " : "FAIL"} ${r.name}${r.detail ? `  (${r.detail})` : ""}`);
console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
if (failed.length) {
  console.error(`\n${failed.length} FAILED:`);
  for (const r of failed) console.error(`  - ${r.name}: ${r.detail}`);
}
process.exit(failed.length ? 1 : 0);
