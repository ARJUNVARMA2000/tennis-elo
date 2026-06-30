"use client";

import { useEffect, useMemo, useState } from "react";
import { useData, useTour } from "@/lib/tour";
import { pct } from "@/lib/ui";
import { PageHead, Loading, Reveal } from "@/components/bits";

type Player = {
  name: string; eloRank: number; elo: number;
  servePct: number; returnPct: number; country: string | null;
};

const DEFAULT_N = 20;
const N_OPTIONS = [10, 20, 30];
const lastName = (n: string) => n.split(" ").slice(-1)[0];

// Quadrant palette (relative to the selected-set average).
const QUADS = [
  { key: "complete", label: "Complete", color: "var(--color-lime)", hint: "above avg serve & return" },
  { key: "server", label: "Serve-first", color: "var(--color-cyan)", hint: "strong serve, weaker return" },
  { key: "returner", label: "Return-first", color: "var(--color-gold)", hint: "strong return, weaker serve" },
  { key: "below", label: "Below avg", color: "var(--color-coral)", hint: "below avg serve & return" },
] as const;

function quadColor(p: Player, mean: { s: number; r: number }) {
  const sHi = p.servePct >= mean.s;
  const rHi = p.returnPct >= mean.r;
  if (sHi && rHi) return QUADS[0].color;
  if (sHi && !rHi) return QUADS[1].color;
  if (!sHi && rHi) return QUADS[2].color;
  return QUADS[3].color;
}

/** Nice round ticks across [min,max] for fractional (0..1) axes. */
function ticks(min: number, max: number, n = 4): number[] {
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

export default function Strength() {
  const { tour } = useTour();
  const { data, loading } = useData<Player[]>("players.json");
  const [count, setCount] = useState(DEFAULT_N);
  const [picks, setPicks] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [adding, setAdding] = useState(false);
  const [hover, setHover] = useState<string | null>(null);

  // ATP ↔ WTA swaps the roster — clear manual picks and the search box.
  useEffect(() => {
    setPicks([]);
    setQuery("");
    setAdding(false);
    setHover(null);
  }, [tour]);

  const sorted = useMemo(
    () => (data ? [...data].sort((a, b) => b.elo - a.elo) : []),
    [data],
  );
  const byName = useMemo(() => {
    const m = new Map<string, Player>();
    sorted.forEach((p) => m.set(p.name, p));
    return m;
  }, [sorted]);

  const topNames = useMemo(() => sorted.slice(0, count).map((p) => p.name), [sorted, count]);
  const shown = useMemo(() => {
    const seen = new Set<string>();
    const out: Player[] = [];
    for (const n of [...topNames, ...picks]) {
      const p = byName.get(n);
      if (p && !seen.has(n)) { seen.add(n); out.push(p); }
    }
    return out;
  }, [topNames, picks, byName]);
  const shownSet = useMemo(() => new Set(shown.map((p) => p.name)), [shown]);

  // Quadrant cross = average of the plotted players (re-centers as you add/remove).
  const sel = useMemo(() => {
    if (!shown.length) return null;
    const s = shown.reduce((a, p) => a + p.servePct, 0) / shown.length;
    const r = shown.reduce((a, p) => a + p.returnPct, 0) / shown.length;
    return { s, r };
  }, [shown]);

  // Tour average = the whole ranked field — drawn as a faint reference crosshair.
  const tourAvg = useMemo(() => {
    if (!sorted.length) return null;
    const s = sorted.reduce((a, p) => a + p.servePct, 0) / sorted.length;
    const r = sorted.reduce((a, p) => a + p.returnPct, 0) / sorted.length;
    return { s, r };
  }, [sorted]);

  const suggestions = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return sorted
      .filter((p) => !shownSet.has(p.name) && p.name.toLowerCase().includes(q))
      .slice(0, 8);
  }, [query, sorted, shownSet]);

  const addPick = (name: string) => {
    setPicks((prev) => (prev.includes(name) ? prev : [...prev, name]));
    setQuery("");
  };
  const removePick = (name: string) => setPicks((prev) => prev.filter((n) => n !== name));

  return (
    <div className="pb-16">
      <PageHead
        eyebrow={`${tour.toUpperCase()} · serve vs return`}
        title="Strength Map"
        sub="Every player placed by serve points won (horizontal) and return points won (vertical), from the opponent-adjusted point model. The solid cross is the average of the plotted group; the dashed crosshair marks the tour average. Stronger all-rounders sit toward the top-right."
      />

      {loading && <Loading />}

      {data && sel && tourAvg && (
        <>
          {/* controls */}
          <Reveal>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <span className="eyebrow">Show top</span>
              <div className="flex rounded-full border border-[var(--color-line)] p-0.5">
                {N_OPTIONS.map((n) => (
                  <button
                    key={n}
                    onClick={() => setCount(n)}
                    className="mono rounded-full px-3 py-1 text-[11px] transition-colors"
                    style={{
                      background: count === n ? "var(--color-lime)" : "transparent",
                      color: count === n ? "#07090d" : "var(--color-muted)",
                    }}
                  >
                    {n}
                  </button>
                ))}
              </div>

              <div className="relative">
                <button
                  onClick={() => setAdding((v) => !v)}
                  className="mono flex items-center gap-1.5 rounded-full border border-[var(--color-line)] px-3 py-1 text-[11px] text-[var(--color-muted)] transition-colors hover:border-[var(--color-lime)] hover:text-[var(--color-text)]"
                >
                  <span className="text-[var(--color-lime)]">＋</span> Add player
                </button>
                {adding && (
                  <div className="absolute left-0 top-9 z-20 w-64 rounded-xl border border-[var(--color-line)] bg-[var(--color-ink2)] p-2 shadow-xl">
                    <input
                      autoFocus
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="Type a name…"
                      className="mono w-full rounded-lg border border-[var(--color-line)] bg-[var(--color-ink)] px-3 py-2 text-sm text-[var(--color-text)] outline-none focus:border-[var(--color-lime)]"
                    />
                    {suggestions.length > 0 && (
                      <div className="mt-1.5 max-h-60 overflow-y-auto">
                        {suggestions.map((p) => (
                          <button
                            key={p.name}
                            onClick={() => addPick(p.name)}
                            className="row-glow flex w-full items-center justify-between rounded-lg px-2.5 py-1.5 text-left text-sm text-[var(--color-text)]"
                          >
                            <span>{p.name}</span>
                            <span className="mono text-[11px] text-[var(--color-faint)]">#{p.eloRank}</span>
                          </button>
                        ))}
                      </div>
                    )}
                    {query.trim() && suggestions.length === 0 && (
                      <div className="mono px-2.5 py-2 text-[11px] text-[var(--color-faint)]">no match (or already shown)</div>
                    )}
                  </div>
                )}
              </div>

              {/* manually added players */}
              {picks.map((n) => (
                <button
                  key={n}
                  onClick={() => removePick(n)}
                  className="chip flex items-center gap-1.5 text-[var(--color-text)] transition-colors hover:border-[var(--color-coral)] hover:text-[var(--color-coral)]"
                  style={{ borderColor: "var(--color-lime)" }}
                  title="Remove"
                >
                  {lastName(n)} <span className="text-[var(--color-faint)]">✕</span>
                </button>
              ))}
            </div>
          </Reveal>

          {/* chart */}
          <Reveal delay={0.05}>
            <div className="mt-5 panel p-3 sm:p-5">
              <ScatterChart
                players={shown}
                picks={new Set(picks)}
                sel={sel}
                tourAvg={tourAvg}
                hover={hover}
                setHover={setHover}
              />
              {/* legend */}
              <div className="mono mt-2 flex flex-wrap items-center gap-x-5 gap-y-2 px-2 text-[11px] text-[var(--color-muted)]">
                {QUADS.map((q) => (
                  <span key={q.key} className="flex items-center gap-1.5" title={q.hint}>
                    <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: q.color }} />
                    {q.label}
                  </span>
                ))}
                <span className="ml-auto flex items-center gap-1.5 text-[var(--color-faint)]">
                  <span className="inline-block h-0 w-5 border-t border-dashed border-[var(--color-faint)]" /> tour average
                </span>
              </div>
            </div>
          </Reveal>

          <p className="mono mt-4 text-[11px] text-[var(--color-faint)]">
            {shown.length} players plotted · serve & return are model point-win rates · hover a dot for the full line
          </p>
        </>
      )}
    </div>
  );
}

function ScatterChart({
  players, picks, sel, tourAvg, hover, setHover,
}: {
  players: Player[];
  picks: Set<string>;
  sel: { s: number; r: number };
  tourAvg: { s: number; r: number };
  hover: string | null;
  setHover: (n: string | null) => void;
}) {
  const W = 760, H = 540;
  const M = { top: 26, right: 30, bottom: 50, left: 62 };
  const iw = W - M.left - M.right;
  const ih = H - M.top - M.bottom;

  // Domain spans the plotted players AND the tour-average point so the reference stays in frame.
  const xs = [...players.map((p) => p.servePct), tourAvg.s];
  const ys = [...players.map((p) => p.returnPct), tourAvg.r];
  let xmin = Math.min(...xs), xmax = Math.max(...xs);
  let ymin = Math.min(...ys), ymax = Math.max(...ys);
  const xpad = (xmax - xmin || 0.02) * 0.09;
  const ypad = (ymax - ymin || 0.02) * 0.12;
  xmin -= xpad; xmax += xpad; ymin -= ypad; ymax += ypad;

  const X = (v: number) => M.left + ((v - xmin) / (xmax - xmin)) * iw;
  const Y = (v: number) => M.top + (1 - (v - ymin) / (ymax - ymin)) * ih; // invert: higher return = higher up

  const xticks = ticks(xmin, xmax);
  const yticks = ticks(ymin, ymax);

  const cx = X(sel.s), cy = Y(sel.r);
  const tx = X(tourAvg.s), ty = Y(tourAvg.r);

  const hovered = hover ? players.find((p) => p.name === hover) : null;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" className="block overflow-visible" role="img" aria-label="Serve versus return scatter plot">
      {/* plot frame */}
      <rect x={M.left} y={M.top} width={iw} height={ih} fill="none" stroke="var(--color-line)" strokeWidth={1} rx={8} />

      {/* gridlines + tick labels */}
      {xticks.map((t) => (
        <g key={`x${t}`}>
          <line x1={X(t)} y1={M.top} x2={X(t)} y2={M.top + ih} stroke="var(--color-line)" strokeWidth={1} strokeOpacity={0.5} />
          <text x={X(t)} y={M.top + ih + 18} textAnchor="middle" fontSize={10} fill="var(--color-faint)" className="mono">{pct(t, 0)}</text>
        </g>
      ))}
      {yticks.map((t) => (
        <g key={`y${t}`}>
          <line x1={M.left} y1={Y(t)} x2={M.left + iw} y2={Y(t)} stroke="var(--color-line)" strokeWidth={1} strokeOpacity={0.5} />
          <text x={M.left - 10} y={Y(t) + 3} textAnchor="end" fontSize={10} fill="var(--color-faint)" className="mono">{pct(t, 0)}</text>
        </g>
      ))}

      {/* axis titles */}
      <text x={M.left + iw / 2} y={H - 8} textAnchor="middle" fontSize={11} fill="var(--color-muted)" className="mono">
        serve points won →
      </text>
      <text x={16} y={M.top + ih / 2} textAnchor="middle" fontSize={11} fill="var(--color-muted)" className="mono" transform={`rotate(-90 16 ${M.top + ih / 2})`}>
        return points won →
      </text>

      {/* tour-average reference crosshair (dashed, faint) */}
      <line x1={tx} y1={M.top} x2={tx} y2={M.top + ih} stroke="var(--color-faint)" strokeWidth={1} strokeDasharray="3 4" />
      <line x1={M.left} y1={ty} x2={M.left + iw} y2={ty} stroke="var(--color-faint)" strokeWidth={1} strokeDasharray="3 4" />

      {/* selected-group average cross (solid, brighter) */}
      <line x1={cx} y1={M.top} x2={cx} y2={M.top + ih} stroke="rgba(255,255,255,0.22)" strokeWidth={1} />
      <line x1={M.left} y1={cy} x2={M.left + iw} y2={cy} stroke="rgba(255,255,255,0.22)" strokeWidth={1} />

      {/* quadrant corner labels (relative to the selected cross) */}
      <text x={M.left + iw - 8} y={M.top + 16} textAnchor="end" fontSize={10} fill="var(--color-lime)" fillOpacity={0.55} className="mono">complete</text>
      <text x={M.left + 8} y={M.top + 16} textAnchor="start" fontSize={10} fill="var(--color-gold)" fillOpacity={0.55} className="mono">return-first</text>
      <text x={M.left + iw - 8} y={M.top + ih - 8} textAnchor="end" fontSize={10} fill="var(--color-cyan)" fillOpacity={0.55} className="mono">serve-first</text>
      <text x={M.left + 8} y={M.top + ih - 8} textAnchor="start" fontSize={10} fill="var(--color-coral)" fillOpacity={0.5} className="mono">below avg</text>

      {/* dots + labels (hovered drawn last) */}
      {players.map((p) => {
        if (hover === p.name) return null;
        return <Dot key={p.name} p={p} X={X} Y={Y} color={quadColor(p, sel)} isPick={picks.has(p.name)} onHover={setHover} />;
      })}
      {hovered && <Dot p={hovered} X={X} Y={Y} color={quadColor(hovered, sel)} isPick={picks.has(hovered.name)} onHover={setHover} />}

      {/* tooltip */}
      {hovered && <Tooltip p={hovered} x={X(hovered.servePct)} y={Y(hovered.returnPct)} W={W} M={M} iw={iw} />}
    </svg>
  );
}

function Dot({
  p, X, Y, color, isPick, onHover,
}: {
  p: Player; X: (v: number) => number; Y: (v: number) => number; color: string; isPick: boolean; onHover: (n: string | null) => void;
}) {
  const x = X(p.servePct), y = Y(p.returnPct);
  return (
    <g
      onMouseEnter={() => onHover(p.name)}
      onMouseLeave={() => onHover(null)}
      style={{ cursor: "pointer" }}
    >
      {/* generous invisible hit area */}
      <circle cx={x} cy={y} r={11} fill="transparent" />
      {isPick && <circle cx={x} cy={y} r={6.5} fill="none" stroke="#fff" strokeWidth={1.4} strokeOpacity={0.85} />}
      <circle cx={x} cy={y} r={isPick ? 4.6 : 4} fill={color} />
      <text x={x + 7} y={y + 3} fontSize={9} fill="var(--color-muted)" className="mono">{lastName(p.name)}</text>
    </g>
  );
}

function Tooltip({
  p, x, y, W, M, iw,
}: {
  p: Player; x: number; y: number; W: number; M: { top: number; right: number; bottom: number; left: number }; iw: number;
}) {
  const bw = 150, bh = 50;
  // flip horizontally / vertically to stay inside the plot
  const left = x + bw + 14 > M.left + iw ? x - bw - 12 : x + 12;
  const top = y - bh - 10 < M.top ? y + 12 : y - bh - 10;
  return (
    <g pointerEvents="none">
      <rect x={left} y={top} width={bw} height={bh} rx={8} fill="var(--color-ink3)" stroke="var(--color-line)" />
      <text x={left + 10} y={top + 17} fontSize={11} fill="var(--color-text)" className="mono">{p.name}</text>
      <text x={left + 10} y={top + 32} fontSize={10} fill="var(--color-muted)" className="mono">
        serve {pct(p.servePct, 1)} · ret {pct(p.returnPct, 1)}
      </text>
      <text x={left + 10} y={top + 44} fontSize={10} fill="var(--color-faint)" className="mono">elo rank #{p.eloRank}</text>
    </g>
  );
}
