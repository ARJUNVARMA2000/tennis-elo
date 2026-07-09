"""Scheduled matchup -> current model prediction: the shared forecasting primitive.

The live feed captures every upcoming / in-progress matchup (``data.live.parse_upcoming``
-> ``upcoming.csv``). Turning one of those rows into a probability takes three steps that
used to live only inside ``eval.track``: resolve the ESPN display names to the model's
canonical spellings, infer the event's surface / best-of, and price it with
``predictor.win_prob``.

Both consumers need exactly that, so it lives here once:
  - the forecast log (``eval.track``) — locked at first sighting, for grading;
  - the web schedule board (``model.export`` -> ``upcoming.json``) — the live view.

``enrich_upcoming`` returns neutral rows; each caller decorates them with its own fields.
"""

from __future__ import annotations

import pandas as pd

from ..config import live_dir
from ..data.results import _name_key as nkey
from ..data.surface import resolve_level, resolve_surface

UPCOMING_COLS = ["tourney_name", "tourney_date", "round", "playerA", "playerB"]


def load_upcoming(tour: str) -> pd.DataFrame:
    """The tour's scheduled / in-progress matchups: ESPN's day-by-day feed unioned with the
    full first round from any released Wikipedia draw (so the board shows every opening-round
    match at release, not just the handful ESPN has named). Deduped by event + unordered
    player pair (ESPN wins ties). A missing or corrupt source is a no-op, never fatal."""
    frames = []
    path = live_dir(tour) / "upcoming.csv"
    if path.exists():
        try:
            frames.append(pd.read_csv(path, encoding="utf-8"))
        except Exception:  # noqa: BLE001 — a corrupt upcoming file must not break anything
            pass
    try:
        from ..data.draws_wiki import wiki_upcoming_rows
        rows = wiki_upcoming_rows(tour)
        if rows:
            frames.append(pd.DataFrame(rows))
    except Exception:  # noqa: BLE001 — the wiki overlay is a bonus, never a build failure
        pass
    if not frames:
        return pd.DataFrame(columns=UPCOMING_COLS)
    df = pd.concat(frames, ignore_index=True).reindex(columns=UPCOMING_COLS)
    pair = [frozenset((str(a), str(b))) for a, b in zip(df["playerA"], df["playerB"])]
    df = df.assign(_ev=df["tourney_name"].astype(str), _pair=pair)
    return (df[~df.duplicated(subset=["_ev", "_pair"])]
            .drop(columns=["_ev", "_pair"]).reset_index(drop=True))


def event_attrs(df: pd.DataFrame, event: str) -> tuple:
    """(surface, best_of) for an ESPN event name, taken from its rows in the match frame
    (matched by loose name containment). Returns (None, None) if not found."""
    if "tourney_name" not in df.columns or "surface_b" not in df.columns:
        return None, None
    ek = str(event).lower()
    names = df["tourney_name"].astype(str)
    mask = names.str.lower().apply(lambda t: bool(t) and (t in ek or ek in t))
    sub = df[mask]
    if sub.empty:
        return None, None
    surf = sub["surface_b"].mode()
    bo = pd.to_numeric(sub["best_of"], errors="coerce").max() if "best_of" in sub.columns else None
    return (surf.iloc[0] if not surf.empty else None,
            int(bo) if pd.notna(bo) else None)


def _surface_best_of(df: pd.DataFrame, event: str, date: str, tour: str) -> tuple:
    """Event surface / best-of. Surface: the archive value for a known event, else the
    Wikipedia main-article surface (data.surface), else a season-by-month fallback. Best-of
    defaults to 3 for a brand-new week's first matches not yet in the frame."""
    surface, bo = event_attrs(df, event)
    surface = resolve_surface(tour, event, date, archive_surface=surface)
    return surface, int(bo) if bo else 3


def enrich_upcoming(predictor, df: pd.DataFrame, up_df: pd.DataFrame | None, tour: str) -> list:
    """Resolve, attribute, and price each scheduled matchup.

    Returns one dict per predictable matchup::

        {event, date, round, surface, best_of, playerA, playerB, pA, level}

    where ``pA`` = P(playerA beats playerB) under the *current* model. Rows with an unknown
    player (not in the rating pool -> ``win_prob`` would be a meaningless ~0.5) or a
    self-pair are dropped. Orientation (A/B) is whatever the feed gave — the match has no
    result yet.
    """
    if up_df is None or up_df.empty:
        return []
    key2name = {nkey(n): n for n in predictor.elo.overall}       # ESPN spelling -> canonical
    out = []
    for r in up_df.itertuples(index=False):
        a, b = key2name.get(nkey(r.playerA)), key2name.get(nkey(r.playerB))
        if not a or not b or nkey(a) == nkey(b):
            continue
        surface, bo = _surface_best_of(df, r.tourney_name, r.tourney_date, tour)
        p = float(predictor.win_prob(a, b, surface=surface, best_of=bo, event=str(r.tourney_name),
                                     h2h_as_of=r.tourney_date))
        out.append({
            "event": str(r.tourney_name), "date": str(r.tourney_date), "round": r.round,
            "surface": surface, "best_of": bo, "playerA": a, "playerB": b, "pA": p,
            "level": resolve_level(tour, str(r.tourney_name)),
        })
    return out
