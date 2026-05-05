from __future__ import annotations

import pandas as pd
import streamlit as st

from app.dashboard_app.data_io import read_uploaded_csv
from app.dashboard_app.scoring import DOMAIN_PRESETS, build_prioritized_issues, compute_quality_score
from app.dashboard_app.sections import (
    render_alerts,
    render_cleaning_section,
    render_drift_section,
    render_overview,
    render_quality_issues,
    render_visual_insights,
)
from app.dashboard_app.styles import apply_design_system, get_asset_data_uri, render_hero, render_stepper
from src.data.quality import analyze_dataset


def run_dashboard() -> None:
    st.set_page_config(
        page_title="Data Guardian",
        page_icon="DG",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    apply_design_system()

    sidebar_logo = get_asset_data_uri("logo-horizontal.png")

    if "main_section" not in st.session_state:
        st.session_state["main_section"] = "Painel"

    with st.sidebar:
        if sidebar_logo:
            st.markdown(
                f"<div class='dg-sidebar-brand'><img class='dg-sidebar-logo' src='{sidebar_logo}' alt='Data Guardian' /></div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown("<div class='dg-sidebar-brand'>DataGuardian</div>", unsafe_allow_html=True)
        st.markdown("### Upload de dataset")
        uploaded_files = st.file_uploader(
            "Adicione um ou mais arquivos CSV",
            type=["csv"],
            accept_multiple_files=True,
            help="Somente CSV. Arquivos grandes podem demorar alguns segundos para perfilamento.",
        )

    if not uploaded_files:
        render_hero()
        st.info("Envie pelo menos um CSV na barra lateral para iniciar a analise.")
        st.markdown(
            """
            <div class='dg-card' style='margin-top:8px;'>
              <div class='dg-card-label'>Estado inicial</div>
              <div style='margin-top:8px;color:#475467;'>
                Fluxo esperado: upload do arquivo &rarr; inspecionar qualidade &rarr; configurar tratamento &rarr; exportar dados tratados &rarr; explorar insights BI.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    with st.spinner("Carregando datasets..."):
        datasets: dict[str, pd.DataFrame] = {}
        file_metas: dict[str, dict[str, str]] = {}
        for uploaded in uploaded_files:
            file_bytes = uploaded.getvalue()
            df, err, meta = read_uploaded_csv(file_bytes, uploaded.name)
            if err:
                st.error(f"**{uploaded.name}**: {err}")
            else:
                datasets[uploaded.name] = df
                file_metas[uploaded.name] = meta

    if not datasets:
        render_hero()
        st.warning("Nenhum arquivo foi carregado com sucesso. Verifique os arquivos enviados.")
        return

    drift_ref_df: pd.DataFrame | None = None

    with st.sidebar:
        selected_file = st.selectbox("Dataset ativo", options=list(datasets.keys()))

        active_meta = file_metas.get(selected_file, {})
        if active_meta:
            st.caption(
                f"Codificacao: `{active_meta.get('encoding', '?')}` "
                f"· Delimitador: `{active_meta.get('delimiter', '?')}`"
            )

        st.markdown("---")
        st.markdown("### Configuracao de score")
        domain_preset = st.selectbox(
            "Preset de dominio",
            options=list(DOMAIN_PRESETS.keys()),
            help="Ajusta os pesos do score de qualidade para o contexto dos seus dados.",
        )
        selected_weights = DOMAIN_PRESETS[domain_preset]

        st.markdown("---")
        st.markdown("### Comparacao de drift")
        drift_uploaded = st.file_uploader(
            "Dataset de referencia (opcional)",
            type=["csv"],
            key="drift_reference",
            help=(
                "Carregue um CSV de referencia (ex: mes anterior) para comparar "
                "distribuicoes e detectar drift entre os dois datasets."
            ),
        )

    if drift_uploaded is not None:
        drift_bytes = drift_uploaded.getvalue()
        drift_ref_df, drift_err, _ = read_uploaded_csv(drift_bytes, drift_uploaded.name)
        if drift_err:
            st.warning(f"Arquivo de referencia para drift: {drift_err}")
            drift_ref_df = None

    df_original = datasets[selected_file]

    with st.spinner("Analisando qualidade dos dados..."):
        analysis = analyze_dataset(df_original)

    if "error" in analysis:
        render_hero()
        st.error(analysis["error"])
        return

    quality_score, quality_level, score_breakdown = compute_quality_score(analysis, custom_weights=selected_weights)
    issues_df = build_prioritized_issues(analysis)

    render_hero(
        dataset_name=selected_file,
        quality_score=quality_score,
        quality_level=quality_level,
        rows=analysis["summary"]["rows"],
        cols=analysis["summary"]["columns"],
    )

    extra_sections = ["Drift"] if drift_ref_df is not None else []
    section = render_stepper(
        st.session_state.get("main_section", "Painel"),
        extra_sections=extra_sections,
    )
    st.session_state["main_section"] = section

    if section == "Painel":
        tabs = st.tabs(["Visao geral", "Problemas de qualidade", "Alertas"])
        with tabs[0]:
            render_overview(df_original, analysis, quality_score, quality_level, score_breakdown)
        with tabs[1]:
            render_quality_issues(analysis, issues_df)
        with tabs[2]:
            render_alerts(analysis, quality_score)

    if section == "Tratamento":
        render_cleaning_section(df_original, selected_file, analysis, quality_score, quality_level)

    if section == "Insights BI":
        if not st.session_state.get("show_bi"):
            st.warning("Abra os insights BI a partir de Tratamento para carregar primeiro os dados tratados.")
        source_df = st.session_state.get("cleaned_df", df_original)
        render_visual_insights(
            source_df,
            analysis=analysis,
            quality_score=quality_score,
            quality_level=quality_level,
        )

    if section == "Drift" and drift_ref_df is not None:
        render_drift_section(df_original, drift_ref_df)
