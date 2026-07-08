"use client";

import { useData, useTour } from "@/lib/tour";
import { PageHead, Loading, Reveal, CallCard } from "@/components/bits";
import { surfaceColor } from "@/lib/ui";
import { groupByEvent, type Upcoming } from "@/lib/upcoming";

export default function Schedule() {
  const { tour } = useTour();
  const { data, loading } = useData<Upcoming[]>("upcoming.json");
  const total = (data || []).length;
  const groups = groupByEvent(data || []);

  return (
    <div className="pb-16">
      <PageHead
        eyebrow={`${tour.toUpperCase()} · upcoming`}
        title="On Deck"
        sub="Every scheduled and in-progress match with the model's current win probability. The favourite is highlighted; the two sides sum to 100%."
      />

      {loading && <Loading />}

      {!loading && total === 0 && (
        <div className="mono mt-10 text-sm text-[var(--color-faint)]">
          No upcoming {tour.toUpperCase()} matches right now — check back when the next round is scheduled.
        </div>
      )}

      {total > 0 && (
        <div className="mt-8 space-y-9">
          {groups.map((g, gi) => (
            <section key={g.event}>
              <div className="mb-3 flex items-center gap-3">
                <span className="chip" style={{ color: surfaceColor(g.surface), borderColor: surfaceColor(g.surface) }}>
                  {g.surface}
                </span>
                <h2 className="display text-lg">{g.event}</h2>
                <span className="mono text-xs text-[var(--color-faint)]">
                  {g.matches.length} {g.matches.length === 1 ? "match" : "matches"}
                </span>
              </div>
              <div className="grid gap-2.5 sm:grid-cols-2">
                {g.matches.map((m, i) => {
                  const aFav = m.pA >= 0.5;
                  const fav = { name: aFav ? m.playerA : m.playerB, prob: aFav ? m.pA : 1 - m.pA, won: true };
                  const dog = { name: aFav ? m.playerB : m.playerA, prob: aFav ? 1 - m.pA : m.pA, won: false };
                  return (
                    <Reveal key={`${m.playerA}-${m.playerB}-${i}`} delay={Math.min(gi * 0.02 + i * 0.01, 0.2)}>
                      <CallCard
                        tone="projection"
                        surface={m.surface}
                        meta={`${m.round} · ${m.date}`}
                        top={fav}
                        bottom={dog}
                      />
                    </Reveal>
                  );
                })}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
