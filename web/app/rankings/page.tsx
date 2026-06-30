"use client";

import { useMemo, useState } from "react";
import { useData, useTour } from "@/lib/tour";
import { eloKey, surfaceColor, SURFACES, pct } from "@/lib/ui";
import { PageHead, Loading, SurfacePill, Reveal } from "@/components/bits";

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
          <div className="mt-8 panel flex flex-wrap items-center gap-x-10 gap-y-4 p-6">
            <div>
              <div className="eyebrow">World #1 · {surface}</div>
              <div className="display mt-2 text-3xl">{top.name}</div>
            </div>
            <div className="mono flex gap-8 text-sm">
              <Stat label="Elo" value={surface === "Overall" ? top.elo : (top as any)[eloKey(surface)]} />
              <Stat label="Serve" value={pct(top.servePct, 1)} />
              <Stat label="Return" value={pct(top.returnPct, 1)} />
              <Stat label="Matches" value={top.matches} />
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
        <table className="w-full text-sm">
          <thead className="mono text-[11px] uppercase tracking-wider text-[var(--color-faint)]">
            <tr className="border-b border-[var(--color-line)]">
              <th className="px-3 py-3 text-left">#</th>
              <th className="px-3 py-3 text-left">Player</th>
              <th className="px-3 py-3 text-left">Country</th>
              <th className="px-3 py-3 text-right">Age</th>
              <th className="px-3 py-3 text-right">Elo</th>
              <th className="hidden px-3 py-3 text-right sm:table-cell" style={{ color: surfaceColor("Hard") }}>Hard</th>
              <th className="hidden px-3 py-3 text-right sm:table-cell" style={{ color: surfaceColor("Clay") }}>Clay</th>
              <th className="hidden px-3 py-3 text-right sm:table-cell" style={{ color: surfaceColor("Grass") }}>Grass</th>
              <th className="px-3 py-3 text-right">Serve</th>
              <th className="hidden px-3 py-3 text-right md:table-cell">Return</th>
            </tr>
          </thead>
          <tbody className="mono">
            {rows.map((p, i) => (
              <tr key={p.name} className="row-glow border-b border-[var(--color-line)]/50">
                <td className="px-3 py-2.5 text-[var(--color-faint)]">{i + 1}</td>
                <td className="px-3 py-2.5 font-[var(--font-body)] text-[var(--color-text)]">{p.name}</td>
                <td className="px-3 py-2.5 text-[var(--color-muted)]">{p.country ?? "—"}</td>
                <td className="px-3 py-2.5 text-right text-[var(--color-muted)]">{p.age ?? "—"}</td>
                <td className="px-3 py-2.5 text-right font-semibold">{surface === "Overall" ? p.elo : (p as any)[eloKey(surface)]}</td>
                <td className="hidden px-3 py-2.5 text-right text-[var(--color-muted)] sm:table-cell">{p.eloHard}</td>
                <td className="hidden px-3 py-2.5 text-right text-[var(--color-muted)] sm:table-cell">{p.eloClay}</td>
                <td className="hidden px-3 py-2.5 text-right text-[var(--color-muted)] sm:table-cell">{p.eloGrass}</td>
                <td className="px-3 py-2.5 text-right text-[var(--color-muted)]">{pct(p.servePct, 0)}</td>
                <td className="hidden px-3 py-2.5 text-right text-[var(--color-muted)] md:table-cell">{pct(p.returnPct, 0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: any }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-[var(--color-faint)]">{label}</div>
      <div className="mt-1 text-lg text-[var(--color-text)]">{value}</div>
    </div>
  );
}
