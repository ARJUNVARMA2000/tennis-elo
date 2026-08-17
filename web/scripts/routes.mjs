// Canonical list of indexable top-level routes — shared by the sitemap, tests, browser
// harness, and post-deploy suite. Trailing slashes match `trailingSlash: true` in
// next.config.ts, so these hit the exported <route>/index.html directly with no redirect.
// Internal /health/ and legacy /upcoming/ are intentionally absent from search discovery.
export const INDEXABLE_ROUTES = [
  "/",
  "/rankings/",
  "/results/",
  "/schedule/",
  "/matches/",
  "/bracket/",
  "/scorecard/",
  "/predict/",
  "/accuracy/",
  "/trends/",
  "/explorer/",
  "/simulator/",
  "/player/",
  "/style/",
  "/strength/",
  "/track/",
  "/method/",
];

// /upcoming/ remains in end-to-end verification because its client redirect to /results/
// must keep working even though crawlers should index only the destination.
export const ROUTES = [...INDEXABLE_ROUTES, "/upcoming/"];
