"use client";

import { useEffect, useMemo, useState } from "react";
import { useData, useTour } from "@/lib/tour";
import { RADAR_AXES, percentileScaler } from "@/lib/ui";
import { PageHead, Loading, Reveal, Radar } from "@/components/bits";

type Profile = {
  name: string;
  servePct: number; returnPct: number;
  eloHard: number; eloClay: number; eloGrass: number;
  style: Record<string, number | null>;
};

const A_COLOR = "var(--color-lime)";
const B_COLOR = "var(--color-cyan)";
const DEFAULTS = ["Jannik Sinner", "Novak Djokovic"];

const lastName = (n: string) => n.split(" ").slice(-1)[0];

function readAxis(p: Profile, key: string, source: "style" | "top"): number | null {
  const v = source === "style" ? p.style?.[key] : (p as unknown as Record<string, number | null>)[key];
  return v == null || isNaN(v) ? null : v;
}

export default function Style() {
  const { tour } = useTour();
  const { data, loading } = useData<Record<string, Profile>>("profiles.json");
  const names = useMemo(() => (data ? Object.keys(data) : []), [data]);
  const [a, setA] = useState("");
  const [b, setB] = useState("");

  // Resolve defaults whenever the roster changes (ATP↔WTA): Sinner vs Djokovic on ATP, else top two.
  useEffect(() => {
    if (!names.length) return;
    if (!names.includes(a)) setA(names.includes(DEFAULTS[0]) ? DEFAULTS[0] : names[0]);
    if (!names.includes(b)) setB(names.includes(DEFAULTS[1]) ? DEFAULTS[1] : (names[1] ?? names[0]));
  }, [names, a, b]);

  // One percentile scaler per axis, built from the whole field for the active tour.
  const scalers = useMemo(() => {
    if (!data) return [];
    const players = Object.values(data);
    return RADAR_AXES.map((ax) => {
      const vals = players
        .map((p) => readAxis(p, ax.key, ax.source))
        .filter((v): v is number => v != null);
      return percentileScaler(vals);
    });
  }, [data]);

  const pa = data?.[a];
  const pb = data?.[b];

  const series = useMemo(() => {
    if (!pa || !pb || !scalers.length) return [];
    const toSeries = (p: Profile, name: string, color: string) => ({
      name, color,
      values: RADAR_AXES.map((ax, i) => {
        const raw = readAxis(p, ax.key, ax.source);
        return raw == null ? 0 : scalers[i](raw);
      }),
    });
    return [toSeries(pa, a, A_COLOR), toSeries(pb, b, B_COLOR)];
  }, [pa, pb, a, b, scalers]);

  return (
    <div className="pb-16">
      <PageHead
        eyebrow={`${tour.toUpperCase()} · playing style`}
        title="Playing Style"
        sub="Two players across 13 serve, rally, return and surface metrics. Each axis is a percentile vs the field — further out means higher than more of the tour. Raw values are listed alongside."
      />

      {loading && <Loading />}

      {data && (
        <>
          <Reveal>
            <div className="mt-8 grid gap-3 sm:grid-cols-2">
              <Picker label="Player A" value={a} onChange={setA} names={names} accent={A_COLOR} />
              <Picker label="Player B" value={b} onChange={setB} names={names} accent={B_COLOR} />
            </div>
          </Reveal>

          {pa && pb && (
            <Reveal delay={0.05}>
              <div className="mt-6 grid gap-5 lg:grid-cols-5">
                {/* radar */}
                <div className="panel p-4 sm:p-6 lg:col-span-3">
                  <div className="mb-1 flex flex-wrap items-center gap-x-6 gap-y-1">
                    <Legend name={a} color={A_COLOR} />
                    <Legend name={b} color={B_COLOR} />
                  </div>
                  <Radar axes={RADAR_AXES} series={series} />
                </div>

                {/* readout table */}
                <div className="panel p-6 lg:col-span-2">
                  <div className="eyebrow mb-3">Stat lines</div>
                  <div className="grid grid-cols-[1fr_auto_auto] gap-x-5 gap-y-1.5">
                    <span className="eyebrow self-end text-[10px]">metric</span>
                    <span className="mono justify-self-end text-xs" style={{ color: A_COLOR }}>{lastName(a)}</span>
                    <span className="mono justify-self-end text-xs" style={{ color: B_COLOR }}>{lastName(b)}</span>
                    {RADAR_AXES.map((ax) => {
                      const ra = readAxis(pa, ax.key, ax.source);
                      const rb = readAxis(pb, ax.key, ax.source);
                      return (
                        <Row
                          key={ax.key}
                          label={ax.label}
                          a={ra == null ? "—" : ax.fmt(ra)}
                          b={rb == null ? "—" : ax.fmt(rb)}
                        />
                      );
                    })}
                  </div>
                  <div className="mono mt-3 text-[10px] text-[var(--color-faint)]">
                    style metrics ×100 (Match Charting Project) · Elo absolute
                  </div>
                </div>
              </div>
            </Reveal>
          )}
        </>
      )}
    </div>
  );
}

function Legend({ name, color }: { name: string; color: string }) {
  return (
    <span className="flex items-center gap-2 text-sm">
      <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: color }} />
      <span className="mono" style={{ color }}>{name}</span>
    </span>
  );
}

function Row({ label, a, b }: { label: string; a: string; b: string }) {
  return (
    <>
      <span className="text-xs text-[var(--color-muted)]">{label}</span>
      <span className="mono justify-self-end text-xs">{a}</span>
      <span className="mono justify-self-end text-xs">{b}</span>
    </>
  );
}

function Picker({ label, value, onChange, names, accent }: { label: string; value: string; onChange: (n: string) => void; names: string[]; accent: string }) {
  return (
    <label className="block">
      <div className="eyebrow mb-2" style={{ color: accent }}>{label}</div>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mono w-full rounded-xl border border-[var(--color-line)] bg-[var(--color-ink2)] px-4 py-3 text-[var(--color-text)] outline-none focus:border-[var(--color-lime)]"
      >
        {names.map((n) => (
          <option key={n} value={n}>{n}</option>
        ))}
      </select>
    </label>
  );
}
