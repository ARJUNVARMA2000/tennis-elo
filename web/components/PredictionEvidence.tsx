import { EVIDENCE_LABELS, type EvidenceSignal, type PredictionEvidenceData } from "@/lib/evidence";
import { pct, STYLE_LABEL } from "@/lib/ui";

type Components = { eloBlend: number | null; pointModel: number | null; combiner: number | null };

const num = (value: unknown): number | null =>
  typeof value === "number" && Number.isFinite(value) ? value : null;

export function evidenceFactLine(signal: EvidenceSignal, a: string, b: string): string {
  const f = signal.facts ?? {};
  if (!signal.available) {
    if (signal.key === "home") return "No reliable event-host context for this matchup.";
    if (signal.key === "h2h") return "No prior meeting is recorded.";
    if (signal.key === "style") return "Both players need adequate charted-match coverage.";
    return "Evidence unavailable for this matchup.";
  }
  if (signal.key === "surfaceElo") {
    const left = num(f.a), right = num(f.b);
    return left == null || right == null
      ? "Surface-adjusted rating comparison."
      : `${a} ${left.toFixed(0)} · ${b} ${right.toFixed(0)}`;
  }
  if (signal.key === "serveReturn") {
    const p = num(f.pointProbabilityA);
    return p == null ? "Opponent-adjusted point model." : `Point model: ${pct(p, 1)} for ${a}.`;
  }
  if (signal.key === "form") {
    const left = num(f.form90A), right = num(f.form90B);
    return left == null || right == null
      ? "Recent-results form signal."
      : `90-day form: ${left.toFixed(0)} vs ${right.toFixed(0)} Elo.`;
  }
  if (signal.key === "rest") {
    const left = num(f.daysSinceA), right = num(f.daysSinceB);
    return left == null || right == null
      ? "Rest and recent workload signal."
      : `Days since play: ${left.toFixed(0)} vs ${right.toFixed(0)}.`;
  }
  if (signal.key === "home") {
    if (f.playerAHome) return `${a} is playing in the recorded host country.`;
    if (f.playerBHome) return `${b} is playing in the recorded host country.`;
    return "Neither player matches the recorded host country.";
  }
  if (signal.key === "h2h") {
    const left = num(f.winsA), right = num(f.winsB);
    return left == null || right == null
      ? "Recorded prior-meeting signal."
      : `Recorded H2H: ${a} ${left.toFixed(0)}–${right.toFixed(0)} ${b}.`;
  }
  const first = Array.isArray(f.contrasts) ? f.contrasts[0] as Record<string, unknown> | undefined : undefined;
  const label = first?.key ? STYLE_LABEL[String(first.key)] ?? String(first.key) : null;
  return label ? `Largest charted contrast: ${label}.` : "Charted style differences are available.";
}

function signalPresentation(signal: EvidenceSignal) {
  const strength = Math.abs(signal.impactPp);
  if (!signal.available) {
    return {
      state: "unavailable",
      badge: "Unavailable",
      impact: "No signal",
      tone: "var(--color-faint)",
      width: 0,
    };
  }
  if (!signal.supports || strength < 0.05) {
    return {
      state: "neutral",
      badge: "Near neutral",
      impact: "≈ 0 pp",
      tone: "var(--color-muted)",
      width: 0,
    };
  }
  return {
    state: signal.impactPp > 0 ? "player-a" : "player-b",
    badge: `Supports ${signal.supports}`,
    impact: `${signal.impactPp > 0 ? "+" : ""}${signal.impactPp.toFixed(1)} pp`,
    tone: signal.impactPp > 0 ? "var(--color-accent)" : "var(--color-cmp)",
    width: Math.min(strength / 30, 1) * 50,
  };
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
    <div data-model-evidence="context-cards-v2">
      {components && (
        <div>
          <div className="mb-2 flex items-baseline justify-between gap-3">
            <span className="eyebrow !text-[9px]">Model stack</span>
            <span className="mono text-[9px] text-[var(--color-faint)]">component probabilities</span>
          </div>
          <div className="grid grid-cols-3 gap-2 text-center">
            {([
              ["Surface Elo", components.eloBlend],
              ["Point model", components.pointModel],
              ["Final", components.combiner],
            ] as const).map(([label, value]) => (
              <div key={label} className="panel-inset min-w-0 px-2 py-2">
                <div className="mono truncate text-[8px] uppercase tracking-wider text-[var(--color-faint)]">{label}</div>
                <div
                  className="mono mt-1 text-[11px]"
                  style={{ color: label === "Final" ? "var(--color-accent)" : "var(--color-text)" }}
                >
                  {value == null ? "—" : pct(value, compact ? 0 : 1)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {shown.length > 0 && (
        <div className={`mt-3 grid gap-2 ${compact ? "grid-cols-1" : "sm:grid-cols-2"}`}>
          {shown.map((signal, index) => {
            const presentation = signalPresentation(signal);
            const label = EVIDENCE_LABELS[signal.key];
            return (
              <article
                key={signal.key}
                data-evidence-signal={signal.key}
                data-signal-state={presentation.state}
                aria-label={`${label}: ${presentation.badge}; ${presentation.impact}`}
                className="relative overflow-hidden rounded-lg border border-[var(--color-line)] bg-[var(--color-panel2)]/30 px-3 py-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.018)]"
              >
                <span
                  aria-hidden="true"
                  className="absolute inset-y-0 left-0 w-px"
                  style={{ background: presentation.tone }}
                />
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between sm:gap-3">
                  <div className="flex min-w-0 items-center gap-2">
                    <span className="mono text-[9px] text-[var(--color-faint)]">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <span className="text-xs font-medium text-[var(--color-text)]">{label}</span>
                  </div>
                  <span
                    className="mono max-w-full self-start truncate rounded border px-1.5 py-0.5 text-[8px] uppercase tracking-wider sm:max-w-[55%]"
                    style={{
                      color: presentation.tone,
                      borderColor: `color-mix(in srgb, ${presentation.tone} 36%, var(--color-line))`,
                      background: `color-mix(in srgb, ${presentation.tone} 9%, transparent)`,
                    }}
                    title={presentation.badge}
                  >
                    {presentation.badge}
                  </span>
                </div>
                {!compact && evidence && (
                  <p className="mt-2 min-h-8 text-[10px] leading-relaxed text-[var(--color-muted)]">
                    {evidenceFactLine(signal, evidence.playerA, evidence.playerB)}
                  </p>
                )}
                <div className="mt-2 flex items-center gap-2">
                  <div className="relative h-1 flex-1 overflow-hidden rounded-full bg-white/[0.05]" aria-hidden="true">
                    <span className="absolute inset-y-0 left-1/2 w-px bg-white/15" />
                    {presentation.width > 0 && (
                      <span
                        className="absolute inset-y-0 rounded-full"
                        style={{
                          background: presentation.tone,
                          width: `${presentation.width}%`,
                          ...(signal.impactPp > 0 ? { left: "50%" } : { right: "50%" }),
                        }}
                      />
                    )}
                  </div>
                  <span className="mono w-14 shrink-0 text-right text-[9px]" style={{ color: presentation.tone }}>
                    {presentation.impact}
                  </span>
                </div>
              </article>
            );
          })}
        </div>
      )}
      <p className="mt-3 border-t border-[var(--color-line)] pt-3 text-[10px] leading-relaxed text-[var(--color-muted)]">
        Model evidence, not a causal explanation. Each signed value is this model&apos;s
        sensitivity when one input group is neutralized; interactions mean the values do not add up.
      </p>
    </div>
  );
}
