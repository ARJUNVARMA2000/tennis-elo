// Start the exported site, wait for readiness, run the narrow real-browser contract, and
// always stop the child server. Keeping lifecycle control here avoids fragile background-shell
// plumbing in the workflow.
import { spawn } from "node:child_process";

const base = process.env.VERIFY_BASE_URL || "http://127.0.0.1:3001";
const timeoutMs = Number(process.env.BROWSER_SMOKE_TIMEOUT_MS || 5 * 60 * 1000);
const server = spawn(process.execPath, ["scripts/serve-static.mjs"], {
  stdio: "inherit",
  env: { ...process.env, PORT: new URL(base).port || "3001" },
});

function waitForExit(child, timeout) {
  if (child.exitCode !== null || child.signalCode !== null) return Promise.resolve(true);
  return new Promise((resolve) => {
    const timer = setTimeout(() => {
      child.off("exit", onExit);
      resolve(false);
    }, timeout);
    const onExit = () => {
      clearTimeout(timer);
      resolve(true);
    };
    child.once("exit", onExit);
  });
}

async function stopChild(child) {
  if (child.exitCode !== null || child.signalCode !== null) return;
  child.kill("SIGTERM");
  if (await waitForExit(child, 3_000)) return;
  child.kill("SIGKILL");
  await waitForExit(child, 3_000);
}

async function ready() {
  for (let attempt = 0; attempt < 80; attempt++) {
    if (server.exitCode !== null) throw new Error(`static server exited ${server.exitCode}`);
    try {
      const response = await fetch(`${base}/scorecard/`);
      if (response.ok) return;
    } catch { /* startup race */ }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error("static browser-smoke server did not become ready");
}

let status = 1;
try {
  await ready();
  status = await new Promise((resolve) => {
    const check = spawn(process.execPath, ["scripts/verify.mjs"], {
      stdio: "inherit",
      env: {
        ...process.env,
        VERIFY_BASE_URL: base,
        VERIFY_BROWSER: process.env.VERIFY_BROWSER || "chromium",
        VERIFY_ROUTES: process.env.VERIFY_ROUTES || "/scorecard/,/player/,/track/",
        VERIFY_VIEWS: process.env.VERIFY_VIEWS || "desktop,mobile",
        VERIFY_SCREENSHOTS: process.env.VERIFY_SCREENSHOTS || "0",
        VERIFY_OFFLINE: "1",
        VERIFY_FIXTURE_DATA: "1",
        VERIFY_ASSERT_NEGATIVE_CONTROLS: "1",
      },
    });
    let settled = false;
    const finish = (code) => {
      if (settled) return;
      settled = true;
      clearTimeout(watchdog);
      resolve(code);
    };
    const watchdog = setTimeout(async () => {
      console.error(`browser smoke exceeded ${timeoutMs}ms`);
      await stopChild(check);
      finish(1);
    }, timeoutMs);
    check.once("exit", (code) => finish(code ?? 1));
  });
} finally {
  await stopChild(server);
}
process.exit(status);
