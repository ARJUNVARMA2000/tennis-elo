"""Attributed, evaluation-only closing odds; never a predictor input."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import tempfile
import urllib.request
from datetime import UTC, datetime

import pandas as pd

from ..config import ODDS_DIR, PLAYER_ALIASES
from .names import name_key

SOURCE_URL = "https://www.valuebetennis.com/en/donnees.htm"
DATA_URL = "https://www.valuebetennis.com/datasets/valuebetennis-matchs-{year}.csv"
ATTRIBUTION = "Valuebetennis, Tennis results and odds since 2021 (CC BY 4.0)"
_CATEGORIES = {"Main tour", "Masters", "Grand Chelem"}
_SURFACES = {"dur": "Hard", "dur intérieur": "Hard", "terre battue": "Clay",
             "terre battue intérieure": "Clay", "gazon": "Grass", "moquette": "Hard"}


def _key(value):
    key = name_key(value)
    return name_key(PLAYER_ALIASES.get(key, value))


def parse(raw: bytes, tour: str, year: int, *, now=None) -> pd.DataFrame:
    rows = pd.read_csv(
        io.BytesIO(raw), sep=";", dtype={"joueur1_id": str, "joueur2_id": str, "vainqueur_id": str, "match_id": str}
    )
    required = {
        "match_id",
        "date",
        "categorie",
        "genre",
        "surface",
        "tour",
        "joueur1",
        "joueur2",
        "joueur1_id",
        "joueur2_id",
        "vainqueur_id",
        "score",
        "cote1_cloture",
        "cote2_cloture",
    }
    if not required <= set(rows):
        raise ValueError("Valuebetennis schema missing required columns")
    dates = pd.to_datetime(rows["date"], utc=True, errors="coerce")
    clock = pd.Timestamp(now or datetime.now(UTC))
    if clock.tzinfo is None:
        clock = clock.tz_localize("UTC")
    if dates.isna().any() or (dates.dt.year != year).any() or (dates > clock).any():
        raise ValueError("Valuebetennis invalid season or future result date")
    # Conflicting duplicate IDs cannot be resolved by input order.
    rows = rows.drop_duplicates().copy()
    rows = rows[~rows.match_id.duplicated(keep=False)].copy()
    rows = rows[
        (rows.genre == tour) & rows.categorie.isin(_CATEGORIES) & pd.to_numeric(rows["tour"], errors="coerce").ge(4)
    ].copy()
    a = pd.to_numeric(rows.cote1_cloture, errors="coerce")
    b = pd.to_numeric(rows.cote2_cloture, errors="coerce")
    winner_a = rows.vainqueur_id == rows.joueur1_id
    valid = (
        a.gt(1)
        & a.lt(float("inf"))
        & b.gt(1)
        & b.lt(float("inf"))
        & rows.vainqueur_id.notna()
        & rows.joueur1_id.ne(rows.joueur2_id)
        & (winner_a | rows.vainqueur_id.eq(rows.joueur2_id))
        & rows.surface.isin(_SURFACES)
        & ~rows.score.fillna("").str.contains(r"w/o|walkover|ret|abandon", case=False, regex=True)
        & rows.score.fillna("").str.contains(r"\d[-–]\d", regex=True)
    )
    out = pd.DataFrame(
        {
            "date": pd.to_datetime(rows.date, utc=True).dt.tz_localize(None).dt.normalize(),
            "winner_key": rows.joueur1.where(winner_a, rows.joueur2).map(_key),
            "loser_key": rows.joueur2.where(winner_a, rows.joueur1).map(_key),
            "surface": rows.surface.map(_SURFACES),
            "odds_w": a.where(winner_a, b),
            "odds_l": b.where(winner_a, a),
            "provider_match_id": rows.match_id,
        }
    )
    out = out[valid & out.winner_key.ne("") & out.loser_key.ne("") & out.winner_key.ne(out.loser_key)].copy()
    return out.drop_duplicates(["date", "winner_key", "loser_key"], keep=False)


def download(year: int) -> None:
    url = DATA_URL.format(year=year)
    req = urllib.request.Request(url, headers={"User-Agent": "DEUCE odds benchmark"})
    with urllib.request.urlopen(req, timeout=60) as response:
        raw = response.read()
    # Validate both tours before replacing a last-good season.
    counts = {tour: len(parse(raw, tour, year)) for tour in ("atp", "wta")}
    if not all(counts.values()):
        raise ValueError("Valuebetennis lacks usable main-event odds for both tours")
    directory = ODDS_DIR / "valuebetennis" / "objects"
    directory.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=directory)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
        digest = hashlib.sha256(raw).hexdigest()
        os.replace(temporary, directory / f"{digest}.csv")
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    receipt = {
        "source": SOURCE_URL,
        "url": url,
        "license": "CC BY 4.0",
        "attribution": ATTRIBUTION,
        "observedAt": datetime.now(UTC).isoformat(),
        "sha256": digest,
        "year": year,
        "usableRows": counts,
    }
    # Commit the pointer last. Interrupted acquisition retains the prior complete generation.
    fd, temporary = tempfile.mkstemp(dir=directory.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(json.dumps(receipt, indent=2) + "\n")
        os.replace(temporary, directory.parent / f"{year}.receipt.json")
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load(tour: str, years) -> pd.DataFrame:
    frames = []
    receipts = []
    for year in years:
        path = ODDS_DIR / "valuebetennis" / f"{year}.receipt.json"
        if path.exists():
            receipt = json.loads(path.read_text())
            digest = receipt.get("sha256", "")
            if (
                not re.fullmatch(r"[0-9a-f]{64}", digest)
                or receipt.get("year") != year
                or receipt.get("url") != DATA_URL.format(year=year)
                or receipt.get("license") != "CC BY 4.0"
            ):
                raise ValueError("Valuebetennis invalid acquisition receipt")
            raw = (path.parent / "objects" / f"{digest}.csv").read_bytes()
            if hashlib.sha256(raw).hexdigest() != digest:
                raise ValueError("Valuebetennis acquisition digest mismatch")
            frames.append(parse(raw, tour, year))
            receipts.append(receipt)
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    out.attrs["receipts"] = receipts
    return out
