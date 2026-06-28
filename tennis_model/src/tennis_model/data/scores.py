"""Tennis score-string parsing.

Score strings look like "6-2 6-1", "7-6(4) 6-3", "2-6 6-3 7-6(10)", with optional
tie-break point counts in parentheses, and incomplete-match markers like "RET",
"W/O", "DEF", "ABD". We extract per-player games won and whether the match finished
normally (a retirement is a win, but a meaningless margin for Weighted-Elo).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# A set token: "6-2", "7-6(4)", "6-7(10)". Capture the two game counts; ignore the
# tie-break parenthetical and any stray bracketed match-tiebreak like "[10-7]".
_SET_RE = re.compile(r"^(\d+)-(\d+)(?:\(\d+\))?$")
_INCOMPLETE = ("RET", "W/O", "WO", "DEF", "ABD", "ABN", "DEFAULT", "RETIRED", "UNFINISHED")


@dataclass(frozen=True)
class ParsedScore:
    winner_games: int
    loser_games: int
    sets: int            # number of completed sets parsed
    completed: bool      # finished normally (no retirement / walkover)
    walkover: bool       # no play occurred


def parse_score(score: object) -> ParsedScore:
    """Parse a score string into games won by winner/loser and completion status."""
    if not isinstance(score, str):
        return ParsedScore(0, 0, 0, False, True)
    s = score.strip()
    if not s:
        return ParsedScore(0, 0, 0, False, True)

    upper = s.upper()
    walkover = "W/O" in upper or upper in ("WO", "W/O", "DEF", "ABD")
    completed = True
    wg = lg = sets = 0

    for tok in s.split():
        tok_u = tok.upper().strip(",.")
        if any(tok_u.startswith(m) or tok_u == m for m in _INCOMPLETE):
            completed = False
            continue
        m = _SET_RE.match(tok)
        if not m:
            # unparseable fragment (e.g. "[10-7]" match tiebreak, stray text) -> skip
            continue
        a, b = int(m.group(1)), int(m.group(2))
        wg += a
        lg += b
        sets += 1

    if walkover or sets == 0:
        completed = False
    return ParsedScore(wg, lg, sets, completed and not walkover, walkover)


def game_diff(parsed: ParsedScore) -> int:
    """Signed game margin from the winner's perspective (>= 0 for completed wins)."""
    return parsed.winner_games - parsed.loser_games
