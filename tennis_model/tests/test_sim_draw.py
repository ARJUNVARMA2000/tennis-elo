"""Live-draw bracket construction — fully synthetic (no model, no network).

Runnable directly (`python tests/test_sim_draw.py`) or under pytest. Pins the fix for a
live board that paired survivors by rating (1v4/2v3) instead of by the actual draw:
`live_draw` must seat still-alive players by their real current-round matchups, and the
reach-a-round odds that fall out must be internally consistent (two players who meet in
the semis can't both be >50% to reach the final — their reach-F odds sum to exactly 1).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tennis_model.sim.draws import advance_slots, draw_status, live_draw, standard_seed_draw
from tennis_model.sim.simulate import simulate_tournament

# A rating-sorted field: Sinner strongest, Fery clearly weakest. `.get` doubles as rank().
R = {"Sinner": 2100.0, "Djokovic": 1950.0, "Zverev": 1900.0, "Fery": 1400.0}


class _Pred:
    """Logistic-Elo stand-in: P(i beats j) from the rating gap, no trained model needed."""
    class _Elo:
        def __init__(self, r):
            self.r = r

        def blended(self, name, surf):
            return self.r[name]

    def __init__(self, r):
        self.elo = self._Elo(r)

    def win_prob_matrix(self, players, surface="Hard", best_of=3,
                        indoor=False, tier_k=1.0, event=None):
        n = len(players)
        P = np.full((n, n), 0.5)
        for i in range(n):
            for j in range(n):
                if i != j:
                    d = self.elo.r[players[i]] - self.elo.r[players[j]]
                    P[i, j] = 1.0 / (1.0 + 10.0 ** (-d / 400.0))
        return P


def _round1(slots: list) -> set:
    """The opponents that meet in the first simulated round (adjacent slot pairs)."""
    return {frozenset((slots[i], slots[i + 1])) for i in range(0, len(slots), 2)}


# ---------------------------------------------------------------------------
# live_draw: bracket construction
# ---------------------------------------------------------------------------
def test_live_draw_respects_actual_matchups():
    """The real SF pairings must become first-round opponents — not a rating re-seed."""
    slots = live_draw(list(R), [("Sinner", "Djokovic"), ("Zverev", "Fery")], R.get)
    assert None not in slots and len(slots) == 4
    assert _round1(slots) == {frozenset(("Sinner", "Djokovic")),
                              frozenset(("Zverev", "Fery"))}
    # the buggy behaviour (strength seeding) would instead pair Sinner-Fery / Djokovic-Zverev
    assert frozenset(("Sinner", "Fery")) not in _round1(slots)
    print("ok test_live_draw_respects_actual_matchups")


def test_live_draw_falls_back_without_matchups():
    """No feed matchups -> old rating-seeded bracket (never worse than before)."""
    assert live_draw(list(R), [], R.get) == standard_seed_draw(
        sorted(R, key=R.get, reverse=True))
    print("ok test_live_draw_falls_back_without_matchups")


def test_live_draw_falls_back_on_partial_frontier():
    """One posted match + two loose survivors = 3 units (not 2^k): seed rather than
    guess a malformed bracket."""
    slots = live_draw(list(R), [("Sinner", "Djokovic")], R.get)   # Zverev, Fery unpaired
    assert slots == standard_seed_draw(sorted(R, key=R.get, reverse=True))
    print("ok test_live_draw_falls_back_on_partial_frontier")


def test_live_draw_mixed_round_gives_advanced_players_a_bye():
    """Mid-round: 2 pending matches + 2 already-through players (4 units = 2^k). The
    pending matchups stay intact and each advanced player gets exactly one bye."""
    r = {"A": 2000.0, "B": 1900.0, "C": 1800.0, "D": 1700.0, "E": 1600.0, "F": 1500.0}
    slots = live_draw(list(r), [("A", "B"), ("C", "D")], r.get)   # E, F already through
    assert len(slots) == 8
    real = {fs for fs in _round1(slots) if None not in fs}
    assert real == {frozenset(("A", "B")), frozenset(("C", "D"))}
    assert slots.count(None) == 2                                 # one bye per advanced player
    for adv in ("E", "F"):
        i = slots.index(adv)
        partner = slots[i + 1] if i % 2 == 0 else slots[i - 1]
        assert partner is None, (adv, slots)
    print("ok test_live_draw_mixed_round_gives_advanced_players_a_bye")


# ---------------------------------------------------------------------------
# advance_slots: collapse a KNOWN ordered draw (Wikipedia) by results, keeping order
# ---------------------------------------------------------------------------
_BR = ["A", "B", "C", "D", "E", "F", "G", "H"]   # A-B, C-D, E-F, G-H in round 1


def test_advance_slots_prestart_is_the_full_ordered_bracket():
    """No results -> the draw is exactly as posted (real adjacency, no rating re-seed)."""
    assert advance_slots(_BR, set()) == _BR
    # a first-round bye stays seated against its None partner
    assert advance_slots(["A", None, "C", "D"], set()) == ["A", None, "C", "D"]
    print("ok test_advance_slots_prestart_is_the_full_ordered_bracket")


def test_advance_slots_folds_decided_rounds_in_place():
    """A fully-decided round collapses to its winners IN BRACKET ORDER — A still meets the
    C/D winner, never a strength re-seed."""
    assert advance_slots(_BR, {"B", "D", "F", "H"}) == ["A", "C", "E", "G"]   # R1 done -> SF
    assert advance_slots(["A", None, "C", "D"], {"D"}) == ["A", "C"]          # bye + a result -> final
    print("ok test_advance_slots_folds_decided_rounds_in_place")


def test_advance_slots_mixed_frontier_byes_the_advanced_player():
    """One R1 match settled, the rest pending: the winner rides a bye into R2, the pending
    matches stay intact and in position."""
    assert advance_slots(_BR, {"B"}) == ["A", None, "C", "D", "E", "F", "G", "H"]
    print("ok test_advance_slots_mixed_frontier_byes_the_advanced_player")


# ---------------------------------------------------------------------------
# draw_status: the honest label, from the SAME decision live_draw makes
# ---------------------------------------------------------------------------
def test_draw_status_real_partial_seeded():
    assert draw_status(list(R), [("Sinner", "Djokovic"), ("Zverev", "Fery")], R.get) == "real"
    assert draw_status(list(R), [("Sinner", "Djokovic")], R.get) == "partial"   # 3 units
    assert draw_status(list(R), [], R.get) == "seeded"
    print("ok test_draw_status_real_partial_seeded")


def test_draw_status_matches_live_draw_fallback():
    """The label is truthful: "real" iff live_draw honoured the actual matchups (differs
    from the rating seed); otherwise live_draw fell back to the seed."""
    seed = standard_seed_draw(sorted(R, key=R.get, reverse=True))
    real = [("Sinner", "Djokovic"), ("Zverev", "Fery")]
    assert draw_status(list(R), real, R.get) == "real" and live_draw(list(R), real, R.get) != seed
    for mus in ([("Sinner", "Djokovic")], []):
        assert draw_status(list(R), mus, R.get) != "real" and live_draw(list(R), mus, R.get) == seed
    print("ok test_draw_status_matches_live_draw_fallback")


# ---------------------------------------------------------------------------
# end-to-end: the reach-a-round odds the scorecard shows
# ---------------------------------------------------------------------------
def test_reach_final_odds_are_consistent_with_the_draw():
    """The bug, reproduced and fixed: with the ACTUAL draw, two players who meet in the
    SF have reach-final odds summing to exactly 1 (one of them must reach it). The old
    board showed Sinner 97% + Djokovic 55% = 152% because it seeded them into opposite
    halves."""
    pred = _Pred(R)
    slots = live_draw(list(R), [("Sinner", "Djokovic"), ("Zverev", "Fery")], R.get)
    sim = simulate_tournament(pred, slots, surface="Grass", best_of=5,
                              n_sims=40000, seed=1)
    row = {t.player: t for t in sim.itertuples(index=False)}

    # exact identity: exactly one of each SF pair reaches the final
    assert abs(row["Sinner"].F + row["Djokovic"].F - 1.0) < 1e-9
    assert abs(row["Zverev"].F + row["Fery"].F - 1.0) < 1e-9
    # the false pairing the old board implied does NOT hold
    assert abs(row["Sinner"].F + row["Fery"].F - 1.0) > 0.1
    # favourite ordering is sane
    assert row["Sinner"].F > row["Djokovic"].F > 0.0
    assert row["Sinner"].Champion == max(t.Champion for t in sim.itertuples(index=False))
    print("ok test_reach_final_odds_are_consistent_with_the_draw")


if __name__ == "__main__":
    test_live_draw_respects_actual_matchups()
    test_live_draw_falls_back_without_matchups()
    test_live_draw_falls_back_on_partial_frontier()
    test_live_draw_mixed_round_gives_advanced_players_a_bye()
    test_advance_slots_prestart_is_the_full_ordered_bracket()
    test_advance_slots_folds_decided_rounds_in_place()
    test_advance_slots_mixed_frontier_byes_the_advanced_player()
    test_draw_status_real_partial_seeded()
    test_draw_status_matches_live_draw_fallback()
    test_reach_final_odds_are_consistent_with_the_draw()
    print("\nALL PASSED")
