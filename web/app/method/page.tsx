"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { useData, useTour } from "@/lib/tour";
import { PageHead, StatCard } from "@/components/bits";
import { fmt, kAt, type MethodDoc } from "@/lib/method";
import { stagger, fadeUp } from "@/lib/motion";

type Meta = {
  dataThrough: string; matches: number; players: number; activePlayers: number;
  modelVersion: string; features?: string[];
};

const REPO = "https://github.com/ARJUNVARMA2000/tennis-elo";

const STEPS = [
  ["Surface-blended Elo", "Every match updates an overall rating plus separate hard, clay and grass ratings — results transfer partially across surfaces, so clay form informs hard-court form — with a dynamic K-factor (new players move fast, veterans settle) and margin-of-victory weighting from games won. At prediction time the overall and surface ratings are blended with a per-tour tuned weight, currently about 60/40 toward the surface rating. ATP ratings also learn from Challenger and qualifying matches, though predictions are trained and scored on tour-level main draws only."],
  ["Serve / return point model", "Each player carries a time-decayed serve and return skill, computed per surface and adjusted for the strength of the opponents faced. These feed a hierarchical Markov model (point → game → tiebreak → set → match) that yields a full set-score distribution and handles best-of-3 vs best-of-5 correctly."],
  ["Tactical fingerprints", "From the Match Charting Project, each charted player gets an eight-dimension style profile — serve dominance, placement variety, net play, serve-and-volley rate, aggression, forehand/backhand balance, return depth, break-point clutch — attached as features where available."],
  ["XGBoost combiner", "An ensemble of seed-bagged XGBoost classifiers fuses Elo, the point model, ranking, rest, fatigue, recent form, head-to-head, home advantage, player profile, style and match context (surface, format, tier, round) into one win probability, then Platt-calibrated so the numbers mean what they say. Elo remains the single most important input."],
  ["Monte Carlo draws", "Pairwise probabilities drive thousands of simulated single-elimination draws for per-round and title odds. Live tournaments are simulated on the real remaining bracket — full draws parsed from Wikipedia, eliminations from ESPN — not a hypothetical re-seed."],
  ["Hourly refresh, daily retrain", "Live scores and results are re-pulled hourly and every figure on this site regenerated; once a day the full pipeline re-downloads all data, re-walks the ratings and retrains the combiner — all walk-forward and leakage-free (betting odds are used only to benchmark, never as inputs)."],
];

/* ---------- local building blocks (section idiom shared with /scorecard) ---------- */

const SectionHead = ({ n, kicker, title, sub }: { n: string; kicker: string; title: string; sub: string }) => (
  <>
    <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--color-accent)]">{n} · {kicker}</div>
    <h2 className="display mt-1.5 text-2xl">{title}</h2>
    <p className="mt-2 max-w-2xl text-[14px] text-[var(--color-muted)]">{sub}</p>
  </>
);

/** A live production value inside a formula — visibly distinct from the algebra. */
const Num = ({ v }: { v: number }) => <span className="text-[var(--color-accent)]">{fmt(v)}</span>;

/** Hand-set equation block (no math lib — static export, minimal deps). */
const Formula = ({ children }: { children: React.ReactNode }) => (
  <div className="mono overflow-x-auto rounded-lg border border-[var(--color-line)] bg-[var(--color-bg)] px-4 py-3 text-[13px] leading-relaxed">
    {children}
  </div>
);

const P = ({ children }: { children: React.ReactNode }) => (
  <p className="max-w-3xl text-[14px] leading-relaxed text-[var(--color-muted)]">{children}</p>
);

function DataTable({ head, rows }: { head: string[]; rows: React.ReactNode[][] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full max-w-xl text-[13px]">
        <thead className="mono text-[10px] uppercase tracking-wider text-[var(--color-faint)]">
          <tr className="border-b border-[var(--color-line)]">
            {head.map((h, i) => (
              <th key={h} className={`py-2 font-medium ${i === 0 ? "text-left" : "text-right"}`}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="mono">
          {rows.map((cells, r) => (
            <tr key={r} className="row-glow border-b border-[var(--color-line)]/40">
              {cells.map((c, i) => (
                <td key={i} className={`py-2 ${i === 0 ? "text-left text-[var(--color-muted)]" : "text-right"}`}>{c}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const TIER_LABEL: Record<string, string> = {
  grand_slam: "Grand Slam", tour_finals: "Tour Finals", masters: "Masters 1000",
  olympics: "Olympics", atp500: "500-level", atp250: "250-level",
  davis_cup: "Team cups", challenger: "Challenger / qualifying",
};

const XGB_LABEL: Record<string, string> = {
  nEstimators: "n_estimators", maxDepth: "max_depth", learningRate: "learning_rate",
  subsample: "subsample", colsampleBytree: "colsample_bytree", minChildWeight: "min_child_weight",
  regAlpha: "reg_alpha", regLambda: "reg_lambda", gamma: "gamma",
};

/** The 42 combiner inputs, collapsed by default — long and code-ish. */
function FeatureList({ features }: { features: string[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button onClick={() => setOpen(!open)} className="mono text-[11px] text-[var(--color-accent)] hover:underline">
        {open ? "hide the full feature list" : `show all ${features.length} features`}
      </button>
      {open && (
        <div className="mono mt-3 flex max-w-3xl flex-wrap gap-1.5 text-[11px]">
          {features.map((f) => <span key={f} className="chip">{f}</span>)}
        </div>
      )}
    </div>
  );
}

/* ------------------------------ detail sections ------------------------------ */

function FullMethodology({ m, features }: { m: MethodDoc; features?: string[] }) {
  const e = m.elo;
  const sr = m.serveReturn;
  const c = m.combiner;
  const kRows = [10, 100, 1000].map((n) => [
    String(n),
    fmt(kAt(e.kScale, e.kOffset, e.kShape, n)),
    fmt(kAt(e.surfaceKScale, e.surfaceKOffset, e.surfaceKShape, n)),
  ]);
  return (
    <motion.div variants={stagger(0.06)} initial="hidden" animate="show" className="mt-8 space-y-5">
      <motion.section variants={fadeUp} className="panel p-6 sm:p-7">
        <SectionHead n="01" kicker="ratings" title="Elo update equations"
          sub="The rating core. The functional form is FiveThirtyEight's tennis Elo (whose dynamic K is 250/(n+5)^0.4); every constant below has been re-tuned per tour against this dataset." />
        <div className="mt-5 space-y-4">
          <Formula>
            E<sub>A</sub> = 1 / (1 + 10<sup>(R<sub>B</sub> − R<sub>A</sub>) / <Num v={e.ratingScale} /></sup>)
            <span className="text-[var(--color-faint)]">   — expected score for player A</span>
          </Formula>
          <Formula>
            R′ = R + K(n) · mov · (S − E<sub>A</sub>)
            <span className="text-[var(--color-faint)]">   — after each match, S = 1 if A won else 0</span>
          </Formula>
          <Formula>
            K(n) = <Num v={e.kScale} /> / (n + <Num v={e.kOffset} />)<sup><Num v={e.kShape} /></sup>
            <span className="text-[var(--color-faint)]">   overall;   </span>
            K<sub>surf</sub>(n) = <Num v={e.surfaceKScale} /> / (n + <Num v={e.surfaceKOffset} />)<sup><Num v={e.surfaceKShape} /></sup>
            <span className="text-[var(--color-faint)]">   per surface</span>
          </Formula>
          <P>
            n is the player&apos;s career (or per-surface) match count, so newcomers move fast and veterans settle.
            Everyone enters at {fmt(m.defaultRating)}. In practice the curves give:
          </P>
          <DataTable head={["career matches", "overall K", "surface K"]} rows={kRows} />
          <P>
            Updates are also scaled by event tier{m.tiers.anchors ? (
              <> — the multipliers below are anchored by two tuned endpoints (Grand Slam {fmt(m.tiers.anchors[0])}, Challenger {fmt(m.tiers.anchors[1])}) with the tiers between them rescaled linearly</>
            ) : null}:
          </P>
          <DataTable head={["tier", "K multiplier"]}
            rows={Object.entries(m.tiers.kMult).map(([k, v]) => [TIER_LABEL[k] ?? k, fmt(v)])} />
        </div>
      </motion.section>

      <motion.section variants={fadeUp} className="panel p-6 sm:p-7">
        <SectionHead n="02" kicker="ratings" title="Surface blend & cross-surface transfer"
          sub="Why the surface ratings can carry most of the prediction weight without going cold on rare surfaces." />
        <div className="mt-5 space-y-4">
          <Formula>
            R<sub>match</sub> = (1 − b) · R<sub>overall</sub> + b · R<sub>surface</sub>
            <span className="text-[var(--color-faint)]">,   </span>b = <Num v={e.surfaceBlend} />
          </Formula>
          <P>
            Every result also updates the other two surfaces&apos; ratings at ×<Num v={e.xsurf} />{" "}of the
            update (cross-surface transfer), so a debutant&apos;s clay rating is informed by their hard-court
            results rather than starting cold — that transfer is what lets the tuned blend lean this far
            toward the surface rating.
            {e.blendN50 === 0 ? " The blend is a fixed linear mix (an adaptive, sample-size-dependent blend was tuned and is off)." : ` The blend adapts with surface sample size (half-saturation at ${fmt(e.blendN50)} matches).`}
          </P>
          <P>
            {e.bo5Scale !== 1
              ? <>Best-of-5 matches stretch the rating difference by ×<Num v={e.bo5Scale} />{" "}before computing E<sub>A</sub> — a small per-point edge compounds over more sets.</>
              : <>No best-of-5 adjustment applies on this tour (its matches are best-of-3).</>}
            {" "}After <Num v={e.inactDays} />{" "}days without a match, the returning player&apos;s K is boosted
            ×(1 + <Num v={e.inactBoost} />) so the rating re-converges quickly.
          </P>
          <P>
            {e.retKMult !== 1
              ? <>Retirements and defaults update at ×<Num v={e.retKMult} />{" "}of the normal K (a retirement says less about skill than a completed match).</>
              : <>Retirements update at full weight (down-weighting them measured no gain on this tour).</>}
            {" "}{e.skipWalkovers
              ? "Walkovers are skipped entirely — zero on-court information."
              : "Walkovers currently still count toward ratings (the skip flag is tuned off)."}
            {" "}{e.homeAdv === 0
              ? "There is no Elo-level home-country bonus — home advantage enters the combiner as a feature instead."
              : `A home-country rating bonus of ${fmt(e.homeAdv)} points applies.`}
          </P>
        </div>
      </motion.section>

      <motion.section variants={fadeUp} className="panel p-6 sm:p-7">
        <SectionHead n="03" kicker="ratings" title="Margin of victory"
          sub="A 6-0 6-0 demolition should move ratings more than a 7-6 7-6 squeaker — logarithmically, so blowouts don't dominate." />
        <div className="mt-5 space-y-4">
          <Formula>
            mov = min(1 + <Num v={e.movFactor} /> · ln(1 + game margin), <Num v={e.movCap} />)
          </Formula>
          <P>
            The game margin is total games won minus lost across the match; a dead-even margin leaves the
            update unscaled (mov = 1). This is the &ldquo;Weighted Elo&rdquo; variant from the tennis-forecasting
            literature, not part of FiveThirtyEight&apos;s original design.
          </P>
        </div>
      </motion.section>

      <motion.section variants={fadeUp} className="panel p-6 sm:p-7">
        <SectionHead n="04" kicker="point model" title="Serve/return Markov model"
          sub="An opponent-adjusted estimate of each player's serve-point win rate, walked through tennis's scoring tree — this is what produces full set-score distributions." />
        <div className="mt-5 space-y-4">
          <Formula>
            p(A wins a serve point on s) = base<sub>s</sub> + serve<sub>A</sub>(s) − return<sub>B</sub>(s)
            <span className="text-[var(--color-faint)]">,   clipped to [{fmt(sr.pClip[0])}, {fmt(sr.pClip[1])}]</span>
          </Formula>
          <P>
            Each player&apos;s serve and return skills are opponent-adjusted running estimates: every match&apos;s
            serve stats are compared against what an average player would have managed against that
            opponent, and the residual updates the skill. Older evidence decays with a half-life of{" "}
            <Num v={sr.formHalflifeDays} />{" "}days (weight = 0.5<sup>Δdays / {fmt(sr.formHalflifeDays)}</sup>).
          </P>
          <P>
            Estimates are shrunk toward priors at two levels: a player&apos;s global skill counts as{" "}
            <Num v={sr.serveShrinkagePoints} />{" "}prior points of tour-average evidence, and per-surface
            deviations are shrunk toward the player&apos;s global level with a <Num v={sr.surfaceServeShrinkage} />-point
            prior — surface-specific serve differences are real but small, so they need heavy evidence.
            {sr.eventShrinkage === 0 ? " (An event-speed baseline was built and tuned off — it failed the adoption arbiter.)" : ""}
          </P>
          <P>
            The two serve-point probabilities then walk a closed-form Markov chain — point → game →
            tiebreak → set → match, for best-of-3 and best-of-5 — which yields the match win probability
            <em> and</em> the full set-score distribution. This probability feeds the combiner as one feature;
            it is also why best-of-5 behaves correctly (a per-point edge compounds over more sets).
          </P>
        </div>
      </motion.section>

      <motion.section variants={fadeUp} className="panel p-6 sm:p-7">
        <SectionHead n="05" kicker="combiner" title="XGBoost + Platt calibration"
          sub="Gradient boosting doesn't replace Elo — it fuses Elo, the point model and context into one calibrated number. Elo remains the dominant input." />
        <div className="mt-5 space-y-4">
          <P>
            The combiner sees <span className="mono text-[var(--color-text)]">{c.featureCount}</span>{" "}features
            per match: {c.featureGroups.antisymmetric}{" "}anti-symmetric differences (Elo gaps, serve/return
            skill gaps, rest, fatigue, head-to-head, home advantage, …), {c.featureGroups.style} Match
            Charting style differences, and {c.featureGroups.symmetric}{" "}symmetric context features (surface,
            format, tier, round, sample-size confidence). Features are stored as winner-minus-loser
            differences with a random half sign-flipped, so the label is ~50/50 and the model can&apos;t learn
            &ldquo;player A always wins&rdquo;.
          </P>
          {features && features.length > 0 && <FeatureList features={features} />}
          <DataTable head={["hyperparameter", "value"]}
            rows={Object.entries(c.xgb).map(([k, v]) => [XGB_LABEL[k] ?? k, fmt(v)])} />
          <P>
            <span className="mono">n_estimators</span> is a cap, not a target — early stopping
            ({fmt(c.earlyStoppingRounds)}{" "}rounds against the held-out calibration season) decides the real
            tree count. Production averages <Num v={c.nBag} />{" "}seed-varied fits (pure variance reduction),
            and the averaged output is calibrated with Platt scaling:
          </P>
          <Formula>
            p = σ(a · logit(p<sub>raw</sub>) + b)
            <span className="text-[var(--color-faint)]">   — a, b fitted per fold on out-of-sample predictions</span>
          </Formula>
          <P>
            Platt beats isotonic here: with a few thousand calibration points, isotonic regression forms
            wide plateaus that collapse distinct matchups to identical probabilities.
          </P>
        </div>
      </motion.section>

      <motion.section variants={fadeUp} className="panel p-6 sm:p-7">
        <SectionHead n="06" kicker="protocol" title="Adoption gate & leakage guarantees"
          sub="How changes ship — and why the backtest numbers are honest." />
        <div className="mt-5 space-y-4">
          <P>
            Every candidate change — a constant, a feature, a training trick — is tuned only on{" "}
            {m.protocol.tuneYears[0]}–{m.protocol.tuneYears[1]}, then must hold up on the untouched{" "}
            {m.protocol.valStartYear}+ window (paired per-match log-loss, ±standard error), and finally
            survive a full {m.protocol.backtestStartYear}–present walk-forward with the combiner retrained.
            Component-level wins that the retrained combiner absorbs are rejected — and the rejections are
            written up with their numbers, not discarded.
          </P>
          <ul className="max-w-3xl list-disc space-y-1.5 pl-5 text-[14px] leading-relaxed text-[var(--color-muted)]">
            <li>Every rating and feature is recorded <em>before</em> its match in one chronological pass — the backtest is walk-forward by construction.</li>
            <li>Calibration is fitted per fold on earlier seasons&apos; out-of-sample predictions, never on the season being scored.</li>
            <li>Betting odds are used only to benchmark, never as model inputs.</li>
            <li>Determinism is pinned by tests: fixed seeds end-to-end, with anti-drift locks on walk-forward outputs.</li>
          </ul>
          <P>
            The full experiment history — adopted and rejected — is public:{" "}
            <a href={`${REPO}/tree/master/tasks`} target="_blank" rel="noopener noreferrer" className="text-[var(--color-accent)] hover:underline">tuning logs</a>{" "}
            and the{" "}
            <a href={`${REPO}/blob/master/tasks/research/ledger.tsv`} target="_blank" rel="noopener noreferrer" className="text-[var(--color-accent)] hover:underline">experiment ledger</a>.
          </P>
        </div>
      </motion.section>
    </motion.div>
  );
}

/* ------------------------------------ page ------------------------------------ */

export default function Method() {
  const { tour } = useTour();
  const { data } = useData<Meta>("meta.json");
  const { data: method, error: methodError } = useData<MethodDoc>("method.json");

  return (
    <div className="pb-16">
      <PageHead
        eyebrow="how it works"
        title="The Method"
        sub="A hybrid model: strong Elo and point-model features fed into a calibrated gradient-boosting combiner. Research is consistent that this beats either ratings or raw ML alone, and approaches the betting market."
      />

      {data && (
        <motion.div
          variants={stagger(0.05)}
          initial="hidden"
          animate="show"
          className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5"
        >
          <motion.div variants={fadeUp}>
            <StatCard label="Tour" value={tour.toUpperCase()} />
          </motion.div>
          <motion.div variants={fadeUp}>
            <StatCard label="Data through" value={data.dataThrough} />
          </motion.div>
          <motion.div variants={fadeUp}>
            <StatCard label="Matches" value={data.matches ?? 0} />
          </motion.div>
          <motion.div variants={fadeUp}>
            <StatCard label="Active players" value={data.activePlayers ?? 0} />
          </motion.div>
          <motion.div variants={fadeUp}>
            <StatCard label="Model" value={`v${data.modelVersion}`} />
          </motion.div>
        </motion.div>
      )}

      <motion.div variants={stagger(0.05)} initial="hidden" animate="show" className="mt-8 space-y-4">
        {STEPS.map(([title, body], i) => (
          <motion.div key={title} variants={fadeUp} className="panel flex gap-5 p-6">
            <div className="display text-3xl text-[var(--color-accent)]">{String(i + 1).padStart(2, "0")}</div>
            <div>
              <div className="display text-lg">{title}</div>
              <p className="mt-2 text-[15px] leading-relaxed text-[var(--color-muted)]">{body}</p>
            </div>
          </motion.div>
        ))}
      </motion.div>

      <div className="mt-14 border-t border-[var(--color-line)] pt-8">
        <div className="eyebrow">full methodology · {tour}</div>
        <h2 className="display mt-2 text-3xl">The exact math</h2>
        <p className="mt-2 max-w-3xl text-[14px] text-[var(--color-muted)]">
          Every constant below is the live production value for the {tour.toUpperCase()}{" "}tour, exported
          from the model&apos;s configuration on each refresh — nothing here is hand-maintained, so a retune
          updates this page automatically. Use the tour toggle to see the other tour&apos;s values.
        </p>
        {method && <FullMethodology m={method} features={data?.features} />}
        {!method && methodError && (
          <p className="mt-6 text-[14px] text-[var(--color-muted)]">
            The detailed constants haven&apos;t been generated for this data snapshot yet — they regenerate
            with every refresh, so check back shortly.
          </p>
        )}
      </div>
    </div>
  );
}
