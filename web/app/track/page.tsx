"use client";

import { useData, useTour } from "@/lib/tour";
import { pct, surfaceColor } from "@/lib/ui";
import { PageHead, Loading, Reveal } from "@/components/bits";

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

function Stat({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="panel p-4">
      <div className="mono text-[11px] uppercase tracking-wider text-[var(--color-faint)]">{label}</div>
      <div className="mono mt-2 text-2xl" style={{ color: accent ? "var(--color-lime)" : undefined }}>{value}</div>
    </div>
  );
}

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
              <Stat label="Graded calls" value={String(mf.graded)} />
              <Stat label="Accuracy" value={mf.overall.acc == null ? "—" : pct(mf.overall.acc, 1)} accent />
              <Stat label="Brier" value={num(mf.overall.brier)} accent />
              <Stat label="Log-loss" value={num(mf.overall.logloss)} />
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
                  {mf.calibration.map((c) => (
                    <div key={c.bin} className="flex items-center gap-3 py-1.5">
                      <span className="mono w-16 text-xs text-[var(--color-faint)]">{c.bin}</span>
                      <div className="relative h-6 flex-1">
                        <div className="bartrack absolute inset-y-0 left-0 h-full w-full" />
                        <div className="absolute inset-y-0 rounded-full" style={{ left: 0, width: `${c.pred * 100}%`, background: "rgba(84,210,255,0.35)" }} />
                        <div className="absolute top-1/2 h-3 w-3 -translate-y-1/2 rounded-full border-2 border-[var(--color-ink)]" style={{ left: `calc(${c.actual * 100}% - 6px)`, background: "var(--color-lime)" }} />
                      </div>
                      <span className="mono w-28 text-right text-xs text-[var(--color-muted)]">
                        {pct(c.pred, 0)} → {pct(c.actual, 0)} · n{c.n}
                      </span>
                    </div>
                  ))}
                  <div className="mono mt-3 flex gap-4 text-[10px] text-[var(--color-faint)]">
                    <span><span className="text-[var(--color-cyan)]">▰</span> predicted</span>
                    <span><span className="text-[var(--color-lime)]">●</span> actual</span>
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
                  <Stat label="Events graded" value={String(to.events)} />
                  <Stat label="Favourite won" value={to.hitRate == null ? "—" : pct(to.hitRate, 0)} accent />
                  <Stat label="Champion Brier" value={num(to.championBrier)} />
                </div>
                <div className="panel overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="mono text-[11px] uppercase tracking-wider text-[var(--color-faint)]">
                      <tr className="border-b border-[var(--color-line)]">
                        <th className="px-4 py-3 text-left">Event</th>
                        <th className="px-4 py-3 text-left">Champion</th>
                        <th className="px-4 py-3 text-left">Model favourite</th>
                        <th className="px-4 py-3 text-right">Brier</th>
                      </tr>
                    </thead>
                    <tbody className="mono">
                      {to.recent.map((e) => (
                        <tr key={e.event + e.end} className="border-b border-[var(--color-line)]/50">
                          <td className="px-4 py-3 font-[var(--font-body)]">{e.event}<span className="ml-2 text-[11px] text-[var(--color-faint)]">{e.end}</span></td>
                          <td className="px-4 py-3 text-[var(--color-lime)]">{e.champion}</td>
                          <td className="px-4 py-3" style={{ color: e.favoritePicked ? "var(--color-lime)" : "var(--color-muted)" }}>
                            {e.modelFavorite}{e.favoritePicked && " ✓"}
                          </td>
                          <td className="px-4 py-3 text-right">{num(e.championBrier)}</td>
                        </tr>
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
                      <div key={i} className="panel p-4">
                        <div className="flex items-center justify-between">
                          <span className="chip" style={{ color: surfaceColor(r.surface), borderColor: surfaceColor(r.surface) }}>{r.surface}</span>
                          <span className="mono text-[11px] text-[var(--color-faint)]">{r.event} · {r.round} · {r.date}</span>
                        </div>
                        <div className="mt-3 flex items-center justify-between gap-2">
                          <div>
                            <div className="text-[15px]" style={{ color: aWon ? "var(--color-lime)" : "var(--color-muted)" }}>
                              {r.playerA}
                            </div>
                            <div className="text-[15px]" style={{ color: !aWon ? "var(--color-lime)" : "var(--color-muted)" }}>
                              {r.playerB}
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="mono text-sm">{pct(r.p, 0)}</div>
                            <div className="mono mt-1 text-xs" style={{ color: r.hit ? "var(--color-muted)" : "var(--color-coral)" }}>
                              {r.hit ? "called it" : "missed"}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
                <div className="mono mt-3 text-[11px] text-[var(--color-faint)]">
                  Probability shown is the model’s pre-match P({"{"}first player{"}"} wins). Green = actual winner.
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
