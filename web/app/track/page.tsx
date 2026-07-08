"use client";

import { motion } from "framer-motion";
import { useData, useTour } from "@/lib/tour";
import { pct, surfaceColor } from "@/lib/ui";
import { PageHead, Loading, Reveal, StatCard, CallCard } from "@/components/bits";
import { EASE, SPRING_SOFT } from "@/lib/motion";

type Metrics = { n: number; acc: number | null; logloss: number | null; brier: number | null };
type Track = {
  tour: string;
  lastUpdated: string;
  matchForecasts: {
    logged: number; graded: number; pending: number;
    overall: Metrics;
    calibration: { bin: string; n: number; pred: number; actual: number }[];
    bySurface: Record<string, Metrics>;
    recent: {
      date: string; event: string; round: string; surface: string;
      playerA: string; playerB: string; p: number; actualWinner: string; hit: boolean;
    }[];
  };
  tournamentOdds: {
    events: number; hitRate: number | null; championBrier: number | null;
    recent: {
      event: string; end: string; champion: string; modelFavorite: string;
      favoritePicked: boolean; championBrier: number; snapshots: number;
    }[];
  };
};

const num = (x: number | null | undefined, d = 4) =>
  x == null || isNaN(x) ? "—" : x.toFixed(d);

/** number → StatCard count-up value, null → em dash. */
const statVal = (x: number | null | undefined): number | string =>
  x == null || isNaN(x) ? "—" : x;

export default function TrackPage() {
  const { tour } = useTour();
  const { data, loading } = useData<Track>("track.json");

  const mf = data?.matchForecasts;
  const to = data?.tournamentOdds;
  const empty = !!mf && mf.graded === 0;

  return (
    <div className="pb-16">
      <PageHead
        eyebrow={`${tour.toUpperCase()} · live forecast log`}
        title="Track Record"
        sub="Predictions captured the moment a match is scheduled — before it's played — then scored once the result is in. Unlike the Accuracy page (a historical backtest), this grades the model's real, point-in-time calls. Lower Brier and log-loss are better."
      />

      {loading && <Loading />}

      {data && mf && to && (
        <>
          {/* headline match-forecast metrics */}
          <Reveal>
            <div className="mt-8 grid grid-cols-2 gap-2.5 sm:grid-cols-4">
              <StatCard label="Graded calls" value={mf.graded} />
              <StatCard label="Accuracy" value={mf.overall.acc == null ? "—" : mf.overall.acc * 100} decimals={1} suffix="%" />
              <StatCard label="Brier" value={statVal(mf.overall.brier)} decimals={4} />
              <StatCard label="Log-loss" value={statVal(mf.overall.logloss)} decimals={4} />
            </div>
            <div className="mono mt-2 text-[11px] text-[var(--color-faint)]">
              {mf.logged} forecasts logged · {mf.graded} graded · {mf.pending} awaiting results
              {data.lastUpdated && <> · updated {data.lastUpdated.slice(0, 10)}</>}
            </div>
          </Reveal>

          {empty && (
            <Reveal>
              <div className="panel mt-6 p-5 text-[14px] leading-relaxed text-[var(--color-muted)]">
                The log is accruing. Forecasts are recorded each refresh for upcoming matches; once those
                matches finish they’ll be scored here. Check back after the next round completes.
              </div>
            </Reveal>
          )}

          {/* calibration */}
          {mf.calibration.length > 0 && (
            <Reveal delay={0.05}>
              <div className="mt-8">
                <div className="eyebrow mb-3">Calibration — predicted vs actual win rate (live forecasts)</div>
                <div className="panel p-5">
                  {mf.calibration.map((c, i) => (
                    <div key={c.bin} className="flex items-center gap-3 py-1.5">
                      <span className="mono w-16 text-xs text-[var(--color-faint)]">{c.bin}</span>
                      <div className="relative h-6 flex-1">
                        <div className="bartrack absolute inset-y-0 left-0 h-full w-full" />
                        {/* static-width wrapper + inner scaleX: compositor-only, crisp pill caps at rest */}
                        <div className="absolute inset-y-0 left-0" style={{ width: `${c.pred * 100}%` }}>
                          <motion.div
                            className="h-full w-full rounded-full"
                            initial={{ scaleX: 0 }}
                            whileInView={{ scaleX: 1 }}
                            viewport={{ once: true }}
                            transition={{ ...SPRING_SOFT, delay: Math.min(i * 0.05, 0.4) }}
                            style={{ background: "rgba(130,143,255,0.35)", transformOrigin: "left" }}
                          />
                        </div>
                        {/* full-width layer translated by its own width % ≡ old `left` %, sans layout */}
                        <motion.div
                          className="pointer-events-none absolute inset-0"
                          initial={{ x: "0%", opacity: 0 }}
                          whileInView={{ x: `${c.actual * 100}%`, opacity: 1 }}
                          viewport={{ once: true }}
                          transition={{ ...SPRING_SOFT, delay: Math.min(i * 0.05, 0.4) }}
                        >
                          <div
                            className="absolute left-0 top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-[var(--color-bg)]"
                            style={{ background: "var(--color-win)" }}
                          />
                        </motion.div>
                      </div>
                      <span className="mono w-28 text-right text-xs text-[var(--color-muted)]">
                        {pct(c.pred, 0)} → {pct(c.actual, 0)} · n{c.n}
                      </span>
                    </div>
                  ))}
                  <div className="mono mt-3 flex gap-4 text-[10px] text-[var(--color-faint)]">
                    <span><span className="text-[var(--color-accent)]">▰</span> predicted</span>
                    <span><span className="text-[var(--color-win)]">●</span> actual</span>
                  </div>
                </div>
              </div>
            </Reveal>
          )}

          {/* by surface */}
          {Object.keys(mf.bySurface).length > 0 && (
            <Reveal delay={0.05}>
              <div className="mt-8 grid grid-cols-1 gap-2.5 sm:grid-cols-3">
                {Object.entries(mf.bySurface).map(([s, m]) => (
                  <div key={s} className="panel p-4">
                    <span className="chip" style={{ color: surfaceColor(s), borderColor: surfaceColor(s) }}>{s}</span>
                    <div className="mono mt-3 flex justify-between text-sm">
                      <span className="text-[var(--color-faint)]">Brier</span>
                      <span>{num(m.brier)}</span>
                    </div>
                    <div className="mono mt-1 flex justify-between text-sm">
                      <span className="text-[var(--color-faint)]">Acc · n</span>
                      <span className="text-[var(--color-muted)]">{m.acc == null ? "—" : pct(m.acc, 0)} · {m.n}</span>
                    </div>
                  </div>
                ))}
              </div>
            </Reveal>
          )}

          {/* tournament title-odds scorecard */}
          {to.events > 0 && (
            <Reveal delay={0.05}>
              <div className="mt-10">
                <div className="eyebrow mb-3">Tournament title odds — did the favourite deliver?</div>
                <div className="mb-3 grid grid-cols-3 gap-2.5">
                  <StatCard label="Events graded" value={to.events} />
                  <StatCard label="Favourite won" value={to.hitRate == null ? "—" : to.hitRate * 100} suffix="%" />
                  <StatCard label="Champion Brier" value={statVal(to.championBrier)} decimals={4} />
                </div>
                <div className="panel overflow-hidden">
                  <table className="w-full text-[13px]">
                    <thead className="mono text-[11px] uppercase tracking-wider text-[var(--color-faint)]">
                      <tr className="border-b border-[var(--color-line)]">
                        <th className="px-4 py-3 text-left">Event</th>
                        <th className="px-4 py-3 text-left">Champion</th>
                        <th className="px-4 py-3 text-left">Model favourite</th>
                        <th className="px-4 py-3 text-right">Brier</th>
                      </tr>
                    </thead>
                    <tbody className="mono">
                      {to.recent.map((e, i) => (
                        <motion.tr
                          key={e.event + e.end}
                          initial={{ opacity: 0, y: 6 }}
                          whileInView={{ opacity: 1, y: 0 }}
                          viewport={{ once: true }}
                          transition={{ duration: 0.35, ease: EASE, delay: Math.min(i * 0.04, 0.3) }}
                          className="row-glow border-b border-[var(--color-line)]/50"
                        >
                          <td className="px-4 py-3 font-[var(--font-body)]">{e.event}<span className="ml-2 text-[11px] text-[var(--color-faint)]">{e.end}</span></td>
                          <td className="px-4 py-3 text-[var(--color-champ)]">{e.champion}</td>
                          <td className="px-4 py-3" style={{ color: e.favoritePicked ? "var(--color-win)" : "var(--color-muted)" }}>
                            {e.modelFavorite}{e.favoritePicked && " ✓"}
                          </td>
                          <td className="px-4 py-3 text-right">{num(e.championBrier)}</td>
                        </motion.tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </Reveal>
          )}

          {/* recent graded decisions */}
          {mf.recent.length > 0 && (
            <Reveal delay={0.05}>
              <div className="mt-10">
                <div className="eyebrow mb-3">Recent calls — pre-match probability vs result</div>
                <div className="grid gap-2.5 sm:grid-cols-2">
                  {mf.recent.map((r, i) => {
                    const aWon = r.actualWinner === r.playerA;
                    return (
                      <Reveal key={i} delay={Math.min(i * 0.04, 0.3)}>
                        <CallCard
                          surface={r.surface}
                          meta={`${r.event} · ${r.round} · ${r.date}`}
                          top={{ name: r.playerA, prob: r.p, won: aWon }}
                          bottom={{ name: r.playerB, prob: 1 - r.p, won: !aWon }}
                          note={`model favoured ${r.p >= 0.5 ? r.playerA : r.playerB}`}
                          verdict={{ label: r.hit ? "called it ✓" : "missed ✗", good: r.hit }}
                        />
                      </Reveal>
                    );
                  })}
                </div>
                <div className="mono mt-3 text-[11px] text-[var(--color-faint)]">
                  Bars are the model’s pre-match win probability for each player (they sum to 100%). Green marks the actual winner.
                </div>
              </div>
            </Reveal>
          )}
        </>
      )}

      {data && !mf && (
        <div className="panel mt-8 p-5 text-[14px] text-[var(--color-muted)]">No forecast data yet.</div>
      )}
    </div>
  );
}
