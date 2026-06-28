"use client";

import { useState } from "react";
import { useData, useTour } from "@/lib/tour";
import { SURFACES, pct, surfaceColor } from "@/lib/ui";
import { PageHead, Loading, SurfacePill, Reveal } from "@/components/bits";

type Draws = {
  field: string[];
  bestOf: number;
  surfaces: Record<string, { name: string; champion: number; final: number; sf: number }[]>;
};

export default function Simulator() {
  const { tour } = useTour();
  const { data, loading } = useData<Draws>("draws.json");
  const [surface, setSurface] = useState("Hard");

  const rows = data?.surfaces[surface] || [];
  const max = rows.length ? rows[0].champion : 1;

  return (
    <div className="pb-16">
      <PageHead
        eyebrow={`${tour.toUpperCase()} · Monte Carlo · Bo${data?.bestOf ?? 3}`}
        title="Draw Simulator"
        sub="A 32-player field of the current top names, standard-seeded and simulated 10,000 times through a single-elimination draw. Title, final and semifinal odds per surface."
      />

      {loading && <Loading />}

      {data && (
        <>
          <div className="mt-8 mb-5 flex flex-wrap gap-2">
            {SURFACES.map((s) => (
              <SurfacePill key={s} s={s} active={surface === s} onClick={() => setSurface(s)} />
            ))}
          </div>

          <div className="panel p-4 sm:p-6">
            {rows.map((r, i) => (
              <Reveal key={r.name} delay={Math.min(i * 0.015, 0.25)}>
                <div className="row-glow flex items-center gap-3 border-b border-[var(--color-line)]/40 py-2.5">
                  <span className="mono w-6 text-right text-[var(--color-faint)]">{i + 1}</span>
                  <span className="w-40 truncate text-sm sm:w-52">{r.name}</span>
                  <div className="bartrack relative h-5 flex-1">
                    <div
                      className="h-full rounded-full"
                      style={{ width: `${(r.champion / max) * 100}%`, background: surfaceColor(surface), opacity: 0.85 }}
                    />
                  </div>
                  <span className="mono w-14 text-right text-sm" style={{ color: surfaceColor(surface) }}>
                    {pct(r.champion, 1)}
                  </span>
                  <span className="mono hidden w-28 text-right text-xs text-[var(--color-muted)] sm:inline">
                    F {pct(r.final, 0)} · SF {pct(r.sf, 0)}
                  </span>
                </div>
              </Reveal>
            ))}
          </div>
          <p className="mono mt-4 text-xs text-[var(--color-faint)]">
            Title odds for a hypothetical even draw of the field — they shift with the actual bracket on a real event.
          </p>
        </>
      )}
    </div>
  );
}
