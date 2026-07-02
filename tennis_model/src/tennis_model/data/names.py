"""The single player-name canonicalisation key, shared by every consumer.

Contract: accent/punctuation-insensitive — NFKD-decompose and drop combining marks,
fold hyphens/periods/apostrophes/backticks to spaces, lowercase, collapse whitespace.
Non-strings map to "".

There is a TypeScript port of this function (`nameKey` in web/lib/live.ts) used to
join ESPN live names to model players in the browser. Behavioural parity between the
two is pinned by the shared fixture tennis_model/tests/fixtures/name_key_cases.json,
consumed by both pytest (test_names_merge.py) and the web test suite. Change one
implementation and the fixture, and the other side's tests will tell you if the port
needs the same change. Known benign divergence: Python strips ALL combining marks,
the TS port strips U+0300-U+036F — identical for Latin-script tennis names.
"""

from __future__ import annotations

import re
import unicodedata


def name_key(name: object) -> str:
    """Accent/punctuation-insensitive key so the same player matches across sources."""
    if not isinstance(name, str):
        return ""
    s = "".join(c for c in unicodedata.normalize("NFKD", name) if not unicodedata.combining(c))
    s = re.sub(r"[-.'`]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()
