from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data.drift import analyze_drift


class TestSchemaDiff:
    def test_added_columns_detected(self) -> None:
        df_ref = pd.DataFrame({"a": [1, 2, 3]})
        df_new = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        result = analyze_drift(df_ref, df_new)
        assert "b" in result["schema_diff"]["colunas_adicionadas"]

    def test_removed_columns_detected(self) -> None:
        df_ref = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        df_new = pd.DataFrame({"a": [1, 2, 3]})
        result = analyze_drift(df_ref, df_new)
        assert "b" in result["schema_diff"]["colunas_removidas"]

    def test_identical_schema_no_changes(self) -> None:
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        result = analyze_drift(df, df.copy())
        assert result["schema_diff"]["colunas_adicionadas"] == []
        assert result["schema_diff"]["colunas_removidas"] == []

    def test_common_column_count(self) -> None:
        df_ref = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
        df_new = pd.DataFrame({"a": [1], "b": [2], "d": [4]})
        result = analyze_drift(df_ref, df_new)
        assert result["schema_diff"]["colunas_em_comum"] == 2


class TestNumericDrift:
    def test_drift_detected_on_clearly_different_distributions(self) -> None:
        np.random.seed(42)
        df_ref = pd.DataFrame({"v": np.random.normal(0, 1, 200)})
        df_new = pd.DataFrame({"v": np.random.normal(10, 1, 200)})
        result = analyze_drift(df_ref, df_new)
        nd = result["numeric_drift"]
        assert not nd.empty
        assert bool(nd.loc[nd["coluna"] == "v", "drift_detectado"].iloc[0])

    def test_no_drift_on_same_data(self) -> None:
        np.random.seed(0)
        data = np.random.normal(0, 1, 200)
        df_ref = pd.DataFrame({"v": data[:100]})
        df_new = pd.DataFrame({"v": data[100:]})
        result = analyze_drift(df_ref, df_new)
        nd = result["numeric_drift"]
        assert not nd.empty
        assert not bool(nd.loc[nd["coluna"] == "v", "drift_detectado"].iloc[0])

    def test_small_series_skipped(self) -> None:
        df_ref = pd.DataFrame({"v": [1.0, 2.0]})
        df_new = pd.DataFrame({"v": [100.0, 200.0]})
        result = analyze_drift(df_ref, df_new)
        # series with < 5 rows should be skipped
        assert result["numeric_drift"].empty

    def test_numeric_drift_result_keys(self) -> None:
        np.random.seed(1)
        df_ref = pd.DataFrame({"v": np.random.normal(0, 1, 50)})
        df_new = pd.DataFrame({"v": np.random.normal(5, 1, 50)})
        result = analyze_drift(df_ref, df_new)
        nd = result["numeric_drift"]
        for key in ("coluna", "media_ref", "media_atual", "drift_detectado"):
            assert key in nd.columns


class TestCategoricalDrift:
    def test_psi_drift_detected_on_shifted_distribution(self) -> None:
        df_ref = pd.DataFrame({"cat": ["A"] * 80 + ["B"] * 20})
        df_new = pd.DataFrame({"cat": ["A"] * 20 + ["B"] * 80})
        result = analyze_drift(df_ref, df_new)
        cd = result["categorical_drift"]
        assert not cd.empty
        assert bool(cd.loc[cd["coluna"] == "cat", "drift_detectado"].iloc[0])

    def test_psi_stable_on_identical_distribution(self) -> None:
        df_ref = pd.DataFrame({"cat": ["A"] * 50 + ["B"] * 50})
        df_new = pd.DataFrame({"cat": ["A"] * 50 + ["B"] * 50})
        result = analyze_drift(df_ref, df_new)
        cd = result["categorical_drift"]
        if not cd.empty and "cat" in cd["coluna"].values:
            assert not bool(cd.loc[cd["coluna"] == "cat", "drift_detectado"].iloc[0])

    def test_high_cardinality_column_skipped(self) -> None:
        # Coluna com >50 valores únicos deve ser ignorada
        df_ref = pd.DataFrame({"id": [f"ID-{i}" for i in range(100)]})
        df_new = pd.DataFrame({"id": [f"ID-{i}" for i in range(50, 150)]})
        result = analyze_drift(df_ref, df_new)
        assert result["categorical_drift"].empty

    def test_severity_labels(self) -> None:
        df_ref = pd.DataFrame({"cat": ["A"] * 80 + ["B"] * 20})
        df_new = pd.DataFrame({"cat": ["A"] * 20 + ["B"] * 80})
        result = analyze_drift(df_ref, df_new)
        cd = result["categorical_drift"]
        assert cd.loc[cd["coluna"] == "cat", "severidade"].iloc[0] in (
            "moderado", "significativo"
        )


class TestDriftSummaryAndStructure:
    def test_all_result_keys_present(self) -> None:
        df = pd.DataFrame({"v": [1.0, 2.0, 3.0]})
        result = analyze_drift(df, df.copy())
        for key in ("schema_diff", "numeric_drift", "categorical_drift", "summary"):
            assert key in result

    def test_summary_keys_always_present(self) -> None:
        df = pd.DataFrame({"v": [1.0, 2.0, 3.0, 4.0, 5.0]})
        result = analyze_drift(df, df.copy())
        for key in ("linhas_ref", "linhas_atual", "colunas_com_drift_numerico", "colunas_com_drift_categorico"):
            assert key in result["summary"]

    def test_no_common_columns(self) -> None:
        df_ref = pd.DataFrame({"a": [1, 2, 3]})
        df_new = pd.DataFrame({"b": [4, 5, 6]})
        result = analyze_drift(df_ref, df_new)
        assert result["numeric_drift"].empty
        assert result["categorical_drift"].empty
        assert result["schema_diff"]["colunas_em_comum"] == 0
