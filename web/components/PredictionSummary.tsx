import Link from "next/link";
import { motion } from "framer-motion";
import type { Tour } from "@/lib/tour";
import { pairHref, playerHref } from "@/lib/url";
import { pct } from "@/lib/ui";
import { SPRING_SOFT } from "@/lib/motion";

export type PredictionCall = {
  favorite: string;
  other: string;
  winProbability: number;
  edgePp: number;
  favoriteIsA: boolean;
  isEven: boolean;
};

/** A descriptive summary of the calibrated probability. "Edge" is explicitly the
    distance from an even matchup, never a claim about price or betting value. */
export function summarizePrediction(
  probabilityA: number,
  playerA: string,
  playerB: string,
): PredictionCall {
  const isEven = Math.abs(probabilityA - 0.5) < 0.0005;
  const favoriteIsA = isEven || probabilityA >= 0.5;
  return {
    favorite: favoriteIsA ? playerA : playerB,
    other: favoriteIsA ? playerB : playerA,
    winProbability: Math.max(probabilityA, 1 - probabilityA),
    edgePp: Math.round(Math.abs(probabilityA - 0.5) * 1_000) / 10,
    favoriteIsA,
    isEven,
  };
}

export default function PredictionSummary({
  probabilityA,
  playerA,
  playerB,
  surface,
  bestOf,
  tour,
}: {
  probabilityA: number;
  playerA: string;
  playerB: string;
  surface: string;
  bestOf: number;
  tour: Tour;
}) {
  const call = summarizePrediction(probabilityA, playerA, playerB);
  const tone = call.isEven
    ? "var(--color-muted)"
    : call.favoriteIsA ? "var(--color-accent)" : "var(--color-cmp)";
  const meter = Math.min(call.edgePp / 50, 1);
  const heading = call.isEven ? "Model sees an even matchup" : `${call.favorite} is favored`;

  return (
    <aside
      aria-labelledby="prediction-call-title"
      className="panel-inset overflow-hidden"
      data-prediction-summary="recommendation-card-adaptation-v1"
    >
      <div className="flex items-center justify-between gap-3 border-b border-[var(--color-line)] px-4 py-3">
        <span className="eyebrow !text-[10px]">Model call</span>
        <span className="chip !text-[9px] text-[var(--color-win)]">Calibrated</span>
      </div>

      <div className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h2 id="prediction-call-title" className="text-[15px] font-medium text-[var(--color-text)]">
              {heading}
            </h2>
            <p className="mt-1 text-[11px] leading-relaxed text-[var(--color-muted)]">
              {surface} · best of {bestOf} · model probability, before the match
            </p>
          </div>
          <div className="shrink-0 text-right">
            <div className="mono text-xl font-semibold" style={{ color: tone }}>
              {pct(call.winProbability, 1)}
            </div>
            <div className="mono mt-0.5 text-[9px] uppercase tracking-wider text-[var(--color-faint)]">
              win probability
            </div>
          </div>
        </div>

        <div
          role="meter"
          aria-label={call.isEven ? "Even matchup model edge from 50 percent" : `${call.favorite} model edge from 50 percent`}
          aria-valuemin={0}
          aria-valuemax={50}
          aria-valuenow={Number(call.edgePp.toFixed(1))}
          aria-valuetext={`${call.edgePp.toFixed(1)} percentage points from an even matchup`}
          className="mt-4"
        >
          <div className="bartrack relative h-2">
            <motion.div
              className="absolute inset-0"
              initial={{ scaleX: 0 }}
              animate={{ scaleX: meter }}
              transition={SPRING_SOFT}
              style={{ background: tone, transformOrigin: "left", width: "100%" }}
            />
          </div>
          <div className="mono mt-1.5 flex items-center justify-between gap-3 text-[9px] uppercase tracking-wider">
            <span className="text-[var(--color-faint)]">Model edge from 50%</span>
            <span style={{ color: tone }}>+{call.edgePp.toFixed(1)}{" "}pp</span>
          </div>
        </div>

        <p className="mt-3 text-[10px] leading-relaxed text-[var(--color-muted)]">
          This is separation from an even matchup, not an edge over a betting market.
        </p>

        <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
          <Link
            href={playerHref(call.favorite, tour)}
            className="mono min-h-11 rounded-md border border-[var(--color-line)] px-3 py-2.5 text-[10px] uppercase tracking-wider text-[var(--color-muted)] transition-colors hover:border-[var(--color-accent)] hover:text-[var(--color-text)] focus-visible:border-[var(--color-accent)] focus-visible:outline-none"
          >
            {call.isEven ? "Player A profile" : "Favorite profile"}{" "}→
          </Link>
          <Link
            href={pairHref("/style/", playerA, playerB, tour)}
            className="mono min-h-11 rounded-md border border-[var(--color-line)] px-3 py-2.5 text-[10px] uppercase tracking-wider text-[var(--color-muted)] transition-colors hover:border-[var(--color-accent)] hover:text-[var(--color-text)] focus-visible:border-[var(--color-accent)] focus-visible:outline-none"
          >
            Compare styles →
          </Link>
        </div>
      </div>
    </aside>
  );
}
