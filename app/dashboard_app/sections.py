from __future__ import annotations

import io
import json
from datetime import UTC, datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.dashboard_app.styles import badge, metric_card
from src.data.cleaning import clean_dataset


def render_overview(df: pd.DataFrame, analysis: dict, quality_score: float, quality_level: str) -> None:
    top = st.columns(6)
    with top[0]:
        metric_card("Score de qualidade", f"{quality_score}/100")
    with top[1]:
        metric_card("Nivel", quality_level)
    with top[2]:
        metric_card("Linhas", f"{analysis['summary']['rows']:,}")
    with top[3]:
        metric_card("Colunas", f"{analysis['summary']['columns']:,}")
    with top[4]:
        metric_card("Celulas faltantes", f"{analysis['summary']['missing_cells']:,}")
    with top[5]:
        metric_card("Duplicadas", f"{analysis['summary']['duplicate_rows']:,}")

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

    with right:
        st.markdown("#### Sugestoes de tipo")
        if analysis["type_suggestions"].empty:
            st.success("Nenhuma inconsistencia forte de tipo detectada.")
        else:
            st.dataframe(analysis["type_suggestions"], width="stretch")

        st.markdown("#### Outliers (IQR)")
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

        corr = df[numeric_cols].corr(numeric_only=True)
        heatmap = go.Figure(
            data=go.Heatmap(
                z=corr.values,
                x=corr.columns,
                y=corr.index,
                zmid=0,
                colorscale="RdBu",
            )
        )
        heatmap.update_layout(title="Matriz de correlacao", template="plotly_white")
        st.plotly_chart(heatmap, width="stretch")

        box_col = st.selectbox("Checagem de outlier (boxplot)", options=numeric_cols)
        fig_box = px.box(df, y=box_col, points="outliers", title=f"Perfil de outlier: {box_col}")
        fig_box.update_layout(template="plotly_white")
        st.plotly_chart(fig_box, width="stretch")


def render_cleaning_section(
    df_original: pd.DataFrame,
    selected_file: str,
    analysis: dict,
    quality_score: float,
    quality_level: str,
) -> None:
    st.markdown("### Configuracao de tratamento")

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

    st.dataframe(cleaned_preview.head(50), width="stretch")

    csv_buffer = io.StringIO()
    cleaned_preview.to_csv(csv_buffer, index=False)

    b1, b2 = st.columns(2)
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
