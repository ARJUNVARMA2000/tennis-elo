// Tiny dependency-free server for the built Next static export used by browser CI.
import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, join, normalize, resolve, sep } from "node:path";

const root = resolve(process.env.STATIC_ROOT || new URL("../out/", import.meta.url).pathname);
const port = Number(process.env.PORT || 3001);
const types = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".txt": "text/plain; charset=utf-8",
  ".xml": "application/xml; charset=utf-8",
};

function fileFor(rawUrl) {
  const pathname = decodeURIComponent(new URL(rawUrl, "http://localhost").pathname);
  const relative = normalize(pathname).replace(/^[/\\]+/, "");
  let candidate = resolve(join(root, relative));
  if (candidate !== root && !candidate.startsWith(root + sep)) return null;
  if (existsSync(candidate) && statSync(candidate).isDirectory()) candidate = join(candidate, "index.html");
  if (!existsSync(candidate) && !extname(candidate)) candidate = join(candidate, "index.html");
  return existsSync(candidate) && statSync(candidate).isFile() ? candidate : null;
}

const server = createServer((request, response) => {
  const file = fileFor(request.url || "/");
  if (!file) {
    response.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
    response.end("not found");
    return;
  }
  response.writeHead(200, {
    "content-type": types[extname(file)] || "application/octet-stream",
    "cache-control": "no-store",
  });
  createReadStream(file).pipe(response);
});

server.listen(port, "127.0.0.1", () => console.log(`static browser-smoke server ready on ${port}`));
for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => server.close(() => process.exit(0)));
}
