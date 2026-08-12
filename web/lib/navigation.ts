export type NavItem = { href: string; label: string; desc: string };
export type NavGroup = { label: string; href?: string; items?: NavItem[] };

/** One route catalogue powers both the visible navigation and command search. */
export const NAV_GROUPS: NavGroup[] = [
  { label: "Overview", href: "/" },
  {
    label: "Matches",
    items: [
      { href: "/schedule", label: "Schedule", desc: "Win odds for scheduled matches" },
      { href: "/results", label: "Results", desc: "Model calls on recent results" },
      { href: "/bracket", label: "Brackets", desc: "Real draws, round by round" },
    ],
  },
  {
    label: "Players",
    items: [
      { href: "/rankings", label: "Rankings", desc: "Live Elo top 100" },
      { href: "/player", label: "Profiles", desc: "History, splits & H2H" },
      { href: "/style", label: "Playing style", desc: "13-axis fingerprints" },
      { href: "/strength", label: "Strength map", desc: "Serve vs return" },
      { href: "/explorer", label: "Explorer", desc: "Any stat vs any stat" },
      { href: "/trends", label: "Risers & fallers", desc: "Recent Elo movers" },
    ],
  },
  {
    label: "Forecasts",
    items: [
      { href: "/predict", label: "Predictor", desc: "Any matchup, any surface" },
      { href: "/simulator", label: "Draw simulator", desc: "Monte Carlo title odds" },
    ],
  },
  {
    label: "Model",
    items: [
      { href: "/scorecard", label: "Scorecard", desc: "Full out-of-sample report" },
      { href: "/accuracy", label: "Vs the market", desc: "Brier & calibration" },
      { href: "/track", label: "Track record", desc: "Graded point-in-time calls" },
      { href: "/method", label: "Method", desc: "How the engine works" },
    ],
  },
];

export const NAV_ITEMS: NavItem[] = NAV_GROUPS.flatMap((group) =>
  group.href
    ? [{ href: group.href, label: group.label, desc: "Current tournaments and title forecasts" }]
    : group.items ?? [],
);
