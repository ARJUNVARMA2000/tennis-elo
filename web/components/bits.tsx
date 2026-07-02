"use client";

import { motion } from "framer-motion";
import { surfaceColor, heat } from "@/lib/ui";
import { EASE, SPRING_SOFT, stagger, fadeUp, hoverLift, useCountUp } from "@/lib/motion";

export function Reveal({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.45, delay, ease: EASE }}
    >
      {children}
    </motion.div>
  );
}

export function PageHead({ eyebrow, title, sub }: { eyebrow: string; title: string; sub?: string }) {
  return (
    <motion.div variants={stagger(0.08)} initial="hidden" animate="show" className="pt-10 sm:pt-14">
      <motion.div variants={fadeUp} className="eyebrow">
        {eyebrow}
      </motion.div>
      <motion.h1 variants={fadeUp} className="display mt-3 text-3xl sm:text-4xl">
        {title}
      </motion.h1>
      {sub && (
        <motion.p
          variants={fadeUp}
          className="mt-3 max-w-2xl text-[15px] leading-relaxed text-[var(--color-muted)]"
        >
          {sub}
        </motion.p>
      )}
    </motion.div>
  );
}

/** Bare shimmer block — building block for Loading and bespoke skeletons. */
export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton ${className}`} />;
}

/** Skeleton placeholder shown while a page's JSON loads. */
export function Loading({ rows = 6 }: { rows?: number }) {
  return (
    <div className="panel mt-8 space-y-3 p-4" aria-busy="true" aria-label="loading">
      <Skeleton className="h-4 w-1/3" />
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} style={{ opacity: 1 - i * 0.13 }}>
          <Skeleton className="h-8" />
        </div>
      ))}
    </div>
  );
}

export function SurfacePill({ s, active, onClick }: { s: string; active?: boolean; onClick?: () => void }) {
  return (
    <motion.button
      onClick={onClick}
      whileTap={{ scale: 0.94 }}
      className="chip transition-colors"
      style={{
        color: active ? "var(--color-on-accent)" : surfaceColor(s),
        background: active ? surfaceColor(s) : "transparent",
        borderColor: surfaceColor(s),
      }}
    >
      {s}
    </motion.button>
  );
}

/** Two-sided win-probability bar (A accent, B comparison-cyan). Springs on change. */
export function ProbBar({ p, w = 120 }: { p: number; w?: number }) {
  return (
    <div className="bartrack flex h-1.5" style={{ width: w }}>
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${p * 100}%` }}
        transition={SPRING_SOFT}
        style={{ background: "var(--color-accent)" }}
      />
      <div className="flex-1" style={{ background: "var(--color-cmp)" }} />
    </div>
  );
}

export function HeatCell({ p }: { p: number }) {
  const c = heat(p);
  return (
    <motion.span
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.35 }}
      className="mono inline-block rounded px-2 py-0.5 text-[11px]"
      style={{ background: `${c}22`, color: c }}
    >
      {(p * 100).toFixed(0)}%
    </motion.span>
  );
}

/** Count-up number for hero stats. Re-animates on tour/surface switches. */
export function AnimatedNumber({
  value,
  decimals = 0,
  suffix = "",
  className = "",
}: {
  value: number;
  decimals?: number;
  suffix?: string;
  className?: string;
}) {
  const v = useCountUp(value);
  return (
    <span className={`mono ${className}`}>
      {v.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}
      {suffix}
    </span>
  );
}

/** Small labelled stat panel (shared by rankings / track / method heroes). */
export function StatCard({
  label,
  value,
  sub,
  decimals = 0,
  suffix = "",
}: {
  label: string;
  value: number | string;
  sub?: string;
  decimals?: number;
  suffix?: string;
}) {
  return (
    <motion.div {...hoverLift} className="panel px-4 py-3">
      <div className="eyebrow !text-[10px]">{label}</div>
      {typeof value === "number" ? (
        <AnimatedNumber
          value={value}
          decimals={decimals}
          suffix={suffix}
          className="mt-1 block text-xl font-semibold text-[var(--color-text)]"
        />
      ) : (
        <div className="mono mt-1 text-xl font-semibold text-[var(--color-text)]">{value}</div>
      )}
      {sub && <div className="mt-0.5 text-[11px] text-[var(--color-faint)]">{sub}</div>}
    </motion.div>
  );
}

export function GitHubIcon({ size = 18 }: { size?: number }) {
  return (
    <svg viewBox="0 0 16 16" width={size} height={size} fill="currentColor" aria-hidden="true">
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
    </svg>
  );
}

/** Multi-axis radar/spider chart. Each series `values` are in 0..1, aligned to `axes`.
    The polygon springs between shapes when the selection changes. */
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
  const shape = (values: number[]) => values.map((v, i) => pt(i, clamp(v)).join(",")).join(" ");
  const center = axes.map((_, i) => pt(i, 0.02).join(",")).join(" ");

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
      {/* series polygons (morph between shapes) + vertex dots */}
      {series.map((s) => (
        <g key={s.name}>
          <motion.polygon
            initial={{ points: center, opacity: 0 }}
            animate={{ points: shape(s.values), opacity: 1 }}
            transition={SPRING_SOFT}
            fill={s.color}
            fillOpacity={0.14}
            stroke={s.color}
            strokeWidth={1.8}
            strokeLinejoin="round"
          />
          {s.values.map((v, i) => {
            const [px, py] = pt(i, clamp(v));
            return (
              <motion.circle
                key={i}
                initial={{ scale: 0, opacity: 0 }}
                animate={{ cx: px, cy: py, scale: 1, opacity: 1 }}
                transition={{ ...SPRING_SOFT, delay: i * 0.03 }}
                style={{ transformBox: "fill-box", transformOrigin: "center" }}
                r={2.4}
                fill={s.color}
              />
            );
          })}
        </g>
      ))}
    </svg>
  );
}

/** Tiny SVG sparkline — draws itself in on first view. */
export function Spark({ points, w = 220, h = 46, color = "var(--color-accent)" }: { points: number[]; w?: number; h?: number; color?: string }) {
  if (!points.length) return null;
  const min = Math.min(...points), max = Math.max(...points);
  const span = max - min || 1;
  const xy = points.map((y, i) => [
    (i / (points.length - 1 || 1)) * w,
    h - ((y - min) / span) * (h - 6) - 3,
  ]);
  const d = xy.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x},${y}`).join(" ");
  const [ex, ey] = xy[xy.length - 1];
  return (
    <svg width={w} height={h} className="overflow-visible">
      <motion.path
        d={d}
        fill="none"
        stroke={color}
        strokeWidth={1.6}
        strokeLinejoin="round"
        initial={{ pathLength: 0 }}
        whileInView={{ pathLength: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 0.9, ease: EASE }}
      />
      <motion.circle
        cx={ex}
        cy={ey}
        r={2.6}
        fill={color}
        initial={{ scale: 0, opacity: 0 }}
        whileInView={{ scale: 1, opacity: 1 }}
        viewport={{ once: true }}
        transition={{ ...SPRING_SOFT, delay: 0.75 }}
        style={{ transformBox: "fill-box", transformOrigin: "center" }}
      />
    </svg>
  );
}
