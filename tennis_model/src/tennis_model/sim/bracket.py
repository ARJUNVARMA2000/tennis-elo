"""Round-by-round bracket reconstruction for the web /bracket explorer.

Unlike ``sim/draws.advance_slots`` — a *frontier* fold that only tracks who is still
alive — this rebuilds the ACTUAL per-round history of an event by pairing the
authoritative ordered Wikipedia draw (``resolved_wslots``) forward and joining each
adjacent pair to the real result. ``advance_slots``'s ``_winner()`` returns the
non-eliminated side, so once a player who won round *k* later loses round *k+1* both are
in the eliminated set and the fold would advance the WRONG player through the historical
round-*k* match. A displayed bracket has to be reconstructed forward from the ordered
slots, never by folding the eliminated set.

Pricing is a separate pass (:func:`price_bracket`) so this module stays pure and easily
tested: it takes ``price_fn``/``logged_fn`` callables and never imports the predictor or
the forecast log. Callers (``sim/tournaments.build_tournaments``) wire those in.

Slot vocabulary (from ``draws_wiki`` -> ``_reconcile_wiki_names``):
  * a canonical player name (``str``)              -> a real entrant
  * ``None``                                       -> a bye (round 0) or TBD (later round)
  * ``"Qualifier N"`` / ``"Lucky Loser"`` (``str``) -> an unresolved placeholder
"""

from __future__ import annotations

from collections import defaultdict

from ..data.results import _name_key
from .draws import SIZE_NAME

_PLACEHOLDER_PREFIXES = ("qualifier", "lucky loser", "bye", "tbd", "tba")


def is_real(x: object) -> bool:
    """A slot that names an actual player (not a bye/TBD ``None`` or a placeholder string)."""
    return isinstance(x, str) and x.strip() != "" and not _is_placeholder(x)


def _is_placeholder(x: object) -> bool:
    s = str(x).strip().lower()
    return any(s.startswith(p) for p in _PLACEHOLDER_PREFIXES)


def _result_index(results) -> dict:
    """``{frozenset(nkey(winner), nkey(loser)): (winner_name, score, round)}``.

    A pair is unique within a single-elimination event, so a plain dict is safe. If a
    duplicate pair ever appears (data noise), the first row wins; a later row whose round
    matches the slot depth would be preferred by :func:`_lookup` only through re-keying,
    which we deliberately avoid — pair identity is enough.
    """
    idx: dict = {}
    for r in results:
        w, l = r.get("winner_name"), r.get("loser_name")
        if not w or not l:
            continue
        key = frozenset((_name_key(w), _name_key(l)))
        idx.setdefault(key, (w, _clean_score(r.get("score")), r.get("round")))
    return idx


def _clean_score(s: object) -> str | None:
    if s is None:
        return None
    t = str(s).strip()
    return t or None


def _resolve_placeholders(slots: list, results) -> list:
    """Adopt a real identity for a ``"Qualifier N"`` slot when its round-0 opponent has
    exactly one opponent-of-record who is not otherwise in the draw (the qualifier who came
    through). Ambiguous (zero or several) placeholders are left as-is. Display-only: it
    never changes who advanced, only the name shown in an already-decided slot."""
    real_keys = {_name_key(s) for s in slots if is_real(s)}
    opps: dict = defaultdict(list)
    for r in results:
        w, l = r.get("winner_name"), r.get("loser_name")
        if not w or not l:
            continue
        opps[_name_key(w)].append(l)
        opps[_name_key(l)].append(w)

    out = list(slots)
    for j, s in enumerate(slots):
        if not _is_placeholder(s):
            continue
        partner = slots[j - 1] if j % 2 else slots[j + 1] if j + 1 < len(slots) else None
        if not is_real(partner):
            continue
        cand = [o for o in opps.get(_name_key(partner), []) if _name_key(o) not in real_keys]
        uniq = list(dict.fromkeys(cand))          # dedupe, preserve order
        if len(uniq) == 1:
            out[j] = uniq[0]
    return out


def _seed_of(seeds: dict | None, name: object) -> int | None:
    if not seeds or not is_real(name):
        return None
    v = seeds.get(name)
    if v is None:                                 # tolerate raw-vs-canonical spelling drift
        nk = _name_key(name)
        for k, sv in seeds.items():
            if _name_key(k) == nk:
                v = sv
                break
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _side_label(x: object) -> str | None:
    """The value shipped for a slot: a real name, a placeholder string as-is, or ``None``
    (bye in round 0 / TBD later — the client distinguishes by round index)."""
    if x is None:
        return None
    return str(x)


def bracket_rounds(slots: list, results, seeds: dict | None = None) -> list[dict]:
    """Forward-fold the ordered ``slots`` into rounds, joining ``results`` per pairing.

    ``slots`` is the authoritative ordered draw (length a power of two). ``results`` is an
    iterable of dicts with ``winner_name``/``loser_name``/``score``/``round``. Returns a
    list of ``{"round": label, "matches": [...]}`` with **unpriced** matches (see
    :func:`price_bracket`); each match is
    ``{a, b, seedA, seedB, winner: "a"|"b"|None, score: str|None}``.
    """
    slots = _resolve_placeholders(list(slots), results)
    idx = _result_index(results)
    rounds: list[dict] = []
    cur = list(slots)
    depth = 0
    while len(cur) > 1:
        matches, nxt = [], []
        for j in range(0, len(cur), 2):
            a, b = cur[j], cur[j + 1]
            winner_side: str | None = None
            score: str | None = None
            adv: object = None

            if depth == 0 and is_real(a) != is_real(b) and (a is None or b is None):
                # round-0 bye: the lone real player auto-advances (no result row exists)
                adv = a if is_real(a) else b
                winner_side = "a" if adv is a else "b"
            elif is_real(a) and is_real(b):
                hit = idx.get(frozenset((_name_key(a), _name_key(b))))
                if hit is not None:
                    winner_name, score, _rnd = hit
                    winner_side = "a" if _name_key(winner_name) == _name_key(a) else "b"
                    adv = a if winner_side == "a" else b
                # else: both real but unplayed -> pending; advance None
            # any other case (placeholder / TBD / double-bye) -> undecided, advance None

            matches.append({
                "a": _side_label(a), "b": _side_label(b),
                "seedA": _seed_of(seeds, a), "seedB": _seed_of(seeds, b),
                "winner": winner_side, "score": score,
            })
            nxt.append(adv)
        rounds.append({"round": SIZE_NAME[len(cur)], "matches": matches})
        cur = nxt
        depth += 1
    return rounds


def bracket_is_meaningful(rounds: list[dict], draw_size: int) -> bool:
    """Whether a bracket is worth showing, or is mostly unresolved placeholders.

    An early wiki capture (frozen by the first-capture cache) can name only a couple of
    direct entrants with the rest still "Qualifier N"; when those unresolved slots also face
    each other there's no named anchor for :func:`_resolve_placeholders`, so the draw stays a
    wall of "Qualifier" cards. Require a real majority of the entrants to be named — an
    all-qualifier bracket is noise, not a draw. A resolved draw (Wimbledon 128/128, or a
    normal event with a handful of qualifiers) clears it comfortably.
    """
    if not rounds or not isinstance(draw_size, int) or draw_size <= 0:
        return False
    real = sum(1 for m in rounds[0]["matches"] for x in (m.get("a"), m.get("b")) if is_real(x))
    return real * 2 >= draw_size


def oriented_logged(index: dict, a: str, b: str) -> float | None:
    """Look a match up in a forecast-log ``index`` and orient its locked prob to slot ``a``.

    ``index`` maps ``frozenset(nkey(playerA), nkey(playerB)) -> (playerA_name, p)`` where
    ``p = P(playerA)`` (as the log stores it). Returns ``p`` when the log's ``playerA`` is
    slot ``a``, else ``1 - p``; ``None`` when the pair was never logged. The caller builds
    ``index`` from the event's ``type == "match"`` log lines (date-windowed) — pairs are
    unique per single-elim event, so a plain pair key is unambiguous.
    """
    rec = index.get(frozenset((_name_key(a), _name_key(b))))
    if rec is None:
        return None
    pa_name, p = rec
    p = float(p)
    return p if _name_key(pa_name) == _name_key(a) else 1.0 - p


def price_bracket(rounds: list[dict], price_fn, logged_fn) -> list[dict]:
    """Fill ``p``/``probSource``/``upset`` on every match, in place.

    ``price_fn(a, b) -> float | None`` recomputes P(a beats b) with the current model
    (``None`` when a player is unrated). ``logged_fn(a, b) -> float | None`` returns the
    pre-match forecast locked in the forecast log, oriented to ``a`` (``None`` when the
    match was never logged). Completed matches prefer the logged value (honest pre-match,
    leakage-free — a recompute would use post-match ratings); pending matches use the
    current model so the board and the bracket agree. ``upset`` is winner-oriented ``p < 0.5``.
    """
    for rnd in rounds:
        for m in rnd["matches"]:
            a, b = m["a"], m["b"]
            p: float | None = None
            src: str | None = None
            if is_real(a) and is_real(b):
                if m["winner"] is not None:                       # completed
                    lp = logged_fn(a, b)
                    if lp is not None:
                        p, src = float(lp), "logged"
                    else:
                        rp = price_fn(a, b)
                        if rp is not None:
                            p, src = float(rp), "model"
                else:                                             # pending
                    rp = price_fn(a, b)
                    if rp is not None:
                        p, src = float(rp), "model"
            m["p"] = round(p, 4) if p is not None else None
            m["probSource"] = src
            if p is not None and m["winner"] is not None:
                won_p = p if m["winner"] == "a" else 1.0 - p
                m["upset"] = bool(won_p < 0.5)
            else:
                m["upset"] = None
    return rounds
