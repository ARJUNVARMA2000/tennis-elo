import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";
import {
  parseCacheControl,
  expectedMimeFor,
  contentTypeOk,
  extractHashedAsset,
  isAbsoluteOnOrigin,
  freshnessOk,
  healthArtifactOk,
  extractOgImage,
  extractCanonical,
  extractGoogleSiteVerification,
  sitemapCoverageProblems,
  coverageProblems,
  drawSourceProblems,
  hasProfileContract,
  hasMatchCenterContract,
  hasLiveScheduleContract,
  hasHomeBracketEntryContract,
  hasPredictionExplanationContract,
  hasBracketLabContract,
  performanceArtifactProblems,
  scrollShellProblems,
  canonicalRouteProblems,
  fetchWithRetry,
  mutableCacheControlOk,
  artifactIndexRefs,
} from "@/scripts/verify-deploy-lib.mjs";
import {
  LINEAGE_FORBIDDEN_PATHS,
  expectedArtifactLineage,
  parseStrictLineageJson,
  validateArtifactLineageManifest,
  verifyArtifactLineageRelease,
} from "@/scripts/verify-deploy.mjs";

type ReleaseRecord = {
  path: string;
  role: string;
  bytes: number;
  sha256: string;
  producer: string;
  sourceFingerprint: string;
  predictorArtifactId: string;
  originRelease: string;
};

type LineageFixture = {
  health: {
    generatedAt: string;
    artifactLineage: {
      schema: string;
      status: string;
      releaseId: string;
      manifestSha256: string;
      tours: string[];
    };
  };
  manifest: {
    schema: string;
    releaseId: string;
    parent: string | null;
    createdAt: string;
    mode: string;
    artifacts: ReleaseRecord[];
  };
  manifestBytes: Uint8Array;
  files: Map<string, Uint8Array>;
};

const LINEAGE_RELEASE_ID = "11111111-1111-4111-8111-111111111111";
const LINEAGE_PREDICTOR_ID = "22222222-2222-4222-8222-222222222222";
const EXPECTED_FORBIDDEN_PATHS = [
  "/data/.last_full_run",
  "/data/release-accepted.private",
  "/data/atp/predictor.pkl",
  "/data/atp/predictor.pkl.envelope",
  "/data/atp/predictor.pkl.envelope.pending",
  "/data/atp/stage-status.private",
  "/data/atp/stage-status.json",
  "/data/atp/health-source.json",
  "/data/atp/tournament_draws-status.private",
  "/data/wta/predictor.pkl",
  "/data/wta/predictor.pkl.envelope",
  "/data/wta/predictor.pkl.envelope.pending",
  "/data/wta/stage-status.private",
  "/data/wta/stage-status.json",
  "/data/wta/health-source.json",
  "/data/wta/tournament_draws-status.private",
];
const EXPECTED_OPTIONAL_PATHS = ["atp", "wta"].flatMap((tour) => (
  ["accuracy.json", "kalshi.json", "market.json", "tennis-abstract.json", "track.json"]
    .map((filename) => `/data/${tour}/${filename}`)
));
const LINEAGE_ENCODER = new TextEncoder();
const LINEAGE_DECODER = new TextDecoder();
const lineageBytes = (value: unknown) => LINEAGE_ENCODER.encode(JSON.stringify(value));
const lineageDigest = (raw: Uint8Array) => createHash("sha256").update(raw).digest("hex");

const lineageFixed = [
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
];

function lineageRole(filename: string): string {
  if (lineageFixed.includes(filename)) return "public-core";
  if (filename === "matrix-index.json") return "matrix-index";
  if (filename === "profile-index.json") return "profile-index";
  if (filename === "scenario-index.json") return "scenario-index";
  if (filename === "upcoming-index.json") return "upcoming-index";
  if (filename.startsWith("matrix-")) return "matrix-shard";
  if (filename.startsWith("profile-")) return "profile-shard";
  if (filename.startsWith("scenario-")) return "scenario-shard";
  if (filename.startsWith("upcoming-event-")) return "upcoming-event";
  if (filename.startsWith("upcoming-evidence-")) return "upcoming-evidence";
  return "evaluation";
}

function buildLineageFixture(extraMatrixShards = 0): LineageFixture {
  const files = new Map<string, Uint8Array>();
  for (const tour of ["atp", "wta"]) {
    for (const filename of lineageFixed) {
      files.set(`${tour}/${filename}`, lineageBytes({ tour, filename }));
    }
    const matrices = [
      "matrix-hard-bo3.json",
      ...Array.from({ length: extraMatrixShards }, (_, i) => `matrix-extra-${String(i).padStart(3, "0")}.json`),
    ];
    files.set(`${tour}/matrix-index.json`, lineageBytes({
      generation: "generation-1",
      surfaces: {
        Hard: Object.fromEntries(matrices.map((filename, i) => [String(i + 3), filename])),
      },
    }));
    files.set(`${tour}/profile-index.json`, lineageBytes({
      generation: "generation-1",
      profiles: [{ name: "Player", file: "profile-0123456789abcdef.json" }],
    }));
    files.set(`${tour}/scenario-index.json`, lineageBytes({
      schemaVersion: 1,
      generation: "generation-1",
      events: [{ name: "Open", file: "scenario-open.json" }],
    }));
    files.set(`${tour}/upcoming-index.json`, lineageBytes({
      schema: "upcoming-v2",
      schemaVersion: 2,
      generation: "generation-1",
      highlights: [],
      events: [{
        name: "Open",
        file: "upcoming-event-open.json",
        evidenceFile: "upcoming-evidence-open.json",
      }],
    }));
    for (const filename of matrices) {
      files.set(`${tour}/${filename}`, lineageBytes({ generation: "generation-1", filename }));
    }
    files.set(`${tour}/profile-0123456789abcdef.json`, lineageBytes({
      generation: "generation-1", name: "Player",
    }));
    files.set(`${tour}/scenario-open.json`, lineageBytes({
      generation: "generation-1", event: { name: "Open" },
    }));
    files.set(`${tour}/upcoming-event-open.json`, lineageBytes({
      generation: "generation-1", event: { name: "Open" },
    }));
    files.set(`${tour}/upcoming-evidence-open.json`, lineageBytes({
      generation: "generation-1", event: { name: "Open" },
    }));
    for (const filename of [
      "accuracy.json",
      "kalshi.json",
      "market.json",
      "tennis-abstract.json",
      "track.json",
    ]) {
      files.set(`${tour}/${filename}`, lineageBytes({ tour, filename, optional: true }));
    }
  }

  const artifacts = [...files.entries()].map(([path, raw]) => ({
    path,
    role: lineageRole(path.split("/")[1]),
    bytes: raw.byteLength,
    sha256: lineageDigest(raw),
    producer: "pipeline.export:v1",
    sourceFingerprint: `sf1:${"a".repeat(64)}`,
    predictorArtifactId: LINEAGE_PREDICTOR_ID,
    originRelease: LINEAGE_RELEASE_ID,
  })).sort((a, b) => a.path.localeCompare(b.path));
  const manifest = {
    schema: "artifact-lineage-v1",
    releaseId: LINEAGE_RELEASE_ID,
    parent: null,
    createdAt: "2025-08-24T12:00:00.000000Z",
    mode: "full",
    artifacts,
  };
  const manifestBytes = lineageBytes(manifest);
  return {
    health: {
      generatedAt: "2026-08-24T12:00:00Z",
      artifactLineage: {
        schema: "artifact-lineage-v1",
        status: "accepted",
        releaseId: LINEAGE_RELEASE_ID,
        manifestSha256: lineageDigest(manifestBytes),
        tours: ["atp", "wta"],
      },
    },
    manifest,
    manifestBytes,
    files,
  };
}

function withLineageManifest(
  fixture: LineageFixture,
  mutate: (manifest: LineageFixture["manifest"]) => void,
): LineageFixture {
  const manifest = structuredClone(fixture.manifest);
  mutate(manifest);
  const manifestBytes = lineageBytes(manifest);
  return {
    ...fixture,
    manifest,
    manifestBytes,
    health: {
      generatedAt: fixture.health.generatedAt,
      artifactLineage: {
        ...fixture.health.artifactLineage,
        manifestSha256: lineageDigest(manifestBytes),
      },
    },
  };
}

function lineageFetcher(
  fixture: LineageFixture,
  overrides: Map<string, { body?: Uint8Array; status?: number; contentType?: string }> = new Map(),
) {
  const calls: string[] = [];
  const requests: { path: string; init?: RequestInit }[] = [];
  const fetcher = async (input: string | URL | Request, init?: RequestInit): Promise<Response> => {
    const url = new URL(typeof input === "string" || input instanceof URL ? input : input.url);
    calls.push(url.pathname);
    requests.push({ path: url.pathname, init });
    if (url.pathname === "/data/health.json") {
      const override = overrides.get("health.json") || {};
      return new Response(new Uint8Array(override.body || lineageBytes(fixture.health)).buffer, {
        status: override.status || 200,
        headers: { "content-type": override.contentType || "application/json" },
      });
    }
    if (url.pathname === "/data/release-manifest.json") {
      const override = overrides.get("release-manifest.json") || {};
      return new Response(new Uint8Array(override.body || fixture.manifestBytes).buffer, {
        status: override.status || 200,
        headers: { "content-type": override.contentType || "application/json" },
      });
    }
    const path = url.pathname.replace(/^\/data\//, "");
    const override = overrides.get(path) || {};
    const body = override.body || fixture.files.get(path) || lineageBytes({ error: "missing" });
    return new Response(new Uint8Array(body).buffer, {
      status: override.status || (fixture.files.has(path) ? 200 : 404),
      headers: { "content-type": override.contentType || "application/json" },
    });
  };
  return { fetcher, calls, requests };
}

describe("accepted release lineage verification", () => {
  it.each([
    ["non-object health", null, /health is not an object/],
    ["missing summary", {}, /artifactLineage is missing or not an object/],
    ["non-object summary", { artifactLineage: [] }, /artifactLineage is missing or not an object/],
    ["non-accepted summary", { artifactLineage: { status: "legacy" } }, /status is legacy; expected accepted/],
  ])("rejects %s", async (_label, health, message) => {
    expect(() => expectedArtifactLineage(health)).toThrow(message);
    let fetched = false;
    await expect(verifyArtifactLineageRelease({
      base: "https://example.com",
      expectedHealth: health,
      fetcher: async () => {
        fetched = true;
        throw new Error("invalid local lineage must not fetch");
      },
    })).rejects.toThrow(message);
    expect(fetched).toBe(false);
  });

  it("rejects malformed accepted summaries", () => {
    expect(() => expectedArtifactLineage({
      artifactLineage: { status: "accepted", schema: "artifact-lineage-v1" },
    })).toThrow(/fields do not match/);
  });

  it("fetches every declared fixed, dynamic, and optional artifact with no sampling", async () => {
    const fixture = buildLineageFixture(35);
    const { fetcher, calls, requests } = lineageFetcher(fixture);
    const result = await verifyArtifactLineageRelease({
      base: "https://example.com/",
      expectedHealth: fixture.health,
      fetcher,
      observedAt: new Date("2026-08-24T12:01:00Z"),
    });

    const expectedPaths = fixture.manifest.artifacts.map((record) => record.path);
    expect(LINEAGE_FORBIDDEN_PATHS).toEqual(EXPECTED_FORBIDDEN_PATHS);
    expect(result).toMatchObject({
      artifactCount: expectedPaths.length,
      absentPathCount: EXPECTED_FORBIDDEN_PATHS.length,
      releaseId: LINEAGE_RELEASE_ID,
      fetchedPaths: expectedPaths,
      probedAbsentPaths: EXPECTED_FORBIDDEN_PATHS,
    });
    expect(new Set(calls.slice(2))).toEqual(
      new Set([
        ...EXPECTED_FORBIDDEN_PATHS,
        ...expectedPaths.map((path) => `/data/${path}`),
      ]),
    );
    expect(calls).toContain("/data/atp/brackets.json");
    expect(calls).toContain("/data/wta/tournaments.json");
    expect(calls).toContain("/data/atp/profile-0123456789abcdef.json");
    expect(calls).toContain("/data/wta/upcoming-evidence-open.json");
    expect(calls).toContain("/data/atp/kalshi.json");
    expect(calls).toContain("/data/wta/matrix-extra-034.json");
    expect(calls).toHaveLength(expectedPaths.length + EXPECTED_FORBIDDEN_PATHS.length + 2);
    for (const path of EXPECTED_FORBIDDEN_PATHS) {
      expect(requests.find((request) => request.path === path)?.init).toMatchObject({
        cache: "no-store",
        redirect: "manual",
      });
    }
  });

  it("requires exact 404s for every known optional artifact omitted from the manifest", async () => {
    const fixture = withLineageManifest(buildLineageFixture(), (manifest) => {
      manifest.artifacts = manifest.artifacts.filter(
        (record) => !EXPECTED_OPTIONAL_PATHS.includes(`/data/${record.path}`),
      );
    });
    for (const path of EXPECTED_OPTIONAL_PATHS) fixture.files.delete(path.replace(/^\/data\//, ""));
    const { fetcher, requests } = lineageFetcher(fixture);
    const result = await verifyArtifactLineageRelease({
      base: "https://example.com",
      expectedHealth: fixture.health,
      fetcher,
      observedAt: new Date("2026-08-24T12:01:00Z"),
    });

    expect(result.probedAbsentPaths).toEqual([
      ...EXPECTED_FORBIDDEN_PATHS,
      ...EXPECTED_OPTIONAL_PATHS,
    ]);
    expect(result.absentPathCount).toBe(
      EXPECTED_FORBIDDEN_PATHS.length + EXPECTED_OPTIONAL_PATHS.length,
    );
    for (const path of EXPECTED_OPTIONAL_PATHS) {
      expect(requests.find((request) => request.path === path)?.init).toMatchObject({
        cache: "no-store",
        redirect: "manual",
      });
    }
  });

  it("detects a stale undeclared optional artifact still served live", async () => {
    const leakedPath = "atp/market.json";
    const fixture = withLineageManifest(buildLineageFixture(), (manifest) => {
      manifest.artifacts = manifest.artifacts.filter((record) => record.path !== leakedPath);
    });
    const { fetcher } = lineageFetcher(fixture);
    await expect(verifyArtifactLineageRelease({
      base: "https://example.com",
      expectedHealth: fixture.health,
      fetcher,
    })).rejects.toThrow(
      /undeclared optional artifact \/data\/atp\/market\.json -> 200; expected 404/,
    );
  });

  it.each([
    ["published acceptance receipt", "release-accepted.private", 200],
    ["published predictor payload", "atp/predictor.pkl", 200],
    ["redirected stage receipt", "wta/stage-status.private", 302],
    ["access-controlled health source", "atp/health-source.json", 403],
    ["failed private probe", "wta/predictor.pkl.envelope.pending", 500],
  ])("rejects a non-404 %s", async (_label, leakedPath, status) => {
    const fixture = buildLineageFixture();
    const { fetcher } = lineageFetcher(fixture, new Map([[leakedPath, { status }]]));
    await expect(verifyArtifactLineageRelease({
      base: "https://example.com",
      expectedHealth: fixture.health,
      fetcher,
    })).rejects.toThrow(
      new RegExp(`forbidden private path /data/${leakedPath.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")} -> ${status}; expected 404`),
    );
  });

  it.each([
    ["first fixed", "atp/brackets.json"],
    ["last fixed", "wta/tournaments.json"],
    ["dynamic profile", "atp/profile-0123456789abcdef.json"],
    ["dynamic upcoming", "wta/upcoming-evidence-open.json"],
    ["optional evaluation", "atp/kalshi.json"],
    ["beyond the first fetch batch", "wta/matrix-extra-031.json"],
  ])("rejects an exact-length mutation in the %s artifact", async (_label, path) => {
    const fixture = buildLineageFixture(35);
    const original = fixture.files.get(path)!;
    const mutated = original.slice();
    mutated[Math.floor(mutated.length / 2)] ^= 1;
    const { fetcher } = lineageFetcher(fixture, new Map([[path, { body: mutated }]]));
    await expect(verifyArtifactLineageRelease({
      base: "https://example.com",
      expectedHealth: fixture.health,
      fetcher,
      observedAt: new Date("2026-08-24T12:01:00Z"),
    })).rejects.toThrow(new RegExp(`${path.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")} digest differs`));
  });

  it("rejects truncation, a missing artifact, and JSON MIME fall-through", async () => {
    const fixture = buildLineageFixture();
    const path = "atp/players.json";
    const raw = fixture.files.get(path)!;

    const truncated = lineageFetcher(fixture, new Map([[path, { body: raw.slice(0, -1) }]]));
    await expect(verifyArtifactLineageRelease({
      base: "https://example.com", expectedHealth: fixture.health, fetcher: truncated.fetcher,
    })).rejects.toThrow(/players\.json byte count differs/);

    const missing = lineageFetcher(fixture, new Map([[path, { status: 404 }]]));
    await expect(verifyArtifactLineageRelease({
      base: "https://example.com", expectedHealth: fixture.health, fetcher: missing.fetcher,
    })).rejects.toThrow(/players\.json -> 404/);

    const mime = lineageFetcher(fixture, new Map([[path, { contentType: "text\/html" }]]));
    await expect(verifyArtifactLineageRelease({
      base: "https://example.com", expectedHealth: fixture.health, fetcher: mime.fetcher,
    })).rejects.toThrow(/players\.json served as text\/html/);
  });

  it("rejects manifest MIME and exact-byte digest mismatches before trusting schema", async () => {
    const fixture = buildLineageFixture();
    const wrongDigest = structuredClone(fixture.health);
    wrongDigest.artifactLineage.manifestSha256 = "0".repeat(64);
    const served = lineageFetcher({ ...fixture, health: wrongDigest });
    await expect(verifyArtifactLineageRelease({
      base: "https://example.com", expectedHealth: wrongDigest, fetcher: served.fetcher,
    })).rejects.toThrow(/manifest digest differs/);

    const mime = lineageFetcher(fixture, new Map([
      ["release-manifest.json", { contentType: "text/html" }],
    ]));
    await expect(verifyArtifactLineageRelease({
      base: "https://example.com", expectedHealth: fixture.health, fetcher: mime.fetcher,
    })).rejects.toThrow(/release-manifest\.json served as text\/html/);
  });

  it("rejects a current deployed health stamp whose lineage summary is from another release", async () => {
    const fixture = buildLineageFixture();
    const deployedHealth = structuredClone(fixture.health);
    deployedHealth.artifactLineage.releaseId = "33333333-3333-4333-8333-333333333333";
    expect(deployedHealth.generatedAt).toBe(fixture.health.generatedAt);
    const served = lineageFetcher(fixture, new Map([
      ["health.json", { body: lineageBytes(deployedHealth) }],
    ]));
    await expect(verifyArtifactLineageRelease({
      base: "https://example.com", expectedHealth: fixture.health, fetcher: served.fetcher,
    })).rejects.toThrow(/deployed health artifactLineage differs from local accepted health/);
  });

  it.each([
    ["missing", {}, /artifactLineage is missing or not an object/],
    ["non-object", { artifactLineage: "accepted" }, /artifactLineage is missing or not an object/],
    ["non-accepted", { artifactLineage: { status: "legacy" } }, /status is legacy; expected accepted/],
  ])("rejects a deployed health document with %s lineage", async (_label, deployedHealth, message) => {
    const fixture = buildLineageFixture();
    const served = lineageFetcher(fixture, new Map([
      ["health.json", { body: lineageBytes(deployedHealth) }],
    ]));
    await expect(verifyArtifactLineageRelease({
      base: "https://example.com",
      expectedHealth: fixture.health,
      fetcher: served.fetcher,
    })).rejects.toThrow(message);
  });

  it.each([
    ["schema", (fixture: LineageFixture) => withLineageManifest(fixture, (manifest) => {
      manifest.schema = "artifact-lineage-v0";
    }), /schema is artifact-lineage-v0/],
    ["unsafe path", (fixture: LineageFixture) => withLineageManifest(fixture, (manifest) => {
      manifest.artifacts[0].path = "atp/../escape.json";
      manifest.artifacts.sort((a, b) => a.path.localeCompare(b.path));
    }), /unsafe declared artifact path/],
    ["duplicate path", (fixture: LineageFixture) => withLineageManifest(fixture, (manifest) => {
      manifest.artifacts.push(structuredClone(manifest.artifacts[0]));
      manifest.artifacts.sort((a, b) => a.path.localeCompare(b.path));
    }), /uniquely and exactly sorted/],
    ["missing WTA tour", (fixture: LineageFixture) => withLineageManifest(fixture, (manifest) => {
      manifest.artifacts = manifest.artifacts.filter((record) => record.path.startsWith("atp/"));
    }), /exactly ATP and WTA/],
    ["noncanonical timestamp", (fixture: LineageFixture) => withLineageManifest(fixture, (manifest) => {
      manifest.createdAt = "2025-08-24 12:00:00Z";
    }), /createdAt is not a bounded UTC timestamp/],
    ["parentless quick release", (fixture: LineageFixture) => withLineageManifest(fixture, (manifest) => {
      manifest.mode = "quick";
    }), /quick release manifest requires an accepted parent/],
    ["carried bootstrap artifact", (fixture: LineageFixture) => withLineageManifest(fixture, (manifest) => {
      manifest.artifacts[0].originRelease = "33333333-3333-4333-8333-333333333333";
    }), /bootstrap release artifacts must originate/],
  ])("rejects a bad %s contract", async (_label, makeFixture, message) => {
    const fixture = makeFixture(buildLineageFixture());
    const { fetcher } = lineageFetcher(fixture);
    await expect(verifyArtifactLineageRelease({
      base: "https://example.com",
      expectedHealth: fixture.health,
      fetcher,
      observedAt: new Date("2026-08-24T12:01:00Z"),
    })).rejects.toThrow(message);
  });

  it("rejects release identity and expected-tour mismatches from local health", async () => {
    const fixture = buildLineageFixture();
    const wrongRelease = structuredClone(fixture.health);
    wrongRelease.artifactLineage.releaseId = "33333333-3333-4333-8333-333333333333";
    const releaseFetch = lineageFetcher({ ...fixture, health: wrongRelease });
    await expect(verifyArtifactLineageRelease({
      base: "https://example.com", expectedHealth: wrongRelease, fetcher: releaseFetch.fetcher,
    })).rejects.toThrow(/releaseId differs from local health/);

    const wrongTours = structuredClone(fixture.health);
    wrongTours.artifactLineage.tours = ["atp"];
    expect(() => expectedArtifactLineage(wrongTours)).toThrow(/exactly atp,wta/);
  });

  it("rejects duplicate manifest keys, invalid bounds, and an index graph omission", async () => {
    const fixture = buildLineageFixture();
    const text = LINEAGE_DECODER.decode(fixture.manifestBytes);
    const duplicateBytes = LINEAGE_ENCODER.encode(
      text.replace('{"schema":', '{"schema":"artifact-lineage-v1","schema":'),
    );
    expect(() => parseStrictLineageJson(duplicateBytes, "release manifest")).toThrow(/duplicate object key/);

    const oversized = structuredClone(fixture.manifest);
    oversized.artifacts[0].bytes = 32 * 1024 * 1024 + 1;
    expect(() => validateArtifactLineageManifest(
      oversized,
      fixture.health.artifactLineage,
      new Date("2026-08-24T12:01:00Z"),
    )).toThrow(/invalid artifact byte count/);

    const omitted = withLineageManifest(fixture, (manifest) => {
      manifest.artifacts = manifest.artifacts.filter(
        (record) => record.path !== "atp/profile-0123456789abcdef.json",
      );
    });
    const omittedFetch = lineageFetcher(omitted);
    await expect(verifyArtifactLineageRelease({
      base: "https://example.com", expectedHealth: omitted.health, fetcher: omittedFetch.fetcher,
      observedAt: new Date("2026-08-24T12:01:00Z"),
    })).rejects.toThrow(/profile-0123456789abcdef\.json is not declared/);
  });
});

describe("artifactIndexRefs", () => {
  it("returns every safe matrix and profile shard reference", () => {
    const result = artifactIndexRefs(
      { generation: "g", surfaces: { Hard: { 3: "matrix-hard-bo3.json" } } },
      { generation: "g", profiles: [{ name: "A", file: "profile-a1.json" }] },
    );
    expect(result.problems).toEqual([]);
    expect(result.files.map((ref: { file: string }) => ref.file)).toEqual([
      "matrix-hard-bo3.json", "profile-a1.json",
    ]);
  });

  it("includes safe event scenario shards at the same generation", () => {
    const result = artifactIndexRefs(
      { generation: "g", surfaces: { Hard: { 3: "matrix-hard-bo3.json" } } },
      { generation: "g", profiles: [{ name: "A", file: "profile-a1.json" }] },
      { schemaVersion: 1, generation: "g", events: [{ name: "Open", file: "scenario-open.json" }] },
    );
    expect(result.problems).toEqual([]);
    expect(result.files.at(-1)).toMatchObject({ kind: "scenario", file: "scenario-open.json" });
  });

  it("includes both upcoming event and evidence shards", () => {
    const result = artifactIndexRefs(
      { generation: "g", surfaces: { Hard: { 3: "matrix-hard-bo3.json" } } },
      { generation: "g", profiles: [{ name: "A", file: "profile-a1.json" }] },
      { schemaVersion: 1, generation: "g", events: [] },
      { schema: "upcoming-v2", schemaVersion: 2, generation: "u", highlights: [], events: [
        { name: "Open", file: "upcoming-event-open.json", evidenceFile: "upcoming-evidence-open.json" },
      ] },
    );
    expect(result.problems).toEqual([]);
    expect(result.files.slice(-2)).toEqual([
      { kind: "upcoming-event", file: "upcoming-event-open.json", generation: "u", name: "Open" },
      { kind: "upcoming-evidence", file: "upcoming-evidence-open.json", generation: "u", name: "Open" },
    ]);
  });

  it("rejects unsafe, duplicate, and empty index references", () => {
    const unsafe = artifactIndexRefs(
      { generation: "g", surfaces: { Hard: { 3: "../matrix.json" } } },
      { generation: "", profiles: [] },
    );
    expect(unsafe.problems.join(" ")).toMatch(/unsafe|generation|no shards/);
  });
});

describe("fetchWithRetry", () => {
  it("recovers from a transient aborted request", async () => {
    let calls = 0;
    const sleeps: number[] = [];
    const response = await fetchWithRetry("https://example.com/schedule/", {}, {
      attempts: 2,
      delayMs: 7,
      timeoutMs: 100,
      fetchImpl: async () => {
        calls += 1;
        if (calls === 1) throw new DOMException("This operation was aborted", "AbortError");
        return new Response("ok");
      },
      sleep: async (ms) => { sleeps.push(ms); },
    });

    expect(await response.text()).toBe("ok");
    expect(calls).toBe(2);
    expect(sleeps).toEqual([7]);
  });

  it("reports the URL and attempt count when retries are exhausted", async () => {
    let calls = 0;
    await expect(fetchWithRetry("https://example.com/schedule/", {}, {
      attempts: 2,
      timeoutMs: 100,
      fetchImpl: async () => {
        calls += 1;
        throw new DOMException("This operation was aborted", "AbortError");
      },
      sleep: async () => {},
    })).rejects.toThrow(
      "GET https://example.com/schedule/ failed after 2 attempts: This operation was aborted",
    );
    expect(calls).toBe(2);
  });
});

describe("parseCacheControl", () => {
  it("flags immutable + long max-age (hashed static assets)", () => {
    const cc = parseCacheControl("public, max-age=31536000, immutable");
    expect(cc.immutable).toBe(true);
    expect(cc.mustRevalidate).toBe(false);
    expect(cc.noCache).toBe(false);
    expect(cc.noStore).toBe(false);
    expect(cc.maxAge).toBe(31536000);
  });
  it("flags no-cache + no-store (mutable data + HTML)", () => {
    const cc = parseCacheControl("no-cache, no-store");
    expect(cc.noCache).toBe(true);
    expect(cc.noStore).toBe(true);
    expect(cc.immutable).toBe(false);
    expect(cc.maxAge).toBeNull();
  });
  it("is case- and whitespace-insensitive and tolerates null", () => {
    expect(parseCacheControl("  PUBLIC,  IMMUTABLE ").immutable).toBe(true);
    expect(parseCacheControl(null)).toEqual({
      immutable: false,
      mustRevalidate: false,
      noCache: false,
      noStore: false,
      maxAge: null,
    });
  });
});

describe("mutableCacheControlOk", () => {
  it("requires the documented non-storage pair", () => {
    expect(mutableCacheControlOk("no-cache, no-store")).toBe(true);
    expect(mutableCacheControlOk("no-store")).toBe(false);
    expect(mutableCacheControlOk("no-cache")).toBe(false);
  });

  it("rejects the zero-age stored policy that produced stuck CDN keys", () => {
    expect(mutableCacheControlOk("public, max-age=0, must-revalidate")).toBe(false);
  });
});

describe("Firebase Hosting cache configuration", () => {
  it("does not store mutable content and keeps only hashed assets immutable", () => {
    const config = JSON.parse(readFileSync(new URL("../../firebase.json", import.meta.url), "utf8"));
    const rules = config.hosting.headers;
    expect(rules).toEqual([
      {
        source: "**",
        headers: [{ key: "Cache-Control", value: "no-cache, no-store" }],
      },
      {
        source: "/_next/static/**",
        headers: [{ key: "Cache-Control", value: "public, max-age=31536000, immutable" }],
      },
    ]);
  });
});

describe("expectedMimeFor", () => {
  it("maps extensions, stripping query/hash", () => {
    expect(expectedMimeFor("/_next/static/x.js")).toBe("javascript");
    expect(expectedMimeFor("/x.mjs")).toBe("javascript");
    expect(expectedMimeFor("/_next/static/x.css?v=1")).toBe("css");
    expect(expectedMimeFor("/data/health.json")).toBe("json");
  });
  it("treats routes (and trailing-slash paths) as html", () => {
    expect(expectedMimeFor("/")).toBe("html");
    expect(expectedMimeFor("/method/")).toBe("html");
  });
});

describe("contentTypeOk", () => {
  it("accepts either javascript spelling but rejects html fall-through", () => {
    expect(contentTypeOk("text/javascript; charset=utf-8", "/a.js")).toBe(true);
    expect(contentTypeOk("application/javascript", "/a.js")).toBe(true);
    // the classic Firebase misconfig: a static asset served as the SPA index
    expect(contentTypeOk("text/html; charset=utf-8", "/a.js")).toBe(false);
  });
  it("checks css and json", () => {
    expect(contentTypeOk("text/css", "/a.css")).toBe(true);
    expect(contentTypeOk("application/json", "/data/health.json")).toBe(true);
    expect(contentTypeOk("text/html", "/data/health.json")).toBe(false);
  });
});

describe("extractHashedAsset", () => {
  const html = `<link rel="stylesheet" href="/_next/static/chunks/3aeqklwtw9sws.css"/>` +
    `<script src="/_next/static/chunks/10qk6v6416kh8.js"></script>`;
  it("finds the first js and css under /_next/static", () => {
    expect(extractHashedAsset(html, "js")).toBe("/_next/static/chunks/10qk6v6416kh8.js");
    expect(extractHashedAsset(html, "css")).toBe("/_next/static/chunks/3aeqklwtw9sws.css");
  });
  it("returns null when absent or html is empty", () => {
    expect(extractHashedAsset("<p>no assets</p>", "js")).toBeNull();
    expect(extractHashedAsset("", "css")).toBeNull();
  });
});

describe("isAbsoluteOnOrigin", () => {
  const origin = "https://deuce-forecast.web.app";
  it("accepts absolute URLs on the origin", () => {
    expect(isAbsoluteOnOrigin("https://deuce-forecast.web.app/og.png", origin)).toBe(true);
    expect(isAbsoluteOnOrigin(origin, origin)).toBe(true);
  });
  it("rejects root-relative and other-origin (catches a SITE_URL regression)", () => {
    expect(isAbsoluteOnOrigin("/og.png", origin)).toBe(false);
    expect(isAbsoluteOnOrigin("https://arjunvarma2000.github.io/tennis-elo/og.png", origin)).toBe(false);
    expect(isAbsoluteOnOrigin("", origin)).toBe(false);
  });
});

describe("freshnessOk", () => {
  it("requires an exact match when an expected stamp is supplied", () => {
    expect(freshnessOk("2026-07-17T20:12:17Z", "2026-07-17T20:12:17Z")).toBe(true);
    expect(freshnessOk("2026-07-17T19:00:00Z", "2026-07-17T20:12:17Z")).toBe(false);
  });
  it("falls back to a presence check when no expected stamp is given", () => {
    expect(freshnessOk("2026-07-17T20:12:17Z", "")).toBe(true);
    expect(freshnessOk("", "")).toBe(false);
    expect(freshnessOk(null, undefined)).toBe(false);
  });
});

describe("healthArtifactOk", () => {
  it("accepts a fresh artifact even when data health has advisory findings", () => {
    expect(healthArtifactOk({ generatedAt: "2026-07-17T20:12:17Z", ok: false },
      "2026-07-17T20:12:17Z")).toBe(true);
  });
  it("rejects missing or stale artifact stamps", () => {
    expect(healthArtifactOk({ ok: true }, "2026-07-17T20:12:17Z")).toBe(false);
    expect(healthArtifactOk({ generatedAt: "old", ok: true },
      "2026-07-17T20:12:17Z")).toBe(false);
  });
});

describe("extractOgImage", () => {
  it("handles both attribute orders", () => {
    expect(
      extractOgImage(`<meta property="og:image" content="https://x/og.png"/>`),
    ).toBe("https://x/og.png");
    expect(
      extractOgImage(`<meta content="https://x/og.png" property="og:image"/>`),
    ).toBe("https://x/og.png");
  });
  it("returns null when there is no og:image", () => {
    expect(extractOgImage(`<meta name="twitter:card" content="summary"/>`)).toBeNull();
  });
});

describe("extractCanonical", () => {
  it("handles both attribute orders", () => {
    expect(
      extractCanonical(`<link rel="canonical" href="https://example.com/method/"/>`),
    ).toBe("https://example.com/method/");
    expect(
      extractCanonical(`<link href="https://example.com/method/" rel="canonical"/>`),
    ).toBe("https://example.com/method/");
  });

  it("returns null when no canonical exists", () => {
    expect(extractCanonical(`<link rel="icon" href="/icon.svg"/>`)).toBeNull();
  });
});

describe("canonicalRouteProblems", () => {
  const origin = "https://example.com";

  it("does not fabricate missing-tag failures for route HTML that was unavailable", () => {
    const html = new Map([
      ["/", `<link rel="canonical" href="${origin}/"/>`],
    ]);
    expect(canonicalRouteProblems(html, origin, ["/", "/schedule/", "/method/"])).toEqual({
      problems: [],
      unavailable: ["/schedule/", "/method/"],
    });
  });

  it("still fails a genuine missing or incorrect canonical in available HTML", () => {
    const html = new Map([
      ["/schedule/", "<title>Schedule</title>"],
      ["/method/", `<link rel="canonical" href="${origin}/wrong/"/>`],
    ]);
    const result = canonicalRouteProblems(html, origin, ["/schedule/", "/method/"]);
    expect(result.unavailable).toEqual([]);
    expect(result.problems).toEqual([
      `/schedule/ -> missing (expected ${origin}/schedule/)`,
      `/method/ -> ${origin}/wrong/ (expected ${origin}/method/)`,
    ]);
  });
});

describe("extractGoogleSiteVerification", () => {
  it("handles both attribute orders", () => {
    expect(
      extractGoogleSiteVerification(
        `<meta name="google-site-verification" content="verification-token"/>`,
      ),
    ).toBe("verification-token");
    expect(
      extractGoogleSiteVerification(
        `<meta content="verification-token" name="google-site-verification"/>`,
      ),
    ).toBe("verification-token");
  });

  it("returns null when the verification tag is absent", () => {
    expect(extractGoogleSiteVerification(`<meta name="description" content="DEUCE"/>`)).toBeNull();
  });
});

describe("sitemapCoverageProblems", () => {
  const origin = "https://deuce-forecast.web.app";
  const routes = ["/", "/rankings/", "/method/"];

  it("accepts the exact canonical route set", () => {
    const xml = `<?xml version="1.0"?><urlset>
      <url><loc>${origin}/</loc></url>
      <url><loc>${origin}/rankings/</loc></url>
      <url><loc>${origin}/method/</loc></url>
    </urlset>`;
    expect(sitemapCoverageProblems(xml, origin, routes)).toEqual([]);
  });

  it("reports missing, duplicate, off-origin, and unexpected URLs", () => {
    const xml = `<urlset>
      <url><loc>${origin}/</loc></url>
      <url><loc>${origin}/</loc></url>
      <url><loc>https://old.example/rankings/</loc></url>
      <url><loc>${origin}/health/</loc></url>
    </urlset>`;
    const problems = sitemapCoverageProblems(xml, origin, routes).join("; ");
    expect(problems).toContain("duplicate /");
    expect(problems).toContain("off-origin https://old.example/rankings/");
    expect(problems).toContain("unexpected /health/");
    expect(problems).toContain("missing /rankings/");
    expect(problems).toContain("missing /method/");
  });
});

describe("coverageProblems", () => {
  const health = {
    eventCoverage: {
      atp: {
        expectedKeys: ["espn:1-2026", "espn:2-2026"],
        shippedKeys: ["espn:1-2026", "espn:2-2026", "card:recent"],
      },
    },
  };

  it("accepts the exact freshly-built tournament membership", () => {
    const cards = [
      { name: "One", coverageKey: "espn:1-2026" },
      { name: "Two", coverageKey: "espn:2-2026" },
      { name: "Recent", coverageKey: "card:recent" },
    ];
    expect(coverageProblems(health, "atp", cards)).toEqual([]);
  });

  it("reports a missing begun event, a duplicate, and a stale extra card", () => {
    const cards = [
      { name: "One", coverageKey: "espn:1-2026" },
      { name: "One Again", coverageKey: "espn:1-2026" },
      { name: "Stale", coverageKey: "card:stale" },
    ];
    const problems = coverageProblems(health, "atp", cards).join("; ");
    expect(problems).toContain("missing expected espn:2-2026");
    expect(problems).toContain("duplicate espn:1-2026");
    expect(problems).toContain("membership differs");
  });
});

describe("drawSourceProblems", () => {
  it("accepts unique source ids and URLs", () => {
    expect(drawSourceProblems([
      { espnId: "188-2026", drawSource: "wikipedia", drawSourceId: "Wimbledon",
        drawSourceUrl: "https://en.wikipedia.org/wiki/Wimbledon" },
      { espnId: "189-2026", drawSource: "wikipedia", drawSourceId: "US Open",
        drawSourceUrl: "https://en.wikipedia.org/wiki/US_Open" },
    ])).toEqual([]);
  });

  it("rejects one source id or canonical URL on different ESPN events", () => {
    const problems = drawSourceProblems([
      { espnId: "188-2026", drawSource: "wikipedia", drawSourceId: "Wimbledon",
        drawSourceUrl: "https://en.wikipedia.org/wiki/Wimbledon?oldid=1" },
      { espnId: "189-2026", drawSource: "wikipedia", drawSourceId: "Wimbledon",
        drawSourceUrl: "https://en.wikipedia.org/wiki/Wimbledon#Draw" },
    ]).join("; ");
    expect(problems).toContain("drawSourceId wikipedia:wimbledon");
    expect(problems).toContain("drawSourceUrl https://en.wikipedia.org/wiki/Wimbledon");
    expect(problems).toContain("188-2026, 189-2026");
  });
});

describe("hasProfileContract", () => {
  it("requires the deployed player page to advertise fail-closed links and a mobile-contained dossier", () => {
    expect(hasProfileContract(
      `<main><div data-profile-contract="fail-closed-links+single-radar+mobile-contained+expectation-v3"></div></main>`,
    )).toBe(true);
    expect(hasProfileContract(`<main><div class="profiles"></div></main>`)).toBe(false);
    expect(hasProfileContract(
      `<div data-profile-contract="fail-closed-links+single-radar-v1"></div>`,
    )).toBe(false);
  });
});

describe("hasMatchCenterContract", () => {
  it("requires the deployed match center to advertise live/scheduled de-duplication", () => {
    expect(hasMatchCenterContract(
      `<main><div data-match-center-contract="upcoming-style-links+forecast-history+watch+evidence+live-dedupe-v4"></div></main>`,
    )).toBe(true);
    expect(hasMatchCenterContract(`<main><div class="matches"></div></main>`)).toBe(false);
    expect(hasMatchCenterContract(
      `<div data-match-center-contract="upcoming-style-links+forecast-history+watch+evidence-v3"></div>`,
    )).toBe(false);
  });

  it("pins the shared exact-event live/scheduled filter on each affected route", () => {
    expect(hasLiveScheduleContract(
      `<div data-live-schedule-contract="exact-event-unordered-pair-v1"></div>`,
    )).toBe(true);
    expect(hasLiveScheduleContract(
      `<div data-live-schedule-contract="player-pair-only-v0"></div>`,
    )).toBe(false);
  });

  it("pins the registry-backed home-to-bracket discovery contract", () => {
    expect(hasHomeBracketEntryContract(
      `<div data-home-bracket-entry-contract="stable-event-id+actual+forecast+scenario-v1"></div>`,
    )).toBe(true);
    expect(hasHomeBracketEntryContract(
      `<div data-home-bracket-entry-contract="event-name+actual-v0"></div>`,
    )).toBe(false);
  });

  it("pins the grouped, non-causal prediction-evidence route", () => {
    expect(hasPredictionExplanationContract(
      `<div data-prediction-explanation-contract="grouped-evidence-not-causation-v2"></div>`,
    )).toBe(true);
    expect(hasPredictionExplanationContract(`<div data-model-evidence="legacy"></div>`)).toBe(false);
  });
});

describe("new forecast surface contracts", () => {
  it("pins the exact three-view bracket lab", () => {
    expect(hasBracketLabContract(
      `<div data-bracket-lab-contract="actual+forecast+scenario-exact-v1"></div>`,
    )).toBe(true);
    expect(hasBracketLabContract(`<div data-bracket-lab-contract="actual-v1"></div>`)).toBe(false);
  });

  it("validates compact performance arithmetic", () => {
    expect(performanceArtifactProblems({ window: 10, players: [
      { name: "A", n: 2, wins: 1, expectedWins: 1.2, delta: -0.2 },
    ] })).toEqual([]);
    expect(performanceArtifactProblems({ window: 10, players: [
      { name: "A", n: 2, wins: 1, expectedWins: 1.2, delta: 0.8 },
    ] }).join(" ")).toContain("inconsistent performance summary");
  });
});

describe("scrollShellProblems", () => {
  it("accepts root-owned horizontal clipping without making body a scroll container", () => {
    expect(scrollShellProblems(`
      html { overflow-x: clip; overscroll-behavior: none; }
      body { min-height: 100dvh; }
    `)).toEqual([]);
  });

  it("rejects the deployed body overflow/overscroll combination that swallowed wheel input", () => {
    expect(scrollShellProblems(
      `html{overflow-x:clip}body{overflow-x:hidden;overscroll-behavior:none}`,
    )).toEqual([
      "body creates an overflow scroll container",
      "body blocks vertical overscroll chaining",
    ]);
  });

  it("rejects missing root clipping and vertical longhand containment", () => {
    expect(scrollShellProblems(`@layer base { body { overscroll-behavior-y: contain; } }`)).toEqual([
      "html is missing overflow-x: clip",
      "body blocks vertical overscroll chaining",
    ]);
  });
});
