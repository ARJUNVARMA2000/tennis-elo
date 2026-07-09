"use client";

import { useData, useTour } from "@/lib/tour";
import { PageHead, Loading, Reveal, CallCard } from "@/components/bits";
import { surfaceColor, tournamentTier } from "@/lib/ui";
import { type TournamentInfo } from "@/lib/live";
import { groupByEvent, upcomingCard, type Upcoming } from "@/lib/upcoming";

export default function Schedule() {
  const { tour } = useTour();
  const { data, loading } = useData<Upcoming[]>("upcoming.json");
  const { data: tournaments } = useData<TournamentInfo[]>("tournaments.json");
  const total = (data || []).length;
  // Join each group to its tournament tier (tournaments.json `level`), then order the board by
  // prestige — Grand Slam → 1000 → 500 → 250. Stable sort keeps the soonest-first order within a tier.
  const levelFor = (event: string) => {
    const ts = tournaments || [];
    const t = ts.find((x) => x.name === event)
      ?? ts.find((x) => x.name.length >= 5 && event.toLowerCase().includes(x.name.toLowerCase()));
    return t?.level;
  };
  const ordered = groupByEvent(data || [])
    .map((g) => ({ g, tier: tournamentTier(levelFor(g.event), g.event) }))
    .sort((a, b) => a.tier.rank - b.tier.rank);

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
          {ordered.map(({ g, tier }, gi) => (
            <section key={g.event}>
              <div className="mb-3 flex items-center gap-3">
                <span className="chip" style={{ color: surfaceColor(g.surface), borderColor: surfaceColor(g.surface) }}>
                  {g.surface}
                </span>
                <span
                  className="chip"
                  style={{
                    color: tier.rank === 0 ? "var(--color-champ)" : "var(--color-muted)",
                    borderColor: tier.rank === 0 ? "var(--color-champ)" : "var(--color-line2)",
                  }}
                >
                  {tier.short}
                </span>
                <h2 className="display text-lg">{g.event}</h2>
                <span className="mono text-xs text-[var(--color-faint)]">
                  {g.matches.length} {g.matches.length === 1 ? "match" : "matches"}
                </span>
              </div>
              <div className="grid gap-2.5 sm:grid-cols-2">
                {g.matches.map((m, i) => (
                  <Reveal key={`${m.playerA}-${m.playerB}-${i}`} delay={Math.min(gi * 0.02 + i * 0.01, 0.2)}>
                    <CallCard tone="projection" {...upcomingCard(m)} />
                  </Reveal>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
