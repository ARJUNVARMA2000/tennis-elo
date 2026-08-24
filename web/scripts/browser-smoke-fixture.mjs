// One contract shared by the fixture writer and the assertions that are only meaningful
// against that fixture. Normal `npm run verify` must never depend on these identities.
export const BROWSER_SMOKE_PLAYER_NAMES = Object.freeze({
  atp: Object.freeze(["Atlas Ace", "Atlas Bravo"]),
  wta: Object.freeze(["Willow Ace", "Willow Bravo"]),
});

/** @param {Record<string, string | undefined>} [env] */
export function getBrowserSmokeTourIdentities(env = process.env) {
  if (env.VERIFY_OFFLINE !== "1" || env.VERIFY_FIXTURE_DATA !== "1") return null;
  return Object.freeze({
    atp: Object.freeze({
      present: BROWSER_SMOKE_PLAYER_NAMES.atp[0],
      absent: BROWSER_SMOKE_PLAYER_NAMES.wta[0],
    }),
    wta: Object.freeze({
      present: BROWSER_SMOKE_PLAYER_NAMES.wta[0],
      absent: BROWSER_SMOKE_PLAYER_NAMES.atp[0],
    }),
  });
}
