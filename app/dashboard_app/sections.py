from __future__ import annotations

import io
import json
from datetime import UTC, datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.dashboard_app.styles import QUALITY_PALETTE, badge, metric_card
from src.data.cleaning import clean_dataset


# ── helpers ──────────────────────────────────────────────────────────────────

def _score_gauge(score: float, level: str) -> go.Figure:
    palette = QUALITY_PALETTE.get(level, QUALITY_PALETTE["Bom"])
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "/100", "font": {"size": 28, "color": palette["color"]}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#94a3b8"},
                "bar": {"color": palette["accent"], "thickness": 0.25},
                "bgcolor": "white",
                "borderwidth": 0,
                "steps": [
                    {"range": [0,  55], "color": "#fff1f2"},
                    {"range": [55, 75], "color": "#fffbeb"},
                    {"range": [75, 90], "color": "#f0fdf9"},
                    {"range": [90, 100], "color": "#ecfdf3"},
                ],
                "threshold": {
                    "line": {"color": palette["accent"], "width": 3},
                    "thickness": 0.85,
                    "value": score,
                },
            },
        )
    )
    fig.update_layout(
        height=200,
        margin=dict(l=20, r=20, t=30, b=10),
        paper_bgcolor="white",
        font={"family": "Manrope, sans-serif"},
    )
    return fig


def _null_heatmap(df: pd.DataFrame, max_cols: int = 30) -> go.Figure | None:
    """Heatmap de presenca/ausencia de nulos por coluna."""
    cols = df.columns.tolist()[:max_cols]
    subset = df[cols]
    if subset.empty:
        return None
    # Amostra de ate 200 linhas para nao sobrecarregar o grafico
    sample = subset.head(200)
    z = sample.isna().astype(int).values
    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=cols,
            y=[f"L{i+1}" for i in range(len(sample))],
            colorscale=[[0, "#ecfdf3"], [1, "#ef4444"]],
            showscale=True,
            colorbar=dict(
                tickvals=[0, 1],
                ticktext=["Presente", "Ausente"],
                thickness=14,
                len=0.6,
            ),
            hovertemplate="Coluna: %{x}<br>Linha: %{y}<br>%{text}<extra></extra>",
            text=[["Presente" if v == 0 else "Ausente" for v in row] for row in z],
        )
    )
    fig.update_layout(
        title="Mapa de ausencia de dados (vermelho = nulo)",
        template="plotly_white",
        height=max(220, min(500, len(sample) * 4)),
        margin=dict(l=10, r=10, t=50, b=10),
        xaxis=dict(tickangle=-45),
    )
    return fig


def _diff_dataframe(before: pd.DataFrame, after: pd.DataFrame) -> pd.DataFrame:
    """
    Retorna DataFrame de texto com células marcadas com asterisco (*) onde houve mudança.
    Alinha por índice e colunas comuns.
    """
    common_cols = [c for c in before.columns if c in after.columns]
    b = before[common_cols].reset_index(drop=True)
    a = after[common_cols].reset_index(drop=True)
    n_rows = min(len(b), len(a), 30)
    b = b.head(n_rows)
    a = a.head(n_rows)
    result = a.copy().astype(str)
    for col in common_cols:
        changed = b[col].astype(str) != a[col].astype(str)
        result.loc[changed, col] = result.loc[changed, col] + " ✱"
    return result


# ── render functions ──────────────────────────────────────────────────────────

def render_overview(
    df: pd.DataFrame,
    analysis: dict,
    quality_score: float,
    quality_level: str,
    score_breakdown: dict[str, float] | None = None,
) -> None:
    palette = QUALITY_PALETTE.get(quality_level, QUALITY_PALETTE["Bom"])
    rows = analysis["summary"]["rows"]
    missing_pct = float(analysis["summary"]["missing_cells_pct"])
    dup_pct = float(analysis["summary"]["duplicate_rows_pct"])

    # Gauge + cards lado a lado
    gauge_col, cards_col = st.columns([1, 2])
    with gauge_col:
        st.plotly_chart(_score_gauge(quality_score, quality_level), width="stretch")

    with cards_col:
        c1, c2, c3 = st.columns(3)
        with c1:
            metric_card(
                "Celulas faltantes",
                f"{analysis['summary']['missing_cells']:,}",
                bar_pct=missing_pct,
                bar_color="#ef4444" if missing_pct > 20 else "#f59e0b" if missing_pct > 5 else "#12b76a",
                sub=f"{missing_pct:.1f}% do total",
            )
        with c2:
            metric_card(
                "Linhas duplicadas",
                f"{analysis['summary']['duplicate_rows']:,}",
                bar_pct=dup_pct,
                bar_color="#ef4444" if dup_pct > 5 else "#f59e0b" if dup_pct > 1 else "#12b76a",
                sub=f"{dup_pct:.1f}% das linhas",
            )
        with c3:
            mem = analysis["summary"]["memory_mb"]
            metric_card(
                "Memoria",
                f"{mem:.2f} MB",
                sub=f"{rows:,} linhas · {analysis['summary']['columns']} cols",
            )

        # Padroes detectados como badges
        if "pattern_table" in analysis and not analysis["pattern_table"].empty:
            pt = analysis["pattern_table"]
            badge_html = ""
            for _, r in pt.iterrows():
                badge_html += badge(f"{r['column']} → {r['pattern']} ({r['match_pct']:.0f}%)", "good")
            st.markdown(
                f"<div style='margin-top:12px;'><span style='font-size:.75rem;font-weight:700;"
                f"text-transform:uppercase;letter-spacing:.04em;color:#475467;'>Padroes detectados</span>"
                f"<br><div style='margin-top:6px;'>{badge_html}</div></div>",
                unsafe_allow_html=True,
            )

    if score_breakdown:
        with st.expander("Detalhamento do score de qualidade"):
            lines = []
            for dimensao, deducao in score_breakdown.items():
                lines.append(f"- **{dimensao}**: :red[{deducao:+.1f} pts]")
            st.markdown("\n".join(lines))

    # Heatmap de nulos
    has_missing = analysis["summary"]["missing_cells"] > 0
    if has_missing:
        with st.expander("Mapa de ausencia de dados"):
            fig_hm = _null_heatmap(df)
            if fig_hm:
                st.plotly_chart(fig_hm, width="stretch")

    st.markdown("### Previa do dataset")
    st.dataframe(df.head(60), width="stretch")


def render_quality_issues(analysis: dict, issues_df: pd.DataFrame) -> None:
    badges = []
    if analysis["summary"]["missing_cells"] > 0:
        badges.append(badge("Dados faltantes detectados", "critical"))
    if analysis["summary"]["duplicate_rows"] > 0:
        badges.append(badge("Linhas duplicadas detectadas", "warning"))
    if len(analysis["constant_columns"]) == 0:
        badges.append(badge("Sem colunas constantes", "good"))

    if badges:
        st.markdown("".join(badges), unsafe_allow_html=True)

    st.markdown("### Fila de prioridades")
    st.dataframe(issues_df, width="stretch")

    left, right = st.columns(2)
    with left:
        st.markdown("#### Dados faltantes por coluna")
        if analysis["missing_table"].empty:
            st.success("Nenhum dado faltante encontrado.")
        else:
            st.dataframe(analysis["missing_table"], width="stretch")

        st.markdown("#### Placeholders de nulos")
        if analysis["placeholder_table"].empty:
            st.info("Nenhum placeholder de nulo detectado.")
        else:
            st.dataframe(analysis["placeholder_table"], width="stretch")

        if "pattern_table" in analysis and not analysis["pattern_table"].empty:
            st.markdown("#### Padroes semanticos detectados")
            st.dataframe(analysis["pattern_table"], width="stretch")

    with right:
        st.markdown("#### Sugestoes de tipo")
        if analysis["type_suggestions"].empty:
            st.success("Nenhuma inconsistencia forte de tipo detectada.")
        else:
            st.dataframe(analysis["type_suggestions"], width="stretch")

        st.markdown("#### Outliers (IQR + Z-score)")
        if analysis["outlier_table"].empty:
            st.info("Sem outliers relevantes pelo criterio IQR.")
        else:
            st.dataframe(analysis["outlier_table"], width="stretch")

def render_alerts(analysis: dict, quality_score: float) -> None:
    st.markdown("### Alertas")

    missing_pct = float(analysis["summary"]["missing_cells_pct"])
    dup_pct = float(analysis["summary"]["duplicate_rows_pct"])

    if quality_score < 55:
        st.error("Qualidade critica. Aplique tratamento antes de modelagem ou BI.")
    elif quality_score < 75:
        st.warning("Qualidade moderada. Revise faltantes e duplicatas antes de publicar insights.")
    else:
        st.success("Qualidade adequada para analise.")

    if missing_pct > 20:
        st.warning(f"Taxa alta de faltantes: {missing_pct:.2f}% das celulas.")
    if dup_pct > 5:
        st.warning(f"Taxa de duplicidade acima do limite: {dup_pct:.2f}% das linhas.")
    if len(analysis["constant_columns"]) > 0:
        st.info("Colunas constantes detectadas: " + ", ".join(analysis["constant_columns"][:6]))
    if "pattern_table" in analysis and not analysis["pattern_table"].empty:
        pt = analysis["pattern_table"]
        for _, r in pt.iterrows():
            st.info(
                f"Coluna **{r['column']}** parece conter dados do tipo **{r['pattern']}** "
                f"({r['match_pct']:.0f}% de conformidade). Considere validacao de formato."
            )


def render_visual_insights(df: pd.DataFrame) -> None:
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "string", "category"]).columns.tolist()

    st.markdown("### Insights visuais")

    if not numeric_cols and not categorical_cols:
        st.info("Sem colunas numericas ou categoricas para visualizar.")
        return

    c1, c2 = st.columns(2)

    with c1:
        if numeric_cols:
            hist_col = st.selectbox(
                "Distribuicao",
                options=numeric_cols,
                help="Inspecione assimetria, caudas e concentracao da variavel numerica.",
            )
            fig_hist = px.histogram(df, x=hist_col, nbins=35, title=f"Distribuicao: {hist_col}")
            fig_hist.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig_hist, width="stretch")
        else:
            st.info("Sem coluna numerica para grafico de distribuicao.")

    with c2:
        if categorical_cols:
            cat_col = st.selectbox(
                "Frequencia por categoria",
                options=categorical_cols,
                help="Principais categorias para checagem de cardinalidade e desbalanceamento.",
            )
            counts = df[cat_col].astype("string").fillna("<NA>").value_counts().head(12)
            fig_bar = px.bar(
                x=counts.index,
                y=counts.values,
                labels={"x": cat_col, "y": "contagem"},
                title=f"Top categorias: {cat_col}",
            )
            fig_bar.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig_bar, width="stretch")
        else:
            st.info("Sem coluna categorica para grafico de frequencia.")

    if len(numeric_cols) >= 2:
        s1, s2, s3 = st.columns(3)
        x_col = s1.selectbox("Dispersao X", options=numeric_cols)
        y_col = s2.selectbox("Dispersao Y", options=numeric_cols, index=1)
        color_col = s3.selectbox("Colorir por", options=["(nenhum)"] + categorical_cols)

        fig_scatter = px.scatter(
            df,
            x=x_col,
            y=y_col,
            color=None if color_col == "(nenhum)" else color_col,
            title=f"Relacao: {x_col} vs {y_col}",
            opacity=0.72,
        )
        fig_scatter.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig_scatter, width="stretch")

        corr_data = df[numeric_cols].corr(numeric_only=True)
        if not corr_data.empty and corr_data.shape[0] >= 2:
            heatmap = go.Figure(
                data=go.Heatmap(
                    z=corr_data.values,
                    x=corr_data.columns,
                    y=corr_data.index,
                    zmid=0,
                    colorscale="RdBu",
                )
            )
            heatmap.update_layout(title="Matriz de correlacao", template="plotly_white")
            st.plotly_chart(heatmap, width="stretch")
        else:
            st.info("Sao necessarias pelo menos 2 colunas numericas com dados validos para a matriz de correlacao.")

        box_col = st.selectbox("Checagem de outlier (boxplot)", options=numeric_cols)
        fig_box = px.box(df, y=box_col, points="outliers", title=f"Perfil de outlier: {box_col}")
        fig_box.update_layout(template="plotly_white")
        st.plotly_chart(fig_box, width="stretch")
    elif numeric_cols:
        st.info("Sao necessarias pelo menos 2 colunas numericas para o grafico de dispersao e matriz de correlacao.")


def render_cleaning_section(
    df_original: pd.DataFrame,
    selected_file: str,
    analysis: dict,
    quality_score: float,
    quality_level: str,
) -> None:
    st.markdown("### Configuracao de tratamento")

    has_missing = analysis["summary"]["missing_cells"] > 0
    has_dups = analysis["summary"]["duplicate_rows"] > 0
    has_placeholders = not analysis["placeholder_table"].empty
    has_type_issues = not analysis["type_suggestions"].empty

    if has_missing or has_dups or has_placeholders or has_type_issues:
        if st.button("Aplicar todas as recomendacoes", type="primary"):
            rec_options: dict = {
                "trim_strings": True,
                "replace_missing_tokens": has_placeholders,
                "normalize_column_names": True,
                "drop_duplicates": has_dups,
                "drop_high_missing_columns_pct": 70.0 if has_missing else 100.0,
                "fill_numeric": "median" if has_missing else "none",
                "fill_categorical": "mode" if has_missing else "none",
            }
            rec_df, _ = clean_dataset(df_original, **rec_options)
            st.session_state["cleaned_df"] = rec_df
            st.session_state["show_bi"] = True
            st.success("Recomendacoes aplicadas. Veja o resultado em Insights BI.")
        st.markdown("---")

    c1, c2, c3 = st.columns(3)
    trim_strings = c1.toggle(
        "Remover espacos em branco",
        value=True,
        help="Remove espacos no inicio/fim dos campos de texto.",
    )
    replace_tokens = c2.toggle(
        "Normalizar tokens de nulo",
        value=True,
        help="Converte valores como NA, NULL, -, none em nulos reais.",
    )
    normalize_cols = c3.toggle(
        "Normalizar nomes de colunas",
        value=True,
        help="Transforma nomes para lowercase_snake_case.",
    )

    c4, c5, c6 = st.columns(3)
    drop_dups = c4.toggle(
        "Remover linhas duplicadas",
        value=True,
        help="Remove registros duplicados exatos.",
    )

    numeric_fill_label = c5.selectbox(
        "Estrategia para nulos numericos",
        ["Mediana (recomendado)", "Media", "Zero", "Nao preencher"],
        index=0,
        help="Como preencher valores nulos numericos.",
    )
    cat_fill_label = c6.selectbox(
        "Estrategia para nulos categoricos",
        ["Moda (recomendado)", "Unknown", "Nao preencher"],
        index=0,
        help="Como preencher valores nulos de texto/categoria.",
    )

    numeric_fill_map = {
        "Mediana (recomendado)": "median",
        "Media": "mean",
        "Zero": "zero",
        "Nao preencher": "none",
    }
    cat_fill_map = {
        "Moda (recomendado)": "mode",
        "Unknown": "unknown",
        "Nao preencher": "none",
    }

    missing_threshold = st.slider(
        "Remover colunas acima do limite de faltantes (%)",
        min_value=0,
        max_value=100,
        value=100,
        step=5,
        help="Colunas com taxa de faltantes acima desse valor serao removidas.",
    )

    with st.spinner("Preparando previa do dataset tratado..."):
        cleaned_preview, report_preview = clean_dataset(
            df_original,
            trim_strings=trim_strings,
            replace_missing_tokens=replace_tokens,
            normalize_column_names=normalize_cols,
            drop_duplicates=drop_dups,
            drop_high_missing_columns_pct=float(missing_threshold),
            fill_numeric=numeric_fill_map[numeric_fill_label],
            fill_categorical=cat_fill_map[cat_fill_label],
        )

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Linhas antes", f"{report_preview['rows_before']:,}")
    s2.metric("Linhas depois", f"{report_preview['rows_after']:,}")
    s3.metric("Colunas antes", f"{report_preview['columns_before']:,}")
    s4.metric("Colunas depois", f"{report_preview['columns_after']:,}")

    # Diff colorido: celulas alteradas marcadas com ✱
    with st.expander("Comparacao antes / depois (✱ = valor alterado)", expanded=True):
        diff_df = _diff_dataframe(df_original, cleaned_preview)
        st.dataframe(diff_df, width="stretch")

    # Botoes de download
    csv_buffer = io.StringIO()
    cleaned_preview.to_csv(csv_buffer, index=False)

    excel_buffer = io.BytesIO()
    try:
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            cleaned_preview.to_excel(writer, sheet_name="Dados tratados", index=False)
            if not analysis["missing_table"].empty:
                analysis["missing_table"].to_excel(writer, sheet_name="Faltantes", index=False)
            if not analysis["outlier_table"].empty:
                analysis["outlier_table"].to_excel(writer, sheet_name="Outliers", index=False)
        excel_available = True
    except Exception:
        excel_available = False

    b1, b2, b3 = st.columns(3)
    with b1:
        st.download_button(
            label="Baixar CSV tratado",
            data=csv_buffer.getvalue().encode("utf-8"),
            file_name=f"cleaned_{selected_file}",
            mime="text/csv",
            width="stretch",
            help="Executa as regras escolhidas e baixa o resultado tratado.",
        )

    with b2:
        if excel_available:
            st.download_button(
                label="Baixar Excel (.xlsx)",
                data=excel_buffer.getvalue(),
                file_name=f"cleaned_{selected_file.replace('.csv', '')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
                help="Exporta dados tratados + abas de qualidade em Excel.",
            )
        else:
            st.info("Instale openpyxl para habilitar export Excel: `pip install openpyxl`")

    with b3:
        open_bi = st.button(
            "Abrir insights BI",
            width="stretch",
            type="primary",
            help="Salva o dataset tratado na sessao e abre o fluxo de insights.",
        )
        if open_bi:
            st.session_state["cleaned_df"] = cleaned_preview
            st.session_state["cleaning_report"] = report_preview
            st.session_state["show_bi"] = True

    with st.expander("Relatorio tecnico"):
        st.json(report_preview)
        report_payload = {
            "generated_at": datetime.now(UTC).isoformat(),
            "dataset": selected_file,
            "quality_score": quality_score,
            "quality_level": quality_level,
            "summary": analysis["summary"],
            "treatment_report": report_preview,
        }
        st.download_button(
            label="Baixar relatorio JSON",
            data=json.dumps(report_payload, ensure_ascii=True, indent=2).encode("utf-8"),
            file_name=f"report_{selected_file}.json",
            mime="application/json",
            width="stretch",
        )
