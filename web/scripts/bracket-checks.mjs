// Behavioral coverage for the fixture's R16 draw; run on both desktop and mobile in CI.
export async function checkBracketProgress(page) {
  const tree = page.locator("[data-bracket-tree]");
  await tree.waitFor({ state: "visible" });
  const rounds = async () => tree.locator("[data-bracket-round]").evaluateAll((cols) => cols.map((col) => col.dataset.bracketRound));
  const assertRemaining = async () => {
    if (JSON.stringify(await rounds()) !== JSON.stringify(["R16", "QF", "SF", "F"])) throw new Error("completed early rounds remain visible");
    if (await tree.locator("[data-bracket-match]").count() !== 15) throw new Error("remaining matchups missing");
    if (await page.getByRole("button", { name: /^Section \d/ }).count()) throw new Error("obsolete section controls remain");
  };
  await assertRemaining();
  await page.getByRole("button", { name: "Full draw", exact: true }).click();
  await page.waitForFunction(() => document.querySelector("[data-bracket-tree]")?.getAttribute("data-start-round") === "R128");
  if (await page.getByRole("button", { name: /^Section \d/ }).count() !== 8) throw new Error("full draw sections missing");
  await page.getByRole("button", { name: "Section 8", exact: true }).click();
  await page.getByRole("button", { name: "Remaining rounds", exact: true }).click();
  await page.waitForFunction(() => document.querySelector("[data-bracket-tree]")?.getAttribute("data-start-round") === "R16");
  await assertRemaining();

  await page.getByRole("button", { name: "Forecast path", exact: true }).click();
  const forecast = page.locator("[data-bracket-forecast-contract]");
  await forecast.waitFor({ state: "visible" });
  const map = page.getByLabel("Draw minimap");
  if (/R128|R64|R32/.test(await map.innerText()) || !(await map.innerText()).includes("R16")) throw new Error("forecast map did not advance");
  const semifinal = page.locator('[data-forecast-node="smoke-draw-2026:r5:m0"]');
  if (!(await semifinal.innerText()).includes("Reach final")) throw new Error("SF probabilities lack reach-final meaning");
  const trigger = semifinal.getByRole("button", { name: "Other players: reach final", exact: true });
  const list = semifinal.getByRole("list");
  // Hover uses a native preview so a centered card never moves before the click lands.
  await trigger.hover();
  if ((await trigger.getAttribute("title"))?.split("\n").length !== 7) throw new Error("hover preview omits candidates");
  await trigger.click();
  await list.waitFor({ state: "visible" });
  if (await list.getByRole("listitem").count() !== 6) throw new Error("others list does not contain every omitted semifinal candidate");
  await trigger.click();
  await list.waitFor({ state: "hidden" });
  await trigger.focus();
  await trigger.press("Enter");
  await list.waitFor({ state: "visible" });
  await trigger.press("Escape");
  await list.waitFor({ state: "hidden" });
  await trigger.click();
  await page.getByRole("heading", { name: "Brackets", exact: true }).hover();
  await list.waitFor({ state: "visible" });
  await trigger.click();
  await list.waitFor({ state: "hidden" });
  const championship = page.locator('[data-forecast-node="smoke-draw-2026:r6:m0"]');
  if (!(await championship.innerText()).includes("Win tournament")) throw new Error("championship probabilities lack win meaning");
  await championship.getByRole("button", { name: "Other players: win tournament" }).click();
  if (await championship.getByRole("listitem").count() !== 13) throw new Error("title outsiders missing");
  await page.getByRole("button", { name: "Actual draw", exact: true }).click();
  await tree.waitFor({ state: "visible" });
  await assertRemaining();
  if (new URL(page.url()).searchParams.has("mode")) throw new Error("actual draw retained forecast URL state");
  await page.getByRole("button", { name: "Forecast path", exact: true }).click();
  await forecast.waitFor({ state: "visible" });
  await page.reload();
  await forecast.waitFor({ state: "visible" });
  if (new URL(page.url()).searchParams.get("mode") !== "forecast") throw new Error("forecast mode did not survive reload");
}
