"use client";

import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { useData, useTour } from "@/lib/tour";
import { SURFACES, pct, scoreDist } from "@/lib/ui";
import { PageHead, Loading, SurfacePill, Reveal, ProbBar, AnimatedNumber } from "@/components/bits";
import { SPRING, stagger, pop } from "@/lib/motion";

type Matrix = {
  players: string[];
  formats: number[];
  surfaces: Record<string, Record<string, number[][]>>;
};

/* Inline chevron for restyled <select> elements (appearance-none). */
const SELECT_CHEVRON: React.CSSProperties = {
  backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M1 1l4 4 4-4' fill='none' stroke='%238a8f98' stroke-width='1.4' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")`,
  backgroundRepeat: "no-repeat",
  backgroundPosition: "right 0.9rem center",
};

export default function Predict() {
  const { tour } = useTour();
  const { data, loading } = useData<Matrix>("matrix.json");
  const [a, setA] = useState(0);
  const [b, setB] = useState(1);
  const [surface, setSurface] = useState("Hard");
  const [bo, setBo] = useState(3);

  const players = data?.players || [];
  const formats = useMemo(() => data?.formats || [3], [data]);

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
              <Picker label="Player A" value={a} onChange={setA} players={players} accent="var(--color-accent)" />
              <Picker label="Player B" value={b} onChange={setB} players={players} accent="var(--color-cmp)" />
            </div>
          </Reveal>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            {SURFACES.map((s) => (
              <SurfacePill key={s} s={s} active={surface === s} onClick={() => setSurface(s)} />
            ))}
            {/* Bo3 / Bo5 segmented control with sliding thumb (mirrors the ATP/WTA switch) */}
            <div className="ml-2 flex items-center rounded-md border border-[var(--color-line)] p-0.5">
              {formats.map((f) => (
                <button
                  key={f}
                  onClick={() => setBo(f)}
                  className="mono relative rounded-[5px] px-3 py-1 text-[11px]"
                >
                  {bo === f && (
                    <motion.span
                      layoutId="bo-thumb"
                      className="absolute inset-0 rounded-[5px] bg-[var(--color-text)]"
                      transition={SPRING}
                    />
                  )}
                  <span
                    className="relative z-10 transition-colors"
                    style={{ color: bo === f ? "var(--color-on-accent)" : "var(--color-muted)" }}
                  >
                    Bo{f}
                  </span>
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
                    <AnimatedNumber
                      value={p * 100}
                      decimals={1}
                      suffix="%"
                      className="mt-1 block text-3xl text-[var(--color-accent)]"
                    />
                  </div>
                  <div className="mono pb-1 text-[var(--color-faint)]">vs</div>
                  <div className="flex-1 text-right">
                    <div className="display text-2xl sm:text-3xl">{players[b]}</div>
                    <AnimatedNumber
                      value={(1 - p) * 100}
                      decimals={1}
                      suffix="%"
                      className="mt-1 block text-3xl text-[var(--color-cmp)]"
                    />
                  </div>
                </div>
                <div className="mt-5">
                  <ProbBar p={p} w={"100%" as any} />
                </div>

                <div className="mono mt-8 text-[11px] uppercase tracking-wider text-[var(--color-faint)]">
                  Most likely set scores
                </div>
                <motion.div
                  variants={stagger(0.04)}
                  initial="hidden"
                  animate="show"
                  className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3"
                >
                  {dist.map((d) => (
                    <motion.div
                      key={d.label}
                      variants={pop}
                      className="flex items-center justify-between rounded-lg border border-[var(--color-line)] px-3 py-2"
                    >
                      <span className="mono text-sm" style={{ color: d.a ? "var(--color-accent)" : "var(--color-cmp)" }}>
                        {d.a ? players[a].split(" ").slice(-1) : players[b].split(" ").slice(-1)} {d.label}
                      </span>
                      <span className="mono text-sm text-[var(--color-muted)]">{pct(d.p, 0)}</span>
                    </motion.div>
                  ))}
                </motion.div>
              </div>
            </Reveal>
          )}
          {a === b && <p className="mono mt-6 text-sm text-[var(--color-loss)]">Pick two different players.</p>}
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
        className="mono w-full appearance-none rounded-md border border-[var(--color-line)] bg-[var(--color-panel2)] py-3 pl-4 pr-10 text-[var(--color-text)] transition-colors focus:border-[var(--color-accent)] focus:outline-none"
        style={SELECT_CHEVRON}
      >
        {players.map((name, i) => (
          <option key={name} value={i}>{name}</option>
        ))}
      </select>
    </label>
  );
}
