"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useData, useTour } from "@/lib/tour";
import { setSearchParam } from "@/lib/url";
import { PageHead, Loading, Reveal, SurfacePill } from "@/components/bits";
import Dropdown, { type DropdownOption } from "@/components/Dropdown";
import BracketTree from "@/components/BracketTree";
import { tournamentTier, heat } from "@/lib/ui";
import {
  type BracketEvent,
  type TournamentLite,
  resolveEventIndex,
  sectionCount,
  sectionLabels,
  titleContenders,
} from "@/lib/bracket";

type PlayerRow = { name: string };

export default function Bracket() {
  const { tour } = useTour();
  return (
    <div className="pb-16">
      <PageHead
        eyebrow={`${tour.toUpperCase()} · draws`}
        title="Brackets"
        sub="The actual tournament draw, round by round. Every match carries the model's pre-match win probability; completed rounds show the real result, scores and upset flags."
      />
      {/* useSearchParams (shareable ?e= links) needs a Suspense boundary under static export */}
      <Suspense fallback={<Loading />}>
        <BracketInner />
      </Suspense>
    </div>
  );
}

function BracketInner() {
  const { tour } = useTour();
  const { data, loading, error } = useData<BracketEvent[]>("brackets.json");
  const { data: tournaments } = useData<TournamentLite[]>("tournaments.json");
  const { data: players } = useData<PlayerRow[]>("players.json");
  const router = useRouter();
  const pathname = usePathname();
  const sp = useSearchParams();
  const eParam = sp.get("e");

  const events = useMemo(() => data ?? [], [data]);
  const roster = useMemo(() => new Set((players ?? []).map((p) => p.name)), [players]);
  const idx = resolveEventIndex(events, eParam);
  const ev = events[idx];
  const [section, setSection] = useState(0);

  useEffect(() => {
    setSection(0);
  }, [idx, tour]);

  // A stale ?e= (event dropped from the feed after a refresh) is stripped so the URL stays
  // shareable and the page falls back to the first (most relevant) event.
  useEffect(() => {
    if (eParam && events.length && !events.some((e) => e.name.toLowerCase() === eParam.toLowerCase())) {
      router.replace(`${pathname}${setSearchParam(window.location.search, "e", null)}`, { scroll: false });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eParam, events, tour]);

  const options: DropdownOption[] = useMemo(
    () =>
      events.map((e) => ({
        value: e.name,
        label: e.name,
        sublabel: `${tournamentTier(e.level, e.name).short} · ${e.status}`,
      })),
    [events],
  );
  const pick = (name: string) =>
    router.replace(`${pathname}${setSearchParam(window.location.search, "e", name)}`, { scroll: false });

  if (loading) return <Loading />;
  if (error || !data)
    return <Empty>Couldn&apos;t load bracket data — it may be refreshing, so try again shortly.</Empty>;
  if (!events.length)
    return (
      <Empty>
        No official draw is on file right now — brackets appear once an event&apos;s draw is released.
      </Empty>
    );
  if (!ev) return <Empty>That event isn&apos;t available — pick another from the list.</Empty>;

  const contenders = titleContenders(tournaments ?? null, ev.name);
  const labels = sectionLabels(ev.bracketSize);
  const tier = tournamentTier(ev.level, ev.name);

  return (
    <>
      <Reveal>
        <div className="mt-8 grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
          <div>
            <div className="eyebrow mb-2">Tournament</div>
            <Dropdown searchable label="Tournament" value={ev.name} onChange={pick} options={options} />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <SurfacePill s={ev.surface} />
            <span className="chip">{ev.bestOf === 5 ? "Best of 5" : "Best of 3"}</span>
            <span className="chip">{ev.drawSize} draw</span>
          </div>
        </div>
      </Reveal>

      <Reveal delay={0.05}>
        <div className="panel mt-4 flex flex-wrap items-center justify-between gap-3 p-4">
          <div>
            <div className="eyebrow">{tier.full}</div>
            <div className="mono mt-0.5 text-xs text-[var(--color-faint)]">
              {ev.start} — {ev.end}
            </div>
          </div>
          {ev.status === "completed" && ev.champion ? (
            <div className="text-right">
              <div className="eyebrow text-[10px]">Champion</div>
              <div className="text-sm" style={{ color: "var(--color-champ)" }}>{ev.champion}</div>
            </div>
          ) : contenders.length ? (
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="eyebrow text-[10px]">Title odds</span>
              {contenders.map((c) => (
                <span
                  key={c.name}
                  className="mono rounded-sm px-1.5 py-0.5 text-[11px]"
                  style={{ background: heat(c.p) }}
                >
                  {c.name.split(" ").slice(-1)[0]} {Math.round(c.p * 100)}%
                </span>
              ))}
            </div>
          ) : null}
        </div>
      </Reveal>

      {sectionCount(ev.bracketSize) > 1 && (
        <div className="mt-4 flex flex-wrap gap-1.5">
          {labels.map((lab, i) => (
            <button
              key={lab}
              onClick={() => setSection(i)}
              aria-pressed={section === i}
              className="chip transition-colors"
              style={
                section === i
                  ? { background: "var(--color-accent)", color: "var(--color-on-accent)", borderColor: "var(--color-accent)" }
                  : undefined
              }
            >
              {lab}
            </button>
          ))}
        </div>
      )}

      <Reveal delay={0.1}>
        <div className="panel mt-4 p-3 sm:p-4">
          <BracketTree ev={ev} section={section} tour={tour} roster={roster} />
        </div>
      </Reveal>

      <div className="mono mt-3 text-[10px] leading-relaxed text-[var(--color-faint)]">
        Win % is P(top player). Completed matches show the forecast logged before play;
        &quot;retro&quot; marks a retrospective estimate. Byes and unreleased qualifiers are unpriced.
        {ev.wikiUrl && (
          <>
            {" · "}
            <a href={ev.wikiUrl} target="_blank" rel="noopener noreferrer" className="hover:underline">
              draw source
            </a>
          </>
        )}
      </div>
    </>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return <div className="mono mt-10 text-sm text-[var(--color-faint)]">{children}</div>;
}
