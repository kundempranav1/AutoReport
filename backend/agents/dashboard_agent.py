"""
Agent 4 — Dashboard Generation Agent.

Builds up to eight Plotly figures by inspecting the dataset:

    1. Bar Chart        — top categorical column vs numeric sum
    2. Line Chart       — first numeric column over row index
    3. Pie Chart        — low-cardinality categorical distribution
    4. Histogram        — numeric column distribution
    5. Scatter Plot     — correlation between first two numeric columns
    6. Box Plot         — statistical distribution of numeric columns
    7. Multi-Line Chart — compare multiple numeric columns over index
    8. Forecast Charts  — linear-regression trend for each numeric col (up to 5)

Each chart is returned as a JSON-serialisable dict that react-plotly.js
can render directly. Charts the dataset can't support are silently skipped.
"""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd
# pyrefly: ignore [missing-import]
import plotly.graph_objects as go


# Cohesive accent palette
PALETTE = ['#1e6cf6', '#3b82f6', '#60a5fa', '#93c5fd', '#0ea5e9', '#6366f1',
           '#22d3ee', '#a78bfa', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6']


class DashboardAgent:

    def run(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        if df is None or df.empty:
            return []

        charts: List[Dict[str, Any]] = []
        charts.append(self._bar_chart(df))
        charts.append(self._line_chart(df))
        charts.append(self._pie_chart(df))
        charts.append(self._histogram(df))
        charts.append(self._scatter_chart(df))
        charts.append(self._box_plot(df))
        charts.append(self._multi_line_chart(df))

        forecasts = self._sales_forecast_charts(df)
        if forecasts:
            charts.extend(forecasts)

        # Drop None entries (e.g. when the dataset can't support a chart).
        return [c for c in charts if c is not None]

    # ------------------------------------------------------------------
    # 1. Bar — sum of first numeric column grouped by best category
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
            fig = go.Figure(data=[
                go.Bar(
                    x=grouped.index.astype(str).tolist(),
                    y=grouped.values.tolist(),
                    marker=dict(
                        color=grouped.values.tolist(),
                        colorscale='Blues',
                        showscale=False,
                    ),
                    text=[f'{v:,.0f}' for v in grouped.values],
                    textposition='auto',
                )
            ])
            fig.update_layout(
                xaxis_title=cat_col, yaxis_title=num,
                bargap=0.25,
            )
            fig_dict = fig.to_dict()
            return {'title': f'Sum of {num} by {cat_col}', 'data': fig_dict['data'], 'layout': fig_dict['layout']}

        if cat_col and not numeric_cols:
            counts = df[cat_col].value_counts().head(15)
            fig = go.Figure(data=[
                go.Bar(
                    x=counts.index.astype(str).tolist(),
                    y=counts.values.tolist(),
                    marker_color=PALETTE[0],
                    text=counts.values.tolist(),
                    textposition='auto',
                )
            ])
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
        fig = go.Figure(data=[
            go.Scatter(
                x=x, y=y,
                mode='lines+markers',
                line=dict(color=PALETTE[1], width=2),
                marker=dict(size=4),
                fill='tozeroy',
                fillcolor='rgba(59, 130, 246, 0.08)',
            )
        ])
        fig.update_layout(xaxis_title='Index', yaxis_title=num)
        fig_dict = fig.to_dict()
        return {'title': f'{num} Trend over Index', 'data': fig_dict['data'], 'layout': fig_dict['layout']}

    # ------------------------------------------------------------------
    # 3. Pie — counts of a low-cardinality category
    # ------------------------------------------------------------------
    def _pie_chart(self, df: pd.DataFrame) -> Dict[str, Any] | None:
        cat_col = _best_categorical(df, max_unique=8)
        if not cat_col:
            return None
        counts = df[cat_col].value_counts().head(8)
        fig = go.Figure(data=[
            go.Pie(
                labels=counts.index.astype(str).tolist(),
                values=counts.values.tolist(),
                marker=dict(colors=PALETTE),
                hole=0.35,
                textinfo='label+percent',
            )
        ])
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
        fig = go.Figure(data=[
            go.Histogram(
                x=df[num].dropna().tolist(),
                marker=dict(
                    color=PALETTE[2],
                    line=dict(color='white', width=0.5),
                ),
                nbinsx=30,
                opacity=0.85,
            )
        ])
        fig.update_layout(xaxis_title=num, yaxis_title='Frequency', bargap=0.05)
        fig_dict = fig.to_dict()
        return {'title': f'Frequency Distribution of {num}', 'data': fig_dict['data'], 'layout': fig_dict['layout']}

    # ------------------------------------------------------------------
    # 5. Scatter Plot — correlation between first two numeric columns
    # ------------------------------------------------------------------
    def _scatter_chart(self, df: pd.DataFrame) -> Dict[str, Any] | None:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) < 2:
            return None

        x_col, y_col = numeric_cols[0], numeric_cols[1]
        temp = df[[x_col, y_col]].dropna().head(500)
        if len(temp) < 5:
            return None

        # Optional: color by categorical column
        cat_col = _best_categorical(df, max_unique=8)
        if cat_col:
            cats = df[cat_col].astype(str).tolist()[:len(temp)]
            unique_cats = list(dict.fromkeys(cats))
            color_map = {c: PALETTE[i % len(PALETTE)] for i, c in enumerate(unique_cats)}
            colors = [color_map[c] for c in cats]
        else:
            colors = PALETTE[0]

        # Compute trendline
        x_arr = temp[x_col].values
        y_arr = temp[y_col].values
        slope, intercept = np.polyfit(x_arr, y_arr, 1)
        trend_x = [float(x_arr.min()), float(x_arr.max())]
        trend_y = [slope * v + intercept for v in trend_x]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=temp[x_col].tolist(),
            y=temp[y_col].tolist(),
            mode='markers',
            marker=dict(
                color=colors,
                size=7,
                opacity=0.7,
                line=dict(color='white', width=0.5),
            ),
            name='Data Points',
        ))
        fig.add_trace(go.Scatter(
            x=trend_x,
            y=trend_y,
            mode='lines',
            line=dict(color='#ef4444', width=2, dash='dot'),
            name='Trend Line',
        ))
        fig.update_layout(xaxis_title=x_col, yaxis_title=y_col)
        fig_dict = fig.to_dict()
        return {
            'title': f'Correlation: {x_col} vs {y_col}',
            'data': fig_dict['data'],
            'layout': fig_dict['layout'],
        }

    # ------------------------------------------------------------------
    # 6. Box Plot — statistical distribution of numeric columns
    # ------------------------------------------------------------------
    def _box_plot(self, df: pd.DataFrame) -> Dict[str, Any] | None:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if not numeric_cols:
            return None

        cols_to_plot = numeric_cols[:6]  # cap at 6 columns
        fig = go.Figure()
        for i, col in enumerate(cols_to_plot):
            data = df[col].dropna().tolist()
            if not data:
                continue
            fig.add_trace(go.Box(
                y=data,
                name=col,
                marker_color=PALETTE[i % len(PALETTE)],
                boxmean='sd',
                jitter=0.3,
                pointpos=-1.8,
                boxpoints='outliers',
            ))
        fig.update_layout(yaxis_title='Value', showlegend=False)
        fig_dict = fig.to_dict()
        return {
            'title': 'Statistical Distribution (Box Plot)',
            'data': fig_dict['data'],
            'layout': fig_dict['layout'],
        }

    # ------------------------------------------------------------------
    # 7. Multi-Line Chart — compare multiple numeric columns over index
    # ------------------------------------------------------------------
    def _multi_line_chart(self, df: pd.DataFrame) -> Dict[str, Any] | None:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) < 2:
            return None

        cols_to_plot = numeric_cols[:5]  # cap at 5 columns
        max_rows = 200
        fig = go.Figure()

        for i, col in enumerate(cols_to_plot):
            series = df[col].dropna().head(max_rows)
            if series.empty:
                continue
            # Normalise to 0-100 scale so different-magnitude columns are comparable
            col_min, col_max = series.min(), series.max()
            if col_max != col_min:
                normalised = ((series - col_min) / (col_max - col_min) * 100).tolist()
            else:
                normalised = [50.0] * len(series)

            fig.add_trace(go.Scatter(
                x=list(range(len(normalised))),
                y=normalised,
                mode='lines',
                name=col,
                line=dict(color=PALETTE[i % len(PALETTE)], width=2),
            ))

        fig.update_layout(
            xaxis_title='Index',
            yaxis_title='Normalised Value (0–100)',
            legend=dict(orientation='h', y=-0.2),
            hovermode='x unified',
        )
        fig_dict = fig.to_dict()
        return {
            'title': 'Multi-Column Trend Comparison (Normalised)',
            'data': fig_dict['data'],
            'layout': fig_dict['layout'],
        }

    # ------------------------------------------------------------------
    # 8. Future Trend Forecasts for all numeric columns (up to 5)
    # ------------------------------------------------------------------
    def _sales_forecast_charts(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Generate forecast charts for every numeric column (up to 5).

        Works on ANY dataset:
        • Prioritises columns whose names suggest revenue/sales/profit.
        • Falls back to any numeric column.
        • Uses a date column if found; otherwise uses row-index labels.
        • Requires at least 4 non-null data points per column.
        """

        # ── 1. Detect best date / time column ───────────────────────────
        date_col: str | None = None
        for col in df.columns:
            if df[col].dtype.name.startswith('datetime'):
                date_col = col
                break
        if not date_col:
            for col in df.columns:
                kw = col.lower()
                if any(k in kw for k in ['date', 'time', 'year', 'month',
                                          'timestamp', 'created', 'period']):
                    try:
                        pd.to_datetime(df[col].dropna().head(10), errors='raise')
                        date_col = col
                        break
                    except Exception:
                        continue

        # ── 2. Collect numeric columns — sales-like ones first ───────────
        SALES_KW = ['sale', 'revenue', 'income', 'profit', 'turnover',
                    'amount', 'price', 'cost', 'total', 'earning', 'gross',
                    'net', 'value', 'order', 'billing']

        all_num = df.select_dtypes(include=[np.number]).columns.tolist()
        if not all_num:
            return []

        sales_cols = [c for c in all_num
                      if any(kw in c.lower() for kw in SALES_KW)]
        other_cols = [c for c in all_num if c not in sales_cols]
        ordered_cols = (sales_cols + other_cols)[:5]   # cap at 5

        # ── 3. Helper: build (hist_x, hist_y, pred_x) for one column ────
        def _next_periods(last_period, n: int):
            """Return n period strings after last_period using the period's frequency."""
            results = []
            cur = last_period
            for _ in range(n):
                cur = cur + 1   # pandas Period supports + integer
                results.append(str(cur))
            return results

        def build_series(col: str):
            if date_col:
                tmp = df[[date_col, col]].dropna().copy()
                tmp[date_col] = pd.to_datetime(tmp[date_col], errors='coerce')
                tmp = tmp.dropna()
                if len(tmp) < 4:
                    return None

                span_days = (tmp[date_col].max() - tmp[date_col].min()).days
                if span_days > 365 * 2:
                    freq = 'Q'
                elif span_days > 90:
                    freq = 'ME'   # pandas >=2.2 uses ME instead of M
                elif span_days > 15:
                    freq = 'W'
                else:
                    freq = 'D'

                try:
                    grp = (tmp.groupby(tmp[date_col].dt.to_period(freq))[col]
                              .sum().sort_index())
                except Exception:
                    # fallback: try without grouping
                    grp = None

                if grp is None or len(grp) < 4:
                    # Fallback: just use the raw series ordered by date
                    tmp_sorted = tmp.sort_values(date_col)
                    hy = tmp_sorted[col].tolist()
                    hx = [str(d)[:10] for d in tmp_sorted[date_col].tolist()]
                    if len(hy) > 100:
                        hy, hx = hy[-100:], hx[-100:]
                    N_idx = len(hx)
                    px = [f'Future +{j}' for j in range(1, 7)]
                else:
                    hx = [str(p) for p in grp.index]
                    hy = grp.values.tolist()
                    last_p = grp.index[-1]
                    try:
                        px = _next_periods(last_p, 6)
                    except Exception:
                        px = [f'Future +{j}' for j in range(1, 7)]
            else:
                hy = df[col].dropna().head(100).tolist()
                if len(hy) < 4:
                    return None
                hx = [f'Row {i+1}' for i in range(len(hy))]
                px = [f'Row {len(hy)+j+1}' for j in range(6)]

            if len(hy) < 4:
                return None
            return hx, hy, px

        # ── 4. Build one forecast chart per column ───────────────────────
        forecast_charts: List[Dict[str, Any]] = []

        for sales_col in ordered_cols:
            try:
                result = build_series(sales_col)
                if result is None:
                    continue
                hist_x, hist_y, pred_x_raw = result

                N = len(hist_y)
                X_idx = np.arange(N, dtype=float)
                slope, intercept = np.polyfit(X_idx, hist_y, 1)

                future_idx = np.arange(N, N + 6, dtype=float)
                pred_y = (slope * future_idx + intercept).tolist()

                residuals = np.array(hist_y) - (slope * X_idx + intercept)
                std_err = float(np.std(residuals)) if N > 2 else float(np.mean(np.abs(hist_y))) * 0.15
                std_err = max(std_err, 0.01)   # avoid zero CI

                upper_y = [round(max(0.0, v + 1.64 * std_err), 4) for v in pred_y]
                lower_y = [round(max(0.0, v - 1.64 * std_err), 4) for v in pred_y]
                pred_y  = [round(v, 4) for v in pred_y]

                # Connector point (last historical → first predicted)
                cx = [hist_x[-1]] + pred_x_raw
                cy = [hist_y[-1]] + pred_y
                cu = [hist_y[-1]] + upper_y
                cl = [hist_y[-1]] + lower_y

                is_sales = any(kw in sales_col.lower() for kw in SALES_KW)
                pred_color = '#ef4444' if is_sales else '#f59e0b'
                fill_color = ('rgba(239,68,68,0.12)' if is_sales
                              else 'rgba(245,158,11,0.12)')

                direction = 'Upward' if slope > 0 else 'Downward'
                badge_label = (f'📈 {direction} Trend' if slope > 0
                               else f'📉 {direction} Trend')

                fig = go.Figure()

                # Historical area + line
                fig.add_trace(go.Scatter(
                    x=hist_x, y=hist_y,
                    mode='lines+markers',
                    name='Historical Data',
                    line=dict(color='#1e6cf6', width=3),
                    marker=dict(size=6, color='#1e6cf6',
                                line=dict(color='white', width=1.5)),
                    fill='tozeroy',
                    fillcolor='rgba(30,108,246,0.07)',
                ))

                # Upper CI (invisible, just for fill reference)
                fig.add_trace(go.Scatter(
                    x=cx, y=cu,
                    mode='lines',
                    line=dict(width=0),
                    showlegend=False,
                    hoverinfo='skip',
                ))

                # Lower CI with fill between upper and lower
                fig.add_trace(go.Scatter(
                    x=cx, y=cl,
                    mode='lines',
                    name='90% Confidence Band',
                    fill='tonexty',
                    fillcolor=fill_color,
                    line=dict(width=0),
                    hoverinfo='skip',
                ))

                # Predicted trend line
                fig.add_trace(go.Scatter(
                    x=cx, y=cy,
                    mode='lines+markers',
                    name='Forecast (Trend)',
                    line=dict(color=pred_color, width=3, dash='dash'),
                    marker=dict(size=7, symbol='diamond',
                                color=pred_color,
                                line=dict(color='white', width=1.5)),
                    customdata=list(zip(upper_y, lower_y)),
                    hovertemplate=(
                        '<b>%{x}</b><br>'
                        f'{sales_col}: %{{y:,.2f}}<br>'
                        'Upper: %{customdata[0]:,.2f}<br>'
                        'Lower: %{customdata[1]:,.2f}<extra></extra>'
                    ),
                ))

                # Vertical divider only works on numeric/date axes
                if date_col and hist_x:
                    try:
                        fig.add_vline(
                            x=hist_x[-1],
                            line_dash='dot',
                            line_color='#9ca3af',
                            line_width=1.5,
                            annotation_text='Forecast \u2192',
                            annotation_position='top right',
                            annotation_font_size=11,
                            annotation_font_color='#6b7280',
                        )
                    except Exception:
                        pass  # vline not supported for categorical axes

                x_label = 'Date Period' if date_col else 'Data Point'
                fig.update_layout(
                    xaxis_title=x_label,
                    yaxis_title=sales_col,
                    hovermode='x unified',
                    legend=dict(orientation='h', y=-0.28,
                                x=0, font=dict(size=11)),
                    yaxis=dict(tickformat=',.0f'),
                    margin=dict(l=60, r=20, t=30, b=80),
                )
                fig_dict = fig.to_dict()

                is_sales_title = any(kw in sales_col.lower() for kw in SALES_KW)
                title = (f'Sales Forecast: Future {sales_col} Trend'
                         if is_sales_title
                         else f'Future {sales_col} Forecast & Trend')

                forecast_summary = {
                    'sales_col': sales_col,
                    'is_sales': is_sales_title,
                    'trend_direction': direction,
                    'slope': round(slope, 4),
                    'last_historical_val': round(float(hist_y[-1]), 2),
                    'last_historical_period': str(hist_x[-1]),
                    'predictions': [
                        {'period': px, 'value': py,
                         'lower': pl, 'upper': pu}
                        for px, py, pl, pu in zip(
                            pred_x_raw, pred_y, lower_y, upper_y)
                    ],
                }

                forecast_charts.append({
                    'title': title,
                    'badge': badge_label,
                    'data': fig_dict['data'],
                    'layout': fig_dict['layout'],
                    'forecast_meta': forecast_summary,
                })

            except Exception as ex:
                print(f'[DashboardAgent] Forecast failed for {sales_col}: {ex}')

        return forecast_charts


# ----------------------------------------------------------------------
def _best_categorical(df: pd.DataFrame, max_unique: int) -> str | None:
    """Return the best categorical column within the cardinality bound."""
    cat_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()
    if not cat_cols:
        return None
    for col in cat_cols:
        n = df[col].nunique(dropna=True)
        if 1 < n <= max_unique:
            return col
    return cat_cols[0]