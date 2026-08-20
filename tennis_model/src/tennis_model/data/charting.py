"""Match Charting Project tactical profiles.

The MCP charts shot-by-shot detail for a *subset* of matches (~12% of the tour,
star-biased — so it can't drive ratings), but it is the best source for *playing
style*. Style is a slowly-varying player attribute, so we aggregate each player's
charted matches into one profile and (in model/features) attach it as a feature to
every match that player plays — with a `has_style` flag so the combiner only leans
on it when both players are profiled.

Profiles (career aggregate, per player): serve dominance, serve-placement variety,
net frequency, serve-and-volley rate, aggression (winners vs errors), forehand/
backhand balance, return depth, and break-point serving clutch.
"""

from __future__ import annotations

import glob
import io
import math
import os
import subprocess
import urllib.request
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import RAW_DIR

CHARTING_DIR = RAW_DIR / "charting"
_GENDER = {"atp": "m", "wta": "w"}
_CHARTING_REPO = "JeffSackmann/tennis_MatchChartingProject"
_CHARTING_FILES = ["matches", "stats-Overview", "stats-ServeBasics", "stats-ServeDirection",
                   "stats-NetPoints", "stats-SnV", "stats-ReturnDepth", "stats-KeyPointsServe"]


def _via_https(filename: str) -> bytes | None:
    try:
        url = f"https://raw.githubusercontent.com/{_CHARTING_REPO}/master/{filename}"
        req = urllib.request.Request(url, headers={"User-Agent": "tennis_model"})
        with urllib.request.urlopen(req, timeout=60) as response:
            return response.read()
    except Exception:  # noqa: BLE001 — authenticated GitHub API is the fallback transport
        return None


def _via_gh(filename: str) -> bytes | None:
    try:
        out = subprocess.run(
            ["gh", "api", "-H", "Accept: application/vnd.github.raw",
             f"repos/{_CHARTING_REPO}/contents/{filename}"],
            capture_output=True, timeout=90,
        )
        return out.stdout if out.returncode == 0 else None
    except Exception:  # noqa: BLE001 — caller reports the exhausted transport chain
        return None


def _valid_charting_csv(data: bytes | None, filename: str) -> bool:
    """Reject HTML/error payloads before they can replace the last good style input."""
    if not data or len(data) < 100:
        return False
    try:
        head = pd.read_csv(io.BytesIO(data), encoding="utf-8-sig", nrows=5)
    except Exception:  # noqa: BLE001 — an unparseable payload is not a charting CSV
        return False
    required = (
        {"match_id", "Player 1", "Player 2"}
        if filename.endswith("-matches.csv")
        else {"match_id", "player"}
    )
    return required.issubset(head.columns)


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def download_charting() -> tuple[list[str], list[str]]:
    """Fetch MCP style inputs, returning exact (downloaded, failed) filenames."""
    CHARTING_DIR.mkdir(parents=True, exist_ok=True)
    done, failed = [], []
    for g in ("m", "w"):
        for f in _CHARTING_FILES:
            fn = f"charting-{g}-{f}.csv"
            for fetch in (_via_https, _via_gh):
                data = fetch(fn)
                if _valid_charting_csv(data, fn):
                    _atomic_write(CHARTING_DIR / fn, data)
                    done.append(fn)
                    break
            else:
                failed.append(fn)
    msg = f"  charting: downloaded {len(done)} file(s)"
    if failed:
        msg += f", FAILED {len(failed)}: {failed}"
    print(msg)
    return done, failed

# the eight style features (anti-symmetric A-B diffs once paired up)
STYLE_FEATURES = [
    "style_serve_dom", "style_placement", "style_net", "style_snv",
    "style_aggression", "style_fhbh", "style_return_depth", "style_bp_clutch",
]
MIN_SERVE_PTS = 200          # need this many charted serve points to trust a profile


# single shared implementation (kept importable here as charting.name_key — the
# established path used by model/features and model/predict)
from .names import name_key  # noqa: E402

_key = name_key


def _read(tour: str, name: str) -> pd.DataFrame:
    g = _GENDER[tour]
    files = glob.glob(str(CHARTING_DIR / f"charting-{g}-{name}.csv"))
    if not files:
        return pd.DataFrame()
    return pd.read_csv(files[0], encoding="utf-8-sig", low_memory=False)


def _totals(df: pd.DataFrame, row_val: str = "Total") -> pd.DataFrame:
    """Keep the per-match aggregate rows and sum the numeric columns per player."""
    if df.empty:
        return df
    rowcol = "set" if "set" in df.columns else "row"
    if rowcol in df.columns:
        df = df[df[rowcol].astype(str) == row_val]
    num = df.select_dtypes("number").columns
    return df.groupby("player")[list(num)].sum()


def _entropy(parts: np.ndarray) -> float:
    tot = parts.sum()
    if tot <= 0:
        return np.nan
    p = parts[parts > 0] / tot
    return float(-(p * np.log(p)).sum() / math.log(len(parts)))  # normalised 0..1


@lru_cache(maxsize=4)
def build_profiles(tour: str) -> dict:
    """Return {player_key: {style feature: value}} for a tour (cached)."""
    ov = _totals(_read(tour, "stats-Overview"))
    sb = _totals(_read(tour, "stats-ServeBasics"))
    sd = _totals(_read(tour, "stats-ServeDirection"))
    np_ = _totals(_read(tour, "stats-NetPoints"), "NetPoints")
    snv = _totals(_read(tour, "stats-SnV"), "SnV")
    rd = _totals(_read(tour, "stats-ReturnDepth"))
    kp = _totals(_read(tour, "stats-KeyPointsServe"), "BP")
    if ov.empty:
        return {}

    out: dict = {}
    for player, o in ov.iterrows():
        sp = o.get("serve_pts", 0)
        if not sp or sp < MIN_SERVE_PTS:
            continue
        rp = o.get("return_pts", 0)
        b, s, _d, n, v, r, k = (sb.loc[player] if player in sb.index else None,
                               sd.loc[player] if player in sd.index else None,
                               None, np_.loc[player] if player in np_.index else None,
                               snv.loc[player] if player in snv.index else None,
                               rd.loc[player] if player in rd.index else None,
                               kp.loc[player] if player in kp.index else None)
        winners, unforced = o.get("winners", 0), o.get("unforced", 0)
        fh, bh = o.get("winners_fh", 0), o.get("winners_bh", 0)
        unret = b.get("unret", 0) if b is not None else 0
        serve_win = (o.get("first_won", 0) + o.get("second_won", 0)) / sp if sp else np.nan

        feat = {
            "style_serve_dom": (o.get("aces", 0) + unret) / sp,
            "style_placement": _entropy(np.array([s.get(c, 0) for c in
                               ("deuce_wide", "deuce_middle", "deuce_t", "ad_wide", "ad_middle", "ad_t")]))
                               if s is not None else np.nan,
            "style_net": (n.get("net_pts", 0) / (sp + rp)) if (n is not None and sp + rp) else 0.0,
            "style_snv": (v.get("snv_pts", 0) / sp) if v is not None else 0.0,
            "style_aggression": winners / (winners + unforced) if (winners + unforced) else np.nan,
            "style_fhbh": fh / (fh + bh) if (fh + bh) else np.nan,
            "style_return_depth": ((r.get("deep", 0) + r.get("very_deep", 0)) / r.get("returnable", 0))
                                  if (r is not None and r.get("returnable", 0)) else np.nan,
            "style_bp_clutch": (k.get("pts_won", 0) / k.get("pts", 0) - serve_win)
                               if (k is not None and k.get("pts", 0) and not np.isnan(serve_win)) else np.nan,
        }
        out[_key(player)] = {kk: (float(vv) if vv == vv else np.nan) for kk, vv in feat.items()}
    return out


if __name__ == "__main__":
    import sys
    tour = sys.argv[1] if len(sys.argv) > 1 else "atp"
    prof = build_profiles(tour)
    print(f"[{tour}] {len(prof)} player profiles")
    for nm in ("john isner", "novak djokovic", "rafael nadal", "aryna sabalenka", "iga swiatek"):
        if nm in prof:
            print(f"  {nm:18s}", {k: round(v, 3) if v == v else None for k, v in prof[nm].items()})
