import { defineConfig } from "eslint/config";
import next from "eslint-config-next/core-web-vitals";

export default defineConfig([
  ...next,
  {
    rules: {
      // This static-export app intentionally uses client-only hydration
      // patterns (localStorage restore, Date.now clocks, roster resets on
      // tour switch) that trip react-hooks v7's new set-state-in-effect
      // rule. They are deliberate — keep the signal visible but non-fatal.
      "react-hooks/set-state-in-effect": "warn",
    },
  },
]);
