"""
Agent 3 — KPI Generation Agent.

Returns a flat {label: value} dictionary that the UI renders as KPI cards.
The set of metrics is data-driven: we always show top-level counts and the
sum/avg/min/max for every numeric column.
"""
from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd


class KpiAgent:

    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        kpis: Dict[str, Any] = {}

        # Universal counts.
        kpis['Total Rows'] = int(len(df))
        kpis['Total Columns'] = int(len(df.columns))

        # Numeric column aggregates.
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        for col in numeric_cols:
            series = df[col].dropna()
            if series.empty:
                continue
            kpis[f'Sum of {col}'] = _round(series.sum())
            kpis[f'Average {col}'] = _round(series.mean())
            kpis[f'Max {col}'] = _round(series.max())
            kpis[f'Min {col}'] = _round(series.min())

        # Top categorical by frequency.
        cat_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()
        for col in cat_cols[:3]:  # keep the KPI grid compact
            try:
                top = df[col].mode(dropna=True)
                if not top.empty:
                    kpis[f'Most Common {col}'] = str(top.iloc[0])
            except Exception:
                pass

        return kpis


def _round(v) -> float:
    try:
        f = float(v)
        if np.isnan(f) or np.isinf(f):
            return 0.0
        # Keep compact decimals.
        return round(f, 3)
    except Exception:
        return 0