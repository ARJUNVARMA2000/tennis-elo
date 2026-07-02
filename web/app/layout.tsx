import type { Metadata, Viewport } from "next";
import { Inter, Geist_Mono } from "next/font/google";
import "./globals.css";
import Nav from "@/components/Nav";
import { TourProvider } from "@/lib/tour";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono" });

const DESC =
  "A tennis forecast engine for the ATP & WTA tours: surface-blended Elo, an opponent-adjusted serve/return point model and an XGBoost combiner. Live ratings, match win probabilities and Monte Carlo draw simulations.";

const TITLE = "DEUCE — Tennis Forecast Engine";
const SITE_URL = "https://arjunvarma2000.github.io" + (process.env.NEXT_PUBLIC_BASE_PATH || "");

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
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

export const viewport: Viewport = { themeColor: "#08090a" };

const GITHUB_URL = "https://github.com/ARJUNVARMA2000/tennis-elo";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${geistMono.variable}`}>
      <body>
        <div className="atmosphere" />
        <TourProvider>
          <Nav />
          <main className="mx-auto w-full max-w-[1240px] px-4 sm:px-6">{children}</main>
          <footer className="mx-auto mt-20 w-full max-w-[1240px] border-t border-[var(--color-line)] px-4 py-8 sm:px-6">
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
                <svg viewBox="0 0 16 16" width="15" height="15" fill="currentColor" aria-hidden="true">
                  <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
                </svg>
                Source on GitHub
              </a>
            </div>
          </footer>
        </TourProvider>
      </body>
    </html>
  );
}
