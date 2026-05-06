from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

# Paleta semantica por nivel de qualidade
QUALITY_PALETTE = {
    "Excelente": {
        "color": "#05603a",
        "bg": "#ecfdf3",
        "border": "#a9efc5",
        "accent": "#12b76a",
    },
    "Bom": {
        "color": "#107569",
        "bg": "#f0fdf9",
        "border": "#99f6e0",
        "accent": "#14b8a6",
    },
    "Atencao": {
        "color": "#92400e",
        "bg": "#fffbeb",
        "border": "#fcd34d",
        "accent": "#f59e0b",
    },
    "Critico": {
        "color": "#7f1d1d",
        "bg": "#fff1f2",
        "border": "#fecaca",
        "accent": "#ef4444",
    },
}


def apply_design_system() -> None:
    st.markdown(
        """
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

          :root {
            --bg: #f4f6fb;
            --surface: #ffffff;
            --surface-soft: #f8fafc;
            --primary: #155eef;
            --primary-strong: #0040c9;
            --secondary: #08768f;
            --text: #0f172a;
            --text-muted: #475467;
            --border: #d0d5dd;
            --shadow: 0 1px 2px rgba(16,24,40,.06), 0 1px 3px rgba(16,24,40,.10);
            --shadow-md: 0 4px 6px -1px rgba(16,24,40,.07), 0 2px 4px -1px rgba(16,24,40,.06);
            --success: #067647;
            --warning: #b54708;
            --error:   #b42318;
            --radius-sm: 8px;
            --radius-md: 12px;
            --radius-lg: 16px;
            --space-1: 8px;
            --space-2: 16px;
            --space-3: 24px;
            --space-4: 32px;
          }

          .stApp {
            background: var(--bg);
            color: var(--text);
            font-family: 'Manrope', sans-serif;
          }

          html, body,
          [data-testid="stAppViewContainer"],
          [data-testid="stMain"],
          section.main {
            background: var(--bg) !important;
            color: var(--text) !important;
          }

          [data-testid="stHeader"],
          header[data-testid="stHeader"] {
            background: var(--bg) !important;
            border-bottom: 1px solid var(--border);
          }

          [data-testid="stToolbar"],
          [data-testid="stToolbar"] * { color: var(--text) !important; }

          .block-container {
            max-width: 1400px;
            padding-top: 0;
            padding-bottom: var(--space-3);
          }

          /* ── Hero section ── */
          .dg-hero {
            background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 55%, #155eef 100%);
            color: #ffffff;
            border-radius: var(--radius-lg);
            padding: 36px 32px 24px;
            margin-bottom: 24px;
            position: relative;
            overflow: visible;
          }
          .dg-hero::before {
            content: '';
            position: absolute;
            top: -40px; right: -40px;
            width: 200px; height: 200px;
            border-radius: 50%;
            background: rgba(255,255,255,.04);
            pointer-events: none;
          }
          .dg-hero::after {
            content: '';
            position: absolute;
            bottom: -60px; left: 30%;
            width: 300px; height: 300px;
            border-radius: 50%;
            background: rgba(255,255,255,.03);
            pointer-events: none;
          }
          .dg-hero-top {
            display: flex;
            align-items: center;
            justify-content: flex-start;
            min-height: 72px;
            margin-bottom: 10px;
            padding-left: 12px;
          }
          .dg-hero-logo {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            background: transparent;
            border: none;
            padding: 0;
          }
          .dg-hero-logo img {
            width: min(54vw, 240px);
            max-width: 240px;
            max-height: 80px;
            height: auto;
            display: block;
            object-fit: contain;
            margin-top: 0;
            filter: drop-shadow(0 6px 16px rgba(0,0,0,.18));
          }
          .dg-logo-pill {
            background: rgba(255,255,255,.15);
            border: 1px solid rgba(255,255,255,.25);
            border-radius: 999px;
            padding: 6px 14px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.82rem;
            font-weight: 700;
            color: #ffffff;
            letter-spacing: 0.05em;
            backdrop-filter: blur(4px);
          }
          .dg-hero-title {
            margin: 0;
            font-size: 1.9rem;
            font-weight: 800;
            color: #ffffff;
            letter-spacing: -0.025em;
            line-height: 1.15;
          }
          .dg-hero-subtitle {
            color: rgba(255,255,255,.65);
            font-size: 0.9rem;
            margin-top: 4px;
          }
          .dg-hero-status {
            display: flex;
            align-items: center;
            gap: 24px;
            margin-top: 18px;
            flex-wrap: wrap;
          }
          .dg-hero-stat {
            display: flex;
            flex-direction: column;
          }
          .dg-hero-stat-label {
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: rgba(255,255,255,.5);
            font-family: 'JetBrains Mono', monospace;
          }
          .dg-hero-stat-value {
            font-size: 1.1rem;
            font-weight: 700;
            color: #ffffff;
          }
          .dg-hero-badge {
            padding: 4px 12px;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 700;
            border: 1px solid;
            margin-top: 2px;
            display: inline-block;
          }

          /* ── Metric cards ── */
          .dg-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 14px 16px 12px;
            box-shadow: var(--shadow);
            height: 100%;
            position: relative;
            overflow: hidden;
          }
          .dg-card-label {
            font-family: 'JetBrains Mono', monospace;
            text-transform: uppercase;
            font-size: 0.67rem;
            color: var(--text-muted);
            letter-spacing: 0.04em;
          }
          .dg-card-value {
            margin-top: 4px;
            font-size: 1.45rem;
            font-weight: 800;
            color: var(--text);
            line-height: 1.2;
          }
          .dg-card-bar-track {
            margin-top: 10px;
            height: 4px;
            background: #e2e8f0;
            border-radius: 99px;
            overflow: hidden;
          }
          .dg-card-bar-fill {
            height: 100%;
            border-radius: 99px;
            transition: width .4s ease;
          }
          .dg-card-sub {
            margin-top: 4px;
            font-size: 0.72rem;
            color: var(--text-muted);
          }

          /* ── Stepper de fluxo ── */
          .dg-stepper {
            display: flex;
            align-items: center;
            gap: 0;
            margin-bottom: 20px;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 6px;
            box-shadow: var(--shadow);
          }
          .dg-step {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 10px 16px;
            border-radius: 8px;
            cursor: default;
            font-weight: 700;
            font-size: 0.85rem;
            color: var(--text-muted);
            transition: background .2s, color .2s;
            white-space: nowrap;
          }
          .dg-step-active {
            background: #1e3a5f;
            color: #ffffff;
          }
          .dg-step-done {
            color: #12b76a;
          }
          .dg-step-num {
            width: 22px; height: 22px;
            border-radius: 50%;
            background: rgba(0,0,0,.07);
            display: flex; align-items: center; justify-content: center;
            font-size: 0.72rem;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
          }
          .dg-step-active .dg-step-num {
            background: rgba(255,255,255,.2);
            color: #ffffff;
          }
          .dg-step-done .dg-step-num {
            background: #ecfdf3;
            color: #12b76a;
          }
          .dg-step-arrow {
            color: var(--border);
            font-size: 1rem;
            padding: 0 2px;
            flex-shrink: 0;
          }

          /* ── Badges ── */
          .dg-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 700;
            border: 1px solid transparent;
            margin-right: 6px;
          }
          .dg-badge-critical { color: #7a271a; background: #fef3f2; border-color: #fecdca; }
          .dg-badge-warning  { color: #93370d; background: #fffaeb; border-color: #fedf89; }
          .dg-badge-good     { color: #085d3a; background: #ecfdf3; border-color: #abefc6; }

          /* ── Tabs ── */
          .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background: transparent;
          }
          .stTabs [data-baseweb="tab"] {
            height: 42px;
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: 10px;
            color: var(--text);
            font-weight: 700;
            padding: 0 14px;
          }
          .stTabs [aria-selected="true"] {
            background: #e8f0ff !important;
            border-color: #b2ccff !important;
            color: #002266 !important;
          }
          .stTabs [data-baseweb="tab-panel"] {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: var(--space-2);
            margin-top: 10px;
          }

          /* ── Sidebar ── */
          .stSidebar,
          [data-testid="stSidebar"] {
            background: #f8fafc !important;
            border-right: 1px solid var(--border);
          }
          [data-testid="stSidebar"] > div:first-child {
            background: #f8fafc !important;
          }
          [data-testid="stSidebar"] * { color: var(--text) !important; }
          .dg-sidebar-brand {
            font-size: 1.08rem;
            font-weight: 800;
            letter-spacing: -0.015em;
            color: #0f172a !important;
            margin: 4px 0 14px;
          }
          .dg-sidebar-logo {
            display: block;
            width: 100%;
            max-width: 180px;
            height: auto;
          }

          /* ── File uploader ── */
          /* Container externo: sem borda propria (a area dashed ja tem a borda) */
          [data-testid="stFileUploader"] {
            border: none !important;
            box-shadow: none !important;
            background: transparent !important;
          }
          /* Tags de arquivo ja enviados: sem borda extra */
          [data-testid="stFileUploaderFile"],
          [data-testid="stFileUploaderFileData"] {
            border: none !important;
            box-shadow: none !important;
            background: #f8fafc !important;
            border-radius: 8px !important;
          }
          /* Zona de drop */
          [data-testid="stFileUploaderDropzone"] {
            background: #ffffff !important;
            border: 1.5px dashed #98a2b3 !important;
            border-radius: 12px !important;
            padding: 12px !important;
            box-shadow: none !important;
          }
          [data-testid="stFileUploaderDropzoneInstructions"] span,
          [data-testid="stFileUploaderDropzone"] small { color: var(--text) !important; }

          [data-testid="stFileUploaderDropzone"] [data-testid="stBaseButton-secondary"] {
            background: #e8f0ff !important;
            color: #0b3b8a !important;
            border: 1px solid #b2ccff !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
            box-shadow: none !important;
            padding: 6px 14px !important;
            min-height: 38px !important;
            display: inline-flex !important;
            align-items: center !important;
            gap: 8px !important;
          }

          [data-testid="stFileUploaderDropzone"] [data-testid="stBaseButton-secondary"]:hover {
            background: #d9e8ff !important;
            color: #062f75 !important;
            border-color: #93b6ff !important;
          }

          [data-testid="stFileUploaderDropzone"] [data-testid="stBaseButton-secondary"]:focus-visible {
            outline: 3px solid #93c5fd !important;
            outline-offset: 1px !important;
          }

          [data-testid="stFileUploaderDropzone"] [data-testid="stBaseButton-secondary"] p,
          [data-testid="stFileUploaderDropzone"] [data-testid="stBaseButton-secondary"] span,
          [data-testid="stFileUploaderDropzone"] [data-testid="stBaseButton-secondary"] div {
            background: transparent !important;
            border: 0 !important;
            box-shadow: none !important;
            color: inherit !important;
          }

          [data-testid="stFileUploader"] section {
            border: 0 !important;
            box-shadow: none !important;
          }

          [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] + div {
            margin-top: 8px !important;
          }

          [data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] {
            border: 1px solid #d0d5dd !important;
            background: #f8fafc !important;
            border-radius: 10px !important;
          }

          /* Botao "Browse files" */
          [data-testid="stFileUploaderDropzone"] button,
          [data-testid="stFileUploader"] button {
            box-shadow: none !important;
          }

          /* ── Typography (escopo global, NAO hero) ── */
          p, span, label, small, li, h1, h2, h3, h4, h5 { color: var(--text); }

          /* Override: hero sempre usa texto branco, independente da cascata global */
          .dg-hero,
          .dg-hero * { color: #ffffff !important; }
          .dg-hero .dg-hero-subtitle { color: rgba(255,255,255,.9) !important; }
          .dg-hero .dg-hero-stat-label { color: rgba(255,255,255,.76) !important; }
          .dg-hero .dg-logo-pill { color: #ffffff !important; }

          /* ── Inputs ── */
          [data-baseweb="select"] > div,
          [data-testid="stNumberInput"] input,
          [data-testid="stTextInput"] input,
          [data-testid="stTextArea"] textarea {
            background: #ffffff !important;
            border: 1px solid var(--border) !important;
            color: var(--text) !important;
          }
          [role="listbox"] { background: #ffffff !important; border: 1px solid var(--border) !important; }
          [role="option"]  { color: var(--text) !important; }

          /* ── Buttons ── */
          .stButton button,
          [data-testid="stDownloadButton"] button {
            background: var(--primary) !important;
            color: #ffffff !important;
            border: 1px solid var(--primary) !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
            text-shadow: none !important;
          }
          .stButton button *,
          [data-testid="stDownloadButton"] button *,
          .stButton button p,
          [data-testid="stDownloadButton"] button p,
          .stButton button span,
          [data-testid="stDownloadButton"] button span { color: #ffffff !important; fill: #ffffff !important; }
          .stButton button:hover,
          [data-testid="stDownloadButton"] button:hover {
            background: var(--primary-strong) !important;
            color: #ffffff !important;
            border-color: var(--primary-strong) !important;
          }
          .stButton button:focus,
          [data-testid="stDownloadButton"] button:focus,
          .stButton button:focus-visible,
          [data-testid="stDownloadButton"] button:focus-visible {
            color: #ffffff !important;
            outline: 3px solid #93c5fd !important;
            outline-offset: 1px !important;
          }
          .stButton button:disabled,
          [data-testid="stDownloadButton"] button:disabled {
            background: #e2e8f0 !important;
            border-color: #cbd5e1 !important;
            color: #334155 !important;
            opacity: 1 !important;
          }
          .stButton button:disabled *,
          [data-testid="stDownloadButton"] button:disabled * { color: #334155 !important; fill: #334155 !important; }

          /* ── Misc ── */
          .stAlert { border-radius: 12px; border: 1px solid var(--border); }
          [data-testid="stDataFrame"] { border: 1px solid var(--border); border-radius: 10px; }

          /* ═══════════════════════════════════════════════════════
             MOBILE RESPONSIVE
             ═══════════════════════════════════════════════════════ */

          @media (max-width: 768px) {

            /* ── Container ── */
            .block-container,
            [data-testid="stMainBlockContainer"] {
              padding-left: 12px !important;
              padding-right: 12px !important;
              padding-top: 0.25rem !important;
              padding-bottom: 1.5rem !important;
              max-width: 100vw !important;
            }

            /* ── Hero ── */
            .dg-hero {
              padding: 28px 20px 22px !important;
              border-radius: 14px !important;
              margin-bottom: 14px !important;
              overflow: hidden !important;
            }
            .dg-hero::before,
            .dg-hero::after { display: none !important; }
            .dg-hero-top {
              min-height: 56px !important;
              margin-bottom: 8px !important;
              padding-left: 0 !important;
              align-items: flex-start !important;
            }
            .dg-hero-title {
              font-size: 1.6rem !important;
              line-height: 1.2 !important;
            }
            .dg-hero-subtitle {
              font-size: 0.88rem !important;
              margin-top: 4px !important;
            }
            .dg-hero-status {
              display: flex !important;
              flex-wrap: wrap !important;
              gap: 14px 24px !important;
              margin-top: 16px !important;
            }
            .dg-hero-stat {
              min-width: 0 !important;
              flex: 0 0 auto !important;
            }
            .dg-hero-stat-value {
              font-size: 1rem !important;
              white-space: nowrap !important;
              overflow: hidden !important;
              text-overflow: ellipsis !important;
              max-width: 160px !important;
            }
            .dg-hero-stat-label { font-size: 0.65rem !important; }
            .dg-hero-badge { font-size: 0.72rem !important; padding: 3px 10px !important; }

            /* ── Stack todas as colunas Streamlit ── */
            [data-testid="stHorizontalBlock"] {
              flex-direction: column !important;
              gap: 10px !important;
            }
            [data-testid="column"],
            [data-testid="stColumn"] {
              width: 100% !important;
              flex: 1 1 100% !important;
              min-width: 100% !important;
            }

            /* ── Metric cards ── */
            .dg-card { padding: 12px 14px 10px !important; }
            .dg-card-value { font-size: 1.15rem !important; }
            .dg-card-label { font-size: 0.62rem !important; }

            /* ── Botoes — full-width e touch-friendly ── */
            .stButton > button,
            [data-testid="stDownloadButton"] > button,
            [data-testid="stBaseButton-primary"],
            [data-testid="stBaseButton-secondary"] {
              width: 100% !important;
              min-height: 48px !important;
              font-size: 0.9rem !important;
              border-radius: 12px !important;
              -webkit-tap-highlight-color: transparent !important;
            }

            /* ── Tabs ── */
            .stTabs [data-baseweb="tab-list"] {
              overflow-x: auto !important;
              -webkit-overflow-scrolling: touch !important;
              flex-wrap: nowrap !important;
              gap: 4px !important;
              padding-bottom: 4px !important;
              scrollbar-width: none !important;
            }
            .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar { display: none; }
            .stTabs [data-baseweb="tab"] {
              padding: 0 10px !important;
              font-size: 0.78rem !important;
              height: 36px !important;
              white-space: nowrap !important;
              flex-shrink: 0 !important;
            }
            .stTabs [data-baseweb="tab-panel"] {
              padding: 12px 8px !important;
            }

            /* ── Segmented control (stepper) — scrollavel ── */
            [data-testid="stSegmentedControl"] {
              overflow-x: auto !important;
              -webkit-overflow-scrolling: touch !important;
              padding-bottom: 2px !important;
              scrollbar-width: none !important;
            }
            [data-testid="stSegmentedControl"]::-webkit-scrollbar { display: none; }
            [data-testid="stSegmentedControl"] > div {
              min-width: max-content !important;
            }
            [data-testid="stSegmentedControl"] button {
              font-size: 0.8rem !important;
              padding: 6px 12px !important;
              min-height: 38px !important;
              white-space: nowrap !important;
            }

            /* ── DataFrames — scroll horizontal ── */
            [data-testid="stDataFrame"],
            [data-testid="stDataFrame"] > div {
              overflow-x: auto !important;
              max-width: 100% !important;
            }

            /* ── Selects e inputs — evita zoom no iOS ── */
            [data-baseweb="select"] > div,
            [data-testid="stNumberInput"] input,
            [data-testid="stTextInput"] input,
            [data-testid="stTextArea"] textarea {
              min-height: 44px !important;
              font-size: 16px !important;
            }

            /* ── Sidebar ── */
            [data-testid="stSidebar"] {
              max-width: 88vw !important;
            }
            .dg-sidebar-logo { max-width: 150px !important; }

            /* ── Plotly ── */
            .js-plotly-plot,
            .plotly.html-widget {
              max-width: 100% !important;
              overflow: hidden !important;
            }

            /* ── Metricas Streamlit ── */
            [data-testid="stMetricValue"] { font-size: 1.2rem !important; }
            [data-testid="stMetricLabel"] { font-size: 0.72rem !important; }
            [data-testid="stMetricDelta"] { font-size: 0.72rem !important; }

            /* ── Alertas ── */
            .stAlert { font-size: 0.85rem !important; padding: 10px 12px !important; }

            /* ── Expanders ── */
            .stExpander details summary { font-size: 0.85rem !important; }

            /* ── Tipografia ── */
            h3 { font-size: 1.05rem !important; }
            h4 { font-size: 0.95rem !important; }

            /* ── Badges ── */
            .dg-badge { font-size: 0.68rem !important; padding: 3px 8px !important; }

            /* ── Slider ── */
            [data-testid="stSlider"] { padding-left: 4px !important; padding-right: 4px !important; }

            /* ── Toggle ── */
            [data-testid="stToggle"] { -webkit-tap-highlight-color: transparent !important; }

            /* ── Radio ── */
            [data-testid="stRadio"] label { font-size: 0.85rem !important; }

            /* ── Spinner ── */
            [data-testid="stSpinner"] { font-size: 0.85rem !important; }

            /* ── Upload area ── */
            [data-testid="stFileUploaderDropzone"] {
              padding: 16px 12px !important;
            }
          }

          /* ── Telas muito pequenas (< 480 px) ── */
          @media (max-width: 480px) {
            .block-container,
            [data-testid="stMainBlockContainer"] {
              padding-left: 8px !important;
              padding-right: 8px !important;
            }
            .dg-hero { padding: 22px 16px 18px !important; }
            .dg-hero-title { font-size: 1.35rem !important; }
            .dg-hero-subtitle { font-size: 0.82rem !important; }
            .dg-hero-status { gap: 10px 18px !important; }
            .dg-hero-stat-value { font-size: 0.9rem !important; max-width: 130px !important; }
            .stTabs [data-baseweb="tab"] {
              font-size: 0.72rem !important;
              padding: 0 8px !important;
            }
            .dg-card-value { font-size: 1rem !important; }
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


_ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"


def get_asset_data_uri(filename: str) -> str:
    file_path = _ASSETS_DIR / filename
    if not file_path.exists():
        return ""
    encoded = base64.b64encode(file_path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def render_hero(
    dataset_name: str | None = None,
    quality_score: float | None = None,
    quality_level: str | None = None,
    rows: int | None = None,
    cols: int | None = None,
) -> None:
    """Hero section com gradiente, identidade DG e status do dataset ativo."""
    palette = QUALITY_PALETTE.get(quality_level or "", QUALITY_PALETTE["Bom"])
    status_html = ""
    if dataset_name:
        badge_style = (
        f"color:{palette['color']} !important;background:{palette['bg']} !important;"
        f"border-color:{palette['border']} !important;"
        )
        level_label = quality_level or "—"
        score_label = f"{quality_score:.0f}/100" if quality_score is not None else "—"
        rows_label  = f"{rows:,}" if rows is not None else "—"
        cols_label  = f"{cols:,}" if cols is not None else "—"

        status_html = f"""
        <div class="dg-hero-status">
          <div class="dg-hero-stat">
            <span class="dg-hero-stat-label">Dataset ativo</span>
            <span class="dg-hero-stat-value">{dataset_name}</span>
          </div>
          <div class="dg-hero-stat">
            <span class="dg-hero-stat-label">Score</span>
            <span class="dg-hero-stat-value">{score_label}</span>
          </div>
          <div class="dg-hero-stat">
            <span class="dg-hero-stat-label">Nivel</span>
            <span class="dg-hero-badge" style="{badge_style}">{level_label}</span>
          </div>
          <div class="dg-hero-stat">
            <span class="dg-hero-stat-label">Linhas</span>
            <span class="dg-hero-stat-value">{rows_label}</span>
          </div>
          <div class="dg-hero-stat">
            <span class="dg-hero-stat-label">Colunas</span>
            <span class="dg-hero-stat-value">{cols_label}</span>
          </div>
        </div>
        """

    st.markdown(
        f"""
        <div class="dg-hero">
          <div class="dg-hero-top">
            <div style="flex:1;min-width:0;">
              <h1 class="dg-hero-title">Data Guardian</h1>
              <p class="dg-hero-subtitle">Plataforma de diagnostico e tratamento de qualidade de dados.</p>
            </div>
          </div>
          {status_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stepper(active: str, extra_sections: list[str] | None = None) -> str:
    """Navegacao principal clicavel. extra_sections adiciona abas opcionais (ex: 'Drift')."""
    labels: dict[str, str] = {
        "Painel": "1 Diagnostico",
        "Tratamento": "2 Tratamento",
        "Insights BI": "3 Insights BI",
    }
    for i, sec in enumerate(extra_sections or [], start=4):
        labels[sec] = f"{i} {sec}"

    options = ["Painel", "Tratamento", "Insights BI"] + (extra_sections or [])
    selected = active if active in options else "Painel"

    picked = st.segmented_control(
        "Navegacao principal",
        options=options,
        default=selected,
        key="nav_stepper",
        format_func=lambda x: labels[x],
        selection_mode="single",
        width="stretch",
        label_visibility="collapsed",
    )

    return picked or selected


def metric_card(
    label: str,
    value: str,
    bar_pct: float | None = None,
    bar_color: str | None = None,
    sub: str | None = None,
) -> None:
    """Card de métrica com barra de progresso contextual opcional."""
    bar_html = ""
    if bar_pct is not None:
        pct = max(0.0, min(100.0, bar_pct))
        color = bar_color or "#155eef"
        bar_html = f"""
        <div class="dg-card-bar-track">
          <div class="dg-card-bar-fill" style="width:{pct:.1f}%;background:{color};"></div>
        </div>
        """

    sub_html = f'<div class="dg-card-sub">{sub}</div>' if sub else ""

    st.markdown(
        f"""
        <div class="dg-card">
          <div class="dg-card-label">{label}</div>
          <div class="dg-card-value">{value}</div>
          {bar_html}
          {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def badge(label: str, kind: str) -> str:
    css_class = {
        "critical": "dg-badge-critical",
        "warning":  "dg-badge-warning",
        "good":     "dg-badge-good",
    }.get(kind, "dg-badge-good")
    return f"<span class='dg-badge {css_class}'>{label}</span>"


# Mantido para retrocompatibilidade — substituido por render_hero
def render_header() -> None:
    render_hero()
