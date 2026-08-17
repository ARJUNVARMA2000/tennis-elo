import { useData } from "@/lib/tour";

export type PredictionComponent = "eloBlend" | "pointModel" | "combiner";

export type MatrixIndex = {
  generation: string;
  players: string[];
  formats: number[];
  surfaces: Record<string, Record<string, string>>;
};

export type MatrixShard = {
  generation: string;
  players: string[];
  surface: string;
  bestOf: number;
  components: Record<PredictionComponent, number[][]>;
};

export function useMatrixShard(surface: string, bestOf: number) {
  const indexState = useData<MatrixIndex>("matrix-index.json");
  const formats = indexState.data?.formats ?? [3];
  const format = formats.includes(bestOf) ? bestOf : formats[0];
  const byFormat = indexState.data?.surfaces?.[surface]
    ?? indexState.data?.surfaces?.Hard;
  const file = byFormat?.[String(format)] ?? byFormat?.[String(formats[0])] ?? "";
  const shardState = useData<MatrixShard>(file);
  return {
    index: indexState.data,
    shard: shardState.data,
    format,
    loading: indexState.loading || (!!file && shardState.loading),
    error: indexState.error || (!!file && shardState.error),
  };
}

export function matrixProbability(
  shard: MatrixShard | null,
  component: PredictionComponent,
  a: number,
  b: number,
): number | null {
  const value = shard?.components?.[component]?.[a]?.[b];
  return typeof value === "number" ? value : null;
}
