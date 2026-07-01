"""
Agent 4 — Dashboard Generation Agent.

Builds up to five Plotly figures (Bar, Line, Pie, Histogram, and Sales Forecast)
by inspecting the dataset. Each chart is returned as a JSON-serialisable dict
that the React frontend can hand straight to `react-plotly.js`.

Selection logic:
    Bar Chart   — top categorical column (≤ 30 unique) → counts,
                  or sum of a numeric column grouped by a category
    Line Chart  — first numeric column across the row index
                  (useful for time-like or ordered data)
    Pie Chart   — top categorical (≤ 8 unique) → counts
    Histogram   — first numeric column → distribution
    Forecast    — identifies date-like and sales-like columns, performs
                  aggregated linear regression trend projections with
                  confidence margins.

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
        charts.append(self._sales_forecast_chart(df))

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

    # ------------------------------------------------------------------
    # 5. Future Sales Forecast & Trend Prediction (NEW Feature)
    # ------------------------------------------------------------------
    def _sales_forecast_chart(self, df: pd.DataFrame) -> Dict[str, Any] | None:
        # Detect datetime-like column
        date_col = None
        for col in df.columns:
            if df[col].dtype.name.startswith('datetime'):
                date_col = col
                break
        if not date_col:
            for col in df.columns:
                col_lower = col.lower()
                if any(k in col_lower for k in ['date', 'time', 'year', 'month', 'timestamp', 'created']):
                    try:
                        pd.to_datetime(df[col].head(5), errors='raise')
                        date_col = col
                        break
                    except Exception:
                        continue

        # Detect sales-like column
        sales_col = None
        for col in df.select_dtypes(include=[np.number]).columns:
            col_lower = col.lower()
            if any(k in col_lower for k in ['sales', 'revenue', 'amount', 'total', 'price', 'quantity']):
                sales_col = col
                break
        if not sales_col:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if numeric_cols:
                sales_col = numeric_cols[0]

        if not sales_col:
            return None

        try:
            if date_col:
                temp_df = df[[date_col, sales_col]].dropna().copy()
                temp_df[date_col] = pd.to_datetime(temp_df[date_col], errors='coerce')
                temp_df = temp_df.dropna()
                if temp_df.empty:
                    raise ValueError("No valid date/sales pairs")
                
                date_min, date_max = temp_df[date_col].min(), temp_df[date_col].max()
                days_span = (date_max - date_min).days
                
                if days_span > 365 * 2:
                    freq = 'Q'
                elif days_span > 90:
                    freq = 'M'
                elif days_span > 15:
                    freq = 'W'
                else:
                    freq = 'D'
                
                grouped = temp_df.groupby(temp_df[date_col].dt.to_period(freq))[sales_col].sum()
                grouped = grouped.sort_index()
                
                hist_x = [str(p) for p in grouped.index]
                hist_y = grouped.values.tolist()
                
                last_period = grouped.index[-1]
                future_periods = [last_period + i for i in range(1, 7)]
                pred_x = [str(p) for p in future_periods]
            else:
                hist_y = df[sales_col].dropna().head(100).tolist()
                if len(hist_y) < 5:
                    return None
                hist_x = [f"Step {i+1}" for i in range(len(hist_y))]
                pred_x = [f"Step {len(hist_y) + i + 1}" for i in range(6)]

            N = len(hist_y)
            if N < 3:
                return None
                
            X_indices = np.arange(N)
            slope, intercept = np.polyfit(X_indices, hist_y, 1)
            
            future_indices = np.arange(N, N + 6)
            pred_y = (slope * future_indices + intercept).tolist()
            
            residuals = np.array(hist_y) - (slope * X_indices + intercept)
            std_err = np.std(residuals) if len(residuals) > 1 else np.mean(hist_y) * 0.15
            
            upper_y = [max(0.0, float(val + 1.64 * std_err)) for val in pred_y]
            lower_y = [max(0.0, float(val - 1.64 * std_err)) for val in pred_y]

            full_pred_x = [hist_x[-1]] + pred_x
            full_pred_y = [hist_y[-1]] + pred_y
            full_upper_y = [hist_y[-1]] + upper_y
            full_lower_y = [hist_y[-1]] + lower_y

            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=hist_x,
                y=hist_y,
                mode='lines+markers',
                name='Historical',
                line=dict(color='#1e6cf6', width=3),
                marker=dict(size=6)
            ))
            
            fig.add_trace(go.Scatter(
                x=full_pred_x,
                y=full_pred_y,
                mode='lines',
                name='Predicted (Trend)',
                line=dict(color='#ef4444', width=3, dash='dash')
            ))
            
            fig.add_trace(go.Scatter(
                x=full_pred_x,
                y=full_upper_y,
                mode='lines',
                line=dict(width=0),
                showlegend=False
            ))
            
            fig.add_trace(go.Scatter(
                x=full_pred_x,
                y=full_lower_y,
                mode='lines',
                name='90% Confidence Interval',
                fill='tonexty',
                fillcolor='rgba(239, 68, 68, 0.12)',
                line=dict(width=0),
                showlegend=True
            ))

            fig.update_layout(
                xaxis_title='Date Period' if date_col else 'Steps',
                yaxis_title=sales_col,
                hovermode='x unified'
            )
            
            fig_dict = fig.to_dict()
            
            forecast_summary = {
                'sales_col': sales_col,
                'last_historical_val': float(hist_y[-1]),
                'last_historical_period': str(hist_x[-1]),
                'predictions': [{'period': px, 'value': round(py, 2), 'lower': round(pl, 2), 'upper': round(pu, 2)}
                                for px, py, pl, pu in zip(pred_x, pred_y, lower_y, upper_y)]
            }
            
            return {
                'title': f'Future {sales_col} Forecast & Trend Prediction',
                'data': fig_dict['data'],
                'layout': fig_dict['layout'],
                'forecast_meta': forecast_summary
            }
            
        except Exception as ex:
            print(f"[DashboardAgent] Forecast failed: {ex}")
            return None


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