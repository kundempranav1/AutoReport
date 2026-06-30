"""
Agent 1 — Data Cleaning Agent.

Takes a raw DataFrame and returns a cleaned one:

    * Detect & fill missing values
        - numeric  → column mean
        - categorical → column mode
    * Remove duplicate rows
    * Remove empty rows
    * Coerce dtypes (numeric / datetime where possible)
"""
from __future__ import annotations

import pandas as pd


class DataCleaningAgent:
    """Stateless cleaning helper — one public method: `run(df)`."""

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return df

        df = df.copy()

        # --- 1. Strip whitespace from string columns ---------------------
        for col in df.select_dtypes(include='object').columns:
            df[col] = df[col].apply(
                lambda v: v.strip() if isinstance(v, str) else v
            )

        # --- 2. Remove fully empty rows -----------------------------------
        df.dropna(how='all', inplace=True)

        # --- 3. Remove duplicates -----------------------------------------
        df.drop_duplicates(inplace=True)

        # --- 4. Type coercion ---------------------------------------------
        df = self._coerce_types(df)

        # --- 5. Fill missing values ---------------------------------------
        df = self._fill_missing(df)

        # --- 6. Reset index -----------------------------------------------
        df.reset_index(drop=True, inplace=True)
        return df

    # ------------------------------------------------------------------
    def _coerce_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Best-effort conversion: numeric where possible, then datetime."""
        for col in df.columns:
            # Skip columns that are entirely empty.
            if df[col].dropna().empty:
                continue

            # Numeric coercion.
            converted = pd.to_numeric(df[col], errors='coerce')
            # If we kept at least half the non-null values, keep numeric.
            if converted.notna().sum() >= 0.5 * df[col].notna().sum():
                df[col] = converted
                continue

            # Datetime coercion (only attempt on string columns).
            if df[col].dtype == 'object':
                try:
                    parsed = pd.to_datetime(df[col], errors='coerce', utc=False)
                    if parsed.notna().sum() >= 0.5 * df[col].notna().sum():
                        df[col] = parsed
                except Exception:
                    pass

        return df

    # ------------------------------------------------------------------
    def _fill_missing(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fill numeric NaNs with mean and categorical NaNs with mode."""
        for col in df.columns:
            if not df[col].isna().any():
                continue

            if pd.api.types.is_numeric_dtype(df[col]):
                mean_val = df[col].mean()
                df[col] = df[col].fillna(mean_val)
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                # Leave datetime NaTs alone — there's no sensible default.
                continue
            else:
                mode_series = df[col].mode(dropna=True)
                fill = mode_series.iloc[0] if not mode_series.empty else 'Unknown'
                df[col] = df[col].fillna(fill)

        return df