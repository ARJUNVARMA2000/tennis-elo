"use client";

import { motion } from "framer-motion";
import { SPRING_SOFT, EASE } from "@/lib/motion";

/** Generic SVG scatter, extracted from the Strength Map so /strength and /explorer
    share one plot. Callers own semantics: what x/y mean, dot colors, tooltip copy,
    and any extra chrome (crosshairs, quadrant labels) via the `annotations`
    render-prop, which receives the pixel scales. Hover stays controlled so pages
    can coordinate it with their own UI. */

export type ScatterDatum = {
  id: string;          // stable key (player name)
  x: number;
  y: number;
  label: string;       // short dot label (last name)
  color: string;
  ring?: boolean;      // accent ring (manually-added players)
};

export type ScatterScales = {
  X: (v: number) => number;
  Y: (v: number) => number;
  bounds: { left: number; top: number; iw: number; ih: number };
};

/** Nice round ticks across [min,max] (works for 0..1 fractions and Elo-sized ints). */
export function niceTicks(min: number, max: number, n = 4): number[] {
  const span = max - min || 1;
  const raw = span / n;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const norm = raw / mag;
  const step = (norm < 1.5 ? 1 : norm < 3 ? 2 : norm < 7 ? 5 : 10) * mag;
  const start = Math.ceil(min / step) * step;
  const out: number[] = [];
  for (let v = start; v <= max + 1e-9; v += step) out.push(Number(v.toFixed(10)));
  return out;
}

export default function ScatterChart<T extends ScatterDatum>({
  data, xLabel, yLabel, xTickFmt, yTickFmt, tooltip, onDotClick, hover, onHover,
  extraDomainPoints = [], annotations, ariaLabel,
}: {
  data: T[];
  xLabel: string;
  yLabel: string;
  xTickFmt: (v: number) => string;
  yTickFmt: (v: number) => string;
  tooltip: (d: T) => { title: string; lines: string[] };
  onDotClick?: (d: T) => void;
  hover: string | null;
  onHover: (id: string | null) => void;
  /** Points that must stay inside the domain without being drawn (e.g. tour average). */
  extraDomainPoints?: { x: number; y: number }[];
  annotations?: (s: ScatterScales) => React.ReactNode;
  ariaLabel: string;
}) {
  const W = 760, H = 540;
  const M = { top: 26, right: 30, bottom: 50, left: 62 };
  const iw = W - M.left - M.right;
  const ih = H - M.top - M.bottom;

  const xs = [...data.map((d) => d.x), ...extraDomainPoints.map((p) => p.x)];
  const ys = [...data.map((d) => d.y), ...extraDomainPoints.map((p) => p.y)];
  let xmin = Math.min(...xs), xmax = Math.max(...xs);
  let ymin = Math.min(...ys), ymax = Math.max(...ys);
  const xpad = (xmax - xmin || 0.02) * 0.09;
  const ypad = (ymax - ymin || 0.02) * 0.12;
  xmin -= xpad; xmax += xpad; ymin -= ypad; ymax += ypad;

  const X = (v: number) => M.left + ((v - xmin) / (xmax - xmin)) * iw;
  const Y = (v: number) => M.top + (1 - (v - ymin) / (ymax - ymin)) * ih; // invert: higher = up

  const xticks = niceTicks(xmin, xmax);
  const yticks = niceTicks(ymin, ymax);
  const hovered = hover ? data.find((d) => d.id === hover) : null;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" className="block overflow-visible" role="img" aria-label={ariaLabel}>
      {/* plot frame */}
      <rect x={M.left} y={M.top} width={iw} height={ih} fill="none" stroke="var(--color-line)" strokeWidth={1} rx={8} />

      {/* gridlines + tick labels */}
      {xticks.map((t) => (
        <g key={`x${t}`}>
          <line x1={X(t)} y1={M.top} x2={X(t)} y2={M.top + ih} stroke="var(--color-line)" strokeWidth={1} strokeOpacity={0.5} />
          <text x={X(t)} y={M.top + ih + 18} textAnchor="middle" fontSize={10} fill="var(--color-faint)" className="mono">{xTickFmt(t)}</text>
        </g>
      ))}
      {yticks.map((t) => (
        <g key={`y${t}`}>
          <line x1={M.left} y1={Y(t)} x2={M.left + iw} y2={Y(t)} stroke="var(--color-line)" strokeWidth={1} strokeOpacity={0.5} />
          <text x={M.left - 10} y={Y(t) + 3} textAnchor="end" fontSize={10} fill="var(--color-faint)" className="mono">{yTickFmt(t)}</text>
        </g>
      ))}

      {/* axis titles */}
      <text x={M.left + iw / 2} y={H - 8} textAnchor="middle" fontSize={11} fill="var(--color-muted)" className="mono">
        {xLabel}
      </text>
      <text x={16} y={M.top + ih / 2} textAnchor="middle" fontSize={11} fill="var(--color-muted)" className="mono" transform={`rotate(-90 16 ${M.top + ih / 2})`}>
        {yLabel}
      </text>

      {/* caller chrome (crosshairs, quadrant labels…) — painted under the dots */}
      {annotations?.({ X, Y, bounds: { left: M.left, top: M.top, iw, ih } })}

      {/* dots + labels (hovered drawn last) */}
      {data.map((d, i) => {
        if (hover === d.id) return null;
        return <Dot key={d.id} d={d} X={X} Y={Y} onHover={onHover} onClick={onDotClick} delay={i * 0.015} />;
      })}
      {hovered && <Dot d={hovered} X={X} Y={Y} onHover={onHover} onClick={onDotClick} delay={0} />}

      {/* tooltip */}
      {hovered && <Tooltip {...tooltip(hovered)} x={X(hovered.x)} y={Y(hovered.y)} M={M} iw={iw} />}
    </svg>
  );
}

function Dot<T extends ScatterDatum>({
  d, X, Y, onHover, onClick, delay,
}: {
  d: T; X: (v: number) => number; Y: (v: number) => number;
  onHover: (id: string | null) => void; onClick?: (d: T) => void; delay: number;
}) {
  const x = X(d.x), y = Y(d.y);
  return (
    <g
      onMouseEnter={() => onHover(d.id)}
      onMouseLeave={() => onHover(null)}
      onClick={onClick ? () => onClick(d) : undefined}
      onKeyDown={onClick ? (e) => { if (e.key === "Enter") onClick(d); } : undefined}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      aria-label={onClick ? d.id : undefined}
      style={{ cursor: "pointer", outline: "none" }}
    >
      {/* generous invisible hit area */}
      <circle cx={x} cy={y} r={11} fill="transparent" />
      {d.ring && (
        <motion.circle
          cx={x}
          cy={y}
          r={6.5}
          fill="none"
          stroke="var(--color-accent)"
          strokeWidth={1.4}
          strokeOpacity={0.85}
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ ...SPRING_SOFT, delay }}
          style={{ transformBox: "fill-box", transformOrigin: "center" }}
        />
      )}
      <motion.circle
        cx={x}
        cy={y}
        r={d.ring ? 4.6 : 4}
        fill={d.color}
        initial={{ scale: 0, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ ...SPRING_SOFT, delay }}
        style={{ transformBox: "fill-box", transformOrigin: "center" }}
      />
      <motion.text
        x={x + 7}
        y={y + 3}
        fontSize={9}
        fill="var(--color-muted)"
        className="mono"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3, delay: delay + 0.3, ease: EASE }}
      >
        {d.label}
      </motion.text>
    </g>
  );
}

function Tooltip({
  title, lines, x, y, M, iw,
}: {
  title: string; lines: string[]; x: number; y: number;
  M: { top: number; right: number; bottom: number; left: number }; iw: number;
}) {
  const bw = 150, bh = 24 + 13 * lines.length;
  // flip horizontally / vertically to stay inside the plot
  const left = x + bw + 14 > M.left + iw ? x - bw - 12 : x + 12;
  const top = y - bh - 10 < M.top ? y + 12 : y - bh - 10;
  return (
    <motion.g
      pointerEvents="none"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.14 }}
      style={{ filter: "drop-shadow(0 8px 32px rgba(0, 0, 0, 0.55))" }}
    >
      <rect x={left} y={top} width={bw} height={bh} rx={8} fill="rgba(22, 23, 26, 0.92)" stroke="var(--color-line)" />
      <text x={left + 10} y={top + 17} fontSize={11} fill="var(--color-text)" className="mono">{title}</text>
      {lines.map((l, i) => (
        <text key={i} x={left + 10} y={top + 32 + 12 * i} fontSize={10} fill={i === lines.length - 1 ? "var(--color-faint)" : "var(--color-muted)"} className="mono">
          {l}
        </text>
      ))}
    </motion.g>
  );
}
