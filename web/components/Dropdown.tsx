"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

export type DropdownOption = { value: string; label: string; sublabel?: string };

/* ---------- pure interaction logic (exported for tests) ---------- */

/** Case-insensitive substring filter over option labels. */
export function filterOptions(options: DropdownOption[], query: string): DropdownOption[] {
  const q = query.trim().toLowerCase();
  if (!q) return options;
  return options.filter((o) => o.label.toLowerCase().includes(q));
}

/** Next keyboard-highlighted index for a listbox navigation key. -1 = nothing highlighted. */
export function moveActive(count: number, current: number, key: string): number {
  if (count <= 0) return -1;
  switch (key) {
    case "ArrowDown":
      return current < 0 ? 0 : Math.min(current + 1, count - 1);
    case "ArrowUp":
      return current < 0 ? count - 1 : Math.max(current - 1, 0);
    case "Home":
      return 0;
    case "End":
      return count - 1;
    default:
      return current;
  }
}

/** First label starting with `buffer` (case-insensitive), scanning forward from
    `from` and wrapping. Returns -1 when nothing matches. */
export function typeAheadIndex(labels: string[], buffer: string, from: number): number {
  const q = buffer.toLowerCase();
  const n = labels.length;
  if (!q || !n) return -1;
  const start = ((from % n) + n) % n;
  for (let i = 0; i < n; i++) {
    const idx = (start + i) % n;
    if (labels[idx].toLowerCase().startsWith(q)) return idx;
  }
  return -1;
}

/* ---------- component ---------- */

function Chevron({ open }: { open: boolean }) {
  return (
    <motion.svg
      viewBox="0 0 10 6"
      width="9"
      height="6"
      animate={{ rotate: open ? 180 : 0 }}
      transition={{ duration: 0.18 }}
      className="shrink-0 opacity-60"
      aria-hidden="true"
    >
      <path d="M1 1l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </motion.svg>
  );
}

function Check({ visible }: { visible: boolean }) {
  return (
    <svg viewBox="0 0 10 8" width="10" height="8" className="shrink-0" style={{ opacity: visible ? 1 : 0 }} aria-hidden="true">
      <path d="M1 4l2.5 2.5L9 1" fill="none" stroke="var(--color-accent)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/**
 * Accessible listbox dropdown, styled to match the Nav glass panels.
 * Keyboard: ArrowUp/Down + Home/End navigate, Enter/Space select, Escape closes
 * (returns focus to the trigger), printable chars type-ahead (non-searchable).
 * `searchable` renders an autofocused filter input at the top of the panel.
 */
export default function Dropdown({
  value,
  onChange,
  options,
  label,
  searchable = false,
  placeholder = "Select…",
  className = "",
  compact = false,
  align = "left",
}: {
  value: string;
  onChange: (v: string) => void;
  options: DropdownOption[];
  label?: string;
  searchable?: boolean;
  placeholder?: string;
  className?: string;
  compact?: boolean;
  align?: "left" | "right";
}) {
  const id = useId();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(-1);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const typeBuf = useRef({ s: "", t: 0 });

  const selected = options.find((o) => o.value === value) ?? null;
  const shown = useMemo(() => (searchable ? filterOptions(options, query) : options), [searchable, options, query]);
  const listboxId = `${id}-listbox`;
  const optId = (i: number) => `${id}-opt-${i}`;
  const activeId = active >= 0 && active < shown.length ? optId(active) : undefined;

  const openPanel = () => {
    setQuery("");
    setActive(options.findIndex((o) => o.value === value));
    setOpen(true);
  };
  const close = (focusTrigger = false) => {
    setOpen(false);
    setQuery("");
    setActive(-1);
    if (focusTrigger) triggerRef.current?.focus();
  };
  const select = (v: string) => {
    onChange(v);
    close(true);
  };

  // outside click closes (pointerdown so it beats focus/click handlers elsewhere)
  useEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
        setQuery("");
        setActive(-1);
      }
    };
    document.addEventListener("pointerdown", onDown);
    return () => document.removeEventListener("pointerdown", onDown);
  }, [open]);

  // move focus into the panel when it opens
  useEffect(() => {
    if (!open) return;
    (searchable ? inputRef.current : listRef.current)?.focus();
  }, [open, searchable]);

  // keep the highlighted option in view
  useEffect(() => {
    if (open && activeId) document.getElementById(activeId)?.scrollIntoView({ block: "nearest" });
  }, [open, activeId]);

  const onPanelKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      e.preventDefault();
      close(true);
      return;
    }
    if (e.key === "Tab") {
      close();
      return;
    }
    if (e.key === "Enter" || (e.key === " " && !searchable)) {
      e.preventDefault();
      const pick = shown[active] ?? (searchable ? shown[0] : undefined);
      if (pick) select(pick.value);
      return;
    }
    if (e.key === "ArrowDown" || e.key === "ArrowUp" || (!searchable && (e.key === "Home" || e.key === "End"))) {
      e.preventDefault();
      setActive((a) => moveActive(shown.length, a, e.key));
      return;
    }
    if (!searchable && e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
      const now = e.timeStamp; // buffer keystrokes typed within 600ms of each other
      const s = now - typeBuf.current.t < 600 ? typeBuf.current.s + e.key : e.key;
      typeBuf.current = { s, t: now };
      const from = s.length === 1 ? active + 1 : Math.max(active, 0);
      const idx = typeAheadIndex(shown.map((o) => o.label), s, from);
      if (idx >= 0) setActive(idx);
    }
  };

  return (
    <div ref={rootRef} className={`relative ${className}`}>
      <button
        ref={triggerRef}
        type="button"
        onClick={() => (open ? close() : openPanel())}
        onKeyDown={(e) => {
          if (!open && (e.key === "ArrowDown" || e.key === "ArrowUp" || e.key === "Enter" || e.key === " ")) {
            e.preventDefault();
            openPanel();
          }
        }}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? listboxId : undefined}
        aria-label={label}
        className={`mono flex w-full items-center justify-between gap-3 rounded-md border border-[var(--color-line)] bg-[var(--color-panel2)] text-left text-[var(--color-text)] transition-colors focus:border-[var(--color-accent)] focus:outline-none ${
          compact ? "px-3 py-1.5 text-[12px]" : "py-3 pl-4 pr-3.5"
        }`}
      >
        <span className="truncate">
          {selected ? selected.label : <span className="text-[var(--color-faint)]">{placeholder}</span>}
        </span>
        <Chevron open={open} />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 4, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 4, scale: 0.98 }}
            transition={{ duration: 0.15, ease: "easeOut" }}
            onKeyDown={onPanelKeyDown}
            className={`absolute top-full z-40 mt-2 w-full min-w-[210px] max-w-[calc(100vw-2rem)] rounded-lg border border-[var(--color-line)] bg-[rgba(22,23,26,0.92)] p-1.5 shadow-[var(--shadow-pop)] backdrop-blur-xl ${
              align === "right" ? "right-0" : "left-0"
            }`}
          >
            {searchable && (
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setActive(e.target.value.trim() ? 0 : -1);
                }}
                placeholder="Type to filter…"
                role="combobox"
                aria-expanded={open}
                aria-controls={listboxId}
                aria-activedescendant={activeId}
                aria-autocomplete="list"
                aria-label={label ? `Filter ${label}` : "Filter options"}
                className="mono mb-1.5 w-full rounded-md border border-[var(--color-line)] bg-[var(--color-bg)] px-3 py-2 text-sm text-[var(--color-text)] outline-none placeholder:text-[var(--color-faint)] focus:border-[var(--color-accent)]"
              />
            )}
            <div
              ref={listRef}
              id={listboxId}
              role="listbox"
              tabIndex={searchable ? undefined : -1}
              aria-label={label}
              aria-activedescendant={searchable ? undefined : activeId}
              className="max-h-[280px] overflow-y-auto outline-none"
            >
              {shown.map((o, i) => {
                const isSel = o.value === value;
                return (
                  <div
                    key={o.value}
                    id={optId(i)}
                    role="option"
                    aria-selected={isSel}
                    onMouseEnter={() => setActive(i)}
                    onClick={() => select(o.value)}
                    className="flex cursor-pointer items-center gap-2 rounded-md px-2.5 py-1.5 text-[13px] transition-colors"
                    style={{
                      background: i === active ? "rgba(255,255,255,0.06)" : undefined,
                      color: isSel ? "var(--color-accent)" : "var(--color-text)",
                    }}
                  >
                    <Check visible={isSel} />
                    <span className="truncate">{o.label}</span>
                    {o.sublabel && (
                      <span className="mono ml-auto shrink-0 pl-3 text-[11px] text-[var(--color-faint)]">{o.sublabel}</span>
                    )}
                  </div>
                );
              })}
              {shown.length === 0 && (
                <div className="mono px-2.5 py-2 text-[11px] text-[var(--color-faint)]">no match</div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
