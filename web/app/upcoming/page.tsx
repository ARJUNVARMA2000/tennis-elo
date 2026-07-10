"use client";

import { useEffect } from "react";
import Link from "next/link";

/** /upcoming showed *past* results and was renamed /results (2026-07). The site is a
    static export (no server redirects), so old links land here and get forwarded
    client-side; the query string rides along so ?tour=wta survives the hop.
    A HARD location.replace (not router.replace) — the tour bridge fires its own
    replace on mount and a soft client redirect loses that race. */
export default function UpcomingMoved() {
  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_BASE_PATH || "";
    window.location.replace(`${base}/results/${window.location.search}`);
  }, []);
  return (
    <div className="pb-16 pt-10">
      <p className="mono text-sm text-[var(--color-muted)]">
        This page moved — redirecting to{" "}
        <Link href="/results/" className="text-[var(--color-accent)] underline">
          Results
        </Link>
        …
      </p>
    </div>
  );
}
