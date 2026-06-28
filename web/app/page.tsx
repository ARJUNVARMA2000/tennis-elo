"use client";

import { useState } from "react";
import { useData, useTour } from "@/lib/tour";
import { pct, surfaceColor, heat } from "@/lib/ui";
import { PageHead, Loading, Reveal } from "@/components/bits";

type Proj = { name: string; champion: number; final: number | null; sf: number | null };
type Tournament = {
  name: string; surface: string; level: string; bestOf: number;
  start: string; end: string; status: "completed" | "live";
  drawSize: number; aliveCount: number;
  champion: string | null; runnerUp: string | null;
  modelFavorite: string | null; favoritePicked: boolean;
  projection: Proj[];
};

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
function dateRange(start: string, end: string): string {
  const s = new Date(start + "T00:00"), e = new Date(end + "T00:00");
  const sm = MONTHS[s.getMonth()], em = MONTHS[e.getMonth()];
  return sm === em ? `${sm} ${s.getDate()}–${e.getDate()}` : `${sm} ${s.getDate()} – ${em} ${e.getDate()}`;
}

export default function Tournaments() {
  const { tour } = useTour();
  const { data, loading } = useData<Tournament[]>("tournaments.json");

  return (
    <div className="pb-16">
      <PageHead
        eyebrow={`${tour.toUpperCase()} · the current swing`}
        title="Latest Tournaments"
        sub="Every recent event with the model's title odds for the field. Live events show who's favoured from here; finished events show whether the model called the champion."
      />

      {loading && <Loading />}
      {data && data.length === 0 && (
        <div className="mono mt-10 text-sm text-[var(--color-faint)]">No recent tournaments in the data yet.</div>
      )}

      <div className="mt-8 grid gap-4 lg:grid-cols-2">
        {(data || []).map((t, i) => (
          <Reveal key={t.name + t.start} delay={Math.min(i * 0.04, 0.3)}>
            <Card t={t} />
          </Reveal>
        ))}
      </div>
    </div>
  );
}

function Card({ t }: { t: Tournament }) {
  const [open, setOpen] = useState(false);
  const sc = surfaceColor(t.surface);
  const live = t.status === "live";
  const shown = open ? t.projection : t.projection.slice(0, 5);
  const maxP = Math.max(0.01, ...t.projection.map((p) => p.champion));

  return (
    <div className="panel flex h-full flex-col p-5">
      {/* header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="chip" style={{ color: sc, borderColor: sc }}>{t.surface}</span>
            <span className="mono text-[11px] text-[var(--color-faint)]">{t.level} · Bo{t.bestOf}</span>
          </div>
          <h3 className="display mt-2 text-2xl leading-tight">{t.name}</h3>
          <div className="mono mt-1 text-[11px] text-[var(--color-faint)]">
            {dateRange(t.start, t.end)} · {t.drawSize} draw
          </div>
        </div>
        {live ? (
          <span className="mono flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-[var(--color-lime)]">
            <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-[var(--color-lime)]" />
            Live · {t.aliveCount} left
          </span>
        ) : (
          <span className="mono text-[11px] uppercase tracking-wider text-[var(--color-faint)]">Final</span>
        )}
      </div>

      {/* champion banner (completed) */}
      {t.champion && (
        <div className="mt-4 flex items-center justify-between rounded-lg border border-[var(--color-line)] bg-[var(--color-ink3)]/40 px-3 py-2">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-[var(--color-faint)]">Champion</div>
            <div className="text-[15px] text-[var(--color-gold)]">🏆 {t.champion}</div>
          </div>
          <div className="text-right">
            <div className="text-[10px] uppercase tracking-wider text-[var(--color-faint)]">Model favoured</div>
            <div className="mono text-[13px]" style={{ color: t.favoritePicked ? "var(--color-lime)" : "var(--color-muted)" }}>
              {t.modelFavorite} {t.favoritePicked ? "✓" : "✗"}
            </div>
          </div>
        </div>
      )}

      {/* projection */}
      <div className="mt-4 flex-1">
        <div className="mono mb-2 text-[10px] uppercase tracking-wider text-[var(--color-faint)]">
          {live ? "Title odds from here" : "Pre-event title odds"}
        </div>
        <div className="space-y-1.5">
          {shown.map((p, i) => {
            const isChamp = p.name === t.champion;
            return (
              <div key={p.name} className="flex items-center gap-2.5">
                <span className="mono w-4 text-right text-[11px] text-[var(--color-faint)]">{i + 1}</span>
                <span className="w-40 truncate text-[13px]" style={{ color: isChamp ? "var(--color-gold)" : "var(--color-text)" }}>
                  {p.name}{isChamp && " 🏆"}
                </span>
                <div className="bartrack h-1.5 flex-1">
                  <div style={{ width: `${(p.champion / maxP) * 100}%`, background: heat(p.champion) }} />
                </div>
                <span className="mono w-10 text-right text-[12px]" style={{ color: heat(p.champion) }}>
                  {pct(p.champion, 0)}
                </span>
              </div>
            );
          })}
        </div>
        {t.projection.length > 5 && (
          <button onClick={() => setOpen(!open)} className="mono mt-3 text-[11px] text-[var(--color-cyan)] hover:underline">
            {open ? "show less" : `show full field (${t.projection.length})`}
          </button>
        )}
      </div>
    </div>
  );
}
