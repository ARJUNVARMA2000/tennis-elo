import type { NextConfig } from "next";

// Static export (out/). Production serves from the Firebase domain ROOT, so
// NEXT_PUBLIC_BASE_PATH is left unset and this resolves to "". It stays wired up so a
// subpath deploy (e.g. project GitHub Pages at "/tennis-elo") keeps working unchanged.
const base = process.env.NEXT_PUBLIC_BASE_PATH || "";

const nextConfig: NextConfig = {
  output: "export",
  basePath: base || undefined,
  images: { unoptimized: true },
  trailingSlash: true,
};

export default nextConfig;
