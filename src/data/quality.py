from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd


MISSING_TOKENS = {"", " ", "na", "n/a", "null", "none", "nan", "-"}

# Padroes de dominio comuns em dados brasileiros
_PATTERNS: dict[str, re.Pattern[str]] = {
    "email":    re.compile(r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$", re.I),
    "cpf":      re.compile(r"^\d{3}[\.\-]?\d{3}[\.\-]?\d{3}[\-]?\d{2}$"),
    "cep":      re.compile(r"^\d{5}[\-]?\d{3}$"),
    "telefone": re.compile(r"^(\+?55\s?)?(\(?\d{2}\)?[\s\-]?)(\d{4,5}[\-\s]?\d{4})$"),
    "url":      re.compile(r"^https?://[^\s]+$", re.I),
}


def _safe_percent(part: float, total: float) -> float:
    if total <= 0:
        return 0.0
    return round((part / total) * 100.0, 2)


def _numeric_like_ratio(series: pd.Series) -> float:
    as_str = series.dropna().astype(str).str.strip()
    if as_str.empty:
        return 0.0
    converted = pd.to_numeric(as_str, errors="coerce")
    return float(converted.notna().mean())


def _datetime_like_ratio(series: pd.Series) -> float:
    as_str = series.dropna().astype(str).str.strip()
    if as_str.empty:
        return 0.0
    converted = pd.to_datetime(as_str, errors="coerce", format="mixed")
    return float(converted.notna().mean())


def _detect_patterns(df: pd.DataFrame, rows: int) -> pd.DataFrame:
    """Detecta padroes semanticos (email, CPF, CEP, telefone, URL) em colunas texto."""
    result_rows: list[dict[str, Any]] = []
    object_cols = df.select_dtypes(include=["object", "string"]).columns.tolist()
    for col in object_cols:
        sample = df[col].dropna().astype(str).str.strip()
        if sample.empty:
            continue
        for pattern_name, regex in _PATTERNS.items():
            matches = sample.apply(lambda v: bool(regex.fullmatch(v)))
            match_pct = float(matches.mean()) * 100.0
            if match_pct >= 60.0:  # pelo menos 60% dos valores conformes
                result_rows.append(
                    {
                        "column": col,
                        "pattern": pattern_name,
                        "match_pct": round(match_pct, 1),
                        "sample": str(sample.iloc[0]) if len(sample) > 0 else "",
                    }
                )
                break  # um padrao por coluna e suficiente
    return pd.DataFrame(result_rows)


def _outliers_zscore(series: pd.Series, threshold: float = 3.0) -> int:
    """Conta outliers pelo metodo Z-score (|z| > threshold)."""
    if series.empty or series.std() == 0:
        return 0
    z = (series - series.mean()) / series.std()
    return int((z.abs() > threshold).sum())


def analyze_dataset(df: pd.DataFrame) -> dict[str, Any]:
    if df is None or df.shape[0] == 0 or df.shape[1] == 0:
        empty_summary: dict[str, Any] = {
            "rows": 0,
            "columns": 0,
            "missing_cells": 0,
            "missing_cells_pct": 0.0,
            "duplicate_rows": 0,
            "duplicate_rows_pct": 0.0,
            "memory_mb": 0.0,
            "constant_columns_count": 0,
        }
        return {
            "error": "DataFrame vazio ou sem colunas validas.",
            "summary": empty_summary,
            "column_profile": pd.DataFrame(),
            "missing_table": pd.DataFrame(),
            "placeholder_table": pd.DataFrame(),
            "type_suggestions": pd.DataFrame(),
            "outlier_table": pd.DataFrame(),
            "pattern_table": pd.DataFrame(),
            "constant_columns": [],
        }

    rows, cols = df.shape
    total_cells = max(rows * cols, 1)

    missing_by_col = df.isna().sum().sort_values(ascending=False)
    missing_table = (
        pd.DataFrame(
            {
                "column": missing_by_col.index,
                "missing_count": missing_by_col.values,
                "missing_pct": [
                    _safe_percent(float(v), float(rows)) for v in missing_by_col.values
                ],
            }
        )
        .query("missing_count > 0")
        .reset_index(drop=True)
    )

    column_profile = pd.DataFrame(
        {
            "column": df.columns,
            "dtype": [str(dtype) for dtype in df.dtypes],
            "non_null": [int(df[col].notna().sum()) for col in df.columns],
            "missing_count": [int(df[col].isna().sum()) for col in df.columns],
            "missing_pct": [
                _safe_percent(float(df[col].isna().sum()), float(rows)) for col in df.columns
            ],
            "unique": [int(df[col].nunique(dropna=True)) for col in df.columns],
            "constant": [bool(df[col].nunique(dropna=False) <= 1) for col in df.columns],
        }
    )

    duplicate_rows = int(df.duplicated().sum())
    duplicate_pct = _safe_percent(float(duplicate_rows), float(rows))

    constant_columns = (
        column_profile.loc[column_profile["constant"], "column"].astype(str).tolist()
    )

    placeholder_table_rows: list[dict[str, Any]] = []
    for col in df.columns:
        if not pd.api.types.is_object_dtype(df[col]) and not pd.api.types.is_string_dtype(df[col]):
            continue
        cleaned = df[col].dropna().astype(str).str.strip().str.lower()
        count = int(cleaned.isin(MISSING_TOKENS).sum())
        if count > 0:
            placeholder_table_rows.append(
                {
                    "column": col,
                    "placeholder_missing_count": count,
                    "placeholder_missing_pct": _safe_percent(float(count), float(rows)),
                }
            )
    placeholder_table = pd.DataFrame(placeholder_table_rows)

    type_suggestions_rows: list[dict[str, Any]] = []
    object_cols = df.select_dtypes(include=["object", "string"]).columns.tolist()
    for col in object_cols:
        num_ratio = _numeric_like_ratio(df[col])
        dt_ratio = _datetime_like_ratio(df[col])
        suggested_type = "text"
        confidence = 0.0
        if num_ratio >= 0.8 and num_ratio >= dt_ratio:
            suggested_type = "numeric"
            confidence = num_ratio
        elif dt_ratio >= 0.8:
            suggested_type = "datetime"
            confidence = dt_ratio
        if suggested_type != "text":
            type_suggestions_rows.append(
                {
                    "column": col,
                    "current_dtype": str(df[col].dtype),
                    "suggested_type": suggested_type,
                    "confidence_pct": round(confidence * 100.0, 2),
                }
            )
    type_suggestions = pd.DataFrame(type_suggestions_rows)

    # Outliers: IQR + Z-score combinados
    outlier_rows: list[dict[str, Any]] = []
    for col in df.select_dtypes(include=["number"]).columns:
        series = df[col].dropna()
        if series.empty:
            continue

        # IQR
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        if iqr > 0:
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            iqr_count = int(((series < lower) | (series > upper)).sum())
        else:
            iqr_count = 0

        # Z-score
        zscore_count = _outliers_zscore(series)

        if iqr_count > 0 or zscore_count > 0:
            outlier_rows.append(
                {
                    "column": col,
                    "outlier_count_iqr": iqr_count,
                    "outlier_pct_iqr": _safe_percent(float(iqr_count), float(rows)),
                    "outlier_count_zscore": zscore_count,
                    "outlier_pct_zscore": _safe_percent(float(zscore_count), float(rows)),
                }
            )
    outlier_table = pd.DataFrame(outlier_rows)

    # Padroes semanticos
    pattern_table = _detect_patterns(df, rows)

    summary = {
        "rows": rows,
        "columns": cols,
        "missing_cells": int(df.isna().sum().sum()),
        "missing_cells_pct": _safe_percent(float(df.isna().sum().sum()), float(total_cells)),
        "duplicate_rows": duplicate_rows,
        "duplicate_rows_pct": duplicate_pct,
        "memory_mb": round(float(df.memory_usage(deep=True).sum()) / (1024**2), 3),
        "constant_columns_count": len(constant_columns),
    }

    return {
        "summary": summary,
        "column_profile": column_profile,
        "missing_table": missing_table,
        "placeholder_table": placeholder_table,
        "type_suggestions": type_suggestions,
        "outlier_table": outlier_table,
        "pattern_table": pattern_table,
        "constant_columns": constant_columns,
    }
