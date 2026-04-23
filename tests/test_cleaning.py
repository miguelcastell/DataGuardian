from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data.cleaning import clean_dataset, _normalize_column_names


class TestNormalizeColumnNames:
    def test_basic_normalization(self) -> None:
        idx = pd.Index(["First Name", "Last Name"])
        result = _normalize_column_names(idx)
        assert result == ["first_name", "last_name"]

    def test_collision_produces_unique_names(self) -> None:
        # "First Name" e "first name" ambos normalizam para "first_name"
        idx = pd.Index(["First Name", "first name"])
        result = _normalize_column_names(idx)
        assert len(set(result)) == 2, "Nomes normalizados devem ser unicos"
        assert result[0] == "first_name"
        assert result[1] == "first_name_1"

    def test_three_way_collision(self) -> None:
        idx = pd.Index(["A B", "a_b", "A_B"])
        result = _normalize_column_names(idx)
        assert len(set(result)) == 3

    def test_special_characters_removed(self) -> None:
        idx = pd.Index(["col@1!", "col#2"])
        result = _normalize_column_names(idx)
        assert all(c.isalnum() or c == "_" for name in result for c in name)


class TestCleanDataset:
    def _simple_df(self) -> pd.DataFrame:
        return pd.DataFrame({
            "Name": ["Alice", "Bob", "Alice"],
            "Age": [25.0, None, 25.0],
            "City": [None, "SP", None],
        })

    def test_returns_dataframe_and_report(self) -> None:
        df = self._simple_df()
        result, report = clean_dataset(df)
        assert isinstance(result, pd.DataFrame)
        assert isinstance(report, dict)

    def test_remove_duplicates(self) -> None:
        df = self._simple_df()
        cleaned, report = clean_dataset(df, drop_duplicates=True)
        assert report["dropped_duplicate_rows"] == 1
        assert len(cleaned) == 2

    def test_all_null_column_does_not_crash(self) -> None:
        df = pd.DataFrame({"a": [None, None, None], "b": [1, 2, 3]})
        cleaned, _ = clean_dataset(df, fill_categorical="mode")
        assert "a" in cleaned.columns or "b" in cleaned.columns

    def test_drop_high_missing_does_not_remove_all_columns(self) -> None:
        df = pd.DataFrame({"a": [None, None, None], "b": [None, None, None]})
        cleaned, report = clean_dataset(df, drop_high_missing_columns_pct=0.0)
        assert cleaned.shape[1] > 0, "Nao deve remover todas as colunas"
        assert len(report["dropped_high_missing_columns"]) == 0

    def test_numeric_fill_median(self) -> None:
        df = pd.DataFrame({"v": [1.0, 2.0, None, 4.0]})
        cleaned, _ = clean_dataset(df, fill_numeric="median")
        assert not cleaned["v"].isna().any()

    def test_categorical_fill_mode(self) -> None:
        df = pd.DataFrame({"c": ["x", "x", None, "y"]})
        cleaned, _ = clean_dataset(df, fill_categorical="mode")
        # Garante que o nulo foi preenchido — o valor exato depende do pandas
        assert not cleaned["c"].isna().any()

    def test_column_name_collision_resolved(self) -> None:
        df = pd.DataFrame({"A B": [1, 2], "a_b": [3, 4]})
        cleaned, _ = clean_dataset(df, normalize_column_names=True)
        assert len(cleaned.columns) == len(set(cleaned.columns)), "Nomes de colunas devem ser unicos"


class TestOutlierTreatment:
    def _outlier_df(self) -> pd.DataFrame:
        # Valores normais 1-19 + dois outliers extremos
        return pd.DataFrame({"v": list(range(1, 20)) + [1000, 2000]})

    def test_no_treatment_preserves_outliers(self) -> None:
        df = self._outlier_df()
        cleaned, report = clean_dataset(df, outlier_treatment="none")
        assert cleaned["v"].max() == 2000
        assert report["outlier_treatment"] == "none"
        assert report["outlier_rows_removed"] == 0

    def test_capping_iqr_reduces_max(self) -> None:
        df = self._outlier_df()
        cleaned, report = clean_dataset(df, outlier_treatment="cap", outlier_method="iqr")
        assert cleaned["v"].max() < 2000
        assert report["outlier_treatment"] == "cap"
        assert len(report["outlier_capped_columns"]) > 0

    def test_capping_zscore_reduces_max(self) -> None:
        df = self._outlier_df()
        cleaned, report = clean_dataset(df, outlier_treatment="cap", outlier_method="zscore")
        assert cleaned["v"].max() < 2000
        assert report["outlier_method"] == "zscore"

    def test_remove_iqr_reduces_row_count(self) -> None:
        df = self._outlier_df()
        cleaned, report = clean_dataset(df, outlier_treatment="remove", outlier_method="iqr")
        assert len(cleaned) < len(df)
        assert report["outlier_rows_removed"] > 0

    def test_remove_does_not_crash_on_zero_iqr_column(self) -> None:
        # Coluna com todos os valores iguais → IQR == 0, não deve quebrar
        # drop_duplicates=False para não remover as linhas idênticas antes do teste de outlier
        df = pd.DataFrame({"v": [5, 5, 5, 5, 5]})
        cleaned, report = clean_dataset(df, outlier_treatment="remove", outlier_method="iqr", drop_duplicates=False)
        assert len(cleaned) == len(df)
        assert report["outlier_rows_removed"] == 0

    def test_capping_preserves_row_count(self) -> None:
        df = self._outlier_df()
        cleaned, _ = clean_dataset(df, outlier_treatment="cap")
        assert len(cleaned) == len(df)

    def test_report_keys_always_present(self) -> None:
        df = self._outlier_df()
        _, report = clean_dataset(df, outlier_treatment="none")
        for key in ("outlier_treatment", "outlier_method", "outlier_capped_columns", "outlier_rows_removed"):
            assert key in report
