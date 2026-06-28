"use client";

import { useMemo, useState } from "react";
import { useData, useTour } from "@/lib/tour";
import { SURFACES, pct, scoreDist } from "@/lib/ui";
import { PageHead, Loading, SurfacePill, Reveal, ProbBar } from "@/components/bits";

type Matrix = {
  players: string[];
  formats: number[];
  surfaces: Record<string, Record<string, number[][]>>;
};

export default function Predict() {
  const { tour } = useTour();
  const { data, loading } = useData<Matrix>("matrix.json");
  const [a, setA] = useState(0);
  const [b, setB] = useState(1);
  const [surface, setSurface] = useState("Hard");
  const [bo, setBo] = useState(3);

  const players = data?.players || [];
  const formats = data?.formats || [3];

  const p = useMemo(() => {
    if (!data || a === b) return null;
    const m = data.surfaces[surface]?.[String(formats.includes(bo) ? bo : formats[0])];
    return m ? m[a][b] : null;
  }, [data, a, b, surface, bo, formats]);

  const dist = p != null ? scoreDist(p, formats.includes(bo) ? bo : formats[0]) : [];

  return (
    <div className="pb-16">
      <PageHead
        eyebrow={`${tour.toUpperCase()} · head to head`}
        title="Match Predictor"
        sub="Pick any two players, a surface and a format. The XGBoost combiner returns a calibrated win probability; the point model gives the most likely set scores."
      />

      {loading && <Loading />}

      {data && (
        <>
          <Reveal>
            <div className="mt-8 grid gap-3 sm:grid-cols-2">
              <Picker label="Player A" value={a} onChange={setA} players={players} accent="var(--color-lime)" />
              <Picker label="Player B" value={b} onChange={setB} players={players} accent="var(--color-cyan)" />
            </div>
          </Reveal>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            {SURFACES.map((s) => (
              <SurfacePill key={s} s={s} active={surface === s} onClick={() => setSurface(s)} />
            ))}
            <div className="ml-2 flex rounded-full border border-[var(--color-line)] p-0.5">
              {formats.map((f) => (
                <button
                  key={f}
                  onClick={() => setBo(f)}
                  className="mono rounded-full px-3 py-1 text-[11px]"
                  style={{ background: bo === f ? "var(--color-text)" : "transparent", color: bo === f ? "#07090d" : "var(--color-muted)" }}
                >
                  Bo{f}
                </button>
              ))}
            </div>
          </div>

          {p != null && (
            <Reveal delay={0.05}>
              <div className="mt-6 panel p-6 sm:p-8">
                <div className="flex items-end justify-between gap-4">
                  <div className="flex-1">
                    <div className="display text-2xl sm:text-3xl">{players[a]}</div>
                    <div className="mono mt-1 text-3xl text-[var(--color-lime)]">{pct(p, 1)}</div>
                  </div>
                  <div className="mono pb-1 text-[var(--color-faint)]">vs</div>
                  <div className="flex-1 text-right">
                    <div className="display text-2xl sm:text-3xl">{players[b]}</div>
                    <div className="mono mt-1 text-3xl text-[var(--color-cyan)]">{pct(1 - p, 1)}</div>
                  </div>
                </div>
                <div className="mt-5">
                  <ProbBar p={p} w={"100%" as any} />
                </div>

                <div className="mono mt-8 text-[11px] uppercase tracking-wider text-[var(--color-faint)]">
                  Most likely set scores
                </div>
                <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
                  {dist.map((d) => (
                    <div key={d.label} className="flex items-center justify-between rounded-lg border border-[var(--color-line)] px-3 py-2">
                      <span className="mono text-sm" style={{ color: d.a ? "var(--color-lime)" : "var(--color-cyan)" }}>
                        {d.a ? players[a].split(" ").slice(-1) : players[b].split(" ").slice(-1)} {d.label}
                      </span>
                      <span className="mono text-sm text-[var(--color-muted)]">{pct(d.p, 0)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </Reveal>
          )}
          {a === b && <p className="mono mt-6 text-sm text-[var(--color-coral)]">Pick two different players.</p>}
        </>
      )}
    </div>
  );
}

function Picker({ label, value, onChange, players, accent }: { label: string; value: number; onChange: (n: number) => void; players: string[]; accent: string }) {
  return (
    <label className="block">
      <div className="eyebrow mb-2" style={{ color: accent }}>{label}</div>
      <select
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mono w-full rounded-xl border border-[var(--color-line)] bg-[var(--color-ink2)] px-4 py-3 text-[var(--color-text)] outline-none focus:border-[var(--color-lime)]"
      >
        {players.map((name, i) => (
          <option key={name} value={i}>{name}</option>
        ))}
      </select>
    </label>
  );
}
