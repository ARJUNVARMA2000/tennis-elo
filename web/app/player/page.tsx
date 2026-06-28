"use client";

import { useEffect, useMemo, useState } from "react";
import { useData, useTour } from "@/lib/tour";
import { pct, surfaceColor, SURFACES } from "@/lib/ui";
import { PageHead, Loading, Reveal, Spark } from "@/components/bits";

type Profile = {
  name: string; elo: number; eloHard: number; eloClay: number; eloGrass: number;
  servePct: number; returnPct: number; rankPoints: number | null; matches: number; hand: string | null;
  style: Record<string, number | null>;
  history: [string, number][];
  recent: { date: string; opp: string; surface: string; won: boolean; score: string; event: string }[];
  h2h: { opp: string; w: number; l: number }[];
};

const STYLE_LABEL: Record<string, string> = {
  style_serve_dom: "Serve dominance", style_placement: "Serve variety", style_net: "Net frequency",
  style_snv: "Serve & volley", style_aggression: "Aggression", style_fhbh: "Forehand bias",
  style_return_depth: "Return depth", style_bp_clutch: "Break-point clutch",
};

export default function Players() {
  const { tour } = useTour();
  const { data, loading } = useData<Record<string, Profile>>("profiles.json");
  const names = useMemo(() => (data ? Object.keys(data) : []), [data]);
  const [sel, setSel] = useState("");

  useEffect(() => { if (names.length && !names.includes(sel)) setSel(names[0]); }, [names, sel]);
  const p = data?.[sel];

  return (
    <div className="pb-16">
      <PageHead eyebrow={`${tour.toUpperCase()} · player dossier`} title="Players" />

      {loading && <Loading />}

      {data && (
        <>
          <Reveal>
            <input
              list="players"
              value={sel}
              onChange={(e) => setSel(e.target.value)}
              placeholder="Search a player…"
              className="mono mt-8 w-full max-w-md rounded-xl border border-[var(--color-line)] bg-[var(--color-ink2)] px-4 py-3 outline-none focus:border-[var(--color-lime)]"
            />
            <datalist id="players">{names.map((n) => <option key={n} value={n} />)}</datalist>
          </Reveal>

          {p && (
            <Reveal delay={0.05}>
              <div className="mt-6 grid gap-5 lg:grid-cols-3">
                {/* identity + elo line */}
                <div className="panel p-6 lg:col-span-2">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="display text-3xl">{p.name}</div>
                      <div className="mono mt-2 text-sm text-[var(--color-muted)]">
                        Elo {p.elo} · {p.matches} matches{p.hand ? ` · ${p.hand}-handed` : ""}{p.rankPoints ? ` · ${p.rankPoints} pts` : ""}
                      </div>
                    </div>
                    <Spark points={p.history.map((h) => h[1])} w={200} color="var(--color-lime)" />
                  </div>
                  <div className="mt-5 grid grid-cols-3 gap-3">
                    {SURFACES.map((s) => (
                      <div key={s} className="rounded-lg border border-[var(--color-line)] p-3">
                        <div className="eyebrow" style={{ color: surfaceColor(s) }}>{s}</div>
                        <div className="mono mt-1 text-xl">{(p as any)[`elo${s}`]}</div>
                      </div>
                    ))}
                  </div>
                  <div className="mono mt-4 flex gap-8 text-sm">
                    <span>Serve <b className="text-[var(--color-lime)]">{pct(p.servePct, 1)}</b></span>
                    <span>Return <b className="text-[var(--color-cyan)]">{pct(p.returnPct, 1)}</b></span>
                  </div>
                </div>

                {/* style fingerprint */}
                <div className="panel p-6">
                  <div className="eyebrow mb-3">Playing style</div>
                  {Object.entries(STYLE_LABEL).map(([k, label]) => {
                    const v = p.style[k];
                    return (
                      <div key={k} className="flex items-center justify-between py-1.5">
                        <span className="text-xs text-[var(--color-muted)]">{label}</span>
                        <span className="mono text-xs">{v == null ? "—" : (k === "style_bp_clutch" ? (v >= 0 ? "+" : "") + (v * 100).toFixed(0) : (v * 100).toFixed(0))}</span>
                      </div>
                    );
                  })}
                  <div className="mono mt-2 text-[10px] text-[var(--color-faint)]">from Match Charting Project</div>
                </div>

                {/* recent form */}
                <div className="panel p-6 lg:col-span-2">
                  <div className="eyebrow mb-3">Recent matches</div>
                  <div className="divide-y divide-[var(--color-line)]/40">
                    {p.recent.slice(0, 10).map((m, i) => (
                      <div key={i} className="flex items-center gap-3 py-2 text-sm">
                        <span className="mono w-5 text-center" style={{ color: m.won ? "var(--color-lime)" : "var(--color-coral)" }}>{m.won ? "W" : "L"}</span>
                        <span className="flex-1 truncate">{m.won ? "d. " : "lost to "}{m.opp}</span>
                        <span className="chip" style={{ color: surfaceColor(m.surface), borderColor: surfaceColor(m.surface) }}>{m.surface[0]}</span>
                        <span className="mono w-28 text-right text-xs text-[var(--color-muted)]">{m.score}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* h2h */}
                <div className="panel p-6">
                  <div className="eyebrow mb-3">Head-to-head</div>
                  {p.h2h.slice(0, 8).map((h) => (
                    <div key={h.opp} className="flex items-center justify-between py-1.5 text-sm">
                      <span className="truncate text-[var(--color-muted)]">{h.opp}</span>
                      <span className="mono"><b className="text-[var(--color-lime)]">{h.w}</b>–<b className="text-[var(--color-coral)]">{h.l}</b></span>
                    </div>
                  ))}
                </div>
              </div>
            </Reveal>
          )}
        </>
      )}
    </div>
  );
}
