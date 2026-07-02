"use client";

import { useEffect, useRef, useState } from "react";
import { animate, useReducedMotion } from "framer-motion";

/* The single motion vocabulary for the app — import these, don't invent new curves. */

export const EASE: [number, number, number, number] = [0.16, 1, 0.3, 1];
export const SPRING = { type: "spring", stiffness: 300, damping: 26 } as const;
export const SPRING_SOFT = { type: "spring", stiffness: 180, damping: 22 } as const;

/** Parent variants: staggers children that use `fadeUp`/`pop`. */
export const stagger = (delay = 0.05, delayChildren = 0) => ({
  hidden: {},
  show: { transition: { staggerChildren: delay, delayChildren } },
});

export const fadeUp = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.45, ease: EASE } },
};

export const fade = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: 0.35 } },
};

export const pop = {
  hidden: { opacity: 0, scale: 0.6 },
  show: { opacity: 1, scale: 1, transition: SPRING_SOFT },
};

/** Spread onto a motion element for a spring hover/press feel. */
export const hoverLift = {
  whileHover: { y: -2 },
  whileTap: { scale: 0.98 },
  transition: SPRING,
} as const;

/**
 * Animate a number toward `value` (0 → value on mount, then springs between
 * changes — e.g. ATP↔WTA or surface switches). Respects reduced motion.
 */
export function useCountUp(value: number, duration = 0.8): number {
  const reduced = useReducedMotion();
  const [display, setDisplay] = useState(0);
  const from = useRef(0);
  useEffect(() => {
    if (!isFinite(value)) return;
    if (reduced) {
      from.current = value;
      setDisplay(value);
      return;
    }
    const controls = animate(from.current, value, {
      duration,
      ease: EASE,
      onUpdate: (v) => setDisplay(v),
    });
    from.current = value;
    return () => controls.stop();
  }, [value, duration, reduced]);
  return display;
}
