import type { NextConfig } from "next";

// Static export (out/). For a project GitHub Pages deploy, set NEXT_PUBLIC_BASE_PATH
// (e.g. "/tennis-elo") so asset + data URLs resolve under the repo subpath.
const base = process.env.NEXT_PUBLIC_BASE_PATH || "";

const nextConfig: NextConfig = {
  output: "export",
  basePath: base || undefined,
  images: { unoptimized: true },
  trailingSlash: true,
};

export default nextConfig;
