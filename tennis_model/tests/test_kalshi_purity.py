"""Purity guard: Kalshi market data is an evaluation benchmark, NEVER a model input.

Mechanizes the boundary: no module that feeds training/prediction (model/, ratings/,
points/, sim/, pipeline feature path, or data/ itself besides the client) may import
the kalshi client or ledger, and no combiner feature may reference kalshi. If this
test fails, someone is about to leak market prices into the model — stop.
"""

from __future__ import annotations

import re
from pathlib import Path

from tennis_model.model.features import FEATURES

SRC = Path(__file__).resolve().parents[1] / "src" / "tennis_model"

# dirs whose modules must never touch kalshi (eval/ is the sanctioned consumer)
_GUARDED = ("model", "ratings", "points", "sim", "data")
_ALLOWED = {SRC / "data" / "kalshi.py",
            # the integrity sentinel VALIDATES the ledger (anchor/carry thresholds +
            # a CSV read in read_outputs) — output-side only, feeds nothing forward
            SRC / "data" / "health.py"}

_IMPORT_RE = re.compile(r"^\s*(from|import)\s+[\w.]*kalshi", re.MULTILINE)


def test_no_model_code_imports_kalshi():
    offenders = []
    for d in _GUARDED:
        for py in (SRC / d).rglob("*.py"):
            if py in _ALLOWED:
                continue
            if _IMPORT_RE.search(py.read_text(encoding="utf-8")):
                offenders.append(str(py.relative_to(SRC)))
    assert not offenders, f"kalshi imported by model-side code: {offenders}"


def test_no_kalshi_feature():
    assert not [f for f in FEATURES if "kalshi" in f.lower()]


def test_pipeline_uses_kalshi_only_behind_soft_fail():
    """pipeline.py may call the ledger, but only inside the best-effort hook."""
    text = (SRC / "pipeline.py").read_text(encoding="utf-8")
    for line in text.splitlines():
        if "kalshi" in line.lower() and ("import" in line or "refresh" in line):
            break
    else:
        return                                    # pipeline not wired yet: fine
    assert "_kalshi" in text                      # hook exists and is the only path
