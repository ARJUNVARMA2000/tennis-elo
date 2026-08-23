"use client";

import { useMemo, useState } from "react";
import { CallCard, Loading, PageHead, Reveal } from "@/components/bits";
import Dropdown from "@/components/Dropdown";
import LiveTicker, { useLiveMatches } from "@/components/LiveTicker";
import PredictionWhy from "@/components/PredictionWhy";
import ForecastTimeline from "@/components/ForecastTimeline";
import { useData, useTour } from "@/lib/tour";
import { excludeLiveMatches, groupByEvent, hasMatchupProfiles, upcomingCard, useUpcomingEvents, worthWatching, type ForecastHistory, type Upcoming } from "@/lib/upcoming";

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
  forecast?: ForecastHistory | null;
};
type Track = { matchForecasts?: { recent?: TrackCall[] } };
const TABS = ["live", "upcoming", "final"] as const;

export default function MatchCenter() {
  const { tour } = useTour();
  const [tab, setTab] = useState<Tab>("live");
  const [event, setEvent] = useState("all");
  const upcomingState = useUpcomingEvents(tab === "upcoming");
  const trackState = useData<Track>("track.json");
  const rosterState = useData<{ name: string }[]>("players.json");
  const live = useLiveMatches(tour);
  const roster = useMemo(
    () => new Set((rosterState.data ?? []).map((player) => player.name)),
    [rosterState.data],
  );
  const upcoming = useMemo(
    () => excludeLiveMatches(upcomingState.data ?? [], live.matches),
    [upcomingState.data, live.matches],
  );
  const finals = useMemo(
    () => trackState.data?.matchForecasts?.recent ?? [],
    [trackState.data],
  );
  const events = useMemo(() => {
    const source = tab === "final" ? finals.map((row) => row.event) : upcoming.map((row) => row.event);
    return [...new Set(source)].sort();
  }, [tab, upcoming, finals]);
  const shownUpcoming = event === "all" ? upcoming : upcoming.filter((row) => row.event === event);
  const watchlist = useMemo(() => worthWatching(shownUpcoming, 5), [shownUpcoming]);
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
    <div
      className="pb-16"
      data-match-center-contract="upcoming-style-links+forecast-history+watch+evidence+live-dedupe-v4"
      data-live-schedule-contract="exact-event-unordered-pair-v1"
    >
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
        {tab === "live" && <LiveTicker live={live} standalone />}
        {tab === "upcoming" && (
          <MatchSection loading={upcomingState.loading} error={upcomingState.error} empty={!shownUpcoming.length}>
            <div className="mt-7 space-y-8">
              {watchlist.length > 0 && <Watchlist matches={watchlist} roster={roster} />}
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
                          <div className="relative">
                            <CallCard
                              tone="projection"
                              {...upcomingCard(match)}
                              matchup={hasMatchupProfiles(match, roster)}
                              profileRoster={roster}
                            />
                          </div>
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
                    <div>
                      <CallCard
                        glow
                        surface={call.surface}
                        meta={`${call.event} · ${call.round} · ${call.date}`}
                        top={{ name: winner, prob: winnerP, won: true }}
                        bottom={{ name: loser, prob: 1 - winnerP, won: false }}
                        note="frozen first-sighting call"
                        verdict={{ label: call.hit ? "called it ✓" : "missed ✗", good: call.hit }}
                        profileRoster={roster}
                      />
                      {call.forecast && (
                        <div className="mx-2 rounded-b-lg border border-t-0 border-[var(--color-line)] px-3 py-2">
                          <ForecastTimeline forecast={call.forecast} player={call.playerA} />
                        </div>
                      )}
                    </div>
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

const WATCH_LABELS = {
  closeness: "Close",
  quality: "Quality",
  styleContrast: "Style",
  stakes: "Stakes",
  titleLeverage: "Title swing",
} as const;

function Watchlist({ matches, roster }: { matches: Upcoming[]; roster: ReadonlySet<string> }) {
  return (
    <section aria-label="Matches worth watching" data-watch-ranking="watch-v1">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="display text-2xl">Matches worth watching</h2>
          <p className="mt-1 text-[11px] text-[var(--color-faint)]">
            Product ranking—not a prediction of entertainment quality. The full schedule remains chronological below.
          </p>
        </div>
        <span className="mono text-[10px] text-[var(--color-faint)]">30 close · 25 quality · 15 each style / stakes / title swing</span>
      </div>
      <div className="grid gap-3 lg:grid-cols-2">
        {matches.map((match) => (
          <article key={`${match.espnId}-${match.round}-${match.playerA}-${match.playerB}`} className="panel p-3">
            <div className="mb-2 flex items-center justify-between gap-3 px-1">
              <span className="eyebrow">#{match.watchRank} to watch</span>
              <span className="mono text-sm text-[var(--color-accent)]">{match.watch?.score.toFixed(1)} / 100</span>
            </div>
            <div className="relative">
              <CallCard
                tone="projection"
                {...upcomingCard(match, { showEvent: true })}
                matchup={hasMatchupProfiles(match, roster)}
                profileRoster={roster}
              />
            </div>
            <div className="mt-2 grid grid-cols-5 gap-1">
              {Object.entries(WATCH_LABELS).map(([key, label]) => {
                const factor = match.watch?.factors?.[key as keyof typeof WATCH_LABELS];
                return (
                  <div key={key} className="min-w-0 rounded border border-[var(--color-line)] px-1 py-1.5 text-center">
                    <div className="mono truncate text-[8px] uppercase text-[var(--color-faint)]">{label}</div>
                    <div className="mono mt-0.5 text-[10px]">{factor?.available ? factor.score.toFixed(0) : "—"}</div>
                  </div>
                );
              })}
            </div>
            <PredictionWhy match={match} />
          </article>
        ))}
      </div>
    </section>
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
