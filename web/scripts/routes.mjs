// Canonical list of the site's top-level routes — one home, imported by both the browser
// harness (verify.mjs, local) and the post-deploy suite (verify-deploy.mjs, CI + local).
// Trailing slashes match `trailingSlash: true` in next.config.ts, so these hit the exported
// <route>/index.html directly with no redirect.
export const ROUTES = [
  "/",
  "/rankings/",
  "/results/",
  "/upcoming/",
  "/schedule/",
  "/bracket/",
  "/scorecard/",
  "/predict/",
  "/accuracy/",
  "/trends/",
  "/explorer/",
];
