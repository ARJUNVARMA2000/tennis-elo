"""Central configuration: paths, data source, Elo parameters, tournament tiers.

All tunable magic numbers live here so the rest of the package reads cleanly and a
single edit re-tunes the whole pipeline (mirrors the wc_model convention).
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
MODEL_DIR = Path(__file__).resolve().parents[2]          # .../tennis_model
DATA_DIR = MODEL_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
ODDS_DIR = RAW_DIR / "odds"
OUTPUT_DIR = DATA_DIR / "output"
WEB_DATA_DIR = MODEL_DIR.parent / "web" / "public" / "data"   # web-app mirror target

TOURS = ("atp", "wta")


def historical_dir(tour: str) -> Path:
    return RAW_DIR / tour / "historical"


def fresh_dir(tour: str) -> Path:
    return RAW_DIR / tour / "fresh"


def live_dir(tour: str) -> Path:
    return RAW_DIR / tour / "live"      # ESPN same-day overlay (lowest de-dup priority)


def output_dir(tour: str) -> Path:
    return OUTPUT_DIR / tour


KALSHI_LEDGER_DIR = DATA_DIR / "kalshi_ledger"   # committed CSVs + report (eval-only)


def kalshi_dir(tour: str) -> Path:
    return RAW_DIR / "kalshi" / tour    # snapshot cache (evictable; ledger is durable)


# ---------------------------------------------------------------------------
# Data sources (per tour)
# ---------------------------------------------------------------------------
# Sackmann's canonical repos went private in 2026 and no single free mirror is both
# fresh AND full-schema, so each tour merges a full-schema HISTORICAL source (serve
# stats; slow-moving) with a results-only FRESH overlay (kept current ~weekly).
# Raw HTTPS may be blocked behind a proxy, so the downloader falls back to `gh api`.
HISTORICAL_SOURCE = {
    "atp": {  # TML-Database: <year>.csv, full Sackmann schema + indoor flag
        "repo": "Tennismylife/TML-Database",
        "path": "{year}.csv",
        "raw": "https://raw.githubusercontent.com/Tennismylife/TML-Database/master/{year}.csv",
        "last_year": 2026,   # repo froze Jan 2026 — later years come from the stats overlay
    },
    "wta": {  # full-schema WTA snapshot (serve stats), through 2024
        "repo": "zeldao08/tennis_players_analysis",
        "path": "files/wta/wta_matches_{year}.csv",
        "raw": "https://raw.githubusercontent.com/zeldao08/tennis_players_analysis/main/files/wta/wta_matches_{year}.csv",
        "last_year": 2024,   # snapshot ends 2024 — later years come from the stats overlay
    },
}
FRESH_SOURCE = {  # LuckyLoser91/TennisCourtLog: results-only, auto-refreshed ~weekly
    "atp": {
        "repo": "LuckyLoser91/TennisCourtLog",
        "path": "tennis_atp/atp_matches_{year}.csv",
        "raw": "https://raw.githubusercontent.com/LuckyLoser91/TennisCourtLog/main/tennis_atp/atp_matches_{year}.csv",
    },
    "wta": {
        "repo": "LuckyLoser91/TennisCourtLog",
        "path": "tennis_wta/wta_matches_{year}.csv",
        "raw": "https://raw.githubusercontent.com/LuckyLoser91/TennisCourtLog/main/tennis_wta/wta_matches_{year}.csv",
    },
}
# TML's GitHub repo froze in Jan 2026 when the project moved to its own site, which
# serves the same-schema year CSVs (full serve stats) updated daily, plus Challenger
# and qualifying companions. ATP only. The STATS overlay dir holds these fast-moving
# files (and, for WTA, our scraped stats), separate from the frozen HISTORICAL archive.
# Challenger files reach back to 1978 and quali files to 2007 (upstream backfilled,
# verified 2026-07-05); first_year=2018 applies to the tour-level year files only.
TML_STATS_SOURCE = {
    "files_api": "https://stats.tennismylife.org/api/data-files",
    "data_url": "https://stats.tennismylife.org/data/{name}",
    "year_file": "{year}.csv",                      # tour-level main draws
    "challenger_file": "{year}_challenger.csv",     # A5 experiment (INCLUDE_CHALLENGERS)
    "quali_file": "atp_quali/{year}_atp_quali.csv",  # tour-event qualifying (Q1-Q3)
    "quali_first_year": 2007,                        # earliest quali file upstream
    "ongoing_challenger_file": "challenger_ongoing_tourneys.csv",  # in-progress events
    "first_year": 2018,
}
# A5 challenger+quali ingestion — ADOPTED 2026-07-05 in RATINGS-ONLY form: lower
# rows feed the rating/point/context walks, while the combiner trains, calibrates
# and is scored on main-draw rows only (see pipeline.py main_rows filter). Full
# 2010-26 arbiter on the identical main-draw eval set: d_tune +0.00587±0.00089,
# d_val +0.00756±0.00100, acc 0.6900→0.6958, Brier 0.1975→0.1947; 17/17 years
# positive. The FULL variant (lower rows also in the combiner) was REJECTED:
# +0.00869 tune but −0.00107 val with ±0.03 per-year swings — the challenger-
# dominated row mix destabilizes fold training/calibration.
INCLUDE_CHALLENGERS = True
# WTA 125s stay OUT: decoupled from the ATP adoption above (no 125/lower source
# covers the 2010-19 tune window, so a 125 experiment is gate-untestable — same
# regime problem the original A5 had).
INCLUDE_WTA_125 = False
# Increment only when an intentional ingestion-policy change makes meta.matches
# incomparable with the prior deploy. Health requires this exact value and resets its
# run-over-run monotonic baseline only across a version boundary; the following run is
# compared normally again. Version 2 removes the ESPN-live WTA-125 policy leak; version 3
# stops deleting same-season rematches that repeat an earlier scoreline in another round;
# version 4 canonicalizes the Cincinnati cross-source WTA aliases, intentionally collapsing
# duplicate historical/live identities and making the old match-count baseline incomparable.
MATCH_POPULATION_VERSION = 4
# Lower-tier (challenger + qualifying) ingestion starts here: 5 warm-up years of
# rating history before the 2010 tune window; the full 1978+ archive would double
# the walk for matches that can no longer influence any scored year.
LOWER_TIER_FIRST_YEAR = 2005


def stats_dir(tour: str) -> Path:
    return RAW_DIR / tour / "stats"     # daily full-schema overlay (TML site / WTA scraper)


def lower_dir(tour: str) -> Path:
    return RAW_DIR / tour / "lower"     # challenger + qualifying overlay (A5, gated)


FIRST_YEAR = 1980          # Elo warm-up era; serve stats begin ~1991
STATS_FIRST_YEAR = 1991    # first year with usable serve/return statistics

# ---------------------------------------------------------------------------
# Elo parameters
# ---------------------------------------------------------------------------
DEFAULT_RATING = 1500.0
RATING_SCALE = 400.0           # logistic divisor: E_a = 1/(1+10^((Rb-Ra)/scale))

# Dynamic K-factor (Sackmann / FiveThirtyEight): K = K_SCALE / (n + K_OFFSET)^K_SHAPE
# where n is the player's career match count. New players move fast; veterans settle.
K_SCALE = 250.0
K_OFFSET = 5.0
K_SHAPE = 0.4

# Surface-specific ratings use a smaller, slower K (less data per surface).
SURFACE_K_SCALE = 200.0
SURFACE_K_OFFSET = 5.0
SURFACE_K_SHAPE = 0.4

# At prediction time, blend overall and surface Elo (Sackmann's ~50/50 mix).
SURFACE_BLEND = 0.5            # weight on the surface-specific rating

# Cross-surface transfer (E2): a result on surface s also moves the OTHER surface
# ratings by XSURF_TRANSFER x the surface-s update (clay form partially informs
# hard-court form). 0 = off = surface ratings update only on their own surface.
XSURF_TRANSFER = 0.0

# Adaptive surface blend (P3): scale each player's surface-blend weight by
# n_s / (n_s + BLEND_N50) where n_s is their own-surface match count, so debutants
# lean on overall Elo and veterans on the surface rating. 0 = off = fixed blend.
BLEND_N50 = 0.0

# Elo home advantage (W2c): rating points added to a player competing in their own
# country when computing expectations (recorded probabilities AND update sizes), so
# home wins move ratings less and ratings become venue-neutral estimates.
# 0 = off. Venue comes from data/geo.py; prediction time stays venue-free.
HOME_ADV = 0.0

# Margin-of-victory ("Weighted Elo"): scale the update by how dominant the win was,
# measured from games won. Disabled => standard Elo (useful as a backtest baseline).
USE_MOV = True
MOV_FACTOR = 0.30             # multiplier = 1 + FACTOR*ln(1 + game_diff), capped
MOV_CAP = 1.60

# Incomplete matches. Measured on 2010-2019/2020+ log-loss: SKIPPING walkovers is
# slightly WORSE on both tours — a withdrawal is weak evidence of injury/decline, so
# the small rating hit carries signal. Keep updating on them. Retirements can be
# down-weighted via RET_K_MULT (tuned offline; 1.0 = no down-weight).
SKIP_WALKOVERS = False
RET_K_MULT = 1.0

# Returning-from-layoff K boost: a player idle > INACT_DAYS gets K scaled by
# 1 + INACT_BOOST*min(gap_years, 2) for their first match back, letting the
# comeback matches move the (stale) rating quickly. 0 disables.
INACT_DAYS = 0.0
INACT_BOOST = 0.0

# Best-of-5 expected score: the favorite's true win probability in Bo5 exceeds the
# Bo3 logistic, so the rating difference is scaled by BO5_SCALE for slams — in both
# the recorded pre-match probability and the update expectation. 1.0 disables.
BO5_SCALE = 1.0

# Window (days) for the form90 Elo-momentum feature: overall-rating change vs
# ~FORM_DAYS ago. Lives on EloParams (the walk computes it), tunable via group=feat.
FORM_DAYS = 90.0

# ---------------------------------------------------------------------------
# Tournament tiers — importance multiplier on K, keyed by `tourney_level`.
# TML levels: G=Slam, F=Tour Finals, M=Masters 1000, 500/250=ATP tour, A=other
# (pre-2009 tour), O=Olympics, D=Davis Cup, C=Challenger.
# ---------------------------------------------------------------------------
TIER_NAMES = {
    # historical Sackmann/TML codes
    "G": "grand_slam", "F": "tour_finals", "M": "masters", "O": "olympics",
    "500": "atp500", "250": "atp250", "A": "atp250", "D": "davis_cup", "C": "challenger",
    "Q": "challenger",   # tour-event qualifying rows (results.py stamps them "Q"):
                         # challenger-strength fields, so they update at challenger K
    "P": "masters", "PM": "masters", "I": "atp250", "W": "atp250",   # legacy WTA codes
    # fresh-overlay vocabulary (LuckyLoser91), mapped onto the same tier names so the
    # K-multipliers below apply unchanged
    "GrandSlam": "grand_slam", "Grand Slam": "grand_slam",
    "ATPFinals": "tour_finals", "WTAFinals": "tour_finals", "Finals": "tour_finals",
    "Masters": "masters", "ATP1000": "masters", "Masters1000": "masters",
    "WTA1000": "masters", "ATP500": "atp500", "WTA500": "atp500",
    "ATP250": "atp250", "WTA250": "atp250", "WTA125": "challenger",
    "Olympics": "olympics", "DavisCup": "davis_cup", "UnitedCup": "atp250", "ATPCup": "atp250",
}
TIER_K_MULT = {
    "grand_slam": 1.10, "tour_finals": 1.05, "masters": 1.05, "olympics": 1.05,
    "atp500": 1.00, "atp250": 0.95, "davis_cup": 0.90, "challenger": 0.85,
}
DEFAULT_TIER_K_MULT = 0.90

# Curated tier for current-season sponsor-named events the match archive can't identify AND
# whose Wikipedia infobox omits `category` (e.g. the Swedish Open = "Nordea Open"). A numeric
# value ("250"/"500"/"1000") is rendered "{TOUR} 250"; a full string ("Grand Slam") is used
# as-is. Display-only; add a line when a new sponsor-named event surfaces on the schedule board.
EVENT_TIER_FALLBACK: dict = {
    "Nordea Open": "250",         # Swedish Open (Bastad) — its infobox omits `category`
    "Grand Est Open 88": "125",   # WTA 125 (also wiki-covered; kept correct as a backstop)
    "Hall of Fame Open": "250",
    # Los Cabos Open — same shape as Nordea: the article resolves (via WIKI_TITLE_OVERRIDES,
    # which now supplies its surface) but its infobox carries no `category` field.
    "Mifel Tennis Open": "250",
}

# ---------------------------------------------------------------------------
# Per-tour tuned overrides (eval/tune.py sweeps; tune window 2010-2019, validated
# on 2020+). An empty dict keeps the shared defaults above. TIER_ANCHORS rescales
# TIER_K_MULT linearly between (grand_slam, challenger) anchors; None keeps it.
# ---------------------------------------------------------------------------
ELO_PARAM_OVERRIDES: dict = {
    # 400-trial `_xsurf` re-sweep (2026-07-02 core round): all five top configs
    # passed the component gate at 3-4 SE (d_tune +0.0017, d_val +0.0011..0.0024);
    # full-pipeline arbiter on the plateau center: acc 0.6878->0.6883, Brier
    # 0.1984->0.1983, d_val +0.00041±0.00040 -> ADOPTED. Cross-surface transfer
    # (xsurf 0.27) reorganizes the geometry: blend 0.45->0.63, MOV factor halved
    # (transfer absorbs part of the margin signal), layoff boost moves to very
    # long absences (~400d), tier anchors flatten (see TIER_ANCHORS). The Bo5
    # rating-diff scale re-converged to 1.28 independently — robust effect.
    "atp": dict(k_scale=145.0, k_offset=5.0, k_shape=0.21,
                surface_k_scale=52.0, surface_k_shape=0.33, surface_blend=0.63,
                mov_factor=0.22, mov_cap=2.0, inact_days=400.0, inact_boost=0.44,
                bo5_scale=1.28, xsurf=0.27),
    # 400-trial `_xsurf` re-sweep with cross-surface transfer in the space
    # (2026-07-02 core round): all five top configs passed the component gate at
    # ~3 SE (d_tune +0.0027, d_val +0.0018..0.0021); full-pipeline arbiter on the
    # plateau center: acc 0.6822->0.6841, Brier 0.2024->0.2023, d_tune
    # +0.00060±0.00045, d_val -0.00032±0.00059 -> ADOPTED. Transfer reorganizes
    # the whole geometry: xsurf 0.17 feeds every surface from every result, so
    # the blend can trust surface ratings (0.375->0.62), the K curve steepens
    # (100/5/0.20 -> 320/1.5/0.37), surface K shrinks (130->45), and retirements
    # are down-weighted (0.72 — measured irrelevant only WITHOUT transfer).
    # bo5 stays default (WTA has no Bo5).
    "wta": dict(k_scale=320.0, k_offset=1.5, k_shape=0.37,
                surface_k_scale=45.0, surface_k_shape=0.40, surface_blend=0.62,
                mov_factor=0.22, mov_cap=1.65, ret_k_mult=0.72,
                inact_days=86.0, inact_boost=0.16, xsurf=0.17,
                form_days=65.0),   # `_fp1` 2026-07-06, adopted with FEAT_PARAM_OVERRIDES
}
SR_PARAM_OVERRIDES: dict = {
    # 200-trial sweep (tune ll 0.6091->0.5886, val 0.6400->0.6145): same story as
    # WTA — form halflife 540->200d, much harder shrinkage, surface serve deviations
    # nearly (not fully) noise. The 250-trial _xwide re-sweep (2026-07-02) found
    # 220/660/1900 passing the COMPONENT gate on both windows (+0.0002 point-model
    # LL), but the full-pipeline arbiter disagreed: combiner LL 0.5788->0.5791 on
    # 2010-26 after retraining on the shifted features — component gains this small
    # don't survive the combiner, so the incumbents stand.
    "atp": dict(form_halflife_days=200.0, serve_shrinkage_points=600.0,
                surface_serve_shrinkage=1400.0),
    # 200-trial sweep (tune ll 0.6402->0.6098, val 0.6460->0.6239): serve/return
    # form decays ~2.5x faster than assumed (halflife 540->200d), estimates shrink
    # much harder, and surface-specific serve deviations are ~noise (huge shrinkage
    # toward the player's global level — but global-ONLY measured worse, so finite).
    "wta": dict(form_halflife_days=200.0, serve_shrinkage_points=550.0,
                surface_serve_shrinkage=3000.0),
}
TIER_ANCHORS: dict = {"atp": (0.91, 0.89),
                      "wta": (1.22, 0.81)}  # (grand_slam, challenger); both re-tuned
                                            # with the xsurf geometry (2026-07-02) —
                                            # ATP flattens almost completely
XGB_PARAM_OVERRIDES: dict = {
    # 200-trial `_mcw` re-sweep with min_child_weight bound 50→400 and TPE anchored
    # at the prior adopted config (2026-07-02 core round). All five top configs
    # passed the gate on BOTH windows; this is the plateau center of the four
    # clustered ones (anchor #129: d_tune +0.00066±0.00024, d_val +0.00108±0.00030).
    # Full 2010–2026 arbiter vs the prior config: acc 0.6811→0.6821, Brier
    # 0.2027→0.2024, d_full +0.00058±0.00020 → ADOPTED. The optimum moved to a new
    # regularization regime (reg_alpha ~5 vs 0.002, mcw ~70 — the old 50 bound was
    # mildly binding; the new 400 bound is not). n_estimators is a CAP — early
    # stopping governs.
    # The ATP sweep remains REJECTED: every candidate beat the tune window but
    # regressed validation beyond ~1 SE (overfit) — ATP keeps the _xgb() defaults.
    "wta": dict(learning_rate=0.03, max_depth=7, min_child_weight=70.0,
                subsample=0.77, colsample_bytree=0.75, reg_alpha=5.0,
                reg_lambda=0.1, gamma=0.0005, n_estimators=2000),
}
FEAT_PARAM_OVERRIDES: dict = {   # FeatureParams per-tour overrides (group=feat sweeps;
                                 # form_days adoptions go into ELO_PARAM_OVERRIDES)
    # 20-trial `_fp1` sweep (2026-07-06, round R1): #13 was the only val-positive
    # passer (unbagged d_tune +0.00089±0.00035, d_val +0.00037±0.00046); full bagged
    # 2010-26 arbiter on the rounded config: d_tune +0.00084±0.00027, d_val
    # +0.00085±0.00038 (val gain == tune gain, 13/17 years positive), acc
    # 0.6829->0.6836, Brier 0.2018->0.2015 -> ADOPTED. Reading: the WTA layoff flag
    # is ~disabled (360d threshold ~never fires), fatigue windows lengthen, peak age
    # moves earlier, form decays faster (form_days 90->65, in ELO_PARAM_OVERRIDES).
    # The ATP `_fp1` arbiter was DECLINED (d_val -0.00006 — 4th ATP tune-overfit
    # instance); ATP keeps the shared defaults below.
    "wta": dict(fatigue_window_days=33.0, layoff_days=360.0, peak_age=24.0,
                winrate_window=23),
}

# Seed-bagging (W1a, adopted 2026-07-02): the combiner is the average of N_BAG
# seed-varied XGB fits (training orientation + tree seed vary; k=0 = the old single
# fit). Paired gate PASSED both tours (ATP d_tune +0.00174, d_val +0.00042; WTA
# +0.00093/+0.00074); ~0.001 full-window LL for pure variance reduction. bag10
# measured no better — 5 is the plateau. Sweeps still search n_bag=1 for speed;
# adoption gates re-score bagged.
N_BAG = 5

# ---------------------------------------------------------------------------
# Surfaces — Carpet (mostly pre-2009 indoor) folds into Hard for the surface bucket.
# ---------------------------------------------------------------------------
SURFACES = ("Hard", "Clay", "Grass")
SURFACE_MAP = {"Hard": "Hard", "Clay": "Clay", "Grass": "Grass", "Carpet": "Hard"}
# Surface by calendar month — the tennis season's surface swings — the LAST-resort fallback
# for a live/new event whose sponsor-named tournament misses the archive AND has no Wikipedia
# surface cached (data/surface.resolve_surface consults it after the archive + wiki tiers).
MONTH_SURFACE = {1: "Hard", 2: "Hard", 3: "Hard", 4: "Clay", 5: "Clay", 6: "Grass",
                 7: "Grass", 8: "Hard", 9: "Hard", 10: "Hard", 11: "Hard", 12: "Hard"}

# Round progression order (for chronological sorting within a tournament).
# Qualifying rounds share the main draw's tourney_id and start date, so they must
# sort strictly before R128 within the same event (negative = pre-main-draw).
ROUND_ORDER = {
    "Q1": -3, "Q2": -2, "Q3": -1,
    "RR": 0, "BR": 0, "R128": 1, "R64": 2, "R32": 3, "R16": 4,
    "QF": 5, "SF": 6, "3rd/4th": 6, "F": 7,
}

# ---------------------------------------------------------------------------
# Serve/return point model
# ---------------------------------------------------------------------------
# League-average fraction of service points won (men's ATP ~0.64). Each player's
# serve/return rating is expressed relative to this baseline.
AVG_SERVE_PCT = 0.64
# Exponential time-decay half-life (days) for serve/return form.
FORM_HALFLIFE_DAYS = 540.0
# Minimum service points behind a serve/return estimate before we trust it (else
# shrink toward the league average).
SERVE_SHRINKAGE_POINTS = 200.0
# Surface-specific estimates see less data, so they shrink (harder) toward the
# player's own global skill — a two-level hierarchical prior.
SURFACE_SERVE_SHRINKAGE = 120.0
# Event-speed baseline (E3): per-event serve-pct residual accumulator, shrunk toward
# 0 by this many service points. Fast/slow venues shift both players' serve probs and
# de-bias the credited serve/return skills. 0 = off (incumbent walk, bit-identical).
EVENT_SHRINKAGE = 0.0

# ---------------------------------------------------------------------------
# Context features (model/features.py) — rest/fatigue/form/age constants, carried
# on the frozen FeatureParams dataclass so sweeps and inference can't diverge.
# ---------------------------------------------------------------------------
FATIGUE_WINDOW_DAYS = 14.0    # rolling window for the games-played workload feature
LAYOFF_DAYS = 120.0           # idle-days threshold for the layoff flag
PEAK_AGE = 26.5               # center of the age curve (both tours, roughly)
WINRATE_WINDOW = 10           # last-N completed matches for the winrate10 feature

# ---------------------------------------------------------------------------
# Data health thresholds (data/health.py) — stale sources turn the daily build red
# instead of silently degrading (the Jan-2026 TML freeze went unnoticed for months).
# ---------------------------------------------------------------------------
HEALTH_MAX_RESULT_AGE_DAYS = 5        # newest completed match must be this recent
MAX_FUTURE_MATCH_DAYS = 60            # a RESULT dated further ahead than this is corrupt, not
                                      # scheduled: the live overlay only reaches 12 days forward
                                      # (live.fetch_events days_fwd), so 60 clears every genuine
                                      # fixture while still catching the realistic corruption —
                                      # a year typo (>=365d off). Load-bearing: one upstream row
                                      # dated 2029/7/20 instead of 2026/7/20 (WTA Iasi final,
                                      # 2026-07-25) pushed elo.last_date three years out, so the
                                      # ACTIVE_DAYS=550 window left only the 2 players in that
                                      # row "active" — the WTA export shipped 2 players instead
                                      # of 200 and build_draws crashed on the 2-slot bracket.
HEALTH_MAX_STATS_AGE_DAYS = 16        # newest row carrying serve stats. ATP stats rows are
                                      # anchored on the tournament START date (Sackmann
                                      # tourney_date), so a slam fortnight legitimately parks
                                      # the newest date ~15d back (start Monday -> the next
                                      # events' rows land day 15); 16 clears that while the
                                      # real failure class (TML site frozen) is still caught.
HEALTH_MAX_FUTURE_DATE_DAYS = 14      # newest match date may not sit further ahead than this.
                                      # Deliberately TIGHTER than MAX_FUTURE_MATCH_DAYS: dropping
                                      # rows is destructive so ingest is permissive, while merely
                                      # REPORTING is cheap. In practice date_max runs a day or two
                                      # behind (the merged frame carries completed results, not the
                                      # live overlay's scheduled rows), so 14 clears reality by a
                                      # wide margin and still catches what ingest let through.
HEALTH_OFFSEASON_RELAX_DAYS = 45      # December: tours are dark, staleness is expected
# Minimum has_stats fraction for the current season, per tour (WTA runs lower than
# ATP because 125-level results carry no stats by design).
HEALTH_MIN_STATS_FRACTION = {"atp": 0.60, "wta": 0.55}
# Per-source freshness: the merged result_age can't see ONE source freeze (the ESPN live
# overlay keeps the merged maximum current), so the silent sources get their own age gates.
HEALTH_MAX_FRESH_AGE_DAYS = 14      # TennisCourtLog overlay updates ~weekly; 14 = two missed
                                    # cycles. Off-season + early January relax to
                                    # HEALTH_OFFSEASON_RELAX_DAYS (weekly updater lags the
                                    # season restart). Enforced only while the stats overlay
                                    # is ALSO stale: the fresh overlay is a redundancy layer,
                                    # and a frozen-but-shadowed source (TennisCourtLog's ATP
                                    # file, 2026-06-22) is a standing red no local action
                                    # can clear — see health.problems().
HEALTH_MAX_CHARTING_AGE_DAYS = 90   # MCP is volunteer batch-updated (a 50d mid-season lag is
                                    # normal); 90 targets the real failure class — repo
                                    # moved/renamed/frozen. Exceeds the longest seasonal gap
                                    # (mid-Nov Finals -> AO chartings landing ~Feb), so no
                                    # off-season term needed.
HEALTH_MAX_FORECAST_AGE_DAYS = 5    # forecast_log max(as_of) — the log appends on every run
                                    # while any upcoming match exists (in-season gaps run
                                    # 2-3d); catches a silently-failing track step within a
                                    # week. Matches HEALTH_MAX_RESULT_AGE_DAYS cadence.

# Produced-output validation (data/health.py::output_problems) — the daily build also
# checks that the JSON the web reads is sane, not just that the sources are fresh.
HEALTH_MIN_MATCHES = {"atp": 250_000, "wta": 100_000}   # match-count floor (now ~283k / ~129k)
HEALTH_MAX_BUILD_AGE_DAYS = 3        # meta.lastUpdated staleness — the full build runs daily year-round
HEALTH_MAX_MODEL_AGE_DAYS = 3        # meta.modelTrainedAt staleness. NOT the same thing as the
                                    # line above: every export stamps lastUpdated, including the
                                    # hourly quick refresh, which republishes the PREVIOUS
                                    # predictor.pkl. So a daily retrain that has been red for days
                                    # leaves the site looking freshly built while the model behind
                                    # it rots (2026-07-19..24: 5 silent days). Same 3d ceiling as
                                    # the build age = three consecutive missed retrains.
# ---------------------------------------------------------------------------
# Event identity (data/events.py)
# ---------------------------------------------------------------------------
# How long a registry entry survives without being seen in ESPN's window. ESPN ids are
# year-scoped (888-2026 -> 888-2027), so growth is ~80 entries/tour/year and a full season of
# alias history costs nothing. An entry still referenced by a wiki cache is NEVER pruned
# regardless of age — a cached draw outliving the entry that names it is how the field lost
# its anchor and padded to an impossible 256-slot bracket (2026-07-11 and again 07-27).
EVENT_REGISTRY_RETENTION_DAYS = 400

# Grace after an event's scheduled end before the board may call it complete without having
# seen a round-"F" row. Two days absorbs a final pushed by rain or a late-night finish; beyond
# that, a missing final is a dropped result, not an event still in progress. Iasi sat "live"
# with three players alive for NINE days because completion keyed only on that row.
EVENT_CALENDAR_COMPLETE_GRACE_DAYS = 2

# How long a cached complete draw survives after ESPN stops listing its event. MUST exceed
# the 40-day `sim.tournaments.recent_tournaments` window: the cache has to outlive the
# discovery sweep it was populated from, because `build_tournaments` keeps projecting an event
# for weeks after ESPN drops it. Pruning on "is ESPN still tracking this?" deleted Wimbledon's
# draw mid-projection — the field lost its anchor, fell back to a noisy results union and
# padded to an impossible 256-slot bracket, taking the whole board down (2026-07-11, and again
# on 07-27 when the 07-11 fix turned out to depend on that very cache still being there).
TOURNAMENT_DRAW_RETENTION_DAYS = 45
# Compatibility for the Wikipedia metadata helpers while draw authority itself is
# source-neutral (`data/draws.py`). New draw code uses TOURNAMENT_DRAW_RETENTION_DAYS.
WIKI_DRAW_RETENTION_DAYS = TOURNAMENT_DRAW_RETENTION_DAYS


HEALTH_MAX_UPCOMING_START_LAG_DAYS = 3  # an "upcoming" event whose start date is further past
                                        # than this never flipped live — its results are not
                                        # joining. Needs slack, not a strict start<=today:
                                        # ESPN start dates include QUALIFYING, so a main draw
                                        # legitimately reads "upcoming" for a couple of days
                                        # (and every Slam does, for a week).
HEALTH_MAX_LIVE_EVENT_AGE_DAYS = 2    # a "live" event whose newest match is older than this
                                      # has either lost its final and stuck live (Iasi sat live
                                      # for 9 days) or gone blind mid-draw (2026-08-05: ESPN
                                      # 403'd the overlay and Toronto showed Zverev alive at 21%
                                      # for three days after he lost). Tour weeks run Mon-Sun, so
                                      # a genuine in-progress event is never 3 days idle — which
                                      # is what this bounds, since the check fires ABOVE it. It
                                      # read 3 until 2026-08-06, one day slacker than that intent.
HEALTH_MAX_LIVERANK_NULL_FRAC = 0.30  # top-200 without a live rank -> rankings source drifted (normal ~3-9%)
# market.json: matched odds may trail the newest scored match by at most this — a larger
# gap means the odds feed dropped a book and the benchmark window silently froze
# (Pinnacle left tennis-data mid-January 2026 and the card sat frozen for months).
HEALTH_MAX_MARKET_LAG_DAYS = 60

# Forecast drift monitor (eval/track.py::_drift_block → track.json matchForecasts.drift,
# surfaced ADVISORY by data/health.py). d = mean(realized logloss − forecast entropy) over
# the trailing window of graded live forecasts; d > 0 = the model scores WORSE than its own
# stated confidence (overconfident = decayed) → an off-cycle re-tune is worth considering.
# The window is filtered to model_version == __version__ — BUMP __version__ WHEN RE-TUNING
# so the monitor resets to the new model instead of latching on the old one's forecasts.
DRIFT_WINDOW_DAYS = 90     # trailing window, anchored to the newest graded result date
DRIFT_MIN_N = 150          # below this the t-stat is noise -> status "insufficient"
DRIFT_TRIGGER_K = 2.5      # fire when d > K*SE (one-sided; daily correlated looks)
DRIFT_MIN_EXCESS = 0.02    # ...AND d > this floor (nats) — practical significance

# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------
DEFAULT_N_SIMS = 20_000

# ---------------------------------------------------------------------------
# Validation / odds benchmark (Tennis-Data.co.uk) — one XLSX per tour-year with
# Pinnacle/Bet365/market-average closing odds, refreshed weekly by the site.
# ---------------------------------------------------------------------------
ODDS_SOURCE = {
    "atp": "http://www.tennis-data.co.uk/{year}/{year}.xlsx",
    "wta": "http://www.tennis-data.co.uk/{year}w/{year}.xlsx",
}


def odds_dir(tour: str) -> Path:
    return ODDS_DIR / tour       # per-tour subdirs: mixing would corrupt the benchmark


# ---------------------------------------------------------------------------
# Wikipedia fallback draw + event metadata (MediaWiki API). First-party ATP/WTA artifacts
# are selected in data/draws.py; this provider supplies an ordered fallback plus the
# main-article surface/tier fields. ESPN remains the incremental partial frontier.
# ---------------------------------------------------------------------------
WIKI_API = "https://en.wikipedia.org/w/api.php"
# Wikimedia etiquette REQUIRES a descriptive User-Agent with contact info (generic UAs
# get blocked) and asks for sequential (not parallel) requests — we make a few/day.
WIKI_UA = "TennisEloModel/1.0 (https://github.com/; av3342@columbia.edu)"
# ESPN sponsor name -> exact Wikipedia article base (year is prefixed, "– Singles"/
# "– Men's singles"/"– Women's singles" is appended at resolve time). Only needed when
# the search API can't disambiguate; keep small, extend when draws_wiki logs a miss.
WIKI_TITLE_OVERRIDES: dict[str, str] = {
    # Main-article metadata alias only: it supplies Los Cabos surface/tier evidence. A main
    # page is not necessarily a singles-bracket page, which is why draw location now belongs
    # to the first-party/source-neutral architecture instead of reusing this alias.
    "Mifel Tennis Open by Telcel Oppo": "Los Cabos Open",
}

# Provider tournament ids are source locators, never event join keys. Normal events resolve
# from official calendars / the historical ATP id archive and persist under events.json
# `sourceIds`; this reviewed table is only for sponsor-renamed or newly moved exceptions.
OFFICIAL_DRAW_ID_OVERRIDES: dict[str, dict[str, str]] = {
    "atp": {
        # Mifel's ESPN title is the stable ATP Los Cabos event (official id 7480).
        "424-2026": "7480",
        # Combined-event sponsor title; ATP's stable Washington id is 418.
        "888-2026": "418",
        # Estoril moved from its usual spring slot in 2026, outside the archive resolver's
        # seasonal candidate window. The provider id itself remains stable.
        "400-2026": "7290",
        # Canadian Masters sponsor title; ATP's Toronto edition uses provider id 421.
        "421-2026": "421",
    },
    "wta": {
        "888-2026": "1045",   # Washington DC
        "875-2026": "2064",   # Odlum Brown VanOpen / Vancouver 125
        "1073-2026": "1163",  # Axeria Open / Targu Mures 125
        "421-2026": "806",    # National Bank Open / Montreal
        "961-2026": "2087",   # T-Mobile Polish Open / Warsaw 125
    },
}

# Public event labels are familiar place/event names, not whichever sponsor title a feed
# happens to publish this week. Exact ESPN edition ids take precedence; a numeric-series key
# is a safe fallback only when the host is unknown (the Canadian Masters rotates cities).
# Identity and provider joins still use espnId/sourceIds — this table is display metadata only.
# The Canadian Masters SWAPS CITIES EVERY YEAR and the two tours are always in opposite
# cities, so a per-edition entry here is a claim about a specific year that silently rots at
# the next one. 2026 is men's Montreal (IGA Stadium) / women's Toronto (Sobeys Stadium); these
# two read the other way round until 2026-08-07, so the men's board was labelled Toronto for
# an event played in Montreal and the women's Montreal for one played in Toronto. ESPN cannot
# settle it — it reports "Toronto, Canada" as the venue for BOTH tours' 421-2026, which is
# exactly why this table exists. The provider ids agree with the corrected labels: WTA 806 is
# the Toronto edition (wtatennis.com/tournaments/806/toronto), ATP 421 the Montreal one.
# ADDING A NEW YEAR: check which city each tour is in before copying the previous entry.
EVENT_DISPLAY_NAME_OVERRIDES: dict[str, dict[str, str]] = {
    "atp": {
        "421-2026": "Montreal",
        "421": "Canada",
    },
    "wta": {
        "421-2026": "Toronto",
        "421": "Canada",
    },
}

# Above this many drawn players missing from a live field, assume the FEED is broken rather
# than that the tournament emptied out, and derive nothing. Real withdrawals are a trickle —
# Toronto and Warsaw each had exactly one — while a feed that briefly under-reports drops them
# in bulk, and acting on that would delete real contenders from the board.
MAX_DERIVED_WITHDRAWALS = 4

# Players who left an event WITHOUT losing a match, mapped to whoever took their slot.
# Eliminations are derived from loser rows, so a withdrawal produces no evidence anything
# can act on: the player sits in the released ordered draw with an unplayed match forever,
# survives `field_pool - eliminated`, and keeps collecting title odds. On 2026-08-06 that
# made Felix Auger-Aliassime — who pulled out with a back injury two hours before his
# opener, having never hit a ball — the Toronto FAVOURITE at 14.3%.
#
# The value is the REPLACEMENT, or None for a walkover, because the tour resolves the two
# cases differently and the draw is only honest if it says which happened:
#   * withdrawal BEFORE the player's first match -> a lucky loser enters that slot, and the
#     match is played normally. Auger-Aliassime's slot went to Jaime Faria, who lost it to
#     Titouan Droguet 7-6 6-2. Modelling this as a walkover would invent a match that never
#     happened AND erase one that did.
#   * retirement/withdrawal MID-EVENT -> no replacement is admitted and the opponent is
#     awarded a walkover.
#
# STOPGAP, not the mechanism: the real signal is already downloaded. ESPN's field for the
# event carries the replacement and drops the withdrawn player, so both the substitution and
# the walkover are derivable without a hand-maintained list. Keyed by ESPN edition id, never
# by name — see the events-join rule in AGENTS.md.
# EMPTY IS THE EXPECTED STATE. `sim/tournaments._derive_withdrawals` now works this out from
# evidence, and was checked against both cases that used to be listed here: it reproduces
# Auger-Aliassime -> Jaime Faria at Toronto and Jeline Vandromme -> Marcelina Podlinska at
# Warsaw with this table empty. An entry belongs here only when the evidence genuinely cannot
# settle a case — two candidates that both fit, or a replacement whose results never joined —
# and `drawnNotInField` will name the event and player when that happens.
EVENT_WITHDRAWN_PLAYERS: dict[str, dict[str, dict[str, str | None]]] = {
    "atp": {},
    "wta": {},
}


# ---------------------------------------------------------------------------
# Player aliases — ONE person our sources spell two ways.
# ---------------------------------------------------------------------------
# data/results.py `_canonicalize_names` already unifies spellings that differ only by
# accents or punctuation, because those share a `_name_key`. A DROPPED OR ADDED SURNAME
# changes the key itself, so that pass can never merge them and the player ships as two
# people: Umag 2026 exported drawSize 29 for a 28-draw, aliveCount 2 on a finished event,
# and split the champion's retrospective title odds across both identities.
# Keyed by `_name_key(variant)` -> the canonical spelling to keep. Deliberately a hand-kept
# list, not a heuristic: "shorter name is a prefix of the longer" would merge genuine
# relatives (the Zverevs, the Bryans). Add an entry when the health gate flags one, or when
# `data/alias_proposer.py` opens a PR proposing one (that path is reviewed, never automatic).
PLAYER_ALIASES: dict[str, str] = {
    "daniel merida aguilar": "Daniel Merida",
    # 2026-07-29 Wimbledon duplicate: the archive's 360-match spelling and the live feed's
    # 2-match inserted-space spelling describe one player. Without this the same match walks
    # ratings twice and the completed Slam grows a phantom 129th entrant.
    "soon woo kwon": "Soonwoo Kwon",
    # 2026-07-29 Athens duplicate: western and family-name-first order describe one player
    # (207 archive matches versus 4 under the reversed live spelling).
    "zheng qinwen": "Qinwen Zheng",
    # Found by the alias proposer's DETERMINISTIC half on 2026-07-28, before any model call:
    # 36 matches as "Diego Dedura", 3 as "Diego Dedura-Palomero", and Stuttgart 2026-06-09
    # carries BOTH — "James Duckworth d. Diego Dedura" and "James Duckworth d. Diego
    # Dedura-Palomero" are one match written twice, which is proof rather than inference.
    # Two Elo histories for one 2007-born German, and the shorter spelling holds the rating.
    "diego dedura palomero": "Diego Dedura",
    # 2026-07-28 live scan: Los Cabos used the full name on an id-less ESPN row while the
    # archive's 180+ matches use Coleman Wong under ATP player id W0BH. ATP's player URL and
    # its own Hong Kong media notes use the full name for that same profile.
    # https://www.atptour.com/en/players/chak-lam-coleman-wong/w0bh/overview
    "chak lam coleman wong": "Coleman Wong",
    # 2026-07-28 alias-proposer: ATP short form and ITF full form identify one player.
    # https://www.atptour.com/en/players/adrian-boitan/b0c0/overview
    "gabi adrian boitan": "Adrian Boitan",
    # 2026-07-28 alias-proposer: both forms carry ATP player id M0WY.
    # https://www.atptour.com/en/players/luis-guto-miguel/m0wy/overview
    "luis guto miguel": "Guto Miguel",
    # 2026-07-28 alias-proposer: both forms identify ATP player RD48.
    # https://www.atptour.com/en/players/igor-marcondes/rd48/overview
    "igor ribeiro marcondes": "Igor Marcondes",
    # 2026-07-28 alias-proposer: ATP pages use both forms under player id S0WT.
    # https://www.atptour.com/en/players/joel-schwaerzler/s0wt/overview
    "joel josef schwaerzler": "Joel Schwaerzler",
    # 2026-07-28 alias-proposer: this third form also carries ATP player id M0WY.
    # https://www.atptour.com/en/players/luis-guto-miguel/m0wy/overview
    "luis miguel": "Guto Miguel",
    # 2026-07-28 alias-proposer: WTA short form and full name identify one player.
    # https://www.wtatennis.com/players/326044/caijsa-hennemann
    "caijsa wilda hennemann": "Caijsa Hennemann",
    # 2026-07-28 alias-proposer: WTA short form and full name identify one player.
    # https://www.wtatennis.com/players/321367/gabriela-knutson
    "gabriela andrea knutson": "Gabriela Knutson",
    # 2026-07-28 alias-proposer: WTA short form and full name identify one player.
    # https://www.wtatennis.com/players/327490/ilinca-amariei
    "ilinca dalina amariei": "Ilinca Amariei",
    # 2026-07-28 alias-proposer: WTA short form and full name identify one player.
    # https://www.wtatennis.com/players/321157/irene-burillo
    "irene burillo escorihuela": "Irene Burillo",
    # 2026-07-28 alias-proposer: WTA short form and full name identify one player.
    # https://www.wtatennis.com/players/329464/maria-torres-murcia
    "maria camila torres murcia": "Maria Torres Murcia",
    # 2026-07-28 alias-proposer: WTA short form and ITF full form identify one player.
    # https://www.itftennis.com/en/players/miriam-bianca-bulgaru/800333881/rou/wt/d/
    "miriam bianca bulgaru": "Miriam Bulgaru",
    # 2026-07-28 alias-proposer: WTA short form and ITF full form identify one player.
    # https://www.itftennis.com/en/players/tiantsoa-sarah-rakotomanga-rajaonah/800507833/fra/jt/D/overview/
    "tiantsoa sarah rakotomanga rajaonah": "Tiantsoa Rakotomanga Rajaonah",
    # 2026-08-07 alias-proposer: The ATP site shows both spellings on the same SY71 player profile, with the canonical display name as Digvijay Pratap Singh.
    # https://www.atptour.com/en/players/digvijay%20pratap-singh/sy71/player-stats
    "digvijaypratap singh": "Digvijay Pratap Singh",
    # 2026-08-07 alias-proposer: The official ATP profile uses Christopher O'Connell, and Tennis Abstract lists the same Australian player as Christopher Oconnell with matching birth-date/ranking context.
    # https://www.atptour.com/en/players/christopher-oconnell/o483/overview
    "christopher oconnell": "Christopher O'Connell",
    # 2026-08-08: family-name-first and western order for Ma Yexin (马烨欣), CHN. Surfaced by
    # _derive_withdrawals, which "resolved" the Memphis Classic draw by substituting the feed's
    # spelling into the slot — correct for the board, but it was papering over a split identity
    # rather than a withdrawal. Checked against the same rules falsify() applies: the two never
    # played each other, carry no conflicting stable ids, and both appear in the record (5
    # matches as the archive spelling, 2 as the reversed one). Canonical follows the archive
    # majority, as with "zheng qinwen"; the WTA's own listing hyphenates it as "Ye-Xin Ma".
    # https://www.wtatennis.com/players/322417/ye-xin-ma
    # https://www.itftennis.com/en/players/yexin-ma/800439388/chn/wt/D/overview/
    "ma yexin": "Ye Xin Ma",
    # 2026-08-17 Cincinnati duplicates: the stable WTA feed and ESPN record the same
    # opponents, dates and scores under family-name-first vs western order. Keep these
    # explicit: general token reversal would merge unrelated people.
    "zhang shuai": "Shuai Zhang",
    "wang xiyu": "Xiyu Wang",
    "wang xinyu": "Xinyu Wang",
    # The same cross-source Cincinnati evidence uses ESPN's full name for the stable/archive
    # nickname. Keep the 133-match historical spelling, not the five-match live fragment.
    "catherine mcnally": "Caty Mcnally",
}


BACKTEST_START_YEAR = 2010    # walk-forward evaluation window start
# Adoption-protocol windows (eval/tune.py sweeps + eval/ab_data.py arbiter share these;
# also published to the site via model.export.build_method).
TUNE_YEARS = (2010, 2019)     # the only window the optimizer ever sees
VAL_START = 2020              # held-out validation window start (2020..latest)
