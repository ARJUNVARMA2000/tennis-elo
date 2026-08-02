import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/seo";
import { INDEXABLE_ROUTES } from "@/scripts/routes.mjs";

export const dynamic = "force-static";

export default function sitemap(): MetadataRoute.Sitemap {
  return INDEXABLE_ROUTES.map((route) => ({
    url: new URL(route, `${SITE_URL}/`).href,
  }));
}
