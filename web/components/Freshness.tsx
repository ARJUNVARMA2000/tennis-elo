"use client";

import { useEffect, useState } from "react";
import { useData } from "@/lib/tour";

type Meta = { lastUpdated?: string };

export function rel(iso: string, now: number): string | null {
  const t = Date.parse(iso);
  if (isNaN(t)) return null;
  const m = Math.max(0, Math.floor((now - t) / 60_000));
  if (m < 1) return "<1m ago";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 48) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export const AGING_H = 6; // several consecutive hourly quick runs missed
export const STALE_H = 26; // the daily full run has been missed

export function staleness(iso: string, now: number): "fresh" | "aging" | "stale" | null {
  const t = Date.parse(iso);
  if (isNaN(t)) return null;
  const h = (now - t) / 3_600_000;
  return h >= STALE_H ? "stale" : h >= AGING_H ? "aging" : "fresh";
}

const DOT: Record<string, string> = {
  fresh: "bg-[var(--color-win)]",
  aging: "bg-[var(--color-champ)]",
  stale: "bg-[var(--color-loss)]",
};

/** "updated Xm ago" pill — driven by the pipeline's meta.json build stamp. The dot goes
 *  gold once several hourly refreshes are missed and red past a missed daily full run,
 *  so a silently-dead pipeline is visible to any viewer, not just the CI watchdog. */
export default function Freshness() {
  const { data } = useData<Meta>("meta.json");
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => {
    setNow(Date.now()); // client-only clock (avoids SSR/prerender mismatch)
    const id = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(id);
  }, []);
  if (!data?.lastUpdated || now === null) return null;
  const r = rel(data.lastUpdated, now);
  const s = staleness(data.lastUpdated, now);
  if (!r || !s) return null;
  return (
    <span
      className={`chip inline-flex items-center gap-1.5 whitespace-nowrap ${
        s === "stale" ? "text-[var(--color-loss)]" : "text-[var(--color-muted)]"
      }`}
      title={s === "stale" ? "data may be stale" : undefined}
    >
      <span aria-hidden="true" className={`h-1.5 w-1.5 rounded-full ${DOT[s]}`} />
      <span className="hidden sm:inline">updated</span>
      {r}
    </span>
  );
}
