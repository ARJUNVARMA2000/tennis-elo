"use client";

import { useMemo, useState, type ReactNode } from "react";
import { motion } from "framer-motion";
import { useData, useTour } from "@/lib/tour";
import { pct, surfaceColor, heat, eloKey, blendedElo, tournamentTier, drawCaveat, byTournamentPriority, tournamentView, tournamentDrawLabel, emptyProjectionNote } from "@/lib/ui";
import { PageHead, Loading, Reveal, PlayerProfileLink } from "@/components/bits";
import { SPRING_SOFT } from "@/lib/motion";
import { nameKey, type PlayerRow } from "@/lib/live";
import LiveTicker from "@/components/LiveTicker";
import Link from "next/link";
import { pairHref } from "@/lib/url";
import { closestUpcomingMatch, matchesForTournament, type Upcoming } from "@/lib/upcoming";

export type Proj = { name: string; champion: number; final: number | null; sf: number | null; reach?: Record<string, number> };
export type Tournament = {
  name: string; surface: string | null; level: string; bestOf: number;
  start: string; end: string; status: "completed" | "live" | "upcoming";
  drawStatus?: "real" | "partial" | "seeded" | "final" | "unavailable";
  espnId?: string | null;
  drawSize: number | null; aliveCount: number | null;
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
const FORECAST_ROUNDS = ["R128", "R64", "R32", "R16", "QF", "SF", "F", "Champion"];
const DEFAULT_VISIBLE_PLAYERS = 16;
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

/** Shared probability cells for both the focused hero and compact top-event cards. */
export function ReachRow({
  player, cols, prefix,
}: {
  player: Proj; cols: string[]; prefix: ReactNode;
}) {
  const reach = reachOf(player);
  return (
    <tr className="row-glow border-t border-[var(--color-line)]">
      {prefix}
      {cols.map((round) => {
        const value = reach[round];
        const isWin = round === "Champion";
        return (
          <td key={round} className="px-1 py-1.5 text-center">
            {value == null ? (
              <span className="text-[var(--color-faint)]">—</span>
            ) : (
              <span
                className={`mono inline-block rounded px-1.5 py-0.5 text-[11px] ${isWin ? "font-semibold" : ""}`}
                style={{
                  background: heatBg(value, isWin),
                  color: isWin ? "var(--color-champ)" : "var(--color-text)",
                }}
              >
                {pct(value, 0)}
              </span>
            )}
          </td>
        );
      })}
    </tr>
  );
}

/** Shared round-by-round table shell. Callers supply their leading player/Elo cells while
    the rounds, heat treatment, and responsive scroll behavior stay identical. */
export function ReachStrip({
  players, cols, headerPrefix, rowPrefix, roundHeader, minWidth = "min-w-[430px]",
}: {
  players: Proj[];
  cols: string[];
  headerPrefix: ReactNode;
  rowPrefix: (player: Proj, index: number) => ReactNode;
  roundHeader?: (round: string) => ReactNode;
  minWidth?: string;
}) {
  return (
    <div className="-mx-1 overflow-x-auto" data-reach-strip>
      <table className={`w-full border-collapse ${minWidth}`}>
        <thead>
          <tr className="mono text-[10px] uppercase tracking-wider text-[var(--color-faint)]">
            {headerPrefix}
            {cols.map((round) => (
              <th key={round} className="px-1 pb-2 text-center font-normal">
                {roundHeader ? roundHeader(round) : ROUND_LABEL[round]}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {players.map((player, index) => (
            <ReachRow
              key={player.name}
              player={player}
              cols={cols}
              prefix={rowPrefix(player, index)}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
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
  const { data: scheduled } = useData<Upcoming[]>("upcoming.json");
  const { data: players } = useData<PlayerRow[]>("players.json");
  const profileRoster = useMemo(() => new Set((players ?? []).map((player) => player.name)), [players]);

  // Lifecycle owns the page before prestige: live events remain primary, but the next top-tier
  // draw keeps its complete forecast after them. Lower upcoming tiers and recent results stay compact.
  const { hero, grid, other, featuredUpcoming, upcoming, recent } = tournamentView(data || []);
  // Recent-only events are deliberately excluded: the insight labels describe live or upcoming
  // draws, so falling back to a completed event would make "Next marquee" misleading.
  const primary = hero ?? grid[0] ?? featuredUpcoming[0] ?? upcoming[0];

  if (hero) {
    const tier = tournamentTier(hero.level, hero.name);
    return (
      <div className="pb-16">
        <PageHead
          eyebrow={`${tour.toUpperCase()} · ${tier.short} · round-by-round forecast`}
          title={hero.name}
          sub={hero.status === "live"
            ? "The model's live title odds — the leading contenders' chances of reaching each round, from the favourites on down. Updated as the draw thins."
            : "The model's pre-event title odds — the leading contenders' chances of reaching each round before play begins."}
        />
        <OverviewInsights
          events={data || []}
          primary={primary}
          matches={scheduled || []}
          profileRoster={profileRoster}
        />
        <LiveTicker />
        <Reveal>
          <SlamHero t={hero} players={players} profileRoster={profileRoster} upcomingMatches={scheduled || []} />
        </Reveal>
        {other.length > 0 && (
          <CompactEvents
            events={other}
            title={hero.status === "live" ? "Also live" : "Also coming up"}
            profileRoster={profileRoster}
            upcomingMatches={scheduled || []}
          />
        )}
        {featuredUpcoming.length > 0 && (
          <FeaturedUpcomingEvents
            events={featuredUpcoming}
            players={players}
            profileRoster={profileRoster}
            upcomingMatches={scheduled || []}
          />
        )}
        {upcoming.length > 0 && (
          <CompactEvents
            events={upcoming}
            title={featuredUpcoming.length ? "More coming up" : "Coming up"}
            profileRoster={profileRoster}
            upcomingMatches={scheduled || []}
          />
        )}
        {recent.length > 0 && <CompactEvents events={recent} title="Recently finished" profileRoster={profileRoster} upcomingMatches={scheduled || []} />}
      </div>
    );
  }

  return (
    <div className="pb-16">
      <PageHead
        eyebrow={`${tour.toUpperCase()} · the current swing`}
        title="Latest Tournaments"
        sub="Every current event with the model's title odds for the field. Live play comes first; upcoming draws stay close without taking over the page."
      />
      {loading && <Loading variant="insights" />}
      {data && (
        <OverviewInsights
          events={data}
          primary={primary}
          matches={scheduled || []}
          profileRoster={profileRoster}
        />
      )}
      <LiveTicker />
      {loading && <Loading variant="forecast" />}
      {data && !hero && grid.length === 0 && featuredUpcoming.length === 0 && upcoming.length === 0 && recent.length === 0 && (
        <div className="mono mt-10 text-sm text-[var(--color-faint)]">No current tournaments in the data yet.</div>
      )}

      <div className="mt-8 grid gap-4 lg:grid-cols-2">
        {grid.map((t, i) => (
          <Reveal key={t.name + t.start} delay={Math.min(i * 0.04, 0.3)}>
            <Card t={t} profileRoster={profileRoster} upcomingMatches={scheduled || []} />
          </Reveal>
        ))}
      </div>
      {featuredUpcoming.length > 0 && (
        <FeaturedUpcomingEvents
          events={featuredUpcoming}
          players={players}
          profileRoster={profileRoster}
          upcomingMatches={scheduled || []}
        />
      )}
      {upcoming.length > 0 && (
        <CompactEvents
          events={upcoming}
          title={featuredUpcoming.length ? "More coming up" : "Coming up"}
          profileRoster={profileRoster}
          upcomingMatches={scheduled || []}
        />
      )}
      {recent.length > 0 && <CompactEvents events={recent} title="Recently finished" profileRoster={profileRoster} upcomingMatches={scheduled || []} />}
    </div>
  );
}

/** Fast, factual scan of the same forecast data rendered below — no new model output. */
function OverviewInsights({
  events,
  primary,
  matches,
  profileRoster,
}: {
  events: Tournament[];
  primary?: Tournament;
  matches: Upcoming[];
  profileRoster: ReadonlySet<string>;
}) {
  const { tour } = useTour();
  const favourite = primary?.projection.reduce<Proj | undefined>(
    (best, player) => (!best || player.champion > best.champion ? player : best),
    undefined,
  );
  const closest = closestUpcomingMatch(matches);
  const live = events.filter((event) => event.status === "live");
  const active = live.length ? live : events.filter((event) => event.status === "upcoming");
  if (!primary && !closest) return null;

  return (
    <Reveal delay={0.03}>
      <section aria-label="At a glance" className="mt-8">
        <div className="mb-2.5 flex items-baseline gap-2">
          <span className="eyebrow !text-[var(--color-text)]">At a glance</span>
          <span className="text-[11px] text-[var(--color-faint)]">from the current forecast board</span>
        </div>
        <div className="data-scroll -mx-1 grid auto-cols-[minmax(260px,82vw)] grid-flow-col gap-3 px-1 pb-2 sm:mx-0 sm:grid-flow-row sm:grid-cols-3 sm:px-0">
          {primary && (
            <article className="panel min-w-0 p-4">
              <div className="flex items-center justify-between gap-3">
                <span className="eyebrow !text-[10px]">{live.length ? "In play" : "Next marquee"}</span>
                <span className="chip" style={{ color: surfaceColor(primary.surface), borderColor: surfaceColor(primary.surface) }}>
                  {primary.surface || "TBD"}
                </span>
              </div>
              <div className="mt-2 truncate text-[16px] font-medium text-[var(--color-text)]">{primary.name}</div>
              <div className="mono mt-1 text-[10px] text-[var(--color-faint)]">
                {active.length} {active.length === 1 ? "event" : "events"} {live.length ? "live" : "with a released draw"}
                {primary.aliveCount != null && primary.status === "live" ? ` · ${primary.aliveCount} players left` : ""}
              </div>
            </article>
          )}

          {primary && favourite && (
            <article className="panel min-w-0 p-4">
              <div className="flex items-center justify-between gap-3">
                <span className="eyebrow !text-[10px]">Title favourite</span>
                <span className="mono text-[16px] font-semibold text-[var(--color-champ)]">{pct(favourite.champion, 0)}</span>
              </div>
              <PlayerProfileLink
                name={favourite.name}
                profileRoster={profileRoster}
                className="mt-2 block truncate text-[16px] font-medium text-[var(--color-text)]"
                linkClassName="hover:text-[var(--color-accent)] hover:underline"
              />
              <div className="panel-inset mt-2.5 h-2 overflow-hidden p-px">
                <motion.div
                  className="h-full rounded-[5px] bg-[var(--color-champ)]"
                  initial={{ scaleX: 0 }}
                  animate={{ scaleX: favourite.champion }}
                  transition={SPRING_SOFT}
                  style={{ width: "100%", transformOrigin: "left" }}
                />
              </div>
              <div className="mono mt-1.5 truncate text-[10px] text-[var(--color-faint)]">{primary.name} · win probability</div>
            </article>
          )}

          {closest && (
            <article className="panel min-w-0 p-4">
              <div className="flex items-center justify-between gap-3">
                <span className="eyebrow !text-[10px]">Closest next match</span>
                <span className="mono text-[13px] text-[var(--color-accent)]">
                  {pct(Math.max(closest.pA, 1 - closest.pA), 0)}–{pct(Math.min(closest.pA, 1 - closest.pA), 0)}
                </span>
              </div>
              <Link
                href={pairHref("/predict/", closest.playerA, closest.playerB, tour)}
                className="mt-2 block truncate text-[15px] font-medium text-[var(--color-text)] hover:text-[var(--color-accent)] hover:underline"
              >
                {closest.playerA} <span className="text-[var(--color-faint)]">vs</span> {closest.playerB}
              </Link>
              <div className="mono mt-2 truncate text-[10px] text-[var(--color-faint)]">{closest.event} · {closest.round} · open predictor →</div>
            </article>
          )}
        </div>
      </section>
    </Reveal>
  );
}

/** Upcoming top-tier draws keep the complete forecast even while another tournament is live.
    They follow the live surface so current play remains the page's first priority. */
function FeaturedUpcomingEvents({
  events,
  players,
  profileRoster,
  upcomingMatches,
}: {
  events: Tournament[];
  players: PlayerRow[] | null;
  profileRoster: ReadonlySet<string>;
  upcomingMatches: Upcoming[];
}) {
  return (
    <section aria-label="Coming up" className="mt-10">
      <div className="mb-3 flex flex-wrap items-baseline gap-2">
        <span className="eyebrow !text-[var(--color-text)]">Coming up</span>
        <span className="text-[11px] text-[var(--color-faint)]">
          Full round-by-round forecast for the next top-tier {events.length === 1 ? "event" : "events"}
        </span>
      </div>
      {events.map((t) => (
        <Reveal key={t.name + t.start}>
          <SlamHero t={t} players={players} profileRoster={profileRoster} upcomingMatches={upcomingMatches} />
        </Reveal>
      ))}
    </section>
  );
}

/** Prominent forecast hero for the focused Slam: top players × per-round reach odds.
    Columns are sortable — tap a round to rank the field by its chance of getting there. */
function SlamHero({
  t,
  players,
  profileRoster,
  upcomingMatches,
}: {
  t: Tournament;
  players: PlayerRow[] | null;
  profileRoster: ReadonlySet<string>;
  upcomingMatches: Upcoming[];
}) {
  const [open, setOpen] = useState(false);
  const { tour } = useTour();
  const sc = surfaceColor(t.surface);
  const present = new Set(t.projection.flatMap((p) => Object.keys(reachOf(p))));
  const cols = FORECAST_ROUNDS.filter((c) => present.has(c));

  // Per contender: overall Elo + rank, and the surface-BLENDED rating + rank (the number the model
  // actually predicts with — raw surface Elo is heavily shrunk and misleads). Joined from players.json
  // by canonical name; ranks are within the top-200 board, the same population /rankings shows.
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
  const shown = open ? sorted : sorted.slice(0, DEFAULT_VISIBLE_PLAYERS);

  return (
    <div className="panel-glow mt-8 p-5 sm:p-6">
      {/* header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="chip" style={{ color: sc, borderColor: sc }}>{t.surface || "Surface TBD"}</span>
            <span className="mono text-[11px] text-[var(--color-faint)]">{tournamentTier(t.level, t.name).full} · Bo{t.bestOf}</span>
          </div>
          <h2 className="display mt-2 text-3xl leading-tight sm:text-4xl">{t.name}</h2>
          <div className="mono mt-1 text-[11px] text-[var(--color-faint)]">
            {dateRange(t.start, t.end)} · {tournamentDrawLabel(t)}
          </div>
        </div>
        {t.status === "completed" ? (
          <span className="mono text-[11px] uppercase tracking-wider text-[var(--color-faint)]">Final</span>
        ) : t.status === "upcoming" ? (
          <span className="mono text-[11px] uppercase tracking-wider text-[var(--color-accent)]">Draw released</span>
        ) : (
          <span className="mono flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-[var(--color-accent)]">
            <span className="live-dot inline-block h-2 w-2 rounded-full bg-[var(--color-accent)]" />
            Live{t.aliveCount != null ? ` · ${t.aliveCount} left` : ""}
          </span>
        )}
      </div>

      <DrawCaveat t={t} />

      {/* champion banner (completed) — who lifted the trophy, and whether the model favoured them */}
      {t.champion && (
        <div className="mt-4 flex items-center justify-between rounded-lg border border-[var(--color-line)] bg-[var(--color-panel2)]/40 px-3 py-2">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-[var(--color-faint)]">Champion</div>
            <PlayerProfileLink
              name={t.champion}
              profileRoster={profileRoster}
              className="text-[15px] font-medium text-[var(--color-champ)]"
              linkClassName="transition-colors hover:underline"
            />
          </div>
          <div className="text-right">
            <div className="text-[10px] uppercase tracking-wider text-[var(--color-faint)]">{t.modelFavorite ? "Model favoured" : "Projection"}</div>
            <div className="mono text-[13px]" style={{ color: t.favoritePicked ? "var(--color-win)" : "var(--color-muted)" }}>
              {t.modelFavorite ? (
                <>
                  <PlayerProfileLink name={t.modelFavorite} profileRoster={profileRoster} linkClassName="hover:underline" />{" "}
                  {t.favoritePicked ? "✓" : "✗"}
                </>
              ) : "Unavailable"}
            </div>
          </div>
        </div>
      )}

      {/* Round-by-round forecast table. Withheld entirely while the draw is mostly
          unresolved qualifiers (sim/tournaments.projection_is_meaningful): odds computed
          over default-rated placeholders describe nobody, and used to inflate the real
          favourite to 53-56% on day one. The card still carries the schedule facts. */}
      {t.projection.length === 0 ? (
        <div className="mono mt-5 text-[11px] text-[var(--color-faint)]">
          {emptyProjectionNote(t)}
        </div>
      ) : (
      <>
      <div className="mono mt-5 mb-2 text-[10px] uppercase tracking-wider text-[var(--color-faint)]">
        {t.status === "completed" ? "Pre-tournament title race" : "Title race"} · chance of reaching each round · <span className="text-[var(--color-muted)]">tap a round to sort</span>
      </div>
      <ReachStrip
        players={shown}
        cols={cols}
        minWidth="min-w-[620px]"
        headerPrefix={(
          <>
            <th className="px-1 pb-2 text-right font-normal">#</th>
            <th className="px-1 pb-2 text-left font-normal">Player</th>
            <th className="px-1 pb-2 text-center font-normal whitespace-nowrap">Overall</th>
            <th className="px-1 pb-2 text-center font-normal whitespace-nowrap">{t.surface} blend</th>
          </>
        )}
        rowPrefix={(p, i) => {
          const e = eloInfo.get(nameKey(p.name));
          return (
            <>
              <td className="mono px-1 py-1.5 text-right text-[11px] text-[var(--color-faint)]">{i + 1}</td>
              <td className="px-1 py-1.5 text-[13px] whitespace-nowrap" style={p.name === t.champion ? { color: "var(--color-champ)" } : undefined}>
                <PlayerProfileLink name={p.name} profileRoster={profileRoster} linkClassName="transition-colors hover:text-[var(--color-accent)] hover:underline" />
              </td>
              <td className="mono px-1 py-1.5 text-center text-[11px] whitespace-nowrap">
                {e ? (
                  <>
                    <span className="text-[var(--color-text)]">{e.overall}</span>
                    <span className="ml-1 text-[10px] text-[var(--color-faint)]">#{e.overallRank}</span>
                  </>
                ) : <span className="text-[var(--color-faint)]">—</span>}
              </td>
              <td className="mono px-1 py-1.5 text-center text-[11px] whitespace-nowrap">
                {e ? (
                  <>
                    <span className="text-[var(--color-text)]">{e.blended}</span>
                    <span className="ml-1 text-[10px] text-[var(--color-faint)]">#{e.blendedRank}</span>
                  </>
                ) : <span className="text-[var(--color-faint)]">—</span>}
              </td>
            </>
          );
        }}
        roundHeader={(c) => {
          const active = sortKey === c;
          const isWin = c === "Champion";
          return (
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
          );
        }}
      />
      {t.projection.length > DEFAULT_VISIBLE_PLAYERS && (
        <button onClick={() => setOpen(!open)} className="mono mt-3 text-[11px] text-[var(--color-accent)] hover:underline">
          {open ? "show less" : `show all projected (${t.projection.length})`}
        </button>
      )}
      </>
      )}
      <TournamentNextUp t={t} matches={upcomingMatches} profileRoster={profileRoster} />
    </div>
  );
}

/** Compact secondary cohort: supporting live events, upcoming draws, or recent prestige results. */
function CompactEvents({
  events,
  title,
  profileRoster,
  upcomingMatches,
}: {
  events: Tournament[];
  title: string;
  profileRoster: ReadonlySet<string>;
  upcomingMatches: Upcoming[];
}) {
  const ordered = byTournamentPriority(events);
  return (
    <section aria-label={title} className="mt-10">
      <div className="mb-3 flex items-baseline gap-2">
        <span className="eyebrow !text-[var(--color-text)]">{title}</span>
        <span className="text-[11px] text-[var(--color-faint)]">{events.length} {events.length === 1 ? "event" : "events"}</span>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        {ordered.map((t, i) => (
          <Reveal key={t.name + t.start} delay={Math.min(i * 0.04, 0.3)}>
            <Card t={t} compact profileRoster={profileRoster} upcomingMatches={upcomingMatches} />
          </Reveal>
        ))}
      </div>
    </section>
  );
}

function matchDate(date: string): string {
  const parsed = new Date(`${date}T00:00`);
  return Number.isNaN(parsed.getTime()) ? date : `${MONTHS[parsed.getMonth()]} ${parsed.getDate()}`;
}

/** A deliberately small schedule footer for a live event. It replaces the old cross-event
    six-card grid: the schedule now sits where its tournament context is immediately clear. */
function TournamentNextUp({
  t,
  matches,
  profileRoster,
}: {
  t: Tournament;
  matches: Upcoming[];
  profileRoster: ReadonlySet<string>;
}) {
  const rows = matchesForTournament(t, matches);
  if (rows.length === 0) return null;
  return (
    <div className="mt-5 border-t border-[var(--color-line)] pt-4" role="group" aria-label={`Next matches for ${t.name}`} data-next-matches>
      <div className="mb-2.5 flex items-center justify-between gap-3">
        <span className="mono text-[10px] uppercase tracking-wider text-[var(--color-faint)]">Next up</span>
        <Link href="/schedule" className="mono whitespace-nowrap text-[10px] text-[var(--color-accent)] hover:underline">
          full schedule →
        </Link>
      </div>
      <div className="space-y-2">
        {rows.map((match, index) => (
          <div key={`${match.playerA}-${match.playerB}-${index}`} className="rounded-lg bg-[var(--color-panel2)]/45 px-3 py-2">
            <div className="mono mb-1 text-[10px] uppercase tracking-wider text-[var(--color-faint)]">
              {match.round} · {matchDate(match.date)}
            </div>
            <div className="flex min-w-0 items-baseline justify-between gap-3 text-[13px]">
              <div className="min-w-0 truncate">
                <PlayerProfileLink name={match.playerA} profileRoster={profileRoster} linkClassName="hover:text-[var(--color-accent)] hover:underline" />
                {" "}<span className="mx-1.5 text-[var(--color-faint)]">vs</span>{" "}
                <PlayerProfileLink name={match.playerB} profileRoster={profileRoster} linkClassName="hover:text-[var(--color-accent)] hover:underline" />
              </div>
              <span className="mono shrink-0 text-[11px] text-[var(--color-muted)]">
                {pct(match.pA, 0)}–{pct(1 - match.pA, 0)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const EMPTY_PROFILE_ROSTER: ReadonlySet<string> = new Set();

export function Card({
  t,
  compact = false,
  profileRoster = EMPTY_PROFILE_ROSTER,
  upcomingMatches = [],
}: {
  t: Tournament;
  compact?: boolean;
  profileRoster?: ReadonlySet<string>;
  upcomingMatches?: Upcoming[];
}) {
  const [open, setOpen] = useState(false);
  const sc = surfaceColor(t.surface);
  const shown = open ? t.projection : t.projection.slice(0, DEFAULT_VISIBLE_PLAYERS);
  const maxP = Math.max(0.01, ...t.projection.map((p) => p.champion));
  const present = new Set(t.projection.flatMap((p) => Object.keys(reachOf(p))));
  const reachCols = FORECAST_ROUNDS.filter((round) => present.has(round));
  const showReach = !compact && t.status !== "completed" && reachCols.length > 1;

  return (
    <div className="panel flex h-full flex-col p-5">
      {/* header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="chip" style={{ color: sc, borderColor: sc }}>{t.surface || "Surface TBD"}</span>
            <span className="mono text-[11px] text-[var(--color-faint)]">{tournamentTier(t.level, t.name).full} · Bo{t.bestOf}</span>
          </div>
          <h3 className="display mt-2 text-2xl leading-tight">{t.name}</h3>
          <div className="mono mt-1 text-[11px] text-[var(--color-faint)]">
            {dateRange(t.start, t.end)} · {tournamentDrawLabel(t)}
          </div>
        </div>
        {t.status === "completed" ? (
          <span className="mono text-[11px] uppercase tracking-wider text-[var(--color-faint)]">Final</span>
        ) : t.status === "upcoming" ? (
          <span className="mono text-[11px] uppercase tracking-wider text-[var(--color-accent)]">Draw released</span>
        ) : (
          <span className="mono flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-[var(--color-accent)]">
            <span className="live-dot inline-block h-2 w-2 rounded-full bg-[var(--color-accent)]" />
            Live{t.aliveCount != null ? ` · ${t.aliveCount} left` : ""}
          </span>
        )}
      </div>

      <DrawCaveat t={t} compact />

      {/* champion banner (completed) */}
      {t.champion && (
        <div className="mt-4 flex items-center justify-between rounded-lg border border-[var(--color-line)] bg-[var(--color-panel2)]/40 px-3 py-2">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-[var(--color-faint)]">Champion</div>
            <PlayerProfileLink
              name={t.champion}
              profileRoster={profileRoster}
              className="text-[15px] font-medium text-[var(--color-champ)]"
              linkClassName="transition-colors hover:underline"
            />
          </div>
          <div className="text-right">
            <div className="text-[10px] uppercase tracking-wider text-[var(--color-faint)]">{t.modelFavorite ? "Model favoured" : "Projection"}</div>
            <div className="mono text-[13px]" style={{ color: t.favoritePicked ? "var(--color-win)" : "var(--color-muted)" }}>
              {t.modelFavorite ? (
                <>
                  <PlayerProfileLink name={t.modelFavorite} profileRoster={profileRoster} linkClassName="hover:underline" />{" "}
                  {t.favoritePicked ? "✓" : "✗"}
                </>
              ) : "Unavailable"}
            </div>
          </div>
        </div>
      )}

      {/* Projection. Withheld while the draw is mostly unresolved qualifiers — see the
          matching guard on the hero card and sim/tournaments.projection_is_meaningful. */}
      <div className="mt-4 flex-1">
        {t.projection.length === 0 ? (
          <div className="mono text-[11px] text-[var(--color-faint)]">
            {emptyProjectionNote(t)}
          </div>
        ) : (
        <>
        {showReach ? (
          <>
            <div className="mono mb-2 text-[10px] uppercase tracking-wider text-[var(--color-faint)]">
              {t.status === "live" ? "Title race from here" : "Pre-event title race"} · chance of reaching each round
            </div>
            <ReachStrip
              players={shown}
              cols={reachCols}
              headerPrefix={(
                <>
                  <th className="px-1 pb-2 text-right font-normal">#</th>
                  <th className="px-1 pb-2 text-left font-normal">Player</th>
                </>
              )}
              rowPrefix={(p, i) => (
                <>
                  <td className="mono px-1 py-1.5 text-right text-[11px] text-[var(--color-faint)]">{i + 1}</td>
                  <td className="max-w-36 truncate px-1 py-1.5 text-[13px] whitespace-nowrap" style={p.name === t.champion ? { color: "var(--color-champ)" } : undefined}>
                    <PlayerProfileLink name={p.name} profileRoster={profileRoster} linkClassName="transition-colors hover:text-[var(--color-accent)] hover:underline" />
                  </td>
                </>
              )}
            />
          </>
        ) : (
          <>
            <div className="mono mb-2 text-[10px] uppercase tracking-wider text-[var(--color-faint)]">
              {t.status === "live" ? "Title odds from here" : "Pre-event title odds"}
            </div>
            <div className="space-y-1.5">
              {shown.map((p, i) => {
                const isChamp = p.name === t.champion;
                return (
                  <div key={p.name} className="flex items-center gap-2.5">
                    <span className="mono w-4 text-right text-[11px] text-[var(--color-faint)]">{i + 1}</span>
                    <PlayerProfileLink
                      name={p.name}
                      profileRoster={profileRoster}
                      className="w-40 truncate text-[13px]"
                      linkClassName="transition-colors hover:text-[var(--color-accent)] hover:underline"
                      style={{ color: isChamp ? "var(--color-champ)" : "var(--color-text)" }}
                    />
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
          </>
        )}
        {t.projection.length > DEFAULT_VISIBLE_PLAYERS && (
          <button onClick={() => setOpen(!open)} className="mono mt-3 text-[11px] text-[var(--color-accent)] hover:underline">
            {open ? "show less" : `show all projected (${t.projection.length})`}
          </button>
        )}
        </>
        )}
      </div>
      <TournamentNextUp t={t} matches={upcomingMatches} profileRoster={profileRoster} />
    </div>
  );
}
