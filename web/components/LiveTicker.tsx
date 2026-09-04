"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { useData, useTour, type Tour } from "@/lib/tour";
import { fadeUp, stagger } from "@/lib/motion";
import { pairHref, playerHref } from "@/lib/url";
import {
  fetchLiveMatches,
  matchContext,
  rosterName,
  winProb,
  type PlayerRow,
  type RawLiveMatch,
  type TournamentInfo,
} from "@/lib/live";
import { useMatrixShard } from "@/lib/matrix";

const POLL_MS = 60_000;

export type LiveMatchesState = {
  matches: RawLiveMatch[];
  loading: boolean;
  error: boolean;
};

/** One browser poll shared by the live ticker and every scheduled-match surface on its page. */
export function useLiveMatches(tour: Tour): LiveMatchesState {
  const [state, setState] = useState<LiveMatchesState & { tour: Tour }>({
    tour,
    matches: [],
    loading: true,
    error: false,
  });

  // Poll ESPN while the tab is visible; abort in-flight work on unmount/switch.
  useEffect(() => {
    let alive = true;
    let ctrl: AbortController | null = null;
    const poll = async (force = false) => {
      if (!force && document.visibilityState === "hidden") return;
      ctrl?.abort();
      ctrl = new AbortController();
      try {
        const matches = await fetchLiveMatches(tour, ctrl.signal);
        if (alive) setState({ tour, matches, loading: false, error: false });
      } catch {
        if (alive) {
          setState((previous) => previous.tour === tour
            ? { ...previous, loading: false, error: true }
            : { tour, matches: [], loading: false, error: true });
        }
      }
    };
    poll(true);
    const id = setInterval(() => poll(), POLL_MS);
    const onVis = () => {
      if (document.visibilityState === "visible") poll();
    };
    document.addEventListener("visibilitychange", onVis);
    return () => {
      alive = false;
      ctrl?.abort();
      clearInterval(id);
      document.removeEventListener("visibilitychange", onVis);
    };
  }, [tour]);

  return state.tour === tour
    ? state
    : { matches: [], loading: true, error: false };
}

/** "Live now" strip — real ESPN scores polled from the browser every minute,
    paired with the model's pre-match win probability. Hides itself entirely when there
    are no live matches (or ESPN is unreachable). */
export default function LiveTicker({
  live,
  standalone = false,
  emptyMessage,
}: {
  live: LiveMatchesState;
  standalone?: boolean;
  emptyMessage?: string;
}) {
  const { tour } = useTour();
  const { data: players } = useData<PlayerRow[]>("players.json");
  const { data: tournaments } = useData<TournamentInfo[]>("tournaments.json");
  const { matches, loading, error } = live;
  const [liveEvent, setLiveEvent] = useState("all");
  const events = useMemo(() => [...new Set(matches.map((match) => match.event))].sort(), [matches]);
  const activeEvent = events.includes(liveEvent) ? liveEvent : "all";
  const shownMatches = activeEvent === "all"
    ? matches
    : matches.filter((match) => match.event === activeEvent);

  if (!matches.length && !standalone) return null;

  return (
    <motion.section aria-label="Live matches" variants={stagger(0.06)} initial="hidden" animate="show" className={standalone ? "mt-6" : "mt-8"}>
      <div className="mb-2.5 flex flex-wrap items-center gap-2">
        <span className="live-dot inline-block h-1.5 w-1.5 rounded-full bg-[var(--color-accent)]" />
        <span className="eyebrow !text-[var(--color-text)]">Live now</span>
        <span className="text-[11px] text-[var(--color-faint)]">
          ESPN scores · pre-match model odds · refreshes every minute
        </span>
        {standalone && events.length > 1 && (
          <label className="mono ml-auto flex items-center gap-2 text-[10px] uppercase tracking-wider text-[var(--color-faint)]">
            Event
            <select
              aria-label="Live tournament filter"
              value={activeEvent}
              onChange={(event) => setLiveEvent(event.target.value)}
              className="rounded-md border border-[var(--color-line)] bg-[var(--color-panel)] px-2 py-1.5 text-[11px] normal-case tracking-normal text-[var(--color-text)]"
            >
              <option value="all">All events</option>
              {events.map((name) => <option key={name} value={name}>{name}</option>)}
            </select>
          </label>
        )}
      </div>
      {standalone && loading && <div className="panel-inset p-6 text-sm text-[var(--color-muted)]">Checking live courts…</div>}
      {standalone && !loading && error && !matches.length && (
        <div className="panel-inset p-6 text-sm text-[var(--color-muted)]">Live scores are temporarily unavailable. Upcoming and final calls remain available in the other tabs.</div>
      )}
      {standalone && !loading && !error && !matches.length && (
        <div className="panel-inset p-6 text-sm text-[var(--color-muted)]">{emptyMessage ?? "No main-draw matches are live right now."}</div>
      )}
      <ul role="list" className={standalone ? "grid gap-3 sm:grid-cols-2" : "flex gap-3 overflow-x-auto pb-2"}>
        {shownMatches.map((m) => (
          <LiveCard key={m.id} m={m} players={players} tournaments={tournaments} tour={tour} standalone={standalone} />
        ))}
      </ul>
    </motion.section>
  );
}

function LiveCard({
  m,
  players,
  tournaments,
  tour,
  standalone,
}: {
  m: RawLiveMatch;
  players: PlayerRow[] | null;
  tournaments: TournamentInfo[] | null;
  tour: Tour;
  standalone: boolean;
}) {
  const { surface, bestOf } = matchContext(m.event, tournaments);
  const { shard } = useMatrixShard(surface, bestOf);
  const { p } = winProb(m.a, m.b, surface, bestOf, players, shard, tour);
  const currentSet = m.sets.length - 1;

  // ESPN names resolved to canonical roster names — the /player and /style deep
  // links need the exact profiles.json keys, and gate off for unrated players.
  const canonA = rosterName(m.a, players);
  const canonB = rosterName(m.b, players);
  const matchupHref = canonA && canonB ? pairHref("/style/", canonA, canonB, tour) : null;

  const row = (name: string, side: 0 | 1, prob: number | null, canonical: string | null) => {
    const leading = prob !== null && prob >= 0.5;
    return (
      <div className="flex items-baseline gap-2">
        <span
          className={`w-36 truncate text-[12.5px]${leading ? " font-semibold" : ""}`}
          style={{ color: leading || prob === null ? "var(--color-text)" : "var(--color-muted)" }}
        >
          {/* relative z-10 keeps the profile link clickable above the card's
              stretched matchup link (same pattern as CallCard) */}
          {canonical ? (
            <Link
              href={playerHref(canonical, tour)}
              className="relative z-10 transition-colors hover:text-[var(--color-accent)] hover:underline"
            >
              {name}
            </Link>
          ) : (
            name
          )}
        </span>
        <span className="mono flex gap-1.5 text-[12px] text-[var(--color-muted)]">
          {m.sets.map((s, i) => (
            <span
              key={i}
              className={i === currentSet ? "underline decoration-dotted underline-offset-2" : undefined}
              style={{ color: i === currentSet ? "var(--color-text)" : undefined }}
            >
              {s[side]}
            </span>
          ))}
        </span>
        {prob !== null && (
          <span
            className="mono ml-auto text-[11.5px]"
            style={{ color: leading ? "var(--color-accent)" : "var(--color-faint)" }}
          >
            <span className="sr-only">pre-match win probability </span>
            {(prob * 100).toFixed(0)}%
          </span>
        )}
      </div>
    );
  };

  return (
    <motion.li
      variants={fadeUp}
      aria-label={`${m.a} vs ${m.b} — ${m.event}, ${m.round || m.detail}, live`}
      className={`panel relative ${standalone ? "min-w-0" : "min-w-[280px] shrink-0"} p-3 ${matchupHref ? "panel-link" : ""}`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="truncate text-[11px] text-[var(--color-faint)]">
          {m.event} · {m.round || m.detail}
        </span>
        <span className="chip !border-transparent bg-[var(--color-accent-dim)] text-[var(--color-accent)]">
          live
        </span>
      </div>
      <div className="mt-2.5 space-y-1.5">
        {row(m.a, 0, p, canonA)}
        {row(m.b, 1, p === null ? null : 1 - p, canonB)}
      </div>
      {p !== null && (
        <div aria-hidden="true" className="bartrack relative mt-2.5 h-1">
          <div className="absolute inset-0" style={{ background: "rgba(255,255,255,0.10)" }} />
          <motion.div
            className="absolute inset-0"
            animate={{ scaleX: p }}
            transition={{ type: "spring", stiffness: 180, damping: 22 }}
            style={{ background: "var(--color-accent)", transformOrigin: "left", width: "100%" }}
          />
        </div>
      )}
      {matchupHref && (
        <Link
          href={matchupHref}
          aria-label={`Style matchup: ${canonA} vs ${canonB}`}
          className="absolute inset-0 rounded-[inherit]"
        />
      )}
    </motion.li>
  );
}
