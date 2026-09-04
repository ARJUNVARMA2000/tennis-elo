"use client";

import CalibrationChart from "@/components/CalibrationChart";
import { motion } from "framer-motion";
import { useMemo } from "react";
import { useData, useTour } from "@/lib/tour";
import { pct, surfaceColor } from "@/lib/ui";
import { PageHead, Loading, Reveal, StatCard, CallCard } from "@/components/bits";
import { EASE } from "@/lib/motion";
import {
  benchmarkSourceLabel,
  benchmarkStageLabel,
  deltaVerdict,
  externalMinusDeuce,
  formatBenchmarkDelta,
  formatBenchmarkMetric,
  formatBenchmarkTimestamp,
  formatExclusionReason,
  isScoredReachAggregate,
  isTennisAbstractBenchmark,
  safeBenchmarkSourceUrl,
  type DeltaVerdict,
  type ReachAggregateComparison,
  type TennisAbstractBenchmark,
} from "@/lib/tennis-abstract";

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

const DELTA_COLOR: Record<DeltaVerdict, string> = {
  deuce: "var(--color-win)",
  "tennis-abstract": "var(--color-cmp)",
  even: "var(--color-faint)",
  unavailable: "var(--color-faint)",
};

const BENCHMARK_STATUS: Record<TennisAbstractBenchmark["status"], string> = {
  accruing: "Accruing",
  complete: "Complete",
  unavailable: "Unavailable",
};

const BENCHMARK_STATUS_COLOR: Record<TennisAbstractBenchmark["status"], string> = {
  accruing: "var(--color-champ)",
  complete: "var(--color-win)",
  unavailable: "var(--color-faint)",
};

function DeltaCell({
  value,
  se,
  sourceName,
}: {
  value: number | null | undefined;
  se?: number | null;
  sourceName: string;
}) {
  const verdict = deltaVerdict(value);
  const label = verdict === "deuce" ? "DEUCE lower"
    : verdict === "tennis-abstract" ? `${sourceName} lower`
      : verdict === "even" ? "Even at shown precision" : "Not graded";
  return (
    <div className="text-right" style={{ color: DELTA_COLOR[verdict] }}>
      <div>{formatBenchmarkDelta(value)}</div>
      <div className="mt-0.5 whitespace-nowrap text-[10px]">
        {se != null && <>SE {formatBenchmarkMetric(se)}{" "}·{" "}</>}{label}
      </div>
    </div>
  );
}

function aggregateDelta(
  aggregate: ReachAggregateComparison,
  metric: "logloss" | "brier",
): number | null {
  const paired = metric === "logloss"
    ? aggregate.paired?.loglossDelta : aggregate.paired?.brierDelta;
  return paired ?? externalMinusDeuce(
    aggregate.tennisAbstract[metric],
    aggregate.deuce[metric],
  );
}

export function TennisAbstractSection({ data }: { data: TennisAbstractBenchmark }) {
  const match = data.matchComparison;
  const sourceName = benchmarkSourceLabel(data.source.name);
  const sourceUrl = safeBenchmarkSourceUrl(data.source.url);
  const reasons = Object.entries(match.exclusionReasons ?? {})
    .filter(([, count]) => Number.isFinite(count) && count > 0)
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  const hasDescriptiveCaveat = data.caveats.some((caveat) =>
    /one tournament/i.test(caveat) && /descriptive/i.test(caveat));
  const reach = data.reachComparison;
  const aggregates = [
    reach?.macro ? { key: "macro", label: "Stage macro", value: reach.macro } : null,
    isScoredReachAggregate(reach?.champion)
      ? { key: "champion", label: "Champion distribution", value: reach.champion } : null,
  ].filter((row): row is { key: string; label: string; value: ReachAggregateComparison } => row !== null);
  const hasMatchScores = data.status !== "unavailable" && match.graded > 0;

  return (
    <Reveal delay={0.05}>
      <section className="mt-10" aria-labelledby="tennis-abstract-heading" data-tennis-abstract-benchmark={data.status}>
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
          <div>
            <div className="eyebrow">{data.benchmark.season} · external forecast benchmark</div>
            <h2 id="tennis-abstract-heading" className="display mt-1.5 text-2xl">
              {data.benchmark.event}: DEUCE vs {sourceName}
            </h2>
            <p className="mt-2 max-w-3xl text-[14px] leading-relaxed text-[var(--color-muted)]">
              Both methods are scored on the same eligible matches, using forecasts frozen before each match.
              Log-loss and Brier are lower-is-better; every Δ is {sourceName}{" "}− DEUCE, so a positive value means DEUCE did better.
            </p>
          </div>
          <span className="chip w-fit" style={{ color: BENCHMARK_STATUS_COLOR[data.status] }}>
            {BENCHMARK_STATUS[data.status]}
          </span>
        </div>

        <div className="mt-5">
          <div className="eyebrow mb-3">Paired match coverage</div>
          <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
            <StatCard label="Eligible pairs" value={match.eligible} />
            <StatCard label="Graded" value={match.graded} />
            <StatCard label="Pending" value={match.pending} />
            <StatCard label="Excluded" value={match.excluded} />
          </div>
        </div>

        {(data.status === "unavailable" || !hasMatchScores) && (
          <div className="panel mt-2.5 p-5 text-[14px] leading-relaxed text-[var(--color-muted)]">
            {data.status === "unavailable"
              ? "No paired forecast score is available for this event and tour. The coverage ledger remains visible so missing data is not mistaken for a tie."
              : "This comparison is accruing. Eligible forecasts are already frozen; scores will appear as those matches finish."}
          </div>
        )}

        {hasMatchScores && (
          <div
            className="panel mt-2.5 overflow-x-auto focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]"
            role="region"
            aria-label="Paired match forecast scores"
            tabIndex={0}
          >
            <table className="w-full min-w-[620px] text-[13px]">
              <thead className="mono text-[10px] uppercase tracking-wider text-[var(--color-faint)]">
                <tr className="border-b border-[var(--color-line)]">
                  <th className="px-4 py-3 text-left">Match forecasts</th>
                  <th className="px-4 py-3 text-right">n</th>
                  <th className="px-4 py-3 text-right">Log-loss ↓</th>
                  <th className="px-4 py-3 text-right">Brier ↓</th>
                </tr>
              </thead>
              <tbody className="mono">
                <tr className="border-b border-[var(--color-line)]/50">
                  <td className="px-4 py-3 font-[var(--font-body)] text-[var(--color-text)]">DEUCE</td>
                  <td className="px-4 py-3 text-right text-[var(--color-faint)]">{match.deuce.n}</td>
                  <td className="px-4 py-3 text-right">{formatBenchmarkMetric(match.deuce.logloss)}</td>
                  <td className="px-4 py-3 text-right">{formatBenchmarkMetric(match.deuce.brier)}</td>
                </tr>
                <tr className="border-b border-[var(--color-line)]/50">
                  <td className="px-4 py-3 font-[var(--font-body)] text-[var(--color-text)]">{sourceName}</td>
                  <td className="px-4 py-3 text-right text-[var(--color-faint)]">{match.tennisAbstract.n}</td>
                  <td className="px-4 py-3 text-right">{formatBenchmarkMetric(match.tennisAbstract.logloss)}</td>
                  <td className="px-4 py-3 text-right">{formatBenchmarkMetric(match.tennisAbstract.brier)}</td>
                </tr>
                <tr className="bg-[var(--color-accent-dim)]">
                  <td className="px-4 py-3 font-[var(--font-body)] text-[var(--color-muted)]">
                    Δ · {sourceName}{" "}− DEUCE
                  </td>
                  <td className="px-4 py-3 text-right text-[var(--color-faint)]">paired</td>
                  <td className="px-4 py-3"><DeltaCell value={match.paired.loglossDelta} se={match.paired.seLogloss} sourceName={sourceName} /></td>
                  <td className="px-4 py-3"><DeltaCell value={match.paired.brierDelta} se={match.paired.seBrier} sourceName={sourceName} /></td>
                </tr>
              </tbody>
            </table>
          </div>
        )}

        {reasons.length > 0 && (
          <div className="panel mt-2.5 p-4">
            <div className="eyebrow mb-2">Excluded from paired match scoring</div>
            <div className="flex flex-wrap gap-2">
              {reasons.map(([reason, count]) => (
                <span key={reason} className="mono rounded-full border border-[var(--color-line)] px-2.5 py-1 text-[11px] text-[var(--color-muted)]">
                  {formatExclusionReason(reason)}{" "}· {count}
                </span>
              ))}
            </div>
          </div>
        )}

        {data.status !== "unavailable" && reach && (reach.stages.length > 0 || aggregates.length > 0) && (
          <div className="mt-6">
            <div className="eyebrow mb-3">Full-field reach forecasts · lower is better</div>
            <div
              className="panel overflow-x-auto focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]"
              role="region"
              aria-label="Full-field reach forecast scores"
              tabIndex={0}
            >
              <table className="w-full min-w-[880px] text-[12px]">
                <thead className="mono text-[10px] uppercase tracking-wider text-[var(--color-faint)]">
                  <tr className="border-b border-[var(--color-line)]">
                    <th rowSpan={2} className="px-4 py-2.5 text-left">Stage</th>
                    <th rowSpan={2} className="px-3 py-2.5 text-right">Resolved</th>
                    <th colSpan={3} className="border-l border-[var(--color-line)] px-3 py-2 text-center">Log-loss ↓</th>
                    <th colSpan={3} className="border-l border-[var(--color-line)] px-3 py-2 text-center">Brier ↓</th>
                  </tr>
                  <tr className="border-b border-[var(--color-line)]">
                    {(["DEUCE", sourceName, "Δ"] as const).map((label, index) => (
                      <th key={`ll-${label}`} className={`${index === 0 ? "border-l border-[var(--color-line)] " : ""}px-3 py-2 text-right`}>{label}</th>
                    ))}
                    {(["DEUCE", sourceName, "Δ"] as const).map((label, index) => (
                      <th key={`brier-${label}`} className={`${index === 0 ? "border-l border-[var(--color-line)] " : ""}px-3 py-2 text-right`}>{label}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="mono">
                  {reach.stages.map((stage) => {
                    const loglossDelta = externalMinusDeuce(stage.tennisAbstract.logloss, stage.deuce.logloss);
                    const brierDelta = externalMinusDeuce(stage.tennisAbstract.brier, stage.deuce.brier);
                    return (
                      <tr key={stage.stage} className="border-b border-[var(--color-line)]/50">
                        <td className="px-4 py-2.5 font-[var(--font-body)] text-[var(--color-text)]">{benchmarkStageLabel(stage.stage)}</td>
                        <td className="px-3 py-2.5 text-right text-[var(--color-faint)]">
                          {stage.resolved}/{stage.n}
                        </td>
                        <td className="border-l border-[var(--color-line)] px-3 py-2.5 text-right">{formatBenchmarkMetric(stage.deuce.logloss)}</td>
                        <td className="px-3 py-2.5 text-right">{formatBenchmarkMetric(stage.tennisAbstract.logloss)}</td>
                        <td className="px-3 py-2.5 text-right" style={{ color: DELTA_COLOR[deltaVerdict(loglossDelta)] }}>{formatBenchmarkDelta(loglossDelta)}</td>
                        <td className="border-l border-[var(--color-line)] px-3 py-2.5 text-right">{formatBenchmarkMetric(stage.deuce.brier)}</td>
                        <td className="px-3 py-2.5 text-right">{formatBenchmarkMetric(stage.tennisAbstract.brier)}</td>
                        <td className="px-3 py-2.5 text-right" style={{ color: DELTA_COLOR[deltaVerdict(brierDelta)] }}>{formatBenchmarkDelta(brierDelta)}</td>
                      </tr>
                    );
                  })}
                  {aggregates.map(({ key, label, value }) => {
                    const loglossDelta = aggregateDelta(value, "logloss");
                    const brierDelta = aggregateDelta(value, "brier");
                    return (
                      <tr key={key} className="border-b border-[var(--color-line)]/50 bg-[var(--color-accent-dim)]">
                        <td className="px-4 py-2.5 font-[var(--font-body)] text-[var(--color-text)]">{label}</td>
                        <td className="px-3 py-2.5 text-right text-[var(--color-faint)]">n{Math.min(value.deuce.n, value.tennisAbstract.n)}</td>
                        <td className="border-l border-[var(--color-line)] px-3 py-2.5 text-right">{formatBenchmarkMetric(value.deuce.logloss)}</td>
                        <td className="px-3 py-2.5 text-right">{formatBenchmarkMetric(value.tennisAbstract.logloss)}</td>
                        <td className="px-3 py-2.5 text-right" style={{ color: DELTA_COLOR[deltaVerdict(loglossDelta)] }}>{formatBenchmarkDelta(loglossDelta)}</td>
                        <td className="border-l border-[var(--color-line)] px-3 py-2.5 text-right">{formatBenchmarkMetric(value.deuce.brier)}</td>
                        <td className="px-3 py-2.5 text-right">{formatBenchmarkMetric(value.tennisAbstract.brier)}</td>
                        <td className="px-3 py-2.5 text-right" style={{ color: DELTA_COLOR[deltaVerdict(brierDelta)] }}>{formatBenchmarkDelta(brierDelta)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="mono mt-2 text-[10px] text-[var(--color-faint)]">
              Stage cells score each frozen player cohort as outcomes resolve. Δ remains {sourceName}{" "}− DEUCE.
            </div>
          </div>
        )}

        <div className="mt-5 border-t border-[var(--color-line)] pt-4 text-[12px] leading-relaxed text-[var(--color-faint)]">
          <div className="flex flex-wrap gap-x-4 gap-y-1">
            <span>External forecast captured {formatBenchmarkTimestamp(data.source.capturedAt)}</span>
            {data.source.lastModified && <span>Source modified {formatBenchmarkTimestamp(data.source.lastModified)}</span>}
            <span>
              Source: {sourceUrl ? (
                <a href={sourceUrl} target="_blank" rel="noopener noreferrer" className="text-[var(--color-accent)] hover:underline">
                  {sourceName}{" "}↗
                </a>
              ) : sourceName}
            </span>
          </div>
          {data.caveats.length > 0 && (
            <ul className="mt-2 list-disc space-y-1 pl-4">
              {data.caveats.map((caveat, index) => <li key={`${caveat}-${index}`}>{caveat}</li>)}
            </ul>
          )}
          {!hasDescriptiveCaveat && (
            <p className="mt-2 text-[var(--color-muted)]">
              This is one tournament and a descriptive comparison—not evidence that either forecasting method is generally better.
            </p>
          )}
        </div>
      </section>
    </Reveal>
  );
}

export function TennisAbstractFallback({
  benchmark,
  ordinaryTrackReady,
  trackLoading,
}: {
  benchmark: TennisAbstractBenchmark | null;
  ordinaryTrackReady: boolean;
  trackLoading: boolean;
}) {
  if (!benchmark || ordinaryTrackReady || trackLoading) return null;
  return <TennisAbstractSection data={benchmark} />;
}

export default function TrackPage() {
  const { tour } = useTour();
  const { data, loading } = useData<Track>("track.json");
  const { data: players } = useData<{ name: string }[]>("players.json");
  const { data: benchmarkArtifact } = useData<unknown>("tennis-abstract.json");
  const benchmark = isTennisAbstractBenchmark(benchmarkArtifact, tour) ? benchmarkArtifact : null;
  const profileRoster = useMemo(() => new Set((players ?? []).map((player) => player.name)), [players]);

  const mf = data?.matchForecasts;
  const to = data?.tournamentOdds;
  const empty = !!mf && mf.graded === 0;
  const ordinaryTrackReady = !!data && !!mf && !!to;

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

          {benchmark && <TennisAbstractSection data={benchmark} />}

          {/* calibration */}
          {mf.calibration.length > 0 && (
            <Reveal delay={0.05}>
              <div className="mt-8">
                <div className="eyebrow mb-3">Calibration — predicted vs actual win rate (live forecasts)</div>
                <div className="panel p-5">
                  <CalibrationChart bins={mf.calibration} />
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
                          profileRoster={profileRoster}
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

      <TennisAbstractFallback
        benchmark={benchmark}
        ordinaryTrackReady={ordinaryTrackReady}
        trackLoading={loading}
      />

      {data && !mf && (
        <div className="panel mt-8 p-5 text-[14px] text-[var(--color-muted)]">No forecast data yet.</div>
      )}
    </div>
  );
}
