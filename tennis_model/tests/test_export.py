"""Unit checks for the web-export serialisation seam (model/export.py).

Focus: _write must never emit non-finite floats. json.dump allows the bare tokens
NaN/Infinity by default (valid Python-JSON), but the browser's strict JSON.parse
rejects them — a single NaN in a shipped file makes the whole file fail to parse and
the page render blank (the /player and /style WTA regression). Runnable directly or
under pytest.
"""

from __future__ import annotations

import json
import math
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import tennis_model.model.export as export


def _raise_nonfinite(tok):
    raise ValueError(f"non-finite token {tok!r}")


def _strict_load(text: str):
    """Parse the way a browser does — reject NaN/Infinity instead of accepting them."""
    return json.loads(text, parse_constant=_raise_nonfinite)


def test_finite_replaces_nonfinite_scalars():
    assert export._finite(math.nan) is None
    assert export._finite(math.inf) is None
    assert export._finite(-math.inf) is None
    # finite values (and non-floats) pass through untouched
    assert export._finite(0.5) == 0.5
    assert export._finite(0) == 0 and export._finite("6-4 6-3") == "6-4 6-3"
    assert export._finite(None) is None and export._finite(True) is True
    print("ok test_finite_replaces_nonfinite_scalars")


def test_finite_recurses_into_nested_containers():
    src = {"recent": [{"score": math.nan, "won": True}, {"score": "6-3", "won": False}],
           "style": {"a": 0.5, "b": float("nan")}, "history": [[1.0, math.inf]]}
    out = export._finite(src)
    assert out["recent"][0]["score"] is None and out["recent"][0]["won"] is True
    assert out["recent"][1]["score"] == "6-3"
    assert out["style"] == {"a": 0.5, "b": None}
    assert out["history"] == [[1.0, None]]
    # the sanitised structure round-trips through a strict (browser-like) parser
    assert _strict_load(json.dumps(out)) == out
    print("ok test_finite_recurses_into_nested_containers")


def test_write_output_is_browser_strict_parseable():
    """A NaN reaching _write (a scoreless match) must ship as null, not the NaN token."""
    payload = {"Sabalenka": {"recent": [{"opp": "Svitolina", "score": math.nan, "won": True}]}}
    orig = export.output_dir
    try:
        with tempfile.TemporaryDirectory() as d:
            export.output_dir = lambda tour: Path(d) / tour
            export._write("wta", "profiles.json", payload)
            text = (Path(d) / "wta" / "profiles.json").read_text(encoding="utf-8")
    finally:
        export.output_dir = orig
    assert "NaN" not in text                       # the bare invalid token is gone
    parsed = _strict_load(text)                     # and it parses under browser rules
    assert parsed["Sabalenka"]["recent"][0]["score"] is None
    print("ok test_write_output_is_browser_strict_parseable")


if __name__ == "__main__":
    test_finite_replaces_nonfinite_scalars()
    test_finite_recurses_into_nested_containers()
    test_write_output_is_browser_strict_parseable()
    print("\nALL PASSED")
