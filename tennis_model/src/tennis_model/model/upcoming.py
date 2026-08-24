"""Scheduled matchup -> current model prediction: the shared forecasting primitive.

The live feed captures every upcoming / in-progress matchup (``data.live.parse_upcoming``
-> ``upcoming.csv``). Turning one of those rows into a probability takes three steps that
used to live only inside ``eval.track``: resolve the ESPN display names to the model's
canonical spellings, infer the event's surface / best-of, and price it with
``predictor.win_prob``.

Both consumers need exactly that, so it lives here once:
  - the forecast log (``eval.track``) — locked at first sighting, for grading;
  - the web schedule board (``model.export`` -> ``upcoming-index`` + lazy shards).

``enrich_upcoming`` returns neutral rows; each caller decorates them with its own fields.
"""

from __future__ import annotations

import pandas as pd

from ..config import ROUND_ORDER, live_dir
from ..data.bracket_rounds import (
    BracketRoundIndex,
    load_bracket_round_index,
    unique_bracket_round,
)
from ..data.results import _name_key as nkey
from ..data.results import tier_mults
from ..data.surface import resolve_level, resolve_surface
from ..timing import timed

UPCOMING_COLS = ["tourney_name", "espn_id", "tourney_date", "round", "playerA", "playerB"]


def _tier_context(level: str | None, tour: str) -> float:
    """Map the public tier vocabulary back to the combiner's trained tier multiplier."""
    text = str(level or "").lower()
    key = (
        "grand_slam" if "grand slam" in text
        else "tour_finals" if "finals" in text
        else "masters" if "1000" in text or "masters" in text
        else "olympics" if "olympic" in text
        else "davis_cup" if "davis" in text or "bjk" in text
        else "atp500" if "500" in text
        else "challenger" if "125" in text or "challenger" in text
        else "atp250" if "250" in text or "united cup" in text
        else None
    )
    mults, default = tier_mults(tour)
    return float(mults.get(key, default)) if key else float(default)


def load_upcoming(tour: str) -> pd.DataFrame:
    """The tour's scheduled / in-progress matchups: ESPN's day-by-day feed unioned with the
    full first round from any released complete draw (so the board shows every opening-round
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
        from ..data.draws import tournament_draw_upcoming_rows
        rows = tournament_draw_upcoming_rows(tour)
        if rows:
            frames.append(pd.DataFrame(rows))
    except Exception:  # noqa: BLE001 — the complete-draw overlay is a bonus, never fatal
        pass
    if not frames:
        return pd.DataFrame(columns=UPCOMING_COLS)
    df = pd.concat(frames, ignore_index=True).reindex(columns=UPCOMING_COLS)
    pair = [frozenset((str(a), str(b))) for a, b in zip(df["playerA"], df["playerB"])]
    # Dedup on the event ID where both rows carry one, else the name. The ESPN feed and the
    # complete-draw overlay can name the same event differently, so a first-round matchup was
    # only ever collapsed when the two happened to agree on the title.
    ev_key = df["espn_id"].astype("object").where(df["espn_id"].notna(),
                                                  df["tourney_name"].astype(str))
    df = df.assign(_ev=ev_key.astype(str), _pair=pair)
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
    # Month-guessed rows are excluded: handing one back as `archive_surface` would
    # short-circuit the Wikipedia tier with a season guess (see sim.tournaments._known_surface).
    known = sub[sub["surface_src"] != "month"] if "surface_src" in sub.columns else sub
    surf = known["surface_b"].mode()
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


def enrich_upcoming(predictor, df: pd.DataFrame, up_df: pd.DataFrame | None, tour: str, *,
                    bracket_index: BracketRoundIndex | None = None) -> list:
    """Resolve, attribute, and price each scheduled matchup.

    Returns one dict per predictable matchup::

        {event, date, round, surface, best_of, playerA, playerB, pA, level}

    where ``pA`` = P(playerA beats playerB) under the *current* model. Rows with an unknown
    player (not in the rating pool -> ``win_prob`` would be a meaningless ~0.5) or a
    self-pair are dropped. Orientation (A/B) is whatever the feed gave — the match has no
    result yet.
    """
    with timed(tour, "upcoming_enrichment"):
        if up_df is None or up_df.empty:
            return []
        if bracket_index is None:
            # ``export_all`` has just generated this artifact before the shared enrichment
            # seam runs. Loading it here also gives forecast tracking and the schedule board
            # exactly the same round evidence without threading a second tournament graph.
            bracket_index = load_bracket_round_index(tour)
        key2name = {nkey(n): n for n in predictor.elo.overall}       # ESPN spelling -> canonical
        out = []
        for r in up_df.itertuples(index=False):
            a, b = key2name.get(nkey(r.playerA)), key2name.get(nkey(r.playerB))
            if not a or not b or nkey(a) == nkey(b):
                continue
            event_id = getattr(r, "espn_id", None)
            surface, bo = _surface_best_of(df, r.tourney_name, r.tourney_date, tour)
            level = resolve_level(tour, str(r.tourney_name), event_id=event_id)
            tier_k = _tier_context(level, tour)
            bracket_round = unique_bracket_round(bracket_index, event_id, a, b)
            round_name = bracket_round if bracket_round is not None else r.round
            if bracket_round is not None and str(r.round) != bracket_round:
                print(f"  round-reconcile/{tour}: upcoming {event_id} {a!r} vs {b!r} "
                      f"{r.round}->{bracket_round}")
            round_order = int(ROUND_ORDER.get(str(round_name), 3))
            if hasattr(predictor, "prediction_components"):
                components = predictor.prediction_components(
                    a, b, surface=surface, best_of=bo, event=str(r.tourney_name),
                    as_of=r.tourney_date, tier_k=tier_k, round_order=round_order)
                p = float(components["combiner"])
                component_payload = {k: round(float(v), 4) for k, v in components.items()}
            else:  # lightweight test doubles and legacy foreign predictors
                p = float(predictor.win_prob(
                    a, b, surface=surface, best_of=bo, event=str(r.tourney_name)))
                component_payload = None
            evidence_payload = None
            if hasattr(predictor, "prediction_evidence"):
                evidence_payload = predictor.prediction_evidence(
                    a, b, surface=surface, best_of=bo, event=str(r.tourney_name),
                    as_of=r.tourney_date, tier_k=tier_k, round_order=round_order)
            out.append({
                "event": str(r.tourney_name), "date": str(r.tourney_date), "round": round_name,
                "surface": surface, "best_of": bo, "playerA": a, "playerB": b, "pA": p,
                "level": level,
                "espnId": event_id,
                "components": component_payload,
                "evidence": evidence_payload,
            })
        return out
