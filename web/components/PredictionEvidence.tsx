import { EVIDENCE_LABELS, type EvidenceSignal, type PredictionEvidenceData } from "@/lib/evidence";
import { pct, STYLE_LABEL } from "@/lib/ui";

type Components = { eloBlend: number | null; pointModel: number | null; combiner: number | null };

const num = (value: unknown): number | null =>
  typeof value === "number" && Number.isFinite(value) ? value : null;

function factLine(signal: EvidenceSignal, a: string, b: string): string {
  const f = signal.facts ?? {};
  if (!signal.available) {
    if (signal.key === "home") return "No reliable event-host context for this matchup.";
    if (signal.key === "h2h") return "No prior meeting is recorded.";
    if (signal.key === "style") return "Both players need adequate charted-match coverage.";
    return "Evidence unavailable for this matchup.";
  }
  if (signal.key === "surfaceElo") {
    return `${a} ${num(f.a)?.toFixed(0) ?? "—"} · ${b} ${num(f.b)?.toFixed(0) ?? "—"}`;
  }
  if (signal.key === "serveReturn") {
    const p = num(f.pointProbabilityA);
    return p == null ? "Opponent-adjusted point model." : `Point model: ${pct(p, 1)} for ${a}.`;
  }
  if (signal.key === "form") {
    return `90-day form: ${num(f.form90A)?.toFixed(0) ?? "—"} vs ${num(f.form90B)?.toFixed(0) ?? "—"} Elo.`;
  }
  if (signal.key === "rest") {
    return `Days since play: ${num(f.daysSinceA)?.toFixed(0) ?? "—"} vs ${num(f.daysSinceB)?.toFixed(0) ?? "—"}.`;
  }
  if (signal.key === "home") {
    if (f.playerAHome) return `${a} is playing in the recorded host country.`;
    if (f.playerBHome) return `${b} is playing in the recorded host country.`;
    return "Neither player matches the recorded host country.";
  }
  if (signal.key === "h2h") {
    return `Recorded H2H: ${a} ${num(f.winsA)?.toFixed(0) ?? 0}–${num(f.winsB)?.toFixed(0) ?? 0} ${b}.`;
  }
  const first = Array.isArray(f.contrasts) ? f.contrasts[0] as Record<string, unknown> | undefined : undefined;
  const label = first?.key ? STYLE_LABEL[String(first.key)] ?? String(first.key) : null;
  return label ? `Largest charted contrast: ${label}.` : "Charted style differences are available.";
}

export default function PredictionEvidence({
  evidence,
  components,
  compact = false,
}: {
  evidence?: PredictionEvidenceData | null;
  components?: Components | null;
  compact?: boolean;
}) {
  if (!evidence && !components) return null;
  const signals = evidence?.signals ?? [];
  const shown = compact ? signals.slice(0, 3) : signals;
  return (
    <div data-model-evidence="evidence-v1">
      {components && (
        <div className="grid grid-cols-3 gap-2 text-center">
          {([
            ["Elo", components.eloBlend],
            ["Points", components.pointModel],
            ["Final", components.combiner],
          ] as const).map(([label, value]) => (
            <div key={label} className="rounded-md border border-[var(--color-line)] px-2 py-1.5">
              <div className="mono text-[9px] uppercase text-[var(--color-faint)]">{label}</div>
              <div className="mono text-[11px]">{value == null ? "—" : pct(value, compact ? 0 : 1)}</div>
            </div>
          ))}
        </div>
      )}

      {shown.length > 0 && (
        <div className="mt-3 space-y-1.5">
          {shown.map((signal, index) => {
            const strength = Math.abs(signal.impactPp);
            return (
              <div key={signal.key} className="rounded-md border border-[var(--color-line)] px-3 py-2">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-xs font-medium text-[var(--color-text)]">
                    {index < 3 && signal.available ? `${index + 1}. ` : ""}{EVIDENCE_LABELS[signal.key]}
                  </span>
                  <span className="mono text-[10px] text-[var(--color-muted)]">
                    {!signal.available ? "unavailable" : signal.supports && strength >= 0.05
                      ? `${signal.impactPp > 0 ? "+" : ""}${signal.impactPp.toFixed(1)} pp · ${signal.supports}`
                      : "near neutral"}
                  </span>
                </div>
                {!compact && evidence && (
                  <div className="mt-1 text-[10px] leading-relaxed text-[var(--color-faint)]">
                    {factLine(signal, evidence.playerA, evidence.playerB)}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
      <p className="mt-3 text-[10px] leading-relaxed text-[var(--color-faint)]">
        Model evidence, not a causal explanation. Each signed value is this model&apos;s
        sensitivity when one input group is neutralized; interactions mean the values do not add up.
      </p>
    </div>
  );
}
