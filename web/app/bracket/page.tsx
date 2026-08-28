"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useData, useTour } from "@/lib/tour";
import { setSearchParam } from "@/lib/url";
import { PageHead, Loading, Reveal, SurfacePill } from "@/components/bits";
import Dropdown, { type DropdownOption } from "@/components/Dropdown";
import BracketTree from "@/components/BracketTree";
import ForecastBracket from "@/components/ForecastBracket";
import { tournamentTier, heat } from "@/lib/ui";
import {
  type BracketEvent,
  type TournamentLite,
  drawSourceLabel,
  resolveEventIndex,
  sectionCount,
  sectionLabels,
  titleContenders,
} from "@/lib/bracket";
import {
  type ScenarioArtifact,
  decodeScenario,
  encodeScenario,
  exactScenario,
} from "@/lib/scenario";

type PlayerRow = { name: string };

export default function Bracket() {
  const { tour } = useTour();
  return (
    <div className="pb-16" data-bracket-lab-contract="actual+forecast+scenario-exact-v1">
      <PageHead
        eyebrow={`${tour.toUpperCase()} · draws`}
        title="Brackets"
        sub="The complete tournament draw, round by round — first-party ATP/WTA when available, with a labeled Wikipedia fallback. Every match carries the model's pre-match win probability; ESPN results advance completed rounds with scores and upset flags."
      />
      {/* useSearchParams (shareable ?e= links) needs a Suspense boundary under static export */}
      <Suspense fallback={<Loading variant="forecast" />}>
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
  const [copied, setCopied] = useState(false);
  const scenarioFile = ev?.scenario?.file ?? ev?.scenarioFile ?? "";
  const scenarioState = useData<ScenarioArtifact>(scenarioFile);
  const requestedMode = sp.get("mode");
  const mode = requestedMode === "forecast" || requestedMode === "scenario" ? requestedMode : "actual";
  const forced = useMemo(() => decodeScenario(sp.get("p")), [sp]);
  const scenarioResult = useMemo(() => {
    const artifact = scenarioState.data;
    if (!artifact) return null;
    return mode === "scenario"
      ? exactScenario(
        artifact.rounds, artifact.players, artifact.matrices.combiner, forced,
        artifact.event.espnId,
      )
      : artifact.base;
  }, [scenarioState.data, mode, forced]);

  useEffect(() => {
    setSection(0);
  }, [idx, tour]);

  // A stale ?e= (event dropped from the feed after a refresh) is stripped so the URL stays
  // shareable and the page falls back to the first (most relevant) event.
  useEffect(() => {
    if (eParam && events.length && !events.some((e) => String(e.espnId ?? "") === eParam
      || e.name.toLowerCase() === eParam.toLowerCase())) {
      router.replace(`${pathname}${setSearchParam(window.location.search, "e", null)}`, { scroll: false });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eParam, events, tour]);

  const options: DropdownOption[] = useMemo(
    () =>
      events.map((e) => ({
        value: String(e.espnId || e.name),
        label: e.name,
        sublabel: `${tournamentTier(e.level, e.name).short} · ${e.status}`,
      })),
    [events],
  );
  const replaceParams = (changes: Record<string, string | null>) => {
    let search = window.location.search;
    for (const [key, value] of Object.entries(changes)) search = setSearchParam(search, key, value);
    router.replace(`${pathname}${search}`, { scroll: false });
  };
  const pick = (eventKey: string) => replaceParams({ e: eventKey, mode: null, p: null });
  const setMode = (next: "actual" | "forecast" | "scenario") =>
    replaceParams({ mode: next === "actual" ? null : next, p: next === "scenario" ? sp.get("p") : null });
  const setForced = (key: string, name: string | null) => {
    const next = { ...forced };
    delete next[key];
    if (name) next[key] = name;
    replaceParams({ mode: "scenario", p: encodeScenario(next) });
  };
  const undoForced = () => {
    const latest = Object.keys(forced).at(-1);
    if (latest) setForced(latest, null);
  };

  if (loading) return <Loading variant="forecast" />;
  if (error || !data)
    return <Empty>Couldn&apos;t load bracket data — it may be refreshing, so try again shortly.</Empty>;
  if (!events.length)
    return (
      <Empty>
        No complete ordered draw is on file right now. Active tournament cards still use
        ESPN&apos;s posted matchups, and this page appears once an ATP/WTA or Wikipedia draw resolves.
      </Empty>
    );
  if (!ev) return <Empty>That event isn&apos;t available — pick another from the list.</Empty>;

  const contenders = titleContenders(tournaments ?? null, ev);
  const labels = sectionLabels(ev.bracketSize);
  const tier = tournamentTier(ev.level, ev.name);
  const canForecast = !!scenarioFile;
  const eventKey = String(ev.espnId || ev.name);

  return (
    <>
      <Reveal>
        <div className="mt-8 grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
          <div>
            <div className="eyebrow mb-2">Tournament</div>
            <Dropdown searchable label="Tournament" value={eventKey} onChange={pick} options={options} />
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

      <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Bracket view">
          {([[
            "actual", "Actual draw",
          ], ["forecast", "Forecast path"], ["scenario", "Scenario"]] as const).map(([value, label]) => (
            <button
              key={value}
              onClick={() => setMode(value)}
              disabled={value !== "actual" && !canForecast}
              aria-pressed={mode === value}
              className="chip transition-colors disabled:cursor-not-allowed disabled:opacity-40"
              style={mode === value ? { background: "var(--color-accent)", color: "var(--color-on-accent)", borderColor: "var(--color-accent)" } : undefined}
            >
              {label}
            </button>
          ))}
        </div>
        {mode === "scenario" && canForecast && (
          <div className="flex items-center gap-1.5">
            <button
              onClick={undoForced}
              disabled={!Object.keys(forced).length}
              className="mono text-[10px] uppercase text-[var(--color-muted)] hover:underline disabled:cursor-not-allowed disabled:opacity-40"
            >
              Undo latest
            </button>
            <button onClick={() => replaceParams({ p: null })} className="mono text-[10px] uppercase text-[var(--color-muted)] hover:underline">
              Reset
            </button>
            <button
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(window.location.href);
                  setCopied(true);
                  window.setTimeout(() => setCopied(false), 1600);
                } catch { setCopied(false); }
              }}
              className="chip"
            >
              {copied ? "Copied" : "Share scenario"}
            </button>
          </div>
        )}
      </div>

      {mode === "actual" && sectionCount(ev.bracketSize) > 1 && (
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
        <div className="panel mt-4 p-2 sm:p-3">
          <div className="panel-inset overflow-hidden p-1 sm:p-2">
            {mode === "actual" ? (
              <BracketTree ev={ev} section={section} tour={tour} roster={roster} />
            ) : scenarioState.loading ? (
              <Loading variant="forecast" />
            ) : scenarioState.error || !scenarioState.data || !scenarioResult ? (
              <div className="mono p-6 text-xs text-[var(--color-faint)]">
                Forecast-path data is unavailable for this settled or unresolved draw.
              </div>
            ) : (
              <ForecastBracket
                artifact={scenarioState.data}
                result={scenarioResult}
                interactive={mode === "scenario"}
                forced={forced}
                onPick={setForced}
                tour={tour}
              />
            )}
          </div>
        </div>
      </Reveal>

      <div className="mono mt-3 text-[10px] leading-relaxed text-[var(--color-faint)]">
        {mode === "actual" ? (
          <>Win % is P(top player). Completed matches show the forecast logged before play;
          &quot;retro&quot; marks a retrospective estimate. Byes and unreleased qualifiers are unpriced.</>
        ) : (
          <>Reach and title odds are exact conditional probabilities through the ordered draw.
          Confirmed results stay fixed; scenario picks describe what-if paths and never enter model evaluation.</>
        )}
        {ev.drawSourceUrl && (
          <>
            {" · "}
            <a href={ev.drawSourceUrl} target="_blank" rel="noopener noreferrer" className="hover:underline">
              {drawSourceLabel(ev.drawSource)}
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
