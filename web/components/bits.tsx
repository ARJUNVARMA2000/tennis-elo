"use client";

import { motion } from "framer-motion";
import { surfaceColor, heat } from "@/lib/ui";

export function Reveal({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.5, delay, ease: [0.16, 1, 0.3, 1] }}
    >
      {children}
    </motion.div>
  );
}

export function PageHead({ eyebrow, title, sub }: { eyebrow: string; title: string; sub?: string }) {
  return (
    <Reveal>
      <div className="pt-10 sm:pt-14">
        <div className="eyebrow">{eyebrow}</div>
        <h1 className="display mt-3 text-4xl sm:text-5xl">{title}</h1>
        {sub && <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-[var(--color-muted)]">{sub}</p>}
      </div>
    </Reveal>
  );
}

export function Loading() {
  return <div className="mono py-20 text-center text-sm text-[var(--color-faint)]">loading…</div>;
}

export function SurfacePill({ s, active, onClick }: { s: string; active?: boolean; onClick?: () => void }) {
  return (
    <button
      onClick={onClick}
      className="chip transition-colors"
      style={{
        color: active ? "#07090d" : surfaceColor(s),
        background: active ? surfaceColor(s) : "transparent",
        borderColor: surfaceColor(s),
      }}
    >
      {s}
    </button>
  );
}

/** Two-sided win-probability bar (A lime, B cyan). */
export function ProbBar({ p, w = 120 }: { p: number; w?: number }) {
  return (
    <div className="bartrack flex h-1.5" style={{ width: w }}>
      <div style={{ width: `${p * 100}%`, background: "var(--color-lime)" }} />
      <div style={{ width: `${(1 - p) * 100}%`, background: "var(--color-cyan)" }} />
    </div>
  );
}

export function HeatCell({ p }: { p: number }) {
  const c = heat(p);
  return (
    <span
      className="mono inline-block rounded px-2 py-0.5 text-[11px]"
      style={{ background: `${c}22`, color: c }}
    >
      {(p * 100).toFixed(0)}%
    </span>
  );
}

/** Multi-axis radar/spider chart. Each series `values` are in 0..1, aligned to `axes`. */
export function Radar({
  axes,
  series,
  maxW = 460,
}: {
  axes: { label: string }[];
  series: { name: string; color: string; values: number[] }[];
  maxW?: number;
}) {
  const N = axes.length;
  if (!N) return null;
  const cx = 220, cy = 190, R = 122, labelR = R + 16;
  const ang = (i: number) => -Math.PI / 2 + (i * 2 * Math.PI) / N;
  const pt = (i: number, r: number): [number, number] => [cx + Math.cos(ang(i)) * R * r, cy + Math.sin(ang(i)) * R * r];
  const clamp = (v: number) => Math.max(0, Math.min(1, v));
  const ring = (r: number) => axes.map((_, i) => pt(i, r).join(",")).join(" ");

  return (
    <svg viewBox="0 0 440 380" width="100%" style={{ maxWidth: maxW }} className="mx-auto block overflow-visible">
      {/* grid rings */}
      {[0.25, 0.5, 0.75, 1].map((r) => (
        <polygon key={r} points={ring(r)} fill="none" stroke="var(--color-line)" strokeWidth={1} />
      ))}
      {/* spokes + rim labels */}
      {axes.map((a, i) => {
        const [ex, ey] = pt(i, 1);
        const lx = cx + Math.cos(ang(i)) * labelR;
        const ly = cy + Math.sin(ang(i)) * labelR;
        const cos = Math.cos(ang(i));
        const anchor = Math.abs(cos) < 0.25 ? "middle" : cos > 0 ? "start" : "end";
        return (
          <g key={a.label}>
            <line x1={cx} y1={cy} x2={ex} y2={ey} stroke="var(--color-line)" strokeWidth={1} />
            <text x={lx} y={ly} textAnchor={anchor} dominantBaseline="middle" fontSize={9.5} fill="var(--color-muted)" className="mono">
              {a.label}
            </text>
          </g>
        );
      })}
      {/* series polygons + vertex dots */}
      {series.map((s) => (
        <g key={s.name}>
          <polygon
            points={s.values.map((v, i) => pt(i, clamp(v)).join(",")).join(" ")}
            fill={s.color}
            fillOpacity={0.14}
            stroke={s.color}
            strokeWidth={1.8}
            strokeLinejoin="round"
          />
          {s.values.map((v, i) => {
            const [px, py] = pt(i, clamp(v));
            return <circle key={i} cx={px} cy={py} r={2.4} fill={s.color} />;
          })}
        </g>
      ))}
    </svg>
  );
}

/** Tiny SVG sparkline from [x,y] series (y auto-scaled). */
export function Spark({ points, w = 220, h = 46, color = "var(--color-lime)" }: { points: number[]; w?: number; h?: number; color?: string }) {
  if (!points.length) return null;
  const min = Math.min(...points), max = Math.max(...points);
  const span = max - min || 1;
  const d = points
    .map((y, i) => `${(i / (points.length - 1)) * w},${h - ((y - min) / span) * (h - 6) - 3}`)
    .join(" ");
  return (
    <svg width={w} height={h} className="overflow-visible">
      <polyline points={d} fill="none" stroke={color} strokeWidth={1.6} strokeLinejoin="round" />
    </svg>
  );
}
