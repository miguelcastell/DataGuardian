from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def analyze_drift(df_ref: pd.DataFrame, df_new: pd.DataFrame) -> dict[str, Any]:
    """
    Compara dois DataFrames e detecta mudancas de distribuicao (drift).

    Numericas: KS test (scipy) — p < 0.05 indica drift.
    Categoricas: PSI — >= 0.1 moderado, >= 0.2 significativo.
    """
    try:
        from scipy import stats as _stats  # type: ignore
        _has_scipy = True
    except ImportError:
        _has_scipy = False

    cols_ref = set(df_ref.columns)
    cols_new = set(df_new.columns)
    common = sorted(cols_ref & cols_new)

    schema_diff: dict[str, Any] = {
        "colunas_adicionadas": sorted(cols_new - cols_ref),
        "colunas_removidas": sorted(cols_ref - cols_new),
        "colunas_em_comum": len(common),
    }

    # ── Drift numerico (KS test) ──────────────────────────────────────────────
    numeric_rows: list[dict[str, Any]] = []
    for col in common:
        if not pd.api.types.is_numeric_dtype(df_ref[col]) or not pd.api.types.is_numeric_dtype(df_new[col]):
            continue
        a = df_ref[col].dropna()
        b = df_new[col].dropna()
        if len(a) < 5 or len(b) < 5:
            continue

        mean_ref = float(a.mean())
        mean_new = float(b.mean())
        std_ref = float(a.std()) if len(a) > 1 else 0.0
        delta_pct = ((mean_new - mean_ref) / abs(mean_ref) * 100.0) if mean_ref != 0 else None

        if _has_scipy:
            ks_stat, p_value = _stats.ks_2samp(a.values, b.values)
            drift_detected = bool(p_value < 0.05)
        else:
            ks_stat = p_value = None
            drift_detected = bool(abs(mean_new - mean_ref) > 0.2 * max(std_ref, 1e-9))

        numeric_rows.append({
            "coluna": col,
            "media_ref": round(mean_ref, 4),
            "media_atual": round(mean_new, 4),
            "delta_pct": round(delta_pct, 2) if delta_pct is not None else None,
            "ks_estatistica": round(float(ks_stat), 4) if ks_stat is not None else None,
            "p_valor": round(float(p_value), 4) if p_value is not None else None,
            "drift_detectado": drift_detected,
        })

    numeric_drift = pd.DataFrame(numeric_rows)

    # ── Drift categorico (PSI) ────────────────────────────────────────────────
    cat_rows: list[dict[str, Any]] = []
    for col in common:
        dtype = df_ref[col].dtype
        is_text = (
            not pd.api.types.is_numeric_dtype(dtype)
            and not pd.api.types.is_bool_dtype(dtype)
            and not pd.api.types.is_datetime64_any_dtype(dtype)
        )
        if not is_text:
            continue

        s_ref = df_ref[col].dropna().astype(str)
        s_new = df_new[col].dropna().astype(str)
        if s_ref.empty or s_new.empty:
            continue

        all_vals = sorted(set(s_ref.unique()) | set(s_new.unique()))
        if len(all_vals) < 2 or len(all_vals) > 50:
            continue

        freq_ref = s_ref.value_counts(normalize=True)
        freq_new = s_new.value_counts(normalize=True)

        psi = 0.0
        for val in all_vals:
            p_r = max(float(freq_ref.get(val, 0.0)), 1e-6)
            p_n = max(float(freq_new.get(val, 0.0)), 1e-6)
            psi += (p_n - p_r) * np.log(p_n / p_r)

        severity = "significativo" if psi >= 0.2 else "moderado" if psi >= 0.1 else "estavel"
        cat_rows.append({
            "coluna": col,
            "unicos_ref": int(s_ref.nunique()),
            "unicos_atual": int(s_new.nunique()),
            "psi": round(psi, 4),
            "severidade": severity,
            "drift_detectado": bool(psi >= 0.1),
        })

    categorical_drift = pd.DataFrame(cat_rows)

    n_num_drift = int(numeric_drift["drift_detectado"].sum()) if not numeric_drift.empty else 0
    n_cat_drift = int(categorical_drift["drift_detectado"].sum()) if not categorical_drift.empty else 0

    return {
        "schema_diff": schema_diff,
        "numeric_drift": numeric_drift,
        "categorical_drift": categorical_drift,
        "summary": {
            "linhas_ref": len(df_ref),
            "linhas_atual": len(df_new),
            "colunas_com_drift_numerico": n_num_drift,
            "colunas_com_drift_categorico": n_cat_drift,
            "scipy_disponivel": _has_scipy,
        },
    }
