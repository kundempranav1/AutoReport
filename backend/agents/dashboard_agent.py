"""
Agent 4 — Dashboard Generation Agent.

Builds up to four Plotly figures (Bar, Line, Pie, Histogram) by inspecting
the dataset. Each chart is returned as a JSON-serialisable dict that the
React frontend can hand straight to `react-plotly.js`.

Selection logic:

    Bar Chart   — top categorical column (≤ 30 unique) → counts,
                  or sum of a numeric column grouped by a category
    Line Chart  — first numeric column across the row index
                  (useful for time-like or ordered data)
    Pie Chart   — top categorical (≤ 8 unique) → counts
    Histogram   — first numeric column → distribution

If the dataset can't support a particular chart we just skip it.
"""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd
# pyrefly: ignore [missing-import]
import plotly.graph_objects as go


# A single accent palette — keeps the dashboard looking cohesive.
PALETTE = ['#1e6cf6', '#3b82f6', '#60a5fa', '#93c5fd', '#0ea5e9', '#6366f1',
           '#22d3ee', '#a78bfa']


class DashboardAgent:

    def run(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        if df is None or df.empty:
            return []

        charts: List[Dict[str, Any]] = []
        charts.append(self._bar_chart(df))
        charts.append(self._line_chart(df))
        charts.append(self._pie_chart(df))
        charts.append(self._histogram(df))

        # Drop None entries (e.g. when the dataset couldn't support a chart).
        return [c for c in charts if c is not None]

    # ------------------------------------------------------------------
    # 1. Bar — sum of (first) numeric column by (first) reasonable category
    # ------------------------------------------------------------------
    def _bar_chart(self, df: pd.DataFrame) -> Dict[str, Any] | None:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cat_col = _best_categorical(df, max_unique=30)

        if numeric_cols and cat_col:
            num = numeric_cols[0]
            grouped = (
                df.groupby(cat_col, dropna=True)[num]
                .sum()
                .sort_values(ascending=False)
                .head(15)
            )
            fig = go.Figure(
                data=[
                    go.Bar(
                        x=grouped.index.astype(str).tolist(),
                        y=grouped.values.tolist(),
                        marker_color=PALETTE[0],
                    )
                ]
            )
            fig.update_layout(xaxis_title=cat_col, yaxis_title=num)
            fig_dict = fig.to_dict()
            return {'title': f'Sum of {num} by {cat_col}', 'data': fig_dict['data'], 'layout': fig_dict['layout']}

        if cat_col and not numeric_cols:
            counts = df[cat_col].value_counts().head(15)
            fig = go.Figure(
                data=[
                    go.Bar(
                        x=counts.index.astype(str).tolist(),
                        y=counts.values.tolist(),
                        marker_color=PALETTE[0],
                    )
                ]
            )
            fig.update_layout(xaxis_title=cat_col, yaxis_title='Count')
            fig_dict = fig.to_dict()
            return {'title': f'Counts of {cat_col}', 'data': fig_dict['data'], 'layout': fig_dict['layout']}

        return None

    # ------------------------------------------------------------------
    # 2. Line — first numeric column over the row index
    # ------------------------------------------------------------------
    def _line_chart(self, df: pd.DataFrame) -> Dict[str, Any] | None:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if not numeric_cols:
            return None
        num = numeric_cols[0]
        y = df[num].head(200).tolist()
        x = list(range(len(y)))
        fig = go.Figure(
            data=[go.Scatter(x=x, y=y, mode='lines+markers', line=dict(color=PALETTE[1]))]
        )
        fig.update_layout(xaxis_title='Index', yaxis_title=num)
        fig_dict = fig.to_dict()
        return {'title': f'{num} over Index', 'data': fig_dict['data'], 'layout': fig_dict['layout']}

    # ------------------------------------------------------------------
    # 3. Pie — counts of a low-cardinality category
    # ------------------------------------------------------------------
    def _pie_chart(self, df: pd.DataFrame) -> Dict[str, Any] | None:
        cat_col = _best_categorical(df, max_unique=8)
        if not cat_col:
            return None
        counts = df[cat_col].value_counts().head(8)
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=counts.index.astype(str).tolist(),
                    values=counts.values.tolist(),
                    marker=dict(colors=PALETTE),
                )
            ]
        )
        fig_dict = fig.to_dict()
        return {'title': f'Distribution of {cat_col}', 'data': fig_dict['data'], 'layout': fig_dict['layout']}

    # ------------------------------------------------------------------
    # 4. Histogram — distribution of a numeric column
    # ------------------------------------------------------------------
    def _histogram(self, df: pd.DataFrame) -> Dict[str, Any] | None:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if not numeric_cols:
            return None
        num = numeric_cols[0]
        fig = go.Figure(
            data=[go.Histogram(x=df[num].dropna().tolist(), marker_color=PALETTE[2])]
        )
        fig.update_layout(xaxis_title=num, yaxis_title='Frequency')
        fig_dict = fig.to_dict()
        return {'title': f'Distribution of {num}', 'data': fig_dict['data'], 'layout': fig_dict['layout']}


# ----------------------------------------------------------------------
def _best_categorical(df: pd.DataFrame, max_unique: int) -> str | None:
    """Return the column name with the smallest unique-cardinality count
    that falls within the supplied bound. Falls back to the first
    non-numeric column if no column is below the bound."""
    cat_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()
    if not cat_cols:
        return None
    for col in cat_cols:
        n = df[col].nunique(dropna=True)
        if 1 < n <= max_unique:
            return col
    # Fallback: pick any non-numeric column.
    return cat_cols[0]