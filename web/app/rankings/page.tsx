"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { useData, useTour } from "@/lib/tour";
import {
  eloKey,
  surfaceColor,
  SURFACES,
  pct,
  blendedElo,
  passesAgeFilter,
  parseAgeFilter,
  filterRankingRows,
  sortRankingRows,
  AGE_MIN,
  AGE_MAX,
  type RankingSortKey,
  type SortDirection,
} from "@/lib/ui";
import { playerHref } from "@/lib/url";
import { PageHead, Loading, SurfacePill, Reveal, StatCard } from "@/components/bits";
import Dropdown from "@/components/Dropdown";

const AGE_MODES = [
  { value: "all", label: "All ages" },
  { value: "under", label: "Under" },
  { value: "over", label: "Over" },
];

type Player = {
  name: string; eloRank: number; elo: number; eloHard: number; eloClay: number; eloGrass: number;
  servePct: number; returnPct: number; rankPoints: number | null; matches: number; hand: string | null;
  age: number | null; country: string | null;
  liveRank?: number | null; liveRankDelta?: number | null;
};

function DeltaBadge({ d }: { d: number | null | undefined }) {
  if (d == null || d === 0) return null;
  const up = d > 0;
  return (
    <span
      className="mono ml-1 text-[10px]"
      style={{ color: up ? "var(--color-win)" : "var(--color-loss)" }}
      title="vs last official ranking"
    >
      {up ? "▲" : "▼"}{Math.abs(d)}
    </span>
  );
}

export default function Rankings() {
  const { tour } = useTour();
  const { data, loading, error } = useData<Player[]>("players.json");
  const [surface, setSurface] = useState<string>("Overall");
  const [ageMode, setAgeMode] = useState("all");
  const [ageValue, setAgeValue] = useState("23");   // persists across mode toggles
  const [query, setQuery] = useState("");
  const [sortKey, setSortKey] = useState<RankingSortKey>("rating");
  const [sortDir, setSortDir] = useState<SortDirection>("desc");
  const ageFilter = useMemo(() => parseAgeFilter(ageMode, ageValue), [ageMode, ageValue]);

  const boardRows = useMemo(() => {
    if (!data) return [];
    // Overall = raw overall Elo; a surface = the model's surface-BLENDED rating (what it predicts with),
    // not the heavily-shrunk raw surface Elo. Age-filter, then rank the top 100 by the chosen rating.
    const rate = (p: Player) =>
      surface === "Overall" ? p.elo : blendedElo(p.elo, (p as any)[eloKey(surface)] as number, tour);
    return data
      .filter((p) => passesAgeFilter(p.age, ageFilter))
      .map((p) => ({ ...p, rate: rate(p) }))
      .sort((a, b) => b.rate - a.rate)
      .slice(0, 100)
      .map((p, i) => ({ ...p, boardRank: i + 1 }));
  }, [data, surface, ageFilter, tour]);
  const rows = useMemo(
    () => sortRankingRows(filterRankingRows(boardRows, query), sortKey, sortDir),
    [boardRows, query, sortKey, sortDir],
  );

  const top = boardRows[0];
  const pickSort = (key: RankingSortKey) => {
    if (sortKey === key) setSortDir((dir) => (dir === "desc" ? "asc" : "desc"));
    else {
      setSortKey(key);
      setSortDir(key === "liveRank" ? "asc" : "desc");
    }
  };
  const pickSurface = (value: string) => {
    setSurface(value);
    setSortKey("rating");
    setSortDir("desc");
  };
  const selectMetric = (key: RankingSortKey) => {
    setSortKey(key);
    setSortDir(key === "liveRank" ? "asc" : "desc");
  };
  const metricOptions = [
    { value: "rating", label: surface === "Overall" ? "Elo rating" : `${surface} rating` },
    { value: "liveRank", label: "Live rank" },
    { value: "serve", label: "Serve points won" },
    { value: "return", label: "Return points won" },
  ];

  return (
    <div className="pb-16">
      <PageHead
        eyebrow={`${tour.toUpperCase()} · Elo ratings`}
        title="The Board"
        sub="Overall Elo, or each player's surface-blended rating — the number the model actually predicts with (raw surface Elo is heavily shrunk and misleads). Switch surfaces to re-rank; serve and return come from the opponent-adjusted point model."
      />

      {loading && <Loading variant="table" />}

      {error && !data && (
        <p className="mt-8 text-sm text-[var(--color-muted)]">Data unavailable — try again shortly.</p>
      )}

      {top && (
        <Reveal delay={0.05}>
          <div className="mt-8 flex flex-wrap items-center gap-x-10 gap-y-5">
            <div>
              <div className="eyebrow">World #1 · {surface}</div>
              <div className="display mt-2 text-3xl sm:text-4xl">{top.name}</div>
            </div>
            <div className="grid min-w-[260px] flex-1 grid-cols-2 gap-3 sm:grid-cols-4">
              <StatCard label={surface === "Overall" ? "Elo" : "Blended"} value={top.rate} />
              <StatCard label="Serve" value={top.servePct * 100} decimals={1} suffix="%" />
              <StatCard label="Return" value={top.returnPct * 100} decimals={1} suffix="%" />
              <StatCard label="Matches" value={top.matches} />
            </div>
          </div>
        </Reveal>
      )}

      <div className="mt-8 mb-4 space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <SurfacePill s="Overall" active={surface === "Overall"} onClick={() => pickSurface("Overall")} />
          {SURFACES.map((s) => (
            <SurfacePill key={s} s={s} active={surface === s} onClick={() => pickSurface(s)} />
          ))}
          <div className="ml-auto flex items-center gap-2">
            <Dropdown
              compact
              align="right"
              label="Age filter"
              value={ageMode}
              onChange={setAgeMode}
              options={AGE_MODES}
            />
            {ageMode !== "all" && (
              <input
                type="number"
                inputMode="numeric"
                min={AGE_MIN}
                max={AGE_MAX}
                step={1}
                value={ageValue}
                onChange={(e) => setAgeValue(e.target.value)}
                onBlur={() => {
                  const f = parseAgeFilter(ageMode, ageValue);
                  if (f) setAgeValue(String(f.value));   // snap display to the clamped parse
                }}
                aria-label={`Age threshold (${ageMode === "under" ? "younger than" : "older than"})`}
                className="mono w-16 rounded-md border border-[var(--color-line)] bg-[var(--color-panel2)] px-3 py-1.5 text-right text-[12px] text-[var(--color-text)] transition-colors focus:border-[var(--color-accent)] focus:outline-none"
              />
            )}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="flex min-w-0 flex-1 items-center gap-2 rounded-md border border-[var(--color-line)] bg-[var(--color-panel2)] px-3 transition-colors focus-within:border-[var(--color-accent)] sm:max-w-sm">
            <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.5" className="shrink-0 text-[var(--color-faint)]" aria-hidden="true">
              <circle cx="7" cy="7" r="4.5" /><path d="m10.5 10.5 3 3" strokeLinecap="round" />
            </svg>
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search the top 100…"
              aria-label="Search rankings"
              className="h-9 min-w-0 flex-1 bg-transparent text-[13px] text-[var(--color-text)] outline-none placeholder:text-[var(--color-faint)]"
            />
          </label>
          <Dropdown
            compact
            align="right"
            label="Rankings metric"
            value={sortKey}
            onChange={(value) => selectMetric(value as RankingSortKey)}
            options={metricOptions}
            className="ml-auto w-44 sm:hidden"
          />
          <span className="mono hidden text-[10px] text-[var(--color-faint)] sm:inline">{rows.length} players</span>
        </div>
      </div>

      <div className="panel data-scroll">
        <table className="w-full border-collapse text-[13px] sm:min-w-[900px]">
          <thead>
            <tr className="mono text-[10px] uppercase tracking-wider text-[var(--color-faint)]">
              <th className="px-3 py-3 text-right font-normal">#</th>
              <th className="px-3 py-3 text-left font-normal">Player</th>
              <th className="hidden px-3 py-3 text-left font-normal sm:table-cell">Country</th>
              <th className="hidden px-3 py-3 text-right font-normal sm:table-cell">Age</th>
              <th className="px-3 py-3 text-right font-normal sm:hidden">{metricOptions.find((option) => option.value === sortKey)?.label}</th>
              <SortHead label={surface === "Overall" ? "Elo" : "Blended"} sortKey="rating" active={sortKey} dir={sortDir} onSort={pickSort} className="hidden sm:table-cell" />
              <SortHead label="Live rank" sortKey="liveRank" active={sortKey} dir={sortDir} onSort={pickSort} className="hidden sm:table-cell" />
              <th className="hidden px-3 py-3 text-right font-normal sm:table-cell" style={{ color: surfaceColor("Hard") }}>Hard</th>
              <th className="hidden px-3 py-3 text-right font-normal sm:table-cell" style={{ color: surfaceColor("Clay") }}>Clay</th>
              <th className="hidden px-3 py-3 text-right font-normal sm:table-cell" style={{ color: surfaceColor("Grass") }}>Grass</th>
              <SortHead label="Serve" sortKey="serve" active={sortKey} dir={sortDir} onSort={pickSort} className="hidden sm:table-cell" />
              <SortHead label="Return" sortKey="return" active={sortKey} dir={sortDir} onSort={pickSort} className="hidden md:table-cell" />
            </tr>
          </thead>
          <tbody>
            {rows.map((p, i) => (
              <motion.tr
                key={p.name}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.35, delay: Math.min(i * 0.02, 0.3) }}
                className="row-glow border-t border-[var(--color-line)]"
              >
                <td className="mono px-3 py-2.5 text-right text-[11px] text-[var(--color-faint)]">{p.boardRank}</td>
                <td className="px-3 py-2.5 whitespace-nowrap text-[var(--color-text)]">
                  <Link href={playerHref(p.name, tour)} className="transition-colors hover:text-[var(--color-accent)] hover:underline">
                    {p.name}
                  </Link>
                </td>
                <td className="mono hidden px-3 py-2.5 text-[11px] text-[var(--color-muted)] sm:table-cell">{p.country ?? "—"}</td>
                <td className="mono hidden px-3 py-2.5 text-right text-[var(--color-muted)] sm:table-cell">{p.age ?? "—"}</td>
                <td className="mono px-3 py-2.5 text-right font-semibold text-[var(--color-text)] sm:hidden">
                  <MobileMetric player={p} metric={sortKey} />
                </td>
                <td className="mono hidden px-3 py-2.5 text-right font-semibold text-[var(--color-text)] sm:table-cell">
                  {p.rate}
                </td>
                <td className="mono hidden px-3 py-2.5 whitespace-nowrap text-right text-[var(--color-muted)] sm:table-cell">
                  {p.liveRank != null ? <>#{p.liveRank}<DeltaBadge d={p.liveRankDelta} /></> : "—"}
                </td>
                <td className="mono hidden px-3 py-2.5 text-right text-[var(--color-muted)] sm:table-cell">{blendedElo(p.elo, p.eloHard, tour)}</td>
                <td className="mono hidden px-3 py-2.5 text-right text-[var(--color-muted)] sm:table-cell">{blendedElo(p.elo, p.eloClay, tour)}</td>
                <td className="mono hidden px-3 py-2.5 text-right text-[var(--color-muted)] sm:table-cell">{blendedElo(p.elo, p.eloGrass, tour)}</td>
                <td className="mono hidden px-3 py-2.5 text-right text-[var(--color-muted)] sm:table-cell">{pct(p.servePct, 0)}</td>
                <td className="mono hidden px-3 py-2.5 text-right text-[var(--color-muted)] md:table-cell">{pct(p.returnPct, 0)}</td>
              </motion.tr>
            ))}
            {rows.length === 0 && (
              <tr><td colSpan={11} className="px-4 py-10 text-center text-sm text-[var(--color-muted)]">No ranked player matches “{query}”.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {boardRows.some((p) => p.liveRank != null) && (
        <p className="mono mt-3 text-[11px] text-[var(--color-faint)]">
          Official live rankings via{" "}
          <a
            href={`https://live-tennis.eu/en/${tour}-live-ranking`}
            target="_blank"
            rel="noopener noreferrer"
            className="underline decoration-[var(--color-line)] underline-offset-2 hover:text-[var(--color-muted)]"
          >
            live-tennis.eu
          </a>
          {" "}— movement vs the last official release, refreshed hourly.
        </p>
      )}
    </div>
  );
}

function SortHead({
  label,
  sortKey,
  active,
  dir,
  onSort,
  className = "",
}: {
  label: string;
  sortKey: RankingSortKey;
  active: RankingSortKey;
  dir: SortDirection;
  onSort: (key: RankingSortKey) => void;
  className?: string;
}) {
  const selected = active === sortKey;
  return (
    <th className={`px-3 py-3 text-right font-normal ${className}`}>
      <button
        type="button"
        onClick={() => onSort(sortKey)}
        aria-label={`Sort by ${label}`}
        className="ml-auto inline-flex items-center gap-1 transition-colors hover:text-[var(--color-text)]"
        style={{ color: selected ? "var(--color-text)" : undefined }}
      >
        {label}<span className="w-2 text-[8px]">{selected ? (dir === "desc" ? "▼" : "▲") : ""}</span>
      </button>
    </th>
  );
}

function MobileMetric({ player, metric }: { player: Player & { rate: number }; metric: RankingSortKey }) {
  if (metric === "liveRank") return player.liveRank != null ? <>#{player.liveRank}<DeltaBadge d={player.liveRankDelta} /></> : <>—</>;
  if (metric === "serve") return <>{pct(player.servePct, 0)}</>;
  if (metric === "return") return <>{pct(player.returnPct, 0)}</>;
  return <>{player.rate}</>;
}
