"use client";

import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { useData, useTour } from "@/lib/tour";
import { eloKey, surfaceColor, SURFACES, pct } from "@/lib/ui";
import { PageHead, Loading, SurfacePill, Reveal, StatCard } from "@/components/bits";

type Player = {
  name: string; eloRank: number; elo: number; eloHard: number; eloClay: number; eloGrass: number;
  servePct: number; returnPct: number; rankPoints: number | null; matches: number; hand: string | null;
  age: number | null; country: string | null;
};

export default function Rankings() {
  const { tour } = useTour();
  const { data, loading } = useData<Player[]>("players.json");
  const [surface, setSurface] = useState<string>("Overall");

  const rows = useMemo(() => {
    if (!data) return [];
    const key = surface === "Overall" ? "elo" : eloKey(surface);
    return [...data].sort((a, b) => (b as any)[key] - (a as any)[key]).slice(0, 100);
  }, [data, surface]);

  const top = rows[0];

  return (
    <div className="pb-16">
      <PageHead
        eyebrow={`${tour.toUpperCase()} · Elo ratings`}
        title="The Board"
        sub="Surface-blended Elo for every active player, with serve and return strength from the opponent-adjusted point model. Switch surfaces to re-rank."
      />

      {loading && <Loading />}

      {top && (
        <Reveal delay={0.05}>
          <div className="mt-8 flex flex-wrap items-center gap-x-10 gap-y-5">
            <div>
              <div className="eyebrow">World #1 · {surface}</div>
              <div className="display mt-2 text-3xl sm:text-4xl">{top.name}</div>
            </div>
            <div className="grid min-w-[260px] flex-1 grid-cols-2 gap-3 sm:grid-cols-4">
              <StatCard
                label="Elo"
                value={surface === "Overall" ? top.elo : ((top as any)[eloKey(surface)] as number)}
              />
              <StatCard label="Serve" value={top.servePct * 100} decimals={1} suffix="%" />
              <StatCard label="Return" value={top.returnPct * 100} decimals={1} suffix="%" />
              <StatCard label="Matches" value={top.matches} />
            </div>
          </div>
        </Reveal>
      )}

      <div className="mt-8 mb-4 flex flex-wrap items-center gap-2">
        <SurfacePill s="Overall" active={surface === "Overall"} onClick={() => setSurface("Overall")} />
        {SURFACES.map((s) => (
          <SurfacePill key={s} s={s} active={surface === s} onClick={() => setSurface(s)} />
        ))}
      </div>

      <div className="panel overflow-hidden">
        <table className="w-full border-collapse text-[13px]">
          <thead>
            <tr className="mono text-[10px] uppercase tracking-wider text-[var(--color-faint)]">
              <th className="px-3 py-3 text-right font-normal">#</th>
              <th className="px-3 py-3 text-left font-normal">Player</th>
              <th className="px-3 py-3 text-left font-normal">Country</th>
              <th className="px-3 py-3 text-right font-normal">Age</th>
              <th className="px-3 py-3 text-right font-normal">Elo</th>
              <th className="hidden px-3 py-3 text-right font-normal sm:table-cell" style={{ color: surfaceColor("Hard") }}>Hard</th>
              <th className="hidden px-3 py-3 text-right font-normal sm:table-cell" style={{ color: surfaceColor("Clay") }}>Clay</th>
              <th className="hidden px-3 py-3 text-right font-normal sm:table-cell" style={{ color: surfaceColor("Grass") }}>Grass</th>
              <th className="px-3 py-3 text-right font-normal">Serve</th>
              <th className="hidden px-3 py-3 text-right font-normal md:table-cell">Return</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p, i) => (
              <motion.tr
                key={p.name}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.35, delay: Math.min(i * 0.02, 0.3) }}
                className="row-glow border-t border-[var(--color-line)]"
              >
                <td className="mono px-3 py-2.5 text-right text-[11px] text-[var(--color-faint)]">{i + 1}</td>
                <td className="px-3 py-2.5 whitespace-nowrap text-[var(--color-text)]">{p.name}</td>
                <td className="mono px-3 py-2.5 text-[11px] text-[var(--color-muted)]">{p.country ?? "—"}</td>
                <td className="mono px-3 py-2.5 text-right text-[var(--color-muted)]">{p.age ?? "—"}</td>
                <td className="mono px-3 py-2.5 text-right font-semibold text-[var(--color-text)]">
                  {surface === "Overall" ? p.elo : (p as any)[eloKey(surface)]}
                </td>
                <td className="mono hidden px-3 py-2.5 text-right text-[var(--color-muted)] sm:table-cell">{p.eloHard}</td>
                <td className="mono hidden px-3 py-2.5 text-right text-[var(--color-muted)] sm:table-cell">{p.eloClay}</td>
                <td className="mono hidden px-3 py-2.5 text-right text-[var(--color-muted)] sm:table-cell">{p.eloGrass}</td>
                <td className="mono px-3 py-2.5 text-right text-[var(--color-muted)]">{pct(p.servePct, 0)}</td>
                <td className="mono hidden px-3 py-2.5 text-right text-[var(--color-muted)] md:table-cell">{pct(p.returnPct, 0)}</td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
