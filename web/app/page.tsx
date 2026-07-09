"use client";

import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { useData, useTour } from "@/lib/tour";
import { pct, surfaceColor, heat, eloKey, blendedElo, tournamentTier, drawCaveat } from "@/lib/ui";
import { PageHead, Loading, Reveal, CallCard } from "@/components/bits";
import { SPRING_SOFT } from "@/lib/motion";
import { nameKey, type PlayerRow } from "@/lib/live";
import LiveTicker from "@/components/LiveTicker";
import Link from "next/link";
import { upcomingCard, byTournamentTier, type Upcoming } from "@/lib/upcoming";

type Proj = { name: string; champion: number; final: number | null; sf: number | null; reach?: Record<string, number> };
type Tournament = {
  name: string; surface: string; level: string; bestOf: number;
  start: string; end: string; status: "completed" | "live" | "upcoming";
  drawStatus?: "real" | "partial" | "seeded" | "final";
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

/** Heat-tint background for a reach-odds pill. The number itself is always drawn at full
    contrast; only this backdrop carries the heat gradient, brighter as the odds climb. */
function heatBg(v: number, strong = false): string {
  const a = Math.min(255, Math.round((strong ? 0x30 : 0x22) + v * (strong ? 0x55 : 0x48)));
  return `${heat(v)}${a.toString(16).padStart(2, "0")}`;
}

/** Honest flag shown only when a live/upcoming card's odds aren't running on the real
    released draw ("seeded"/"partial") — so a projected bracket never masquerades as the
    official one. Absent (returns nothing) for real-draw and completed events. */
function DrawCaveat({ t, compact = false }: { t: Tournament; compact?: boolean }) {
  const c = drawCaveat(t);
  if (!c) return null;
  if (compact)
    return <div className="mono mt-2 text-[10px] uppercase tracking-wider text-[var(--color-accent)]" title={c.note}>⚠ {c.label}</div>;
  return (
    <div className="mt-4 rounded-lg border px-3 py-2" style={{ borderColor: "color-mix(in srgb, var(--color-accent) 40%, transparent)", background: "color-mix(in srgb, var(--color-accent) 8%, transparent)" }}>
      <div className="mono text-[10px] uppercase tracking-wider text-[var(--color-accent)]">⚠ {c.label}</div>
      <div className="mt-0.5 text-[12px] text-[var(--color-muted)]">{c.note}</div>
    </div>
  );
}

export default function Tournaments() {
  const { tour } = useTour();
  const { data, loading } = useData<Tournament[]>("tournaments.json");

  // When a Grand Slam is in progress, the home page focuses on it: a prominent
  // round-by-round forecast, with the week's other events tucked behind a toggle.
  const slam = (data || []).find((t) => t.status !== "completed" && tournamentTier(t.level, t.name).rank === 0);
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
        <UpNext />
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
      <UpNext />

      {loading && <Loading />}
      {data && data.length === 0 && (
        <div className="mono mt-10 text-sm text-[var(--color-faint)]">No recent tournaments in the data yet.</div>
      )}

      <div className="mt-8 grid gap-4 lg:grid-cols-2">
        {[...(data || [])]
          .sort((a, b) => tournamentTier(a.level, a.name).rank - tournamentTier(b.level, b.name).rank)
          .map((t, i) => (
            <Reveal key={t.name + t.start} delay={Math.min(i * 0.04, 0.3)}>
              <Card t={t} />
            </Reveal>
          ))}
      </div>
    </div>
  );
}

/** Prominent forecast hero for the focused Slam: top players × per-round reach odds.
    Columns are sortable — tap a round to rank the field by its chance of getting there. */
function SlamHero({ t }: { t: Tournament }) {
  const [open, setOpen] = useState(false);
  const { tour } = useTour();
  const sc = surfaceColor(t.surface);
  const present = new Set(t.projection.flatMap((p) => Object.keys(reachOf(p))));
  const cols = DEEP_ROUNDS.filter((c) => present.has(c));

  // Per contender: overall Elo + rank, and the surface-BLENDED rating + rank (the number the model
  // actually predicts with — raw surface Elo is heavily shrunk and misleads). Joined from players.json
  // by canonical name; ranks are within the top-200 board, the same population /rankings shows.
  const { data: players } = useData<PlayerRow[]>("players.json");
  const eloInfo = useMemo(() => {
    const m = new Map<string, { overall: number; overallRank: number; blended: number; blendedRank: number }>();
    if (!players) return m;
    const key = eloKey(t.surface) as keyof PlayerRow;
    const overallRank = new Map<string, number>();
    [...players]
      .filter((p) => typeof p.elo === "number")
      .sort((a, b) => b.elo - a.elo)
      .forEach((p, i) => overallRank.set(nameKey(p.name), i + 1));
    players
      .filter((p) => typeof p.elo === "number" && typeof p[key] === "number")
      .map((p) => ({ k: nameKey(p.name), overall: p.elo, blended: blendedElo(p.elo, Number(p[key]), tour) }))
      .sort((a, b) => b.blended - a.blended)
      .forEach((x, i) => m.set(x.k, { overall: x.overall, overallRank: overallRank.get(x.k) ?? 0, blended: x.blended, blendedRank: i + 1 }));
    return m;
  }, [players, t.surface, tour]);

  // Sortable table. Default is the title odds (Champion) — the order the data already ships
  // in — so the page opens unchanged; tapping a round header re-ranks the whole field by it.
  const [sortKey, setSortKey] = useState<string>("Champion");
  const [sortDir, setSortDir] = useState<"desc" | "asc">("desc");
  const sortBy = (c: string) => {
    if (sortKey === c) setSortDir((d) => (d === "desc" ? "asc" : "desc"));
    else { setSortKey(c); setSortDir("desc"); }
  };

  const sorted = useMemo(() => {
    const arr = [...t.projection];
    arr.sort((a, b) => {
      const av = reachOf(a)[sortKey] ?? -1, bv = reachOf(b)[sortKey] ?? -1;
      return sortDir === "desc" ? bv - av : av - bv;
    });
    return arr;
  }, [t.projection, sortKey, sortDir]);
  const shown = open ? sorted : sorted.slice(0, 16);

  return (
    <div className="panel-glow mt-8 p-5 sm:p-6">
      {/* header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="chip" style={{ color: sc, borderColor: sc }}>{t.surface}</span>
            <span className="mono text-[11px] text-[var(--color-faint)]">{tournamentTier(t.level, t.name).full} · Bo{t.bestOf}</span>
          </div>
          <h2 className="display mt-2 text-3xl leading-tight sm:text-4xl">{t.name}</h2>
          <div className="mono mt-1 text-[11px] text-[var(--color-faint)]">
            {dateRange(t.start, t.end)} · {t.drawSize} draw
          </div>
        </div>
        {t.status === "upcoming" ? (
          <span className="mono text-[11px] uppercase tracking-wider text-[var(--color-accent)]">Draw released</span>
        ) : (
          <span className="mono flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-[var(--color-accent)]">
            <span className="live-dot inline-block h-2 w-2 rounded-full bg-[var(--color-accent)]" />
            Live · {t.aliveCount} left
          </span>
        )}
      </div>

      <DrawCaveat t={t} />

      {/* round-by-round forecast table */}
      <div className="mono mt-5 mb-2 text-[10px] uppercase tracking-wider text-[var(--color-faint)]">
        Title race · chance of reaching each round · <span className="text-[var(--color-muted)]">tap a round to sort</span>
      </div>
      <div className="-mx-1 overflow-x-auto">
        <table className="w-full min-w-[620px] border-collapse">
          <thead>
            <tr className="mono text-[10px] uppercase tracking-wider text-[var(--color-faint)]">
              <th className="px-1 pb-2 text-right font-normal">#</th>
              <th className="px-1 pb-2 text-left font-normal">Player</th>
              <th className="px-1 pb-2 text-center font-normal whitespace-nowrap">Overall</th>
              <th className="px-1 pb-2 text-center font-normal whitespace-nowrap">{t.surface} blend</th>
              {cols.map((c) => {
                const active = sortKey === c;
                const isWin = c === "Champion";
                return (
                  <th key={c} className="px-1 pb-2 font-normal">
                    <button
                      type="button"
                      onClick={() => sortBy(c)}
                      aria-label={`Sort by chance of reaching ${ROUND_LABEL[c]}`}
                      className={`mono mx-auto flex items-center gap-0.5 uppercase tracking-wider transition-colors hover:text-[var(--color-text)] ${
                        isWin ? "text-[var(--color-champ)]" : active ? "text-[var(--color-text)]" : "text-[var(--color-faint)]"
                      }`}
                    >
                      {ROUND_LABEL[c]}
                      <span className="w-1.5 text-[7px] leading-none">{active ? (sortDir === "desc" ? "▼" : "▲") : ""}</span>
                    </button>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {shown.map((p, i) => {
              const r = reachOf(p);
              const e = eloInfo.get(nameKey(p.name));
              return (
                <tr key={p.name} className="row-glow border-t border-[var(--color-line)]">
                  <td className="mono px-1 py-1.5 text-right text-[11px] text-[var(--color-faint)]">{i + 1}</td>
                  <td className="px-1 py-1.5 text-[13px] whitespace-nowrap">{p.name}</td>
                  <td className="mono px-1 py-1.5 text-center text-[11px] whitespace-nowrap">
                    {e ? (
                      <>
                        <span className="text-[var(--color-text)]">{e.overall}</span>
                        <span className="ml-1 text-[10px] text-[var(--color-faint)]">#{e.overallRank}</span>
                      </>
                    ) : (
                      <span className="text-[var(--color-faint)]">—</span>
                    )}
                  </td>
                  <td className="mono px-1 py-1.5 text-center text-[11px] whitespace-nowrap">
                    {e ? (
                      <>
                        <span className="text-[var(--color-text)]">{e.blended}</span>
                        <span className="ml-1 text-[10px] text-[var(--color-faint)]">#{e.blendedRank}</span>
                      </>
                    ) : (
                      <span className="text-[var(--color-faint)]">—</span>
                    )}
                  </td>
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
                            style={{ background: heatBg(v, isWin), color: isWin ? "var(--color-champ)" : "var(--color-text)" }}
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
  const ordered = [...events].sort((a, b) => tournamentTier(a.level, a.name).rank - tournamentTier(b.level, b.name).rank);
  return (
    <div className="mt-10 border-t border-[var(--color-line)] pt-6">
      <button onClick={() => setOpen(!open)} className="mono text-[12px] text-[var(--color-accent)] hover:underline">
        {open ? "hide other recent events" : `show other recent events (${events.length})`}
      </button>
      {open && (
        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          {ordered.map((t, i) => (
            <Reveal key={t.name + t.start} delay={Math.min(i * 0.04, 0.3)}>
              <Card t={t} />
            </Reveal>
          ))}
        </div>
      )}
    </div>
  );
}

/** "Up next" — the soonest scheduled matches with the model's current win probability,
    reusing the same upcoming.json + projection cards the /schedule board uses (so the two
    surfaces can't drift). Self-hides when nothing is scheduled. Lives on the Overview page
    so the latest model calls are always one glance away, in both the Slam and no-Slam
    layouts; upcoming.json is regenerated every refresh, so these stay current for free. */
const UP_NEXT_COUNT = 6;
function UpNext() {
  const { data } = useData<Upcoming[]>("upcoming.json");
  // Lead with the marquee events: byTournamentTier orders by prestige (Grand Slam → 1000 → …),
  // keeping soonest-first within a tier — so during Wimbledon the SF cards surface here instead
  // of a concurrent 125's opening round that merely happens to be scheduled a day sooner.
  const rows = byTournamentTier(data || []).slice(0, UP_NEXT_COUNT);
  if (rows.length === 0) return null;
  return (
    <section aria-label="Upcoming matches" className="mt-10">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex items-baseline gap-2">
          <span className="eyebrow !text-[var(--color-text)]">Up next</span>
          <span className="hidden text-[11px] text-[var(--color-faint)] sm:inline">model win odds · latest predictions</span>
        </div>
        <Link href="/schedule" className="mono whitespace-nowrap text-[11px] text-[var(--color-accent)] hover:underline">
          full schedule →
        </Link>
      </div>
      <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
        {rows.map((m, i) => (
          <Reveal key={`${m.playerA}-${m.playerB}-${i}`} delay={Math.min(i * 0.03, 0.2)}>
            {/* showEvent: this grid mixes tournaments, so each card names its event (the
                /schedule board omits it — there the event is a section header). */}
            <CallCard tone="projection" {...upcomingCard(m, { showEvent: true })} />
          </Reveal>
        ))}
      </div>
    </section>
  );
}

function Card({ t }: { t: Tournament }) {
  const [open, setOpen] = useState(false);
  const sc = surfaceColor(t.surface);
  const live = t.status !== "completed";     // live or upcoming: show the forward projection
  const shown = open ? t.projection : t.projection.slice(0, 5);
  const maxP = Math.max(0.01, ...t.projection.map((p) => p.champion));

  return (
    <div className="panel flex h-full flex-col p-5">
      {/* header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="chip" style={{ color: sc, borderColor: sc }}>{t.surface}</span>
            <span className="mono text-[11px] text-[var(--color-faint)]">{tournamentTier(t.level, t.name).full} · Bo{t.bestOf}</span>
          </div>
          <h3 className="display mt-2 text-2xl leading-tight">{t.name}</h3>
          <div className="mono mt-1 text-[11px] text-[var(--color-faint)]">
            {dateRange(t.start, t.end)} · {t.drawSize} draw
          </div>
        </div>
        {t.status === "completed" ? (
          <span className="mono text-[11px] uppercase tracking-wider text-[var(--color-faint)]">Final</span>
        ) : t.status === "upcoming" ? (
          <span className="mono text-[11px] uppercase tracking-wider text-[var(--color-accent)]">Draw released</span>
        ) : (
          <span className="mono flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-[var(--color-accent)]">
            <span className="live-dot inline-block h-2 w-2 rounded-full bg-[var(--color-accent)]" />
            Live · {t.aliveCount} left
          </span>
        )}
      </div>

      <DrawCaveat t={t} compact />

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
          {t.status === "live" ? "Title odds from here" : "Pre-event title odds"}
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
                    className="h-full w-full"
                    initial={{ scaleX: 0 }}
                    animate={{ scaleX: p.champion / maxP }}
                    transition={{ ...SPRING_SOFT, delay: Math.min(i * 0.04, 0.4) }}
                    style={{ background: heat(p.champion), transformOrigin: "left" }}
                  />
                </div>
                <span className="mono w-10 text-right text-[12px]" style={{ color: isChamp ? "var(--color-champ)" : "var(--color-text)" }}>
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
