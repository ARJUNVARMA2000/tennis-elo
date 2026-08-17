"use client";

import { Suspense, useMemo } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { useData, useTour } from "@/lib/tour";
import { pct, RADAR_AXES, surfaceColor, SURFACES, STYLE_LABEL } from "@/lib/ui";
import {
  buildRadarScalers,
  profileRadarSeries,
  resolveProfileSelection,
  type ProfileDetail,
  type ProfileIndex,
  type RadarProfile,
} from "@/lib/profile";
import { playerHref, setSearchParam } from "@/lib/url";
import { PageHead, Loading, Reveal, Spark, AnimatedNumber, Radar } from "@/components/bits";
import Dropdown, { type DropdownOption } from "@/components/Dropdown";
import { stagger, fadeUp } from "@/lib/motion";

type Profile = RadarProfile & {
  name: string; elo: number; eloHard: number; eloClay: number; eloGrass: number; eloRank?: number;
  servePct: number; returnPct: number; rankPoints: number | null; matches: number; hand: string | null;
  history: [string, number][];
  recent: { date: string; opp: string; surface: string; won: boolean; score: string; event: string }[];
  h2h: { opp: string; w: number; l: number }[];
};

export default function Players() {
  const { tour } = useTour();
  return (
    <div className="pb-16" data-profile-contract="fail-closed-links+single-radar+mobile-contained-v2">
      <PageHead eyebrow={`${tour.toUpperCase()} · player dossier`} title="Profiles" />
      {/* useSearchParams (deep links) requires its own Suspense boundary under static export */}
      <Suspense fallback={<Loading />}>
        <PlayersInner />
      </Suspense>
    </div>
  );
}

function PlayersInner() {
  const { tour } = useTour();
  const { data: index, loading: indexLoading } = useData<ProfileIndex>("profile-index.json");
  const { data: roster, loading: rosterLoading } = useData<Array<{
    name: string; elo: number; eloHard: number; eloClay: number; eloGrass: number;
    eloRank?: number; servePct: number; returnPct: number; rankPoints: number | null;
    matches: number; hand: string | null;
  }>>("players.json");
  const router = useRouter();
  const pathname = usePathname();
  const urlName = useSearchParams().get("p");
  const summaries = useMemo(() => Object.fromEntries(
    (index?.profiles ?? []).map((profile) => [profile.name, profile]),
  ), [index]);
  const names = useMemo(() => (index?.profiles ?? []).map((profile) => profile.name), [index]);
  const options: DropdownOption[] = useMemo(
    () =>
      names.map((n) => ({
        value: n,
        label: n,
        sublabel: summaries[n]?.eloRank != null ? `#${summaries[n].eloRank}` : undefined,
      })),
    [names, summaries],
  );
  const sel = resolveProfileSelection(names, urlName, "");
  const selectedSummary = summaries[sel];
  const { data: detail, loading: detailLoading } = useData<ProfileDetail>(selectedSummary?.file ?? "");

  // URL is the source of truth for the selection. An explicit unknown ?p= is an
  // honest not-found state; only the bare /player page defaults to the top player.
  const notFound = !!urlName && names.length > 0 && !names.includes(urlName);
  const current = roster?.find((player) => player.name === sel);
  const p = useMemo(
    () => selectedSummary && detail?.name === sel && current
      ? ({ ...selectedSummary, ...detail, ...current } as Profile)
      : null,
    [selectedSummary, detail, sel, current],
  );
  const loading = indexLoading || rosterLoading || (!!selectedSummary && detailLoading);
  const profileRoster = useMemo(() => new Set(names), [names]);
  const radarScalers = useMemo(
    () => buildRadarScalers(index?.profiles ?? []),
    [index],
  );
  const radarSeries = useMemo(
    () => p ? profileRadarSeries(p, radarScalers, "var(--color-accent)") : [],
    [p, radarScalers],
  );

  const pick = (n: string) => {
    router.replace(`${pathname}${setSearchParam(window.location.search, "p", n)}`, { scroll: false });
  };
  const opp = (name: string) => profileRoster.has(name) ? (
    <Link href={playerHref(name, tour)} className="transition-colors hover:text-[var(--color-accent)] hover:underline">
      {name}
    </Link>
  ) : <span>{name}</span>;

  return (
    <>
      {loading && <Loading />}

      {!loading && names.length === 0 && (
        <div className="mono mt-10 text-sm text-[var(--color-faint)]">
          No {tour.toUpperCase()} player profiles available right now — the data may be refreshing, so check back shortly.
        </div>
      )}

      {names.length > 0 && (
        <>
          <Reveal>
            <Dropdown
              searchable
              label="Search a player"
              placeholder="Search a player…"
              value={sel}
              onChange={pick}
              options={options}
              className="mt-8 w-full max-w-md"
            />
          </Reveal>

          {notFound && (
            <div className="panel mt-6 border-[var(--color-line)] p-5 text-sm text-[var(--color-muted)]">
              No {tour.toUpperCase()} player profile is available for “{urlName}”. Search above to choose a player with a complete dossier.
            </div>
          )}

          {p && (
            <motion.div
              variants={stagger(0.07, 0.05)}
              initial="hidden"
              animate="show"
              className="mt-6 grid min-w-0 gap-5 lg:grid-cols-3"
            >
              {/* identity + elo line */}
              <motion.div variants={fadeUp} className="panel min-w-0 p-6 lg:col-span-2">
                <div className="flex min-w-0 flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <div className="display text-3xl">{p.name}</div>
                    <div className="mono mt-2 text-sm text-[var(--color-muted)]">
                      Elo {p.elo} · {p.matches} matches{p.hand ? ` · ${p.hand}-handed` : ""}{p.rankPoints ? ` · ${p.rankPoints} pts` : ""}
                    </div>
                  </div>
                  <div className="max-w-full shrink-0 overflow-hidden sm:overflow-visible">
                    <Spark points={p.history.map((h) => h[1])} w={200} color="var(--color-accent)" />
                  </div>
                </div>
                <div className="mt-5 grid grid-cols-3 gap-3">
                  {SURFACES.map((s) => (
                    <div key={s} className="rounded-lg border border-[var(--color-line)] p-3">
                      <div className="eyebrow" style={{ color: surfaceColor(s) }}>{s}</div>
                      <AnimatedNumber value={(p as any)[`elo${s}`]} className="mt-1 block text-xl" />
                    </div>
                  ))}
                </div>
                <div className="mono mt-4 flex gap-8 text-sm">
                  <span>Serve <b className="text-[var(--color-accent)]">{pct(p.servePct, 1)}</b></span>
                  <span>Return <b className="text-[var(--color-cmp)]">{pct(p.returnPct, 1)}</b></span>
                </div>
              </motion.div>

              {/* style fingerprint */}
              <motion.div variants={fadeUp} className="panel min-w-0 p-6">
                <div className="eyebrow mb-3">Playing style</div>
                {Object.entries(STYLE_LABEL).map(([k, label]) => {
                  const v = p.style[k];
                  return (
                    <div key={k} className="flex items-center justify-between py-1.5">
                      <span className="text-xs text-[var(--color-muted)]">{label}</span>
                      <span className="mono text-xs">{v == null ? "—" : (k === "style_bp_clutch" ? (v >= 0 ? "+" : "") + (v * 100).toFixed(0) : (v * 100).toFixed(0))}</span>
                    </div>
                  );
                })}
                <div className="mono mt-2 text-[10px] text-[var(--color-faint)]">from Match Charting Project</div>
              </motion.div>

              {/* same tour-relative spider chart used by the two-player comparison */}
              <motion.div variants={fadeUp} className="panel min-w-0 p-4 sm:p-6 lg:col-span-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="eyebrow">Style profile</div>
                    <div className="mt-1 text-xs text-[var(--color-faint)]">
                      Percentile versus the {tour.toUpperCase()} profile field · further out means higher
                    </div>
                  </div>
                  <span className="flex items-center gap-2 text-sm">
                    <span className="inline-block h-2.5 w-2.5 rounded-sm bg-[var(--color-accent)]" />
                    <span className="mono text-[var(--color-accent)]">{p.name}</span>
                  </span>
                </div>
                <Radar
                  axes={RADAR_AXES}
                  series={radarSeries}
                  ariaLabel={`${p.name} style profile percentile radar`}
                />
              </motion.div>

              {/* recent form */}
              <motion.div variants={fadeUp} className="panel min-w-0 p-6 lg:col-span-2">
                <div className="eyebrow mb-3">Recent matches</div>
                <div className="divide-y divide-[var(--color-line)]/40">
                  {p.recent.slice(0, 10).map((m, i) => (
                    <div key={i} className="flex items-center gap-3 py-2 text-sm">
                      <span className="mono w-5 text-center" style={{ color: m.won ? "var(--color-win)" : "var(--color-loss)" }}>{m.won ? "W" : "L"}</span>
                      <span className="flex-1 truncate">{m.won ? "d. " : "lost to "}{opp(m.opp)}</span>
                      <span className="chip" style={{ color: surfaceColor(m.surface), borderColor: surfaceColor(m.surface) }}>{m.surface[0]}</span>
                      <span className="mono w-28 text-right text-xs text-[var(--color-muted)]">{m.score}</span>
                    </div>
                  ))}
                </div>
              </motion.div>

              {/* h2h */}
              <motion.div variants={fadeUp} className="panel min-w-0 p-6">
                <div className="eyebrow mb-3">Head-to-head</div>
                {p.h2h.slice(0, 8).map((h) => (
                  <div key={h.opp} className="flex items-center justify-between py-1.5 text-sm">
                    <span className="truncate text-[var(--color-muted)]">{opp(h.opp)}</span>
                    <span className="mono"><b className="text-[var(--color-win)]">{h.w}</b>–<b className="text-[var(--color-loss)]">{h.l}</b></span>
                  </div>
                ))}
              </motion.div>
            </motion.div>
          )}
        </>
      )}
    </>
  );
}
