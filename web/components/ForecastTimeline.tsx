import type { ForecastHistory } from "@/lib/upcoming";

const timeLabel = (value?: string) => {
  if (!value) return "Unknown time";
  const parsed = new Date(value);
  return Number.isNaN(parsed.valueOf()) ? value : parsed.toLocaleString([], {
    month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
  });
};

export default function ForecastTimeline({ forecast, player }: { forecast: ForecastHistory; player: string }) {
  const points = forecast.timeline ?? [];
  const min = Math.min(...points.map((point) => point.p), forecast.first, forecast.current);
  const max = Math.max(...points.map((point) => point.p), forecast.first, forecast.current);
  const span = Math.max(0.02, max - min);
  const polyline = points.map((point, index) => {
    const x = points.length <= 1 ? 50 : index * 100 / (points.length - 1);
    const y = 38 - ((point.p - min) / span) * 32;
    return `${x},${y}`;
  }).join(" ");
  return (
    <details className="mt-3" data-forecast-timeline="timeline-v1">
      <summary className="mono cursor-pointer text-[10px] text-[var(--color-muted)]">
        Forecast history · {forecast.first.toLocaleString(undefined, { style: "percent", maximumFractionDigits: 1 })}
        {" → "}{forecast.current.toLocaleString(undefined, { style: "percent", maximumFractionDigits: 1 })}
        {" · "}{forecast.delta >= 0 ? "+" : ""}{(forecast.delta * 100).toFixed(1)} pp
      </summary>
      {points.length > 0 ? (
        <>
          <svg viewBox="0 0 100 42" role="img" aria-label={`${player} forecast probability over time`} className="mt-2 h-20 w-full overflow-visible">
            <line x1="0" x2="100" y1="38" y2="38" stroke="var(--color-line)" strokeWidth="0.8" />
            {points.length > 1
              ? <polyline points={polyline} fill="none" stroke="var(--color-accent)" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
              : <circle cx="50" cy="22" r="2" fill="var(--color-accent)" />}
            {points.map((point, index) => {
              const x = points.length <= 1 ? 50 : index * 100 / (points.length - 1);
              const y = 38 - ((point.p - min) / span) * 32;
              return <circle key={`${point.asOf}-${index}`} cx={x} cy={y} r={point.firstSighting ? 1.8 : 1.2} fill={point.firstSighting ? "var(--color-champ)" : "var(--color-accent)"}>
                <title>{timeLabel(point.asOf)} · {(point.p * 100).toFixed(1)}% · model {point.modelVersion ?? "unknown"}</title>
              </circle>;
            })}
          </svg>
          <div className="data-scroll mt-2 overflow-x-auto">
            <table className="w-full min-w-[620px] text-left text-[10px]">
              <thead className="text-[var(--color-faint)]"><tr><th className="pb-1">Observed</th><th className="pb-1 text-right">P({player})</th><th className="pb-1 text-right">Elo</th><th className="pb-1 text-right">Points</th><th className="pb-1 text-right">Version</th><th className="pb-1 text-right">Status</th></tr></thead>
              <tbody>
                {points.map((point, index) => (
                  <tr key={`${point.asOf}-${index}`} className="border-t border-[var(--color-line)]">
                    <td className="py-1">{timeLabel(point.asOf)}</td>
                    <td className="mono py-1 text-right">{(point.p * 100).toFixed(1)}%</td>
                    <td className="mono py-1 text-right">{point.components?.eloBlend == null ? "—" : `${(point.components.eloBlend * 100).toFixed(1)}%`}</td>
                    <td className="mono py-1 text-right">{point.components?.pointModel == null ? "—" : `${(point.components.pointModel * 100).toFixed(1)}%`}</td>
                    <td className="mono py-1 text-right text-[var(--color-faint)]">{point.modelVersion ?? "—"}</td>
                    <td className="py-1 text-right text-[var(--color-faint)]">{point.firstSighting ? "published call" : "refresh"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <div className="mt-2 text-[10px] text-[var(--color-faint)]">Only the first/current summary is available for this legacy forecast.</div>
      )}
      <div className="mt-2 text-[10px] text-[var(--color-faint)]">Model/data refreshes—not betting-market movement or a causal explanation.</div>
    </details>
  );
}
