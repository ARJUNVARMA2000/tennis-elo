"""Round-by-round bracket reconstruction — fully synthetic (no model, no network).

Runnable directly (`python tests/test_sim_bracket.py`) or under pytest. Pins the
history-vs-frontier distinction: `sim.draws.advance_slots` folds the eliminated set and
would mis-credit a player who won an early round then lost a later one; `bracket_rounds`
joins real results forward off the ordered draw and must credit the actual winner.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tennis_model.data.results import _name_key
from tennis_model.sim.bracket import (
    bracket_is_meaningful,
    bracket_rounds,
    is_real,
    oriented_logged,
    price_bracket,
)


def _res(w, l, score="6-4 6-4", rnd=None):
    return {"winner_name": w, "loser_name": l, "score": score, "round": rnd}


# --- an 8-slot event played to completion (QF -> SF -> F) ----------------------
# slots: P1..P8 in order. P5 wins it. P1 wins QF+SF then loses the final.
_SLOTS8 = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"]
_RESULTS8 = [
    _res("P1", "P2", rnd="QF"), _res("P3", "P4", rnd="QF"),
    _res("P5", "P6", rnd="QF"), _res("P7", "P8", rnd="QF"),
    _res("P1", "P3", rnd="SF"), _res("P5", "P7", rnd="SF"),
    _res("P5", "P1", "7-6 6-4", rnd="F"),
]


def test_round_labels_and_shape():
    rounds = bracket_rounds(_SLOTS8, _RESULTS8)
    assert [r["round"] for r in rounds] == ["QF", "SF", "F"]
    assert [len(r["matches"]) for r in rounds] == [4, 2, 1]


def test_winner_trap_credits_actual_r1_winner():
    # P1 won its QF (beat P2) but is later eliminated in the final. A frontier fold keyed
    # on the eliminated set would advance P2; the real history must credit P1.
    rounds = bracket_rounds(_SLOTS8, _RESULTS8)
    qf = rounds[0]["matches"]
    m = next(x for x in qf if x["a"] == "P1")
    assert m["winner"] == "a"           # P1, even though P1 is eliminated overall
    assert m["b"] == "P2"


def test_feeder_consistency_and_champion():
    rounds = bracket_rounds(_SLOTS8, _RESULTS8)
    # every decided match's winner appears as the corresponding participant next round
    for k in range(len(rounds) - 1):
        for j, m in enumerate(rounds[k]["matches"]):
            if m["winner"] is None:
                continue
            won = m["a"] if m["winner"] == "a" else m["b"]
            nxt = rounds[k + 1]["matches"][j // 2]
            side = nxt["a"] if j % 2 == 0 else nxt["b"]
            assert side == won
    final = rounds[-1]["matches"][0]
    champ = final["a"] if final["winner"] == "a" else final["b"]
    assert champ == "P5"
    assert final["score"] == "7-6 6-4"


def test_bye_auto_advances_with_no_result_row():
    # 8-bracket, 2 byes -> drawSize 6. Byes decide with no result row, null score.
    slots = ["P1", None, "P3", "P4", None, "P6", "P7", "P8"]
    results = [_res("P3", "P4", rnd="QF"), _res("P7", "P8", rnd="QF")]
    rounds = bracket_rounds(slots, results)
    qf = rounds[0]["matches"]
    bye1 = qf[0]
    assert bye1["a"] == "P1" and bye1["b"] is None
    assert bye1["winner"] == "a" and bye1["score"] is None
    bye2 = qf[2]
    assert bye2["a"] is None and bye2["b"] == "P6"
    assert bye2["winner"] == "b"
    # SF is unplayed -> pending, participants seated where decided, None where not
    sf = rounds[1]["matches"]
    assert sf[0]["a"] == "P1" and sf[0]["b"] == "P3"      # both fed from decided QFs
    assert sf[0]["winner"] is None                        # not played yet


def test_tbd_propagates_when_feeder_pending():
    # top half plays, bottom half hasn't -> bottom SF slot is TBD (None), final all TBD
    slots = _SLOTS8
    results = [_res("P1", "P2", rnd="QF"), _res("P3", "P4", rnd="QF")]  # only top half
    rounds = bracket_rounds(slots, results)
    sf = rounds[1]["matches"]
    assert sf[0]["a"] == "P1" and sf[0]["b"] == "P3"      # decided feeders
    assert sf[1]["a"] is None and sf[1]["b"] is None      # bottom half undecided -> TBD
    assert rounds[2]["matches"][0]["a"] is None           # final TBD


def test_qualifier_resolves_from_unique_opponent():
    # slot 1 is a placeholder; its partner P1 has exactly one opponent-of-record ("Quinn")
    # who is not otherwise in the draw -> adopt Quinn as the qualifier's identity.
    slots = ["P1", "Qualifier 1", "P3", "P4"]
    results = [_res("Quinn", "P1", rnd="SF"), _res("P3", "P4", rnd="SF")]
    rounds = bracket_rounds(slots, results)
    m = rounds[0]["matches"][0]
    assert m["b"] == "Quinn"
    assert m["winner"] == "b"            # Quinn beat P1


def test_qualifier_stays_placeholder_when_ambiguous():
    slots = ["P1", "Qualifier 1", "P3", "P4"]
    # P1 has TWO opponents not in the draw -> cannot disambiguate -> leave placeholder
    results = [_res("Quinn", "P1", rnd="SF"), _res("P1", "Rowe", rnd="SF")]
    rounds = bracket_rounds(slots, results)
    m = rounds[0]["matches"][0]
    assert m["b"] == "Qualifier 1"
    assert m["winner"] is None          # placeholder never resolves -> undecided


def test_seeds_attached_when_present():
    rounds = bracket_rounds(_SLOTS8, _RESULTS8, seeds={"P1": 1, "P5": 3})
    m = next(x for x in rounds[0]["matches"] if x["a"] == "P1")
    assert m["seedA"] == 1 and m["seedB"] is None


# --- pricing -------------------------------------------------------------------
def test_oriented_logged_flips_for_slot_b():
    # log stored p = P(playerA); index key is the unordered pair
    index = {frozenset((_name_key("P1"), _name_key("P2"))): ("P1", 0.7)}
    assert oriented_logged(index, "P1", "P2") == 0.7          # a == log playerA
    assert abs(oriented_logged(index, "P2", "P1") - 0.3) < 1e-9  # a == log playerB -> 1-p
    assert oriented_logged(index, "P3", "P4") is None         # never logged


def test_price_completed_prefers_logged_pending_uses_model():
    rounds = bracket_rounds(_SLOTS8, _RESULTS8)
    logged = {frozenset((_name_key("P1"), _name_key("P2"))): ("P1", 0.9)}
    price_bracket(
        rounds,
        price_fn=lambda a, b: 0.5,                           # model recompute stub
        logged_fn=lambda a, b: oriented_logged(logged, a, b),
    )
    qf = rounds[0]["matches"]
    m12 = next(x for x in qf if x["a"] == "P1")
    assert m12["p"] == 0.9 and m12["probSource"] == "logged"  # completed -> logged wins
    m34 = next(x for x in qf if x["a"] == "P3")
    assert m34["p"] == 0.5 and m34["probSource"] == "model"   # completed, no log -> model


def test_price_unrated_player_is_null():
    slots = ["P1", "P2"]
    rounds = bracket_rounds(slots, [_res("P1", "P2", rnd="F")])
    price_bracket(rounds, price_fn=lambda a, b: None, logged_fn=lambda a, b: None)
    m = rounds[0]["matches"][0]
    assert m["p"] is None and m["probSource"] is None and m["upset"] is None


def test_upset_is_winner_oriented():
    # b won but the model favored a (p = P(a) = 0.7) -> upset
    rounds = bracket_rounds(["A", "B"], [_res("B", "A", rnd="F")])
    price_bracket(rounds, price_fn=lambda a, b: 0.7, logged_fn=lambda a, b: None)
    m = rounds[0]["matches"][0]
    assert m["winner"] == "b" and m["p"] == 0.7 and m["upset"] is True
    # favorite holds serve: a wins with p = 0.7 -> not an upset
    rounds2 = bracket_rounds(["A", "B"], [_res("A", "B", rnd="F")])
    price_bracket(rounds2, price_fn=lambda a, b: 0.7, logged_fn=lambda a, b: None)
    assert rounds2[0]["matches"][0]["upset"] is False


def test_bracket_meaningful_rejects_mostly_placeholder_draw():
    # Gstaad's frozen early capture: 2 named + 26 "Qualifier N" in a 32-slot draw -> noise
    slots = ["Named One", "Named Two"] + [f"Qualifier {i}" for i in range(1, 27)] + [None] * 4
    rounds = bracket_rounds(slots, [], {})
    assert not bracket_is_meaningful(rounds, 28)          # only 2 of 28 are real
    # a fully-resolved bye-draw (28 named + 4 byes) is worth showing
    resolved = [f"Player {i}" for i in range(28)] + [None] * 4
    assert bracket_is_meaningful(bracket_rounds(resolved, [], {}), 28)
    # empty / degenerate inputs are not meaningful
    assert not bracket_is_meaningful([], 28)
    assert not bracket_is_meaningful(rounds, 0)
    print("ok test_bracket_meaningful_rejects_mostly_placeholder_draw")


def test_is_real_classifies_slots():
    assert is_real("Jannik Sinner")
    assert not is_real(None)
    assert not is_real("Qualifier 3")
    assert not is_real("Lucky Loser")
    assert not is_real("")


if __name__ == "__main__":                                   # pragma: no cover
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")
