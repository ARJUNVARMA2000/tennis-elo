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
import { ROUTES } from "./routes.mjs";
import {
  parseCacheControl,
  contentTypeOk,
  extractHashedAsset,
  isAbsoluteOnOrigin,
  freshnessOk,
  extractOgImage,
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
// Freshness may lag deploy by a few seconds of CDN propagation; poll before failing.
// Overridable via env so CI can widen the window and tests can shorten it.
const FRESH_TRIES = Number(process.env.FRESH_TRIES) || (EXPECT_GENERATED_AT ? 12 : 1);
const FRESH_DELAY_MS = Number(process.env.FRESH_DELAY_MS) || 5000;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function fetchT(url, opts = {}, ms = 30000) {
  const ac = new AbortController();
  const t = setTimeout(() => ac.abort(), ms);
  try {
    return await fetch(url, { signal: ac.signal, ...opts });
  } finally {
    clearTimeout(t);
  }
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

await check("routes 200 + text/html", async () => {
  const bad = [];
  for (const route of ROUTES) {
    const res = await fetchT(BASE + route);
    const ct = res.headers.get("content-type");
    if (res.status !== 200 || !contentTypeOk(ct, route)) bad.push(`${route} -> ${res.status} ${ct}`);
    if (route === "/") homeHtml = await res.text();
  }
  must(bad.length === 0, `bad routes: ${bad.join("; ")}`);
  return `${ROUTES.length} routes ok`;
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

await check("cache-control: data + HTML revalidate, hashed static immutable", async () => {
  const dataRes = await fetchT(BASE + "/data/health.json");
  must(parseCacheControl(dataRes.headers.get("cache-control")).mustRevalidate, "data/health.json not must-revalidate");

  const homeRes = await fetchT(BASE + "/");
  must(parseCacheControl(homeRes.headers.get("cache-control")).mustRevalidate, "/ HTML not must-revalidate");

  const asset = extractHashedAsset(homeHtml, "js");
  must(asset, "no hashed /_next/static js asset found in home HTML");
  const assetRes = await fetchT(BASE + asset);
  const cc = parseCacheControl(assetRes.headers.get("cache-control"));
  must(cc.immutable, `hashed asset ${asset} not immutable (got "${assetRes.headers.get("cache-control")}")`);
  return "revalidate/immutable split correct";
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

await check(
  EXPECT_GENERATED_AT ? `freshness: live generatedAt == ${EXPECT_GENERATED_AT}` : "freshness: live health.json ok",
  async () => {
    let last = "";
    for (let i = 0; i < FRESH_TRIES; i++) {
      const res = await fetchT(BASE + "/data/health.json");
      const j = await res.json();
      last = j.generatedAt;
      must(j.ok === true, `live health.json reports ok=${j.ok}`);
      if (freshnessOk(j.generatedAt, EXPECT_GENERATED_AT)) {
        return `generatedAt ${j.generatedAt} (ok=true)`;
      }
      if (i < FRESH_TRIES - 1) await sleep(FRESH_DELAY_MS);
    }
    throw new Error(`stale: live generatedAt "${last}" != expected "${EXPECT_GENERATED_AT}" after ${FRESH_TRIES} tries`);
  },
);

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
