"use client";

import { useEffect, useState } from "react";
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
  type Matrix,
  type PlayerRow,
  type RawLiveMatch,
  type TournamentInfo,
} from "@/lib/live";

const BASE = process.env.NEXT_PUBLIC_BASE_PATH || "";
const POLL_MS = 60_000;

/** "Live now" strip — real ESPN scores polled from the browser every minute,
    paired with the model's win probability. Hides itself entirely when there
    are no live matches (or ESPN is unreachable). */
export default function LiveTicker() {
  const { tour } = useTour();
  const { data: players } = useData<PlayerRow[]>("players.json");
  const { data: tournaments } = useData<TournamentInfo[]>("tournaments.json");
  const [matches, setMatches] = useState<RawLiveMatch[]>([]);
  const [matrix, setMatrix] = useState<{ tour: string; m: Matrix } | null>(null);

  // poll ESPN while the tab is visible; abort in-flight work on unmount/switch
  useEffect(() => {
    let alive = true;
    let ctrl: AbortController | null = null;
    const poll = async (force = false) => {
      if (!force && document.visibilityState === "hidden") return;
      ctrl?.abort();
      ctrl = new AbortController();
      try {
        const m = await fetchLiveMatches(tour, ctrl.signal);
        if (alive) setMatches(m);
      } catch {
        /* keep last good data; first failure leaves the strip hidden */
      }
    };
    setMatches([]);
    poll(true); // first fetch always runs (later polls pause while hidden)
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

  // the pairwise matrix is ~1.5 MB — fetch it only once live matches exist
  useEffect(() => {
    if (!matches.length || matrix?.tour === tour) return;
    let alive = true;
    fetch(`${BASE}/data/${tour}/matrix.json`)
      .then((r) => (r.ok ? r.json() : null))
      .then((m) => alive && m && setMatrix({ tour, m }))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [matches.length, tour, matrix?.tour]);

  if (!matches.length) return null;
  const mtx = matrix?.tour === tour ? matrix.m : null;

  return (
    <motion.section aria-label="Live matches" variants={stagger(0.06)} initial="hidden" animate="show" className="mt-8">
      <div className="mb-2.5 flex items-center gap-2">
        <span className="live-dot inline-block h-1.5 w-1.5 rounded-full bg-[var(--color-accent)]" />
        <span className="eyebrow !text-[var(--color-text)]">Live now</span>
        <span className="text-[11px] text-[var(--color-faint)]">
          ESPN scores · model win odds · refreshes every minute
        </span>
      </div>
      <ul role="list" className="flex gap-3 overflow-x-auto pb-2">
        {matches.map((m) => (
          <LiveCard key={m.id} m={m} players={players} tournaments={tournaments} matrix={mtx} tour={tour} />
        ))}
      </ul>
    </motion.section>
  );
}

function LiveCard({
  m,
  players,
  tournaments,
  matrix,
  tour,
}: {
  m: RawLiveMatch;
  players: PlayerRow[] | null;
  tournaments: TournamentInfo[] | null;
  matrix: Matrix | null;
  tour: Tour;
}) {
  const { surface, bestOf } = matchContext(m.event, tournaments);
  const { p } = winProb(m.a, m.b, surface, bestOf, players, matrix, tour);
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
            <span className="sr-only">win probability </span>
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
      className={`panel relative min-w-[280px] shrink-0 p-3 ${matchupHref ? "panel-link" : ""}`}
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
