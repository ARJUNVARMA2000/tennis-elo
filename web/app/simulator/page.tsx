"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { useData, useTour } from "@/lib/tour";
import { SURFACES, pct, surfaceColor } from "@/lib/ui";
import { PageHead, Loading, SurfacePill } from "@/components/bits";
import { EASE, SPRING_SOFT } from "@/lib/motion";

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

          <div key={surface} className="panel p-4 sm:p-6">
            {rows.map((r, i) => (
              <motion.div
                key={r.name}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.45, ease: EASE, delay: Math.min(i * 0.015, 0.25) }}
                className="row-glow flex items-center gap-3 border-b border-[var(--color-line)]/40 py-2.5"
              >
                <span className="mono w-6 text-right text-[var(--color-faint)]">{i + 1}</span>
                <span className="w-40 truncate text-sm sm:w-52">{r.name}</span>
                <div className="bartrack relative h-5 flex-1">
                  {/* static width wrapper + inner scaleX keeps the pill caps crisp at rest
                      while the entrance animation stays compositor-only */}
                  <div className="h-full" style={{ width: `${(r.champion / max) * 100}%` }}>
                    <motion.div
                      className="h-full w-full rounded-full"
                      initial={{ scaleX: 0 }}
                      animate={{ scaleX: 1 }}
                      transition={{ ...SPRING_SOFT, delay: Math.min(i * 0.04, 0.4) }}
                      style={{ background: surfaceColor(surface), opacity: 0.85, transformOrigin: "left" }}
                    />
                  </div>
                </div>
                <span className="mono w-14 text-right text-sm" style={{ color: surfaceColor(surface) }}>
                  {pct(r.champion, 1)}
                </span>
                <span className="mono hidden w-28 text-right text-xs text-[var(--color-muted)] sm:inline">
                  F {pct(r.final, 0)} · SF {pct(r.sf, 0)}
                </span>
              </motion.div>
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
