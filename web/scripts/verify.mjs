// Browser verification harness against the local dev server (:3001).
// Usage: npm run verify   (dev server must already be running — check who holds
// :3001 first; Next refuses a second instance from the same directory).
//
// Uses playwright-core with the installed Chrome (channel), so neither local npm
// install nor CI ever downloads browser binaries. Screenshots land in web/.verify/
// (gitignored). Exits non-zero if any route fails, so it can gate a "done" claim.
import { chromium } from "playwright-core";
import { mkdirSync } from "node:fs";

const BASE = process.env.VERIFY_BASE_URL || "http://localhost:3001";
// /upcoming/ stays listed: it must render the client redirect that lands on Results.
const ROUTES = ["/", "/rankings/", "/results/", "/upcoming/", "/schedule/", "/scorecard/",
                "/predict/", "/accuracy/", "/trends/", "/explorer/"];
const OUT = new URL("../.verify/", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ channel: "chrome" });
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

const consoleErrors = [];
page.on("console", (msg) => {
  if (msg.type() === "error") consoleErrors.push(`${page.url()}: ${msg.text()}`);
});
page.on("pageerror", (err) => consoleErrors.push(`${page.url()}: ${err.message}`));

let failed = 0;
for (const route of ROUTES) {
  const label = route === "/" ? "home" : route.replaceAll("/", "");
  try {
    const resp = await page.goto(BASE + route, { waitUntil: "networkidle", timeout: 30000 });
    if (!resp || resp.status() >= 400) throw new Error(`HTTP ${resp?.status()}`);
    // A page stuck on the loading state means its data JSON is missing/corrupt
    // (web/public/data is machine-generated — regenerate it from the saved model).
    await page.waitForFunction(
      () => !document.body.innerText.match(/^\s*Loading/i) && document.body.innerText.trim().length > 80,
      { timeout: 15000 },
    );
    await page.screenshot({ path: `${OUT}${label}.png`, fullPage: false });
    console.log(`ok   ${route}`);
  } catch (err) {
    failed++;
    console.error(`FAIL ${route}: ${err.message}`);
    try { await page.screenshot({ path: `${OUT}FAIL-${label}.png` }); } catch { /* page may be dead */ }
  }
}

await browser.close();
if (consoleErrors.length) {
  console.error(`\nConsole errors (${consoleErrors.length}):`);
  for (const e of consoleErrors.slice(0, 20)) console.error("  " + e);
}
console.log(`\n${ROUTES.length - failed}/${ROUTES.length} routes ok; screenshots in web/.verify/`);
process.exit(failed || consoleErrors.length ? 1 : 0);
