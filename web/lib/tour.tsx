"use client";

import { createContext, useContext, useEffect, useState } from "react";

export type Tour = "atp" | "wta";

const BASE = process.env.NEXT_PUBLIC_BASE_PATH || "";

const Ctx = createContext<{ tour: Tour; setTour: (t: Tour) => void }>({
  tour: "atp",
  setTour: () => {},
});

export function TourProvider({ children }: { children: React.ReactNode }) {
  const [tour, setTour] = useState<Tour>("atp");
  useEffect(() => {
    const saved = localStorage.getItem("tour") as Tour | null;
    if (saved === "atp" || saved === "wta") setTour(saved);
  }, []);
  const set = (t: Tour) => {
    setTour(t);
    localStorage.setItem("tour", t);
  };
  return <Ctx.Provider value={{ tour, setTour: set }}>{children}</Ctx.Provider>;
}

export const useTour = () => useContext(Ctx);

/** Fetch a JSON artifact for the active tour from /data/<tour>/<file>. */
export function useData<T>(file: string): { data: T | null; loading: boolean } {
  const { tour } = useTour();
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let live = true;
    setLoading(true);
    fetch(`${BASE}/data/${tour}/${file}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((j) => live && (setData(j), setLoading(false)))
      .catch(() => live && setLoading(false));
    return () => {
      live = false;
    };
  }, [tour, file]);
  return { data, loading };
}
