import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import { APP_VIEWPORT } from "@/lib/mobile";

const readWebSource = (path: string) =>
  readFileSync(new URL(`../${path}`, import.meta.url), "utf-8");

describe("mobile browser shell", () => {
  it("opts into edge-to-edge dark browser chrome", () => {
    expect(APP_VIEWPORT).toEqual({
      colorScheme: "dark",
      themeColor: "#08090a",
      viewportFit: "cover",
    });
  });

  it("uses safe-area gutters on every edge-to-edge shell surface", () => {
    const css = readWebSource("app/globals.css");
    const layout = readWebSource("app/layout.tsx");
    const nav = readWebSource("components/Nav.tsx");

    expect(css).toContain("env(safe-area-inset-left, 0px)");
    expect(css).toContain("env(safe-area-inset-right, 0px)");
    expect(css).toContain("env(safe-area-inset-top, 0px)");
    expect(css).toContain("env(safe-area-inset-bottom, 0px)");
    expect(layout).toMatch(/<main className="[^"]*safe-x/);
    expect(layout).toMatch(/<footer className="[^"]*safe-bottom[^"]*safe-x/);
    expect(nav).toMatch(/<header className="[^"]*safe-top/);
    expect(nav.match(/safe-x/g)).toHaveLength(2);
  });

  it("pins touch interaction and dynamic-height invariants", () => {
    const css = readWebSource("app/globals.css");
    const hoverGate = css.indexOf("@media (hover: hover) and (pointer: fine)");
    const coarseGate = css.indexOf("@media (hover: none) and (pointer: coarse)");

    expect(css).toContain("min-height: 100svh");
    expect(css).toContain("min-height: 100dvh");
    expect(css).toContain("overflow-x: clip");
    expect(css.match(/overscroll-behavior: none/g)).toHaveLength(2);
    expect(css).toContain("touch-action: manipulation");
    expect(css).toContain("user-select: none");
    expect(css.indexOf(".panel-link:hover")).toBeGreaterThan(hoverGate);
    expect(css.indexOf(".row-glow:hover")).toBeGreaterThan(hoverGate);
    expect(css.indexOf("input, select, textarea { font-size: 16px; }")).toBeGreaterThan(coarseGate);
    expect(css.indexOf(":active { opacity: 0.72; }")).toBeGreaterThan(coarseGate);
  });

  it("keeps rankings data reachable through an adaptive mobile metric column", () => {
    const rankings = readWebSource("app/rankings/page.tsx");
    const css = readWebSource("app/globals.css");

    expect(rankings).toContain('className="panel data-scroll"');
    expect(rankings).toContain('className="ml-auto w-44 sm:hidden"');
    expect(rankings).toContain("<MobileMetric");
    expect(rankings).not.toContain('className="panel overflow-hidden"');
    expect(css).toContain(".data-scroll");
    expect(css).toContain("overflow-x: auto");
  });
});
