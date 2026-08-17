import { pct } from "@/lib/ui";
import type { Upcoming } from "@/lib/upcoming";

/** Shared explanation disclosure for scheduled-match cards. Component probabilities
    show model agreement/disagreement; they deliberately do not claim causal attribution. */
export default function PredictionWhy({ match }: { match: Upcoming }) {
  if (!match.components && !match.forecast) return null;
  return (
    <details className="mx-2 rounded-b-lg border border-t-0 border-[var(--color-line)] px-3 py-2">
      <summary className="mono cursor-pointer text-[10px] uppercase tracking-wider text-[var(--color-muted)]">
        Why this prediction?
      </summary>
      {match.components && (
        <div className="mt-2 grid grid-cols-3 gap-2 text-center">
          {([
            ["Elo", match.components.eloBlend],
            ["Points", match.components.pointModel],
            ["Final", match.components.combiner],
          ] as const).map(([label, value]) => (
            <div key={label}>
              <div className="mono text-[9px] uppercase text-[var(--color-faint)]">{label}</div>
              <div className="mono text-[11px]">{pct(value, 0)}</div>
            </div>
          ))}
        </div>
      )}
      {match.forecast && (
        <div className="mono mt-2 text-[10px] text-[var(--color-muted)]">
          Since first sighting: {match.forecast.delta >= 0 ? "+" : ""}
          {(match.forecast.delta * 100).toFixed(1)} pp for {match.playerA}
        </div>
      )}
      <div className="mt-2 text-[10px] leading-relaxed text-[var(--color-faint)]">
        Component comparison, not causal/SHAP attribution.
      </div>
    </details>
  );
}
