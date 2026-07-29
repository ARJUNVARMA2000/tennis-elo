"""The proposer's guarantee is not that the model is right — it is that a wrong model
answer cannot reach config.py. These tests are almost entirely about the falsifier: every
case below is a plausible-sounding proposal the data refutes."""

from __future__ import annotations

import json

import pandas as pd
import pytest
from tennis_model.data.alias_proposer import Question

from tennis_model.data import alias_proposer as ap


def _frame(rows):
    return pd.DataFrame(rows, columns=["winner_name", "loser_name", "date"])


# Three shapes a surname heuristic cannot tell apart:
#   Merida  — one player, two spellings, never meets himself      -> the alias we want
#   Zverev  — brothers; not a token-subset pair, so never a candidate at all
#   Gomez   — a token-SUBSET pair who have played each other      -> two people, and the
#             only shape the subset rule alone would get wrong
FRAME = _frame([
    ("Daniel Merida", "Otto Virtanen", pd.Timestamp("2026-06-01")),
    ("Daniel Merida", "Marco Trungelliti", pd.Timestamp("2026-06-08")),
    ("Daniel Merida Aguilar", "Pol Martin Tiffon", pd.Timestamp("2026-06-15")),
    ("Alexander Zverev", "Mischa Zverev", pd.Timestamp("2026-06-20")),
    ("Alexander Zverev", "Otto Virtanen", pd.Timestamp("2026-06-22")),
    ("Carlos Gomez Herrera", "Carlos Gomez", pd.Timestamp("2026-06-25")),
    ("Carlos Gomez", "Otto Virtanen", pd.Timestamp("2026-06-27")),
])


@pytest.fixture
def evidence():
    return ap.build_evidence(FRAME)


@pytest.fixture
def unpatched_config(monkeypatch):
    """Merida is in the real PLAYER_ALIASES and Mifel in the real WIKI_TITLE_OVERRIDES —
    both were added by hand for exactly these incidents. Empty the tables so the fixtures
    exercise the scan/falsifier rather than the already-shipped fix."""
    monkeypatch.setattr(ap, "PLAYER_ALIASES", {})
    monkeypatch.setattr(ap, "WIKI_TITLE_OVERRIDES", {})


def _asked(*questions):
    return {q.key: q for q in questions}


def _pair(a, b, tour="atp"):
    return Question(kind="player_alias", tour=tour, subject=tuple(sorted((a, b))), context="")


# --------------------------------------------------------------------------- questions
def test_health_report_yields_one_question_per_unresolved_event():
    report = {"tours": {"atp": {
        "problems": [],
        "output": {"problems": [
            "atp: upcoming tournament 'Mifel Tennis Open by Telcel Oppo' tier did not "
            "resolve (shows the generic 'ATP Tour')",
            "atp: tournament 'Generali Open' level 'WTA 125' is not in the ATP level vocabulary",
            "atp: tournaments.json is empty",
        ]}}}}
    qs = ap.questions_from_health(report)
    assert [q.subject[0] for q in qs] == ["Mifel Tennis Open by Telcel Oppo", "Generali Open"]
    assert {q.kind for q in qs} == {"wiki_title"}


def test_cross_tour_problem_keeps_its_own_tour_not_the_block_it_is_filed_under():
    """check_all files cross-tour problems under the FIRST tour's block, so reading the tour
    from the dict key would ask Wikipedia for a WTA event on the ATP tour."""
    report = {"tours": {"atp": {"output": {"problems": [
        "wta: upcoming tournament 'Some WTA Event' tier did not resolve (shows 'WTA Tour')",
    ]}}}}
    assert ap.questions_from_health(report)[0].tour == "wta"


def test_coverage_failures_become_contained_event_search_questions():
    report = {"tours": {"atp": {"output": {"problems": [
        "atp: begun tournament 'Odlum Brown VanOpen' (coverage key espn:875-2026) "
        "is missing from tournaments.json",
        "atp: begun tournament 'Mystery Open' (coverage key evidence:abc123) "
        "is missing from tournaments.json",
    ]}}}}
    qs = ap.questions_from_health(report)
    assert [(q.kind, q.subject) for q in qs] == [
        ("missing_event", ("Odlum Brown VanOpen", "espn:875-2026")),
        ("event_identity", ("Mystery Open", "evidence:abc123")),
    ]


def test_event_search_answer_cannot_change_the_asked_coverage_identity():
    q = Question(kind="missing_event", tour="wta",
                 subject=("Odlum Brown VanOpen", "espn:875-2026"), context="missing")
    good = {"kind": "missing_event", "tour": "wta", "event_name": "Odlum Brown VanOpen",
            "coverage_key": "espn:875-2026", "espn_id": "875-2026",
            "article": "2026 Odlum Brown VanOpen", "tier": "WTA 125",
            "sources": ["https://www.wtatennis.com/tournament/2098/vancouver-125/2026/overview"]}
    assert ap.falsify(good, _asked(q)) is None
    changed = {**good, "coverage_key": "espn:999-2026", "espn_id": "999-2026"}
    assert "not one of the questions asked" in ap.falsify(changed, _asked(q))


def test_player_scan_asks_about_the_dropped_surname(evidence, unpatched_config):
    subjects = [q.subject for q in ap.player_questions(evidence, "atp")]
    assert ("Daniel Merida", "Daniel Merida Aguilar") in subjects


def test_scan_never_asks_about_a_shared_surname_alone(evidence, unpatched_config):
    """The rule is token-SUBSET, not shared surname — "shorter name is a prefix of the
    longer" would put every pair of tennis brothers on the list."""
    subjects = [q.subject for q in ap.player_questions(evidence, "atp")]
    assert not any("Mischa Zverev" in s for s in subjects)


def test_scan_drops_a_subset_pair_that_has_played_each_other(evidence, unpatched_config):
    """The one shape the subset rule alone gets wrong, and the reason the scan consults the
    match record before spending a search on a pair: these two are a textbook
    dropped-surname candidate who happen to be two different people."""
    subjects = [q.subject for q in ap.player_questions(evidence, "atp")]
    assert ("Carlos Gomez", "Carlos Gomez Herrera") not in subjects


def test_player_scan_skips_pairs_config_already_covers(evidence, monkeypatch):
    monkeypatch.setattr(ap, "PLAYER_ALIASES", {"daniel merida aguilar": "Daniel Merida"})
    assert ap.player_questions(evidence, "atp") == []


def test_stable_player_ids_refute_a_subset_pair_before_search(unpatched_config):
    """Two ATP names can have the exact dropped-surname shape and still be two people.

    The tour's alphanumeric player id is stronger evidence than the name heuristic, while
    two spellings carrying the same id remain a legitimate question.
    """
    frame = pd.DataFrame([
        ("Joao Lucas Reis Da Silva", "Opponent One", "R0A7", "O001", pd.Timestamp("2026-07-01")),
        ("Joao Silva", "Opponent Two", "S0Y4", "O002", pd.Timestamp("2026-07-02")),
        ("Guto Miguel", "Opponent Three", "M0WY", "O003", pd.Timestamp("2026-07-03")),
        ("Guto Miguel", "Opponent Six", "M0WY", "O006", pd.Timestamp("2026-07-03")),
        ("Luis Guto Miguel", "Opponent Four", "M0WY", "O004", pd.Timestamp("2026-07-04")),
        ("Luis Miguel", "Opponent Five", "M0WY", "O005", pd.Timestamp("2026-07-05")),
    ], columns=["winner_name", "loser_name", "winner_id", "loser_id", "date"])
    subjects = [q.subject for q in ap.player_questions(ap.build_evidence(frame), "atp")]
    assert ("Joao Lucas Reis Da Silva", "Joao Silva") not in subjects
    assert ("Guto Miguel", "Luis Guto Miguel") in subjects
    assert ("Guto Miguel", "Luis Miguel") in subjects
    assert ("Luis Guto Miguel", "Luis Miguel") not in subjects


def test_numeric_source_local_ids_do_not_refute_a_wta_name_pair(unpatched_config):
    """Historical and current WTA feeds use different numeric id namespaces."""
    frame = pd.DataFrame([
        ("Caijsa Hennemann", "Opponent One", 326044.0, 1.0, pd.Timestamp("2026-07-01")),
        ("Caijsa Wilda Hennemann", "Opponent Two", 216385.0, 2.0, pd.Timestamp("2026-07-02")),
    ], columns=["winner_name", "loser_name", "winner_id", "loser_id", "date"])
    subjects = [q.subject for q in ap.player_questions(ap.build_evidence(frame), "wta")]
    assert ("Caijsa Hennemann", "Caijsa Wilda Hennemann") in subjects


# --------------------------------------------------------------------------- falsifier
def test_match_record_outranks_the_model(evidence):
    """The core rule. Even asked about, even asserted, two names that met across a net are
    two people — this is what stops a confident search result fusing two rating histories."""
    q = _pair("Alexander Zverev", "Mischa Zverev")
    proposal = {"kind": "player_alias", "tour": "atp", "variant": "Mischa Zverev",
                "canonical": "Alexander Zverev", "same_person": True,
                "reason": "same family, appears to be the same player"}
    reason = ap.falsify(proposal, _asked(q), evidence)
    assert reason and "played each other" in reason


def test_stable_player_id_outranks_the_model(unpatched_config):
    frame = pd.DataFrame([
        ("Joao Lucas Reis Da Silva", "Opponent One", "R0A7", "O001", pd.Timestamp("2026-07-01")),
        ("Joao Silva", "Opponent Two", "S0Y4", "O002", pd.Timestamp("2026-07-02")),
    ], columns=["winner_name", "loser_name", "winner_id", "loser_id", "date"])
    q = _pair("Joao Lucas Reis Da Silva", "Joao Silva")
    proposal = {"kind": "player_alias", "tour": "atp", "variant": "Joao Silva",
                "canonical": "Joao Lucas Reis Da Silva", "same_person": True}
    reason = ap.falsify(proposal, _asked(q), ap.build_evidence(frame))
    assert reason and "different stable player ids" in reason


def test_model_cannot_widen_the_candidate_set(evidence):
    """A proposal about a pair nobody asked about is dead before its content is read."""
    q = _pair("Daniel Merida", "Daniel Merida Aguilar")
    proposal = {"kind": "player_alias", "tour": "atp", "variant": "Rafael Nadal Parera",
                "canonical": "Rafael Nadal", "same_person": True}
    reason = ap.falsify(proposal, _asked(q), evidence)
    assert reason and "not one of the questions asked" in reason


def test_the_real_split_identity_survives_every_check(evidence):
    q = _pair("Daniel Merida", "Daniel Merida Aguilar")
    proposal = {"kind": "player_alias", "tour": "atp", "variant": "Daniel Merida Aguilar",
                "canonical": "Daniel Merida", "same_person": True}
    assert ap.falsify(proposal, _asked(q), evidence) is None


def test_canonical_spelling_nobody_plays_under_is_rejected(evidence):
    """Backstop behind containment, for when questions outlive the frame that generated
    them: the questions file is written in one run and adjudicated after a refresh, so a
    name can vanish between the two. Retiring a real spelling in favour of one that is in
    no match would erase the player from the board entirely."""
    q = _pair("Daniel Merida", "Dani Merida")
    proposal = {"kind": "player_alias", "tour": "atp", "variant": "Daniel Merida",
                "canonical": "Dani Merida", "same_person": True}
    assert "does not appear in the match record" in ap.falsify(proposal, _asked(q), evidence)


def test_uncertain_answer_is_not_a_proposal(evidence):
    q = _pair("Daniel Merida", "Daniel Merida Aguilar")
    proposal = {"kind": "player_alias", "tour": "atp", "variant": "Daniel Merida Aguilar",
                "canonical": "Daniel Merida", "same_person": False}
    assert "did not assert" in ap.falsify(proposal, _asked(q), evidence)


def test_redundant_alias_is_rejected(evidence):
    """Spellings that share a name key are already merged by _canonicalize_names; adding an
    entry for them grows a hand-kept table with a no-op."""
    q = _pair("Daniel Merida", "Daniel Mérida")
    proposal = {"kind": "player_alias", "tour": "atp", "variant": "Daniel Mérida",
                "canonical": "Daniel Merida", "same_person": True}
    assert "no-op" in ap.falsify(proposal, _asked(q), evidence)


def test_event_tier_must_be_in_this_tour_vocabulary():
    q = Question(kind="wiki_title", tour="atp", subject=("Acme Open pres. by Sponsor",),
                 context="")
    base = {"kind": "wiki_title", "tour": "atp",
            "espn_name": "Acme Open pres. by Sponsor", "article": "Acme Open"}
    assert ap.falsify({**base, "tier": "ATP 250"}, _asked(q)) is None
    # 125s are WTA-only; "ATP 125" is a tier that does not exist.
    assert "level vocabulary" in ap.falsify({**base, "tier": "ATP 125"}, _asked(q))
    # Wikipedia's own prose dialect is folded, not rejected.
    assert ap.falsify({**base, "tier": "ATP 250 series"}, _asked(q)) is None


def test_article_must_actually_resolve():
    """The empirical half: apply the override and run OUR parser against it. An article that
    resolves to nothing would leave the card exactly as broken as before."""
    proposal = {"kind": "wiki_title", "tour": "atp", "article": "Los Cabos Open"}
    assert "resolves to nothing" in ap.verify_article(proposal, meta_fn=lambda *a: (None, None))
    assert ap.verify_article(proposal, meta_fn=lambda *a: ("Hard", "ATP 250")) is None
    assert proposal["parsed_surface"] == "Hard"


def test_article_lookup_failure_rejects_rather_than_raises():
    def boom(*a):
        raise RuntimeError("429 Too Many Requests")
    proposal = {"kind": "wiki_title", "tour": "atp", "article": "Los Cabos Open"}
    assert "article lookup failed" in ap.verify_article(proposal, meta_fn=boom)


# --------------------------------------------------------------------------- parsing
def test_json_is_read_from_the_last_fenced_block():
    """Structured outputs are not used here (a web-search turn puts server-tool blocks ahead
    of the text), so the parser has to survive prose, and a worked example, before the answer."""
    text = ('Here is the shape I am aiming for:\n```json\n{"proposals": []}\n```\n'
            'After searching, my answer:\n```json\n{"proposals": [{"kind": "wiki_title"}]}\n```')
    assert ap.extract_json(text)["proposals"] == [{"kind": "wiki_title"}]


def test_unparseable_answer_is_zero_proposals_not_a_crash():
    assert ap.extract_json("I could not determine this.") == {}
    assert ap.extract_json("```json\n{oops\n```") == {}
    assert ap.extract_json(None) == {}


# --------------------------------------------------------------------------- patching
CONFIG_SRC = '''"""cfg"""
EVENT_TIER_FALLBACK: dict = {
    "Nordea Open": "250",
}

WIKI_TITLE_OVERRIDES: dict[str, str] = {
    "Mifel Tennis Open by Telcel Oppo": "Los Cabos Open",
}

PLAYER_ALIASES: dict[str, str] = {
    "daniel merida aguilar": "Daniel Merida",
}

BACKTEST_START_YEAR = 2010
'''


def test_accepted_entries_land_inside_their_dict_and_the_file_still_parses():
    accepted = [
        {"kind": "player_alias", "variant": "Pol Martin Tiffon", "canonical": "Pol Martin",
         "reason": "same player", "sources": ["https://example.test/p"]},
        {"kind": "wiki_title", "espn_name": "Hall of Fame Open",
         "article": "2026 Hall of Fame Open", "tier": "ATP 250",
         "parsed_category": "ATP 250", "reason": "article resolves"},
    ]
    out = ap.apply_to_config(CONFIG_SRC, accepted, today="2026-07-28")
    ns: dict = {}
    exec(compile(out, "config.py", "exec"), ns)          # the edit must leave valid Python
    assert ns["PLAYER_ALIASES"]["pol martin tiffon"] == "Pol Martin"
    assert ns["WIKI_TITLE_OVERRIDES"]["Hall of Fame Open"] == "2026 Hall of Fame Open"
    assert ns["EVENT_TIER_FALLBACK"] == {"Nordea Open": "250"}, \
        "a resolved category needs no curated tier fallback"
    assert "2026-07-28 alias-proposer" in out and "https://example.test/p" in out
    # Style parity with the hand-written entries around it. A bot line that is visually
    # obvious in the diff invites skimming; the reviewer should judge it on its evidence.
    assert '    "pol martin tiffon": "Pol Martin",' in out


def test_an_accented_name_stays_readable_in_the_diff():
    """json.dumps would \\uXXXX-escape it by default, turning a reviewable name into a code
    point the reviewer has to decode before they can judge the proposal."""
    accepted = [{"kind": "player_alias", "variant": "Daniel Mérida Aguilar",
                 "canonical": "Daniel Mérida", "reason": "r"}]
    out = ap.apply_to_config(CONFIG_SRC, accepted, today="2026-07-28")
    assert '"Daniel Mérida"' in out and "\\u00e9" not in out
    ns: dict = {}
    exec(compile(out, "config.py", "exec"), ns)
    assert ns["PLAYER_ALIASES"]["daniel merida aguilar"] == "Daniel Mérida"


def test_article_without_a_category_also_gets_a_tier_fallback():
    """The Nordea/Mifel shape: the title override alone resolves the article but leaves the
    tier generic, because the infobox carries no `category` field."""
    accepted = [{"kind": "wiki_title", "espn_name": "Some Open", "article": "Some Open",
                 "tier": "ATP 250", "parsed_category": None, "reason": "no category field"}]
    ns: dict = {}
    exec(compile(ap.apply_to_config(CONFIG_SRC, accepted), "config.py", "exec"), ns)
    assert ns["EVENT_TIER_FALLBACK"]["Some Open"] == "250"


def test_a_missing_table_is_loud():
    """A silent no-op edit would open an empty PR that reads like a clean bill of health."""
    with pytest.raises(KeyError):
        ap.apply_to_config("X = 1\n", [{"kind": "player_alias", "variant": "A B C",
                                        "canonical": "A B"}])


# --------------------------------------------------------------------------- end to end
def test_adjudicate_splits_a_mixed_answer_and_keeps_the_reasons(evidence):
    questions = [_pair("Daniel Merida", "Daniel Merida Aguilar"),
                 _pair("Alexander Zverev", "Mischa Zverev")]
    raw = [
        {"kind": "player_alias", "tour": "atp", "variant": "Daniel Merida Aguilar",
         "canonical": "Daniel Merida", "same_person": True, "reason": "same Madrid player"},
        {"kind": "player_alias", "tour": "atp", "variant": "Mischa Zverev",
         "canonical": "Alexander Zverev", "same_person": True, "reason": "same surname"},
        "not even an object",
    ]
    result = ap.adjudicate(questions, raw, evidence)
    assert [p["variant"] for p in result["accepted"]] == ["Daniel Merida Aguilar"]
    assert len(result["rejected"]) == 2
    assert all(r["reason"] for r in result["rejected"])
    body = ap.summarize(result)
    assert "Daniel Merida" in body and "Discarded by the falsifier" in body


def test_adjudicate_uses_evidence_from_each_proposals_tour():
    atp = ap.build_evidence(_frame([
        ("Daniel Merida", "ATP Opponent", pd.Timestamp("2026-06-01")),
        ("Daniel Merida Aguilar", "ATP Other", pd.Timestamp("2026-06-02")),
    ]))
    wta = ap.build_evidence(_frame([
        ("Ilinca Amariei", "WTA Opponent", pd.Timestamp("2026-06-01")),
        ("Ilinca Dalina Amariei", "WTA Other", pd.Timestamp("2026-06-02")),
    ]))
    questions = [_pair("Daniel Merida", "Daniel Merida Aguilar", "atp"),
                 _pair("Ilinca Amariei", "Ilinca Dalina Amariei", "wta")]
    raw = [
        {"kind": "player_alias", "tour": "atp", "variant": "Daniel Merida Aguilar",
         "canonical": "Daniel Merida", "same_person": True},
        {"kind": "player_alias", "tour": "wta", "variant": "Ilinca Dalina Amariei",
         "canonical": "Ilinca Amariei", "same_person": True},
    ]
    result = ap.adjudicate(questions, raw, {"atp": atp, "wta": wta})
    assert [p["canonical"] for p in result["accepted"]] == ["Daniel Merida", "Ilinca Amariei"]


def _openrouter_response(payload):
    class _Response:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return json.dumps(payload).encode()

    return _Response()


def test_ask_openrouter_pins_auth_search_and_reasoning_contract():
    captured = {}

    def opener(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["payload"] = json.loads(request.data)
        captured["timeout"] = timeout
        return _openrouter_response({
            "choices": [{"finish_reason": "stop", "message": {"content":
                '```json\n{"proposals": [{"kind": "player_alias"}]}\n```'}}]
        })

    proposals, _ = ap.ask_openrouter(
        [_pair("A B", "A B C")], opener=opener, api_key="test-openrouter-key")

    assert proposals == [{"kind": "player_alias"}]
    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-openrouter-key"
    assert captured["headers"]["Content-type"] == "application/json"
    payload = captured["payload"]
    assert payload["model"] == "openai/gpt-5.4-mini"
    assert payload["messages"][0] == {"role": "system", "content": ap._SYSTEM}
    assert "Resolve these open identities" in payload["messages"][1]["content"]
    assert payload["reasoning"] == {"effort": "medium", "exclude": True}
    assert payload["tools"] == [{
        "type": "openrouter:web_search",
        "parameters": {"max_uses": 8, "max_total_results": 24},
    }]
    assert payload["max_tool_calls"] == 8
    assert "test-openrouter-key" not in json.dumps(payload)
    assert captured["timeout"] >= 300


def test_ask_openrouter_never_lets_a_refusal_look_like_an_empty_answer():
    def opener(*_args, **_kwargs):
        return _openrouter_response({
            "choices": [{"finish_reason": "content_filter",
                         "message": {"content": "", "refusal": "not allowed"}}]
        })

    proposals, text = ap.ask_openrouter(
        [_pair("A B", "A B C")], opener=opener, api_key="test-openrouter-key")
    assert proposals == [] and "declined" in text
