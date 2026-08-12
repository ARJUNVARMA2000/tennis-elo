import type { Metadata, Viewport } from "next";
import { Inter, Geist_Mono } from "next/font/google";
import "./globals.css";
import Nav from "@/components/Nav";
import { GitHubIcon } from "@/components/bits";
import { TourProvider } from "@/lib/tour";
import { APP_VIEWPORT } from "@/lib/mobile";
import { SITE_URL, SITE_VERIFICATION, WEBSITE_JSON_LD } from "@/lib/seo";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono" });

const DESC =
  "A tennis forecast engine for the ATP & WTA tours: surface-blended Elo, an opponent-adjusted serve/return point model and an XGBoost combiner. Live ratings, match win probabilities and Monte Carlo draw simulations.";

const TITLE = "DEUCE — Tennis Forecast Engine";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  alternates: { canonical: "/" },
  applicationName: "DEUCE",
  verification: SITE_VERIFICATION,
  title: { default: TITLE, template: "%s · DEUCE" },
  description: DESC,
  openGraph: {
    siteName: "DEUCE",
    type: "website",
    title: TITLE,
    description: DESC,
    images: ["/og.png"],
  },
  twitter: {
    card: "summary_large_image",
    title: TITLE,
    description: DESC,
    images: ["/og.png"],
  },
};

export const viewport: Viewport = APP_VIEWPORT;

const GITHUB_URL = "https://github.com/ARJUNVARMA2000/tennis-elo";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${geistMono.variable}`}>
      <body>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify(WEBSITE_JSON_LD).replace(/</g, "\\u003c"),
          }}
        />
        <div className="atmosphere" />
        <TourProvider>
          <Nav />
          <main className="safe-x mx-auto w-full max-w-[1240px]">{children}</main>
          <footer className="safe-bottom safe-x mx-auto mt-20 w-full max-w-[1240px] border-t border-[var(--color-line)] py-8">
            <div className="flex flex-wrap items-center justify-between gap-3 text-[13px] text-[var(--color-faint)]">
              <p>
                <span className="font-medium text-[var(--color-muted)]">Deuce</span> — hybrid Elo +
                serve/return point model + XGBoost combiner. Walk-forward, leakage-free. Data
                refreshed hourly.
              </p>
              <a
                href={GITHUB_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-[var(--color-muted)] transition-colors hover:text-[var(--color-text)]"
              >
                <GitHubIcon size={15} />
                Source on GitHub
              </a>
            </div>
          </footer>
        </TourProvider>
      </body>
    </html>
  );
}
