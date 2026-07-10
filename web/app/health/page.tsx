"use client";

import { useEffect, useState } from "react";
import { useRootData } from "@/lib/tour";
import { PageHead, Loading, Reveal } from "@/components/bits";
import { rel } from "@/components/Freshness";
import {
  type CheckRow, type Drift, type HealthReport, type Tone, type TourReport,
  TONE_COLOR, REPO, checkTone, checkStatusLabel, driftTone, driftLabel,
  overall, fmtValue, fmtLimit,
} from "@/lib/health";

type Meta = { lastUpdated?: string; matches?: number; modelVersion?: string };
type Track = { matchForecasts?: { drift?: Drift } };
type Run = { id: number; conclusion: string | null; run_started_at: string; html_url: string; event: string };

function Dot({ tone, pulse = false }: { tone: Tone; pulse?: boolean }) {
  return (
    <span
      aria-hidden="true"
      className={`inline-block h-1.5 w-1.5 shrink-0 rounded-full ${pulse ? "live-dot" : ""}`}
      style={{ background: TONE_COLOR[tone] }}
    />
  );
}

function StatusWord({ tone, label }: { tone: Tone; label: string }) {
  return (
    <span className="mono inline-flex items-center gap-1.5 text-[11px] uppercase tracking-wider" style={{ color: TONE_COLOR[tone] }}>
      <Dot tone={tone} />
      {label}
    </span>
  );
}

/** Statuspage-style strip of the last refresh runs, oldest → newest. Best-effort:
    the unauthenticated GitHub API rate-limits at 60/h per IP — any failure renders
    nothing rather than an error. */
function RunsStrip() {
  const [runs, setRuns] = useState<Run[] | null>(null);
  useEffect(() => {
    let live = true;
    fetch(`https://api.github.com/repos/${REPO}/actions/workflows/refresh.yml/runs?per_page=30`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((j) => {
        if (live && Array.isArray(j.workflow_runs)) setRuns(j.workflow_runs.slice().reverse());
      })
      .catch(() => {});
    return () => {
      live = false;
    };
  }, []);
  if (!runs?.length) return null;
  const tone = (c: string | null): Tone => (c === "success" ? "ok" : c === "failure" ? "fail" : "muted");
  return (
    <div className="panel mt-4 p-4">
      <div className="flex items-center justify-between">
        <div className="eyebrow !text-[10px]">pipeline runs · last {runs.length}</div>
        <div className="mono text-[10px] text-[var(--color-faint)]">oldest → newest</div>
      </div>
      <div className="mt-3 flex items-end gap-[3px]">
        {runs.map((r) => (
          <a
            key={r.id}
            href={r.html_url}
            target="_blank"
            rel="noreferrer"
            title={`${r.run_started_at.slice(0, 16).replace("T", " ")}Z · ${r.event} · ${r.conclusion ?? "in progress"}`}
            className="h-6 flex-1 rounded-[2px] transition-transform hover:scale-y-125"
            style={{ background: TONE_COLOR[tone(r.conclusion)], opacity: r.conclusion ? 0.85 : 0.4, maxWidth: 14 }}
          />
        ))}
      </div>
    </div>
  );
}

function SourceChecks({ t }: { t: TourReport }) {
  return (
    <table className="w-full text-[13px]">
      <thead className="mono text-[11px] uppercase tracking-wider text-[var(--color-faint)]">
        <tr className="border-b border-[var(--color-line)]">
          <th className="py-2.5 pr-2 text-left font-normal">Source check</th>
          <th className="py-2.5 pr-2 text-right font-normal">Newest</th>
          <th className="py-2.5 pr-2 text-right font-normal">Age / value</th>
          <th className="py-2.5 pr-2 text-right font-normal">Limit</th>
          <th className="py-2.5 text-right font-normal">Status</th>
        </tr>
      </thead>
      <tbody>
        {t.checks.map((c: CheckRow) => (
          <tr
            key={c.key}
            className="border-b border-[var(--color-line)]/50"
            title={c.problem ?? c.note ?? undefined}
          >
            <td className="py-2.5 pr-2">{c.label}</td>
            <td className="mono py-2.5 pr-2 text-right text-[var(--color-faint)]">{c.date ?? "—"}</td>
            <td className="mono py-2.5 pr-2 text-right" style={{ color: TONE_COLOR[checkTone(c)] }}>
              {fmtValue(c)}
            </td>
            <td className="mono py-2.5 pr-2 text-right text-[var(--color-faint)]">{fmtLimit(c)}</td>
            <td className="py-2.5 text-right">
              <StatusWord tone={checkTone(c)} label={checkStatusLabel(c)} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function TourPanel({ tour, t, now }: { tour: string; t: TourReport; now: number }) {
  const { data: meta } = useRootData<Meta>(`${tour}/meta.json`);
  const { data: track } = useRootData<Track>(`${tour}/track.json`);
  const drift = track?.matchForecasts?.drift;
  const built = meta?.lastUpdated ? rel(meta.lastUpdated, now) : null;
  const outputProblems = t.output.problems;
  return (
    <div className="panel p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div className="display text-lg uppercase">{tour}</div>
        <div className="mono text-[11px] text-[var(--color-faint)]">
          {t.matches.toLocaleString("en-US")} matches · results to {t.date_max ?? "—"}
          {built && <> · built {built}</>}
        </div>
      </div>

      <div className="mt-4">
        <SourceChecks t={t} />
      </div>

      {/* over-limit-but-covered context, spelled out (the amber rows above) */}
      {t.checks.filter((c) => c.ok && c.note).map((c) => (
        <div key={c.key} className="mono mt-3 text-[11px] leading-relaxed text-[var(--color-champ)]">
          {c.label}: {c.note}
        </div>
      ))}

      <div className="mt-5 border-t border-[var(--color-line)] pt-4">
        <div className="flex items-center justify-between">
          <div className="eyebrow !text-[10px]">output integrity</div>
          <StatusWord
            tone={outputProblems.length ? "fail" : "ok"}
            label={outputProblems.length ? `${outputProblems.length} problem${outputProblems.length > 1 ? "s" : ""}` : "all invariants passing"}
          />
        </div>
        {outputProblems.length > 0 && (
          <ul className="mono mt-2 space-y-1 text-[11px] text-[var(--color-loss)]">
            {outputProblems.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        )}
      </div>

      <div className="mt-4 border-t border-[var(--color-line)] pt-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="eyebrow !text-[10px]">forecast log</div>
          <div className="mono text-[11px] text-[var(--color-muted)]">
            {t.output.forecast_lines?.toLocaleString("en-US") ?? "—"} logged · last advanced{" "}
            {t.output.forecast_max_as_of ?? "—"}
          </div>
        </div>
        <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
          <div className="eyebrow !text-[10px]">model drift</div>
          <StatusWord tone={driftTone(drift?.status)} label={driftLabel(drift)} />
        </div>
      </div>
    </div>
  );
}

const BANNER: Record<Tone, { title: string; sub: string }> = {
  ok: { title: "All systems operational", sub: "every source check and output invariant is passing" },
  warn: { title: "Operational — on redundancy", sub: "a source is over its limit but fully covered by another; nothing is alarmed" },
  fail: { title: "Problems detected", sub: "the sentinel has open findings — see the data-health issue" },
  muted: { title: "—", sub: "" },
};

export default function HealthPage() {
  const { data: report, loading, error } = useRootData<HealthReport>("health.json");
  const [now] = useState(() => Date.now());
  const o = report ? overall(report) : null;

  return (
    <div className="pb-16">
      <PageHead
        eyebrow="operations · internal"
        title="System Health"
        sub="Live status of every data source, output invariant and drift monitor — written by the pipeline's data-health sentinel on each run. This page is unlisted; alerting happens through the data-health GitHub issue, not here."
      />

      {loading && <Loading />}

      {error && !report && (
        <div className="panel mt-8 p-5 text-[14px] leading-relaxed text-[var(--color-muted)]">
          No health report is available at <span className="mono">/data/health.json</span> — the sentinel
          hasn&apos;t run since this deploy shipped, or the mirror step failed. Run{" "}
          <span className="mono">python -m tennis_model.data.health</span> in the pipeline to generate it.
        </div>
      )}

      {report && o && (
        <>
          <Reveal>
            <div className="panel mt-8 flex flex-wrap items-center justify-between gap-3 p-5">
              <div className="flex items-center gap-3">
                <span
                  className={`inline-block h-2.5 w-2.5 rounded-full ${o.tone === "ok" ? "live-dot" : ""}`}
                  style={{ background: TONE_COLOR[o.tone] }}
                />
                <div>
                  <div className="text-lg font-semibold" style={{ color: o.tone === "fail" ? "var(--color-loss)" : "var(--color-text)" }}>
                    {o.tone === "fail" ? `${o.problems} problem${o.problems > 1 ? "s" : ""} detected` : BANNER[o.tone].title}
                  </div>
                  <div className="mono mt-0.5 text-[11px] text-[var(--color-faint)]">{BANNER[o.tone].sub}</div>
                </div>
              </div>
              <div className="mono text-right text-[11px] text-[var(--color-muted)]">
                report generated {report.generatedAt ? (rel(report.generatedAt, now) ?? report.generated) : report.generated}
                <div className="text-[var(--color-faint)]">refreshes hourly with the pipeline</div>
              </div>
            </div>
            <RunsStrip />
          </Reveal>

          <Reveal delay={0.05}>
            <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
              {Object.entries(report.tours).map(([tour, t]) => (
                <TourPanel key={tour} tour={tour} t={t} now={now} />
              ))}
            </div>
          </Reveal>

          <Reveal delay={0.08}>
            <div className="mono mt-6 flex flex-wrap gap-x-5 gap-y-1 text-[11px] text-[var(--color-faint)]">
              <a className="transition-colors hover:text-[var(--color-accent)]" href={`https://github.com/${REPO}/actions/workflows/refresh.yml`} target="_blank" rel="noreferrer">
                pipeline runs ↗
              </a>
              <a className="transition-colors hover:text-[var(--color-accent)]" href={`https://github.com/${REPO}/issues?q=label%3Adata-health`} target="_blank" rel="noreferrer">
                data-health issues ↗
              </a>
              <a className="transition-colors hover:text-[var(--color-accent)]" href={`https://github.com/${REPO}/issues?q=label%3Awatchdog`} target="_blank" rel="noreferrer">
                watchdog issues ↗
              </a>
            </div>
          </Reveal>
        </>
      )}
    </div>
  );
}
