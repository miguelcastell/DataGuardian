from __future__ import annotations

import pandas as pd

# Como funciona o sistema de score
# ─────────────────────────────────────────────────────────────────────────────
# O score parte de 100 e desconta penalidades por cada dimensão de qualidade.
#
# Fórmula por dimensão:
#   penalidade = min(percentual_do_problema × peso, cap)
#   score_final = 100 − soma_de_todas_as_penalidades  (clampado entre 0 e 100)
#
# Por que pesos diferentes por dimensão?
#   - "duplicates" tem peso 2.0 (o mais alto): uma linha duplicada contamina
#     agregações, contagens e modelos de forma direta e previsível — o dano
#     é certo e imediato.
#   - "missing" tem peso 1.5: dados ausentes comprometem análises, mas em
#     muitos casos podem ser imputados sem grande perda de fidelidade.
#   - "type" tem peso 1.0: colunas com tipo errado (ex: número como texto)
#     quebram pipelines, mas o fix é determinístico e barato.
#   - "placeholder" e "constant" têm peso 0.8: são problemas de estrutura,
#     não de conteúdo — impactam menos análises do que missing real.
#   - "outlier" tem peso 0.5 (o mais baixo): outliers podem ser legítimos
#     (ex: transação VIP, evento raro); penalizar menos evita falsos alarmes.
#
# Por que caps por dimensão?
#   Os caps impedem que um único problema domine o score inteiro. Por exemplo,
#   se 80% das células estão vazias, sem cap a penalidade seria 120 pts — o
#   score travaria em zero mesmo que os outros 20% fossem perfeitos. Com cap
#   de 30 pts, o score mínimo por missing é 70, deixando as outras dimensões
#   contribuírem proporcionalmente.
#
# Por que presets de domínio?
#   Diferentes contextos têm tolerâncias distintas. Em dados financeiros,
#   qualquer duplicata é potencialmente fraude — então o peso sobe para 3.0.
#   Em dados de marketing, duplicatas de lead são comuns e menos críticas —
#   peso 1.5. Os presets permitem calibrar sem alterar o código.
# ─────────────────────────────────────────────────────────────────────────────

# Pesos padrão por dimensão. Podem ser sobrescritos via custom_weights.
_DEFAULT_WEIGHTS: dict[str, float] = {
    "missing":     1.5,  # por % de células faltantes (cap: 30 pts)
    "duplicates":  2.0,  # por % de linhas duplicadas (cap: 20 pts)
    "constant":    0.8,  # por % de colunas constantes (cap: 10 pts)
    "placeholder": 0.8,  # por % de células com tokens de nulo (cap: 10 pts)
    "type":        1.0,  # por % de colunas com sugestão de tipo (cap: 15 pts)
    "outlier":     0.5,  # por % média de outliers (cap: 10 pts)
}

_DEFAULT_CAPS: dict[str, float] = {
    "missing": 30.0,
    "duplicates": 20.0,
    "constant": 10.0,
    "placeholder": 10.0,
    "type": 15.0,
    "outlier": 10.0,
}

# Limiares de nível de qualidade
_LEVEL_EXCELLENT = 90
_LEVEL_GOOD = 75
_LEVEL_ATTENTION = 55

# Presets de domínio: ajustam os pesos conforme o contexto dos dados
DOMAIN_PRESETS: dict[str, dict[str, float]] = {
    "Geral": _DEFAULT_WEIGHTS,
    "Financeiro": {
        "missing": 2.5,
        "duplicates": 3.0,
        "constant": 0.8,
        "placeholder": 1.2,
        "type": 1.5,
        "outlier": 1.0,
    },
    "Marketing / CRM": {
        "missing": 1.0,
        "duplicates": 1.5,
        "constant": 0.5,
        "placeholder": 0.8,
        "type": 0.8,
        "outlier": 0.3,
    },
    "RH / Pessoas": {
        "missing": 2.0,
        "duplicates": 2.5,
        "constant": 0.6,
        "placeholder": 1.0,
        "type": 1.0,
        "outlier": 0.4,
    },
    "Logistica / Operacoes": {
        "missing": 1.8,
        "duplicates": 2.0,
        "constant": 0.7,
        "placeholder": 0.9,
        "type": 1.2,
        "outlier": 0.8,
    },
}


def compute_quality_score(
    analysis: dict,
    custom_weights: dict[str, float] | None = None,
) -> tuple[float, str, dict[str, float]]:
    weights = {**_DEFAULT_WEIGHTS, **(custom_weights or {})}

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

    def _deduct(label: str, key: str, pct: float) -> None:
        nonlocal penalty
        w = weights.get(key, _DEFAULT_WEIGHTS[key])
        cap = _DEFAULT_CAPS[key]
        d = min(pct * w, cap)
        if d > 0:
            penalty += d
            breakdown[label] = -round(d, 1)

    _deduct("Valores ausentes",       "missing",     missing_pct)
    _deduct("Linhas duplicadas",      "duplicates",  dup_pct)
    _deduct("Colunas constantes",     "constant",    constant_pct)
    _deduct("Tokens de nulo",         "placeholder", placeholder_pct)
    _deduct("Inconsistencias de tipo","type",        type_issue_pct)
    _deduct("Outliers",               "outlier",     outlier_pct)

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

    # Alertas de cardinalidade
    if "cardinality_table" in analysis and not analysis["cardinality_table"].empty:
        for _, row in analysis["cardinality_table"].iterrows():
            issues.append(
                {
                    "prioridade": "Media",
                    "tipo_problema": "Cardinalidade suspeita",
                    "detalhes": f"Coluna {row['column']}: {row['flag']} ({row['unique_pct']}% unicos)",
                    "acao_recomendada": "Verificar se e ID/chave ou categorica numerica mal tipada",
                }
            )

    # Alertas de quase-duplicatas
    if "fuzzy_table" in analysis and not analysis["fuzzy_table"].empty:
        cols_with_fuzzy = analysis["fuzzy_table"]["column"].unique()
        for col in cols_with_fuzzy[:3]:
            issues.append(
                {
                    "prioridade": "Media",
                    "tipo_problema": "Quase-duplicatas textuais",
                    "detalhes": f"Coluna {col} tem valores com alta similaridade (possivel erro de digitacao)",
                    "acao_recomendada": "Padronizar categorias com fuzzy matching",
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
