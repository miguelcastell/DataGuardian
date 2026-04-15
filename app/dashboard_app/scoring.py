from __future__ import annotations

import pandas as pd

# Pesos de penalidade por ponto percentual de cada dimensao de qualidade.
# Cap maximo por dimensao para evitar que um unico problema collapse o score inteiro.
_MISSING_WEIGHT = 1.5       # por % de celulas faltantes (cap: 30 pts)
_DUP_WEIGHT = 2.0           # por % de linhas duplicadas (cap: 20 pts)
_CONSTANT_WEIGHT = 0.8      # por % de colunas constantes (cap: 10 pts)
_PLACEHOLDER_WEIGHT = 0.8   # por % de celulas com tokens de nulo (cap: 10 pts)
_TYPE_WEIGHT = 1.0          # por % de colunas com sugestao de tipo (cap: 15 pts)
_OUTLIER_WEIGHT = 0.5       # por % media de outliers nas colunas numericas (cap: 10 pts)

# Limiares de nivel de qualidade
_LEVEL_EXCELLENT = 90
_LEVEL_GOOD = 75
_LEVEL_ATTENTION = 55


def compute_quality_score(analysis: dict) -> tuple[float, str, dict[str, float]]:
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

    breakdown: dict[str, float] = {}
    penalty = 0.0

    def _deduct(label: str, pct: float, weight: float, cap: float) -> None:
        nonlocal penalty
        d = min(pct * weight, cap)
        if d > 0:
            penalty += d
            breakdown[label] = -round(d, 1)

    _deduct("Valores ausentes", missing_pct, _MISSING_WEIGHT, 30.0)
    _deduct("Linhas duplicadas", dup_pct, _DUP_WEIGHT, 20.0)
    _deduct("Colunas constantes", constant_pct, _CONSTANT_WEIGHT, 10.0)
    _deduct("Tokens de nulo", placeholder_pct, _PLACEHOLDER_WEIGHT, 10.0)
    _deduct("Inconsistencias de tipo", type_issue_pct, _TYPE_WEIGHT, 15.0)
    _deduct("Outliers", outlier_pct, _OUTLIER_WEIGHT, 10.0)

    score = round(max(0.0, min(100.0, 100.0 - penalty)), 1)

    if score >= _LEVEL_EXCELLENT:
        level = "Excelente"
    elif score >= _LEVEL_GOOD:
        level = "Bom"
    elif score >= _LEVEL_ATTENTION:
        level = "Atencao"
    else:
        level = "Critico"

    return score, level, breakdown


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
