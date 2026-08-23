"""Small, dependency-free timing seam for pipeline hot paths.

The hourly refresh log is the profiler we always have in CI. Keep each measurement to
one atomic line so ATP/WTA output remains readable when their exports run concurrently.
"""

from __future__ import annotations

import time
from contextlib import contextmanager


@contextmanager
def timed(tour: str, stage: str):
    """Print elapsed wall time for one named per-tour stage."""
    started = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - started
        print(f"  timing/{tour}/{stage}: {elapsed:.3f}s", flush=True)
