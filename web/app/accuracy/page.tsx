"use client";

import CalibrationChart from "@/components/CalibrationChart";
import { motion } from "framer-motion";
import { useData, useTour } from "@/lib/tour";
import { pct } from "@/lib/ui";
import { PageHead, Loading, Reveal } from "@/components/bits";
import { EASE } from "@/lib/motion";

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
                <CalibrationChart bins={data.calibration} />
              </div>
            </div>
          </Reveal>
        </>
      )}
    </div>
  );
}
