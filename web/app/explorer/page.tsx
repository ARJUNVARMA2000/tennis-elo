"use client";

import { Suspense, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { useData, useTour } from "@/lib/tour";
import {
  availableAxes, EXPLORER_PRESETS, plottable, sortByAxis,
  type ExplorerAxis, type ExplorerPlayer,
} from "@/lib/ui";
import { playerHref, setSearchParam } from "@/lib/url";
import { PageHead, Loading, Reveal } from "@/components/bits";
import ScatterChart from "@/components/ScatterChart";
import Dropdown from "@/components/Dropdown";
import { SPRING } from "@/lib/motion";

const N_OPTIONS = [25, 50, 100];
const DEFAULT_N = 50;
const lastName = (n: string) => n.split(" ").slice(-1)[0];
// URL defaults are elided so the canonical explorer URL stays clean.
const DEFAULTS = { x: "servePct", y: "returnPct", sort: "elo" };

export default function Explorer() {
  const { tour } = useTour();
  return (
    <div className="pb-16">
      <PageHead
        eyebrow={`${tour.toUpperCase()} · attribute explorer`}
        title="Explorer"
        sub="Pick any two attributes to plot the field against each other, or flip to the table and rank everyone by any single stat. Attributes come straight from the model: ratings, serve/return point-win rates, form, style and bio."
      />
      {/* useSearchParams (shareable axis/sort state) needs a Suspense boundary under static export */}
      <Suspense fallback={<Loading />}>
        <ExplorerInner />
      </Suspense>
    </div>
  );
}

function ExplorerInner() {
  const { tour } = useTour();
  const router = useRouter();
  const pathname = usePathname();
  const sp = useSearchParams();
  const { data, loading } = useData<ExplorerPlayer[]>("players.json");
  const [count, setCount] = useState(DEFAULT_N);
  const [hover, setHover] = useState<string | null>(null);

  const sorted = useMemo(() => (data ? [...data].sort((a, b) => b.elo - a.elo) : []), [data]);
  const field = useMemo(() => sorted.slice(0, count), [sorted, count]);
  const axes = useMemo(() => availableAxes(sorted, tour), [sorted, tour]);

  const axisFor = (key: string | null, fallback: string): ExplorerAxis | undefined =>
    axes.find((a) => a.key === key) ?? axes.find((a) => a.key === fallback) ?? axes[0];

  const view = sp.get("view") === "table" ? "table" : "scatter";
  const xAxis = axisFor(sp.get("x"), DEFAULTS.x);
  const yAxis = axisFor(sp.get("y"), DEFAULTS.y);
  const sortAxis = axisFor(sp.get("sort"), DEFAULTS.sort);
  const dir: "asc" | "desc" = sp.get("dir") === "asc" ? "asc" : "desc";

  const setParams = (kv: Record<string, string | null>) => {
    let q = window.location.search;
    for (const [k, v] of Object.entries(kv)) q = setSearchParam(q, k, v);
    router.replace(`${pathname}${q}`, { scroll: false });
  };
  const onSort = (a: ExplorerAxis) => {
    const next: "asc" | "desc" = sortAxis?.key === a.key ? (dir === "desc" ? "asc" : "desc") : "desc";
    setParams({ sort: a.key === DEFAULTS.sort ? null : a.key, dir: next === "desc" ? null : "asc" });
  };

  if (loading) return <Loading />;
  if (!data || !axes.length || !xAxis || !yAxis || !sortAxis) {
    return (
      <div className="mono mt-10 text-sm text-[var(--color-faint)]">
        No {tour.toUpperCase()} player data available right now — the data may be refreshing, so check back shortly.
      </div>
    );
  }

  const { points, missing } = plottable(field, xAxis, yAxis, tour);
  const mean = points.length
    ? {
        x: points.reduce((s, d) => s + d.x, 0) / points.length,
        y: points.reduce((s, d) => s + d.y, 0) / points.length,
      }
    : null;
  const tableRows = sortByAxis(field, sortAxis, dir, tour);
  const presets = EXPLORER_PRESETS.filter(
    (p) => axes.some((a) => a.key === p.x) && axes.some((a) => a.key === p.y),
  );
  const axisOptions = axes.map((a) => ({ value: a.key, label: a.label }));

  return (
    <>
      {/* controls */}
      <Reveal>
        <div className="mt-8 flex flex-wrap items-center gap-3">
          {/* view toggle */}
          <div className="flex rounded-full border border-[var(--color-line)] p-0.5">
            {(["scatter", "table"] as const).map((v) => (
              <motion.button
                key={v}
                onClick={() => setParams({ view: v === "scatter" ? null : v })}
                whileTap={{ scale: 0.96 }}
                transition={SPRING}
                className="mono rounded-full px-3 py-1 text-[11px] uppercase tracking-wider transition-colors"
                style={{
                  background: view === v ? "var(--color-accent)" : "transparent",
                  color: view === v ? "var(--color-on-accent)" : "var(--color-muted)",
                }}
              >
                {v}
              </motion.button>
            ))}
          </div>

          <span className="eyebrow">Top</span>
          <div className="flex rounded-full border border-[var(--color-line)] p-0.5">
            {N_OPTIONS.map((n) => (
              <motion.button
                key={n}
                onClick={() => setCount(n)}
                whileTap={{ scale: 0.96 }}
                transition={SPRING}
                className="mono rounded-full px-3 py-1 text-[11px] transition-colors"
                style={{
                  background: count === n ? "var(--color-accent)" : "transparent",
                  color: count === n ? "var(--color-on-accent)" : "var(--color-muted)",
                }}
              >
                {n}
              </motion.button>
            ))}
          </div>

          {view === "scatter" && (
            <>
              <Dropdown
                compact
                label="X axis"
                value={xAxis.key}
                onChange={(v) => setParams({ x: v === DEFAULTS.x ? null : v })}
                options={axisOptions}
              />
              <Dropdown
                compact
                label="Y axis"
                value={yAxis.key}
                onChange={(v) => setParams({ y: v === DEFAULTS.y ? null : v })}
                options={axisOptions}
              />
            </>
          )}
        </div>
      </Reveal>

      {/* quick presets (scatter) */}
      {view === "scatter" && (
        <Reveal delay={0.03}>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            {presets.map((p) => {
              const active = xAxis.key === p.x && yAxis.key === p.y;
              return (
                <motion.button
                  key={p.label}
                  onClick={() => setParams({ x: p.x === DEFAULTS.x ? null : p.x, y: p.y === DEFAULTS.y ? null : p.y })}
                  whileTap={{ scale: 0.96 }}
                  transition={SPRING}
                  className="chip transition-colors"
                  style={{
                    background: active ? "var(--color-accent)" : "transparent",
                    color: active ? "var(--color-on-accent)" : "var(--color-muted)",
                    borderColor: active ? "var(--color-accent)" : "var(--color-line)",
                  }}
                >
                  {p.label}
                </motion.button>
              );
            })}
          </div>
        </Reveal>
      )}

      {view === "scatter" ? (
        <>
          <Reveal delay={0.05}>
            <div className="mt-5 panel p-3 sm:p-5">
              <ScatterChart
                key={`${tour}-${xAxis.key}-${yAxis.key}-${count}`}
                data={points.map(({ p, x, y }) => ({
                  id: p.name, x, y, label: lastName(p.name), color: "var(--color-accent)", p,
                }))}
                xLabel={`${xAxis.label.toLowerCase()} →`}
                yLabel={`${yAxis.label.toLowerCase()} →`}
                xTickFmt={xAxis.fmt}
                yTickFmt={yAxis.fmt}
                tooltip={(d) => ({
                  title: d.p.name,
                  lines: [
                    `${xAxis.label.toLowerCase()} ${xAxis.fmt(d.x)}`,
                    `${yAxis.label.toLowerCase()} ${yAxis.fmt(d.y)}`,
                    `elo rank #${d.p.eloRank}`,
                  ],
                })}
                onDotClick={(d) => router.push(playerHref(d.id, tour))}
                hover={hover}
                onHover={setHover}
                ariaLabel={`${xAxis.label} versus ${yAxis.label} scatter plot`}
                annotations={({ X, Y, bounds: b }) =>
                  mean && (
                    <>
                      <line x1={X(mean.x)} y1={b.top} x2={X(mean.x)} y2={b.top + b.ih} stroke="var(--color-line2)" strokeWidth={1} strokeDasharray="3 4" />
                      <line x1={b.left} y1={Y(mean.y)} x2={b.left + b.iw} y2={Y(mean.y)} stroke="var(--color-line2)" strokeWidth={1} strokeDasharray="3 4" />
                    </>
                  )
                }
              />
            </div>
          </Reveal>
          <p className="mono mt-4 text-[11px] text-[var(--color-faint)]">
            {points.length} of {field.length} plotted
            {missing > 0 && ` · ${missing} missing ${xAxis.label.toLowerCase()} or ${yAxis.label.toLowerCase()}`}
            {" · dashed cross = group average · hover a dot for the line · click through to the profile"}
          </p>
        </>
      ) : (
        <>
          <Reveal delay={0.05}>
            <div className="panel mt-5 overflow-x-auto">
              <table className="w-full border-collapse text-[13px]">
                <thead>
                  <tr className="mono text-[10px] uppercase tracking-wider text-[var(--color-faint)]">
                    <th className="px-3 py-3 text-right font-normal">#</th>
                    <th className="sticky left-0 bg-[var(--color-panel)] px-3 py-3 text-left font-normal">Player</th>
                    {axes.map((a) => {
                      const active = sortAxis.key === a.key;
                      return (
                        <th
                          key={a.key}
                          aria-sort={active ? (dir === "asc" ? "ascending" : "descending") : undefined}
                          className="whitespace-nowrap px-3 py-3 text-right font-normal"
                        >
                          <button
                            onClick={() => onSort(a)}
                            className="mono uppercase tracking-wider transition-colors hover:text-[var(--color-text)]"
                            style={{ color: active ? "var(--color-accent)" : undefined }}
                          >
                            {a.label}{active ? (dir === "asc" ? " ▲" : " ▼") : ""}
                          </button>
                        </th>
                      );
                    })}
                  </tr>
                </thead>
                <tbody>
                  {tableRows.map((p, i) => (
                    <motion.tr
                      key={p.name}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ duration: 0.35, delay: Math.min(i * 0.015, 0.3) }}
                      className="row-glow border-t border-[var(--color-line)]"
                    >
                      <td className="mono px-3 py-2.5 text-right text-[11px] text-[var(--color-faint)]">{i + 1}</td>
                      <td className="sticky left-0 whitespace-nowrap bg-[var(--color-panel)] px-3 py-2.5 text-[var(--color-text)]">
                        <Link href={playerHref(p.name, tour)} className="transition-colors hover:text-[var(--color-accent)] hover:underline">
                          {p.name}
                        </Link>
                      </td>
                      {axes.map((a) => {
                        const v = a.get(p, tour);
                        const active = sortAxis.key === a.key;
                        return (
                          <td
                            key={a.key}
                            className="mono px-3 py-2.5 text-right"
                            style={{ color: active ? "var(--color-text)" : "var(--color-muted)", fontWeight: active ? 600 : undefined }}
                          >
                            {v == null ? "—" : a.fmt(v)}
                          </td>
                        );
                      })}
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Reveal>
          <p className="mono mt-4 text-[11px] text-[var(--color-faint)]">
            top {field.length} by Elo · click a column header to rank by that stat · missing values sort last
          </p>
        </>
      )}
    </>
  );
}
