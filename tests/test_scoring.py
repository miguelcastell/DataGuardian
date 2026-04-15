from __future__ import annotations

import pandas as pd
import pytest

from app.dashboard_app.scoring import compute_quality_score


def _make_analysis(
    rows: int = 100,
    cols: int = 5,
    missing_cells: int = 0,
    missing_cells_pct: float = 0.0,
    duplicate_rows: int = 0,
    duplicate_rows_pct: float = 0.0,
    constant_columns: list | None = None,
    missing_table: pd.DataFrame | None = None,
    placeholder_table: pd.DataFrame | None = None,
    type_suggestions: pd.DataFrame | None = None,
    outlier_table: pd.DataFrame | None = None,
) -> dict:
    return {
        "summary": {
            "rows": rows,
            "columns": cols,
            "missing_cells": missing_cells,
            "missing_cells_pct": missing_cells_pct,
            "duplicate_rows": duplicate_rows,
            "duplicate_rows_pct": duplicate_rows_pct,
            "memory_mb": 0.1,
            "constant_columns_count": len(constant_columns or []),
        },
        "constant_columns": constant_columns or [],
        "missing_table": missing_table if missing_table is not None else pd.DataFrame(),
        "placeholder_table": placeholder_table if placeholder_table is not None else pd.DataFrame(),
        "type_suggestions": type_suggestions if type_suggestions is not None else pd.DataFrame(),
        "outlier_table": outlier_table if outlier_table is not None else pd.DataFrame(),
    }


class TestComputeQualityScore:
    def test_perfect_dataset_scores_100(self) -> None:
        analysis = _make_analysis()
        score, level, breakdown = compute_quality_score(analysis)
        assert score == 100.0
        assert level == "Excelente"
        assert breakdown == {}

    def test_score_in_valid_range(self) -> None:
        analysis = _make_analysis(missing_cells=50, missing_cells_pct=10.0)
        score, _, _ = compute_quality_score(analysis)
        assert 0.0 <= score <= 100.0

    def test_returns_three_values(self) -> None:
        result = compute_quality_score(_make_analysis())
        assert len(result) == 3

    def test_breakdown_has_negative_values_only(self) -> None:
        analysis = _make_analysis(missing_cells=20, missing_cells_pct=4.0)
        _, _, breakdown = compute_quality_score(analysis)
        for val in breakdown.values():
            assert val <= 0.0

    def test_more_missing_means_lower_score(self) -> None:
        low_missing = _make_analysis(missing_cells=5, missing_cells_pct=1.0)
        high_missing = _make_analysis(missing_cells=50, missing_cells_pct=10.0)
        score_low, _, _ = compute_quality_score(low_missing)
        score_high, _, _ = compute_quality_score(high_missing)
        assert score_low > score_high

    def test_quality_levels(self) -> None:
        _, level_good, _ = compute_quality_score(_make_analysis(missing_cells_pct=5.0))
        _, level_critical, _ = compute_quality_score(_make_analysis(missing_cells_pct=50.0))
        assert level_good in ("Excelente", "Bom", "Atencao")
        assert level_critical in ("Atencao", "Critico")

    def test_duplicate_penalty_applied(self) -> None:
        no_dups = _make_analysis()
        with_dups = _make_analysis(duplicate_rows=20, duplicate_rows_pct=20.0)
        score_no, _, _ = compute_quality_score(no_dups)
        score_with, _, _ = compute_quality_score(with_dups)
        assert score_no > score_with
