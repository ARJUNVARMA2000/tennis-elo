"use client";

import { useState } from "react";
import { useData, useTour } from "@/lib/tour";
import { pct, surfaceColor } from "@/lib/ui";
import { PageHead, Loading, Reveal } from "@/components/bits";

type Fixture = {
  date: string; event: string; surface: string; round: string;
  winner: string; loser: string; score: string; modelProb: number; upset: boolean;
};

export default function Upcoming() {
  const { tour } = useTour();
  const { data, loading } = useData<Fixture[]>("fixtures.json");
  const [onlyUpsets, setOnlyUpsets] = useState(false);

  const rows = (data || []).filter((f) => !onlyUpsets || f.upset);

  return (
    <div className="pb-16">
      <PageHead
        eyebrow={`${tour.toUpperCase()} · latest results`}
        title="The Feed"
        sub="Every recent completed match with the model's pre-match win probability for the actual winner. Low numbers are upsets the model didn't see coming."
      />

      {loading && <Loading />}

      {data && (
        <>
          <div className="mt-8 mb-4 flex items-center gap-3">
            <button
              onClick={() => setOnlyUpsets(!onlyUpsets)}
              className="chip transition-colors"
              style={{ background: onlyUpsets ? "var(--color-coral)" : "transparent", color: onlyUpsets ? "#07090d" : "var(--color-coral)", borderColor: "var(--color-coral)" }}
            >
              Upsets only
            </button>
            <span className="mono text-xs text-[var(--color-faint)]">{rows.length} matches</span>
          </div>

          <div className="grid gap-2.5 sm:grid-cols-2">
            {rows.map((f, i) => (
              <Reveal key={i} delay={Math.min(i * 0.01, 0.2)}>
                <div className="panel p-4">
                  <div className="flex items-center justify-between">
                    <span className="chip" style={{ color: surfaceColor(f.surface), borderColor: surfaceColor(f.surface) }}>
                      {f.surface}
                    </span>
                    <span className="mono text-[11px] text-[var(--color-faint)]">{f.event} · {f.round} · {f.date}</span>
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-2">
                    <div>
                      <div className="text-[15px] text-[var(--color-lime)]">{f.winner}</div>
                      <div className="text-[15px] text-[var(--color-muted)]">{f.loser}</div>
                    </div>
                    <div className="text-right">
                      <div className="mono text-sm">{f.score}</div>
                      <div className="mono mt-1 text-xs" style={{ color: f.upset ? "var(--color-coral)" : "var(--color-muted)" }}>
                        model {pct(f.modelProb, 0)} {f.upset && "· upset"}
                      </div>
                    </div>
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
