import type { MatrixShard } from "@/lib/matrix";

export const EVIDENCE_LABELS = {
  surfaceElo: "Surface Elo",
  serveReturn: "Serve / return",
  form: "Recent form",
  rest: "Rest & workload",
  home: "Home advantage",
  h2h: "Head-to-head",
  style: "Playing style",
} as const;

export type EvidenceKey = keyof typeof EVIDENCE_LABELS;
export type EvidenceSignal = {
  key: EvidenceKey;
  available: boolean;
  supports: string | null;
  impactPp: number;
  facts?: Record<string, unknown>;
};
export type PredictionEvidenceData = {
  schema: "evidence-v1";
  playerA: string;
  playerB: string;
  asOf?: string;
  probabilityA?: number;
  signals: EvidenceSignal[];
  note?: string;
};

const KEYS = Object.keys(EVIDENCE_LABELS) as EvidenceKey[];

function upperIndex(size: number, i: number, j: number): { index: number; sign: number } | null {
  if (i === j || i < 0 || j < 0 || i >= size || j >= size) return null;
  const left = Math.min(i, j);
  const right = Math.max(i, j);
  return {
    index: left * (2 * size - left - 1) / 2 + right - left - 1,
    sign: i < j ? 1 : -1,
  };
}

function encodedValue(
  value: number[][] | number[] | undefined,
  size: number,
  i: number,
  j: number,
  signed: boolean,
  packed: boolean,
): number | undefined {
  if (!value) return undefined;
  if (!packed) {
    const row = value[i];
    return Array.isArray(row) && typeof row[j] === "number" ? row[j] : undefined;
  }
  const position = upperIndex(size, i, j);
  if (!position) return signed ? 0 : undefined;
  const raw = value[position.index];
  return typeof raw === "number" ? raw * (signed ? position.sign : 1) : undefined;
}

/** Re-orient signed evidence while keeping the supported player's actual name stable. */
export function orientEvidence(
  evidence: PredictionEvidenceData,
  flip: boolean,
): PredictionEvidenceData {
  if (!flip) return evidence;
  const swap = (facts: Record<string, unknown>, left: string, right: string) => {
    if (left in facts || right in facts) [facts[left], facts[right]] = [facts[right], facts[left]];
  };
  const signals = evidence.signals.map((signal) => {
    const facts = { ...(signal.facts ?? {}) };
    for (const [left, right] of [
      ["a", "b"], ["form90A", "form90B"], ["recentWinRateA", "recentWinRateB"],
      ["daysSinceA", "daysSinceB"], ["workloadA", "workloadB"], ["winsA", "winsB"],
      ["surfaceWinsA", "surfaceWinsB"], ["playerAHome", "playerBHome"],
    ]) swap(facts, left, right);
    if (typeof facts.pointProbabilityA === "number") {
      facts.pointProbabilityA = Math.round((1 - facts.pointProbabilityA) * 10_000) / 10_000;
    }
    for (const key of ["gap", "serveEdge", "returnEdge", "diff"]) {
      if (typeof facts[key] === "number") facts[key] = -facts[key];
    }
    if (Array.isArray(facts.contrasts)) {
      facts.contrasts = facts.contrasts.map((item) => {
        if (!item || typeof item !== "object") return item;
        const contrast = { ...(item as Record<string, unknown>) };
        [contrast.a, contrast.b] = [contrast.b, contrast.a];
        if (typeof contrast.diff === "number") contrast.diff = -contrast.diff;
        return contrast;
      });
    }
    return { ...signal, impactPp: -signal.impactPp, facts };
  });
  return {
    ...evidence,
    playerA: evidence.playerB,
    playerB: evidence.playerA,
    probabilityA: evidence.probabilityA == null
      ? undefined : Math.round((1 - evidence.probabilityA) * 10_000) / 10_000,
    signals,
  };
}

/** Evidence available in the selected lazy matrix shard for an arbitrary matchup. */
export function matrixEvidence(
  shard: MatrixShard | null,
  a: number,
  b: number,
): PredictionEvidenceData | null {
  if (!shard?.evidence || a === b) return null;
  const playerA = shard.players[a];
  const playerB = shard.players[b];
  if (!playerA || !playerB) return null;
  const packed = shard.evidence.encoding === "upper-triangle-bps-v1";
  const signals = KEYS.map((key): EvidenceSignal => {
    const effect = encodedValue(
      shard.evidence?.effects?.[key], shard.players.length, a, b, true, packed,
    );
    const conditional = encodedValue(
      shard.evidence?.available?.[key], shard.players.length, a, b, false, packed,
    );
    const available = key === "home"
      ? Boolean(shard.evidence?.homeAvailable)
      : conditional == null ? true : Boolean(conditional);
    const impactPp = typeof effect === "number"
      ? packed ? effect / 100 : Math.round(effect * 10_000) / 100
      : 0;
    return {
      key,
      available,
      supports: impactPp > 0.005 ? playerA : impactPp < -0.005 ? playerB : null,
      impactPp,
    };
  }).sort((left, right) => {
    if (left.available !== right.available) return left.available ? -1 : 1;
    return Math.abs(right.impactPp) - Math.abs(left.impactPp)
      || left.key.localeCompare(right.key);
  });
  return {
    schema: "evidence-v1",
    playerA,
    playerB,
    signals,
    note: "Grouped model sensitivity; evidence, not causation; groups need not add up.",
  };
}
