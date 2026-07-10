"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { useData, useTour } from "@/lib/tour";
import { pct } from "@/lib/ui";
import { playerHref } from "@/lib/url";
import { PageHead, Loading, Reveal } from "@/components/bits";
import ScatterChart from "@/components/ScatterChart";
import { SPRING } from "@/lib/motion";

type Player = {
  name: string; eloRank: number; elo: number;
  servePct: number; returnPct: number; country: string | null;
};

const DEFAULT_N = 20;
const N_OPTIONS = [10, 20, 30];
const lastName = (n: string) => n.split(" ").slice(-1)[0];

// Quadrant palette (relative to the selected-set average).
const QUADS = [
  { key: "complete", label: "Complete", color: "var(--color-win)", hint: "above avg serve & return" },
  { key: "server", label: "Serve-first", color: "var(--color-hard)", hint: "strong serve, weaker return" },
  { key: "returner", label: "Return-first", color: "var(--color-champ)", hint: "strong return, weaker serve" },
  { key: "below", label: "Below avg", color: "var(--color-loss)", hint: "below avg serve & return" },
] as const;

function quadColor(p: Player, mean: { s: number; r: number }) {
  const sHi = p.servePct >= mean.s;
  const rHi = p.returnPct >= mean.r;
  if (sHi && rHi) return QUADS[0].color;
  if (sHi && !rHi) return QUADS[1].color;
  if (!sHi && rHi) return QUADS[2].color;
  return QUADS[3].color;
}

export default function Strength() {
  const { tour } = useTour();
  const router = useRouter();
  const { data, loading } = useData<Player[]>("players.json");
  const [count, setCount] = useState(DEFAULT_N);
  const [picks, setPicks] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [adding, setAdding] = useState(false);
  const [hover, setHover] = useState<string | null>(null);
  const [activeSug, setActiveSug] = useState(-1);
  const addRef = useRef<HTMLDivElement>(null);
  const addBtnRef = useRef<HTMLButtonElement>(null);

  // ATP ↔ WTA swaps the roster — clear manual picks and the search box.
  useEffect(() => {
    setPicks([]);
    setQuery("");
    setAdding(false);
    setHover(null);
  }, [tour]);

  // outside click closes the add-player popover
  useEffect(() => {
    if (!adding) return;
    const onDown = (e: PointerEvent) => {
      if (addRef.current && !addRef.current.contains(e.target as Node)) setAdding(false);
    };
    document.addEventListener("pointerdown", onDown);
    return () => document.removeEventListener("pointerdown", onDown);
  }, [adding]);

  // keep the keyboard-highlighted suggestion in view
  useEffect(() => {
    if (activeSug >= 0) document.getElementById(`strength-sug-${activeSug}`)?.scrollIntoView({ block: "nearest" });
  }, [activeSug]);

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

  // keyboard support for the add-player popover (Escape / ArrowUp / ArrowDown / Enter)
  const onAddKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      e.preventDefault();
      setAdding(false);
      addBtnRef.current?.focus();
      return;
    }
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (!suggestions.length) return;
      setActiveSug((i) =>
        e.key === "ArrowDown" ? Math.min(i + 1, suggestions.length - 1) : Math.max(i - 1, 0),
      );
      return;
    }
    if (e.key === "Enter") {
      e.preventDefault();
      const pick = suggestions[activeSug] ?? suggestions[0];
      if (pick) addPick(pick.name);
    }
  };

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

              <div ref={addRef} className="relative">
                <motion.button
                  ref={addBtnRef}
                  onClick={() => {
                    setAdding((v) => !v);
                    setActiveSug(-1);
                  }}
                  whileTap={{ scale: 0.96 }}
                  transition={SPRING}
                  aria-haspopup="listbox"
                  aria-expanded={adding}
                  aria-controls={adding ? "strength-add-list" : undefined}
                  className="mono flex items-center gap-1.5 rounded-full border border-[var(--color-line)] px-3 py-1 text-[11px] text-[var(--color-muted)] transition-colors hover:border-[var(--color-accent)] hover:text-[var(--color-text)]"
                >
                  <span className="text-[var(--color-accent)]">＋</span> Add player
                </motion.button>
                <AnimatePresence>
                  {adding && (
                    <motion.div
                      initial={{ opacity: 0, y: 4, scale: 0.98 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: 2, scale: 0.98 }}
                      transition={{ duration: 0.14 }}
                      onKeyDown={onAddKeyDown}
                      className="absolute left-0 top-9 z-20 w-64 rounded-lg border border-[var(--color-line)] bg-[rgba(22,23,26,0.92)] p-2 shadow-[var(--shadow-pop)] backdrop-blur-xl"
                    >
                      <input
                        autoFocus
                        value={query}
                        onChange={(e) => {
                          setQuery(e.target.value);
                          setActiveSug(-1);
                        }}
                        placeholder="Type a name…"
                        role="combobox"
                        aria-expanded={suggestions.length > 0}
                        aria-controls="strength-add-list"
                        aria-activedescendant={activeSug >= 0 ? `strength-sug-${activeSug}` : undefined}
                        aria-autocomplete="list"
                        aria-label="Add player"
                        className="mono w-full rounded-lg border border-[var(--color-line)] bg-[var(--color-bg)] px-3 py-2 text-sm text-[var(--color-text)] outline-none focus:border-[var(--color-accent)]"
                      />
                      {suggestions.length > 0 && (
                        <div id="strength-add-list" role="listbox" aria-label="Player suggestions" className="mt-1.5 max-h-60 overflow-y-auto">
                          {suggestions.map((p, i) => (
                            <button
                              key={p.name}
                              id={`strength-sug-${i}`}
                              role="option"
                              aria-selected={i === activeSug}
                              onClick={() => addPick(p.name)}
                              onMouseEnter={() => setActiveSug(i)}
                              className="row-glow flex w-full items-center justify-between rounded-lg px-2.5 py-1.5 text-left text-sm text-[var(--color-text)]"
                              style={{ background: i === activeSug ? "rgba(255,255,255,0.06)" : undefined }}
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
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* manually added players */}
              {picks.map((n) => (
                <motion.button
                  key={n}
                  onClick={() => removePick(n)}
                  whileTap={{ scale: 0.96 }}
                  transition={SPRING}
                  className="chip flex items-center gap-1.5 text-[var(--color-text)] transition-colors hover:border-[var(--color-loss)] hover:text-[var(--color-loss)]"
                  style={{ borderColor: "var(--color-accent)" }}
                  title="Remove"
                >
                  {lastName(n)} <span className="text-[var(--color-faint)]">✕</span>
                </motion.button>
              ))}
            </div>
          </Reveal>

          {/* chart */}
          <Reveal delay={0.05}>
            <div className="mt-5 panel p-3 sm:p-5">
              <ScatterChart
                key={`${tour}-${count}`}
                data={shown.map((p) => ({
                  id: p.name, x: p.servePct, y: p.returnPct,
                  label: lastName(p.name), color: quadColor(p, sel), ring: picks.includes(p.name), p,
                }))}
                xLabel="serve points won →"
                yLabel="return points won →"
                xTickFmt={(v) => pct(v, 0)}
                yTickFmt={(v) => pct(v, 0)}
                tooltip={(d) => ({
                  title: d.p.name,
                  lines: [`serve ${pct(d.p.servePct, 1)} · ret ${pct(d.p.returnPct, 1)}`, `elo rank #${d.p.eloRank}`],
                })}
                onDotClick={(d) => router.push(playerHref(d.id, tour))}
                hover={hover}
                onHover={setHover}
                extraDomainPoints={[{ x: tourAvg.s, y: tourAvg.r }]}
                ariaLabel="Serve versus return scatter plot"
                annotations={({ X, Y, bounds: b }) => (
                  <>
                    {/* tour-average reference crosshair (dashed, faint) */}
                    <line x1={X(tourAvg.s)} y1={b.top} x2={X(tourAvg.s)} y2={b.top + b.ih} stroke="var(--color-faint)" strokeWidth={1} strokeDasharray="3 4" />
                    <line x1={b.left} y1={Y(tourAvg.r)} x2={b.left + b.iw} y2={Y(tourAvg.r)} stroke="var(--color-faint)" strokeWidth={1} strokeDasharray="3 4" />
                    {/* selected-group average cross (solid, brighter) */}
                    <line x1={X(sel.s)} y1={b.top} x2={X(sel.s)} y2={b.top + b.ih} stroke="var(--color-line2)" strokeWidth={1} />
                    <line x1={b.left} y1={Y(sel.r)} x2={b.left + b.iw} y2={Y(sel.r)} stroke="var(--color-line2)" strokeWidth={1} />
                    {/* quadrant corner labels (relative to the selected cross) */}
                    <text x={b.left + b.iw - 8} y={b.top + 16} textAnchor="end" fontSize={10} fill="var(--color-win)" fillOpacity={0.55} className="mono">complete</text>
                    <text x={b.left + 8} y={b.top + 16} textAnchor="start" fontSize={10} fill="var(--color-champ)" fillOpacity={0.55} className="mono">return-first</text>
                    <text x={b.left + b.iw - 8} y={b.top + b.ih - 8} textAnchor="end" fontSize={10} fill="var(--color-hard)" fillOpacity={0.55} className="mono">serve-first</text>
                    <text x={b.left + 8} y={b.top + b.ih - 8} textAnchor="start" fontSize={10} fill="var(--color-loss)" fillOpacity={0.5} className="mono">below avg</text>
                  </>
                )}
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
            {shown.length} players plotted · serve & return are model point-win rates · hover a dot for the full line · click through to the profile
          </p>
        </>
      )}
    </div>
  );
}
