"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useData, useTour } from "@/lib/tour";
import { pct } from "@/lib/ui";
import { PageHead, Loading, Reveal, StatCard } from "@/components/bits";
import { rel } from "@/components/Freshness";
import { EASE } from "@/lib/motion";

/* ============================== types ============================== */
type Metrics = { n: number; acc: number; logloss: number; brier: number };
type CalBin = { bin: string; n: number; pred: number; actual: number };

type Accuracy = {
  window: string; n: number;
  models: Record<string, Metrics>;
  marketAnchor: { acc: number; brier: number };
  calibration: CalBin[];
};
type Track = {
  matchForecasts: {
    logged: number; graded: number; pending: number;
    overall: { n: number; acc: number | null; logloss: number | null; brier: number | null };
    byMonth: { month: string; n: number; acc: number; logloss: number; brier: number }[];
  };
};
type Market = {
  years: [number, number]; matched: number;
  stack?: { fit?: { valStart: number; nVal: number }; val?: { model: Metrics; market: Metrics; stack: Metrics } };
};
type Block = { n: number; acc: number; logloss: number; brier: number };
type Paired = {
  n: number; model: Block; kalshi: Block;
  d_ll: number; d_ll_se: number; d_brier: number; d_brier_se: number; d_acc: number; t: number;
};
type Seg = Paired & { segment: string };
type Receipt = {
  date: string; tour: string; event: string; round: string;
  winner: string; loser: string; pModel: number; pKalshi: number; predSource: string;
};
type Kalshi = {
  tour: string; lastUpdated: string;
  coverage: {
    events: number; matched: number; pending: number; unmatched: number;
    cancelled: number; walkovers: number; retirements: number; date_range: [string | null, string | null];
  };
  headline: Paired | { n: number };
  segments: Seg[];
  calibration: { model: CalBin[]; kalshi: CalBin[] };
  bestCalls: Receipt[];
  worstMisses: Receipt[];
  disagree: { n: number; modelRight: number };
};

/* ============================== helpers ============================== */
const num = (x: number | null | undefined, d = 4) => (x == null || isNaN(x) ? "—" : x.toFixed(d));
const signed = (x: number, d = 4) => (x >= 0 ? "+" : "−") + Math.abs(x).toFixed(d);
const hasHead = (h: Kalshi["headline"]): h is Paired => (h as Paired).model !== undefined;

type Verdict = "ahead" | "behind" | "even";
const verdictOf = (d: number, se: number): Verdict => {
  const lo = d - 1.96 * se, hi = d + 1.96 * se;
  return hi < 0 ? "behind" : lo > 0 ? "ahead" : "even";
};
const VCOLOR: Record<Verdict, string> = {
  ahead: "var(--color-win)", behind: "var(--color-loss)", even: "var(--color-faint)",
};

const MODEL_LABEL: Record<string, string> = {
  eloBlend: "Elo (surface-blended)", pointModel: "Serve/return model", combiner: "XGBoost combiner",
};

/* segment grouping for the forest plot */
const MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const monthLabel = (m: string) => { const [y, mm] = m.split("-"); return `${MONTHS[+mm]} ${y}`; };
const relabel = (s: string): string => {
  if (s.startsWith("pred_source")) return s.includes("live") ? "Live-frozen forecasts" : "Walk-forward backfill";
  if (s.startsWith("kalshi favorite ")) return "Priced " + s.replace("kalshi favorite ", "");
  if (s.startsWith("surface: ")) return s.replace("surface: ", "");
  if (s.startsWith("round ")) return cap(s.replace("round ", ""));
  if (s.startsWith("tier: ")) {
    const t = s.replace("tier: ", "");
    return ({ grand_slam: "Grand slams", masters: "Masters 1000", atp500: "500-level", atp250: "250-level" } as Record<string, string>)[t] || t;
  }
  if (s.startsWith("month ")) return monthLabel(s.replace("month ", ""));
  return cap(s);
};
const GROUPS: { title: string; match: (s: string) => boolean }[] = [
  { title: "Forecast provenance", match: (s) => s.startsWith("pred_source") },
  { title: "Players' rank", match: (s) => s.startsWith("best rank") || s.includes("top-20") || s.includes("top-50") },
  { title: "How the market priced it", match: (s) => s.startsWith("kalshi favorite") },
  { title: "Surface", match: (s) => s.startsWith("surface:") },
  { title: "Tournament tier", match: (s) => s.startsWith("tier:") },
  { title: "Round", match: (s) => s.startsWith("round") },
  { title: "When we disagree with the market", match: (s) => s.includes("agree") },
];

/* ============================== charts ============================== */
/** Reliability bars: predicted (accent) with the realized win-rate dot (green). */
function CalBars({ bins }: { bins: CalBin[] }) {
  return (
    <div>
      {bins.map((c, i) => (
        <div key={c.bin} className="flex items-center gap-3 py-1">
          <span className="mono w-14 text-[11px] text-[var(--color-faint)]">{c.bin}</span>
          <div className="relative h-5 flex-1">
            <div className="bartrack absolute inset-0" />
            <div className="absolute inset-y-0 left-0" style={{ width: `${c.pred * 100}%` }}>
              <motion.div className="h-full w-full rounded-full"
                initial={{ scaleX: 0 }} whileInView={{ scaleX: 1 }} viewport={{ once: true }}
                transition={{ duration: 0.5, ease: EASE, delay: Math.min(i * 0.04, 0.3) }}
                style={{ background: "var(--color-accent-dim)", transformOrigin: "left" }} />
            </div>
            <motion.div className="pointer-events-none absolute inset-0"
              initial={{ x: "0%", opacity: 0 }} whileInView={{ x: `${c.actual * 100}%`, opacity: 1 }}
              viewport={{ once: true }} transition={{ duration: 0.5, ease: EASE, delay: Math.min(i * 0.04, 0.3) }}>
              <div className="absolute left-0 top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-[var(--color-bg)]"
                style={{ background: "var(--color-win)" }} />
            </motion.div>
          </div>
          <span className="mono w-24 text-right text-[11px] text-[var(--color-muted)]">{pct(c.pred, 0)}→{pct(c.actual, 0)}</span>
        </div>
      ))}
      <div className="mono mt-2 flex gap-4 text-[10px] text-[var(--color-faint)]">
        <span><span className="text-[var(--color-accent)]">▰</span> predicted</span>
        <span><span className="text-[var(--color-win)]">●</span> actual win-rate</span>
      </div>
    </div>
  );
}

/** Horizontal accuracy ladder: each model as a bar; combiner highlighted, market anchor a dashed rule. */
function Ladder({ models, anchor }: { models: [string, number][]; anchor: number }) {
  const lo = 0.6, hi = 0.72;
  const X = (v: number) => `${Math.max(0, Math.min(100, ((v - lo) / (hi - lo)) * 100))}%`;
  return (
    <div className="relative">
      {models.map(([k, acc], i) => (
        <div key={k} className="flex items-center gap-3 py-1.5">
          <span className="w-36 text-[12px] text-[var(--color-muted)]">{MODEL_LABEL[k] || k}</span>
          <div className="bartrack relative h-6 flex-1">
            <motion.div className="absolute inset-y-0 left-0 rounded-[4px]"
              initial={{ width: 0 }} whileInView={{ width: X(acc) }} viewport={{ once: true }}
              transition={{ duration: 0.6, ease: EASE, delay: i * 0.06 }}
              style={{ background: k === "combiner" ? "var(--color-accent)" : "var(--color-line2)" }} />
            <span className="mono absolute right-2 top-1/2 -translate-y-1/2 text-[11px]"
              style={{ color: k === "combiner" ? "var(--color-on-accent)" : "var(--color-text)" }}>{pct(acc, 1)}</span>
          </div>
        </div>
      ))}
      <div className="flex items-center gap-3 py-1.5">
        <span className="w-36 text-[12px] text-[var(--color-faint)]">Bookmaker anchor</span>
        <div className="relative h-6 flex-1">
          <div className="absolute inset-y-0 border-l-2 border-dashed border-[var(--color-champ)]" style={{ left: X(anchor) }} />
          <span className="mono absolute text-[11px] text-[var(--color-champ)]" style={{ left: `calc(${X(anchor)} + 6px)`, top: "50%", transform: "translateY(-50%)" }}>{pct(anchor, 1)}</span>
        </div>
      </div>
      <div className="mono mt-1 flex justify-between text-[10px] text-[var(--color-faint)]"><span>{pct(lo, 0)}</span><span>accuracy →</span><span>{pct(hi, 0)}</span></div>
    </div>
  );
}

/** Monthly accuracy bars. */
function MonthBars({ rows }: { rows: { month: string; n: number; acc: number }[] }) {
  const lo = 0.5, hi = 0.9;
  return (
    <div className="flex items-end gap-4" style={{ height: 150 }}>
      {rows.map((m, i) => {
        const barH = Math.max(4, ((m.acc - lo) / (hi - lo)) * 120);
        return (
          <div key={m.month} className="flex flex-1 flex-col items-center justify-end">
            <span className="mono mb-1 text-[12px] font-semibold text-[var(--color-text)]">{pct(m.acc, 0)}</span>
            <motion.div className="w-full max-w-[64px] rounded-t-[3px]"
              initial={{ height: 0 }} whileInView={{ height: barH }} viewport={{ once: true }}
              transition={{ duration: 0.5, ease: EASE, delay: i * 0.08 }} style={{ background: "var(--color-accent)" }} />
            <span className="mono mt-2 text-[11px] text-[var(--color-faint)]">{monthLabel(m.month)} · n{m.n}</span>
          </div>
        );
      })}
    </div>
  );
}

/* forest plot (paired d_ll ± 95% CI by segment) */
type Row = { kind: "head"; label: string } | { kind: "seg"; s: Seg };
function Forest({ segs }: { segs: Seg[] }) {
  const groups = GROUPS.map((g) => ({ title: g.title, rows: segs.filter((s) => g.match(s.segment)) })).filter((g) => g.rows.length);
  const rows: Row[] = [];
  for (const g of groups) { rows.push({ kind: "head", label: g.title }); for (const s of g.rows) rows.push({ kind: "seg", s }); }

  const W = 760, labelW = 236, rightW = 66, headH = 30, rowH = 25, padTop = 8, axisH = 40;
  let y = padTop;
  const ys = rows.map((r) => { const cur = y; y += r.kind === "head" ? headH : rowH; return cur; });
  const plotH = y, H = plotH + axisH;
  const ci = segs.flatMap((s) => [s.d_ll - 1.96 * s.d_ll_se, s.d_ll + 1.96 * s.d_ll_se]);
  let lo = Math.min(0, ...ci), hi = Math.max(0, ...ci);
  const pad = (hi - lo) * 0.06; lo -= pad; hi += pad;
  const X = (v: number) => labelW + ((v - lo) / (hi - lo)) * (W - labelW - rightW);
  const clampX = (v: number) => Math.max(labelW, Math.min(W - rightW, X(v)));
  const ticks: number[] = [];
  for (let t = Math.ceil(lo / 0.025) * 0.025; t <= hi; t += 0.025) ticks.push(+t.toFixed(3));

  return (
    <div className="overflow-x-auto">
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ minWidth: 640 }} role="img"
        aria-label="Paired log-loss difference vs Kalshi by segment, 95% intervals">
        {ticks.map((t) => {
          const zero = Math.abs(t) < 1e-9;
          return (
            <g key={t}>
              <line x1={X(t)} y1={padTop} x2={X(t)} y2={plotH} stroke={zero ? "var(--color-line2)" : "var(--color-line)"} strokeWidth={zero ? 1.5 : 1} />
              <text x={X(t)} y={plotH + 15} textAnchor="middle" fontSize={9.5} className="mono" fill="var(--color-faint)">
                {zero ? "parity" : t.toFixed(3).replace("0.", ".").replace("-.", "−.")}
              </text>
            </g>
          );
        })}
        <text x={X(lo) + 2} y={H - 6} fontSize={9.5} className="mono" fill="var(--color-loss)">← market sharper</text>
        <text x={X(hi) - 2} y={H - 6} textAnchor="end" fontSize={9.5} className="mono" fill="var(--color-win)">model sharper →</text>
        {rows.map((r, i) => {
          const yy = ys[i];
          if (r.kind === "head")
            return (
              <text key={i} x={0} y={yy + 20} fontSize={10.5} fontWeight={600} letterSpacing="0.06em" className="mono"
                fill="var(--color-accent)" style={{ textTransform: "uppercase" }}>{r.label}</text>
            );
          const s = r.s, cy = yy + rowH / 2;
          const vv = verdictOf(s.d_ll, s.d_ll_se), col = VCOLOR[vv];
          const l = clampX(s.d_ll - 1.96 * s.d_ll_se), hx = clampX(s.d_ll + 1.96 * s.d_ll_se);
          return (
            <g key={i}>
              <text x={0} y={cy + 4} fontSize={12} fill="var(--color-text)">{relabel(s.segment)}</text>
              <text x={labelW - 12} y={cy + 4} textAnchor="end" fontSize={10.5} className="mono" fill="var(--color-faint)">{s.n}</text>
              <motion.line x1={l} y1={cy} x2={hx} y2={cy} stroke={col} strokeWidth={2}
                initial={{ pathLength: 0, opacity: 0 }} whileInView={{ pathLength: 1, opacity: 1 }} viewport={{ once: true }}
                transition={{ duration: 0.5, ease: EASE, delay: Math.min(i * 0.015, 0.3) }} />
              <line x1={l} y1={cy - 3.5} x2={l} y2={cy + 3.5} stroke={col} strokeWidth={2} />
              <line x1={hx} y1={cy - 3.5} x2={hx} y2={cy + 3.5} stroke={col} strokeWidth={2} />
              <motion.circle cx={X(s.d_ll)} cy={cy} r={vv === "even" ? 3.6 : 4.4} fill={col}
                initial={{ scale: 0 }} whileInView={{ scale: 1 }} viewport={{ once: true }}
                transition={{ duration: 0.3, delay: Math.min(i * 0.015 + 0.15, 0.4) }}
                style={{ transformBox: "fill-box", transformOrigin: "center" }} />
              <text x={W} y={cy + 4} textAnchor="end" fontSize={10.5} className="mono" fill={vv === "even" ? "var(--color-muted)" : col}>
                {signed(s.d_ll, 3)}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

/** Best-call / worst-miss table. */
function Receipts({ rows, good }: { rows: Receipt[]; good: boolean }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[13px]">
        <thead className="mono text-[10px] uppercase tracking-wider text-[var(--color-faint)]">
          <tr className="border-b border-[var(--color-line)]">
            <th className="py-2 pr-2 text-left">Match</th>
            <th className="px-2 py-2 text-right">Model</th>
            <th className="px-2 py-2 text-right">Market</th>
          </tr>
        </thead>
        <tbody className="mono">
          {rows.map((r, i) => (
            <motion.tr key={r.event + r.winner + i} initial={{ opacity: 0, y: 5 }} whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }} transition={{ duration: 0.3, delay: Math.min(i * 0.05, 0.3) }}
              className="row-glow border-b border-[var(--color-line)]/40">
              <td className="py-2 pr-2">
                <div className="font-[var(--font-body)] text-[var(--color-text)]">{r.winner} <span className="text-[var(--color-faint)]">d.</span> {r.loser}</div>
                <div className="text-[11px] text-[var(--color-faint)]">
                  {r.event} · {r.round} · {r.date}
                  <span className="ml-1.5" style={{ color: r.predSource === "live" ? "var(--color-win)" : "var(--color-faint)" }}>
                    {r.predSource === "live" ? "live" : "backfill"}</span>
                </div>
              </td>
              <td className="px-2 py-2 text-right font-semibold" style={{ color: good ? "var(--color-win)" : "var(--color-loss)" }}>{pct(r.pModel, 0)}</td>
              <td className="px-2 py-2 text-right text-[var(--color-muted)]">{pct(r.pKalshi, 0)}</td>
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const Eyebrow = ({ children }: { children: React.ReactNode }) => <div className="eyebrow mb-3">{children}</div>;
const SectionHead = ({ n, kicker, title, sub }: { n: string; kicker: string; title: string; sub: string }) => (
  <>
    <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--color-accent)]">{n} · {kicker}</div>
    <h2 className="display mt-1.5 text-2xl">{title}</h2>
    <p className="mt-2 max-w-2xl text-[14px] text-[var(--color-muted)]">{sub}</p>
  </>
);

/* ============================== page ============================== */
export default function ScorecardPage() {
  const { tour } = useTour();
  const acc = useData<Accuracy>("accuracy.json").data;
  const track = useData<Track>("track.json").data;
  const market = useData<Market>("market.json").data;
  const { data: kalshi, loading } = useData<Kalshi>("kalshi.json");

  const h = kalshi?.headline;
  const kHead = h && hasHead(h) ? h : null;
  const kv = kHead ? verdictOf(kHead.d_ll, kHead.d_ll_se) : "even";
  const combiner = acc?.models?.combiner;
  const live = track?.matchForecasts;
  const val = market?.stack?.val;

  const [now, setNow] = useState<number | null>(null);
  useEffect(() => {
    setNow(Date.now());
    const id = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(id);
  }, []);
  const freshness = kalshi?.lastUpdated && now !== null ? rel(kalshi.lastUpdated, now) : null;

  return (
    <div className="pb-16">
      <PageHead
        eyebrow={`${tour.toUpperCase()} · model scorecard${acc?.window ? ` · ${acc.window}` : ""}`}
        title="The Scorecard"
        sub="Every number here is out-of-sample: a full walk-forward backtest, live forecasts frozen before results, and paired comparisons against the market on identical matches. Lower log-loss and Brier are better; positive Δ means the model was sharper than the market."
      />

      {loading && !kalshi && <Loading />}

      {/* ---------- hero ---------- */}
      <Reveal>
        <div className="mt-8 grid grid-cols-2 gap-2.5 lg:grid-cols-4">
          <StatCard label="Walk-forward accuracy" value={combiner ? combiner.acc * 100 : "—"} decimals={1} suffix="%"
            sub={combiner ? `${combiner.n.toLocaleString()} matches · Brier ${combiner.brier.toFixed(3)}` : undefined} />
          <StatCard label="Live record" value={live?.overall.acc != null ? live.overall.acc * 100 : "—"} decimals={1} suffix="%"
            sub={live ? `${live.graded} graded pre-match calls` : undefined} />
          <StatCard label="Vs Kalshi (Δ log-loss)" value={kHead ? signed(kHead.d_ll) : "—"}
            sub={kHead ? `±${num(kHead.d_ll_se)} · ${kv === "even" ? "at parity" : kv}` : undefined} />
          <StatCard label="Vs Pinnacle (Δ log-loss)" value={val ? signed(val.market.logloss - val.model.logloss, 4) : "—"}
            sub={val && market ? `${val.model.n.toLocaleString()} matches (${market.stack?.fit?.valStart ?? market.years[0]}+ validation) · closing odds` : undefined} />
        </div>
        {freshness && (
          <div className="mono mt-2 flex items-center gap-1.5 text-[11px] text-[var(--color-faint)]">
            <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-[var(--color-win)]" /> ledger updated {freshness}
          </div>
        )}
      </Reveal>

      {/* ---------- 01 absolute skill ---------- */}
      {acc && combiner && (
        <section className="mt-14">
          <SectionHead n="01" kicker="Absolute skill" title="The combiner earns its keep — and stays honest"
            sub={`Walk-forward testing across ${acc.window}: every prediction trained only on earlier data. The XGBoost combiner adds a point or two over its best component, and a “70%” really wins about 70% of the time.`} />
          <div className="mt-5 grid gap-2.5 lg:grid-cols-2">
            <div className="panel p-5">
              <Eyebrow>Model ladder — accuracy by layer</Eyebrow>
              <Ladder models={(["eloBlend", "pointModel", "combiner"] as const).filter((k) => acc.models[k]).map((k) => [k, acc.models[k].acc] as [string, number])}
                anchor={acc.marketAnchor.acc} />
            </div>
            <div className="panel p-5">
              <Eyebrow>Calibration — {acc.n.toLocaleString()} walk-forward matches</Eyebrow>
              <CalBars bins={acc.calibration} />
            </div>
          </div>
        </section>
      )}

      {/* ---------- 02 vs the markets ---------- */}
      {kHead && kalshi && (
        <section className="mt-14">
          <SectionHead n="02" kicker="Against the markets" title="Where we hold our own, and where we don’t"
            sub="Paired against Kalshi’s morning line (de-vigged bid/ask mid at 08:00 UTC, rebuilt from candlesticks) on identical matches. Bars that clear parity are colored; with a couple of months of data, most straddle it — and saying so is the point." />

          <div className="mt-5 panel p-4 sm:p-5">
            <Eyebrow>Paired Δ log-loss by segment, 95% intervals</Eyebrow>
            <Forest segs={kalshi.segments.filter((s) => !s.segment.startsWith("tour:"))} />
            <div className="mono mt-2 flex flex-wrap gap-4 text-[10px] text-[var(--color-faint)]">
              <span><span style={{ color: "var(--color-win)" }}>●</span> model sharper (95%)</span>
              <span><span style={{ color: "var(--color-loss)" }}>●</span> market sharper (95%)</span>
              <span><span style={{ color: "var(--color-faint)" }}>●</span> statistically even</span>
            </div>
            {kalshi.disagree.n > 0 && (
              <p className="mt-3 border-t border-[var(--color-line)] pt-3 text-[13px] text-[var(--color-muted)]">
                When model and market disagree by ≥10 points, the model was closer to the outcome in{" "}
                <span className="mono text-[var(--color-text)]">{kalshi.disagree.modelRight}/{kalshi.disagree.n}</span> matches.
              </p>
            )}
          </div>

          <div className="mt-2.5 grid gap-2.5 lg:grid-cols-2">
            <div className="panel p-5">
              <Eyebrow>Calibration vs Kalshi — model &amp; market</Eyebrow>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <div className="mono mb-1 text-[11px] text-[var(--color-accent)]">Model</div>
                  <CalBars bins={kalshi.calibration.model} />
                </div>
                <div>
                  <div className="mono mb-1 text-[11px] text-[var(--color-cmp)]">Kalshi</div>
                  <CalBars bins={kalshi.calibration.kalshi} />
                </div>
              </div>
            </div>
            <div className="panel p-5">
              <Eyebrow>Vs Pinnacle closing{val && market ? ` · validation ${market.stack?.fit?.valStart ?? market.years[0]}–${market.years[1]}` : ""}</Eyebrow>
              {val ? (
                <table className="w-full text-[13px]">
                  <thead className="mono text-[10px] uppercase tracking-wider text-[var(--color-faint)]">
                    <tr className="border-b border-[var(--color-line)]"><th className="py-2 text-left"></th><th className="px-2 py-2 text-right">Acc</th><th className="px-2 py-2 text-right">Log-loss</th><th className="px-2 py-2 text-right">Brier</th></tr>
                  </thead>
                  <tbody className="mono">
                    {([["Model", val.model], ["Market", val.market], ["Model+market stack", val.stack]] as [string, Metrics][]).map(([label, m]) => (
                      <tr key={label} className="border-b border-[var(--color-line)]/40">
                        <td className="py-2 text-[var(--color-text)]">{label}</td>
                        <td className="px-2 py-2 text-right">{pct(m.acc, 1)}</td>
                        <td className="px-2 py-2 text-right text-[var(--color-muted)]">{m.logloss.toFixed(4)}</td>
                        <td className="px-2 py-2 text-right">{m.brier.toFixed(4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : <p className="text-[13px] text-[var(--color-faint)]">Odds benchmark not available for this tour yet.</p>}
              <p className="mono mt-3 text-[11px] leading-relaxed text-[var(--color-faint)]">
                Pinnacle’s closing line is the sharpest in tennis. The Kalshi numbers are its <span className="text-[var(--color-muted)]">morning</span> line — a weaker bar, on a favorite-heavy subset. Not directly comparable.
              </p>
            </div>
          </div>
        </section>
      )}

      {/* ---------- 03 live record ---------- */}
      {live && live.byMonth.length > 0 && (
        <section className="mt-14">
          <SectionHead n="03" kicker="The live record" title="Frozen before the match, graded as results land"
            sub="The strictest numbers here — probabilities logged at first sighting, never touched, then scored once the match resolves." />
          <div className="mt-5 panel p-5">
            <Eyebrow>Graded accuracy by month</Eyebrow>
            <MonthBars rows={live.byMonth} />
          </div>
        </section>
      )}

      {/* ---------- 04 receipts ---------- */}
      {kalshi && (kalshi.bestCalls.length > 0 || kalshi.worstMisses.length > 0) && (
        <section className="mt-14">
          <SectionHead n="04" kicker="Receipts" title="Called against the market — and the ones that got away"
            sub="Matches where the model and the market stood on opposite sides of 50%. Percentages are what each gave the eventual winner." />
          <div className="mt-5 grid gap-2.5 lg:grid-cols-2">
            <div className="panel p-5">
              <Eyebrow><span className="text-[var(--color-win)]">Model right, market wrong ✓</span></Eyebrow>
              <Receipts rows={kalshi.bestCalls} good />
            </div>
            <div className="panel p-5">
              <Eyebrow><span className="text-[var(--color-loss)]">Market saw it, we didn’t ✗</span></Eyebrow>
              <Receipts rows={kalshi.worstMisses} good={false} />
            </div>
          </div>
        </section>
      )}

      {/* ---------- 05 coverage & caveats ---------- */}
      {kalshi && (
        <section className="mt-14">
          <SectionHead n="05" kicker="Coverage & caveats" title="What these numbers can and can’t say" sub="" />
          <div className="mt-5 grid gap-2.5 lg:grid-cols-2">
            <div className="panel overflow-hidden">
              <table className="w-full text-[13px]">
                <tbody className="mono">
                  {([
                    ["Kalshi events seen", kalshi.coverage.events],
                    ["Matched to a result", kalshi.coverage.matched],
                    ["Awaiting play / results", kalshi.coverage.pending],
                    ["Cancelled (never played)", kalshi.coverage.cancelled],
                    ["Walkovers & retirements", kalshi.coverage.walkovers + kalshi.coverage.retirements],
                    ["Unmatched (mostly qualifying)", kalshi.coverage.unmatched],
                  ] as [string, number][]).map(([label, n], i) => (
                    <motion.tr key={label} initial={{ opacity: 0, y: 5 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
                      transition={{ duration: 0.3, delay: Math.min(i * 0.04, 0.25) }} className="row-glow border-b border-[var(--color-line)]/40 last:border-0">
                      <td className="px-4 py-2.5 font-[var(--font-body)] text-[var(--color-text)]">{label}</td>
                      <td className="px-4 py-2.5 text-right text-[var(--color-text)]">{n}</td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="panel p-5 text-[13px] leading-relaxed text-[var(--color-muted)]">
              <p><span className="text-[var(--color-text)]">Read as direction, not destiny.</span> Two months of exchange data is a small sample; most segment intervals cross parity. The Kalshi comparison is against the <span className="text-[var(--color-text)]">morning</span> line, a weaker bar than the Pinnacle close.</p>
              <p className="mt-2.5">Most rows are back-filled with walk-forward probabilities (today’s model, leak-free walk). The <span className="text-[var(--color-text)]">live-frozen</span> slice — forecasts logged days before the match — is the honest real-time number, broken out first in the forest plot. As it accumulates across surfaces it becomes the series that matters most.</p>
              <p className="mt-2.5 mono text-[11px] text-[var(--color-faint)]">Sources: track.json &amp; kalshi.json refreshed hourly by CI; accuracy.json &amp; market.json rebuilt by the daily full retrain.</p>
            </div>
          </div>
        </section>
      )}

      {kalshi && !kHead && (
        <div className="panel mt-8 p-5 text-[14px] text-[var(--color-muted)]">
          The Kalshi ledger is accruing — no scored matches for {tour.toUpperCase()} yet. The backtest, live-record and calibration sections above still apply.
        </div>
      )}
    </div>
  );
}
