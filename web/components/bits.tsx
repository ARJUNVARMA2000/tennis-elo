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
