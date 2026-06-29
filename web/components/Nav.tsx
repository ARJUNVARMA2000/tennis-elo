"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTour } from "@/lib/tour";

const LINKS = [
  ["/", "Tournaments"],
  ["/rankings", "Rankings"],
  ["/predict", "Predict"],
  ["/simulator", "Simulator"],
  ["/upcoming", "Latest"],
  ["/player", "Players"],
  ["/style", "Style"],
  ["/trends", "Trends"],
  ["/accuracy", "Accuracy"],
  ["/track", "Track record"],
  ["/method", "Method"],
];

export default function Nav() {
  const path = usePathname();
  const { tour, setTour } = useTour();
  const active = (href: string) => (href === "/" ? path === "/" : path.startsWith(href));

  return (
    <header className="sticky top-0 z-50 border-b border-[var(--color-line)] bg-[rgba(7,9,13,0.78)] backdrop-blur-md">
      <div className="mx-auto flex w-full max-w-[1240px] items-center gap-4 px-4 py-3 sm:px-6">
        <Link href="/" className="display text-xl tracking-wide">
          DE<span className="text-[var(--color-lime)]">U</span>CE
        </Link>

        <nav className="ml-3 hidden flex-1 items-center gap-5 text-[13px] text-[var(--color-muted)] lg:flex">
          {LINKS.map(([href, label]) => (
            <Link key={href} href={href} className="navlink py-1" data-active={active(href)}>
              {label}
            </Link>
          ))}
        </nav>

        {/* ATP / WTA toggle */}
        <div className="ml-auto flex items-center rounded-full border border-[var(--color-line)] p-0.5">
          {(["atp", "wta"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTour(t)}
              className="mono rounded-full px-3 py-1 text-[11px] uppercase tracking-wider transition-colors"
              style={{
                background: tour === t ? "var(--color-lime)" : "transparent",
                color: tour === t ? "#07090d" : "var(--color-muted)",
              }}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* mobile nav */}
      <nav className="flex gap-4 overflow-x-auto border-t border-[var(--color-line)] px-4 py-2 text-[12px] text-[var(--color-muted)] lg:hidden">
        {LINKS.map(([href, label]) => (
          <Link key={href} href={href} className="whitespace-nowrap" data-active={active(href)}>
            {label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
