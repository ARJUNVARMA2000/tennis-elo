"use client";

import { motion } from "framer-motion";

/** Remounted on every navigation — gives each page an entrance transition.
    (Cross-route exit animations need router hacks; deliberately not done.) */
export default function Template({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
    >
      {children}
    </motion.div>
  );
}
