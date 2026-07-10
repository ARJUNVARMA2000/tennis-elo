"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { useData, useTour } from "@/lib/tour";
import { pct, surfaceColor, SURFACES, STYLE_LABEL } from "@/lib/ui";
import { playerHref, setSearchParam } from "@/lib/url";
import { PageHead, Loading, Reveal, Spark, AnimatedNumber } from "@/components/bits";
import Dropdown, { type DropdownOption } from "@/components/Dropdown";
import { stagger, fadeUp } from "@/lib/motion";

type Profile = {
  name: string; elo: number; eloHard: number; eloClay: number; eloGrass: number; eloRank?: number;
  servePct: number; returnPct: number; rankPoints: number | null; matches: number; hand: string | null;
  style: Record<string, number | null>;
  history: [string, number][];
  recent: { date: string; opp: string; surface: string; won: boolean; score: string; event: string }[];
  h2h: { opp: string; w: number; l: number }[];
};

export default function Players() {
  const { tour } = useTour();
  return (
    <div className="pb-16">
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
  const { data, loading } = useData<Record<string, Profile>>("profiles.json");
  const router = useRouter();
  const pathname = usePathname();
  const urlName = useSearchParams().get("p");
  const names = useMemo(() => (data ? Object.keys(data) : []), [data]);
  const options: DropdownOption[] = useMemo(
    () =>
      names.map((n) => ({
        value: n,
        label: n,
        sublabel: data?.[n]?.eloRank != null ? `#${data[n].eloRank}` : undefined,
      })),
    [names, data],
  );
  const [sel, setSel] = useState("");

  // URL is the source of truth for the selection: ?p= wins when it names a known
  // player (cross-links, back/forward); otherwise fall back to the top player.
  useEffect(() => {
    if (!names.length) return;
    if (urlName && names.includes(urlName)) {
      if (urlName !== sel) setSel(urlName);
    } else if (!names.includes(sel)) {
      setSel(names[0]);
    }
  }, [names, urlName, sel]);
  const notFound = !!urlName && names.length > 0 && !names.includes(urlName);
  const p = data?.[sel];

  const pick = (n: string) => {
    setSel(n);
    router.replace(`${pathname}${setSearchParam(window.location.search, "p", n)}`, { scroll: false });
  };
  const opp = (name: string) => (
    <Link href={playerHref(name, tour)} className="transition-colors hover:text-[var(--color-accent)] hover:underline">
      {name}
    </Link>
  );

  return (
    <>
      {loading && <Loading />}

      {!loading && (!data || names.length === 0) && (
        <div className="mono mt-10 text-sm text-[var(--color-faint)]">
          No {tour.toUpperCase()} player profiles available right now — the data may be refreshing, so check back shortly.
        </div>
      )}

      {data && names.length > 0 && (
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
            <div className="mono mt-3 text-xs text-[var(--color-faint)]">
              No {tour.toUpperCase()} profile for “{urlName}” — showing {sel || "the top player"} instead.
            </div>
          )}

          {p && (
            <motion.div
              variants={stagger(0.07, 0.05)}
              initial="hidden"
              animate="show"
              className="mt-6 grid gap-5 lg:grid-cols-3"
            >
              {/* identity + elo line */}
              <motion.div variants={fadeUp} className="panel p-6 lg:col-span-2">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="display text-3xl">{p.name}</div>
                    <div className="mono mt-2 text-sm text-[var(--color-muted)]">
                      Elo {p.elo} · {p.matches} matches{p.hand ? ` · ${p.hand}-handed` : ""}{p.rankPoints ? ` · ${p.rankPoints} pts` : ""}
                    </div>
                  </div>
                  <Spark points={p.history.map((h) => h[1])} w={200} color="var(--color-accent)" />
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
              <motion.div variants={fadeUp} className="panel p-6">
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

              {/* recent form */}
              <motion.div variants={fadeUp} className="panel p-6 lg:col-span-2">
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
              <motion.div variants={fadeUp} className="panel p-6">
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
