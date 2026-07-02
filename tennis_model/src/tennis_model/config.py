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

TOURS = ("atp", "wta")


def historical_dir(tour: str) -> Path:
    return RAW_DIR / tour / "historical"


def fresh_dir(tour: str) -> Path:
    return RAW_DIR / tour / "fresh"


def live_dir(tour: str) -> Path:
    return RAW_DIR / tour / "live"      # ESPN same-day overlay (lowest de-dup priority)


def output_dir(tour: str) -> Path:
    return OUTPUT_DIR / tour


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
    },
    "wta": {  # full-schema WTA snapshot (serve stats), through 2024
        "repo": "zeldao08/tennis_players_analysis",
        "path": "files/wta/wta_matches_{year}.csv",
        "raw": "https://raw.githubusercontent.com/zeldao08/tennis_players_analysis/main/files/wta/wta_matches_{year}.csv",
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
TML_STATS_SOURCE = {
    "files_api": "https://stats.tennismylife.org/api/data-files",
    "data_url": "https://stats.tennismylife.org/data/{name}",
    "year_file": "{year}.csv",                      # tour-level main draws
    "challenger_file": "{year}_challenger.csv",     # A5 experiment (INCLUDE_CHALLENGERS)
    "first_year": 2018,
}
INCLUDE_CHALLENGERS = False   # gate for the Challenger-ingestion experiment


def stats_dir(tour: str) -> Path:
    return RAW_DIR / tour / "stats"     # daily full-schema overlay (TML site / WTA scraper)


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

# ---------------------------------------------------------------------------
# Tournament tiers — importance multiplier on K, keyed by `tourney_level`.
# TML levels: G=Slam, F=Tour Finals, M=Masters 1000, 500/250=ATP tour, A=other
# (pre-2009 tour), O=Olympics, D=Davis Cup, C=Challenger.
# ---------------------------------------------------------------------------
TIER_NAMES = {
    # historical Sackmann/TML codes
    "G": "grand_slam", "F": "tour_finals", "M": "masters", "O": "olympics",
    "500": "atp500", "250": "atp250", "A": "atp250", "D": "davis_cup", "C": "challenger",
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

# ---------------------------------------------------------------------------
# Per-tour tuned overrides (eval/tune.py sweeps; tune window 2010-2019, validated
# on 2020+). An empty dict keeps the shared defaults above. TIER_ANCHORS rescales
# TIER_K_MULT linearly between (grand_slam, challenger) anchors; None keeps it.
# ---------------------------------------------------------------------------
ELO_PARAM_OVERRIDES: dict = {
    # 650-trial TPE sweep, plateau-center values (tune ll 0.5956->0.5860, val
    # 0.6387->0.6208). Near-flat K curve with strong MOV weighting, mild layoff
    # boost, and a REAL Bo5 effect: slam favorites' rating edge scales x1.28.
    "atp": dict(k_scale=40.0, k_offset=25.0, k_shape=0.10,
                surface_k_scale=45.0, surface_k_shape=0.31, surface_blend=0.45,
                mov_factor=0.45, mov_cap=2.5, inact_days=80.0, inact_boost=0.15,
                bo5_scale=1.28),
    # 400-trial TPE sweep, plateau-center values (tune ll 0.6196->0.6096, val
    # 0.6294->0.6168). Flatter K curve, softer MOV, blend 0.5->0.375, and a real
    # layoff K-boost (+47%/idle-year after ~110 days out). bo5/ret stay default
    # (WTA has no Bo5; retirement down-weight measured ~irrelevant).
    "wta": dict(k_scale=100.0, k_offset=5.0, k_shape=0.20,
                surface_k_scale=130.0, surface_k_shape=0.56, surface_blend=0.375,
                mov_factor=0.20, mov_cap=1.85, inact_days=110.0, inact_boost=0.47),
}
SR_PARAM_OVERRIDES: dict = {
    # 200-trial sweep (tune ll 0.6091->0.5886, val 0.6400->0.6145): same story as
    # WTA — form halflife 540->200d, much harder shrinkage, surface serve deviations
    # nearly (not fully) noise.
    "atp": dict(form_halflife_days=200.0, serve_shrinkage_points=600.0,
                surface_serve_shrinkage=1400.0),
    # 200-trial sweep (tune ll 0.6402->0.6098, val 0.6460->0.6239): serve/return
    # form decays ~2.5x faster than assumed (halflife 540->200d), estimates shrink
    # much harder, and surface-specific serve deviations are ~noise (huge shrinkage
    # toward the player's global level — but global-ONLY measured worse, so finite).
    "wta": dict(form_halflife_days=200.0, serve_shrinkage_points=550.0,
                surface_serve_shrinkage=3000.0),
}
TIER_ANCHORS: dict = {"atp": (1.15, 0.95), "wta": (0.93, 0.68)}  # (grand_slam, challenger)

# ---------------------------------------------------------------------------
# Surfaces — Carpet (mostly pre-2009 indoor) folds into Hard for the surface bucket.
# ---------------------------------------------------------------------------
SURFACES = ("Hard", "Clay", "Grass")
SURFACE_MAP = {"Hard": "Hard", "Clay": "Clay", "Grass": "Grass", "Carpet": "Hard"}

# Round progression order (for chronological sorting within a tournament).
ROUND_ORDER = {
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

# ---------------------------------------------------------------------------
# Data health thresholds (data/health.py) — stale sources turn the daily build red
# instead of silently degrading (the Jan-2026 TML freeze went unnoticed for months).
# ---------------------------------------------------------------------------
HEALTH_MAX_RESULT_AGE_DAYS = 5        # newest completed match must be this recent
HEALTH_MAX_STATS_AGE_DAYS = 12        # newest row carrying serve stats
HEALTH_OFFSEASON_RELAX_DAYS = 45      # December: tours are dark, staleness is expected
# Minimum has_stats fraction for the current season, per tour (WTA runs lower than
# ATP because 125-level results carry no stats by design).
HEALTH_MIN_STATS_FRACTION = {"atp": 0.60, "wta": 0.55}

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


BACKTEST_START_YEAR = 2010    # walk-forward evaluation window start
