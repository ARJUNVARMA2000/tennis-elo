import { describe, expect, it } from "vitest";

import robots from "@/app/robots";
import sitemap from "@/app/sitemap";
import {
  GOOGLE_SITE_VERIFICATION,
  pageMetadata,
  SITE_URL,
  SITE_VERIFICATION,
  WEBSITE_JSON_LD,
} from "@/lib/seo";
import { INDEXABLE_ROUTES } from "@/scripts/routes.mjs";

describe("search discovery metadata", () => {
  it("publishes the complete public route inventory and excludes private/legacy routes", () => {
    expect(INDEXABLE_ROUTES).toEqual([
      "/",
      "/rankings/",
      "/results/",
      "/schedule/",
      "/matches/",
      "/bracket/",
      "/scorecard/",
      "/predict/",
      "/accuracy/",
      "/trends/",
      "/explorer/",
      "/simulator/",
      "/player/",
      "/style/",
      "/strength/",
      "/track/",
      "/method/",
    ]);

    const paths = sitemap().map((entry) => new URL(entry.url).pathname);
    expect(paths).toEqual(INDEXABLE_ROUTES);
    expect(paths).not.toContain("/health/");
    expect(paths).not.toContain("/upcoming/");
    expect(new Set(paths).size).toBe(paths.length);
  });

  it("allows crawling and points crawlers at the absolute sitemap", () => {
    expect(robots()).toEqual({
      rules: { userAgent: "*", allow: "/" },
      sitemap: `${SITE_URL}/sitemap.xml`,
      host: SITE_URL,
    });
  });

  it("gives every public subpage a clean self-canonical URL", () => {
    for (const route of INDEXABLE_ROUTES.filter((path) => path !== "/")) {
      const slug = route.slice(1, -1);
      expect(pageMetadata(slug).alternates).toEqual({ canonical: route });
    }
  });

  it("identifies the site consistently for search engines", () => {
    expect(WEBSITE_JSON_LD).toEqual({
      "@context": "https://schema.org",
      "@type": "WebSite",
      name: "DEUCE",
      alternateName: "DEUCE Tennis Forecast Engine",
      url: `${SITE_URL}/`,
    });
  });

  it("publishes the exact Google Search Console ownership token", () => {
    expect(GOOGLE_SITE_VERIFICATION).toBe(
      "A9r3zgELsRVJ1tEyVaDH4heFNcEeDXIvZ_KzRH__eHQ",
    );
    expect(SITE_VERIFICATION).toEqual({ google: GOOGLE_SITE_VERIFICATION });
  });
});
