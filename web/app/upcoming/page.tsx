"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { useData, useTour } from "@/lib/tour";
import { PageHead, Loading, Reveal, CallCard } from "@/components/bits";

type Fixture = {
  date: string; event: string; surface: string; round: string;
  winner: string; loser: string; score: string; modelProb: number; upset: boolean;
};

export default function Upcoming() {
  const { tour } = useTour();
  const { data, loading } = useData<Fixture[]>("fixtures.json");
  const [onlyUpsets, setOnlyUpsets] = useState(false);

  const rows = (data || []).filter((f) => !onlyUpsets || f.upset);

  return (
    <div className="pb-16">
      <PageHead
        eyebrow={`${tour.toUpperCase()} · latest results`}
        title="The Feed"
        sub="Every recent completed match with the model's pre-match win probability for the actual winner. Low numbers are upsets the model didn't see coming."
      />

      {loading && <Loading />}

      {data && (
        <>
          <div className="mt-8 mb-4 flex items-center gap-3">
            <motion.button
              onClick={() => setOnlyUpsets(!onlyUpsets)}
              whileTap={{ scale: 0.94 }}
              className="chip transition-colors"
              style={{ background: onlyUpsets ? "var(--color-loss)" : "transparent", color: onlyUpsets ? "var(--color-on-accent)" : "var(--color-loss)", borderColor: "var(--color-loss)" }}
            >
              Upsets only
            </motion.button>
            <span className="mono text-xs text-[var(--color-faint)]">{rows.length} matches</span>
          </div>

          <div key={onlyUpsets ? "upsets" : "all"} className="grid gap-2.5 sm:grid-cols-2">
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
                />
              </Reveal>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
