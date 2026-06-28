import type { Metadata } from "next";
import { Anton, Hanken_Grotesk, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import Nav from "@/components/Nav";
import { TourProvider } from "@/lib/tour";

const anton = Anton({ weight: "400", subsets: ["latin"], variable: "--font-anton" });
const hanken = Hanken_Grotesk({ subsets: ["latin"], variable: "--font-hanken" });
const jb = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono-jb" });

const DESC =
  "A tennis forecast engine for the ATP & WTA tours: surface-blended Elo, an opponent-adjusted serve/return point model and an XGBoost combiner. Live ratings, match win probabilities and Monte Carlo draw simulations.";

export const metadata: Metadata = {
  title: "DEUCE — Tennis Forecast Engine",
  description: DESC,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${anton.variable} ${hanken.variable} ${jb.variable}`}>
      <body>
        <div className="atmosphere" />
        <TourProvider>
          <Nav />
          <main className="mx-auto w-full max-w-[1240px] px-4 sm:px-6">{children}</main>
          <footer className="mx-auto mt-20 w-full max-w-[1240px] border-t border-[var(--color-line)] px-4 py-8 text-[12px] text-[var(--color-faint)] sm:px-6">
            <span className="mono">DEUCE</span> — hybrid Elo + serve/return point model + XGBoost combiner.
            Walk-forward, leakage-free. Data refreshed weekly.
          </footer>
        </TourProvider>
      </body>
    </html>
  );
}
