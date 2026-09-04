export type NavItem = { href: string; label: string; desc: string };
export type NavGroup = { label: string; href?: string; items?: NavItem[] };

/** One route catalogue powers both the visible navigation and command search. */
export const NAV_GROUPS: NavGroup[] = [
  { label: "Overview", href: "/" },
  { label: "Matches", href: "/matches" },
  {
    label: "Players",
    items: [
      { href: "/rankings", label: "Rankings", desc: "Live Elo top 100" },
      { href: "/player", label: "Profiles", desc: "History, splits & H2H" },
      { href: "/style", label: "Playing style", desc: "10-axis fingerprints" },
      { href: "/strength", label: "Strength map", desc: "Serve vs return" },
      { href: "/explorer", label: "Explorer", desc: "Any stat vs any stat" },
      { href: "/trends", label: "Risers & fallers", desc: "Recent Elo movers" },
    ],
  },
  {
    label: "Forecasts",
    items: [
      { href: "/bracket", label: "Brackets", desc: "Actual draws, forecast paths & what-if scenarios" },
      { href: "/predict", label: "Predictor", desc: "Any matchup, any surface" },
      { href: "/simulator", label: "Draw simulator", desc: "Monte Carlo title odds" },
    ],
  },
  {
    label: "Model",
    items: [
      { href: "/scorecard", label: "Performance", desc: "Overview, historical tests & live track record" },
      { href: "/method", label: "Method", desc: "How the engine works" },
    ],
  },
];

export const SECTION_TABS = [
  { label: "Matches", items: [
    { href: "/matches", label: "Match center", desc: "Live, upcoming and frozen final calls" },
    { href: "/schedule", label: "Schedule", desc: "Full schedule with surface filters" },
    { href: "/results", label: "Recent results", desc: "Retrospective estimates from today's model" },
  ] },
  { label: "Performance", items: [
    { href: "/scorecard", label: "Overview", desc: "Model and market comparisons" },
    { href: "/accuracy", label: "Historical tests", desc: "Walk-forward Brier & calibration" },
    { href: "/track", label: "Live record", desc: "Frozen calls & external forecast benchmarks" },
  ] },
];

export function sectionForPath(path: string) {
  const clean = path.replace(/\/$/, "");
  return SECTION_TABS.find((section) => section.items.some((item) => item.href === clean));
}

const primaryItems: NavItem[] = NAV_GROUPS.flatMap((group) =>
  group.href
    ? [{ href: group.href, label: group.label, desc: group.href === "/" ? "Current tournaments and title forecasts" : "Live, scheduled and completed matches" }]
    : group.items ?? [],
);

/** Secondary destinations remain discoverable in command search and old bookmarks. */
export const NAV_ITEMS: NavItem[] = [
  ...primaryItems,
  ...SECTION_TABS.flatMap((section) => section.items).filter((item) => !primaryItems.some((primary) => primary.href === item.href)),
];
