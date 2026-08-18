"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { Tour } from "@/lib/tour";
import { playerHref, withTour } from "@/lib/url";
import { isRealSlot } from "@/lib/bracket";
import type { ScenarioArtifact, ScenarioNode, ScenarioResult } from "@/lib/scenario";
import { titleSwings } from "@/lib/scenario";

type Pick = (key: string, name: string | null) => void;

export default function ForecastBracket({
  artifact,
  result,
  interactive,
  forced,
  onPick,
  tour,
}: {
  artifact: ScenarioArtifact;
  result: ScenarioResult;
  interactive: boolean;
  forced: Record<string, string>;
  onPick: Pick;
  tour: Tour;
}) {
  const closing = result.nodes.slice(-3);
  const early = result.nodes.slice(0, -3);
  const champion = result.champion[0];
  const [focus, setFocus] = useState(champion?.name ?? artifact.players[0] ?? "");
  const focusName = result.reach[focus] ? focus : (champion?.name ?? artifact.players[0] ?? "");
  const swings = interactive ? titleSwings(artifact.base, result) : [];
  const openMatches = interactive ? result.nodes.flatMap((round) => round.matches).filter((node) => {
    const match = artifact.rounds[node.roundIndex]?.matches[node.matchIndex];
    return node.status !== "confirmed" && isRealSlot(match?.a) && isRealSlot(match?.b)
      && match.winner == null;
  }) : [];

  return (
    <div data-bracket-forecast-contract="exact-v1">
      {openMatches.length > 0 && (
        <div className="mb-4 rounded-lg border border-[var(--color-line)] bg-[var(--color-panel)] p-3">
          <div className="eyebrow">Set a current match result</div>
          <p className="mt-1 text-[10px] text-[var(--color-faint)]">
            Only real unresolved matchups can be fixed. Future pairings remain probabilistic.
          </p>
          <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {openMatches.map((node) => {
              const match = artifact.rounds[node.roundIndex].matches[node.matchIndex];
              const names = [match.a, match.b].filter(isRealSlot);
              return (
                <div key={node.key} className="rounded-md border border-[var(--color-line)] p-2">
                  <div className="mono mb-1 text-[8px] uppercase text-[var(--color-faint)]">{node.round}</div>
                  {names.map((name) => {
                    const probability = node.candidates.find((row) => row.name === name)?.p;
                    const selected = forced[node.key] === name;
                    return (
                      <button
                        key={name}
                        onClick={() => onPick(node.key, selected ? null : name)}
                        aria-pressed={selected}
                        className="grid w-full grid-cols-[1fr_auto] gap-2 rounded px-1.5 py-1 text-left text-[11px] hover:bg-[var(--color-accent-dim)]"
                        style={selected ? { color: "var(--color-accent)" } : undefined}
                      >
                        <span className="truncate">{name}</span>
                        <span className="mono">{selected ? "winner" : probability == null ? "—" : `${(probability * 100).toFixed(0)}%`}</span>
                      </button>
                    );
                  })}
                </div>
              );
            })}
          </div>
        </div>
      )}
      {early.length > 0 && (
        <div className="mb-3 flex min-w-max items-center gap-1.5 overflow-x-auto pb-1" aria-label="Draw minimap">
          <span className="eyebrow mr-1 text-[9px]">Draw map</span>
          {result.nodes.map((round, index) => (
            <div key={round.round} className="flex items-center gap-1.5">
              <span className="mono rounded-sm border border-[var(--color-line)] px-2 py-1 text-[9px] text-[var(--color-muted)]">
                {round.round} · {round.matches.length}
              </span>
              {index < result.nodes.length - 1 && <span className="text-[var(--color-faint)]">→</span>}
            </div>
          ))}
        </div>
      )}

      <div className="overflow-x-auto pb-2">
        <div className="relative mx-auto min-h-[450px] min-w-[920px] overflow-hidden rounded-lg border border-[var(--color-line)] bg-[var(--color-panel)] p-5">
          <ConnectorLines />
          {closing.length >= 3 ? (
            <SymmetricFinals
              rounds={closing}
              artifact={artifact}
              interactive={interactive}
              forced={forced}
              onPick={onPick}
              tour={tour}
            />
          ) : (
            <CompactFinals
              rounds={closing}
              artifact={artifact}
              interactive={interactive}
              forced={forced}
              onPick={onPick}
              tour={tour}
            />
          )}
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1.3fr)_minmax(260px,.7fr)]">
        <ReachFunnel result={result} focus={focusName} setFocus={setFocus} tour={tour} />
        <div className="panel-inset p-4">
          <div className="eyebrow">{interactive ? "Scenario impact" : "Title forecast"}</div>
          {interactive && Object.keys(forced).length ? (
            <div className="mt-3 space-y-2">
              {swings.map((row) => (
                <div key={row.name} className="grid grid-cols-[1fr_auto] items-center gap-3 text-xs">
                  <span className="truncate">{row.name}</span>
                  <span className="mono" style={{ color: row.delta >= 0 ? "var(--color-win)" : "var(--color-loss)" }}>
                    {row.delta >= 0 ? "+" : ""}{(row.delta * 100).toFixed(1)} pp
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="mt-3 space-y-2">
              {result.champion.slice(0, 5).map((row) => (
                <div key={row.name} className="grid grid-cols-[1fr_auto] items-center gap-3 text-xs">
                  <span className="truncate">{row.name}</span>
                  <span className="mono">{(row.p * 100).toFixed(1)}%</span>
                </div>
              ))}
            </div>
          )}
          <p className="mt-3 text-[10px] leading-relaxed text-[var(--color-faint)]">
            Exact propagation through this draw. Confirmed results are fixed; projected and user-forced paths are labeled separately.
          </p>
        </div>
      </div>
    </div>
  );
}

function SymmetricFinals({ rounds, ...props }: {
  rounds: ScenarioResult["nodes"];
  artifact: ScenarioArtifact;
  interactive: boolean;
  forced: Record<string, string>;
  onPick: Pick;
  tour: Tour;
}) {
  const [outer, inner, final] = rounds;
  const half = Math.ceil(outer.matches.length / 2);
  return (
    <div className="relative z-[1] grid h-full min-h-[405px] grid-cols-[1fr_.9fr_1.1fr_.9fr_1fr] gap-5">
      <RoundLane label={outer.round} nodes={outer.matches.slice(0, half)} side="left" {...props} />
      <RoundLane label={inner.round} nodes={inner.matches.slice(0, 1)} side="left" center {...props} />
      <div className="flex flex-col items-center justify-center">
        <div className="eyebrow mb-3 text-[10px]" style={{ color: "var(--color-champ)" }}>Championship</div>
        <NodeCard node={final.matches[0]} prominent {...props} />
      </div>
      <RoundLane label={inner.round} nodes={inner.matches.slice(1)} side="right" center {...props} />
      <RoundLane label={outer.round} nodes={outer.matches.slice(half)} side="right" {...props} />
    </div>
  );
}

function CompactFinals({ rounds, ...props }: {
  rounds: ScenarioResult["nodes"];
  artifact: ScenarioArtifact;
  interactive: boolean;
  forced: Record<string, string>;
  onPick: Pick;
  tour: Tour;
}) {
  return (
    <div className="relative z-[1] flex h-full min-h-[400px] items-stretch gap-6">
      {rounds.map((round) => <RoundLane key={round.round} label={round.round} nodes={round.matches} {...props} />)}
    </div>
  );
}

function RoundLane({ label, nodes, center = false, ...props }: {
  label: string;
  nodes: ScenarioNode[];
  side?: "left" | "right";
  center?: boolean;
  artifact: ScenarioArtifact;
  interactive: boolean;
  forced: Record<string, string>;
  onPick: Pick;
  tour: Tour;
}) {
  return (
    <div className="flex min-w-0 flex-1 flex-col">
      <div className="eyebrow text-center text-[9px]">{label}</div>
      <div className={`flex flex-1 flex-col ${center ? "justify-center" : "justify-around"} gap-3`}>
        {nodes.map((node) => <NodeCard key={node.key} node={node} {...props} />)}
      </div>
    </div>
  );
}

function NodeCard({ node, artifact, interactive, forced, onPick, tour, prominent = false }: {
  node?: ScenarioNode;
  artifact: ScenarioArtifact;
  interactive: boolean;
  forced: Record<string, string>;
  onPick: Pick;
  tour: Tour;
  prominent?: boolean;
}) {
  if (!node) return <div />;
  const shown = node.candidates.slice(0, prominent ? 3 : 2);
  const residual = Math.max(0, 1 - shown.reduce((sum, row) => sum + row.p, 0));
  const tooltip = nodeTooltip(node, artifact, shown, residual);
  const source = artifact.rounds[node.roundIndex]?.matches[node.matchIndex];
  const lockable = interactive && node.status !== "confirmed" && source?.winner == null
    && isRealSlot(source?.a) && isRealSlot(source?.b);
  return (
    <div
      className={`rounded-lg border bg-[var(--color-bg)] ${prominent ? "p-3 shadow-lg" : "p-2.5"}`}
      style={{ borderColor: node.status === "confirmed" ? "var(--color-win)" : node.status === "forced" ? "var(--color-accent)" : "var(--color-line)" }}
      title={tooltip}
    >
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <span className="mono text-[8px] uppercase tracking-wider text-[var(--color-faint)]">{node.status}</span>
        {interactive && forced[node.key] && (
          <button onClick={() => onPick(node.key, null)} className="mono text-[8px] uppercase text-[var(--color-accent)] hover:underline">
            change
          </button>
        )}
      </div>
      <div className="space-y-1">
        {shown.map((row, i) => {
          const content = (
            <>
              <span className="truncate">{row.name}</span>
              <span className="mono text-[10px]">{(row.p * 100).toFixed(row.p < 0.1 ? 1 : 0)}%</span>
            </>
          );
          return lockable && node.status === "projected" ? (
            <button
              key={row.name}
              onClick={() => onPick(node.key, row.name)}
              className="grid w-full grid-cols-[1fr_auto] gap-2 rounded px-1 py-0.5 text-left text-[11px] hover:bg-[var(--color-accent-dim)]"
              aria-label={`Force ${row.name} to win ${node.round}`}
            >{content}</button>
          ) : (
            <Link
              key={row.name}
              href={withTour(playerHref(row.name, tour), tour)}
              className={`grid grid-cols-[1fr_auto] gap-2 px-1 py-0.5 text-[11px] hover:underline ${i ? "text-[var(--color-muted)]" : ""}`}
            >{content}</Link>
          );
        })}
      </div>
      {residual > 0.0005 && <div className="mono mt-1 text-right text-[8px] text-[var(--color-faint)]">others {(residual * 100).toFixed(1)}%</div>}
    </div>
  );
}

function nodeTooltip(node: ScenarioNode, artifact: ScenarioArtifact, shown: { name: string; p: number }[], residual: number) {
  const lines = [`${node.round} · ${node.status}`, ...shown.map((row) => `${row.name}: ${(row.p * 100).toFixed(1)}%`),
    `Residual field: ${(residual * 100).toFixed(1)}%`];
  if (shown.length === 2) {
    const a = artifact.players.indexOf(shown[0].name);
    const b = artifact.players.indexOf(shown[1].name);
    if (a >= 0 && b >= 0) lines.push(
      `If they meet — Elo ${(artifact.matrices.eloBlend[a][b] * 100).toFixed(0)}%, ` +
      `points ${(artifact.matrices.pointModel[a][b] * 100).toFixed(0)}%, ` +
      `final ${(artifact.matrices.combiner[a][b] * 100).toFixed(0)}% for ${shown[0].name}`,
    );
  }
  return lines.join("\n");
}

function ReachFunnel({ result, focus, setFocus, tour }: {
  result: ScenarioResult;
  focus: string;
  setFocus: (name: string) => void;
  tour: Tour;
}) {
  const options = useMemo(() => result.champion.slice(0, 12), [result.champion]);
  const reach = result.reach[focus] ?? {};
  return (
    <div className="panel-inset p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="eyebrow">Round reach funnel</div>
          <Link href={withTour(playerHref(focus, tour), tour)} className="mt-1 block text-sm hover:underline">{focus}</Link>
        </div>
        <select
          value={focus}
          onChange={(event) => setFocus(event.target.value)}
          className="rounded border border-[var(--color-line)] bg-[var(--color-bg)] px-2 py-1 text-xs"
          aria-label="Funnel player"
        >
          {options.map((row) => <option key={row.name}>{row.name}</option>)}
        </select>
      </div>
      <div className="mt-4 flex items-end gap-1.5" style={{ minHeight: 140 }}>
        {Object.entries(reach).map(([round, p]) => (
          <div key={round} className="flex min-w-0 flex-1 flex-col items-center justify-end gap-1">
            <span className="mono text-[9px]">{(p * 100).toFixed(p < 0.1 ? 1 : 0)}%</span>
            <div className="w-full rounded-t-sm bg-[var(--color-accent)]" style={{ height: `${Math.max(3, p * 100)}px`, opacity: .35 + .65 * p }} />
            <span className="mono max-w-full truncate text-[8px] text-[var(--color-faint)]">{round}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ConnectorLines() {
  return (
    <svg className="pointer-events-none absolute inset-0 h-full w-full text-[var(--color-line)]" aria-hidden="true" preserveAspectRatio="none">
      <path d="M 175 115 H 245 V 225 H 335" fill="none" stroke="currentColor" />
      <path d="M 175 335 H 245 V 225" fill="none" stroke="currentColor" />
      <path d="M 335 225 H 435" fill="none" stroke="currentColor" />
      <path d="M 745 115 H 675 V 225 H 585" fill="none" stroke="currentColor" />
      <path d="M 745 335 H 675 V 225" fill="none" stroke="currentColor" />
      <path d="M 585 225 H 485" fill="none" stroke="currentColor" />
    </svg>
  );
}
