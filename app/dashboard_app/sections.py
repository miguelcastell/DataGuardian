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

        st.markdown("#### Cardinalidade suspeita")
        if not analysis.get("cardinality_table", pd.DataFrame()).empty:
            st.dataframe(analysis["cardinality_table"], width="stretch")
        else:
            st.info("Nenhuma coluna com cardinalidade suspeita.")

        st.markdown("#### Quase-duplicatas textuais")
        if not analysis.get("fuzzy_table", pd.DataFrame()).empty:
            st.dataframe(analysis["fuzzy_table"], width="stretch")
        else:
            st.info("Nenhuma quase-duplicata textual detectada."
                    " (Instale rapidfuzz para habilitar: `pip install rapidfuzz`)")

    st.markdown("#### Dependencias funcionais entre colunas")
    fd = analysis.get("functional_deps", pd.DataFrame())
    if not fd.empty:
        st.dataframe(fd, width="stretch")
        st.caption(
            "Uma coluna determinante mapeia cada valor para exatamente um valor da coluna dependente "
            "(ex: cidade → estado). Colunas dependentes podem ser redundantes em modelos."
        )
    else:
        st.info("Nenhuma dependencia funcional detectada.")

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


def _fmt_number(val: float) -> str:
    """Formata um numero para exibicao em KPI card (K / M para grandes valores)."""
    if abs(val) >= 1_000_000:
        return f"{val / 1_000_000:.2f}M"
    if abs(val) >= 1_000:
        return f"{val / 1_000:.1f}K"
    if val == int(val):
        return f"{int(val):,}"
    return f"{val:,.2f}"


def _analysis_numeric_cols(df: pd.DataFrame) -> list[str]:
    """Numericas com variancia real — exclui IDs (>95% unicos) e constantes."""
    n = max(len(df), 1)
    result = []
    for col in df.select_dtypes(include=["number"]).columns:
        s = df[col].dropna()
        if s.empty or s.std() == 0:
            continue
        if s.nunique() / n > 0.95:
            continue
        result.append(col)
    return result


def _grouping_cats(df: pd.DataFrame) -> list[str]:
    """Categoricas com 2–25 valores unicos — boas para agrupar."""
    return [
        col for col in df.select_dtypes(include=["object", "string"]).columns
        if 2 <= int(df[col].nunique(dropna=True)) <= 25
    ]


def _detect_date_cols(df: pd.DataFrame, analysis: dict | None) -> list[str]:
    """Detecta colunas de data por sugestao de tipo ou por nome heuristico."""
    found: list[str] = []
    if analysis:
        ts = analysis.get("type_suggestions", pd.DataFrame())
        if not ts.empty:
            found = ts.loc[ts["suggested_type"] == "datetime", "column"].tolist()
    keywords = {"data", "date", "dt", "mes", "ano", "year", "month", "dia", "day", "periodo", "cadastro"}
    for col in df.columns:
        if col in found:
            continue
        if any(kw in col.lower() for kw in keywords):
            try:
                pd.to_datetime(df[col].dropna().astype(str).head(20), format="mixed")
                found.append(col)
            except Exception:
                pass
    return found


def render_visual_insights(
    df: pd.DataFrame,
    analysis: dict | None = None,
    quality_score: float | None = None,
    quality_level: str | None = None,
) -> None:
    an_nums = _analysis_numeric_cols(df)
    grp_cats = _grouping_cats(df)
    all_nums = df.select_dtypes(include=["number"]).columns.tolist()
    all_cats = df.select_dtypes(include=["object", "string", "category"]).columns.tolist()
    date_cols = _detect_date_cols(df, analysis)

    st.markdown("### Insights BI")

    if not all_nums and not all_cats:
        st.info("Sem colunas numericas ou categoricas para visualizar.")
        return

    # ── KPI cards — metricas dos dados ───────────────────────────────────────
    kpi_cols = an_nums[:6] if an_nums else all_nums[:6]
    if kpi_cols:
        cols_per_row = min(len(kpi_cols), 4)
        rows = [kpi_cols[i:i + cols_per_row] for i in range(0, len(kpi_cols), cols_per_row)]
        for row_cols in rows:
            grid = st.columns(len(row_cols))
            for gc, col in zip(grid, row_cols):
                s = df[col].dropna()
                if s.empty:
                    continue
                mean_val = float(s.mean())
                median_val = float(s.median())
                gc.metric(
                    label=col,
                    value=_fmt_number(mean_val),
                    delta=f"mediana {_fmt_number(median_val)}",
                    delta_color="off",
                    help=f"min {_fmt_number(float(s.min()))} · max {_fmt_number(float(s.max()))} · desvio {_fmt_number(float(s.std()))}",
                )
        st.markdown("")

    # ── Agregacao por categoria ────────────────────────────────────────────────
    if grp_cats and an_nums:
        st.markdown("#### Agregacao por categoria")
        a1, a2, a3 = st.columns(3)
        agg_cat = a1.selectbox("Agrupar por", options=grp_cats, key="bi_agg_cat")
        agg_num = a2.selectbox("Metrica", options=an_nums, key="bi_agg_num")
        agg_fn_label = a3.selectbox(
            "Funcao",
            options=["Media", "Soma", "Contagem", "Mediana", "Maximo", "Minimo"],
            key="bi_agg_fn",
        )
        agg_fn_map = {
            "Media": "mean", "Soma": "sum", "Contagem": "count",
            "Mediana": "median", "Maximo": "max", "Minimo": "min",
        }
        agg_result = (
            df.groupby(agg_cat, dropna=True)[agg_num]
            .agg(agg_fn_map[agg_fn_label])
            .reset_index()
            .sort_values(agg_num, ascending=True)
        )
        agg_result.columns = [agg_cat, "valor"]
        fig_agg = px.bar(
            agg_result,
            x="valor",
            y=agg_cat,
            orientation="h",
            title=f"{agg_fn_label} de {agg_num} por {agg_cat}",
            color="valor",
            color_continuous_scale="Blues",
            labels={"valor": f"{agg_fn_label} ({agg_num})", agg_cat: ""},
            text=agg_result["valor"].apply(_fmt_number),
        )
        fig_agg.update_traces(textposition="outside")
        fig_agg.update_layout(
            template="plotly_white",
            margin=dict(l=10, r=60, t=50, b=10),
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_agg, width="stretch")

    # ── Distribuicao + Estatisticas descritivas ───────────────────────────────
    if all_nums:
        st.markdown("#### Distribuicao e estatisticas")
        d1, d2 = st.columns([3, 2])
        with d1:
            dist_col = st.selectbox("Coluna", options=all_nums, key="bi_dist")
            fig_hist = px.histogram(
                df,
                x=dist_col,
                nbins=30,
                marginal="box",
                title=f"Distribuicao: {dist_col}",
                color_discrete_sequence=["#155eef"],
            )
            fig_hist.update_layout(
                template="plotly_white",
                margin=dict(l=10, r=10, t=50, b=10),
                showlegend=False,
            )
            st.plotly_chart(fig_hist, width="stretch")

        with d2:
            s = df[dist_col].dropna()
            desc = {
                "Contagem": f"{len(s):,}",
                "Minimo": _fmt_number(float(s.min())),
                "Q1 (25%)": _fmt_number(float(s.quantile(0.25))),
                "Mediana": _fmt_number(float(s.median())),
                "Media": _fmt_number(float(s.mean())),
                "Q3 (75%)": _fmt_number(float(s.quantile(0.75))),
                "Maximo": _fmt_number(float(s.max())),
                "Desvio padrao": _fmt_number(float(s.std())),
                "Assimetria": f"{float(s.skew()):.3f}",
                "Curtose": f"{float(s.kurt()):.3f}",
            }
            desc_df = pd.DataFrame(
                {"Estatistica": list(desc.keys()), "Valor": list(desc.values())}
            )
            st.markdown(f"**Estatisticas: {dist_col}**")
            st.dataframe(desc_df, hide_index=True, width="stretch")

    # ── Serie temporal ────────────────────────────────────────────────────────
    if date_cols and all_nums:
        st.markdown("#### Serie temporal")
        t1, t2, t3 = st.columns(3)
        date_col = t1.selectbox("Coluna de data", options=date_cols, key="bi_date")
        ts_num = t2.selectbox("Metrica", options=all_nums, key="bi_ts_num")
        ts_agg_label = t3.selectbox(
            "Agregacao",
            options=["Media", "Soma", "Contagem"],
            key="bi_ts_agg",
        )
        ts_agg_map = {"Media": "mean", "Soma": "sum", "Contagem": "count"}

        try:
            ts_df = df[[date_col, ts_num]].copy()
            ts_df[date_col] = pd.to_datetime(ts_df[date_col], errors="coerce", format="mixed")
            ts_df = ts_df.dropna(subset=[date_col])
            date_range = (ts_df[date_col].max() - ts_df[date_col].min()).days
            freq = "ME" if date_range > 60 else ("W" if date_range > 14 else "D")
            ts_agg = (
                ts_df.set_index(date_col)[ts_num]
                .resample(freq)
                .agg(ts_agg_map[ts_agg_label])
                .reset_index()
            )
            fig_ts = px.line(
                ts_agg,
                x=date_col,
                y=ts_num,
                title=f"{ts_agg_label} de {ts_num} ao longo do tempo",
                markers=True,
                color_discrete_sequence=["#155eef"],
            )
            fig_ts.update_layout(
                template="plotly_white",
                margin=dict(l=10, r=10, t=50, b=10),
            )
            st.plotly_chart(fig_ts, width="stretch")
        except Exception:
            st.info("Nao foi possivel renderizar a serie temporal com a coluna selecionada.")

    # ── Dispersao + Correlacao ────────────────────────────────────────────────
    if len(all_nums) >= 2:
        st.markdown("#### Relacoes entre variaveis")
        s1, s2, s3 = st.columns(3)
        x_col = s1.selectbox("Eixo X", options=all_nums, key="bi_sx")
        y_col = s2.selectbox(
            "Eixo Y",
            options=all_nums,
            index=min(1, len(all_nums) - 1),
            key="bi_sy",
        )
        color_col = s3.selectbox(
            "Colorir por",
            options=["(nenhum)"] + grp_cats,
            key="bi_sc",
        )
        fig_scatter = px.scatter(
            df,
            x=x_col,
            y=y_col,
            color=None if color_col == "(nenhum)" else color_col,
            title=f"Dispersao: {x_col} vs {y_col}",
            opacity=0.75,
        )
        fig_scatter.update_layout(
            template="plotly_white",
            margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(fig_scatter, width="stretch")

        corr_data = df[an_nums if len(an_nums) >= 2 else all_nums].corr(numeric_only=True)
        if not corr_data.empty and corr_data.shape[0] >= 2:
            text_vals = [[f"{v:.2f}" for v in row] for row in corr_data.values]
            fig_corr = go.Figure(
                data=go.Heatmap(
                    z=corr_data.values,
                    x=corr_data.columns.tolist(),
                    y=corr_data.index.tolist(),
                    zmid=0,
                    colorscale="RdBu",
                    text=text_vals,
                    texttemplate="%{text}",
                    textfont={"size": 11},
                )
            )
            fig_corr.update_layout(
                title="Matriz de correlacao",
                template="plotly_white",
                margin=dict(l=10, r=10, t=50, b=10),
                height=max(350, corr_data.shape[0] * 55),
            )
            st.plotly_chart(fig_corr, width="stretch")

    # ── Top / Bottom N ────────────────────────────────────────────────────────
    if an_nums:
        st.markdown("#### Ranking — Top / Bottom")
        r1, r2, r3 = st.columns(3)
        rank_col = r1.selectbox("Ordenar por", options=an_nums, key="bi_rank_col")
        rank_n = r2.slider("Quantidade", min_value=3, max_value=min(20, len(df)), value=5, key="bi_rank_n")
        rank_order = r3.radio("Ordem", options=["Maiores", "Menores"], horizontal=True, key="bi_rank_ord")

        ascending = rank_order == "Menores"
        ranked = df.sort_values(rank_col, ascending=ascending).head(rank_n)
        display_cols = (
            [rank_col]
            + [c for c in grp_cats[:3] if c in df.columns]
            + [c for c in an_nums[:3] if c != rank_col and c in df.columns]
        )
        display_cols = list(dict.fromkeys(display_cols))
        st.dataframe(ranked[display_cols].reset_index(drop=True), width="stretch")


def render_drift_section(df_main: pd.DataFrame, df_ref: pd.DataFrame) -> None:
    from src.data.drift import analyze_drift

    st.markdown("### Analise de Drift")
    st.caption(
        "Compara distribuicoes do dataset ativo com o dataset de referencia. "
        "KS test (p < 0.05) para numericas; PSI para categoricas (>= 0.1 moderado, >= 0.2 significativo)."
    )

    with st.spinner("Calculando drift..."):
        drift = analyze_drift(df_ref, df_main)

    summary = drift["summary"]
    schema = drift["schema_diff"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Linhas — referencia", f"{summary['linhas_ref']:,}")
    c2.metric("Linhas — atual", f"{summary['linhas_atual']:,}")
    c3.metric("Drift numerico", summary["colunas_com_drift_numerico"])
    c4.metric("Drift categorico", summary["colunas_com_drift_categorico"])

    if schema["colunas_adicionadas"] or schema["colunas_removidas"]:
        with st.expander("Mudancas de schema", expanded=True):
            if schema["colunas_adicionadas"]:
                st.success("Adicionadas: " + ", ".join(schema["colunas_adicionadas"]))
            if schema["colunas_removidas"]:
                st.error("Removidas: " + ", ".join(schema["colunas_removidas"]))
    else:
        st.success(f"Schemas identicos — {schema['colunas_em_comum']} colunas em comum.")

    # ── Drift numerico ────────────────────────────────────────────────────────
    st.markdown("#### Drift numerico")
    nd = drift["numeric_drift"]
    if nd.empty:
        st.info("Nenhuma coluna numerica em comum para comparar.")
    else:
        if not summary["scipy_disponivel"]:
            st.warning(
                "scipy nao instalado — deteccao simplificada por delta de media. "
                "`pip install scipy` para o KS test completo."
            )
        drifted_num = nd[nd["drift_detectado"]].sort_values(
            "ks_estatistica", ascending=False, na_position="last"
        )
        stable_num = nd[~nd["drift_detectado"]]

        if not drifted_num.empty:
            st.error(f"{len(drifted_num)} coluna(s) com drift detectado:")
            st.dataframe(drifted_num, width="stretch")

            top_col = str(drifted_num.iloc[0]["coluna"])
            if top_col in df_ref.columns and top_col in df_main.columns:
                combined = pd.concat(
                    [
                        df_ref[[top_col]].assign(fonte="Referencia"),
                        df_main[[top_col]].assign(fonte="Atual"),
                    ],
                    ignore_index=True,
                )
                fig = px.histogram(
                    combined,
                    x=top_col,
                    color="fonte",
                    barmode="overlay",
                    opacity=0.7,
                    title=f"Distribuicao comparada: {top_col}",
                    color_discrete_map={"Referencia": "#155eef", "Atual": "#ef4444"},
                )
                fig.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=50, b=10))
                st.plotly_chart(fig, width="stretch")
        else:
            st.success("Nenhuma coluna numerica com drift detectado.")

        if not stable_num.empty:
            with st.expander(f"{len(stable_num)} coluna(s) estaveis"):
                st.dataframe(stable_num, width="stretch")

    # ── Drift categorico ──────────────────────────────────────────────────────
    st.markdown("#### Drift categorico (PSI)")
    cd = drift["categorical_drift"]
    if cd.empty:
        st.info("Nenhuma coluna categorica em comum com cardinalidade adequada (2–50 valores).")
    else:
        drifted_cat = cd[cd["drift_detectado"]].sort_values("psi", ascending=False)
        stable_cat = cd[~cd["drift_detectado"]]

        if not drifted_cat.empty:
            st.error(f"{len(drifted_cat)} coluna(s) com drift categorico:")
            st.dataframe(drifted_cat, width="stretch")

            top_cat = str(drifted_cat.iloc[0]["coluna"])
            if top_cat in df_ref.columns and top_cat in df_main.columns:
                freq_r = (
                    df_ref[top_cat].astype(str)
                    .value_counts(normalize=True)
                    .head(12)
                    .reset_index()
                    .rename(columns={top_cat: "categoria", "proportion": "frequencia",
                                     "count": "frequencia"})
                )
                freq_r.columns = ["categoria", "frequencia"]
                freq_r["fonte"] = "Referencia"

                freq_n = (
                    df_main[top_cat].astype(str)
                    .value_counts(normalize=True)
                    .head(12)
                    .reset_index()
                    .rename(columns={top_cat: "categoria", "proportion": "frequencia",
                                     "count": "frequencia"})
                )
                freq_n.columns = ["categoria", "frequencia"]
                freq_n["fonte"] = "Atual"

                combined_cat = pd.concat([freq_r, freq_n], ignore_index=True)
                fig_cat = px.bar(
                    combined_cat,
                    x="categoria",
                    y="frequencia",
                    color="fonte",
                    barmode="group",
                    title=f"Distribuicao categorica: {top_cat}",
                    color_discrete_map={"Referencia": "#155eef", "Atual": "#ef4444"},
                )
                fig_cat.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=50, b=10))
                st.plotly_chart(fig_cat, width="stretch")
        else:
            st.success("Nenhuma coluna categorica com drift significativo (PSI < 0.1).")

        if not stable_cat.empty:
            with st.expander(f"{len(stable_cat)} coluna(s) estaveis"):
                st.dataframe(stable_cat, width="stretch")


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
                "outlier_treatment": "cap" if not analysis["outlier_table"].empty else "none",
                "outlier_method": "iqr",
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

    st.markdown("#### Tratamento de outliers")
    oc1, oc2 = st.columns(2)
    outlier_treatment_label = oc1.selectbox(
        "Acao para outliers",
        ["Nenhuma", "Capping (limitar pelos percentis)", "Remover linhas"],
        index=0,
        help="Capping aplica winsorization pelos limites IQR ou Z-score. Remover exclui as linhas.",
    )
    outlier_method_label = oc2.selectbox(
        "Metodo de deteccao",
        ["IQR (1.5×IQR)", "Z-score (|z| > 3)"],
        index=0,
        help="Criterio para identificar outliers.",
    )
    outlier_treatment_map = {
        "Nenhuma": "none",
        "Capping (limitar pelos percentis)": "cap",
        "Remover linhas": "remove",
    }
    outlier_method_map = {
        "IQR (1.5×IQR)": "iqr",
        "Z-score (|z| > 3)": "zscore",
    }

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
            outlier_treatment=outlier_treatment_map[outlier_treatment_label],
            outlier_method=outlier_method_map[outlier_method_label],
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
