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
    expect(nav.match(/safe-x/g)).toHaveLength(3);
  });

  it("uses four stable mobile destinations and a grouped accessible More sheet", () => {
    const nav = readWebSource("components/Nav.tsx");
    expect(nav).toContain("MOBILE_PRIMARY");
    expect(nav).toContain('aria-haspopup="dialog"');
    expect(nav).toContain('role="dialog"');
    expect(nav).toContain('aria-modal="true"');
    expect(nav).toContain('event.key === "Tab"');
    expect(nav).toContain("mobilePanelRef");
    expect(nav).toContain("moreRef.current?.focus()");
    expect(nav).not.toContain("overflow-x-auto border-t");
  });

  it("keeps title odds visible while round and rating detail collapses on mobile", () => {
    const home = readWebSource("app/page.tsx");
    expect(home).toContain("data-mobile-title-odds");
    expect(home).toContain('reach[round] < 0.9995');
    expect(home).toContain('className="-mx-1 hidden overflow-x-auto sm:block"');
  });

  it("pins touch interaction and dynamic-height invariants", () => {
    const css = readWebSource("app/globals.css");
    const hoverGate = css.indexOf("@media (hover: hover) and (pointer: fine)");
    const coarseGate = css.indexOf("@media (hover: none) and (pointer: coarse)");

    expect(css).toContain("min-height: 100svh");
    expect(css).toContain("min-height: 100dvh");
    expect(css).toContain("overflow-x: clip");
    expect(css.match(/overscroll-behavior: none/g)).toHaveLength(1);
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

  it("lets the player dossier shrink within a narrow viewport", () => {
    const player = readWebSource("app/player/page.tsx");

    expect(player).toContain('className="mt-6 grid min-w-0 gap-5 lg:grid-cols-3"');
    expect(player).toContain("flex min-w-0 flex-col gap-4 sm:flex-row");
    expect(player.match(/className="panel min-w-0/g)).toHaveLength(5);
    expect(player).toContain("single-radar+mobile-contained-v2");
  });
});
