"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { MotionConfig } from "framer-motion";

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
  return (
    <Ctx.Provider value={{ tour, setTour: set }}>
      <MotionConfig reducedMotion="user">{children}</MotionConfig>
    </Ctx.Provider>
  );
}

export const useTour = () => useContext(Ctx);

/** Fetch a JSON artifact for the active tour from /data/<tour>/<file>.
    `error` flips on HTTP failure or a rejected fetch (pages may ignore it). */
export function useData<T>(file: string): { data: T | null; loading: boolean; error: boolean } {
  const { tour } = useTour();
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  useEffect(() => {
    let live = true;
    setLoading(true);
    setError(false);
    fetch(`${BASE}/data/${tour}/${file}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((j) => {
        if (live) {
          setData(j);
          setLoading(false);
        }
      })
      .catch(() => {
        if (live) {
          setData(null);
          setError(true);
          setLoading(false);
        }
      });
    return () => {
      live = false;
    };
  }, [tour, file]);
  return { data, loading, error };
}
