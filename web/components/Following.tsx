"use client";

import { createContext, useContext, useEffect, useRef, useState } from "react";
import { followsPlayer, followingStorageKey, parseFollowing, toggleFollowing } from "@/lib/following";
import { useTour, type Tour } from "@/lib/tour";

type Saved = Record<Tour, string[]>;
const FollowingContext = createContext({
  names: { atp: [], wta: [] } as Saved,
  ready: false,
  persistent: true,
  toggle: (_tour: Tour, _name: string) => {},
});

export function FollowingProvider({ children }: { children: React.ReactNode }) {
  const [names, setNames] = useState<Saved>({ atp: [], wta: [] });
  const latest = useRef(names);
  const [ready, setReady] = useState(false);
  const [persistent, setPersistent] = useState(true);
  useEffect(() => {
    try {
      latest.current = {
        atp: parseFollowing(localStorage.getItem(followingStorageKey("atp"))),
        wta: parseFollowing(localStorage.getItem(followingStorageKey("wta"))),
      };
      setNames(latest.current);
    } catch { setPersistent(false); }
    setReady(true);
    const onStorage = (event: StorageEvent) => {
      for (const tour of ["atp", "wta"] as const) {
        if (event.key !== null && event.key !== followingStorageKey(tour)) continue;
        latest.current = { ...latest.current, [tour]: parseFollowing(event.newValue) };
      }
      setNames(latest.current);
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);
  const toggle = (tour: Tour, name: string) => {
    if (!ready) return;
    let current = latest.current[tour];
    if (persistent) {
      try { current = parseFollowing(localStorage.getItem(followingStorageKey(tour))); }
      catch { setPersistent(false); }
    }
    const next = toggleFollowing(current, name);
    latest.current = { ...latest.current, [tour]: next };
    setNames(latest.current);
    try { localStorage.setItem(followingStorageKey(tour), JSON.stringify(next)); }
    catch { setPersistent(false); }
  };
  return <FollowingContext.Provider value={{ names, ready, persistent, toggle }}>{children}</FollowingContext.Provider>;
}

export function useFollowing() {
  const { tour } = useTour();
  const state = useContext(FollowingContext);
  const names = state.names[tour];
  return { names, ready: state.ready, persistent: state.persistent,
    follows: (player: string) => followsPlayer(names, player),
    toggle: (player: string) => state.toggle(tour, player) };
}

export function FollowButton({ name, compact = false }: { name: string; compact?: boolean }) {
  const { follows, ready, toggle, persistent } = useFollowing();
  const active = follows(name);
  return (
    <button type="button" aria-pressed={active} aria-label={`${active ? "Unfollow" : "Follow"} ${name}`} disabled={!ready}
      title={`${active ? "Unfollow" : "Follow"} ${name}${persistent ? "" : " (this session only)"}`}
      onClick={() => toggle(name)} data-follow-player={name}
      className={`relative z-10 shrink-0 rounded-md border px-2 py-1.5 text-[11px] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)] disabled:opacity-50 ${active ? "border-[var(--color-accent)] bg-[var(--color-accent-dim)] text-[var(--color-accent)]" : "border-[var(--color-line2)] text-[var(--color-muted)] hover:text-[var(--color-text)]"}`}>
      <span aria-hidden="true">{active ? "★" : "☆"}</span>{!compact && <span className="ml-1.5">{active ? "Following" : "Follow"}</span>}
    </button>
  );
}
