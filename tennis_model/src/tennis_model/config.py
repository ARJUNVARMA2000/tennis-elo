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
# Simulation
# ---------------------------------------------------------------------------
DEFAULT_N_SIMS = 20_000

# ---------------------------------------------------------------------------
# Validation / odds benchmark (Tennis-Data.co.uk)
# ---------------------------------------------------------------------------
ODDS_BASE_URL = "http://www.tennis-data.co.uk/{year}/{year}.zip"
BACKTEST_START_YEAR = 2010    # walk-forward evaluation window start
