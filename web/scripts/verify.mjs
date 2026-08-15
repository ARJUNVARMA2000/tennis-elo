// Browser verification harness against the local dev server (:3001).
// Usage: npm run verify   (dev server must already be running — check who holds
// :3001 first; Next refuses a second instance from the same directory).
//
// Uses playwright-core with the installed Chrome (channel), so neither local npm
// install nor CI ever downloads browser binaries. Screenshots land in web/.verify/
// (gitignored). Exits non-zero if any route fails, so it can gate a "done" claim.
import { chromium } from "playwright-core";
import { mkdirSync } from "node:fs";
import { ROUTES } from "./routes.mjs";

const BASE = process.env.VERIFY_BASE_URL || "http://localhost:3001";
// ROUTES is shared with verify-deploy.mjs. /upcoming/ stays listed: it must render the
// client redirect that lands on Results.
const OUT = new URL("../.verify/", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
mkdirSync(OUT, { recursive: true });

const consoleErrors = [];
let failed = 0;
let checked = 0;

async function checkRoute(page, route, view) {
  const label = route === "/" ? "home" : route.replaceAll("/", "");
  const resp = await page.goto(BASE + route, { waitUntil: "networkidle", timeout: 30000 });
  if (!resp || resp.status() >= 400) throw new Error(`HTTP ${resp?.status()}`);
  // A page stuck on the loading state means its data JSON is missing/corrupt
  // (web/public/data is machine-generated — regenerate it from the saved model).
  await page.waitForFunction(
    () => !document.body.innerText.match(/^\s*Loading/i) && document.body.innerText.trim().length > 80,
    undefined,
    { timeout: 15000 },
  );

  const geometry = await page.evaluate(() => ({
    canScroll: document.documentElement.scrollHeight > innerHeight + 1,
    rootClientWidth: document.documentElement.clientWidth,
    rootScrollWidth: document.documentElement.scrollWidth,
    bodyClientWidth: document.body.clientWidth,
    bodyScrollWidth: document.body.scrollWidth,
  }));
  if (view === "mobile") {
    if (geometry.rootScrollWidth > geometry.rootClientWidth + 1) {
      throw new Error(`root is ${geometry.rootScrollWidth - geometry.rootClientWidth}px too wide`);
    }
    if (geometry.bodyScrollWidth > geometry.bodyClientWidth + 1) {
      throw new Error(`body is ${geometry.bodyScrollWidth - geometry.bodyClientWidth}px too wide`);
    }
    if (route === "/player/") {
      const clipped = await page.locator("[data-profile-contract] .panel").evaluateAll((panels) =>
        panels.filter((panel) => {
          const rect = panel.getBoundingClientRect();
          return rect.left < -1 || rect.right > document.documentElement.clientWidth + 1;
        }).length,
      );
      if (clipped) throw new Error(`${clipped} player panel(s) escape the mobile viewport`);
    }
  }

  if (geometry.canScroll) {
    await page.evaluate(() => scrollTo({ top: 0, behavior: "instant" }));
    await page.mouse.move(5, Math.floor(page.viewportSize().height / 2));
    await page.mouse.wheel(0, 600);
    await page.waitForFunction(() => scrollY > 0, undefined, { timeout: 1500 });
  }

  if (view === "mobile" && route === "/scorecard/") {
    const forest = page.locator("div.overflow-x-auto").filter({
      has: page.locator('svg[aria-label^="Paired log-loss difference"]'),
    });
    await forest.scrollIntoViewIfNeeded();
    const box = await forest.boundingBox();
    if (!box) throw new Error("scorecard forest plot is not visible");
    await page.mouse.move(box.x + box.width / 2, box.y + Math.min(box.height / 2, 300));
    await page.mouse.wheel(240, 0);
    await page.waitForFunction(
      (element) => element.scrollLeft > 0,
      await forest.elementHandle(),
      { timeout: 1500 },
    );
  }

  await page.screenshot({ path: `${OUT}${view}-${label}.png`, fullPage: false });
}

const browser = await chromium.launch({ channel: "chrome" });
for (const { name, viewport } of [
  { name: "desktop", viewport: { width: 1280, height: 900 } },
  { name: "mobile", viewport: { width: 390, height: 844 } },
]) {
  const page = await browser.newPage({ viewport });
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(`${name} ${page.url()}: ${msg.text()}`);
  });
  page.on("pageerror", (err) => consoleErrors.push(`${name} ${page.url()}: ${err.message}`));

  for (const route of ROUTES) {
    const label = route === "/" ? "home" : route.replaceAll("/", "");
    checked++;
    try {
      await checkRoute(page, route, name);
      console.log(`ok   ${name.padEnd(7)} ${route}`);
    } catch (err) {
      failed++;
      console.error(`FAIL ${name} ${route}: ${err.message}`);
      try { await page.screenshot({ path: `${OUT}FAIL-${name}-${label}.png` }); } catch { /* page may be dead */ }
    }
  }
  await page.close();
}

await browser.close();
if (consoleErrors.length) {
  console.error(`\nConsole errors (${consoleErrors.length}):`);
  for (const e of consoleErrors.slice(0, 20)) console.error("  " + e);
}
console.log(`\n${checked - failed}/${checked} route/viewport checks ok; screenshots in web/.verify/`);
process.exit(failed || consoleErrors.length ? 1 : 0);
