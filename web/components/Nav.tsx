"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useTour } from "@/lib/tour";
import { SPRING } from "@/lib/motion";
import { GitHubIcon } from "@/components/bits";
import Freshness from "@/components/Freshness";

const GITHUB_URL = "https://github.com/ARJUNVARMA2000/tennis-elo";

type Item = { href: string; label: string; desc: string };
type Group = { label: string; href?: string; items?: Item[] };

const GROUPS: Group[] = [
  { label: "Overview", href: "/" },
  {
    label: "Players",
    items: [
      { href: "/rankings", label: "Rankings", desc: "Live Elo top 100" },
      { href: "/player", label: "Profiles", desc: "History, splits & H2H" },
      { href: "/style", label: "Playing style", desc: "13-axis fingerprints" },
      { href: "/strength", label: "Strength map", desc: "Serve vs return" },
      { href: "/trends", label: "Risers & fallers", desc: "Recent Elo movers" },
    ],
  },
  {
    label: "Forecasts",
    items: [
      { href: "/predict", label: "Predictor", desc: "Any matchup, any surface" },
      { href: "/simulator", label: "Draw simulator", desc: "Monte Carlo title odds" },
      { href: "/upcoming", label: "Latest results", desc: "Model calls on results" },
    ],
  },
  {
    label: "Model",
    items: [
      { href: "/accuracy", label: "Vs the market", desc: "Brier & calibration" },
      { href: "/track", label: "Track record", desc: "Graded point-in-time calls" },
      { href: "/method", label: "Method", desc: "How the engine works" },
    ],
  },
];

const FLAT: { href: string; label: string }[] = GROUPS.flatMap((g) =>
  g.href ? [{ href: g.href, label: g.label }] : g.items!.map(({ href, label }) => ({ href, label })),
);

const isActive = (path: string, href: string) => (href === "/" ? path === "/" : path.startsWith(href));

function Chevron({ open }: { open: boolean }) {
  return (
    <motion.svg
      viewBox="0 0 10 6"
      width="9"
      height="6"
      animate={{ rotate: open ? 180 : 0 }}
      transition={{ duration: 0.18 }}
      className="opacity-60"
      aria-hidden="true"
    >
      <path d="M1 1l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </motion.svg>
  );
}

export default function Nav() {
  const path = usePathname();
  const { tour, setTour } = useTour();
  const [open, setOpen] = useState<string | null>(null);

  // close any dropdown when the route changes
  useEffect(() => setOpen(null), [path]);

  return (
    <header className="sticky top-0 z-50 border-b border-[var(--color-line)] bg-[rgba(8,9,10,0.72)] backdrop-blur-[20px]">
      <div className="mx-auto flex h-14 w-full max-w-[1240px] items-center gap-4 px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2 text-[15px] font-semibold tracking-tight">
          <span className="inline-block h-2 w-2 rounded-[2px] bg-[var(--color-accent)]" />
          Deuce
        </Link>

        {/* desktop: grouped nav with sliding active pill + glass dropdowns */}
        <nav className="ml-2 hidden flex-1 items-center gap-1 text-[13px] text-[var(--color-muted)] lg:flex">
          {GROUPS.map((g) => {
            const groupActive = g.href
              ? isActive(path, g.href)
              : g.items!.some((it) => isActive(path, it.href));
            const label = (
              <>
                {groupActive && (
                  <motion.span
                    layoutId="nav-pill"
                    className="absolute inset-0 rounded-md bg-white/[0.06]"
                    transition={SPRING}
                  />
                )}
                <span
                  className="relative z-10 inline-flex items-center gap-1.5 transition-colors"
                  style={{ color: groupActive ? "var(--color-text)" : undefined }}
                >
                  {g.label}
                  {g.items && <Chevron open={open === g.label} />}
                </span>
              </>
            );

            if (g.href) {
              return (
                <Link key={g.label} href={g.href} className="relative rounded-md px-3 py-1.5 hover:text-[var(--color-text)]">
                  {label}
                </Link>
              );
            }
            return (
              <div
                key={g.label}
                className="relative"
                onMouseEnter={() => setOpen(g.label)}
                onMouseLeave={() => setOpen((o) => (o === g.label ? null : o))}
              >
                <button
                  className="relative rounded-md px-3 py-1.5 hover:text-[var(--color-text)]"
                  onClick={() => setOpen((o) => (o === g.label ? null : g.label))}
                  aria-expanded={open === g.label}
                >
                  {label}
                </button>
                <AnimatePresence>
                  {open === g.label && (
                    <motion.div
                      initial={{ opacity: 0, y: 6, scale: 0.98 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: 4, scale: 0.98 }}
                      transition={{ duration: 0.16, ease: "easeOut" }}
                      className="absolute left-0 top-full w-64 pt-2"
                    >
                      <div className="rounded-lg border border-[var(--color-line)] bg-[rgba(15,16,17,0.88)] p-1.5 shadow-[var(--shadow-pop)] backdrop-blur-xl">
                        {g.items!.map((it) => {
                          const a = isActive(path, it.href);
                          return (
                            <Link
                              key={it.href}
                              href={it.href}
                              className="flex items-start gap-2.5 rounded-md px-2.5 py-2 transition-colors hover:bg-white/[0.05]"
                              style={{ background: a ? "var(--color-accent-dim)" : undefined }}
                            >
                              <span
                                className="mt-[7px] h-1 w-1 shrink-0 rounded-full"
                                style={{ background: a ? "var(--color-accent)" : "var(--color-line2)" }}
                              />
                              <span>
                                <span className="block text-[13px]" style={{ color: a ? "var(--color-accent)" : "var(--color-text)" }}>
                                  {it.label}
                                </span>
                                <span className="block text-[11.5px] text-[var(--color-faint)]">{it.desc}</span>
                              </span>
                            </Link>
                          );
                        })}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-3">
          <Freshness />

          {/* ATP / WTA segmented control with sliding thumb */}
          <div className="flex items-center rounded-md border border-[var(--color-line)] p-0.5">
            {(["atp", "wta"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTour(t)}
                className="mono relative rounded-[5px] px-3 py-1 text-[11px] uppercase tracking-wider"
              >
                {tour === t && (
                  <motion.span
                    layoutId="tour-thumb"
                    className="absolute inset-0 rounded-[5px] bg-[var(--color-accent)]"
                    transition={SPRING}
                  />
                )}
                <span
                  className="relative z-10 transition-colors"
                  style={{ color: tour === t ? "var(--color-on-accent)" : "var(--color-muted)" }}
                >
                  {t}
                </span>
              </button>
            ))}
          </div>

          <motion.a
            href={GITHUB_URL}
            target="_blank"
            rel="noopener noreferrer"
            whileHover={{ scale: 1.12, rotate: -4 }}
            whileTap={{ scale: 0.92 }}
            transition={SPRING}
            className="text-[var(--color-muted)] transition-colors hover:text-[var(--color-text)]"
            aria-label="Source on GitHub"
          >
            <GitHubIcon />
          </motion.a>
        </div>
      </div>

      {/* mobile: flat scrollable chip strip */}
      <nav className="flex gap-1.5 overflow-x-auto border-t border-[var(--color-line)] px-4 py-2 text-[12px] text-[var(--color-muted)] lg:hidden">
        {FLAT.map(({ href, label }) => {
          const a = isActive(path, href);
          return (
            <Link key={href} href={href} className="relative whitespace-nowrap rounded-md px-2.5 py-1">
              {a && (
                <motion.span
                  layoutId="nav-pill-mobile"
                  className="absolute inset-0 rounded-md bg-white/[0.07]"
                  transition={SPRING}
                />
              )}
              <span className="relative z-10" style={{ color: a ? "var(--color-text)" : undefined }}>
                {label}
              </span>
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
