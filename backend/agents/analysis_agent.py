"""
Agent 2 — Analysis Agent.

Produces a dictionary describing the cleaned dataset:

    * row & column counts
    * per-column dtypes
    * missing-value counts
    * numeric describe() summary
    * categorical describe() summary
    * Pearson correlation matrix across numeric columns
"""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd


class AnalysisAgent:

    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        if df is None or df.empty:
            return {
                'rows': 0,
                'columns': 0,
                'dtypes': {},
                'missing': {},
                'numeric_summary': {},
                'categorical_summary': {},
                'correlation': {},
            }

        # --- Counts --------------------------------------------------------
        rows = int(len(df))
        cols = int(len(df.columns))

        # --- Dtypes (stringify for JSON) -----------------------------------
        dtypes = {c: str(df[c].dtype) for c in df.columns}

        # --- Missing values -----------------------------------------------
        missing = {c: int(df[c].isna().sum()) for c in df.columns}

        # --- Numeric summary ----------------------------------------------
        numeric_df = df.select_dtypes(include=[np.number])
        numeric_summary: Dict[str, Dict[str, float]] = {}
        if not numeric_df.empty:
            desc = numeric_df.describe().to_dict()
            for col, stats in desc.items():
                numeric_summary[col] = {k: _safe_float(v) for k, v in stats.items()}

        # --- Categorical summary ------------------------------------------
        cat_df = df.select_dtypes(exclude=[np.number])
        categorical_summary: Dict[str, Dict[str, Any]] = {}
        for col in cat_df.columns:
            try:
                top = cat_df[col].mode(dropna=True)
                top_val = top.iloc[0] if not top.empty else None
                categorical_summary[col] = {
                    'unique': int(cat_df[col].nunique(dropna=True)),
                    'top': _safe_scalar(top_val),
                }
            except Exception:
                categorical_summary[col] = {'unique': 0, 'top': None}

        # --- Correlation --------------------------------------------------
        correlation: Dict[str, Dict[str, float]] = {}
        if not numeric_df.empty and numeric_df.shape[1] >= 2:
            corr = numeric_df.corr(numeric_only=True)
            for r in corr.columns:
                correlation[str(r)] = {
                    str(c): _safe_float(corr.loc[r, c]) for c in corr.columns
                }

        return {
            'rows': rows,
            'columns': cols,
            'dtypes': dtypes,
            'missing': missing,
            'numeric_summary': numeric_summary,
            'categorical_summary': categorical_summary,
            'correlation': correlation,
        }


def _safe_float(v) -> float:
    try:
        f = float(v)
        if np.isnan(f) or np.isinf(f):
            return 0.0
        return f
    except Exception:
        return 0.0


def _safe_scalar(v) -> Any:
    try:
        if v is None:
            return None
        if isinstance(v, (np.integer,)):
            return int(v)
        if isinstance(v, (np.floating,)):
            return _safe_float(v)
        return v
    except Exception:
        return None