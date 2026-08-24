"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useTour } from "@/lib/tour";
import { withTour } from "@/lib/url";
import { NAV_GROUPS } from "@/lib/navigation";
import { SPRING } from "@/lib/motion";
import { GitHubIcon } from "@/components/bits";
import Freshness from "@/components/Freshness";
import CommandSearch from "@/components/CommandSearch";

const GITHUB_URL = "https://github.com/ARJUNVARMA2000/tennis-elo";

const isActive = (path: string, href: string) => (href === "/" ? path === "/" : path.startsWith(href));
const MOBILE_PRIMARY = [
  { href: "/", label: "Home", paths: ["/"] },
  { href: "/matches", label: "Matches", paths: ["/matches", "/schedule", "/results"] },
  { href: "/rankings", label: "Players", paths: ["/rankings", "/player", "/style", "/strength", "/explorer", "/trends"] },
  { href: "/bracket", label: "Brackets", paths: ["/bracket"] },
];

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
  const [mobileOpen, setMobileOpen] = useState(false);
  const navRef = useRef<HTMLElement>(null);
  const moreRef = useRef<HTMLButtonElement>(null);
  const mobilePanelRef = useRef<HTMLDivElement>(null);
  const btnRefs = useRef(new Map<string, HTMLButtonElement>());
  const panelRefs = useRef(new Map<string, HTMLDivElement>());

  // close any dropdown when the route changes
  useEffect(() => {
    setOpen(null);
    setMobileOpen(false);
  }, [path]);

  useEffect(() => {
    if (!mobileOpen) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    requestAnimationFrame(() => {
      mobilePanelRef.current?.querySelector<HTMLElement>("[data-mobile-sheet-close]")?.focus();
    });
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMobileOpen(false);
        moreRef.current?.focus();
        return;
      }
      if (event.key === "Tab" && mobilePanelRef.current) {
        const focusable = Array.from(
          mobilePanelRef.current.querySelectorAll<HTMLElement>(
            'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
          ),
        );
        if (!focusable.length) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKey);
    };
  }, [mobileOpen]);

  const closeMobile = (restoreFocus = false) => {
    setMobileOpen(false);
    if (restoreFocus) requestAnimationFrame(() => moreRef.current?.focus());
  };

  // outside click closes the open dropdown
  useEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent) => {
      if (navRef.current && !navRef.current.contains(e.target as Node)) setOpen(null);
    };
    document.addEventListener("pointerdown", onDown);
    return () => document.removeEventListener("pointerdown", onDown);
  }, [open]);

  const menuLinks = (label: string) =>
    Array.from(panelRefs.current.get(label)?.querySelectorAll<HTMLAnchorElement>("a") ?? []);

  /** Escape closes (focus back on trigger); ArrowUp/Down roves focus through the panel links. */
  const onGroupKeyDown = (label: string) => (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      if (open === label) {
        e.preventDefault();
        setOpen(null);
        btnRefs.current.get(label)?.focus();
      }
      return;
    }
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    e.preventDefault();
    if (open !== label) {
      setOpen(label);
      requestAnimationFrame(() => menuLinks(label)[0]?.focus());
      return;
    }
    const links = menuLinks(label);
    if (!links.length) return;
    const i = links.indexOf(document.activeElement as HTMLAnchorElement);
    if (e.key === "ArrowDown") {
      (links[i + 1] ?? links[links.length - 1]).focus();
    } else if (i === 0) {
      btnRefs.current.get(label)?.focus();
    } else {
      (links[i - 1] ?? links[links.length - 1]).focus();
    }
  };

  return (
    <header className="safe-top sticky top-0 z-50 border-b border-[var(--color-line)] bg-[rgba(8,9,10,0.72)] backdrop-blur-[20px]">
      <div className="safe-x mx-auto flex h-14 w-full max-w-[1240px] items-center gap-4">
        <Link href={withTour("/", tour)} className="flex items-center gap-2 text-[15px] font-semibold tracking-tight">
          <span className="inline-block h-2 w-2 rounded-[2px] bg-[var(--color-accent)]" />
          Deuce
        </Link>

        {/* desktop: grouped nav with sliding active pill + glass dropdowns */}
        <nav ref={navRef} aria-label="Primary" className="ml-2 hidden flex-1 items-center gap-1 text-[13px] text-[var(--color-muted)] lg:flex">
          {NAV_GROUPS.map((g) => {
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
                <Link key={g.label} href={withTour(g.href, tour)} className="relative rounded-md px-3 py-1.5 hover:text-[var(--color-text)]">
                  {label}
                </Link>
              );
            }
            const menuId = `nav-menu-${g.label}`;
            return (
              <div
                key={g.label}
                className="relative"
                onMouseEnter={() => setOpen(g.label)}
                onMouseLeave={() => setOpen((o) => (o === g.label ? null : o))}
                onKeyDown={onGroupKeyDown(g.label)}
              >
                <button
                  ref={(el) => {
                    if (el) btnRefs.current.set(g.label, el);
                    else btnRefs.current.delete(g.label);
                  }}
                  className="relative rounded-md px-3 py-1.5 hover:text-[var(--color-text)]"
                  onClick={() => setOpen((o) => (o === g.label ? null : g.label))}
                  aria-haspopup="true"
                  aria-expanded={open === g.label}
                  aria-controls={open === g.label ? menuId : undefined}
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
                      <div
                        ref={(el) => {
                          if (el) panelRefs.current.set(g.label, el);
                          else panelRefs.current.delete(g.label);
                        }}
                        id={menuId}
                        role="menu"
                        aria-label={g.label}
                        className="rounded-lg border border-[var(--color-line)] bg-[rgba(15,16,17,0.88)] p-1.5 shadow-[var(--shadow-pop)] backdrop-blur-xl"
                      >
                        {g.items!.map((it) => {
                          const a = isActive(path, it.href);
                          return (
                            <Link
                              key={it.href}
                              href={withTour(it.href, tour)}
                              role="menuitem"
                              className="flex items-start gap-2.5 rounded-md px-2.5 py-2 transition-colors hover:bg-white/[0.05] focus-visible:bg-white/[0.05] focus-visible:outline-none"
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
          <CommandSearch />

          {/* ATP / WTA segmented control with sliding thumb */}
          <div className="flex items-center rounded-md border border-[var(--color-line)] p-0.5">
            {(["atp", "wta"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTour(t)}
                aria-pressed={tour === t}
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

      {/* Mobile: four stable destinations plus an accessible grouped route sheet. */}
      <nav aria-label="Primary (mobile)" className="mobile-nav safe-x grid grid-cols-5 gap-1 border-t border-[var(--color-line)] py-1.5 text-[11px] text-[var(--color-muted)] lg:hidden">
        {MOBILE_PRIMARY.map(({ href, label, paths }) => {
          const a = paths.some((candidate) => isActive(path, candidate));
          return (
            <Link key={href} href={withTour(href, tour)} className="relative rounded-md px-1 py-2 text-center">
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
        <button
          ref={moreRef}
          type="button"
          onClick={() => setMobileOpen((value) => !value)}
          aria-haspopup="dialog"
          aria-expanded={mobileOpen}
          aria-controls="mobile-more-sheet"
          className="relative rounded-md px-1 py-2 text-center"
          style={{ color: mobileOpen ? "var(--color-text)" : undefined }}
        >
          More
        </button>
      </nav>
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            id="mobile-more-sheet"
            role="dialog"
            aria-modal="true"
            aria-label="All pages"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-x-0 bottom-0 top-[105px] z-50 lg:hidden"
          >
            <button
              type="button"
              aria-label="Close navigation"
              onClick={() => closeMobile(true)}
              className="absolute inset-0 bg-black/60"
            />
            <motion.div
              ref={mobilePanelRef}
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 20, opacity: 0 }}
              className="safe-x absolute inset-x-0 bottom-0 max-h-[78vh] overflow-y-auto rounded-t-2xl border-t border-[var(--color-line)] bg-[rgba(15,16,17,0.98)] pb-[calc(1rem+env(safe-area-inset-bottom))] pt-4 shadow-[var(--shadow-pop)]"
            >
              <div className="mb-3 flex items-center justify-between">
                <span className="eyebrow">All pages</span>
                <button
                  type="button"
                  data-mobile-sheet-close
                  onClick={() => closeMobile(true)}
                  className="mono rounded-md px-3 py-1 text-xs text-[var(--color-muted)]"
                >
                  close
                </button>
              </div>
              <div className="space-y-5">
                {NAV_GROUPS.map((group) => {
                  const items = group.href
                    ? [{ href: group.href, label: group.label, desc: "Current tournament forecasts" }]
                    : group.items ?? [];
                  return (
                    <section key={group.label}>
                      <h2 className="mono mb-2 text-[10px] uppercase tracking-wider text-[var(--color-faint)]">{group.label}</h2>
                      <div className="grid gap-1 sm:grid-cols-2">
                        {items.map((item) => {
                          const active = isActive(path, item.href);
                          return (
                            <Link
                              key={item.href}
                              href={withTour(item.href, tour)}
                              aria-current={active ? "page" : undefined}
                              className="rounded-lg border border-[var(--color-line)] px-3 py-2.5"
                              style={{ background: active ? "var(--color-accent-dim)" : undefined }}
                            >
                              <span className="block text-sm" style={{ color: active ? "var(--color-accent)" : "var(--color-text)" }}>{item.label}</span>
                              <span className="block text-[11px] text-[var(--color-faint)]">{item.desc}</span>
                            </Link>
                          );
                        })}
                      </div>
                    </section>
                  );
                })}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
