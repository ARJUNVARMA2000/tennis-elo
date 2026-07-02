import type { Metadata } from "next";

/** Per-route titles/descriptions — consumed by each route's layout.tsx
    (pages are client components, so metadata lives in tiny server layouts). */
const PAGE_META: Record<string, { title: string; description: string }> = {
  rankings: {
    title: "Rankings",
    description: "Live Elo ratings for the ATP & WTA top 100 — overall and per surface.",
  },
  predict: {
    title: "Match Predictor",
    description: "Calibrated win probability and set-score distribution for any matchup, surface and format.",
  },
  simulator: {
    title: "Draw Simulator",
    description: "Monte Carlo tournament projections — title odds for the full field.",
  },
  upcoming: {
    title: "Latest Results",
    description: "Recent results with the model's pre-match calls, upset flags included.",
  },
  player: {
    title: "Player Profiles",
    description: "Elo history, surface splits, serve/return stats and head-to-heads for every ranked player.",
  },
  style: {
    title: "Playing Style",
    description: "13-axis style fingerprints from Match Charting data — compare any two players.",
  },
  strength: {
    title: "Strength Map",
    description: "Serve strength vs return strength for the tour's best, quadrant by quadrant.",
  },
  trends: {
    title: "Risers & Fallers",
    description: "The biggest recent Elo movers across both tours.",
  },
  accuracy: {
    title: "Model vs Market",
    description: "Walk-forward Brier scores and calibration against the bookmaker baseline.",
  },
  track: {
    title: "Track Record",
    description: "A graded, point-in-time forecast log — every call the model made, scored.",
  },
  method: {
    title: "Method",
    description: "How the engine works: surface-blended Elo, a serve/return Markov model and an XGBoost combiner.",
  },
};

export function pageMetadata(slug: keyof typeof PAGE_META | string): Metadata {
  const m = PAGE_META[slug];
  return m ? { title: m.title, description: m.description } : {};
}
