"use client";

import { motion } from "framer-motion";
import { useData, useTour } from "@/lib/tour";
import { pct } from "@/lib/ui";
import { PageHead, Loading, Reveal, StatCard } from "@/components/bits";
import { EASE } from "@/lib/motion";

type Block = { n: number; acc: number; logloss: number; brier: number };
type Paired = {
  n: number; model: Block; kalshi: Block;
  d_ll: number; d_ll_se: number; d_brier: number; d_brier_se: number; d_acc: number; t: number;
};
type Seg = Paired & { segment: string };
type Kalshi = {
  tour: string;
  lastUpdated: string;
  coverage: {
    events: number; matched: number; pending: number; unmatched: number;
    cancelled: number; ambiguous: number; walkovers: number; retirements: number;
    no_price: number; date_range: [string | null, string | null];
  };
  headline: Paired | { n: number };
  segments: Seg[];
};

const num = (x: number, d = 4) => (isNaN(x) ? "—" : x.toFixed(d));
const signed = (x: number, d = 4) => (x >= 0 ? "+" : "") + x.toFixed(d);
const hasHead = (h: Kalshi["headline"]): h is Paired => (h as Paired).model !== undefined;

/** Which side of parity a paired estimate lands on, at the 95% level. */
type Verdict = "ahead" | "behind" | "even";
function verdictOf(d: number, se: number): Verdict {
  const lo = d - 1.96 * se, hi = d + 1.96 * se;
  return hi < 0 ? "behind" : lo > 0 ? "ahead" : "even";
}
const VCOLOR: Record<Verdict, string> = {
  ahead: "var(--color-win)",
  behind: "var(--color-loss)",
  even: "var(--color-faint)",
};

/* ---- segment grouping: flat labels → display groups with friendly names ---- */
const MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const relabel = (s: string): string => {
  if (s.startsWith("pred_source")) return s.includes("live") ? "Live-frozen forecasts" : "Walk-forward backfill";
  if (s.startsWith("kalshi favorite ")) return "Priced " + s.replace("kalshi favorite ", "");
  if (s.startsWith("surface: ")) return s.replace("surface: ", "");
  if (s.startsWith("round ")) return cap(s.replace("round ", ""));
  if (s.startsWith("tier: ")) {
    const t = s.replace("tier: ", "");
    return ({ grand_slam: "Grand slams", masters: "Masters 1000", atp500: "500-level", atp250: "250-level" } as Record<string, string>)[t] || t;
  }
  if (s.startsWith("month ")) { const [y, m] = s.replace("month ", "").split("-"); return `${MONTHS[+m]} ${y}`; }
  return cap(s);
};
const GROUPS: { title: string; match: (s: string) => boolean }[] = [
  { title: "Forecast provenance", match: (s) => s.startsWith("pred_source") },
  { title: "Players' rank", match: (s) => s.startsWith("best rank") || s.includes("top-20") || s.includes("top-50") },
  { title: "How the market priced it", match: (s) => s.startsWith("kalshi favorite") },
  { title: "Surface", match: (s) => s.startsWith("surface:") },
  { title: "Tournament tier", match: (s) => s.startsWith("tier:") },
  { title: "Round", match: (s) => s.startsWith("round") },
  { title: "Month", match: (s) => s.startsWith("month") },
  { title: "When we disagree with the market", match: (s) => s.includes("agree") },
];
function groupSegments(segs: Seg[]) {
  return GROUPS.map((g) => ({ title: g.title, rows: segs.filter((s) => g.match(s.segment)) })).filter((g) => g.rows.length);
}

/* ---------------------------- forest plot ---------------------------- */
type Row = { kind: "head"; label: string } | { kind: "seg"; s: Seg };

function Forest({ segs }: { segs: Seg[] }) {
  const groups = groupSegments(segs);
  const rows: Row[] = [];
  for (const g of groups) {
    rows.push({ kind: "head", label: g.title });
    for (const s of g.rows) rows.push({ kind: "seg", s });
  }

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
        aria-label="Paired log-loss difference vs Kalshi by segment, with 95% confidence intervals">
        {/* gridlines + axis ticks */}
        {ticks.map((t) => {
          const zero = Math.abs(t) < 1e-9;
          return (
            <g key={t}>
              <line x1={X(t)} y1={padTop} x2={X(t)} y2={plotH}
                stroke={zero ? "var(--color-line2)" : "var(--color-line)"} strokeWidth={zero ? 1.5 : 1} />
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
              <text key={i} x={0} y={yy + 20} fontSize={10.5} fontWeight={600} letterSpacing="0.06em"
                className="mono" fill="var(--color-accent)" style={{ textTransform: "uppercase" }}>
                {r.label}
              </text>
            );
          const s = r.s, cy = yy + rowH / 2;
          const v = verdictOf(s.d_ll, s.d_ll_se), col = VCOLOR[v];
          const l = clampX(s.d_ll - 1.96 * s.d_ll_se), h = clampX(s.d_ll + 1.96 * s.d_ll_se);
          return (
            <g key={i} className="row-glow">
              <text x={0} y={cy + 4} fontSize={12} fill="var(--color-text)">{relabel(s.segment)}</text>
              <text x={labelW - 12} y={cy + 4} textAnchor="end" fontSize={10.5} className="mono" fill="var(--color-faint)">{s.n}</text>
              <motion.line
                x1={l} y1={cy} x2={h} y2={cy} stroke={col} strokeWidth={2}
                initial={{ pathLength: 0, opacity: 0 }} whileInView={{ pathLength: 1, opacity: 1 }}
                viewport={{ once: true }} transition={{ duration: 0.5, ease: EASE, delay: Math.min(i * 0.015, 0.3) }} />
              <line x1={l} y1={cy - 3.5} x2={l} y2={cy + 3.5} stroke={col} strokeWidth={2} />
              <line x1={h} y1={cy - 3.5} x2={h} y2={cy + 3.5} stroke={col} strokeWidth={2} />
              <motion.circle
                cx={X(s.d_ll)} cy={cy} r={v === "even" ? 3.6 : 4.4} fill={col}
                initial={{ scale: 0 }} whileInView={{ scale: 1 }} viewport={{ once: true }}
                transition={{ duration: 0.3, delay: Math.min(i * 0.015 + 0.15, 0.4) }}
                style={{ transformBox: "fill-box", transformOrigin: "center" }} />
              <text x={W} y={cy + 4} textAnchor="end" fontSize={10.5} className="mono"
                fill={v === "even" ? "var(--color-muted)" : col}>{signed(s.d_ll, 3).replace("-", "−")}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

/* ------------------------------- page ------------------------------- */
export default function ScorecardPage() {
  const { tour } = useTour();
  const { data, loading } = useData<Kalshi>("kalshi.json");
  const h = data?.headline;
  const head = h && hasHead(h) ? h : null;
  const range = data?.coverage.date_range;
  const v = head ? verdictOf(head.d_ll, head.d_ll_se) : "even";

  return (
    <div className="pb-16">
      <PageHead
        eyebrow={`${tour.toUpperCase()} · vs Kalshi${range?.[0] ? ` · ${range[0]} → ${range[1]}` : ""}`}
        title="Vs the Exchange"
        sub="A match-by-match ledger against Kalshi, the prediction market. Its price is the de-vigged bid/ask mid at 08:00 UTC on match day — the morning line — rebuilt from candlestick history. Positive Δ means the model's probability was sharper than the market's; every figure is paired on the same matches, with 95% intervals."
      />

      {loading && <Loading />}

      {data && !head && (
        <div className="panel mt-8 p-5 text-[14px] text-[var(--color-muted)]">
          The ledger is accruing — no scored matches for {tour.toUpperCase()} yet. Prices are captured for
          upcoming matches and scored once results land.
        </div>
      )}

      {data && head && (
        <>
          {/* headline verdict */}
          <Reveal>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <span className="chip" style={{ color: VCOLOR[v], borderColor: VCOLOR[v] }}>
                {v === "ahead" ? "Ahead of the market" : v === "behind" ? "Behind the market" : "At parity"}
              </span>
              <span className="text-[14px] text-[var(--color-muted)]">
                Across <span className="mono text-[var(--color-text)]">{head.n}</span> scored matches, the model&rsquo;s
                log-loss is <span className="mono text-[var(--color-text)]">{num(head.model.logloss)}</span> vs the market&rsquo;s{" "}
                <span className="mono text-[var(--color-text)]">{num(head.kalshi.logloss)}</span>.
              </span>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2.5 sm:grid-cols-4">
              <StatCard label="Scored matches" value={head.n} />
              <StatCard label="Model accuracy" value={head.model.acc * 100} decimals={1} suffix="%" sub={`Kalshi ${pct(head.kalshi.acc, 1)}`} />
              <StatCard label="Δ log-loss" value={signed(head.d_ll)} sub={`±${num(head.d_ll_se)} · 95% CI`} />
              <StatCard label="Δ Brier" value={signed(head.d_brier)} sub={`±${num(head.d_brier_se)}`} />
            </div>
          </Reveal>

          {/* the forest plot */}
          <Reveal delay={0.05}>
            <div className="mt-10">
              <div className="eyebrow mb-1">Where we hold our own — and where we don&rsquo;t</div>
              <p className="mb-3 max-w-2xl text-[13px] leading-relaxed text-[var(--color-faint)]">
                Each row is the paired log-loss difference on that slice of matches, with its 95% interval. Bars that
                clear parity are colored; bars straddling it are statistically even — with two months of data, that&rsquo;s
                most of them, and saying so is the point.
              </p>
              <div className="panel p-4 sm:p-5">
                <Forest segs={data.segments.filter((s) => !s.segment.startsWith("tour:"))} />
                <div className="mono mt-2 flex flex-wrap gap-4 text-[10px] text-[var(--color-faint)]">
                  <span><span style={{ color: "var(--color-win)" }}>●</span> model sharper (95%)</span>
                  <span><span style={{ color: "var(--color-loss)" }}>●</span> market sharper (95%)</span>
                  <span><span style={{ color: "var(--color-faint)" }}>●</span> statistically even</span>
                </div>
              </div>
            </div>
          </Reveal>

          {/* coverage */}
          <Reveal delay={0.05}>
            <div className="mt-10">
              <div className="eyebrow mb-3">Ledger coverage</div>
              <div className="panel overflow-hidden">
                <table className="w-full text-[13px]">
                  <tbody className="mono">
                    {([
                      ["Kalshi events seen", data.coverage.events, "market questions listed for the tour"],
                      ["Matched to a result", data.coverage.matched, "joined to our result frame by player + date"],
                      ["Awaiting play / results", data.coverage.pending, "upcoming or not yet graded"],
                      ["Cancelled (no match)", data.coverage.cancelled, "settled to a fair price — never played"],
                      ["Walkovers & retirements", data.coverage.walkovers + data.coverage.retirements, "recorded, excluded from scoring"],
                      ["Unmatched", data.coverage.unmatched, "mostly qualifying — no results source"],
                    ] as [string, number, string][]).map(([label, n, note], i) => (
                      <motion.tr
                        key={label}
                        initial={{ opacity: 0, y: 6 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.35, ease: EASE, delay: Math.min(i * 0.04, 0.3) }}
                        className="row-glow border-b border-[var(--color-line)]/50 last:border-0"
                      >
                        <td className="px-4 py-2.5 font-[var(--font-body)] text-[var(--color-text)]">{label}</td>
                        <td className="px-4 py-2.5 text-right text-[var(--color-text)]">{n}</td>
                        <td className="hidden px-4 py-2.5 text-[12px] text-[var(--color-faint)] sm:table-cell">{note}</td>
                      </motion.tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </Reveal>

          {/* caveats */}
          <Reveal delay={0.05}>
            <div className="panel mt-8 p-5 text-[13px] leading-relaxed text-[var(--color-muted)]">
              <p>
                <span className="text-[var(--color-text)]">Read this as direction, not destiny.</span> Two months of
                exchange data is a small sample; most segment intervals cross parity. The comparison is against Kalshi&rsquo;s{" "}
                <span className="text-[var(--color-text)]">morning</span> line, not its sharpest closing price — a weaker
                bar than the Pinnacle-closing benchmark on the <a className="text-[var(--color-accent)]" href="./accuracy">Vs the Market</a> page.
              </p>
              <p className="mt-2.5">
                Most rows are back-filled with walk-forward probabilities (today&rsquo;s model, leak-free walk); the{" "}
                <span className="text-[var(--color-text)]">live-frozen</span> slice — forecasts logged days before the
                match — is the honest real-time number and is broken out first in the plot. As it accumulates across
                surfaces it becomes the series that matters most.
              </p>
            </div>
          </Reveal>
        </>
      )}
    </div>
  );
}
