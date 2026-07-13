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
    description: "Monte Carlo projections for a hypothetical top-32 field — title, final and semifinal odds per surface.",
  },
  results: {
    title: "Results",
    description: "Recent results with the model's pre-match calls, upset flags included.",
  },
  bracket: {
    title: "Brackets",
    description: "The actual ATP & WTA tournament draws, round by round, with the model's pre-match win probability on every match.",
  },
  schedule: {
    title: "Schedule",
    description: "Model win probabilities for every scheduled ATP & WTA match, by surface and round.",
  },
  player: {
    title: "Profiles",
    description: "Elo history, surface splits, serve/return stats and head-to-heads for every ranked player.",
  },
  explorer: {
    title: "Explorer",
    description: "Plot any two attributes for the tour's best — or rank the field by any stat in a sortable table.",
  },
  style: {
    title: "Playing Style",
    description: "13-axis style radar — eight Match Charting style dimensions plus serve/return and surface-Elo percentiles — compare any two players.",
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
  scorecard: {
    title: "Scorecard",
    description: "The full out-of-sample report: walk-forward skill, calibration, the live record and paired comparisons against Kalshi and the bookmaker closing line.",
  },
  method: {
    title: "Method",
    description: "How the engine works: surface-blended Elo, a serve/return Markov model and an XGBoost combiner.",
  },
  // internal operations page — deliberately unlinked (URL-only) and noindexed
  health: {
    title: "Health",
    description: "Pipeline status: source freshness, output integrity and model drift, straight from the data-health sentinel.",
  },
};

export function pageMetadata(slug: keyof typeof PAGE_META | string): Metadata {
  const m = PAGE_META[slug];
  return m ? { title: m.title, description: m.description } : {};
}
