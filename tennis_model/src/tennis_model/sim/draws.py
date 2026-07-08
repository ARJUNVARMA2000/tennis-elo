"""Tournament draw construction.

Two ways to get a 2^k bracket order (player at each slot, top-to-bottom):
  - reconstruct_draw: rebuild the *actual* bracket of a completed event from results
    (follow each match's winner back to the round they came from). Used for honest
    backtesting of the simulator against what really happened.
  - standard_seed_draw: place a rating-sorted field into standard seeded positions,
    for projecting a hypothetical or upcoming draw.
"""

from __future__ import annotations

import pandas as pd

_ROUND_SEQ = ["R128", "R64", "R32", "R16", "QF", "SF", "F"]
SIZE_NAME = {128: "R128", 64: "R64", 32: "R32", 16: "R16", 8: "QF", 4: "SF", 2: "F", 1: "Champion"}


def find_tournament(df: pd.DataFrame, name: str, year: int) -> list:
    """tourney_ids matching a name substring in a given year (most matches first)."""
    m = (df["tourney_name"].str.contains(name, case=False, na=False)) & (df["date"].dt.year == year)
    return list(df[m]["tourney_id"].value_counts().index)


def reconstruct_draw(df: pd.DataFrame, tourney_id: str) -> dict:
    """Rebuild bracket order + actual results for one completed single-elim event."""
    t = df[df["tourney_id"] == tourney_id]
    rounds = {r: list(zip(g["winner_name"], g["loser_name"]))
              for r, g in t.groupby("round") if r in _ROUND_SEQ}
    present = [r for r in _ROUND_SEQ if r in rounds]
    if not present:
        raise ValueError(f"{tourney_id}: no single-elimination rounds found")
    first_round, final_round = present[0], present[-1]
    won_match = {r: {w: (w, l) for w, l in rounds[r]} for r in present}

    def expand(r: str, a: str, b: str) -> list:
        if r == first_round:
            return [a, b]
        prev = present[present.index(r) - 1]
        out = []
        for player in (a, b):
            mp = won_match[prev].get(player)
            out += expand(prev, mp[0], mp[1]) if mp else [player]
        return out

    f_w, f_l = rounds[final_round][0]
    slots = expand(final_round, f_w, f_l)

    # actual: furthest round size reached per player
    reached = {}
    for r in present:
        size = 2 * len(rounds[r])           # players competing in round r
        for w, l in rounds[r]:
            reached[w] = max(reached.get(w, size), size)
            reached[l] = reached.get(l, size)
    reached[f_w] = 1                          # champion
    return {
        "tourney_id": tourney_id,
        "name": t["tourney_name"].iloc[0],
        "surface": t["surface_b"].iloc[0],
        "best_of": int(pd.to_numeric(t["best_of"], errors="coerce").max()),
        "slots": slots,
        "champion": f_w,
        "runner_up": f_l,
        "reached": reached,                   # player -> smallest round-size reached
    }


def _seed_positions(n: int) -> list:
    """Standard seeded bracket positions (1-based seed at each slot) for a 2^k draw."""
    seeds = [1, 2]
    while len(seeds) < n:
        m = len(seeds) * 2
        seeds = [s for pair in ((x, m + 1 - x) for x in seeds) for s in pair]
    return seeds


def standard_seed_draw(players_by_rating: list) -> list:
    """Order a rating-sorted field (best first) into standard seeded slots.

    The field is padded up to the next power of two with byes (None) so #1 meets the
    weakest, etc., and the top two seeds can only meet in the final.
    """
    n = 1 << (len(players_by_rating) - 1).bit_length()
    field = list(players_by_rating) + [None] * (n - len(players_by_rating))
    return [field[s - 1] for s in _seed_positions(n)]


def live_draw(alive: list, matchups: list, rank) -> list:
    """Seat still-alive players into a bracket using the *actual* remaining draw.

    Unlike ``standard_seed_draw`` (which invents a rating-seeded bracket), this respects
    the real matchups the live feed already knows — the fix for a live board that paired
    survivors by strength (1v4/2v3) instead of by who actually plays whom.

    ``matchups`` is an iterable of (playerA, playerB) pairs scheduled/in-progress among
    the alive field (the true current-round draw, from ``upcoming.csv``); ``rank(player)``
    orders players/units by strength to resolve the pairings the feed can't yet know
    (which side of the bracket two future winners land on).

      - each real matchup becomes an adjacent slot pair (they meet next round, as they will)
      - a player already through this round (no listed opponent) gets a bye into the next
      - the resulting "units" (one per current-round match) are spread by strength, so the
        two strongest survivors still can't meet before the final

    Falls back to ``standard_seed_draw`` when the feed gives no usable matchup, or when the
    unit count isn't a power of two (a partial/odd frontier we can't seat cleanly) — never
    worse than the old behaviour, exact whenever the round's matchups are fully posted.
    """
    alive = list(dict.fromkeys(alive))
    aset = set(alive)
    used: set = set()
    pairs = []
    for a, b in matchups:
        if a in aset and b in aset and a != b and a not in used and b not in used:
            pairs.append(tuple(sorted((a, b), key=rank, reverse=True)))    # stronger first
            used.update((a, b))
    if not pairs:                                     # no real draw info -> old behaviour
        return standard_seed_draw(sorted(alive, key=rank, reverse=True))

    singles = sorted((p for p in alive if p not in used), key=rank, reverse=True)
    units = [list(pr) for pr in pairs] + [[s] for s in singles]     # one unit per frontier match
    u = len(units)
    if u & (u - 1):                                   # not 2^k: can't seat a clean bracket
        return standard_seed_draw(sorted(alive, key=rank, reverse=True))

    units.sort(key=lambda un: rank(un[0]), reverse=True)           # strongest unit first
    order = _seed_positions(u) if u > 1 else [1]                   # spread strong units apart
    slots: list = []
    for un in (units[s - 1] for s in order):
        slots.append(un[0])
        slots.append(un[1] if len(un) > 1 else None)              # lone survivor -> bye partner
    return slots


def draw_size_rounds(n: int) -> list:
    """Round-size labels reachable from a draw of size n (entry .. champion)."""
    sizes = []
    s = n
    while s >= 1:
        sizes.append(s)
        s //= 2
    return [SIZE_NAME[s] for s in sizes]
