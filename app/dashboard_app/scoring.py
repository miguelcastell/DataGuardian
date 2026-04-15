from __future__ import annotations

import pandas as pd


def compute_quality_score(analysis: dict) -> tuple[float, str]:
    rows = max(int(analysis["summary"]["rows"]), 1)
    cols = max(int(analysis["summary"]["columns"]), 1)
    total_cells = max(rows * cols, 1)

    missing_pct = float(analysis["summary"]["missing_cells_pct"])
    dup_pct = float(analysis["summary"]["duplicate_rows_pct"])
    constant_pct = (len(analysis["constant_columns"]) / cols) * 100.0

    placeholder_count = 0
    if not analysis["placeholder_table"].empty:
        placeholder_count = int(analysis["placeholder_table"]["placeholder_missing_count"].sum())
    placeholder_pct = (placeholder_count / total_cells) * 100.0

    type_issue_pct = 0.0
    if cols > 0 and not analysis["type_suggestions"].empty:
        type_issue_pct = (len(analysis["type_suggestions"]) / cols) * 100.0

    outlier_pct = 0.0
    if not analysis["outlier_table"].empty:
        outlier_pct = float(analysis["outlier_table"]["outlier_pct_iqr"].mean())

    penalty = (
        (missing_pct * 1.20)
        + (dup_pct * 1.00)
        + (constant_pct * 0.80)
        + (placeholder_pct * 0.80)
        + (type_issue_pct * 0.90)
        + (outlier_pct * 0.50)
    )

    if analysis["summary"]["missing_cells"] > 0:
        penalty += 4.0
    if analysis["summary"]["duplicate_rows"] > 0:
        penalty += 4.0
    if len(analysis["constant_columns"]) > 0:
        penalty += 3.0
    if not analysis["type_suggestions"].empty:
        penalty += 6.0
    if not analysis["outlier_table"].empty:
        penalty += 3.0

    score = max(0.0, min(100.0, 100.0 - penalty))

    if score >= 90:
        level = "Excelente"
    elif score >= 75:
        level = "Bom"
    elif score >= 55:
        level = "Atencao"
    else:
        level = "Critico"

    return round(score, 1), level


def build_prioritized_issues(analysis: dict) -> pd.DataFrame:
    issues: list[dict[str, str]] = []

    if not analysis["missing_table"].empty:
        top_missing = analysis["missing_table"].sort_values("missing_pct", ascending=False).head(4)
        for _, row in top_missing.iterrows():
            severity = "Alta" if float(row["missing_pct"]) >= 25 else "Media"
            issues.append(
                {
                    "prioridade": severity,
                    "tipo_problema": "Dados faltantes",
                    "detalhes": f"Coluna {row['column']} com {row['missing_pct']}% faltante",
                    "acao_recomendada": "Imputar valores ou remover se tiver baixo sinal",
                }
            )

    dup_count = int(analysis["summary"]["duplicate_rows"])
    if dup_count > 0:
        issues.append(
            {
                "prioridade": "Alta" if dup_count > 100 else "Media",
                "tipo_problema": "Linhas duplicadas",
                "detalhes": f"{dup_count} linhas duplicadas encontradas",
                "acao_recomendada": "Remover duplicidades exatas",
            }
        )

    for col in analysis["constant_columns"][:3]:
        issues.append(
            {
                "prioridade": "Media",
                "tipo_problema": "Coluna constante",
                "detalhes": f"Coluna {col} sem variacao",
                "acao_recomendada": "Remover para modelagem",
            }
        )

    if not analysis["type_suggestions"].empty:
        top_types = analysis["type_suggestions"].sort_values("confidence_pct", ascending=False).head(3)
        for _, row in top_types.iterrows():
            issues.append(
                {
                    "prioridade": "Media",
                    "tipo_problema": "Inconsistencia de tipo",
                    "detalhes": (
                        f"Coluna {row['column']} parece {row['suggested_type']} "
                        f"({row['confidence_pct']}% de confianca)"
                    ),
                    "acao_recomendada": "Converter tipo antes de analise/modelagem",
                }
            )

    if not issues:
        issues.append(
            {
                "prioridade": "Baixa",
                "tipo_problema": "Sem problemas criticos",
                "detalhes": "Nenhum problema bloqueante detectado",
                "acao_recomendada": "Prosseguir para analise exploratoria",
            }
        )

    order = {"Alta": 0, "Media": 1, "Baixa": 2}
    issues_df = pd.DataFrame(issues)
    issues_df["_order"] = issues_df["prioridade"].map(order).fillna(9)
    return issues_df.sort_values(["_order", "tipo_problema"]).drop(columns=["_order"]).reset_index(drop=True)
