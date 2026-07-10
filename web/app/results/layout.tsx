import { pageMetadata } from "@/lib/seo";

export const metadata = pageMetadata("results");

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
