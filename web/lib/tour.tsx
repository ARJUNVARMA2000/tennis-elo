"use client";

import { createContext, Suspense, useContext, useEffect, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { MotionConfig } from "framer-motion";
import { resolveTour, setSearchTour } from "@/lib/url";

export type Tour = "atp" | "wta";

const BASE = process.env.NEXT_PUBLIC_BASE_PATH || "";

const Ctx = createContext<{ tour: Tour; setTour: (t: Tour) => void }>({
  tour: "atp",
  setTour: () => {},
});

/** Reconciles the ?tour= URL param with the context on every navigation:
    an explicit param wins (shared links open what the sender saw); a param-less
    URL while WTA is active gets canonicalized so the state is always shareable.
    Loop-safe: setTour updates state and URL together, so each pass reconciles a
    real mismatch at most once. Lives in its own component because useSearchParams
    needs a Suspense boundary under static export. */
function TourUrlBridge() {
  const { tour, setTour } = useContext(Ctx);
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  // URL→state applies only when the search string actually CHANGED (a navigation:
  // back/forward, cross-link). On a toggle the effect fires with tour updated but
  // searchParams still stale — applying the old param there would revert the toggle.
  const lastSearch = useRef<string | null>(null);
  useEffect(() => {
    const q = searchParams.toString();
    const navigated = lastSearch.current !== q;
    lastSearch.current = q;
    const param = searchParams.get("tour");
    if (param === "atp" || param === "wta") {
      if (navigated && param !== tour) setTour(param);
    } else if (tour === "wta") {
      router.replace(`${pathname}${setSearchTour(q, tour)}`, { scroll: false });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, tour, pathname]);
  return null;
}

export function TourProvider({ children }: { children: React.ReactNode }) {
  const [tour, setTourState] = useState<Tour>("atp");
  const router = useRouter();
  const pathname = usePathname();
  useEffect(() => {
    // initial load precedence: URL param > saved preference > atp.
    // window.location is read directly so the provider itself needs no Suspense.
    const param = new URLSearchParams(window.location.search).get("tour");
    const t = resolveTour(param, localStorage.getItem("tour"));
    setTourState(t);
    if (param === "atp" || param === "wta") localStorage.setItem("tour", param);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const set = (t: Tour) => {
    setTourState(t);
    localStorage.setItem("tour", t);
    router.replace(`${pathname}${setSearchTour(window.location.search, t)}`, { scroll: false });
  };
  return (
    <Ctx.Provider value={{ tour, setTour: set }}>
      <Suspense fallback={null}>
        <TourUrlBridge />
      </Suspense>
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
