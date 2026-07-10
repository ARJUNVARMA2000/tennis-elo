import type { Metadata } from "next";
import { pageMetadata } from "@/lib/seo";

// Internal operations page: reachable only by typing /health — never linked from the
// site (absent from Nav's GROUPS) and kept out of search indexes.
export const metadata: Metadata = {
  ...pageMetadata("health"),
  robots: { index: false, follow: false },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
