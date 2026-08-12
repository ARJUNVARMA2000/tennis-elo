"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useMemo, useRef, useState } from "react";
import { useTour, type Tour } from "@/lib/tour";
import { commandResults, type CommandResult, type SearchBracket, type SearchPlayer } from "@/lib/search";

const BASE = process.env.NEXT_PUBLIC_BASE_PATH || "";

const KIND: Record<CommandResult["kind"], string> = {
  page: "Page",
  player: "Player",
  tournament: "Draw",
  prediction: "Predict",
};

function SearchIcon() {
  return (
    <svg viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
      <circle cx="7" cy="7" r="4.5" />
      <path d="m10.5 10.5 3 3" strokeLinecap="round" />
    </svg>
  );
}

export default function CommandSearch() {
  const { tour } = useTour();
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const [index, setIndex] = useState<{
    tour: Tour;
    players: SearchPlayer[];
    brackets: SearchBracket[];
  } | null>(null);
  const results = useMemo(() => {
    const ready = index?.tour === tour ? index : null;
    return commandResults(query, tour, ready?.players ?? [], ready?.brackets ?? []);
  }, [query, tour, index]);

  const show = () => {
    setQuery("");
    setActive(0);
    setOpen(true);
  };
  const close = () => setOpen(false);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const typing = target?.matches("input, textarea, select, [contenteditable='true']");
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        open ? close() : show();
      } else if (!open && event.key === "/" && !typing && !event.metaKey && !event.ctrlKey && !event.altKey) {
        event.preventDefault();
        show();
      } else if (open && event.key === "Escape") {
        event.preventDefault();
        close();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  // Players and complete brackets are sizeable; fetch the search index only on demand.
  useEffect(() => {
    if (!open || index?.tour === tour) return;
    let live = true;
    Promise.all([
      fetch(`${BASE}/data/${tour}/players.json`).then((response) => response.ok ? response.json() : []),
      fetch(`${BASE}/data/${tour}/brackets.json`).then((response) => response.ok ? response.json() : []),
    ])
      .then(([nextPlayers, nextBrackets]) => {
        if (live) setIndex({ tour, players: nextPlayers, brackets: nextBrackets });
      })
      .catch(() => {
        if (live) setIndex({ tour, players: [], brackets: [] });
      });
    return () => { live = false; };
  }, [open, tour, index?.tour]);

  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    requestAnimationFrame(() => inputRef.current?.focus());
    return () => {
      document.body.style.overflow = previous;
    };
  }, [open]);

  const navigate = (result: CommandResult | undefined) => {
    if (!result) return;
    close();
    router.push(result.href);
  };

  return (
    <>
      <button
        type="button"
        onClick={show}
        className="mono inline-flex h-8 items-center gap-2 rounded-md border border-[var(--color-line)] px-2 text-[11px] text-[var(--color-muted)] transition-colors hover:border-[var(--color-line2)] hover:text-[var(--color-text)]"
        aria-label="Search DEUCE"
        aria-haspopup="dialog"
      >
        <SearchIcon />
        <span className="hidden xl:inline">Search</span>
        <kbd className="hidden rounded border border-[var(--color-line)] px-1 text-[9px] text-[var(--color-faint)] xl:inline">⌘K</kbd>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            className="fixed inset-0 z-[100] flex items-start justify-center px-3 pt-[max(4rem,env(safe-area-inset-top,0px))] sm:pt-[14vh]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            data-command-search
          >
            <button
              type="button"
              className="absolute inset-0 bg-black/65 backdrop-blur-sm"
              onClick={close}
              aria-label="Close search"
            />
            <motion.div
              role="dialog"
              aria-modal="true"
              aria-label="Search DEUCE"
              initial={{ opacity: 0, y: 10, scale: 0.985 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 6, scale: 0.99 }}
              transition={{ duration: 0.16, ease: "easeOut" }}
              className="relative w-full max-w-xl overflow-hidden rounded-xl border border-[var(--color-line2)] bg-[rgba(15,16,17,0.96)] shadow-[var(--shadow-pop)]"
            >
              <div className="flex items-center gap-3 border-b border-[var(--color-line)] px-4">
                <span className="text-[var(--color-faint)]"><SearchIcon /></span>
                <input
                  ref={inputRef}
                  value={query}
                  onChange={(event) => {
                    setQuery(event.target.value);
                    setActive(0);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "ArrowDown") {
                      event.preventDefault();
                      setActive((index) => Math.min(index + 1, results.length - 1));
                    } else if (event.key === "ArrowUp") {
                      event.preventDefault();
                      setActive((index) => Math.max(index - 1, 0));
                    } else if (event.key === "Enter") {
                      event.preventDefault();
                      navigate(results[active]);
                    }
                  }}
                  role="combobox"
                  aria-expanded="true"
                  aria-controls="command-results"
                  aria-activedescendant={results[active] ? `command-result-${active}` : undefined}
                  placeholder="Search pages, players, draws, or ‘Sinner vs Alcaraz’"
                  className="h-14 min-w-0 flex-1 bg-transparent text-[15px] text-[var(--color-text)] outline-none placeholder:text-[var(--color-faint)]"
                />
                <span className="mono rounded border border-[var(--color-line)] px-1.5 py-0.5 text-[9px] text-[var(--color-faint)]">ESC</span>
              </div>
              <div id="command-results" role="listbox" className="max-h-[min(440px,65vh)] overflow-y-auto p-2">
                {results.map((result, index) => (
                  <Link
                    key={result.key}
                    id={`command-result-${index}`}
                    href={result.href}
                    role="option"
                    aria-selected={index === active}
                    onMouseEnter={() => setActive(index)}
                    onClick={close}
                    className="flex items-center gap-3 rounded-lg px-3 py-2.5 outline-none transition-colors"
                    style={{ background: index === active ? "rgba(255,255,255,0.06)" : undefined }}
                  >
                    <span className="mono w-14 shrink-0 text-[9px] uppercase tracking-wider text-[var(--color-faint)]">{KIND[result.kind]}</span>
                    <span className="min-w-0">
                      <span className="block truncate text-[13px] text-[var(--color-text)]">{result.label}</span>
                      <span className="block truncate text-[11px] text-[var(--color-faint)]">{result.desc}</span>
                    </span>
                    <span className="mono ml-auto text-[11px] text-[var(--color-faint)]">↵</span>
                  </Link>
                ))}
                {results.length === 0 && (
                  <div className="px-3 py-10 text-center">
                    <div className="text-sm text-[var(--color-muted)]">No match</div>
                    <div className="mono mt-1 text-[10px] text-[var(--color-faint)]">Try a player, tournament, or page name.</div>
                  </div>
                )}
              </div>
              <div className="mono flex items-center gap-4 border-t border-[var(--color-line)] px-4 py-2 text-[9px] text-[var(--color-faint)]">
                <span>↑↓ navigate</span><span>↵ open</span><span>esc close</span><span className="ml-auto hidden sm:inline">/ opens search</span>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
