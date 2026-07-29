"""Propose the entries the hand-kept name tables need. Never apply them unreviewed.

Three tables in `config.py` exist for one reason: two sources spell one thing two ways.
`PLAYER_ALIASES` (one person, two spellings), `WIKI_TITLE_OVERRIDES` (ESPN's sponsor title
vs. the Wikipedia article), `EVENT_TIER_FALLBACK` (an article whose infobox omits
``category``). Every entry in all three was added by hand, hours or days AFTER the mismatch
had already shipped to the board — "Mifel Tennis Open by Telcel Oppo" sat as a generic
"ATP Tour" card until the tier-did-not-resolve advisory finally named it.

This module closes that loop without putting a model anywhere near the pipeline:

    gate problem / near-miss scan   deterministic — generates the candidate set
      -> OpenRouter + web search    adjudicates ONLY the candidates it was handed
      -> falsify()                  deterministic — discards what the data refutes
      -> a config patch on a branch  human review is the last gate

The model is sandwiched between two deterministic layers. It cannot widen the candidate
set (`falsify` rejects any pair that was not asked about), it cannot invent a spelling
nobody plays under, it cannot emit a tier outside `LEVEL_VOCAB`, and it cannot outvote the
match record: **two names that have ever met each other across a net are two people**,
whatever a search result says. What it can do is the one thing no heuristic here could —
read an entry list and tell us that "Daniel Merida Aguilar" and "Daniel Merida" are the
same player from Madrid, while the Zverevs and the Bryans are not.

Deliberately quarantined from the pipeline:
  * nothing on the hourly path imports this module;
  * the OpenRouter transport uses only the standard library, so no LLM client enters
    requirements.txt (the retrain must stay reproducible from pins taken from CI logs);
  * the CLI exits 0 on every failure mode. A proposer outage must never be able to red a
    run or block a deploy; the worst case is a week with no PR.

Run:  PYTHONPATH=src python -m tennis_model.data.alias_proposer --health <path> [--apply]
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import date

from ..config import EVENT_TIER_FALLBACK, PLAYER_ALIASES, WIKI_TITLE_OVERRIDES
from .names import name_key
from .surface import LEVEL_VOCAB, normalize_level

MODEL = "openai/gpt-5.4-mini"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# A weekly cap. The board carries a handful of open identities at a time; a scan returning
# fifty means the near-miss rule broke, and the right response is to look at it, not to
# spend an hour of search on noise.
MAX_QUESTIONS = 12
# Only names seen this recently are candidates. The archive's older spellings were settled
# long ago by `_canonicalize_names`; re-litigating them weekly buys nothing.
SCAN_WINDOW_DAYS = 180


# ---------------------------------------------------------------------------
# Questions — what we ask about, and the containment key that pins the answer
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Question:
    """One open identity. ``subject`` is the exact tuple of strings under question and is
    also the containment key: a proposal whose subject is not in the asked set is rejected,
    so the model can only ever answer what it was given."""

    kind: str                    # player_alias | wiki_title | missing_event | event_identity
    tour: str
    subject: tuple[str, ...]
    context: str                 # the gate problem / scan finding, quoted into the prompt

    @property
    def key(self) -> tuple[str, str, tuple[str, ...]]:
        return (self.kind, self.tour, self.subject)


# `{name!r}` renders with single quotes unless the name contains one, so accept both.
_QUOTED_EVENT = re.compile(r"tournament (['\"])(.+?)\1")
# The two markers that mean "we could not identify this event from its ESPN name".
_EVENT_MARKERS = ("tier did not resolve", "level vocabulary")
_TOUR_PREFIX = re.compile(r"^([a-z]+):")
_COVERAGE_EVENT = re.compile(
    r"begun tournament (['\"])(.+?)\1 \(coverage key ([^)]+)\) is missing from tournaments\.json")


def questions_from_health(report: dict) -> list[Question]:
    """Open event identities, read from a health.json report.

    The gate already names every event it could not resolve; this just turns those problem
    strings back into structured questions. Cross-tour problems are attached to the first
    tour's block (see health.check_all), so the tour is read from the problem string's own
    ``"{tour}: "`` prefix and only falls back to the block it was filed under."""
    out: list[Question] = []
    seen: set = set()
    for block_tour, block in (report.get("tours") or {}).items():
        problems = list(block.get("problems") or [])
        problems += list((block.get("output") or {}).get("problems") or [])
        for problem in problems:
            coverage = _COVERAGE_EVENT.search(problem)
            if coverage:
                name, coverage_key = coverage.group(2), coverage.group(3)
                pref = _TOUR_PREFIX.match(problem)
                tour = pref.group(1) if pref and pref.group(1) in LEVEL_VOCAB else block_tour
                kind = "missing_event" if coverage_key.startswith("espn:") else "event_identity"
                q = Question(kind=kind, tour=tour, subject=(name, coverage_key), context=problem)
                if q.key not in seen:
                    seen.add(q.key)
                    out.append(q)
                continue
            if not any(marker in problem for marker in _EVENT_MARKERS):
                continue
            m = _QUOTED_EVENT.search(problem)
            if not m:
                continue
            name = m.group(2)
            pref = _TOUR_PREFIX.match(problem)
            tour = pref.group(1) if pref and pref.group(1) in LEVEL_VOCAB else block_tour
            q = Question(kind="wiki_title", tour=tour, subject=(name,), context=problem)
            if q.key in seen:
                continue
            seen.add(q.key)
            out.append(q)
    return out


# ---------------------------------------------------------------------------
# Evidence — the match record, which outranks anything a search result says
# ---------------------------------------------------------------------------
@dataclass
class MatchEvidence:
    """The facts `falsify` rules on. Built once from a match frame, then pure.

    ``opponents`` is the load-bearing one: a frozenset of the two name keys for every match
    ever played. If a proposed pair is in it, those two names stood on opposite sides of a
    net, and no amount of biographical similarity makes them one person."""

    opponents: set = field(default_factory=set)
    spellings: dict = field(default_factory=dict)   # name_key -> {spelling: count}
    counts: dict = field(default_factory=dict)      # name_key -> matches played
    stable_ids: dict = field(default_factory=dict)  # name_key -> cross-feed player ids

    def played_each_other(self, a: str, b: str) -> bool:
        return frozenset((name_key(a), name_key(b))) in self.opponents

    def known(self, name: str) -> bool:
        return name_key(name) in self.counts

    def different_stable_ids(self, a: str, b: str) -> bool:
        a_ids = self.stable_ids.get(name_key(a)) or set()
        b_ids = self.stable_ids.get(name_key(b)) or set()
        return bool(a_ids and b_ids and a_ids.isdisjoint(b_ids))

    def shared_stable_ids(self, a: str, b: str) -> set[str]:
        return ((self.stable_ids.get(name_key(a)) or set())
                & (self.stable_ids.get(name_key(b)) or set()))

    def best_spelling(self, key: str) -> str | None:
        seen = self.spellings.get(key) or {}
        return max(seen, key=lambda s: (seen[s], s)) if seen else None


def _stable_player_id(value) -> str | None:
    """Return an id that is safe to compare across the loaded match feeds.

    ATP's ids are alphanumeric strings (for example R0A7) and persist across the archive
    and current feed. The WTA frames currently contain numeric ids from incompatible source
    namespaces, so treating two different numbers as two people would refute real aliases.
    """
    if not isinstance(value, str):
        return None
    player_id = value.strip().upper()
    if not player_id.isalnum():
        return None
    if not any(c.isalpha() for c in player_id) or not any(c.isdigit() for c in player_id):
        return None
    return player_id


def build_evidence(df, since=None) -> MatchEvidence:
    """Index a match frame. ``df`` needs winner_name / loser_name (and date when ``since``
    is given). Kept dependency-light so tests can hand it a three-row frame."""
    ev = MatchEvidence()
    if since is not None and "date" in getattr(df, "columns", ()):
        df = df[df["date"] >= since]
    columns = getattr(df, "columns", ())
    winner_ids = df["winner_id"] if "winner_id" in columns else [None] * len(df)
    loser_ids = df["loser_id"] if "loser_id" in columns else [None] * len(df)
    for w, l, winner_id, loser_id in zip(
            df["winner_name"], df["loser_name"], winner_ids, loser_ids):
        kw, kl = name_key(w), name_key(l)
        if not kw or not kl:
            continue
        ev.opponents.add(frozenset((kw, kl)))
        for key, spelling, raw_id in ((kw, w, winner_id), (kl, l, loser_id)):
            ev.counts[key] = ev.counts.get(key, 0) + 1
            ev.spellings.setdefault(key, {})
            ev.spellings[key][spelling] = ev.spellings[key].get(spelling, 0) + 1
            player_id = _stable_player_id(raw_id)
            if player_id:
                ev.stable_ids.setdefault(key, set()).add(player_id)
    return ev


def player_questions(evidence: MatchEvidence, tour: str, limit: int = MAX_QUESTIONS) -> list[Question]:
    """Near-miss spellings one canonicalisation pass provably cannot merge.

    `_canonicalize_names` unifies anything sharing a `name_key`, so accents and punctuation
    are already handled. What survives it is a DROPPED OR ADDED SURNAME, which changes the
    key itself — the Umag 2026 shape, where one player shipped as two and the event exported
    drawSize 29 for a 28-draw. So the candidate rule is exactly that shape: one key's tokens
    are a strict superset of the other's.

    Note what this deliberately does NOT do: it never proposes a merge on shared-surname
    alone. "Alexander Zverev" and "Mischa Zverev" are not a subset pair and never become a
    question; a pair that has met across a net is dropped here rather than asked about."""
    keys = [k for k in evidence.counts if len(k.split()) >= 2]
    toks = {k: frozenset(k.split()) for k in keys}
    cands: list[tuple[int, str, str, str]] = []
    stable_subjects: set[tuple[str, str]] = set()

    # A single stable id can have three spellings. Pairwise subset questions would then
    # produce an alias chain, but results._canonicalize_names intentionally applies this
    # table once. Build connected dropped-name components and ask every variant directly
    # against the component's most-used spelling instead.
    keys_by_id: dict[str, set[str]] = {}
    for key, player_ids in evidence.stable_ids.items():
        for player_id in player_ids:
            keys_by_id.setdefault(player_id, set()).add(key)
    for player_id, id_keys in keys_by_id.items():
        remaining = set(id_keys)
        while remaining:
            component = {remaining.pop()}
            changed = True
            while changed:
                changed = False
                for candidate in list(remaining):
                    if any(toks.get(candidate, frozenset()) < toks.get(member, frozenset())
                           or toks.get(member, frozenset()) < toks.get(candidate, frozenset())
                           for member in component):
                        component.add(candidate)
                        remaining.remove(candidate)
                        changed = True
            if len(component) < 2:
                continue
            canonical = max(component, key=lambda key: (
                evidence.counts[key], -len(key.split()), evidence.best_spelling(key) or key))
            canonical_spelling = evidence.best_spelling(canonical) or canonical
            for variant in component - {canonical}:
                if variant in PLAYER_ALIASES or canonical in PLAYER_ALIASES:
                    continue
                variant_spelling = evidence.best_spelling(variant) or variant
                subject = tuple(sorted((canonical_spelling, variant_spelling)))
                if evidence.played_each_other(*subject):
                    continue
                stable_subjects.add(subject)
                cands.append((evidence.counts[variant], *subject,
                              f"{variant_spelling!r} ({evidence.counts[variant]} matches) "
                              f"and {canonical_spelling!r} ({evidence.counts[canonical]} "
                              f"matches) share stable player id {player_id}"))

    for short in keys:
        for long in keys:
            if short == long or not toks[short] < toks[long]:
                continue
            # Already covered by a hand-kept entry, or refuted before we spend a token on it.
            if short in PLAYER_ALIASES or long in PLAYER_ALIASES:
                continue
            if frozenset((short, long)) in evidence.opponents:
                continue
            if evidence.different_stable_ids(short, long):
                continue
            if evidence.shared_stable_ids(short, long):
                continue
            a = evidence.best_spelling(short) or short
            b = evidence.best_spelling(long) or long
            # Rarest-first: a split identity is lopsided (many matches under one spelling,
            # a handful under the other), and that is also the ordering that puts the
            # freshly-broken name ahead of a long-settled ambiguity.
            subject = tuple(sorted((a, b)))
            if subject in stable_subjects:
                continue
            cands.append((min(evidence.counts[short], evidence.counts[long]), *subject,
                          f"{a!r} ({evidence.counts[short]} matches) and "
                          f"{b!r} ({evidence.counts[long]} matches) never played each "
                          f"other and differ only by a dropped/added name part"))
    cands.sort(key=lambda c: (c[0], c[1], c[2]))
    return [
        Question(kind="player_alias", tour=tour, subject=(a, b), context=context)
        for _, a, b, context in cands[:limit]
    ]


# ---------------------------------------------------------------------------
# The falsifier — pure, and the only reason a model is allowed near this at all
# ---------------------------------------------------------------------------
def falsify(proposal: dict, asked: dict, evidence: MatchEvidence | None = None) -> str | None:
    """Return why this proposal must be discarded, or None if it survives.

    Pure. Every check here is something the model cannot argue with, and the ordering is
    deliberate: containment first, so a proposal about something we never asked about is
    dead before any of its content is even inspected."""
    kind = proposal.get("kind")
    if kind not in ("player_alias", "wiki_title", "missing_event", "event_identity"):
        return f"unknown proposal kind {kind!r}"
    tour = str(proposal.get("tour") or "")

    if kind == "player_alias":
        variant, canonical = proposal.get("variant"), proposal.get("canonical")
        if not isinstance(variant, str) or not isinstance(canonical, str):
            return "variant/canonical missing or not strings"
        subject = tuple(sorted((variant, canonical)))
        if (kind, tour, subject) not in asked:
            return f"pair {subject!r} was not one of the questions asked"
        if not proposal.get("same_person"):
            return "model did not assert these are the same person"
        if name_key(variant) == name_key(canonical):
            return ("already merged by the shared name key — an alias entry would be a "
                    "no-op (see results._canonicalize_names)")
        if evidence is not None:
            if evidence.played_each_other(variant, canonical):
                return ("these two names have played each other, so they are two people "
                        "— the match record outranks the search result")
            if evidence.different_stable_ids(variant, canonical):
                return ("these names carry different stable player ids, so they are two "
                        "people — the match record outranks the search result")
            if not evidence.known(canonical):
                return f"canonical spelling {canonical!r} does not appear in the match record"
        return None

    if kind in ("missing_event", "event_identity"):
        event_name, coverage_key = proposal.get("event_name"), proposal.get("coverage_key")
        if not isinstance(event_name, str) or not isinstance(coverage_key, str):
            return "event_name/coverage_key missing or not strings"
        if (kind, tour, (event_name, coverage_key)) not in asked:
            return f"event {(event_name, coverage_key)!r} was not one of the questions asked"
        expected_id = coverage_key.removeprefix("espn:") if coverage_key.startswith("espn:") else None
        proposed_id = proposal.get("espn_id")
        if expected_id and str(proposed_id or "") != expected_id:
            return (f"espn_id {proposed_id!r} contradicts deterministic coverage key "
                    f"{coverage_key!r}")
        article = proposal.get("article")
        if article is not None and (not isinstance(article, str) or not article.strip()):
            return "article must be a non-empty string or null"
        tier = proposal.get("tier")
        if tier is not None and normalize_level(tier, tour) is None:
            return f"tier {tier!r} is not in the {tour.upper()} level vocabulary"
        sources = proposal.get("sources")
        if not isinstance(sources, list) or not any(
                isinstance(source, str) and source.startswith(("http://", "https://"))
                for source in sources):
            return "event diagnosis has no cited source URL"
        return None

    espn_name, article = proposal.get("espn_name"), proposal.get("article")
    if not isinstance(espn_name, str) or not isinstance(article, str) or not article.strip():
        return "espn_name/article missing or not strings"
    if (kind, tour, (espn_name,)) not in asked:
        return f"event {espn_name!r} was not one of the questions asked"
    if WIKI_TITLE_OVERRIDES.get(espn_name) == article:
        return "override already present in config — no-op"
    tier = proposal.get("tier")
    # The model must speak our vocabulary, not Wikipedia's prose. `normalize_level` folds
    # the dialects it is allowed to fold and returns None for everything else; a tier that
    # cannot survive it would ship an unreadable string on a card.
    if tier is not None and normalize_level(tier, tour) is None:
        return f"tier {tier!r} is not in the {tour.upper()} level vocabulary"
    return None


def verify_article(proposal: dict, meta_fn=None, year: int | None = None) -> str | None:
    """Empirical half of the falsifier for events: does the proposed override actually FIX
    the problem? Applies it — runs OUR parser against the article the model named — and
    rejects anything that resolves no better than what we already had. Network; ``meta_fn``
    is injectable so tests never touch Wikipedia."""
    if proposal.get("kind") not in ("wiki_title", "missing_event", "event_identity"):
        return None
    if proposal.get("kind") in ("missing_event", "event_identity") and not proposal.get("article"):
        return None
    if meta_fn is None:
        from .draws_wiki import event_meta as meta_fn  # local: keeps the import optional
    year = year or date.today().year
    try:
        surface, category = meta_fn(proposal["article"], year, proposal.get("tour") or "atp")
    except Exception as e:                                  # noqa: BLE001 — never raise here
        return f"article lookup failed: {e}"
    if surface is None and category is None:
        return (f"article {proposal['article']!r} resolves to nothing our parser can read "
                f"(no surface, no category) — the override would not fix anything")
    proposal["parsed_surface"], proposal["parsed_category"] = surface, category
    return None


# ---------------------------------------------------------------------------
# The model call
# ---------------------------------------------------------------------------
_SYSTEM = """You resolve identity mismatches for a tennis forecasting model.

Two sources disagree about how to spell something and the model has shipped it as two
different things. Your job is to say — from evidence you can cite — whether two spellings
name one thing, and if so which spelling is canonical.

Rules:
- Answer ONLY the numbered questions given. Never introduce a pair or an event that is not
  on the list; anything else is discarded unread.
- Use web search. Prefer tournament entry lists, official tour player profiles, and
  Wikipedia articles over aggregator pages.
- Uncertainty is a valid answer and is much cheaper than a wrong merge. If the evidence is
  thin, say so and set the assertion false. A missed alias costs one more week; a wrong
  merge silently fuses two players' rating histories.
- Two people with the same surname are usually relatives, not one person. Only assert one
  identity when a source shows the SAME individual written both ways.
- A coverage question is already backed by deterministic match/schedule evidence. Search may
  identify the official event, article, tier, cancellation, or source-feed explanation, but
  must not replace its coverage key or claim a different ESPN id than the one supplied.
"""

_SCHEMA_HINT = """Reply with prose reasoning, then end your message with ONE fenced JSON
block (```json ... ```) of this exact shape:

{"proposals": [
  {"kind": "player_alias", "tour": "atp", "variant": "<the spelling to retire>",
   "canonical": "<the spelling to keep>", "same_person": true,
   "reason": "<one sentence>", "sources": ["<url>", ...]},
  {"kind": "wiki_title", "tour": "atp", "espn_name": "<exact name from the question>",
   "article": "<exact Wikipedia article title>", "tier": "<ATP 250|WTA 500|...|null>",
   "reason": "<one sentence>", "sources": ["<url>", ...]},
  {"kind": "missing_event", "tour": "wta", "event_name": "<exact asked name>",
   "coverage_key": "<exact asked key>", "espn_id": "<id from espn:key, or null>",
   "official_name": "<official title or null>", "article": "<Wikipedia title or null>",
   "tier": "<WTA 125|...|null>", "event_exists": true,
   "reason": "<why this event is real and/or why a source may miss it>", "sources": ["<url>"]},
  {"kind": "event_identity", "tour": "atp", "event_name": "<exact asked name>",
   "coverage_key": "<exact asked key>", "espn_id": "<verified id or null>",
   "official_name": "<official title or null>", "article": "<Wikipedia title or null>",
   "tier": "<ATP 250|...|null>", "event_exists": true,
   "reason": "<one sentence>", "sources": ["<url>"]}
]}

`variant`/`canonical`, `espn_name`, and coverage `event_name`/`coverage_key` must be copied
CHARACTER-FOR-CHARACTER from the question. `tier` must be one of the tour's tiers or null.
Emit an empty list rather than a guess."""


def render_prompt(questions: list[Question]) -> str:
    lines = ["Resolve these open identities.\n"]
    for i, q in enumerate(questions, 1):
        if q.kind == "player_alias":
            a, b = q.subject
            lines.append(f"{i}. [{q.tour.upper()} player] Are {a!r} and {b!r} the same "
                         f"person? Observed: {q.context}")
        elif q.kind == "wiki_title":
            lines.append(f"{i}. [{q.tour.upper()} event] Which Wikipedia article covers the "
                         f"{date.today().year} edition of {q.subject[0]!r}, and what tier is "
                         f"it? Observed: {q.context}")
        else:
            name, coverage_key = q.subject
            ask = ("Why is this confirmed event missing from the site, and what official "
                   "title/article/tier identifies it?" if q.kind == "missing_event" else
                   "What stable official identity, if any, belongs to this id-less event?")
            lines.append(f"{i}. [{q.tour.upper()} {q.kind}] {ask} Event {name!r}; "
                         f"coverage key {coverage_key!r}. Observed: {q.context}")
    lines.append("\n" + _SCHEMA_HINT)
    return "\n".join(lines)


_FENCE = re.compile(r"```json\s*(.+?)\s*```", re.S)


def extract_json(text: str) -> dict:
    """Last fenced JSON block, else the last balanced-looking object. Returns {} rather than
    raising: an unparseable answer is simply zero proposals, which is a safe outcome."""
    blocks = _FENCE.findall(text or "")
    if not blocks:
        start, end = (text or "").find("{"), (text or "").rfind("}")
        blocks = [text[start:end + 1]] if 0 <= start < end else []
    for block in reversed(blocks):
        try:
            parsed = json.loads(block)
        except (ValueError, TypeError):
            continue
        if isinstance(parsed, dict):
            return parsed
    return {}


def ask_openrouter(questions: list[Question], *, opener=None, api_key: str | None = None,
                   model: str = MODEL) -> tuple[list[dict], str]:
    """Make one search-enabled OpenRouter call; return proposals and the full model text.

    This deliberately uses the small OpenAI-compatible HTTP surface instead of adding an
    SDK to the workflow environment. OpenRouter performs the server-tool loop itself, so
    this remains one request even when the model searches several times. Parsing the last
    fenced block is intentional: the deterministic ``falsify`` step, not a provider schema,
    is the boundary that decides what can reach the config patch.
    """
    from urllib.request import Request, urlopen

    api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")
    payload = {
        "model": model,
        "max_tokens": 16000,
        "reasoning": {"effort": "medium", "exclude": True},
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": render_prompt(questions)},
        ],
        "tools": [{
            "type": "openrouter:web_search",
            "parameters": {"max_uses": 8, "max_total_results": 24},
        }],
        "max_tool_calls": 8,
    }
    request = Request(
        OPENROUTER_URL,
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    open_request = opener or urlopen
    with open_request(request, timeout=600) as response:
        result = json.loads(response.read())
    if not isinstance(result, dict):
        raise RuntimeError("OpenRouter returned a non-object response")
    if result.get("error"):
        error = result["error"]
        message = error.get("message") if isinstance(error, dict) else None
        raise RuntimeError(f"OpenRouter error: {message or 'request failed'}")
    choices = result.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("OpenRouter returned no choices")
    choice = choices[0] if isinstance(choices[0], dict) else {}
    message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
    if message.get("refusal") or choice.get("finish_reason") in {"content_filter", "refusal"}:
        return [], "(model declined the request)"
    content = message.get("content")
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        text = "\n".join(
            block.get("text", "") for block in content if isinstance(block, dict)
        )
    else:
        text = ""
    raw = extract_json(text).get("proposals")
    return (raw if isinstance(raw, list) else []), text


def adjudicate(questions: list[Question], raw: list[dict],
               evidence: MatchEvidence | dict[str, MatchEvidence] | None = None,
               meta_fn=None) -> dict:
    """Run every proposal past both halves of the falsifier. Returns accepted + rejected;
    the rejected list carries its reason because that is what makes the falsifier reviewable
    — a PR that shows what it threw away and why is one a human can actually audit."""
    asked = {q.key: q for q in questions}
    accepted, rejected = [], []
    for proposal in raw:
        if not isinstance(proposal, dict):
            rejected.append({"proposal": proposal, "reason": "not an object"})
            continue
        proposal_evidence = (evidence.get(str(proposal.get("tour") or ""))
                             if isinstance(evidence, dict) else evidence)
        reason = falsify(proposal, asked, proposal_evidence) or verify_article(proposal, meta_fn)
        (rejected.append({**proposal, "reason": reason}) if reason
         else accepted.append(proposal))
    return {"accepted": accepted, "rejected": rejected}


# ---------------------------------------------------------------------------
# Emitting the patch
# ---------------------------------------------------------------------------
def _lit(s: str) -> str:
    """A double-quoted Python string literal, so a proposed entry is indistinguishable in
    style from the hand-written ones around it. `repr` would emit single quotes and make
    every bot line visually obvious in a diff a human is trying to read on its merits.
    `ensure_ascii=False` keeps accented names readable rather than \\uXXXX-escaped."""
    return json.dumps(s, ensure_ascii=False)


def _entries(proposals: list[dict], today: str) -> dict:
    """Accepted proposals -> {table: [source lines]}. `PLAYER_ALIASES` is keyed by
    `name_key(variant)` because that is what `_canonicalize_names` looks up."""
    out: dict = {}
    for p in proposals:
        if p["kind"] == "player_alias":
            key, val, table = name_key(p["variant"]), p["canonical"], "PLAYER_ALIASES"
        elif p["kind"] == "wiki_title":
            key, val, table = p["espn_name"], p["article"], "WIKI_TITLE_OVERRIDES"
        elif p.get("article"):
            key, val, table = p["event_name"], p["article"], "WIKI_TITLE_OVERRIDES"
        else:
            continue                         # diagnosis artifact only; no deterministic edit
        why = " ".join(str(p.get("reason") or "proposed by the alias proposer").split())
        src = (p.get("sources") or [None])[0]
        out.setdefault(table, []).append(
            f'    # {today} alias-proposer: {why}\n'
            + (f'    # {src}\n' if src else "")
            + f'    {_lit(key)}: {_lit(val)},\n')
        # An article that resolves but whose infobox omits `category` is exactly the Nordea
        # / Mifel shape: the title override alone still leaves the tier unresolved, so the
        # curated fallback has to carry it. Bare number, matching the table's convention.
        tier = p.get("tier")
        if p["kind"] in ("wiki_title", "missing_event", "event_identity") \
                and tier and not p.get("parsed_category"):
            event_name = p.get("espn_name") or p.get("event_name")
            digits = re.search(r"\d+", str(tier))
            if digits and event_name not in EVENT_TIER_FALLBACK:
                out.setdefault("EVENT_TIER_FALLBACK", []).append(
                    f'    # {today} alias-proposer: article resolves but its infobox '
                    f'carries no `category`\n'
                    f'    {_lit(event_name)}: {_lit(digits.group())},\n')
    return out


def apply_to_config(source: str, proposals: list[dict], today: str | None = None) -> str:
    """Insert accepted entries into the config source, at the end of each dict literal.
    Returns the new source. Raises KeyError if a table is missing — a silent no-op edit
    would produce an empty PR that looks like a clean bill of health."""
    today = today or str(date.today())
    for table, lines in _entries(proposals, today).items():
        opener = re.search(rf"^{table}\b[^=\n]*=\s*\{{\s*$", source, re.M)
        if not opener:
            raise KeyError(f"{table} dict literal not found in config source")
        closer = re.compile(r"^\}", re.M).search(source, opener.end())
        if not closer:
            raise KeyError(f"{table} dict literal is not closed at column 0")
        source = source[:closer.start()] + "".join(lines) + source[closer.start():]
    return source


def summarize(result: dict) -> str:
    """Markdown for the PR body. Shows the rejections too — the falsifier's work is the
    reason to trust the accepted half."""
    lines = ["## Proposed identity fixes", ""]
    if not result["accepted"]:
        lines.append("_No proposal survived the falsifier._")
    for p in result["accepted"]:
        if p["kind"] == "player_alias":
            what = f"`{p['variant']}` -> `{p['canonical']}`"
        elif p["kind"] == "wiki_title":
            what = f"`{p['espn_name']}` -> [{p['article']}] ({p.get('tier') or 'tier unchanged'})"
        else:
            article = f" -> [{p['article']}]" if p.get("article") else ""
            what = (f"`{p['event_name']}` ({p['coverage_key']}){article} "
                    f"({p.get('tier') or 'tier unknown'})")
        lines.append(f"- **{p['kind']}** ({p.get('tour')}): {what} — {p.get('reason', '')}")
        for s in (p.get("sources") or [])[:3]:
            lines.append(f"  - {s}")
    if result["rejected"]:
        lines += ["", "### Discarded by the falsifier", ""]
        for p in result["rejected"]:
            lines.append(f"- `{p.get('variant') or p.get('espn_name') or p.get('event_name')}` "
                         f"— {p.get('reason')}")
    lines += ["", "Every entry above is a *proposal*. The runtime is unchanged and stays "
              "fully deterministic; merging this PR is what adopts it."]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
def main() -> int:
    import argparse

    from ..config import MODEL_DIR

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--health", help="path to health.json (event questions)")
    ap.add_argument("--tour", action="append", dest="tours",
                    help="scan this tour's match frame for split player identities (repeatable)")
    ap.add_argument("--out", help="write the adjudication result as JSON here")
    ap.add_argument("--body", help="write the PR-body markdown here")
    ap.add_argument("--apply", action="store_true", help="edit config.py in place")
    ap.add_argument("--dry-run", action="store_true", help="print the questions; make no API call")
    args = ap.parse_args()

    try:
        questions: list[Question] = []
        if args.health and os.path.exists(args.health):
            with open(args.health) as fh:
                questions += questions_from_health(json.load(fh))
        evidence_by_tour: dict[str, MatchEvidence] = {}
        for tour in args.tours or []:
            import pandas as pd

            from .results import load_matches
            df = load_matches(tour)
            since = pd.Timestamp.now().normalize() - pd.Timedelta(days=SCAN_WINDOW_DAYS)
            evidence_by_tour[tour] = build_evidence(df, since=since)
            questions += player_questions(evidence_by_tour[tour], tour)
        questions = questions[:MAX_QUESTIONS]

        for q in questions:
            print(f"  ASK/{q.tour} {q.kind}: {q.subject}")
        if not questions:
            print("  no open identities — nothing to propose")
            return 0
        if args.dry_run:
            print(render_prompt(questions))
            return 0

        raw, text = ask_openrouter(questions)
        result = adjudicate(questions, raw, evidence_by_tour)
        result["questions"] = [q.context for q in questions]
        result["transcript"] = text
        for p in result["accepted"]:
            print(f"  ACCEPT: {p}")
        for p in result["rejected"]:
            print(f"  REJECT: {p.get('reason')}")

        if args.out:
            with open(args.out, "w") as fh:
                json.dump(result, fh, indent=2)
        if args.body:
            with open(args.body, "w") as fh:
                fh.write(summarize(result))
        if args.apply and result["accepted"]:
            cfg = MODEL_DIR / "src" / "tennis_model" / "config.py"
            cfg.write_text(apply_to_config(cfg.read_text(), result["accepted"]))
            print(f"  applied {len(result['accepted'])} entr(ies) to {cfg}")
    except Exception as e:                                  # noqa: BLE001
        # Exit 0 on every failure. This job has no consumers that can be hurt by silence,
        # and a red proposer run would page the owner for something that never touched the
        # site — the exact false-alarm class report-data-health.sh exists to avoid.
        print(f"::warning::alias proposer failed: {type(e).__name__}: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
