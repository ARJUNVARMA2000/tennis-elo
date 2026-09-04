import { calibrationInterval, type CalibrationBin } from "@/lib/calibration";
import { pct } from "@/lib/ui";

/** Shared probability ruler: stable geometry, visible counts, and no motion needed to read it. */
export default function CalibrationChart({ bins }: { bins: CalibrationBin[] }) {
  return (
    <div data-calibration="counts+wilson-v1">
      <div className="space-y-4">
        {bins.map((bin) => {
          const interval = calibrationInterval(bin.actual, bin.n);
          const valid = interval && Number.isFinite(bin.pred) && bin.pred >= 0 && bin.pred <= 1;
          const sparse = bin.n < 30;
          return (
            <div key={bin.bin} className="min-w-0" data-calibration-bin={bin.bin}>
              <div className="mb-2 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 text-[11px]">
                <span className="mono text-[var(--color-muted)]">{bin.bin}</span>
                <span className="mono text-[var(--color-muted)]">n = {Number.isInteger(bin.n) && bin.n >= 0 ? bin.n.toLocaleString("en-US") : "—"}{sparse && bin.n > 0 && <span className="ml-2 font-[var(--font-body)]">Small sample</span>}</span>
              </div>
              {valid ? <>
                <div role="img" aria-label={`${bin.bin}: predicted ${pct(bin.pred, 1)}, observed ${pct(bin.actual, 1)}; approximate 95% interval ${pct(interval[0], 1)} to ${pct(interval[1], 1)}; ${bin.n} matches${sparse ? ", small sample" : ""}`} className="relative mx-1 h-5">
                  <div className="absolute inset-x-0 top-1/2 h-px bg-[var(--color-line2)]" />
                  <div className={`absolute top-1/2 h-2 -translate-y-1/2 border-x border-current ${sparse ? "text-[var(--color-muted)]" : "text-[var(--color-win)]"}`} style={{ left: `${interval[0] * 100}%`, width: `${(interval[1] - interval[0]) * 100}%` }}>
                    <div className={`absolute inset-x-0 top-1/2 border-t border-current ${sparse ? "border-dashed" : ""}`} />
                  </div>
                  <span className="absolute inset-y-0 w-0.5 -translate-x-1/2 bg-[var(--color-accent)]" style={{ left: `${bin.pred * 100}%` }} />
                  <span className={`absolute top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-[var(--color-panel)] ${sparse ? "bg-[var(--color-muted)]" : "bg-[var(--color-win)]"}`} style={{ left: `${bin.actual * 100}%` }} />
                </div>
                <div className="mt-1 flex flex-wrap justify-between gap-x-3 gap-y-1 text-[11px] text-[var(--color-muted)]">
                  <span>{pct(bin.pred, 0)} predicted → {pct(bin.actual, 0)} observed</span>
                  <span>95% interval: {pct(interval[0], 0)}–{pct(interval[1], 0)}</span>
                </div>
              </> : <p className="text-[12px] text-[var(--color-muted)]">No scored observations available.</p>}
            </div>
          );
        })}
      </div>
      <p className="mt-4 border-t border-[var(--color-line)] pt-3 text-[11px] leading-relaxed text-[var(--color-muted)]">
        Tick: predicted · dot: observed · whisker: approximate 95% interval. All rulers run from 0% to 100%.
        Bins with fewer than 30 matches are marked as small samples. Intervals describe sampling uncertainty;
        related matches and rounded source rates limit their precision.
      </p>
    </div>
  );
}
