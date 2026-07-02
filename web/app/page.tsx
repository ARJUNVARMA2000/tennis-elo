"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { useData, useTour } from "@/lib/tour";
import { pct, surfaceColor, heat } from "@/lib/ui";
import { PageHead, Loading, Reveal } from "@/components/bits";
import { SPRING_SOFT } from "@/lib/motion";
import LiveTicker from "@/components/LiveTicker";

type Proj = { name: string; champion: number; final: number | null; sf: number | null; reach?: Record<string, number> };
type Tournament = {
  name: string; surface: string; level: string; bestOf: number;
  start: string; end: string; status: "completed" | "live";
  drawSize: number; aliveCount: number;
  champion: string | null; runnerUp: string | null;
  modelFavorite: string | null; favoritePicked: boolean;
  projection: Proj[];
};

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
function dateRange(start: string, end: string): string {
  const s = new Date(start + "T00:00"), e = new Date(end + "T00:00");
  const sm = MONTHS[s.getMonth()], em = MONTHS[e.getMonth()];
  return sm === em ? `${sm} ${s.getDate()}–${e.getDate()}` : `${sm} ${s.getDate()} – ${em} ${e.getDate()}`;
}

// Round-by-round forecast table: which rounds to show (deepest, top-players-down) + labels.
const DEEP_ROUNDS = ["R16", "QF", "SF", "F", "Champion"];
const ROUND_LABEL: Record<string, string> = {
  R128: "R128", R64: "R64", R32: "R32", R16: "R16", QF: "QF", SF: "SF", F: "F", Champion: "Win",
};

/** Per-round reach odds for a player, with a graceful fallback if `reach` is absent (stale JSON). */
function reachOf(p: Proj): Record<string, number> {
  if (p.reach && Object.keys(p.reach).length) return p.reach;
  const r: Record<string, number> = {};
  if (p.sf != null) r.SF = p.sf;
  if (p.final != null) r.F = p.final;
  r.Champion = p.champion;
  return r;
}

export default function Tournaments() {
  const { tour } = useTour();
  const { data, loading } = useData<Tournament[]>("tournaments.json");

  // When a Grand Slam is in progress, the home page focuses on it: a prominent
  // round-by-round forecast, with the week's other events tucked behind a toggle.
  const slam = (data || []).find((t) => t.status === "live" && t.level === "Grand Slam");
  const others = (data || []).filter((t) => t !== slam);

  if (slam) {
    return (
      <div className="pb-16">
        <PageHead
          eyebrow={`${tour.toUpperCase()} · championship forecast`}
          title={slam.name}
          sub="The model's live title odds — every contender's chance of reaching each round, from the favourites on down. Updated as the draw thins."
        />
        <LiveTicker />
        <Reveal>
          <SlamHero t={slam} />
        </Reveal>
        {others.length > 0 && <OtherEvents events={others} />}
      </div>
    );
  }

  return (
    <div className="pb-16">
      <PageHead
        eyebrow={`${tour.toUpperCase()} · the current swing`}
        title="Latest Tournaments"
        sub="Every recent event with the model's title odds for the field. Live events show who's favoured from here; finished events show whether the model called the champion."
      />
      <LiveTicker />

      {loading && <Loading />}
      {data && data.length === 0 && (
        <div className="mono mt-10 text-sm text-[var(--color-faint)]">No recent tournaments in the data yet.</div>
      )}

      <div className="mt-8 grid gap-4 lg:grid-cols-2">
        {(data || []).map((t, i) => (
          <Reveal key={t.name + t.start} delay={Math.min(i * 0.04, 0.3)}>
            <Card t={t} />
          </Reveal>
        ))}
      </div>
    </div>
  );
}

/** Prominent forecast hero for the focused Slam: top players × per-round reach odds. */
function SlamHero({ t }: { t: Tournament }) {
  const [open, setOpen] = useState(false);
  const sc = surfaceColor(t.surface);
  const present = new Set(t.projection.flatMap((p) => Object.keys(reachOf(p))));
  const cols = DEEP_ROUNDS.filter((c) => present.has(c));
  const shown = open ? t.projection : t.projection.slice(0, 16);

  return (
    <div className="panel-glow mt-8 p-5 sm:p-6">
      {/* header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="chip" style={{ color: sc, borderColor: sc }}>{t.surface}</span>
            <span className="mono text-[11px] text-[var(--color-faint)]">{t.level} · Bo{t.bestOf}</span>
          </div>
          <h2 className="display mt-2 text-3xl leading-tight sm:text-4xl">{t.name}</h2>
          <div className="mono mt-1 text-[11px] text-[var(--color-faint)]">
            {dateRange(t.start, t.end)} · {t.drawSize} draw
          </div>
        </div>
        <span className="mono flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-[var(--color-accent)]">
          <span className="live-dot inline-block h-2 w-2 rounded-full bg-[var(--color-accent)]" />
          Live · {t.aliveCount} left
        </span>
      </div>

      {/* round-by-round forecast table */}
      <div className="mono mt-5 mb-2 text-[10px] uppercase tracking-wider text-[var(--color-faint)]">
        Title race · chance of reaching each round
      </div>
      <div className="-mx-1 overflow-x-auto">
        <table className="w-full min-w-[460px] border-collapse">
          <thead>
            <tr className="mono text-[10px] uppercase tracking-wider text-[var(--color-faint)]">
              <th className="px-1 pb-2 text-right font-normal">#</th>
              <th className="px-1 pb-2 text-left font-normal">Player</th>
              {cols.map((c) => (
                <th
                  key={c}
                  className={`px-1 pb-2 text-center font-normal ${c === "Champion" ? "text-[var(--color-champ)]" : ""}`}
                >
                  {ROUND_LABEL[c]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {shown.map((p, i) => {
              const r = reachOf(p);
              return (
                <tr key={p.name} className="row-glow border-t border-[var(--color-line)]">
                  <td className="mono px-1 py-1.5 text-right text-[11px] text-[var(--color-faint)]">{i + 1}</td>
                  <td className="px-1 py-1.5 text-[13px] whitespace-nowrap">{p.name}</td>
                  {cols.map((c) => {
                    const v = r[c];
                    const isWin = c === "Champion";
                    return (
                      <td key={c} className="px-1 py-1.5 text-center">
                        {v == null ? (
                          <span className="text-[var(--color-faint)]">—</span>
                        ) : (
                          <span
                            className={`mono inline-block rounded px-1.5 py-0.5 text-[11px] ${isWin ? "font-semibold" : ""}`}
                            style={{ background: `${heat(v)}${isWin ? "33" : "1a"}`, color: heat(v) }}
                          >
                            {pct(v, 0)}
                          </span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {t.projection.length > 16 && (
        <button onClick={() => setOpen(!open)} className="mono mt-3 text-[11px] text-[var(--color-accent)] hover:underline">
          {open ? "show less" : `show full field (${t.projection.length})`}
        </button>
      )}
    </div>
  );
}

/** The week's non-Slam events, collapsed by default so the Slam stays front-and-centre. */
function OtherEvents({ events }: { events: Tournament[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-10 border-t border-[var(--color-line)] pt-6">
      <button onClick={() => setOpen(!open)} className="mono text-[12px] text-[var(--color-accent)] hover:underline">
        {open ? "hide other recent events" : `show other recent events (${events.length})`}
      </button>
      {open && (
        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          {events.map((t, i) => (
            <Reveal key={t.name + t.start} delay={Math.min(i * 0.04, 0.3)}>
              <Card t={t} />
            </Reveal>
          ))}
        </div>
      )}
    </div>
  );
}

function Card({ t }: { t: Tournament }) {
  const [open, setOpen] = useState(false);
  const sc = surfaceColor(t.surface);
  const live = t.status === "live";
  const shown = open ? t.projection : t.projection.slice(0, 5);
  const maxP = Math.max(0.01, ...t.projection.map((p) => p.champion));

  return (
    <div className="panel flex h-full flex-col p-5">
      {/* header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="chip" style={{ color: sc, borderColor: sc }}>{t.surface}</span>
            <span className="mono text-[11px] text-[var(--color-faint)]">{t.level} · Bo{t.bestOf}</span>
          </div>
          <h3 className="display mt-2 text-2xl leading-tight">{t.name}</h3>
          <div className="mono mt-1 text-[11px] text-[var(--color-faint)]">
            {dateRange(t.start, t.end)} · {t.drawSize} draw
          </div>
        </div>
        {live ? (
          <span className="mono flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-[var(--color-accent)]">
            <span className="live-dot inline-block h-2 w-2 rounded-full bg-[var(--color-accent)]" />
            Live · {t.aliveCount} left
          </span>
        ) : (
          <span className="mono text-[11px] uppercase tracking-wider text-[var(--color-faint)]">Final</span>
        )}
      </div>

      {/* champion banner (completed) */}
      {t.champion && (
        <div className="mt-4 flex items-center justify-between rounded-lg border border-[var(--color-line)] bg-[var(--color-panel2)]/40 px-3 py-2">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-[var(--color-faint)]">Champion</div>
            <div className="text-[15px] font-medium text-[var(--color-champ)]">{t.champion}</div>
          </div>
          <div className="text-right">
            <div className="text-[10px] uppercase tracking-wider text-[var(--color-faint)]">Model favoured</div>
            <div className="mono text-[13px]" style={{ color: t.favoritePicked ? "var(--color-win)" : "var(--color-muted)" }}>
              {t.modelFavorite} {t.favoritePicked ? "✓" : "✗"}
            </div>
          </div>
        </div>
      )}

      {/* projection */}
      <div className="mt-4 flex-1">
        <div className="mono mb-2 text-[10px] uppercase tracking-wider text-[var(--color-faint)]">
          {live ? "Title odds from here" : "Pre-event title odds"}
        </div>
        <div className="space-y-1.5">
          {shown.map((p, i) => {
            const isChamp = p.name === t.champion;
            return (
              <div key={p.name} className="flex items-center gap-2.5">
                <span className="mono w-4 text-right text-[11px] text-[var(--color-faint)]">{i + 1}</span>
                <span className="w-40 truncate text-[13px]" style={{ color: isChamp ? "var(--color-champ)" : "var(--color-text)" }}>
                  {p.name}
                </span>
                <div className="bartrack h-1.5 flex-1">
                  <motion.div
                    className="h-full"
                    initial={{ width: 0 }}
                    animate={{ width: `${(p.champion / maxP) * 100}%` }}
                    transition={{ ...SPRING_SOFT, delay: Math.min(i * 0.04, 0.4) }}
                    style={{ background: heat(p.champion) }}
                  />
                </div>
                <span className="mono w-10 text-right text-[12px]" style={{ color: heat(p.champion) }}>
                  {pct(p.champion, 0)}
                </span>
              </div>
            );
          })}
        </div>
        {t.projection.length > 5 && (
          <button onClick={() => setOpen(!open)} className="mono mt-3 text-[11px] text-[var(--color-accent)] hover:underline">
            {open ? "show less" : `show full field (${t.projection.length})`}
          </button>
        )}
      </div>
    </div>
  );
}
