"use client";

import { createContext, Suspense, useContext, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { MotionConfig } from "framer-motion";
import { resolveTour, setSearchTour } from "@/lib/url";

export type Tour = "atp" | "wta";

const BASE = process.env.NEXT_PUBLIC_BASE_PATH || "";

const Ctx = createContext<{ tour: Tour; setTour: (t: Tour) => void }>({
  tour: "atp",
  setTour: () => {},
});

function mirrorTourUrl(tour: Tour) {
  window.history.replaceState(
    null,
    "",
    `${window.location.pathname}${setSearchTour(window.location.search, tour)}${window.location.hash}`,
  );
}

/** Reconciles the ?tour= URL param with the context on every navigation:
    an explicit param wins (shared links open what the sender saw); a param-less
    URL while WTA is active gets canonicalized so the state is always shareable.
    Loop-safe: setTour updates state and URL together, so each pass reconciles a
    real mismatch at most once. Lives in its own component because useSearchParams
    needs a Suspense boundary under static export. */
function TourUrlBridge() {
  const { tour, setTour } = useContext(Ctx);
  const searchParams = useSearchParams();
  // URL→state applies only when the search string actually CHANGED (a navigation:
  // back/forward, cross-link). On a toggle the effect fires with tour updated but
  // searchParams still stale — applying the old param there would revert the toggle.
  const lastSearch = useRef(searchParams.toString());
  useEffect(() => {
    const q = searchParams.toString();
    const navigated = lastSearch.current !== q;
    lastSearch.current = q;
    const param = searchParams.get("tour");
    if (param === "atp" || param === "wta") {
      if (navigated && param !== tour) setTour(param);
    } else if (navigated && tour === "wta") {
      mirrorTourUrl(tour);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, tour]);
  return null;
}

export function TourProvider({ children }: { children: React.ReactNode }) {
  const [tour, setTourState] = useState<Tour>("atp");
  useEffect(() => {
    // initial load precedence: URL param > saved preference > atp.
    // window.location is read directly so the provider itself needs no Suspense.
    const param = new URLSearchParams(window.location.search).get("tour");
    let saved: string | null = null;
    try { saved = localStorage.getItem("tour"); } catch { /* Session-only browsing. */ }
    const t = resolveTour(param, saved);
    setTourState(t);
    if (param === "atp" || param === "wta") {
      try { localStorage.setItem("tour", param); } catch { /* URL still records the tour. */ }
    } else if (t === "wta") {
      mirrorTourUrl(t);
    }
  }, []);
  const set = (t: Tour) => {
    setTourState(t);
    try { localStorage.setItem("tour", t); } catch { /* URL still records the tour. */ }
    // This state change is already local; using an asynchronous framework navigation for its URL mirror
    // can lose a rapid WTA -> ATP transition while the previous replacement is settling
    // (the page shows ATP but remains shareably tagged ?tour=wta). Next observes native
    // history updates when the caller does not pass Next's own internal history marker. Use
    // the browser pathname so a configured basePath and any anchor both survive the mirror.
    mirrorTourUrl(t);
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

type CacheEntry = {
  data?: unknown;
  promise?: Promise<unknown>;
  fetchedAt: number;
};

const jsonCache = new Map<string, CacheEntry>();
const tourGenerations = new Map<Tour, string>();
const META_MAX_AGE_MS = 60_000;

function invalidateTour(tour: Tour, keep: string) {
  const prefix = `${BASE}/data/${tour}/`;
  for (const key of jsonCache.keys()) {
    if (key.startsWith(prefix) && key !== keep) jsonCache.delete(key);
  }
}

function loadJson(url: string, maxAge = Number.POSITIVE_INFINITY): Promise<unknown> {
  const cached = jsonCache.get(url);
  if (cached?.data !== undefined && Date.now() - cached.fetchedAt <= maxAge) {
    return Promise.resolve(cached.data);
  }
  if (cached?.promise) return cached.promise;
  const promise = fetch(url)
    .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
    .then((data) => {
      jsonCache.set(url, { data, fetchedAt: Date.now() });
      return data;
    })
    .catch((error) => {
      jsonCache.delete(url);
      throw error;
    });
  jsonCache.set(url, { data: cached?.data, fetchedAt: cached?.fetchedAt ?? 0, promise });
  return promise;
}

type Meta = { lastUpdated?: string } & Record<string, unknown>;

function useTourMeta(tour: Tour): { data: Meta | null; loading: boolean; error: boolean; generation: string } {
  const [state, setState] = useState<{ tour: Tour; data: Meta | null; loading: boolean; error: boolean; generation: string }>({
    tour,
    data: null,
    loading: true,
    error: false,
    generation: tourGenerations.get(tour) ?? "",
  });
  useEffect(() => {
    let live = true;
    const url = `${BASE}/data/${tour}/meta.json`;
    const check = () => {
      loadJson(url, META_MAX_AGE_MS)
        .then((raw) => {
          if (!live) return;
          const data = raw as Meta;
          const generation = String(data.lastUpdated ?? "unversioned");
          const previous = tourGenerations.get(tour);
          if (previous && previous !== generation) invalidateTour(tour, url);
          tourGenerations.set(tour, generation);
          setState({ tour, data, loading: false, error: false, generation });
        })
        .catch(() => live && setState((s) => ({ ...s, loading: false, error: true })));
    };
    check();
    const onVisible = () => {
      if (document.visibilityState === "visible") check();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      live = false;
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [tour]);
  if (state.tour !== tour) {
    return { data: null, loading: true, error: false, generation: tourGenerations.get(tour) ?? "" };
  }
  return state;
}

function useJson<T>(url: string, enabled = true, generation = ""): { data: T | null; loading: boolean; error: boolean } {
  const requestKey = enabled && url ? `${url}\u0000${generation}` : "";
  const [state, setState] = useState<{ key: string; data: T | null; error: boolean }>({
    key: "",
    data: null,
    error: false,
  });
  useEffect(() => {
    if (!requestKey) return;
    let live = true;
    loadJson(url)
      .then((j) => {
        if (live) setState({ key: requestKey, data: j as T, error: false });
      })
      .catch(() => {
        if (live) setState({ key: requestKey, data: null, error: true });
      });
    return () => {
      live = false;
    };
  }, [url, requestKey]);
  if (!requestKey) return { data: null, loading: false, error: false };
  if (state.key !== requestKey) return { data: null, loading: true, error: false };
  return { data: state.data, loading: false, error: state.error };
}

/** Fetch a JSON artifact for the active tour from /data/<tour>/<file>.
    `error` flips on HTTP failure or a rejected fetch (pages may ignore it). */
export function useData<T>(file: string): { data: T | null; loading: boolean; error: boolean } {
  const { tour } = useTour();
  const meta = useTourMeta(tour);
  const artifact = useJson<T>(
    file ? `${BASE}/data/${tour}/${file}` : "",
    !!file && !!meta.generation,
    meta.generation,
  );
  if (file === "meta.json") {
    return { data: meta.data as T | null, loading: meta.loading, error: meta.error };
  }
  return {
    data: artifact.data,
    loading: meta.loading || artifact.loading,
    error: meta.error || artifact.error,
  };
}

/** Fetch a dynamic list of artifacts for the active tour through the same generation-aware
    cache as `useData`. One hook owns the whole list, so index-declared shard membership can
    change without changing React hook order. */
export function useDataFiles<T>(files: string[], enabled = true): {
  data: T[] | null; loading: boolean; error: boolean;
} {
  const { tour } = useTour();
  const meta = useTourMeta(tour);
  const fileKey = files.join("\u0000");
  const requestKey = enabled && meta.generation
    ? `${tour}\u0000${meta.generation}\u0000${fileKey}` : "";
  const [state, setState] = useState<{ key: string; data: T[] | null; error: boolean }>({
    key: "", data: null, error: false,
  });
  useEffect(() => {
    if (!requestKey) return;
    let live = true;
    Promise.all(files.map((file) => loadJson(`${BASE}/data/${tour}/${file}`)))
      .then((rows) => {
        if (live) setState({ key: requestKey, data: rows as T[], error: false });
      })
      .catch(() => {
        if (live) setState({ key: requestKey, data: null, error: true });
      });
    return () => { live = false; };
  }, [files, requestKey, tour]);
  if (!enabled) return { data: null, loading: false, error: false };
  if (meta.loading || !meta.generation || state.key !== requestKey) {
    return { data: null, loading: true, error: meta.error };
  }
  return { data: state.data, loading: false, error: meta.error || state.error };
}

/** Fetch a JSON artifact by path under /data/, tour-agnostic — "health.json" for the
    root report or an explicit "atp/track.json". Used by the (hidden) /health page,
    which shows both tours at once regardless of the site's tour toggle. */
export function useRootData<T>(file: string): { data: T | null; loading: boolean; error: boolean } {
  return useJson<T>(`${BASE}/data/${file}`);
}
