"use client";

import { useMemo, useState } from "react";
import { CallCard, Loading, PageHead, Reveal } from "@/components/bits";
import Dropdown from "@/components/Dropdown";
import LiveTicker from "@/components/LiveTicker";
import PredictionWhy from "@/components/PredictionWhy";
import { useData, useTour } from "@/lib/tour";
import { groupByEvent, upcomingCard, type Upcoming } from "@/lib/upcoming";

type Tab = "live" | "upcoming" | "final";
type TrackCall = {
  date: string;
  event: string;
  round: string;
  surface: string;
  playerA: string;
  playerB: string;
  p: number;
  actualWinner: string;
  hit: boolean;
};
type Track = { matchForecasts?: { recent?: TrackCall[] } };
const TABS = ["live", "upcoming", "final"] as const;

export default function MatchCenter() {
  const { tour } = useTour();
  const upcomingState = useData<Upcoming[]>("upcoming.json");
  const trackState = useData<Track>("track.json");
  const rosterState = useData<{ name: string }[]>("players.json");
  const [tab, setTab] = useState<Tab>("live");
  const [event, setEvent] = useState("all");
  const roster = useMemo(
    () => new Set((rosterState.data ?? []).map((player) => player.name)),
    [rosterState.data],
  );
  const upcoming = useMemo(() => upcomingState.data ?? [], [upcomingState.data]);
  const finals = useMemo(
    () => trackState.data?.matchForecasts?.recent ?? [],
    [trackState.data],
  );
  const events = useMemo(() => {
    const source = tab === "final" ? finals.map((row) => row.event) : upcoming.map((row) => row.event);
    return [...new Set(source)].sort();
  }, [tab, upcoming, finals]);
  const shownUpcoming = event === "all" ? upcoming : upcoming.filter((row) => row.event === event);
  const shownFinals = event === "all" ? finals : finals.filter((row) => row.event === event);
  const switchTab = (next: Tab) => {
    setTab(next);
    setEvent("all");
  };
  const onTabKeyDown = (keyboardEvent: React.KeyboardEvent<HTMLButtonElement>) => {
    if (keyboardEvent.key !== "ArrowLeft" && keyboardEvent.key !== "ArrowRight") return;
    keyboardEvent.preventDefault();
    const current = TABS.indexOf(tab);
    const delta = keyboardEvent.key === "ArrowRight" ? 1 : -1;
    const next = TABS[(current + delta + TABS.length) % TABS.length];
    switchTab(next);
    requestAnimationFrame(() => document.getElementById(`match-tab-${next}`)?.focus());
  };

  return (
    <div className="pb-16">
      <PageHead
        eyebrow={`${tour.toUpperCase()} · match center`}
        title="Matches"
        sub="One board for courts in play, scheduled model calls, and completed point-in-time forecasts."
      />
      <div className="mt-7 flex flex-wrap items-center gap-2">
        <div role="tablist" aria-label="Match state" className="flex rounded-lg border border-[var(--color-line)] p-1">
          {TABS.map((value) => (
            <button
              key={value}
              id={`match-tab-${value}`}
              type="button"
              role="tab"
              aria-selected={tab === value}
              aria-controls="match-tabpanel"
              tabIndex={tab === value ? 0 : -1}
              onClick={() => switchTab(value)}
              onKeyDown={onTabKeyDown}
              className="mono rounded-md px-4 py-2 text-[11px] uppercase tracking-wider"
              style={{
                color: tab === value ? "var(--color-on-accent)" : "var(--color-muted)",
                background: tab === value ? "var(--color-accent)" : "transparent",
              }}
            >
              {value}
            </button>
          ))}
        </div>
        {tab !== "live" && events.length > 1 && (
          <Dropdown
            compact
            searchable
            align="right"
            label="Tournament filter"
            value={event}
            onChange={setEvent}
            options={[
              { value: "all", label: "All events" },
              ...events.map((name) => ({ value: name, label: name })),
            ]}
            className="ml-auto w-full sm:w-64"
          />
        )}
      </div>

      <div id="match-tabpanel" role="tabpanel" aria-labelledby={`match-tab-${tab}`}>
        {tab === "live" && <LiveTicker standalone />}
        {tab === "upcoming" && (
          <MatchSection loading={upcomingState.loading} error={upcomingState.error} empty={!shownUpcoming.length}>
            <div className="mt-7 space-y-8">
              {groupByEvent(shownUpcoming).map((group) => (
                <section key={group.event}>
                  <div className="mb-3 flex items-baseline gap-3">
                    <h2 className="display text-xl">{group.event}</h2>
                    <span className="mono text-[11px] text-[var(--color-faint)]">{group.matches.length} scheduled</span>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    {group.matches.map((match, index) => (
                      <Reveal key={`${match.playerA}-${match.playerB}-${index}`} delay={Math.min(index * 0.02, 0.16)}>
                        <div>
                          <CallCard tone="projection" {...upcomingCard(match)} profileRoster={roster} />
                          <PredictionWhy match={match} />
                        </div>
                      </Reveal>
                    ))}
                  </div>
                </section>
              ))}
            </div>
          </MatchSection>
        )}
        {tab === "final" && (
          <MatchSection loading={trackState.loading} error={trackState.error} empty={!shownFinals.length}>
            <div className="mt-7 grid gap-3 sm:grid-cols-2">
              {shownFinals.map((call, index) => {
                const aWon = call.actualWinner === call.playerA;
                const winner = aWon ? call.playerA : call.playerB;
                const loser = aWon ? call.playerB : call.playerA;
                const winnerP = aWon ? call.p : 1 - call.p;
                return (
                  <Reveal key={`${call.date}-${call.playerA}-${call.playerB}-${index}`} delay={Math.min(index * 0.015, 0.18)}>
                    <CallCard
                      glow
                      surface={call.surface}
                      meta={`${call.event} · ${call.round} · ${call.date}`}
                      top={{ name: winner, prob: winnerP, won: true }}
                      bottom={{ name: loser, prob: 1 - winnerP, won: false }}
                      note="frozen pre-match call"
                      verdict={{ label: call.hit ? "called it ✓" : "missed ✗", good: call.hit }}
                      profileRoster={roster}
                    />
                  </Reveal>
                );
              })}
            </div>
          </MatchSection>
        )}
      </div>
    </div>
  );
}

function MatchSection({
  loading,
  error,
  empty,
  children,
}: {
  loading: boolean;
  error: boolean;
  empty: boolean;
  children: React.ReactNode;
}) {
  if (loading) return <Loading variant="cards" />;
  if (error) return <div className="panel-inset mt-7 p-6 text-sm text-[var(--color-muted)]">This match feed is temporarily unavailable.</div>;
  if (empty) return <div className="panel-inset mt-7 p-6 text-sm text-[var(--color-muted)]">No matches in this view right now.</div>;
  return children;
}
