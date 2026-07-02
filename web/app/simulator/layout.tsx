import { pageMetadata } from "@/lib/seo";

export const metadata = pageMetadata("simulator");

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
