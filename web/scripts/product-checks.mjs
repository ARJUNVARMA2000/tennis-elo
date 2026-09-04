// Browser assertions run only with the explicit deterministic fixture capability.
// They exercise saved preferences and navigation, not source-code text or implementation details.
import { BROWSER_SMOKE_PLAYER_NAMES } from "./browser-smoke-fixture.mjs";

export async function checkFollowing(page, base) {
  const player = BROWSER_SMOKE_PLAYER_NAMES.atp[0];
  const other = BROWSER_SMOKE_PLAYER_NAMES.atp[1];
  const follow = () => page.getByRole("button", { name: `Follow ${player}`, exact: true }).first();
  const unfollow = () => page.getByRole("button", { name: `Unfollow ${player}`, exact: true }).first();
  await page.goto(`${base}/matches/?tab=upcoming&foo=keep#matches`, { waitUntil: "networkidle" });
  await follow().click();
  await page.getByRole("checkbox", { name: /Following only/ }).check();
  await page.waitForFunction(({ player, other }) => {
    const panel = document.getElementById("match-tabpanel");
    return panel?.innerText.includes(player) && !panel.innerText.includes(other);
  }, { player, other });
  await page.reload({ waitUntil: "networkidle" });
  await unfollow().waitFor({ state: "visible" });
  if (!await page.getByRole("checkbox", { name: /Following only/ }).isChecked()) throw new Error("Following filter lost on reload");
  await page.getByRole("tab", { name: "final", exact: true }).click();
  await page.getByRole("tab", { name: "live", exact: true }).click();
  await page.goBack();
  await page.waitForFunction(() => document.querySelector('[role="tab"][aria-selected="true"]')?.textContent?.trim() === "final");
  await page.goBack();
  await page.waitForFunction(() => document.querySelector('[role="tab"][aria-selected="true"]')?.textContent?.trim() === "upcoming");
  const url = new URL(page.url());
  if (url.searchParams.get("foo") !== "keep" || url.hash !== "#matches") throw new Error("tab navigation discarded unrelated URL state");
  await page.getByRole("button", { name: /^wta$/i }).click();
  await page.getByText("Choose a player above to see their matches here.", { exact: true }).waitFor({ state: "visible" });
  await page.getByRole("button", { name: /^atp$/i }).click();
  await unfollow().click();
  await page.getByText("Choose a player above to see their matches here.", { exact: true }).waitFor({ state: "visible" });
  await page.getByRole("checkbox", { name: /Following only/ }).uncheck();
  await follow().waitFor({ state: "visible" });

  // A write from another browser tab must update this one without reload.
  const peer = await page.context().newPage();
  // A same-origin blank document avoids starting a second app/ESPN poll in offline tests.
  await peer.route(`${base}/__storage-test__`, (route) => route.fulfill({
    contentType: "text/html", body: "<!doctype html><title>Storage peer</title>",
  }));
  await peer.goto(`${base}/__storage-test__`, { waitUntil: "domcontentloaded" });
  await peer.evaluate((name) => localStorage.setItem("deuce:following:v1:atp", JSON.stringify([name])), player);
  await unfollow().waitFor({ state: "visible" });
  await peer.close();
  await unfollow().click();

  // Profiles and the match board share the same preference.
  await page.goto(`${base}/player/?p=${encodeURIComponent(player)}`, { waitUntil: "networkidle" });
  await follow().click();
  await page.goto(`${base}/matches/?tab=upcoming&following=1`, { waitUntil: "networkidle" });
  await unfollow().waitFor({ state: "visible" });
  await unfollow().click();

  // Blocked storage keeps the controls functional and reports session-only persistence.
  await page.addInitScript(() => {
    Storage.prototype.getItem = () => { throw new DOMException("blocked", "SecurityError"); };
    Storage.prototype.setItem = () => { throw new DOMException("blocked", "SecurityError"); };
  });
  await page.goto(`${base}/matches/?tab=upcoming`, { waitUntil: "networkidle" });
  await follow().click();
  await unfollow().waitFor({ state: "visible" });
  await page.getByText("Browser storage is unavailable. Your follows last for this session only.", { exact: true }).waitFor({ state: "visible" });
}

export async function checkPerformanceNavigation(page, base) {
  await page.goto(`${base}/scorecard/?tour=wta`, { waitUntil: "networkidle" });
  const nav = page.getByRole("navigation", { name: "Performance sections" });
  await nav.getByRole("link", { name: "Historical tests" }).click();
  await page.waitForURL(/\/accuracy\//);
  await page.locator('[data-calibration="counts+wilson-v1"]').first().waitFor({ state: "visible" });
  if (new URL(page.url()).searchParams.get("tour") !== "wta") throw new Error("section navigation lost tour");
  const rulers = page.locator('[data-calibration] [role="img"]');
  if (await rulers.count() === 0 || !(await rulers.first().getAttribute("aria-label"))?.includes("matches")) throw new Error("calibration omitted accessible sample evidence");
  await nav.getByRole("link", { name: "Live record" }).click();
  await page.waitForURL(/\/track\//);
  await page.locator('[data-calibration="counts+wilson-v1"]').first().waitFor({ state: "visible" });
  await page.getByText("Small sample", { exact: true }).waitFor({ state: "visible" });
  await page.getByRole("button", { name: /^atp$/i }).click();
}
