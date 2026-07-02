"use client";

import { motion } from "framer-motion";
import { useData, useTour } from "@/lib/tour";
import { PageHead, StatCard } from "@/components/bits";
import { stagger, fadeUp } from "@/lib/motion";

type Meta = { dataThrough: string; matches: number; players: number; activePlayers: number; modelVersion: string };

const STEPS = [
  ["Surface-blended Elo", "Every match updates an overall rating plus separate hard, clay and grass ratings, with a dynamic K-factor (new players move fast, veterans settle) and margin-of-victory weighting from games won. At prediction time the overall and surface ratings are blended ~50/50."],
  ["Serve / return point model", "Each player carries a time-decayed serve and return skill, computed per surface and adjusted for the strength of the opponents faced. These feed a hierarchical Markov model (point → game → tiebreak → set → match) that yields a full set-score distribution and handles best-of-3 vs best-of-5 correctly."],
  ["Tactical fingerprints", "From the Match Charting Project, each charted player gets a style profile — serve dominance, placement variety, net play, aggression, return depth, break-point clutch — attached as features where available."],
  ["XGBoost combiner", "A gradient-boosted classifier fuses Elo, the point model, ranking, rest, head-to-head and style into one win probability, then Platt-calibrated so the numbers mean what they say. Elo remains the single most important input."],
  ["Monte Carlo draws", "Pairwise probabilities drive thousands of simulated single-elimination draws for per-round and title odds."],
  ["Weekly refresh", "Results are pulled weekly, ratings and the combiner retrained, and every figure on this site regenerated — all walk-forward and leakage-free (betting odds are used only to benchmark, never as inputs)."],
];

export default function Method() {
  const { tour } = useTour();
  const { data } = useData<Meta>("meta.json");

  return (
    <div className="pb-16">
      <PageHead
        eyebrow="how it works"
        title="The Method"
        sub="A hybrid model: strong Elo and point-model features fed into a calibrated gradient-boosting combiner. Research is consistent that this beats either ratings or raw ML alone, and approaches the betting market."
      />

      {data && (
        <motion.div
          variants={stagger(0.05)}
          initial="hidden"
          animate="show"
          className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5"
        >
          <motion.div variants={fadeUp}>
            <StatCard label="Tour" value={tour.toUpperCase()} />
          </motion.div>
          <motion.div variants={fadeUp}>
            <StatCard label="Data through" value={data.dataThrough} />
          </motion.div>
          <motion.div variants={fadeUp}>
            <StatCard label="Matches" value={data.matches ?? 0} />
          </motion.div>
          <motion.div variants={fadeUp}>
            <StatCard label="Active players" value={data.activePlayers ?? 0} />
          </motion.div>
          <motion.div variants={fadeUp}>
            <StatCard label="Model" value={`v${data.modelVersion}`} />
          </motion.div>
        </motion.div>
      )}

      <motion.div variants={stagger(0.05)} initial="hidden" animate="show" className="mt-8 space-y-4">
        {STEPS.map(([title, body], i) => (
          <motion.div key={title} variants={fadeUp} className="panel flex gap-5 p-6">
            <div className="display text-3xl text-[var(--color-accent)]">{String(i + 1).padStart(2, "0")}</div>
            <div>
              <div className="display text-lg">{title}</div>
              <p className="mt-2 text-[15px] leading-relaxed text-[var(--color-muted)]">{body}</p>
            </div>
          </motion.div>
        ))}
      </motion.div>
    </div>
  );
}
