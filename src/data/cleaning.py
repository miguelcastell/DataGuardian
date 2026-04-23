from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.data.quality import MISSING_TOKENS


def _normalize_column_names(columns: pd.Index) -> list[str]:
    normalized = (
        pd.Series(columns.astype(str))
        .str.strip()
        .str.lower()
        .str.replace(r"[^a-z0-9]+", "_", regex=True)
        .str.replace(r"(^_+|_+$)", "", regex=True)
        .tolist()
    )
    seen: dict[str, int] = {}
    result: list[str] = []
    for name in normalized:
        if name in seen:
            seen[name] += 1
            result.append(f"{name}_{seen[name]}")
        else:
            seen[name] = 0
            result.append(name)
    return result


def clean_dataset(
    df: pd.DataFrame,
    *,
    trim_strings: bool = True,
    replace_missing_tokens: bool = True,
    normalize_column_names: bool = True,
    drop_duplicates: bool = True,
    drop_high_missing_columns_pct: float = 100.0,
    fill_numeric: str = "median",
    fill_categorical: str = "mode",
    outlier_treatment: str = "none",
    outlier_method: str = "iqr",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Limpa e trata o dataset conforme as opcoes selecionadas.

    outlier_treatment:
        "none"   — nenhuma acao (padrao)
        "cap"    — capping pelos limites IQR (winsorization)
        "remove" — remove linhas com outliers

    outlier_method:
        "iqr"     — usa regra 1.5×IQR
        "zscore"  — usa |z| > 3
    """
    cleaned = df.copy()
    report: dict[str, Any] = {
        "rows_before": int(df.shape[0]),
        "columns_before": int(df.shape[1]),
    }

    if normalize_column_names:
        original_cols = cleaned.columns.tolist()
        normalized_cols = _normalize_column_names(cleaned.columns)
        cleaned.columns = normalized_cols
        report["columns_renamed"] = int(sum(a != b for a, b in zip(original_cols, normalized_cols)))
    else:
        report["columns_renamed"] = 0

    if trim_strings:
        object_cols = cleaned.select_dtypes(include=["object", "string"]).columns.tolist()
        for col in object_cols:
            cleaned[col] = cleaned[col].astype("string").str.strip()
        report["trimmed_string_columns"] = len(object_cols)
    else:
        report["trimmed_string_columns"] = 0

    if replace_missing_tokens:
        object_cols = cleaned.select_dtypes(include=["object", "string"]).columns.tolist()
        replaced_total = 0
        for col in object_cols:
            original_nulls = int(cleaned[col].isna().sum())
            cleaned[col] = cleaned[col].replace(
                {token: np.nan for token in MISSING_TOKENS}
            )
            cleaned[col] = cleaned[col].replace(
                {token.upper(): np.nan for token in MISSING_TOKENS}
            )
            after_nulls = int(cleaned[col].isna().sum())
            replaced_total += max(0, after_nulls - original_nulls)
        report["missing_tokens_converted"] = replaced_total
    else:
        report["missing_tokens_converted"] = 0

    if drop_duplicates:
        dup_count = int(cleaned.duplicated().sum())
        cleaned = cleaned.drop_duplicates().reset_index(drop=True)
        report["dropped_duplicate_rows"] = dup_count
    else:
        report["dropped_duplicate_rows"] = 0

    dropped_cols: list[str] = []
    if drop_high_missing_columns_pct < 100.0:
        miss_pct = cleaned.isna().mean() * 100.0
        candidates = miss_pct[miss_pct > float(drop_high_missing_columns_pct)].index.tolist()
        if candidates and len(candidates) < len(cleaned.columns):
            dropped_cols = candidates
            cleaned = cleaned.drop(columns=dropped_cols)
        elif candidates:
            dropped_cols = []
    report["dropped_high_missing_columns"] = dropped_cols

    if fill_numeric in {"median", "mean", "zero"}:
        for col in cleaned.select_dtypes(include=["number"]).columns:
            if not cleaned[col].isna().any():
                continue
            if fill_numeric == "median":
                value = cleaned[col].median()
            elif fill_numeric == "mean":
                value = cleaned[col].mean()
            else:
                value = 0
            cleaned[col] = cleaned[col].fillna(value)
    report["numeric_fill_strategy"] = fill_numeric

    if fill_categorical in {"mode", "unknown"}:
        for col in cleaned.select_dtypes(include=["object", "string", "category"]).columns:
            if not cleaned[col].isna().any():
                continue
            if fill_categorical == "mode":
                modes = cleaned[col].mode(dropna=True)
                fill_value = modes.iloc[0] if not modes.empty else "unknown"
            else:
                fill_value = "unknown"
            cleaned[col] = cleaned[col].fillna(fill_value)
    report["categorical_fill_strategy"] = fill_categorical

    # Tratamento de outliers
    outliers_treated_cols: list[str] = []
    outliers_rows_removed = 0
    if outlier_treatment in {"cap", "remove"}:
        numeric_cols = cleaned.select_dtypes(include=["number"]).columns.tolist()
        if outlier_treatment == "remove":
            outlier_mask = pd.Series([False] * len(cleaned), index=cleaned.index)
        for col in numeric_cols:
            series = cleaned[col].dropna()
            if series.empty:
                continue
            if outlier_method == "zscore":
                std = series.std()
                if std == 0:
                    continue
                z = (cleaned[col] - series.mean()) / std
                is_outlier = z.abs() > 3.0
            else:  # iqr (default)
                q1 = series.quantile(0.25)
                q3 = series.quantile(0.75)
                iqr = q3 - q1
                if iqr == 0:
                    continue
                lower = q1 - 1.5 * iqr
                upper = q3 + 1.5 * iqr
                is_outlier = (cleaned[col] < lower) | (cleaned[col] > upper)

            if not is_outlier.any():
                continue

            if outlier_treatment == "cap":
                if outlier_method == "zscore":
                    mean = series.mean()
                    std = series.std()
                    lower = mean - 3.0 * std
                    upper = mean + 3.0 * std
                cleaned[col] = cleaned[col].clip(lower=lower, upper=upper)
                outliers_treated_cols.append(col)
            elif outlier_treatment == "remove":
                outlier_mask = outlier_mask | is_outlier.reindex(cleaned.index, fill_value=False)

        if outlier_treatment == "remove" and outlier_mask.any():
            outliers_rows_removed = int(outlier_mask.sum())
            cleaned = cleaned[~outlier_mask].reset_index(drop=True)

    report["outlier_treatment"] = outlier_treatment
    report["outlier_method"] = outlier_method
    report["outlier_capped_columns"] = outliers_treated_cols
    report["outlier_rows_removed"] = outliers_rows_removed

    report["rows_after"] = int(cleaned.shape[0])
    report["columns_after"] = int(cleaned.shape[1])
    report["missing_cells_after"] = int(cleaned.isna().sum().sum())
    return cleaned, report
