from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data.quality import analyze_dataset


def _make_df(**kwargs: list) -> pd.DataFrame:
    return pd.DataFrame(kwargs)


class TestAnalyzeDatasetGuards:
    def test_empty_dataframe_returns_error_key(self) -> None:
        df = pd.DataFrame()
        result = analyze_dataset(df)
        assert "error" in result

    def test_zero_rows_returns_error_key(self) -> None:
        df = pd.DataFrame({"a": pd.Series([], dtype=float)})
        result = analyze_dataset(df)
        assert "error" in result

    def test_error_result_has_required_keys(self) -> None:
        result = analyze_dataset(pd.DataFrame())
        for key in ("summary", "missing_table", "outlier_table", "type_suggestions", "constant_columns"):
            assert key in result

    def test_no_numeric_columns_does_not_crash(self) -> None:
        df = _make_df(name=["Alice", "Bob"], city=["SP", "RJ"])
        result = analyze_dataset(df)
        assert "error" not in result
        assert result["outlier_table"].empty


class TestAnalyzeDatasetLogic:
    def test_missing_cells_counted_correctly(self) -> None:
        df = _make_df(a=[1, None, 3], b=[None, None, 6])
        result = analyze_dataset(df)
        assert result["summary"]["missing_cells"] == 3

    def test_duplicate_rows_detected(self) -> None:
        df = _make_df(a=[1, 1, 2], b=["x", "x", "y"])
        result = analyze_dataset(df)
        assert result["summary"]["duplicate_rows"] == 1

    def test_constant_column_detected(self) -> None:
        df = _make_df(a=[5, 5, 5], b=[1, 2, 3])
        result = analyze_dataset(df)
        assert "a" in result["constant_columns"]
        assert "b" not in result["constant_columns"]

    def test_outlier_detected(self) -> None:
        # Necessario ter variacao suficiente para IQR != 0
        values = list(range(1, 20)) + [1000]
        df = _make_df(v=values)
        result = analyze_dataset(df)
        assert not result["outlier_table"].empty

    def test_all_null_column_does_not_crash(self) -> None:
        df = _make_df(a=[None, None, None], b=[1, 2, 3])
        result = analyze_dataset(df)
        assert "error" not in result


class TestCardinalityDetection:
    def test_high_cardinality_text_column_flagged(self) -> None:
        # Coluna com 100% de valores únicos em texto → possível ID
        df = pd.DataFrame({"id": [f"UUID-{i}" for i in range(20)], "valor": range(20)})
        result = analyze_dataset(df)
        flagged = result["cardinality_table"]
        assert not flagged.empty
        assert "id" in flagged["column"].values

    def test_low_cardinality_numeric_column_flagged(self) -> None:
        # Coluna numérica com apenas 3 valores únicos → possível categórica mal tipada
        df = pd.DataFrame({"status": [1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3], "valor": range(12)})
        result = analyze_dataset(df)
        flagged = result["cardinality_table"]
        assert not flagged.empty
        assert "status" in flagged["column"].values

    def test_normal_column_not_flagged(self) -> None:
        # Coluna numérica com muitos valores únicos não deve ser flagrada
        df = pd.DataFrame({"preco": [float(i) * 1.1 for i in range(30)]})
        result = analyze_dataset(df)
        flagged = result["cardinality_table"]
        assert "preco" not in (flagged["column"].values if not flagged.empty else [])

    def test_cardinality_table_in_empty_result(self) -> None:
        result = analyze_dataset(pd.DataFrame())
        assert "cardinality_table" in result

    def test_cardinality_table_in_normal_result(self) -> None:
        df = _make_df(a=[1, 2, 3], b=["x", "y", "z"])
        result = analyze_dataset(df)
        assert "cardinality_table" in result
        assert isinstance(result["cardinality_table"], pd.DataFrame)


class TestFuzzyDuplicates:
    def test_fuzzy_table_present_in_result(self) -> None:
        df = _make_df(nome=["João Silva", "Joao Silva", "Maria"], valor=[1, 2, 3])
        result = analyze_dataset(df)
        assert "fuzzy_table" in result
        assert isinstance(result["fuzzy_table"], pd.DataFrame)

    def test_fuzzy_table_in_empty_result(self) -> None:
        result = analyze_dataset(pd.DataFrame())
        assert "fuzzy_table" in result
