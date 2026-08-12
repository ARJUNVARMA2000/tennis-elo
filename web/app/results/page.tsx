"use client";

import { useMemo, useState } from "react";
import { useData, useTour } from "@/lib/tour";
import { PageHead, Loading, Reveal, CallCard, FilterChip } from "@/components/bits";
import { filterResults, resultCounts, type ResultFilter } from "@/lib/results";

type Fixture = {
  date: string; event: string; surface: string; round: string;
  winner: string; loser: string; score: string; modelProb: number; upset: boolean;
};

export default function Results() {
  const { tour } = useTour();
  const { data, loading } = useData<Fixture[]>("fixtures.json");
  const { data: players } = useData<{ name: string }[]>("players.json");
  const profileRoster = useMemo(() => new Set((players ?? []).map((player) => player.name)), [players]);
  const [filter, setFilter] = useState<ResultFilter>("all");

  const counts = resultCounts(data || []);
  const rows = filterResults(data || [], filter);

  return (
    <div className="pb-16">
      <PageHead
        eyebrow={`${tour.toUpperCase()} · the feed`}
        title="Results"
        sub="Every recent completed match with the win probability today's model gives the actual winner — a retrospective read, not a frozen pre-match call (those live on the Track Record page). Low numbers are upsets the model didn't see coming."
      />

      {loading && <Loading variant="cards" />}

      {data && (
        <>
          <div className="mt-8 mb-4 flex flex-wrap items-center gap-2">
            <FilterChip label="All" count={counts.all} active={filter === "all"} onClick={() => setFilter("all")} />
            <FilterChip label="Called" count={counts.called} active={filter === "called"} onClick={() => setFilter("called")} color="var(--color-win)" />
            <FilterChip label="Upsets" count={counts.upsets} active={filter === "upsets"} onClick={() => setFilter("upsets")} color="var(--color-loss)" />
            <span className="mono ml-auto text-xs text-[var(--color-faint)]">{rows.length} matches shown</span>
          </div>

          <div key={filter} className="grid gap-2.5 sm:grid-cols-2">
            {rows.map((f, i) => (
              <Reveal key={i} delay={Math.min(i * 0.01, 0.2)}>
                <CallCard
                  glow
                  surface={f.surface}
                  meta={`${f.event} · ${f.round} · ${f.date}`}
                  top={{ name: f.winner, prob: f.modelProb, won: true }}
                  bottom={{ name: f.loser, prob: 1 - f.modelProb, won: false }}
                  note={f.score}
                  verdict={{ label: f.upset ? "upset ✗" : "called it ✓", good: !f.upset }}
                  profileRoster={profileRoster}
                />
              </Reveal>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
