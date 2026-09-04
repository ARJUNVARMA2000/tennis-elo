// Post-deploy verification suite for the LIVE Firebase site — the serving-side analogue of
// the pre-deploy `health.py --gate` (which only sees local JSON). Catches the Firebase
// failure class that only shows up against the deployed URL: a "successful" deploy whose CDN
// still serves old content, a cache-header regression, MIME fall-through to index.html,
// trailingSlash/404 misbehaviour, or a SITE_URL/basePath regression baked into the HTML.
//
// Fetch-based — no browser, so it runs on any CI Node (the browser check stays in verify.mjs).
//
// Usage:
//   node scripts/verify-deploy.mjs [--base <url>] [--expect-generated-at <iso>]
//       [--expected-health <path>]
//   VERIFY_BASE_URL=... EXPECT_GENERATED_AT=... EXPECTED_HEALTH_PATH=... npm run verify:deploy
// Exits non-zero if any check fails, so it can gate/alert in the workflow.
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { INDEXABLE_ROUTES, ROUTES } from "./routes.mjs";
import {
  parseCacheControl,
  contentTypeOk,
  extractHashedAsset,
  isAbsoluteOnOrigin,
  coverageProblems,
  drawSourceProblems,
  extractOgImage,
  canonicalRouteProblems,
  extractGoogleSiteVerification,
  sitemapCoverageProblems,
  hasProfileContract,
  hasMatchCenterContract,
  hasLiveScheduleContract,
  hasHomeBracketEntryContract,
  hasPredictionExplanationContract,
  hasBracketLabContract,
  performanceArtifactProblems,
  scrollShellProblems,
  healthArtifactOk,
  artifactIndexRefs,
  fetchWithRetry,
  mutableCacheControlOk,
} from "./verify-deploy-lib.mjs";

// ---- config -----------------------------------------------------------------
function argVal(flag) {
  const i = process.argv.indexOf(flag);
  if (i >= 0 && process.argv[i + 1]) return process.argv[i + 1];
  const eq = process.argv.find((a) => a.startsWith(flag + "="));
  return eq ? eq.slice(flag.length + 1) : undefined;
}
const BASE = (argVal("--base") || process.env.VERIFY_BASE_URL || "https://deuce-forecast.web.app").replace(/\/$/, "");
const EXPECT_GENERATED_AT = argVal("--expect-generated-at") || process.env.EXPECT_GENERATED_AT || "";
const EXPECTED_HEALTH_PATH = argVal("--expected-health")
  || process.env.EXPECTED_HEALTH_PATH
  || "out/data/health.json";
const ORIGIN = new URL(BASE).origin;
const GOOGLE_SITE_VERIFICATION = "A9r3zgELsRVJ1tEyVaDH4heFNcEeDXIvZ_KzRH__eHQ";
// Freshness may lag deploy by a few seconds of CDN propagation; poll before failing.
// Overridable via env so CI can widen the window and tests can shorten it.
const FRESH_TRIES = Number(process.env.FRESH_TRIES) || (EXPECT_GENERATED_AT ? 12 : 1);
const FRESH_DELAY_MS = Number(process.env.FRESH_DELAY_MS) || 5000;
const FETCH_TRIES = Number(process.env.FETCH_TRIES) || 2;
const FETCH_RETRY_DELAY_MS = Number(process.env.FETCH_RETRY_DELAY_MS) || 500;

const LINEAGE_SCHEMA = "artifact-lineage-v1";
const LINEAGE_MANIFEST_PATH = "/data/release-manifest.json";
const LINEAGE_HEALTH_PATH = "/data/health.json";
const LINEAGE_MANIFEST_MAX_BYTES = 2 * 1024 * 1024;
const LINEAGE_HEALTH_MAX_BYTES = 8 * 1024 * 1024;
const LINEAGE_ARTIFACT_MAX_BYTES = 32 * 1024 * 1024;
const LINEAGE_RELEASE_MAX_BYTES = 512 * 1024 * 1024;
const LINEAGE_MAX_ARTIFACTS = 1024;
const LINEAGE_MAX_INDEX_REFERENCES = 512;
const LINEAGE_MAX_JSON_DEPTH = 64;
const LINEAGE_MAX_JSON_NODES = 1_000_000;
const LINEAGE_FETCH_BATCH = 16;
const LINEAGE_MAX_FILENAME_CHARS = 160;
const LINEAGE_MAX_PRODUCER_CHARS = 160;
const LINEAGE_FUTURE_SKEW_MS = 5 * 60 * 1000;
const LINEAGE_TOURS = ["atp", "wta"];
const LINEAGE_MANIFEST_FIELDS = ["artifacts", "createdAt", "mode", "parent", "releaseId", "schema"];
const LINEAGE_RECORD_FIELDS = [
  "bytes",
  "originRelease",
  "path",
  "predictorArtifactId",
  "producer",
  "role",
  "sha256",
  "sourceFingerprint",
];
const LINEAGE_SUMMARY_FIELDS = ["manifestSha256", "releaseId", "schema", "status", "tours"];
const LINEAGE_FIXED_CORE = new Set([
  "brackets.json",
  "draws.json",
  "event_coverage.json",
  "fixtures.json",
  "meta.json",
  "method.json",
  "performance.json",
  "players.json",
  "ratings_history.json",
  "tournaments.json",
]);
const LINEAGE_INDEX_ROLES = new Map([
  ["matrix-index.json", "matrix-index"],
  ["profile-index.json", "profile-index"],
  ["scenario-index.json", "scenario-index"],
  ["upcoming-index.json", "upcoming-index"],
]);
const LINEAGE_OPTIONAL_EVALUATION = new Set([
  "accuracy.json",
  "kalshi.json",
  "market.json",
  "tennis-abstract.json",
  "track.json",
]);
// These exact operational filenames come from the producer's private-output contracts. Firebase
// has no directory-listing API, so exact live-set verification combines the accepted positive
// graph with bounded negative probes for every known private path and every known optional file
// omitted from that graph.
const LINEAGE_PRIVATE_TOUR_FILENAMES = Object.freeze([
  "predictor.pkl",
  "predictor.pkl.envelope",
  "predictor.pkl.envelope.pending",
  "stage-status.private",
  "stage-status.json",
  "health-source.json",
  "tournament_draws-status.private",
]);
export const LINEAGE_FORBIDDEN_PATHS = Object.freeze([
  "/data/.last_full_run",
  "/data/release-accepted.private",
  ...LINEAGE_TOURS.flatMap((tour) => (
    LINEAGE_PRIVATE_TOUR_FILENAMES.map((filename) => `/data/${tour}/${filename}`)
  )),
]);
const LINEAGE_MAX_NEGATIVE_PROBES = LINEAGE_FORBIDDEN_PATHS.length
  + LINEAGE_TOURS.length * LINEAGE_OPTIONAL_EVALUATION.size;
const LINEAGE_DYNAMIC_PATTERNS = new Map([
  ["matrix-shard", /^matrix-[A-Za-z0-9][A-Za-z0-9._-]*\.json$/],
  ["profile-shard", /^profile-[0-9a-f]{16}\.json$/],
  ["scenario-shard", /^scenario-[A-Za-z0-9][A-Za-z0-9._-]*\.json$/],
  ["upcoming-event", /^upcoming-event-[A-Za-z0-9][A-Za-z0-9._-]*\.json$/],
  ["upcoming-evidence", /^upcoming-evidence-[A-Za-z0-9][A-Za-z0-9._-]*\.json$/],
]);
const LINEAGE_ROLES = new Set([
  "public-core",
  ...LINEAGE_INDEX_ROLES.values(),
  ...LINEAGE_DYNAMIC_PATTERNS.keys(),
  "evaluation",
]);
const UUID4_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const SHA256_RE = /^[0-9a-f]{64}$/;
const SOURCE_FINGERPRINT_RE = /^sf1:[0-9a-f]{64}$/;
const PRODUCER_RE = /^[A-Za-z0-9][A-Za-z0-9_.:/@+-]*$/;
const JSON_FILENAME_RE = /^[A-Za-z0-9][A-Za-z0-9._-]*\.json$/;
const UTC_TIMESTAMP_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$/;

function lineageMust(condition, message) {
  if (!condition) throw new Error(message);
}

function exactFields(value, expected) {
  return value !== null
    && typeof value === "object"
    && !Array.isArray(value)
    && JSON.stringify(Object.keys(value).sort()) === JSON.stringify(expected);
}

function sha256(raw) {
  return createHash("sha256").update(raw).digest("hex");
}

/**
 * Parse UTF-8 JSON while rejecting duplicate object keys and bounding depth/node count.
 * JSON.parse alone silently keeps the last duplicate key, which would let the live verifier
 * interpret different lineage from the Python acceptance gate.
 *
 * @param {Uint8Array} raw
 * @param {string} label
 * @returns {unknown}
 */
export function parseStrictLineageJson(raw, label = "lineage JSON") {
  let text;
  try {
    text = new TextDecoder("utf-8", { fatal: true }).decode(raw);
  } catch {
    throw new Error(`${label} is not valid UTF-8`);
  }

  let position = 0;
  let nodes = 0;
  const fail = (detail) => {
    throw new Error(`${label} is not strict bounded JSON (${detail})`);
  };
  const whitespace = () => {
    while (position < text.length && " \t\r\n".includes(text[position])) position += 1;
  };
  const parseString = () => {
    if (text[position] !== "\"") fail("string expected");
    const start = position;
    position += 1;
    while (position < text.length) {
      const code = text.charCodeAt(position);
      if (text[position] === "\"") {
        position += 1;
        try {
          return JSON.parse(text.slice(start, position));
        } catch {
          fail("invalid string escape");
        }
      }
      if (code < 0x20) fail("unescaped control character");
      if (text[position] === "\\") {
        position += 1;
        if (position >= text.length || !'"\\/bfnrtu'.includes(text[position])) {
          fail("invalid string escape");
        }
        if (text[position] === "u") {
          const escape = text.slice(position + 1, position + 5);
          if (!/^[0-9a-fA-F]{4}$/.test(escape)) fail("invalid unicode escape");
          position += 4;
        }
      }
      position += 1;
    }
    fail("unterminated string");
  };
  const parseValue = (depth) => {
    whitespace();
    nodes += 1;
    if (nodes > LINEAGE_MAX_JSON_NODES || depth > LINEAGE_MAX_JSON_DEPTH) {
      fail("structure exceeds bounds");
    }
    const token = text[position];
    if (token === "{") {
      position += 1;
      whitespace();
      const keys = new Set();
      if (text[position] === "}") {
        position += 1;
        return;
      }
      while (position < text.length) {
        whitespace();
        const key = parseString();
        if (keys.has(key)) fail(`duplicate object key ${JSON.stringify(key)}`);
        keys.add(key);
        whitespace();
        if (text[position] !== ":") fail("colon expected");
        position += 1;
        parseValue(depth + 1);
        whitespace();
        if (text[position] === "}") {
          position += 1;
          return;
        }
        if (text[position] !== ",") fail("object comma expected");
        position += 1;
      }
      fail("unterminated object");
    }
    if (token === "[") {
      position += 1;
      whitespace();
      if (text[position] === "]") {
        position += 1;
        return;
      }
      while (position < text.length) {
        parseValue(depth + 1);
        whitespace();
        if (text[position] === "]") {
          position += 1;
          return;
        }
        if (text[position] !== ",") fail("array comma expected");
        position += 1;
      }
      fail("unterminated array");
    }
    if (token === "\"") {
      parseString();
      return;
    }
    const remainder = text.slice(position);
    const number = remainder.match(/^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/);
    if (number) {
      if (!Number.isFinite(Number(number[0]))) fail("non-finite number");
      position += number[0].length;
      return;
    }
    for (const literal of ["true", "false", "null"]) {
      if (remainder.startsWith(literal)) {
        position += literal.length;
        return;
      }
    }
    fail("value expected");
  };

  parseValue(0);
  whitespace();
  if (position !== text.length) fail("trailing content");
  try {
    return JSON.parse(text);
  } catch {
    fail("invalid JSON syntax");
  }
}

async function responseBytes(response, limit, label) {
  const declaredLength = response.headers.get("content-length");
  if (declaredLength && /^\d+$/.test(declaredLength)) {
    lineageMust(Number(declaredLength) <= limit, `${label} exceeds the ${limit}-byte cap`);
  }
  if (!response.body || typeof response.body.getReader !== "function") {
    const raw = new Uint8Array(await response.arrayBuffer());
    lineageMust(raw.byteLength <= limit, `${label} exceeds the ${limit}-byte cap`);
    return raw;
  }
  const reader = response.body.getReader();
  const chunks = [];
  let total = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const chunk = value instanceof Uint8Array ? value : new Uint8Array(value);
    total += chunk.byteLength;
    if (total > limit) {
      await reader.cancel();
      throw new Error(`${label} exceeds the ${limit}-byte cap`);
    }
    chunks.push(chunk);
  }
  const raw = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    raw.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return raw;
}

function validUtcTimestamp(value) {
  if (typeof value !== "string" || value.length > 40 || !UTC_TIMESTAMP_RE.test(value)) return false;
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) return false;
  // Date.parse normalizes invalid calendar dates such as February 30. Pin the components
  // that precede fractional seconds so those spellings cannot cross the language boundary.
  return new Date(parsed).toISOString().slice(0, 19) === value.slice(0, 19);
}

/**
 * Return the accepted local lineage expectation. Missing, malformed, and non-accepted summaries
 * fail closed because every deploy must now carry an exact accepted artifact graph.
 *
 * @param {unknown} health
 * @returns {{schema: string, status: string, releaseId: string, manifestSha256: string, tours: string[]}}
 */
export function expectedArtifactLineage(health) {
  lineageMust(
    health !== null && typeof health === "object" && !Array.isArray(health),
    "health is not an object with accepted artifactLineage",
  );
  const summary = health.artifactLineage;
  lineageMust(
    summary !== null && typeof summary === "object" && !Array.isArray(summary),
    "health artifactLineage is missing or not an object",
  );
  lineageMust(
    summary.status === "accepted",
    `health artifactLineage status is ${String(summary.status)}; expected accepted`,
  );
  lineageMust(
    exactFields(summary, LINEAGE_SUMMARY_FIELDS),
    "accepted local health artifactLineage fields do not match artifact-lineage-v1",
  );
  lineageMust(summary.schema === LINEAGE_SCHEMA, `accepted local lineage schema is ${String(summary.schema)}`);
  lineageMust(UUID4_RE.test(summary.releaseId), "accepted local lineage releaseId is not a canonical UUID4");
  lineageMust(SHA256_RE.test(summary.manifestSha256), "accepted local lineage manifestSha256 is invalid");
  lineageMust(
    JSON.stringify(summary.tours) === JSON.stringify(LINEAGE_TOURS),
    "accepted local lineage tours must be exactly atp,wta",
  );
  return summary;
}

function expectedRole(filename, role) {
  if (LINEAGE_FIXED_CORE.has(filename)) return role === "public-core";
  if (LINEAGE_INDEX_ROLES.has(filename)) return role === LINEAGE_INDEX_ROLES.get(filename);
  if (LINEAGE_OPTIONAL_EVALUATION.has(filename)) return role === "evaluation";
  return LINEAGE_DYNAMIC_PATTERNS.has(role) && LINEAGE_DYNAMIC_PATTERNS.get(role).test(filename);
}

/** @param {unknown} manifest */
export function validateArtifactLineageManifest(manifest, expected, observedAt = new Date()) {
  lineageMust(
    exactFields(manifest, LINEAGE_MANIFEST_FIELDS),
    "release manifest top-level fields do not match artifact-lineage-v1",
  );
  lineageMust(manifest.schema === LINEAGE_SCHEMA, `release manifest schema is ${String(manifest.schema)}`);
  lineageMust(UUID4_RE.test(manifest.releaseId), "release manifest releaseId is not a canonical UUID4");
  lineageMust(manifest.releaseId === expected.releaseId, "release manifest releaseId differs from local health");
  lineageMust(
    manifest.parent === null || (UUID4_RE.test(manifest.parent) && manifest.parent !== manifest.releaseId),
    "release manifest parent is invalid",
  );
  lineageMust(validUtcTimestamp(manifest.createdAt), "release manifest createdAt is not a bounded UTC timestamp");
  lineageMust(
    Date.parse(manifest.createdAt) <= observedAt.getTime() + LINEAGE_FUTURE_SKEW_MS,
    "release manifest is implausibly future-dated",
  );
  lineageMust(manifest.mode === "full" || manifest.mode === "quick", "release manifest mode is unknown");
  lineageMust(
    manifest.mode !== "quick" || manifest.parent !== null,
    "quick release manifest requires an accepted parent",
  );
  lineageMust(
    Array.isArray(manifest.artifacts)
      && manifest.artifacts.length > 0
      && manifest.artifacts.length <= LINEAGE_MAX_ARTIFACTS,
    "release manifest artifact list is empty or oversized",
  );

  const paths = [];
  const tours = new Set();
  let totalBytes = 0;
  for (const record of manifest.artifacts) {
    lineageMust(
      exactFields(record, LINEAGE_RECORD_FIELDS),
      "release manifest artifact fields do not match artifact-lineage-v1",
    );
    const path = record.path;
    lineageMust(
      typeof path === "string"
        && path.length <= "wta/".length + LINEAGE_MAX_FILENAME_CHARS
        && !path.includes("\\")
        && path.split("/").length === 2,
      `unsafe declared artifact path ${String(path)}`,
    );
    const [tour, filename] = path.split("/");
    lineageMust(LINEAGE_TOURS.includes(tour), `unknown artifact tour in ${path}`);
    lineageMust(
      filename.length <= LINEAGE_MAX_FILENAME_CHARS
        && !filename.includes("..")
        && JSON_FILENAME_RE.test(filename),
      `unsafe declared artifact path ${path}`,
    );
    lineageMust(LINEAGE_ROLES.has(record.role), `unknown artifact role for ${path}`);
    lineageMust(expectedRole(filename, record.role), `artifact role does not match ${path}`);
    lineageMust(
      Number.isInteger(record.bytes)
        && record.bytes > 0
        && record.bytes <= LINEAGE_ARTIFACT_MAX_BYTES,
      `invalid artifact byte count for ${path}`,
    );
    lineageMust(SHA256_RE.test(record.sha256), `invalid artifact SHA-256 for ${path}`);
    lineageMust(
      typeof record.producer === "string"
        && record.producer.length > 0
        && record.producer.length <= LINEAGE_MAX_PRODUCER_CHARS
        && PRODUCER_RE.test(record.producer),
      `invalid artifact producer for ${path}`,
    );
    lineageMust(
      typeof record.sourceFingerprint === "string"
        && SOURCE_FINGERPRINT_RE.test(record.sourceFingerprint),
      `invalid source fingerprint for ${path}`,
    );
    lineageMust(UUID4_RE.test(record.predictorArtifactId), `invalid predictor artifact id for ${path}`);
    lineageMust(UUID4_RE.test(record.originRelease), `invalid origin release id for ${path}`);
    paths.push(path);
    tours.add(tour);
    totalBytes += record.bytes;
    lineageMust(totalBytes <= LINEAGE_RELEASE_MAX_BYTES, "release artifact bytes exceed the cap");
  }
  lineageMust(
    paths.every((path, index) => index === 0 || paths[index - 1] < path),
    "release manifest artifact records must be uniquely and exactly sorted by path",
  );
  lineageMust(
    JSON.stringify([...tours].sort()) === JSON.stringify(LINEAGE_TOURS),
    "release manifest must cover exactly ATP and WTA",
  );
  for (const tour of LINEAGE_TOURS) {
    for (const filename of [...LINEAGE_FIXED_CORE, ...LINEAGE_INDEX_ROLES.keys()]) {
      lineageMust(paths.includes(`${tour}/${filename}`), `release manifest is missing ${tour}/${filename}`);
    }
  }
  lineageMust(
    manifest.parent !== null
      || manifest.artifacts.every((record) => record.originRelease === manifest.releaseId),
    "bootstrap release artifacts must originate in their release",
  );
  return manifest;
}

function validateIndexClosure(manifest, indexPayloads) {
  const records = new Map(manifest.artifacts.map((record) => [record.path, record]));
  const referenced = new Set();
  const declareReference = (tour, filename, role) => {
    lineageMust(typeof filename === "string", `${tour} index contains a non-string shard reference`);
    const path = `${tour}/${filename}`;
    lineageMust(!referenced.has(path), `release indexes contain duplicate shard reference ${path}`);
    referenced.add(path);
    const record = records.get(path);
    lineageMust(record && record.role === role, `release index reference ${path} is not declared as ${role}`);
  };

  for (const tour of LINEAGE_TOURS) {
    const matrix = indexPayloads.get(`${tour}/matrix-index.json`);
    lineageMust(
      matrix && typeof matrix === "object"
        && matrix.surfaces && typeof matrix.surfaces === "object"
        && !Array.isArray(matrix.surfaces),
      `${tour} matrix index is malformed`,
    );
    let matrixReferences = 0;
    for (const formats of Object.values(matrix.surfaces || {})) {
      lineageMust(formats && typeof formats === "object" && !Array.isArray(formats), `${tour} matrix index is malformed`);
      for (const filename of Object.values(formats)) {
        matrixReferences += 1;
        declareReference(tour, filename, "matrix-shard");
      }
    }
    lineageMust(matrixReferences <= LINEAGE_MAX_INDEX_REFERENCES, `${tour} matrix index exceeds its reference cap`);

    const profiles = indexPayloads.get(`${tour}/profile-index.json`);
    lineageMust(Array.isArray(profiles?.profiles), `${tour} profile index is malformed`);
    lineageMust(profiles.profiles.length <= LINEAGE_MAX_INDEX_REFERENCES, `${tour} profile index exceeds its reference cap`);
    for (const row of profiles.profiles) declareReference(tour, row?.file, "profile-shard");

    const scenarios = indexPayloads.get(`${tour}/scenario-index.json`);
    lineageMust(Array.isArray(scenarios?.events), `${tour} scenario index is malformed`);
    lineageMust(scenarios.events.length <= LINEAGE_MAX_INDEX_REFERENCES, `${tour} scenario index exceeds its reference cap`);
    for (const row of scenarios.events) declareReference(tour, row?.file, "scenario-shard");

    const upcoming = indexPayloads.get(`${tour}/upcoming-index.json`);
    lineageMust(Array.isArray(upcoming?.events), `${tour} upcoming index is malformed`);
    lineageMust(
      upcoming.events.length * 2 <= LINEAGE_MAX_INDEX_REFERENCES,
      `${tour} upcoming index exceeds its reference cap`,
    );
    for (const row of upcoming.events) {
      declareReference(tour, row?.file, "upcoming-event");
      declareReference(tour, row?.evidenceFile, "upcoming-evidence");
    }
  }

  const declaredDynamic = manifest.artifacts
    .filter((record) => LINEAGE_DYNAMIC_PATTERNS.has(record.role))
    .map((record) => record.path)
    .sort();
  lineageMust(
    JSON.stringify([...referenced].sort()) === JSON.stringify(declaredDynamic),
    "release manifest dynamic shard set does not match its index graph",
  );
}

async function verifyKnownAbsentLineagePaths(base, manifest, fetcher) {
  const declared = new Set(manifest.artifacts.map((record) => `/data/${record.path}`));
  const probes = [
    ...LINEAGE_FORBIDDEN_PATHS.map((path) => ({ path, kind: "forbidden private path" })),
    ...LINEAGE_TOURS.flatMap((tour) => [...LINEAGE_OPTIONAL_EVALUATION]
      .map((filename) => `/data/${tour}/${filename}`)
      .filter((path) => !declared.has(path))
      .map((path) => ({ path, kind: "undeclared optional artifact" }))),
  ];
  lineageMust(
    probes.length <= LINEAGE_MAX_NEGATIVE_PROBES
      && new Set(probes.map((probe) => probe.path)).size === probes.length,
    "lineage negative-probe set is duplicate or exceeds its bound",
  );

  await Promise.all(probes.map(async ({ path, kind }) => {
    const response = await fetcher(base + path, {
      cache: "no-store",
      redirect: "manual",
    });
    const status = response.status;
    if (response.body) await response.body.cancel();
    lineageMust(status === 404, `${kind} ${path} -> ${status}; expected 404`);
  }));
  return probes.map((probe) => probe.path);
}

/**
 * Verify one accepted live release without sampling. The fetcher is injected for deterministic
 * adversarial tests and is normally the retrying production fetch wrapper.
 *
 * @param {{base: string, expectedHealth: unknown, fetcher?: typeof fetch, observedAt?: Date}} options
 */
export async function verifyArtifactLineageRelease({
  base,
  expectedHealth,
  fetcher = fetch,
  observedAt = new Date(),
}) {
  const expected = expectedArtifactLineage(expectedHealth);

  const normalizedBase = String(base).replace(/\/$/, "");
  const healthResponse = await fetcher(normalizedBase + LINEAGE_HEALTH_PATH, { cache: "no-store" });
  lineageMust(healthResponse.status === 200, `${LINEAGE_HEALTH_PATH} -> ${healthResponse.status}`);
  lineageMust(
    contentTypeOk(healthResponse.headers.get("content-type"), LINEAGE_HEALTH_PATH),
    `${LINEAGE_HEALTH_PATH} served as ${healthResponse.headers.get("content-type")}`,
  );
  const liveHealth = parseStrictLineageJson(
    await responseBytes(healthResponse, LINEAGE_HEALTH_MAX_BYTES, LINEAGE_HEALTH_PATH),
    "deployed health",
  );
  const liveExpected = expectedArtifactLineage(liveHealth);
  lineageMust(
    LINEAGE_SUMMARY_FIELDS.every((field) => JSON.stringify(liveExpected[field]) === JSON.stringify(expected[field])),
    "deployed health artifactLineage differs from local accepted health",
  );

  const manifestResponse = await fetcher(normalizedBase + LINEAGE_MANIFEST_PATH, { cache: "no-store" });
  lineageMust(manifestResponse.status === 200, `${LINEAGE_MANIFEST_PATH} -> ${manifestResponse.status}`);
  lineageMust(
    contentTypeOk(manifestResponse.headers.get("content-type"), LINEAGE_MANIFEST_PATH),
    `${LINEAGE_MANIFEST_PATH} served as ${manifestResponse.headers.get("content-type")}`,
  );
  const manifestBytes = await responseBytes(
    manifestResponse,
    LINEAGE_MANIFEST_MAX_BYTES,
    LINEAGE_MANIFEST_PATH,
  );
  lineageMust(
    sha256(manifestBytes) === expected.manifestSha256,
    "live release manifest digest differs from local accepted health",
  );
  const manifest = validateArtifactLineageManifest(
    parseStrictLineageJson(manifestBytes, "release manifest"),
    expected,
    observedAt,
  );
  const probedAbsentPaths = await verifyKnownAbsentLineagePaths(
    normalizedBase,
    manifest,
    fetcher,
  );

  const fetchedPaths = [];
  const indexPayloads = new Map();
  for (let start = 0; start < manifest.artifacts.length; start += LINEAGE_FETCH_BATCH) {
    const batch = manifest.artifacts.slice(start, start + LINEAGE_FETCH_BATCH);
    const verified = await Promise.all(batch.map(async (record) => {
      const urlPath = `/data/${record.path}`;
      const response = await fetcher(normalizedBase + urlPath, { cache: "no-store" });
      lineageMust(response.status === 200, `${urlPath} -> ${response.status}`);
      lineageMust(
        contentTypeOk(response.headers.get("content-type"), urlPath),
        `${urlPath} served as ${response.headers.get("content-type")}`,
      );
      const raw = await responseBytes(response, LINEAGE_ARTIFACT_MAX_BYTES, urlPath);
      lineageMust(raw.byteLength === record.bytes, `${urlPath} byte count differs from release manifest`);
      lineageMust(sha256(raw) === record.sha256, `${urlPath} digest differs from release manifest`);
      let indexPayload = null;
      if (LINEAGE_INDEX_ROLES.has(record.path.split("/")[1])) {
        indexPayload = parseStrictLineageJson(raw, urlPath);
      }
      return { path: record.path, indexPayload };
    }));
    for (const item of verified) {
      fetchedPaths.push(item.path);
      if (item.indexPayload !== null) indexPayloads.set(item.path, item.indexPayload);
    }
  }
  validateIndexClosure(manifest, indexPayloads);
  lineageMust(fetchedPaths.length === manifest.artifacts.length, "not every declared release artifact was fetched");
  return {
    artifactCount: manifest.artifacts.length,
    absentPathCount: probedAbsentPaths.length,
    releaseId: manifest.releaseId,
    fetchedPaths,
    probedAbsentPaths,
  };
}

export function loadExpectedHealth(path) {
  try {
    const raw = readFileSync(path);
    return parseStrictLineageJson(raw, `expected health ${path}`);
  } catch (error) {
    if (error?.code === "ENOENT") return {};
    throw error;
  }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function fetchT(url, opts = {}, ms = 30000) {
  return fetchWithRetry(url, opts, {
    attempts: FETCH_TRIES,
    delayMs: FETCH_RETRY_DELAY_MS,
    timeoutMs: ms,
    sleep,
  });
}

// ---- check runner -----------------------------------------------------------
async function main() {
const results = [];
async function check(name, fn) {
  try {
    const detail = await fn();
    results.push({ name, ok: true, detail: detail || "" });
  } catch (err) {
    results.push({ name, ok: false, detail: err?.message || String(err) });
  }
}
function must(cond, msg) {
  if (!cond) throw new Error(msg);
}

// ---- checks -----------------------------------------------------------------
// Home page fetched once and reused (cache header + asset discovery + meta).
let homeHtml = "";
const routeHtml = new Map();

await check("routes 200 + text/html", async () => {
  const bad = [];
  for (const route of ROUTES) {
    const res = await fetchT(BASE + route);
    const ct = res.headers.get("content-type");
    const served = res.status === 200 && contentTypeOk(ct, route);
    if (!served) bad.push(`${route} -> ${res.status} ${ct}`);
    const html = await res.text();
    if (served) {
      routeHtml.set(route, html);
      if (route === "/") homeHtml = html;
    }
  }
  must(bad.length === 0, `bad routes: ${bad.join("; ")}`);
  return `${ROUTES.length} routes ok`;
});

await check("crawl discovery: robots.txt + sitemap.xml", async () => {
  const robotsRes = await fetchT(BASE + "/robots.txt");
  must(robotsRes.status === 200, `robots.txt -> ${robotsRes.status}`);
  must(
    String(robotsRes.headers.get("content-type") || "").includes("text/plain"),
    `robots.txt served as ${robotsRes.headers.get("content-type")}`,
  );
  const robots = await robotsRes.text();
  must(/^User-agent:\s*\*$/im.test(robots), "robots.txt missing User-agent: *");
  must(/^Allow:\s*\/$/im.test(robots), "robots.txt does not allow /");
  must(
    robots.includes(`Sitemap: ${ORIGIN}/sitemap.xml`),
    `robots.txt sitemap is not ${ORIGIN}/sitemap.xml`,
  );

  const sitemapRes = await fetchT(BASE + "/sitemap.xml");
  must(sitemapRes.status === 200, `sitemap.xml -> ${sitemapRes.status}`);
  const sitemapType = String(sitemapRes.headers.get("content-type") || "").toLowerCase();
  must(sitemapType.includes("xml"), `sitemap.xml served as ${sitemapType}`);
  const problems = sitemapCoverageProblems(await sitemapRes.text(), ORIGIN, INDEXABLE_ROUTES);
  must(problems.length === 0, problems.join("; "));
  return `${INDEXABLE_ROUTES.length} canonical URLs`;
});

await check("meta: every indexable route has a self-canonical URL", async () => {
  const { problems, unavailable } = canonicalRouteProblems(routeHtml, ORIGIN, INDEXABLE_ROUTES);
  must(problems.length === 0, problems.join("; "));
  const checked = INDEXABLE_ROUTES.length - unavailable.length;
  return unavailable.length
    ? `${checked} self-canonicals; ${unavailable.length} unavailable (covered by route check)`
    : `${checked} self-canonicals`;
});

await check("meta: Google Search Console ownership token", async () => {
  const token = extractGoogleSiteVerification(homeHtml);
  must(
    token === GOOGLE_SITE_VERIFICATION,
    `verification token was ${token || "missing"}`,
  );
  return "exact token present";
});

await check("trailingSlash: /method -> 301 /method/", async () => {
  const res = await fetchT(BASE + "/method", { redirect: "manual" });
  const loc = res.headers.get("location") || "";
  must(res.status >= 300 && res.status < 400, `expected 3xx, got ${res.status}`);
  must(loc.endsWith("/method/"), `Location was "${loc}"`);
  return `${res.status} -> ${loc}`;
});

await check("unknown path -> 404 page", async () => {
  const res = await fetchT(BASE + "/__deuce_no_such_path_" + Date.now() + "/");
  must(res.status === 404, `expected 404, got ${res.status}`);
  const body = (await res.text()).toLowerCase();
  must(body.includes("could not be found") || body.includes("404"), "404 body marker missing");
  return "404 served";
});

await check("cache-control: mutable content not stored, hashed static immutable", async () => {
  const dataRes = await fetchT(BASE + "/data/health.json");
  const dataCc = dataRes.headers.get("cache-control");
  must(mutableCacheControlOk(dataCc), `data/health.json can be stored (got "${dataCc}")`);

  const homeRes = await fetchT(BASE + "/");
  const homeCc = homeRes.headers.get("cache-control");
  must(mutableCacheControlOk(homeCc), `/ HTML can be stored (got "${homeCc}")`);

  const asset = extractHashedAsset(homeHtml, "js");
  must(asset, "no hashed /_next/static js asset found in home HTML");
  const assetRes = await fetchT(BASE + asset);
  const cc = parseCacheControl(assetRes.headers.get("cache-control"));
  must(cc.immutable, `hashed asset ${asset} not immutable (got "${assetRes.headers.get("cache-control")}")`);
  return "no-store/immutable split correct";
});

await check("MIME: js/css/json not falling through to html", async () => {
  const js = extractHashedAsset(homeHtml, "js");
  const css = extractHashedAsset(homeHtml, "css");
  must(js, "no js asset to MIME-check");
  const jsRes = await fetchT(BASE + js);
  must(contentTypeOk(jsRes.headers.get("content-type"), js), `js served as ${jsRes.headers.get("content-type")}`);
  if (css) {
    const cssRes = await fetchT(BASE + css);
    must(contentTypeOk(cssRes.headers.get("content-type"), css), `css served as ${cssRes.headers.get("content-type")}`);
  }
  const jsonRes = await fetchT(BASE + "/data/health.json");
  must(contentTypeOk(jsonRes.headers.get("content-type"), "/data/health.json"), `json served as ${jsonRes.headers.get("content-type")}`);
  return `js${css ? "/css" : ""}/json MIME ok`;
});

await check("scroll shell: wheel input reaches the document scroller", async () => {
  const css = extractHashedAsset(homeHtml, "css");
  must(css, "no hashed /_next/static css asset found in home HTML");
  const res = await fetchT(BASE + css, { cache: "no-store" });
  must(res.status === 200, `${css} -> ${res.status}`);
  const problems = scrollShellProblems(await res.text());
  must(problems.length === 0, problems.join("; "));
  return "root-owned vertical scroll contract";
});

await check(
  EXPECT_GENERATED_AT ? `freshness: live generatedAt == ${EXPECT_GENERATED_AT}` : "freshness: live health.json ok",
  async () => {
    let last = "";
    for (let i = 0; i < FRESH_TRIES; i++) {
      const res = await fetchT(BASE + "/data/health.json");
      const j = await res.json();
      last = j.generatedAt;
      if (healthArtifactOk(j, EXPECT_GENERATED_AT)) {
        return `generatedAt ${j.generatedAt} (serving contract ok; data ok=${j.ok})`;
      }
      if (i < FRESH_TRIES - 1) await sleep(FRESH_DELAY_MS);
    }
    throw new Error(`stale: live generatedAt "${last}" != expected "${EXPECT_GENERATED_AT}" after ${FRESH_TRIES} tries`);
  },
);

await check("release lineage: exact accepted artifact graph", async () => {
  const expectedHealth = loadExpectedHealth(EXPECTED_HEALTH_PATH);
  // Local lineage cannot change during CDN propagation, so reject it before the retry window.
  expectedArtifactLineage(expectedHealth);
  let lastError;
  for (let attempt = 0; attempt < FRESH_TRIES; attempt++) {
    try {
      const result = await verifyArtifactLineageRelease({
        base: BASE,
        expectedHealth,
        fetcher: fetchT,
      });
      return `${result.artifactCount} exact artifact(s), ${result.absentPathCount} known absent path(s), release ${result.releaseId}`;
    } catch (error) {
      lastError = error;
      if (attempt < FRESH_TRIES - 1) await sleep(FRESH_DELAY_MS);
    }
  }
  throw lastError;
});

await check("coverage: every begun event is on the live site exactly once", async () => {
  let last = [];
  for (let i = 0; i < FRESH_TRIES; i++) {
    const healthRes = await fetchT(BASE + "/data/health.json", { cache: "no-store" });
    must(healthRes.status === 200, `health.json -> ${healthRes.status}`);
    const health = await healthRes.json();
    last = [];
    for (const tour of ["atp", "wta"]) {
      const path = `/data/${tour}/tournaments.json`;
      const res = await fetchT(BASE + path, { cache: "no-store" });
      if (res.status !== 200) {
        last.push(`${path} -> ${res.status}`);
        continue;
      }
      last.push(...coverageProblems(health, tour, await res.json()));
    }
    if (last.length === 0) {
      const n = ["atp", "wta"].reduce(
        (sum, tour) => sum + (health?.eventCoverage?.[tour]?.expectedKeys?.length || 0), 0,
      );
      return `${n} begun event(s), exact membership`;
    }
    if (i < FRESH_TRIES - 1) await sleep(FRESH_DELAY_MS);
  }
  throw new Error(last.join("; "));
});

await check("bracket provenance: one draw source per ESPN event", async () => {
  const problems = [];
  let checked = 0;
  for (const tour of ["atp", "wta"]) {
    const path = `/data/${tour}/brackets.json`;
    const res = await fetchT(BASE + path, { cache: "no-store" });
    if (res.status !== 200) {
      problems.push(`${path} -> ${res.status}`);
      continue;
    }
    const brackets = await res.json();
    problems.push(...drawSourceProblems(brackets).map((problem) => `${tour}: ${problem}`));
    checked += Array.isArray(brackets) ? brackets.length : 0;
  }
  must(problems.length === 0, problems.join("; "));
  return `${checked} bracket source attachment(s) unique`;
});

await check("sharded artifacts: every index reference is served at one generation", async () => {
  let checked = 0;
  for (const tour of ["atp", "wta"]) {
    const matrixRes = await fetchT(BASE + `/data/${tour}/matrix-index.json`, { cache: "no-store" });
    const profileRes = await fetchT(BASE + `/data/${tour}/profile-index.json`, { cache: "no-store" });
    const scenarioRes = await fetchT(BASE + `/data/${tour}/scenario-index.json`, { cache: "no-store" });
    const upcomingRes = await fetchT(BASE + `/data/${tour}/upcoming-index.json`, { cache: "no-store" });
    must(matrixRes.status === 200, `${tour}/matrix-index.json -> ${matrixRes.status}`);
    must(profileRes.status === 200, `${tour}/profile-index.json -> ${profileRes.status}`);
    must(scenarioRes.status === 200, `${tour}/scenario-index.json -> ${scenarioRes.status}`);
    must(upcomingRes.status === 200, `${tour}/upcoming-index.json -> ${upcomingRes.status}`);
    const matrix = await matrixRes.json();
    const profiles = await profileRes.json();
    const scenarios = await scenarioRes.json();
    const upcoming = await upcomingRes.json();
    const { problems, files } = artifactIndexRefs(matrix, profiles, scenarios, upcoming);
    must(problems.length === 0, `${tour}: ${problems.join("; ")}`);
    for (let start = 0; start < files.length; start += 24) {
      const batch = files.slice(start, start + 24);
      const responses = await Promise.all(batch.map(async (ref) => {
        const path = `/data/${tour}/${ref.file}`;
        const res = await fetchT(BASE + path, { cache: "no-store" });
        if (res.status !== 200) return `${path} -> ${res.status}`;
        if (!contentTypeOk(res.headers.get("content-type"), path)) {
          return `${path} served as ${res.headers.get("content-type")}`;
        }
        const payload = await res.json();
        if (payload?.generation !== ref.generation) return `${path} generation mismatch`;
        if (ref.kind === "profile" && payload?.name !== ref.name) return `${path} player mismatch`;
        if (ref.kind === "scenario" && payload?.event?.name !== ref.name) return `${path} event mismatch`;
        if ((ref.kind === "upcoming-event" || ref.kind === "upcoming-evidence")
            && payload?.event?.name !== ref.name) return `${path} upcoming event mismatch`;
        if (ref.kind === "matrix") {
          const components = Object.keys(payload?.components || {}).sort().join(",");
          if (components !== "combiner,eloBlend,pointModel") return `${path} component set ${components}`;
        }
        return "";
      }));
      const bad = responses.filter(Boolean);
      must(bad.length === 0, bad.join("; "));
      checked += batch.length;
    }
  }
  return `${checked} referenced shard(s)`;
});

await check("player profiles: fail-closed links + responsive dossier contract", async () => {
  const res = await fetchT(BASE + "/player/", { cache: "no-store" });
  must(res.status === 200, `/player/ -> ${res.status}`);
  const html = await res.text();
  must(hasProfileContract(html), "player profile contract marker missing (stale or partial deploy)");
  return "fail-closed-links+single-radar+mobile-contained+expectation-v3";
});

await check("match center: upcoming Playing Style drill-in contract", async () => {
  const html = routeHtml.get("/matches/");
  if (!html) return "route unavailable (covered by route check)";
  must(hasMatchCenterContract(html), "match-center contract marker missing (stale or partial deploy)");
  return "upcoming-style-links+forecast-history+watch+evidence+live-dedupe-v4";
});

await check("live/scheduled state: active matches excluded from upcoming surfaces", async () => {
  const missing = ["/", "/matches/"].filter((route) => {
    const html = routeHtml.get(route);
    return html && !hasLiveScheduleContract(html);
  });
  must(missing.length === 0, `live-schedule contract marker missing on ${missing.join(", ")}`);
  return "exact event id + unordered player pair on overview/match center";
});

await check("home discovery: current tournaments open the bracket lab", async () => {
  if (!homeHtml) return "route unavailable (covered by route check)";
  must(hasHomeBracketEntryContract(homeHtml), "home bracket-entry contract marker missing (stale or partial deploy)");
  return "stable event id + actual/forecast/scenario links";
});

await check("prediction explanation: grouped evidence is explicitly non-causal", async () => {
  const html = routeHtml.get("/predict/");
  if (!html) return "route unavailable (covered by route check)";
  must(hasPredictionExplanationContract(html), "prediction-explanation contract marker missing (stale or partial deploy)");
  return "grouped-evidence-not-causation-v2";
});

await check("bracket lab: actual draw + exact forecast/scenario contract", async () => {
  const html = routeHtml.get("/bracket/");
  if (!html) return "route unavailable (covered by route check)";
  must(hasBracketLabContract(html), "bracket lab contract marker missing (stale or partial deploy)");
  return "actual+forecast+scenario-exact-v1";
});

await check("expectation artifacts: live summary arithmetic", async () => {
  const problems = [];
  for (const tour of ["atp", "wta"]) {
    const path = `/data/${tour}/performance.json`;
    const res = await fetchT(BASE + path, { cache: "no-store" });
    if (res.status !== 200) problems.push(`${path} -> ${res.status}`);
    else problems.push(...performanceArtifactProblems(await res.json()).map((problem) => `${tour}: ${problem}`));
  }
  must(problems.length === 0, problems.join("; "));
  return "ATP/WTA performance summaries consistent";
});

await check("meta: og:image absolute + on origin", async () => {
  const og = extractOgImage(homeHtml);
  must(og, "no og:image meta found");
  must(isAbsoluteOnOrigin(og, ORIGIN), `og:image "${og}" not absolute on ${ORIGIN}`);
  return og;
});

// ---- report -----------------------------------------------------------------
const failed = results.filter((r) => !r.ok);
console.log(`\nDeploy verification — ${BASE}\n`);
for (const r of results) console.log(`${r.ok ? "ok  " : "FAIL"} ${r.name}${r.detail ? `  (${r.detail})` : ""}`);
console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
if (failed.length) {
  console.error(`\n${failed.length} FAILED:`);
  for (const r of failed) console.error(`  - ${r.name}: ${r.detail}`);
}
return failed.length ? 1 : 0;
}

const entrypoint = process.argv[1] ? resolve(process.argv[1]) : "";
if (entrypoint === fileURLToPath(import.meta.url)) {
  process.exit(await main());
}
