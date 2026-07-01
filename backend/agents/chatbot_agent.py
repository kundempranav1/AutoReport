"""
Agent 6 — Chatbot Agent.

Two-tier answer strategy:
    1. LOCAL ENGINE  — answers common dataset questions instantly using pandas.
       Works with zero API credits. Handles: avg/mean, sum/total, max/min,
       row/column counts, missing values, unique values, top/most common,
       correlation, and column listing.
    2. OPENAI FALLBACK — used only for complex/free-form questions when an
       API key is available and has quota.

A simple in-memory cache keyed by `file_id` stores the primed agent so we
don't rebuild the summary on every chat request.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


# ----------------------------------------------------------------------
class ChatbotAgent:
    """Dataset-specific chatbot with local analytics + optional OpenAI."""

    # Per-process cache: file_id -> ChatbotAgent instance
    _CACHE: Dict[str, "ChatbotAgent"] = {}

    # ------------------------------------------------------------------
    def __init__(self, api_key: str = "", model: str = "gpt-3.5-turbo"):
        self.api_key = api_key
        self.model = model
        self.summary: str = ""
        self.dataset_columns: list[str] = []
        self.row_count: int = 0
        self.col_count: int = 0
        # Store numeric & categorical stats for local engine
        self._num_stats: Dict[str, Dict[str, float]] = {}   # col -> {mean,sum,min,max,std,count}
        self._cat_stats: Dict[str, Dict[str, Any]]  = {}   # col -> {unique, top, freq}
        self._missing: Dict[str, int] = {}
        self._dtypes: Dict[str, str] = {}
        self.forecast_meta: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------
    @classmethod
    def cache_get(cls, file_id: str) -> Optional["ChatbotAgent"]:
        return cls._CACHE.get(file_id)

    @classmethod
    def cache_set(cls, file_id: str, agent: "ChatbotAgent") -> None:
        cls._CACHE[file_id] = agent

    # ------------------------------------------------------------------
    def prime(self, df: pd.DataFrame, forecast_meta: Optional[Dict[str, Any]] = None) -> None:
        """Pre-compute stats from the DataFrame for instant local answers."""
        self.forecast_meta = forecast_meta
        if df is None or df.empty:
            self.summary = "The dataset is empty."
            return

        self.dataset_columns = df.columns.tolist()
        self.row_count = int(len(df))
        self.col_count = int(len(df.columns))

        # Missing values
        self._missing = {c: int(df[c].isna().sum()) for c in df.columns}
        self._dtypes  = {c: str(df[c].dtype) for c in df.columns}

        # Numeric stats
        for col in df.select_dtypes(include=[np.number]).columns:
            s = df[col].dropna()
            if s.empty:
                continue
            self._num_stats[col] = {
                "mean":  round(float(s.mean()),  4),
                "sum":   round(float(s.sum()),   4),
                "min":   round(float(s.min()),   4),
                "max":   round(float(s.max()),   4),
                "std":   round(float(s.std()),   4),
                "count": int(len(s)),
                "median": round(float(s.median()), 4),
            }

        # Categorical stats
        for col in df.select_dtypes(exclude=[np.number]).columns:
            s = df[col].dropna()
            top_series = s.mode()
            top_val = str(top_series.iloc[0]) if not top_series.empty else "—"
            freq = int((s == top_series.iloc[0]).sum()) if not top_series.empty else 0
            vc = s.value_counts().head(5).to_dict()
            self._cat_stats[col] = {
                "unique": int(s.nunique()),
                "top":    top_val,
                "freq":   freq,
                "top5":   {str(k): int(v) for k, v in vc.items()},
            }

        # Build text summary for OpenAI fallback
        parts: list[str] = [
            f"Dataset: {self.row_count} rows × {self.col_count} columns.",
            f"Columns: {', '.join(self.dataset_columns)}.",
        ]
        for col, st in self._num_stats.items():
            parts.append(
                f" - {col} (numeric): mean={st['mean']}, sum={st['sum']}, "
                f"min={st['min']}, max={st['max']}, std={st['std']}."
            )
        for col, st in self._cat_stats.items():
            parts.append(
                f" - {col} (categorical): {st['unique']} unique, "
                f"most common='{st['top']}' ({st['freq']} times)."
            )
        missing_cols = [c for c, n in self._missing.items() if n > 0]
        if missing_cols:
            parts.append("Missing values in: " +
                         ", ".join(f"{c}={self._missing[c]}" for c in missing_cols) + ".")
        else:
            parts.append("No missing values.")

        # First 5 rows sample
        sample = df.head(5).fillna("").to_dict(orient="records")
        parts.append("Sample rows:")
        for i, row in enumerate(sample, 1):
            row_str = ", ".join(f"{k}={v}" for k, v in row.items())
            if len(row_str) > 400:
                row_str = row_str[:400] + "..."
            parts.append(f"  {i}. {row_str}")

        # Add predictive forecast metadata to context if present
        if self.forecast_meta:
            parts.append("\nPREDICTIVE FORECASTING DATA:")
            parts.append(f"Historical trend extrapolation for column: {self.forecast_meta['sales_col']}")
            parts.append(f"Last observed actual value: {self.forecast_meta['last_historical_val']} (Period: {self.forecast_meta['last_historical_period']})")
            parts.append("Future sales forecasts:")
            for p in self.forecast_meta['predictions']:
                parts.append(f"  - Period {p['period']}: Projected={p['value']} (range: {p['lower']} to {p['upper']})")

        self.summary = "\n".join(parts)

    # ------------------------------------------------------------------
    def ask(self, question: str) -> str:
        """Answer a question — tries local engine first, then OpenAI."""
        if not self.dataset_columns:
            return "No dataset loaded yet. Please upload and process a dataset first."

        # --- 1. Try local analytics engine first ----------------------
        local = self._local_answer(question)
        if local is not None:
            return local

        # --- 2. Fall back to OpenAI if key available ------------------
        if not self.api_key:
            return self._summarise_from_context(question)

        return self._openai_answer(question)

    # ------------------------------------------------------------------
    # LOCAL ANALYTICS ENGINE
    # ------------------------------------------------------------------
    def _local_answer(self, question: str) -> Optional[str]:
        """
        Pattern-match common dataset questions and answer them from the
        pre-computed stats. Returns None if the question is not recognised.
        """
        q = question.lower().strip()

        # --- Future Forecast / Predictions (NEW) -----------------------
        if re.search(r'\b(forecast|predict|prediction|future|project|projection)\b', q):
            if self.forecast_meta:
                meta = self.forecast_meta
                lines = [
                    f"🔮 **AutoReport AI Forecasting Summary for {meta['sales_col']}:**",
                    f"Last actual observed value: **{meta['last_historical_val']:,}** (Period: {meta['last_historical_period']})",
                    "",
                    "**Projected values (next 6 periods):**"
                ]
                for p in meta['predictions']:
                    lines.append(f"  • **{p['period']}**: {p['value']:,} *(range: {p['lower']:,} to {p['upper']:,})*")
                return "\n".join(lines)
            else:
                return "I don't have enough historic time-series data or numerical values to generate a reliable future forecast for this dataset."

        # --- Row / column counts --------------------------------------
        if re.search(r'\b(how many|total|number of)\b.*\brow', q) or q in ("rows?", "row count"):
            return f"The dataset has **{self.row_count:,} rows**."

        if re.search(r'\b(how many|total|number of)\b.*\bcolumn', q) or "column count" in q:
            return f"The dataset has **{self.col_count} columns**: {', '.join(self.dataset_columns)}."

        # --- List columns ---------------------------------------------
        if re.search(r'\b(list|show|what are|what)\b.*\bcolumn', q) or q == "columns":
            return f"**Columns ({self.col_count}):** {', '.join(self.dataset_columns)}."

        # --- Missing values -------------------------------------------
        if re.search(r'\bmissing\b|\bnull\b|\bnan\b|\bna\b', q):
            col = self._find_column(q)
            if col:
                n = self._missing.get(col, 0)
                pct = round(100 * n / self.row_count, 2) if self.row_count else 0
                return f"Column **{col}** has **{n} missing values** ({pct}% of rows)."
            total_missing = sum(self._missing.values())
            if total_missing == 0:
                return "✅ The dataset has **no missing values**."
            lines = [f"**Total missing values: {total_missing}**"]
            for c, n in self._missing.items():
                if n > 0:
                    lines.append(f"  • {c}: {n} ({round(100*n/self.row_count,1)}%)")
            return "\n".join(lines)

        # --- Average / mean -------------------------------------------
        if re.search(r'\b(average|mean|avg)\b', q):
            col = self._find_numeric_column(q)
            if col:
                st = self._num_stats[col]
                return f"The **average (mean) of {col}** is **{st['mean']:,}**."
            # List all averages
            if self._num_stats:
                lines = ["**Averages for all numeric columns:**"]
                for c, st in self._num_stats.items():
                    lines.append(f"  • {c}: {st['mean']:,}")
                return "\n".join(lines)

        # --- Median ---------------------------------------------------
        if re.search(r'\bmedian\b', q):
            col = self._find_numeric_column(q)
            if col:
                return f"The **median of {col}** is **{self._num_stats[col]['median']:,}**."

        # --- Sum / total ----------------------------------------------
        if re.search(r'\b(sum|total)\b', q) and not re.search(r'\brow\b|\bcolumn\b', q):
            col = self._find_numeric_column(q)
            if col:
                st = self._num_stats[col]
                return f"The **total (sum) of {col}** is **{st['sum']:,}**."
            if self._num_stats:
                lines = ["**Sums for all numeric columns:**"]
                for c, st in self._num_stats.items():
                    lines.append(f"  • {c}: {st['sum']:,}")
                return "\n".join(lines)

        # --- Maximum --------------------------------------------------
        if re.search(r'\b(max|maximum|highest|largest|biggest)\b', q):
            col = self._find_numeric_column(q)
            if col:
                return f"The **maximum of {col}** is **{self._num_stats[col]['max']:,}**."

        # --- Minimum --------------------------------------------------
        if re.search(r'\b(min|minimum|lowest|smallest)\b', q):
            col = self._find_numeric_column(q)
            if col:
                return f"The **minimum of {col}** is **{self._num_stats[col]['min']:,}**."

        # --- Standard deviation ---------------------------------------
        if re.search(r'\b(std|standard deviation|variance)\b', q):
            col = self._find_numeric_column(q)
            if col:
                return f"The **standard deviation of {col}** is **{self._num_stats[col]['std']:,}**."

        # --- Most common / top / frequent -----------------------------
        if re.search(r'\b(most common|top|frequent|popular|mode)\b', q):
            col = self._find_categorical_column(q) or self._find_column(q)
            if col and col in self._cat_stats:
                st = self._cat_stats[col]
                top5 = "\n".join(f"  {i+1}. {k}: {v} times"
                                 for i, (k, v) in enumerate(st['top5'].items()))
                return (f"**Most common values in {col}:**\n{top5}\n"
                        f"*(most frequent: '{st['top']}' — {st['freq']} occurrences)*")
            if self._cat_stats:
                col = next(iter(self._cat_stats))
                st = self._cat_stats[col]
                return f"Most common value in **{col}** is **'{st['top']}'** ({st['freq']} times)."

        # --- Unique values --------------------------------------------
        if re.search(r'\b(unique|distinct|different)\b', q):
            col = self._find_column(q)
            if col and col in self._cat_stats:
                return f"Column **{col}** has **{self._cat_stats[col]['unique']} unique values**."
            if col and col in self._num_stats:
                return f"Column **{col}** is numeric with {self._num_stats[col]['count']} non-null values."

        # --- Generic column stats ------------------------------------
        if re.search(r'\b(stat|describe|summary|info|about)\b', q):
            col = self._find_column(q)
            if col:
                return self._col_summary(col)
            # Full dataset summary
            lines = [f"**Dataset: {self.row_count:,} rows × {self.col_count} columns**"]
            for c, st in self._num_stats.items():
                lines.append(f"  • {c}: mean={st['mean']}, min={st['min']}, max={st['max']}")
            for c, st in self._cat_stats.items():
                lines.append(f"  • {c}: {st['unique']} unique, top='{st['top']}'")
            return "\n".join(lines)

        # --- Direct column name mention -------------------------------
        col = self._find_column(q)
        if col:
            return self._col_summary(col)

        return None  # Not handled locally

    # ------------------------------------------------------------------
    def _col_summary(self, col: str) -> str:
        if col in self._num_stats:
            st = self._num_stats[col]
            return (
                f"**{col}** (numeric, {self._dtypes.get(col, 'number')}):\n"
                f"  • Mean: {st['mean']:,}\n"
                f"  • Sum: {st['sum']:,}\n"
                f"  • Min: {st['min']:,}  |  Max: {st['max']:,}\n"
                f"  • Std Dev: {st['std']:,}\n"
                f"  • Missing: {self._missing.get(col, 0)}"
            )
        if col in self._cat_stats:
            st = self._cat_stats[col]
            top5 = ", ".join(f"{k}({v})" for k, v in list(st['top5'].items())[:5])
            return (
                f"**{col}** (categorical, {self._dtypes.get(col, 'object')}):\n"
                f"  • Unique values: {st['unique']}\n"
                f"  • Most common: '{st['top']}' ({st['freq']} times)\n"
                f"  • Top 5: {top5}\n"
                f"  • Missing: {self._missing.get(col, 0)}"
            )
        return f"Column **{col}** found in dataset (type: {self._dtypes.get(col, 'unknown')})."

    # ------------------------------------------------------------------
    def _find_column(self, q: str) -> Optional[str]:
        """Find a column name mentioned in the question (case-insensitive)."""
        q_lower = q.lower()
        # Exact match first
        for col in self.dataset_columns:
            if col.lower() in q_lower:
                return col
        # Partial/fuzzy match
        for col in self.dataset_columns:
            words = col.lower().split()
            if any(w in q_lower for w in words if len(w) > 2):
                return col
        return None

    def _find_numeric_column(self, q: str) -> Optional[str]:
        col = self._find_column(q)
        if col and col in self._num_stats:
            return col
        if self._num_stats:
            return next(iter(self._num_stats))
        return None

    def _find_categorical_column(self, q: str) -> Optional[str]:
        col = self._find_column(q)
        if col and col in self._cat_stats:
            return col
        return None

    # ------------------------------------------------------------------
    def _summarise_from_context(self, question: str) -> str:
        """Answer from summary text when OpenAI is unavailable."""
        return (
            "🤖 **Local answer** (OpenAI unavailable — quota exceeded or no API key):\n\n"
            f"Here is what I know about your dataset:\n\n{self.summary}\n\n"
            "💡 *Tip: Ask about specific columns, averages, totals, max, min, "
            "missing values, or unique counts — I can answer those instantly!*"
        )

    # ------------------------------------------------------------------
    def _openai_answer(self, question: str) -> str:
        """Use OpenAI LLM for complex questions."""
        try:
            # pyrefly: ignore [missing-import]
            from langchain_openai import ChatOpenAI
            # pyrefly: ignore [missing-import]
            from langchain_core.prompts import ChatPromptTemplate
        except Exception as e:
            return f"LangChain / OpenAI libraries are unavailable: {e}"

        system_prompt = (
            "You are a dataset assistant for the AutoReport AI app.\n"
            "Answer ONLY using the dataset context below. "
            "If a question cannot be answered from the data, say so.\n"
            "Be concise and use plain English.\n\n"
            "DATASET CONTEXT:\n"
            f"{self.summary}"
        )

        try:
            llm = ChatOpenAI(model=self.model, api_key=self.api_key, temperature=0.0)
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{question}"),
            ])
            chain = prompt | llm
            response = chain.invoke({"question": question})
            return response.content if hasattr(response, "content") else str(response)

        except Exception as e:
            msg = str(e)
            if "api_key" in msg.lower() or "incorrect api key" in msg.lower():
                return "❌ The configured OpenAI API key is invalid or missing."
            if "rate limit" in msg.lower():
                return "⏳ OpenAI rate limit reached. Please try again shortly."
            if "insufficient_quota" in msg or "quota" in msg.lower():
                # Quota exceeded — fall back to local summary
                local = self._local_answer(question)
                if local:
                    return f"*(OpenAI quota exceeded — answered locally)*\n\n{local}"
                return (
                    "⚠️ **OpenAI quota exceeded.** Your API key has no credits.\n\n"
                    "You can still ask me about: averages, totals, min/max, "
                    "missing values, unique counts, and top categories — "
                    "those are answered instantly without OpenAI!"
                )
            if "model" in msg.lower() and "not found" in msg.lower():
                return f"❌ Model '{self.model}' not found. Check OPENAI_MODEL in .env."
            return f"Chatbot error: {msg}"