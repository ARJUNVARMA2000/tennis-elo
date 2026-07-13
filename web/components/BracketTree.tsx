"use client";

import Link from "next/link";
import type { Tour } from "@/lib/tour";
import { playerHref, pairHref, withTour } from "@/lib/url";
import {
  type BracketColumn,
  type BracketEvent,
  type BracketMatch,
  finalsColumns,
  isRealSlot,
  sectionColumns,
  sideLabel,
} from "@/lib/bracket";

/** The bracket as a horizontal row of equal-height columns. Because every column shares a
    height and distributes its cards with space-around, a round-N match sits centred between
    its two feeders with no per-card grid math — the classic printed-draw shape falls out. */
export default function BracketTree({
  ev,
  section,
  tour,
  roster,
}: {
  ev: BracketEvent;
  section: number;
  tour: Tour;
  roster: ReadonlySet<string>;
}) {
  const cols: BracketColumn[] = [...sectionColumns(ev, section), ...finalsColumns(ev)];
  return (
    <div className="overflow-x-auto pb-2">
      <div className="flex min-h-[520px] gap-3 sm:gap-4" style={{ minWidth: cols.length * 210 }}>
        {cols.map((col, i) => (
          <div
            key={`${col.round}-${i}`}
            className="flex flex-1 flex-col"
            style={{ minWidth: 190, scrollSnapAlign: "start" }}
          >
            <div
              className="eyebrow mb-2 text-center text-[10px]"
              style={col.finals ? { color: "var(--color-accent)" } : undefined}
            >
              {col.round}
            </div>
            {/* only the cards are distributed, so a round-N match sits centred between its
                two feeders while the round label stays pinned at the top */}
            <div className="flex flex-1 flex-col justify-around gap-2">
              {col.matches.map(({ m, idx }) => (
                <MatchCard key={idx} m={m} roundIndex={col.roundIndex} tour={tour} roster={roster} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function MatchCard({
  m,
  roundIndex,
  tour,
  roster,
}: {
  m: BracketMatch;
  roundIndex: number;
  tour: Tour;
  roster: ReadonlySet<string>;
}) {
  const pending = m.winner === null;
  const bothReal = isRealSlot(m.a) && isRealSlot(m.b);
  // pending, both players known & rated -> the whole card drills into the style matchup
  const drill =
    pending && bothReal && roster.has(m.a as string) && roster.has(m.b as string)
      ? withTour(pairHref("/style/", m.a as string, m.b as string, tour), tour)
      : null;

  return (
    <div className="relative">
      <div className="panel px-2.5 py-1.5">
        <Side
          name={m.a}
          seed={m.seedA}
          roundIndex={roundIndex}
          won={m.winner === "a"}
          lost={m.winner === "b"}
          tour={tour}
          roster={roster}
        />
        <div className="my-1 flex items-center gap-2">
          <div className="bartrack relative h-1 flex-1">
            {m.p != null && (
              <div
                className="absolute inset-y-0 left-0"
                style={{ width: `${Math.round(m.p * 100)}%`, background: "var(--color-accent)" }}
              />
            )}
          </div>
          {m.p != null ? (
            <span className="mono text-[10px] text-[var(--color-muted)]">
              {Math.round(m.p * 100)}<span className="text-[var(--color-faint)]">/</span>
              {100 - Math.round(m.p * 100)}
            </span>
          ) : (
            <span className="mono text-[10px] text-[var(--color-faint)]">—</span>
          )}
        </div>
        <Side
          name={m.b}
          seed={m.seedB}
          roundIndex={roundIndex}
          won={m.winner === "b"}
          lost={m.winner === "a"}
          tour={tour}
          roster={roster}
        />
        {(m.score || m.upset || (m.probSource === "model" && !pending)) && (
          <div className="mt-1 flex items-center gap-1.5">
            {m.score && <span className="mono text-[10px] text-[var(--color-faint)]">{m.score}</span>}
            {m.upset && (
              <span
                className="mono rounded-sm px-1 text-[9px] uppercase"
                style={{ color: "var(--color-loss)", border: "1px solid var(--color-loss)" }}
              >
                upset
              </span>
            )}
            {m.probSource === "model" && !pending && (
              <span
                className="mono text-[9px] text-[var(--color-faint)]"
                title="Retrospective estimate — no pre-match forecast was logged for this match"
              >
                retro
              </span>
            )}
          </div>
        )}
      </div>
      {drill && (
        <Link
          href={drill}
          aria-label={`Compare ${m.a} and ${m.b}`}
          className="absolute inset-0 z-10 rounded-[inherit]"
        />
      )}
    </div>
  );
}

function Side({
  name,
  seed,
  roundIndex,
  won,
  lost,
  tour,
  roster,
}: {
  name: string | null;
  seed: number | null;
  roundIndex: number;
  won: boolean;
  lost: boolean;
  tour: Tour;
  roster: ReadonlySet<string>;
}) {
  const label = sideLabel(name, roundIndex);
  const real = isRealSlot(name);
  const linked = real && roster.has(name as string);
  const color = won ? "var(--color-text)" : lost ? "var(--color-faint)" : "var(--color-muted)";

  return (
    <div className="flex items-center gap-1.5 leading-tight">
      {won && (
        <span className="live-dot inline-block h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: "var(--color-win)" }} />
      )}
      {seed != null && <span className="mono text-[9px] text-[var(--color-faint)]">{seed}</span>}
      {linked ? (
        <Link
          href={withTour(playerHref(name as string, tour), tour)}
          className="relative z-20 truncate text-xs hover:underline"
          style={{ color }}
        >
          {label}
        </Link>
      ) : (
        <span className={`truncate text-xs ${real ? "" : "italic"}`} style={{ color: real ? color : "var(--color-faint)" }}>
          {label}
        </span>
      )}
    </div>
  );
}
