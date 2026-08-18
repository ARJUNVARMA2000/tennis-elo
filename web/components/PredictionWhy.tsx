import ForecastTimeline from "@/components/ForecastTimeline";
import PredictionEvidence from "@/components/PredictionEvidence";
import type { Upcoming } from "@/lib/upcoming";

/** Shared explanation disclosure for scheduled-match cards. Component probabilities
    show model agreement/disagreement; they deliberately do not claim causal attribution. */
export default function PredictionWhy({ match }: { match: Upcoming }) {
  if (!match.components && !match.evidence && !match.forecast) return null;
  return (
    <details className="mx-2 rounded-b-lg border border-t-0 border-[var(--color-line)] px-3 py-2">
      <summary className="mono cursor-pointer text-[10px] uppercase tracking-wider text-[var(--color-muted)]">
        Model evidence
      </summary>
      <div className="mt-3">
        <PredictionEvidence evidence={match.evidence} components={match.components} compact />
        {match.forecast && <ForecastTimeline forecast={match.forecast} player={match.playerA} />}
      </div>
    </details>
  );
}
