"use client";

import { useState } from "react";
import ForecastTimeline from "@/components/ForecastTimeline";
import PredictionEvidence from "@/components/PredictionEvidence";
import { useUpcomingDetail, type Upcoming } from "@/lib/upcoming";

/** Shared explanation disclosure for scheduled-match cards. Component probabilities
    show model agreement/disagreement; they deliberately do not claim causal attribution. */
export default function PredictionWhy({ match }: { match: Upcoming }) {
  const [open, setOpen] = useState(false);
  const detail = useUpcomingDetail(match, open);
  const full = { ...match, ...(detail.data ?? {}) };
  if (!match.matchId && !full.components && !full.evidence && !full.forecast) return null;
  return (
    <details
      className="mx-2 rounded-b-lg border border-t-0 border-[var(--color-line)] px-3 py-2"
      onToggle={(event) => setOpen(event.currentTarget.open)}
    >
      <summary className="mono flex min-h-9 cursor-pointer list-none items-center justify-between gap-3 text-[10px] uppercase tracking-wider text-[var(--color-muted)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]">
        <span className="inline-flex items-center gap-2">
          <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-[var(--color-accent)]" />
          Model evidence
        </span>
        <span className="text-[9px] text-[var(--color-faint)]">view signals</span>
      </summary>
      <div className="mt-3" aria-live="polite">
        {detail.loading && (
          <div className="mono text-[10px] text-[var(--color-faint)]">Loading evidence…</div>
        )}
        {!detail.loading && detail.error && (
          <div className="mono text-[10px] text-[var(--color-faint)]">Evidence unavailable.</div>
        )}
        <PredictionEvidence evidence={full.evidence} components={full.components} compact />
        {full.forecast && <ForecastTimeline forecast={full.forecast} player={full.playerA} />}
      </div>
    </details>
  );
}
