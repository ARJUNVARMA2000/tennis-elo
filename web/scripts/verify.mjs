// Browser verification harness against a local dev or exported-static server (:3001).
// Usage: npm run verify   (a server must already be running).
//
// Local runs use the installed Chrome channel. CI installs the exact lockfile-pinned
// Playwright Chromium and selects it with VERIFY_BROWSER=chromium. Screenshots land in
// web/.verify/ (gitignored) unless VERIFY_SCREENSHOTS=0. Exits non-zero on any failure.
import { chromium } from "playwright-core";
import { mkdirSync } from "node:fs";
import { getBrowserSmokeTourIdentities } from "./browser-smoke-fixture.mjs";
import { ROUTES } from "./routes.mjs";

const BASE = process.env.VERIFY_BASE_URL || "http://localhost:3001";
const SELECTED_ROUTES = process.env.VERIFY_ROUTES
  ? process.env.VERIFY_ROUTES.split(",").map((route) => route.trim()).filter(Boolean)
  : ROUTES;
const SELECTED_VIEWS = new Set(
  (process.env.VERIFY_VIEWS || "desktop,mobile").split(",").map((view) => view.trim()),
);
const WRITE_SCREENSHOTS = process.env.VERIFY_SCREENSHOTS !== "0";
const OFFLINE = process.env.VERIFY_OFFLINE === "1";
const ASSERT_NEGATIVE_CONTROLS = process.env.VERIFY_ASSERT_NEGATIVE_CONTROLS === "1";
const FIXTURE_TOUR_IDENTITIES = getBrowserSmokeTourIdentities(process.env);
const BROWSER = process.env.VERIFY_BROWSER || "chrome";
// ROUTES is shared with verify-deploy.mjs. /upcoming/ stays listed: it must render the
// client redirect that lands on Results.
const OUT = new URL("../.verify/", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
mkdirSync(OUT, { recursive: true });

const consoleErrors = [];
const externalRequests = new Set();
let failed = 0;
let checked = 0;

async function checkRoute(page, route, view) {
  const label = route === "/" ? "home" : route.replaceAll("/", "");
  const preservesUnrelatedUrlState = view === "desktop" && route === "/player/";
  const target = preservesUnrelatedUrlState ? `${BASE}${route}?foo=bar#profile` : BASE + route;
  const resp = await page.goto(target, { waitUntil: "networkidle", timeout: 30000 });
  if (!resp || resp.status() >= 400) throw new Error(`HTTP ${resp?.status()}`);
  // A page stuck on the loading state means its data JSON is missing/corrupt
  // (web/public/data is machine-generated — regenerate it from the saved model).
  await page.waitForFunction(
    () => !document.body.innerText.match(/^\s*Loading/i) && document.body.innerText.trim().length > 80,
    undefined,
    { timeout: 15000 },
  );

  // One real state/URL interaction in the narrow CI smoke: the tour control must update
  // the shareable URL and then restore the original dataset without a stale-state race.
  // Exercise it before the scroll probes move the sticky navigation out of its initial state.
  let assertFinalTour = null;
  if (view === "desktop" && route === "/player/") {
    const waitForTour = async (expected) => {
      const identity = FIXTURE_TOUR_IDENTITIES?.[expected];
      try {
        await page.waitForFunction(
          ({ tour, presentName, absentName, preserveUrlState }) => {
            const url = new URL(location.href);
            const query = url.searchParams.get("tour");
            const pressed = [...document.querySelectorAll(`button[aria-pressed="true"]`)]
              .map((button) => button.textContent?.trim().toLowerCase())
              .find((label) => label === "atp" || label === "wta");
            const body = document.body.innerText;
            return query === (tour === "wta" ? "wta" : null)
              && (!preserveUrlState || (url.searchParams.get("foo") === "bar" && url.hash === "#profile"))
              && pressed === tour
              && (presentName === null || body.includes(presentName))
              && (absentName === null || !body.includes(absentName));
          },
          {
            tour: expected,
            presentName: identity?.present ?? null,
            absentName: identity?.absent ?? null,
            preserveUrlState: preservesUnrelatedUrlState,
          },
          { timeout: 5000 },
        );
      } catch {
        throw new Error(`tour toggle expected rendered ${expected} data and URL, got ${page.url()}`);
      }
    };
    await page.getByRole("button", { name: /^wta$/i }).click();
    await waitForTour("wta");
    // A saved WTA preference must also canonicalize a fresh param-less document load without
    // dropping unrelated URL state. This is the mount path, distinct from the local toggle path.
    await page.goto(target, { waitUntil: "networkidle", timeout: 30000 });
    await waitForTour("wta");
    await page.getByRole("button", { name: /^atp$/i }).click();
    await waitForTour("atp");
    assertFinalTour = () => waitForTour("atp");
  }

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

  // The scorecard fixture is deliberately long and owns the document-wheel contract.
  // /player/ is the state/URL route and can legitimately fit a desktop viewport when its
  // deterministic fixture is small; requiring every selected route to scroll makes the gate
  // depend on incidental content height instead of the behavior it is meant to exercise.
  if (ASSERT_NEGATIVE_CONTROLS && route === "/scorecard/" && !geometry.canScroll) {
    throw new Error("fixture route is not vertically scrollable; wheel contract was not exercised");
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

  if (WRITE_SCREENSHOTS) {
    await page.screenshot({ path: `${OUT}${view}-${label}.png`, fullPage: false });
  }
  // Let any framework transition queued by the interaction settle, then prove the page did
  // not drift back to stale query or data state while the remainder of the route was checked.
  if (assertFinalTour) {
    await page.waitForTimeout(250);
    await assertFinalTour();
  }
}

async function preparePage(page) {
  if (!OFFLINE) return;
  // No provider, analytics, or production traffic belongs in a pre-merge browser gate.
  // Allow only this local static origin. ESPN has an explicit deterministic response for a
  // future route that genuinely needs it; every other external request is recorded and blocked.
  const localOrigin = new URL(BASE).origin;
  await page.route("**/*", (route) => {
    const requested = new URL(route.request().url());
    if (requested.origin === localOrigin) return route.continue();
    if (requested.hostname === "site.api.espn.com") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ events: [] }),
      });
    }
    externalRequests.add(requested.href);
    return route.abort("blockedbyclient");
  });
}

async function assertNegativeControls(browser) {
  const viewport = { width: 390, height: 844 };

  // Reproduce the historical body scroll-container + overscroll trap. The same wheel probe
  // used by checkRoute must observe zero movement under the broken CSS.
  const vertical = await browser.newPage({ viewport });
  await preparePage(vertical);
  await vertical.goto(BASE + "/scorecard/", { waitUntil: "networkidle", timeout: 30000 });
  await vertical.waitForFunction(() => document.documentElement.scrollHeight > innerHeight + 1);
  await vertical.evaluate(() => {
    scrollTo({ top: 0, behavior: "instant" });
    document.body.style.overflowX = "hidden";
    document.body.style.overscrollBehavior = "none";
  });
  await vertical.mouse.move(5, Math.floor(viewport.height / 2));
  await vertical.mouse.wheel(0, 600);
  await vertical.waitForTimeout(250);
  if (await vertical.evaluate(() => scrollY > 0)) {
    throw new Error("vertical negative control no longer traps wheel input");
  }
  await vertical.close();

  // The scorecard forest is deliberately wider than mobile. Suppressing its horizontal
  // overflow must leave scrollLeft at zero, proving the ordinary probe would fail.
  const horizontal = await browser.newPage({ viewport });
  await preparePage(horizontal);
  await horizontal.goto(BASE + "/scorecard/", { waitUntil: "networkidle", timeout: 30000 });
  const forest = horizontal.locator("div.overflow-x-auto").filter({
    has: horizontal.locator('svg[aria-label^="Paired log-loss difference"]'),
  });
  await forest.scrollIntoViewIfNeeded();
  await forest.evaluate((element) => {
    element.style.overflowX = "hidden";
    element.scrollLeft = 0;
  });
  const box = await forest.boundingBox();
  if (!box) throw new Error("horizontal negative-control forest is not visible");
  await horizontal.mouse.move(box.x + box.width / 2, box.y + Math.min(box.height / 2, 300));
  await horizontal.mouse.wheel(240, 0);
  await horizontal.waitForTimeout(250);
  if (await forest.evaluate((element) => element.scrollLeft > 0)) {
    throw new Error("horizontal negative control still accepts wheel input");
  }
  await horizontal.close();
  console.log("ok   negative controls trap vertical and horizontal wheel input");
}

const browser = BROWSER === "chromium"
  ? await chromium.launch()
  : await chromium.launch({ channel: BROWSER });
if (ASSERT_NEGATIVE_CONTROLS) await assertNegativeControls(browser);
for (const { name, viewport } of [
  { name: "desktop", viewport: { width: 1280, height: 900 } },
  { name: "mobile", viewport: { width: 390, height: 844 } },
].filter(({ name }) => SELECTED_VIEWS.has(name))) {
  const page = await browser.newPage({ viewport });
  await preparePage(page);
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(`${name} ${page.url()}: ${msg.text()}`);
  });
  page.on("pageerror", (err) => consoleErrors.push(`${name} ${page.url()}: ${err.message}`));

  for (const route of SELECTED_ROUTES) {
    const label = route === "/" ? "home" : route.replaceAll("/", "");
    checked++;
    try {
      await checkRoute(page, route, name);
      console.log(`ok   ${name.padEnd(7)} ${route}`);
    } catch (err) {
      failed++;
      console.error(`FAIL ${name} ${route}: ${err.message}`);
      if (WRITE_SCREENSHOTS) {
        try { await page.screenshot({ path: `${OUT}FAIL-${name}-${label}.png` }); } catch { /* page may be dead */ }
      }
    }
  }
  await page.close();
}

await browser.close();
if (consoleErrors.length) {
  console.error(`\nConsole errors (${consoleErrors.length}):`);
  for (const e of consoleErrors.slice(0, 20)) console.error("  " + e);
}
if (externalRequests.size) {
  console.error(`\nBlocked external requests (${externalRequests.size}):`);
  for (const url of [...externalRequests].slice(0, 20)) console.error("  " + url);
}
console.log(`\n${checked - failed}/${checked} route/viewport checks ok${WRITE_SCREENSHOTS ? "; screenshots in web/.verify/" : ""}`);
process.exit(failed || consoleErrors.length || externalRequests.size ? 1 : 0);
