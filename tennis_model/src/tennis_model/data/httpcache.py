"""Opt-in on-disk cache for historical (immutable) API responses.

Backfills of completed seasons re-fetch thousands of rate-limited URLs whenever a
run crashes or is repeated — the WTA API hard-locks after ~2k calls, so a restart
used to re-spend hours of 429 budget. Caching responses by URL makes a rerun
resume in seconds from where the last one stopped.

Scope: ONLY data that can no longer change (seasons strictly before the current
year). Live or current-season fetches must never be served from this cache — the
enabling caller owns that decision (see wta_stats.download_wta_stats). Entries
never expire; deleting the cache directory is the reset.

Leaf module: stdlib only, no package imports, so any scraper can use it.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

# Distinguishes "upstream said 404" (deterministic, worth caching so reruns skip
# the call) from a plain miss. Transient failures are never cached.
_SENTINEL_404 = {"__http_404__": True}


class ResponseCache:
    """URL-keyed JSON response cache. One file per URL, atomic writes."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, url: str) -> Path:
        return self.root / (hashlib.sha256(url.encode("utf-8")).hexdigest() + ".json")

    def get(self, url: str) -> tuple[bool, object]:
        """Return (hit, value); a cached 404 is (True, None). Corrupt files are misses."""
        p = self._path(url)
        if not p.exists():
            return False, None
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False, None  # partial/corrupt entry: treat as miss, it gets rewritten
        if data == _SENTINEL_404:
            return True, None
        return True, data

    def put(self, url: str, data: object) -> None:
        """Store a successful response, or None for a deterministic upstream 404."""
        p = self._path(url)
        tmp = p.with_suffix(".tmp")  # atomic: a crash mid-write must not corrupt the entry
        tmp.write_text(json.dumps(_SENTINEL_404 if data is None else data),
                       encoding="utf-8")
        tmp.replace(p)
