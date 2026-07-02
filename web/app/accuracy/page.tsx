"use client";

import { motion } from "framer-motion";
import { useData, useTour } from "@/lib/tour";
import { pct } from "@/lib/ui";
import { PageHead, Loading, Reveal } from "@/components/bits";
import { EASE, SPRING_SOFT } from "@/lib/motion";

type Accuracy = {
  window: string; n: number;
  models: Record<string, { n: number; acc: number; logloss: number; brier: number }>;
  marketAnchor: { acc: number; brier: number };
  calibration: { bin: string; n: number; pred: number; actual: number }[];
};

const LABELS: Record<string, string> = { eloBlend: "Elo (surface-blended)", pointModel: "Serve/return point model", combiner: "XGBoost combiner" };

export default function AccuracyPage() {
  const { tour } = useTour();
  const { data, loading } = useData<Accuracy>("accuracy.json");
  const modelRows = data ? Object.entries(data.models) : [];

  return (
    <div className="pb-16">
      <PageHead
        eyebrow={`${tour.toUpperCase()} · walk-forward · ${data?.window ?? ""}`}
        title="Vs the Market"
        sub="Every prediction is out-of-sample: trained on the past, scored on the future, never using betting odds as an input. Brier and log-loss are proper scores — lower is better."
      />

      {loading && <Loading />}

      {data && (
        <>
          <Reveal>
            <div className="mt-8 panel overflow-hidden">
              <table className="w-full text-[13px]">
                <thead className="mono text-[11px] uppercase tracking-wider text-[var(--color-faint)]">
                  <tr className="border-b border-[var(--color-line)]">
                    <th className="px-4 py-3 text-left">Model</th>
                    <th className="px-4 py-3 text-right">Accuracy</th>
                    <th className="px-4 py-3 text-right">Log-loss</th>
                    <th className="px-4 py-3 text-right">Brier</th>
                  </tr>
                </thead>
                <tbody className="mono">
                  {modelRows.map(([k, m], i) => (
                    <motion.tr
                      key={k}
                      initial={{ opacity: 0, y: 6 }}
                      whileInView={{ opacity: 1, y: 0 }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.35, ease: EASE, delay: Math.min(i * 0.05, 0.3) }}
                      className="row-glow border-b border-[var(--color-line)]/50"
                      style={{ background: k === "combiner" ? "var(--color-accent-dim)" : undefined }}
                    >
                      <td className="px-4 py-3 font-[var(--font-body)]">{LABELS[k] || k}</td>
                      <td className="px-4 py-3 text-right">{pct(m.acc, 1)}</td>
                      <td className="px-4 py-3 text-right text-[var(--color-muted)]">{m.logloss.toFixed(4)}</td>
                      <td className="px-4 py-3 text-right" style={{ color: k === "combiner" ? "var(--color-accent)" : undefined }}>{m.brier.toFixed(4)}</td>
                    </motion.tr>
                  ))}
                  <motion.tr
                    initial={{ opacity: 0, y: 6 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.35, ease: EASE, delay: Math.min(modelRows.length * 0.05, 0.3) }}
                    className="text-[var(--color-faint)]"
                  >
                    <td className="px-4 py-3">Bookmaker (literature anchor)</td>
                    <td className="px-4 py-3 text-right">{pct(data.marketAnchor.acc, 1)}</td>
                    <td className="px-4 py-3 text-right">—</td>
                    <td className="px-4 py-3 text-right">{data.marketAnchor.brier.toFixed(3)}</td>
                  </motion.tr>
                </tbody>
              </table>
            </div>
          </Reveal>

          <Reveal delay={0.05}>
            <div className="mt-8">
              <div className="eyebrow mb-3">Calibration — predicted vs actual win rate</div>
              <div className="panel p-5">
                {data.calibration.map((c, i) => (
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
                    <span className="mono w-24 text-right text-xs text-[var(--color-muted)]">
                      {pct(c.pred, 0)} → {pct(c.actual, 0)}
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
        </>
      )}
    </div>
  );
}
