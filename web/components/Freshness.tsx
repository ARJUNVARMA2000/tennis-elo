"use client";

import { useEffect, useState } from "react";
import { useData } from "@/lib/tour";

type Meta = { lastUpdated?: string };

function rel(iso: string, now: number): string | null {
  const t = Date.parse(iso);
  if (isNaN(t)) return null;
  const m = Math.max(0, Math.floor((now - t) / 60_000));
  if (m < 1) return "<1m ago";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 48) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

/** "updated Xm ago" pill — driven by the pipeline's meta.json build stamp. */
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
  if (!r) return null;
  return (
    <span className="chip hidden items-center gap-1.5 whitespace-nowrap text-[var(--color-muted)] sm:inline-flex">
      <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-win)]" />
      updated {r}
    </span>
  );
}
