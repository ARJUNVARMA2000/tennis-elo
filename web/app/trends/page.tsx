"use client";

import { useMemo } from "react";
import Link from "next/link";
import { useData, useTour } from "@/lib/tour";
import { playerHref } from "@/lib/url";
import { PageHead, Loading, Reveal, Spark } from "@/components/bits";

type History = Record<string, [string, number][]>;

export default function Trends() {
  const { tour } = useTour();
  const { data, loading } = useData<History>("ratings_history.json");

  const movers = useMemo(() => {
    if (!data) return { up: [], down: [] };
    const deltas = Object.entries(data)
      .map(([name, pts]) => {
        const recent = pts.slice(-13); // ~1 year
        if (recent.length < 4) return null;
        return { name, delta: recent[recent.length - 1][1] - recent[0][1], series: pts.map((p) => p[1]) };
      })
      .filter(Boolean) as { name: string; delta: number; series: number[] }[];
    const sorted = [...deltas].sort((a, b) => b.delta - a.delta);
    return { up: sorted.slice(0, 8), down: sorted.slice(-8).reverse() };
  }, [data]);

  return (
    <div className="pb-16">
      <PageHead
        eyebrow={`${tour.toUpperCase()} · rating trajectories`}
        title="Risers & Fallers"
        sub="Monthly Elo trajectories. The biggest movers over roughly the last year of play, in either direction — form arriving, and form leaving."
      />

      {loading && <Loading />}

      {data && (
        <div className="mt-8 grid gap-8 lg:grid-cols-2">
          <MoverList title="Rising" color="var(--color-win)" arrow="↑" rows={movers.up} />
          <MoverList title="Falling" color="var(--color-loss)" arrow="↓" rows={movers.down} />
        </div>
      )}
    </div>
  );
}

function MoverList({
  title,
  color,
  arrow,
  rows,
}: {
  title: string;
  color: string;
  arrow: string;
  rows: { name: string; delta: number; series: number[] }[];
}) {
  const { tour } = useTour();
  return (
    <div>
      <div className="eyebrow mb-3" style={{ color }}>{title}</div>
      <div className="panel divide-y divide-[var(--color-line)]">
        {rows.map((r, i) => (
          <Reveal key={r.name} delay={Math.min(i * 0.04, 0.3)}>
            <Link href={playerHref(r.name, tour)} className="row-glow flex items-center gap-4 p-4">
              <div className="flex-1">
                <div className="text-[13px] text-[var(--color-text)]">{r.name}</div>
                <div className="mono mt-1 text-xs" style={{ color }}>
                  <span aria-hidden>{arrow}</span> {r.delta >= 0 ? "+" : ""}{Math.round(r.delta)} Elo / ~1yr
                </div>
              </div>
              <Spark points={r.series} color={color} />
            </Link>
          </Reveal>
        ))}
      </div>
    </div>
  );
}
