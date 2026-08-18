"use client";

import { useMemo } from "react";
import Link from "next/link";
import { useData, useTour } from "@/lib/tour";
import { playerHref } from "@/lib/url";
import { PageHead, Loading, Reveal, Spark } from "@/components/bits";

type History = Record<string, [string, number][]>;
type Performance = {
  window: number;
  players: { name: string; n: number; wins: number; expectedWins: number; delta: number }[];
};
const EXPECTATION_MIN_N = 5;

export default function Trends() {
  const { tour } = useTour();
  const { data, loading } = useData<History>("ratings_history.json");
  const { data: performance, loading: performanceLoading } = useData<Performance>("performance.json");

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
  const expectation = useMemo(() => {
    const rows = (performance?.players ?? []).filter((row) => row.n >= EXPECTATION_MIN_N);
    return {
      over: [...rows].sort((a, b) => b.delta - a.delta).slice(0, 8),
      under: [...rows].sort((a, b) => a.delta - b.delta).slice(0, 8),
    };
  }, [performance]);

  return (
    <div className="pb-16">
      <PageHead
        eyebrow={`${tour.toUpperCase()} · rating trajectories`}
        title="Risers & Fallers"
        sub="Monthly Elo trajectories. The biggest movers over roughly the last year of play, in either direction — form arriving, and form leaving."
      />

      {(loading || performanceLoading) && <Loading />}

      {data && (
        <>
          <div className="mt-8 grid gap-8 lg:grid-cols-2">
            <MoverList title="Rising" color="var(--color-win)" arrow="↑" rows={movers.up} />
            <MoverList title="Falling" color="var(--color-loss)" arrow="↓" rows={movers.down} />
          </div>
          {!!expectation.over.length && (
            <section className="mt-12">
              <div className="mb-4">
                <div className="eyebrow">Performance vs expectation</div>
                <p className="mt-1 max-w-3xl text-xs leading-relaxed text-[var(--color-faint)]">
                  Actual wins minus first-sighting expected wins over each player&apos;s latest {performance?.window ?? 10} graded calls. Minimum {EXPECTATION_MIN_N} matches; walkovers and retrospective estimates excluded. Descriptive only—not a model feature.
                </p>
              </div>
              <div className="grid gap-8 lg:grid-cols-2">
                <ExpectationList title="Above expectation" color="var(--color-win)" rows={expectation.over} />
                <ExpectationList title="Below expectation" color="var(--color-loss)" rows={expectation.under} />
              </div>
            </section>
          )}
          {performance && !expectation.over.length && (
            <section className="panel-inset mt-12 p-5">
              <div className="eyebrow">Performance vs expectation</div>
              <p className="mt-2 max-w-3xl text-xs leading-relaxed text-[var(--color-faint)]">
                No player has reached the {EXPECTATION_MIN_N}-match minimum yet. This board uses
                only graded first-sighting calls and does not fill missing history with estimates.
              </p>
            </section>
          )}
        </>
      )}
    </div>
  );
}

function ExpectationList({ title, color, rows }: {
  title: string;
  color: string;
  rows: { name: string; n: number; wins: number; expectedWins: number; delta: number }[];
}) {
  const { tour } = useTour();
  return (
    <div>
      <div className="eyebrow mb-3" style={{ color }}>{title}</div>
      <div className="panel divide-y divide-[var(--color-line)]">
        {rows.map((row, index) => (
          <Reveal key={row.name} delay={Math.min(index * 0.04, 0.3)}>
            <Link href={playerHref(row.name, tour)} className="row-glow flex items-center justify-between gap-4 p-4">
              <div className="min-w-0">
                <div className="truncate text-[13px]">{row.name}</div>
                <div className="mono mt-1 text-[10px] text-[var(--color-faint)]">
                  {row.wins} actual · {row.expectedWins.toFixed(2)} expected · n={row.n}
                </div>
              </div>
              <div className="mono shrink-0 text-sm" style={{ color }}>
                {row.delta >= 0 ? "+" : ""}{row.delta.toFixed(2)} wins
              </div>
            </Link>
          </Reveal>
        ))}
      </div>
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
