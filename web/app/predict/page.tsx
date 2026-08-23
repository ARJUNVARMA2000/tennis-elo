"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { useData, useTour } from "@/lib/tour";
import { SURFACES, pct, scoreDist } from "@/lib/ui";
import { setSearchParam } from "@/lib/url";
import { PageHead, Loading, SurfacePill, Reveal, ProbBar, AnimatedNumber } from "@/components/bits";
import Dropdown, { type DropdownOption } from "@/components/Dropdown";
import { SPRING, stagger, pop } from "@/lib/motion";
import { matrixProbability, useMatrixShard } from "@/lib/matrix";
import { orientForecast, useUpcomingDetail, useUpcomingEvents } from "@/lib/upcoming";
import ForecastTimeline from "@/components/ForecastTimeline";
import PredictionEvidence from "@/components/PredictionEvidence";
import PredictionSummary from "@/components/PredictionSummary";
import { matrixEvidence, orientEvidence } from "@/lib/evidence";

export default function Predict() {
  const { tour } = useTour();
  return (
    <div className="pb-16" data-prediction-explanation-contract="grouped-evidence-not-causation-v2">
      <PageHead
        eyebrow={`${tour.toUpperCase()} · head to head`}
        title="Match Predictor"
        sub="Pick any two players, a surface and a format. The XGBoost combiner returns a calibrated win probability; the most likely set scores are back-solved from it with the Markov set model."
      />
      {/* useSearchParams (shareable ?a=&b= matchup links) needs a Suspense boundary under static export */}
      <Suspense fallback={<Loading variant="forecast" />}>
        <PredictInner />
      </Suspense>
    </div>
  );
}

function PredictInner() {
  const { tour } = useTour();
  const { data: roster } = useData<{ name: string; eloRank: number }[]>("players.json");
  const { data: upcoming } = useUpcomingEvents();
  const router = useRouter();
  const pathname = usePathname();
  const sp = useSearchParams();
  const urlA = sp.get("a");
  const urlB = sp.get("b");
  const [a, setA] = useState(0);
  const [b, setB] = useState(1);
  const [surface, setSurface] = useState("Hard");
  const [bo, setBo] = useState(3);
  const { index: data, shard, format, loading } = useMatrixShard(surface, bo);

  const players = useMemo(() => data?.players || [], [data]);
  const formats = useMemo(() => data?.formats || [3], [data]);

  // Deep links carry NAMES (matrix indices are unstable across data refreshes);
  // resolve them against the loaded matrix, ignore unknowns and degenerate pairs,
  // and strip params that don't resolve (e.g. an ATP pair after switching to WTA).
  useEffect(() => {
    if (!players.length) return;
    const ia = urlA ? players.indexOf(urlA) : -1;
    const ib = urlB ? players.indexOf(urlB) : -1;
    if (ia >= 0 && ib >= 0 && ia !== ib) { setA(ia); setB(ib); }
    else {
      if (ia >= 0 && ia !== b) setA(ia);
      if (ib >= 0 && ib !== a) setB(ib);
    }
    if ((urlA && ia < 0) || (urlB && ib < 0)) {
      let q = window.location.search;
      if (urlA && ia < 0) q = setSearchParam(q, "a", null);
      if (urlB && ib < 0) q = setSearchParam(q, "b", null);
      router.replace(`${pathname}${q}`, { scroll: false });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [players, urlA, urlB]);

  const pickA = (i: number) => {
    setA(i);
    if (players[i]) router.replace(`${pathname}${setSearchParam(window.location.search, "a", players[i])}`, { scroll: false });
  };
  const pickB = (i: number) => {
    setB(i);
    if (players[i]) router.replace(`${pathname}${setSearchParam(window.location.search, "b", players[i])}`, { scroll: false });
  };

  // Elo rank sublabels for the pickers, where the roster has the player.
  const options: DropdownOption[] = useMemo(() => {
    const rank = new Map((roster ?? []).map((r) => [r.name, r.eloRank]));
    return players.map((name, i) => ({
      value: String(i),
      label: name,
      sublabel: rank.has(name) ? `#${rank.get(name)}` : undefined,
    }));
  }, [players, roster]);

  const p = useMemo(() => {
    if (!data || a === b) return null;
    return matrixProbability(shard, "combiner", a, b);
  }, [data, shard, a, b]);

  const components = useMemo(() => {
    if (!shard || a === b) return null;
    return {
      eloBlend: matrixProbability(shard, "eloBlend", a, b),
      pointModel: matrixProbability(shard, "pointModel", a, b),
      combiner: matrixProbability(shard, "combiner", a, b),
    };
  }, [shard, a, b]);

  const scheduled = useMemo(() => (upcoming ?? []).find((m) =>
      m.surface === surface && m.bestOf === format
      && ((m.playerA === players[a] && m.playerB === players[b])
        || (m.playerA === players[b] && m.playerB === players[a])),
  ), [upcoming, surface, format, players, a, b]);
  const scheduledDetail = useUpcomingDetail(scheduled, Boolean(scheduled));
  const scheduledFull = useMemo(
    () => scheduled ? { ...scheduled, ...(scheduledDetail.data ?? {}) } : undefined,
    [scheduled, scheduledDetail.data],
  );

  const movement = useMemo(() => {
    const row = scheduledFull;
    if (!row?.forecast) return null;
    return orientForecast(row.forecast, row.playerA !== players[a]);
  }, [scheduledFull, players, a]);
  const evidence = useMemo(
    () => scheduledFull?.evidence
      ? orientEvidence(scheduledFull.evidence, scheduledFull.playerA !== players[a])
      : matrixEvidence(shard, a, b),
    [scheduledFull, players, a, shard, b],
  );

  const dist = p != null ? scoreDist(p, format) : [];

  return (
    <>
      {loading && <Loading variant="forecast" />}

      {data && (
        <>
          <Reveal>
            <fieldset
              className="panel mt-8"
              data-prediction-setup="fine-tune-card-adaptation-v1"
            >
              <legend className="sr-only">Prediction setup</legend>
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--color-line)] px-4 py-3 sm:px-5">
                <div>
                  <div className="eyebrow !text-[10px] !text-[var(--color-text)]">Prediction setup</div>
                  <p className="mt-1 text-[11px] text-[var(--color-muted)]">
                    Fine-tune the matchup and match conditions.
                  </p>
                </div>
                <span className="chip text-[var(--color-muted)]">{surface} · Bo{format}</span>
              </div>

              <div className="p-4 sm:p-5">
                <div className="grid gap-3 sm:grid-cols-2">
                  <Picker label="Player A" value={a} onChange={pickA} options={options} accent="var(--color-accent)" />
                  <Picker label="Player B" value={b} onChange={pickB} options={options} accent="var(--color-cmp)" />
                </div>

                <div className="panel-inset mt-4 grid gap-4 p-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
                  <div>
                    <div id="prediction-surface-label" className="eyebrow mb-2 !text-[9px]">Court surface</div>
                    <div
                      role="group"
                      aria-labelledby="prediction-surface-label"
                      className="flex flex-wrap items-center gap-2"
                    >
                      {SURFACES.map((s) => (
                        <SurfacePill key={s} s={s} active={surface === s} onClick={() => setSurface(s)} />
                      ))}
                    </div>
                  </div>

                  <div>
                    <div id="prediction-format-label" className="eyebrow mb-2 !text-[9px]">Match format</div>
                    <div
                      role="group"
                      aria-labelledby="prediction-format-label"
                      className="flex items-center rounded-md border border-[var(--color-line)] p-0.5"
                    >
                      {formats.map((f) => (
                        <button
                          key={f}
                          type="button"
                          aria-pressed={format === f}
                          onClick={() => setBo(f)}
                          className="mono relative min-h-9 rounded-[5px] px-3 py-1 text-[11px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]"
                        >
                          {format === f && (
                            <motion.span
                              layoutId="bo-thumb"
                              className="absolute inset-0 rounded-[5px] bg-[var(--color-text)]"
                              transition={SPRING}
                            />
                          )}
                          <span
                            className="relative z-10 transition-colors"
                            style={{ color: format === f ? "var(--color-on-accent)" : "var(--color-muted)" }}
                          >
                            Bo{f}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </fieldset>
          </Reveal>

          {p != null && (
            <Reveal delay={0.05}>
              <div className="panel mt-6 p-5 sm:p-6 lg:p-8">
                <div className="grid gap-5 lg:grid-cols-[minmax(0,1.35fr)_minmax(280px,0.65fr)]">
                  <section
                    aria-label="Predicted win probabilities"
                    aria-live="polite"
                    className="panel-inset flex min-w-0 flex-col justify-center p-5 sm:p-6"
                  >
                    <div className="flex items-end justify-between gap-4">
                      <div className="min-w-0 flex-1">
                        <div className="display text-xl leading-tight sm:truncate sm:text-3xl">{players[a]}</div>
                        <AnimatedNumber
                          value={p * 100}
                          decimals={1}
                          suffix="%"
                          className="mt-1 block text-3xl text-[var(--color-accent)]"
                        />
                      </div>
                      <div className="mono pb-1 text-[var(--color-faint)]">vs</div>
                      <div className="min-w-0 flex-1 text-right">
                        <div className="display text-xl leading-tight sm:truncate sm:text-3xl">{players[b]}</div>
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
                    <p className="mono mt-2 text-[9px] uppercase tracking-wider text-[var(--color-muted)]">
                      Calibrated pre-match probability · {surface} · Bo{format}
                    </p>
                  </section>

                  <PredictionSummary
                    probabilityA={p}
                    playerA={players[a]}
                    playerB={players[b]}
                    surface={surface}
                    bestOf={format}
                    tour={tour}
                  />
                </div>

                {(components || evidence) && (
                  <details id="model-evidence" className="panel-inset mt-6 p-4">
                    <summary className="flex min-h-9 cursor-pointer list-none items-center justify-between gap-3 text-sm font-medium text-[var(--color-text)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]">
                      <span className="inline-flex items-center gap-2">
                        <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-[var(--color-accent)]" />
                        Model evidence
                      </span>
                      <span className="mono text-[9px] uppercase tracking-wider text-[var(--color-faint)]">
                        {evidence ? `${evidence.signals.filter((signal) => signal.available).length} available` : "model stack"}
                      </span>
                    </summary>
                    <div className="mt-4" aria-live="polite">
                      <PredictionEvidence evidence={evidence} components={components} />
                    </div>
                    {movement && (
                      <ForecastTimeline forecast={movement} player={players[a]} />
                    )}
                  </details>
                )}

                <div className="panel-inset mt-8 p-3 sm:p-4">
                  <div className="mono text-[11px] uppercase tracking-wider text-[var(--color-faint)]">
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
                        className="flex items-center justify-between rounded-lg border border-[var(--color-line)] bg-[var(--color-panel)] px-3 py-2"
                      >
                        <span className="mono text-sm" style={{ color: d.a ? "var(--color-accent)" : "var(--color-cmp)" }}>
                          {d.a ? players[a].split(" ").slice(-1) : players[b].split(" ").slice(-1)} {d.label}
                        </span>
                        <span className="mono text-sm text-[var(--color-muted)]">{pct(d.p, 0)}</span>
                      </motion.div>
                    ))}
                  </motion.div>
                </div>
              </div>
            </Reveal>
          )}
          {a === b && <p className="mono mt-6 text-sm text-[var(--color-loss)]">Pick two different players.</p>}
        </>
      )}
    </>
  );
}

function Picker({ label, value, onChange, options, accent }: { label: string; value: number; onChange: (n: number) => void; options: DropdownOption[]; accent: string }) {
  return (
    <div className="block">
      <div className="eyebrow mb-2" style={{ color: accent }}>{label}</div>
      <Dropdown
        searchable
        label={label}
        value={String(value)}
        onChange={(v) => onChange(Number(v))}
        options={options}
      />
    </div>
  );
}
