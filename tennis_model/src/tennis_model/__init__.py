"""Men's (ATP) tennis prediction model.

A hybrid forecasting pipeline:
  data  ->  surface-blended Elo  +  serve/return point model  ->  XGBoost combiner
        ->  single-match predictor  +  Monte Carlo draw simulator

See README.md for methodology and the design rationale.
"""

from __future__ import annotations

__version__ = "0.1.0"
