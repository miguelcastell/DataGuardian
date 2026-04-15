from __future__ import annotations

import streamlit as st


def apply_design_system() -> None:
    st.markdown(
        """
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

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
            --shadow: 0 1px 2px rgba(16, 24, 40, 0.06), 0 1px 3px rgba(16, 24, 40, 0.10);
            --success: #067647;
            --warning: #b54708;
            --error: #b42318;
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
          [data-testid="stToolbar"] * {
            color: var(--text) !important;
          }

          .block-container {
            max-width: 1400px;
            padding-top: var(--space-3);
            padding-bottom: var(--space-3);
          }

          .dg-title {
            margin: 0;
            font-size: 1.75rem;
            font-weight: 800;
            color: var(--text);
            letter-spacing: -0.02em;
          }

          .dg-subtitle {
            margin-top: 6px;
            color: var(--text-muted);
            font-size: 0.95rem;
          }

          .dg-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 14px 16px;
            box-shadow: var(--shadow);
            height: 100%;
          }

          .dg-card-label {
            font-family: 'JetBrains Mono', monospace;
            text-transform: uppercase;
            font-size: 0.69rem;
            color: var(--text-muted);
            letter-spacing: 0.04em;
          }

          .dg-card-value {
            margin-top: 4px;
            font-size: 1.5rem;
            font-weight: 800;
            color: var(--text);
            line-height: 1.2;
          }

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

          .dg-badge-critical {
            color: #7a271a;
            background: #fef3f2;
            border-color: #fecdca;
          }

          .dg-badge-warning {
            color: #93370d;
            background: #fffaeb;
            border-color: #fedf89;
          }

          .dg-badge-good {
            color: #085d3a;
            background: #ecfdf3;
            border-color: #abefc6;
          }

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

          .stSidebar {
            background: #f8fafc;
            border-right: 1px solid var(--border);
          }

          [data-testid="stSidebar"],
          [data-testid="stSidebar"] * {
            color: var(--text) !important;
            background-color: transparent;
          }

          [data-testid="stFileUploaderDropzone"] {
            background: #ffffff !important;
            border: 1.5px dashed #98a2b3 !important;
            border-radius: 12px !important;
          }

          [data-testid="stFileUploaderDropzoneInstructions"] span,
          [data-testid="stFileUploaderDropzone"] small {
            color: var(--text) !important;
          }

          [data-testid="stFileUploaderDropzone"] button,
          [data-testid="stFileUploaderDropzone"] button p,
          [data-testid="stFileUploaderDropzone"] button span,
          [data-testid="stFileUploader"] button,
          [data-testid="stFileUploader"] button p,
          [data-testid="stFileUploader"] button span {
            background: #e8f0ff !important;
            color: #0b3b8a !important;
            border: 1px solid #b2ccff !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
          }

          [data-testid="stFileUploaderDropzone"] button:hover,
          [data-testid="stFileUploader"] button:hover {
            background: #d9e8ff !important;
            color: #062f75 !important;
          }

          p, span, label, small, li, h1, h2, h3, h4, h5 {
            color: var(--text);
          }

          [data-baseweb="select"] > div,
          [data-testid="stNumberInput"] input,
          [data-testid="stTextInput"] input,
          [data-testid="stTextArea"] textarea {
            background: #ffffff !important;
            border: 1px solid var(--border) !important;
            color: var(--text) !important;
          }

          [role="listbox"] {
            background: #ffffff !important;
            border: 1px solid var(--border) !important;
          }

          [role="option"] {
            color: var(--text) !important;
          }

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
          [data-testid="stDownloadButton"] button span {
            color: #ffffff !important;
            fill: #ffffff !important;
          }

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
          [data-testid="stDownloadButton"] button:disabled * {
            color: #334155 !important;
            fill: #334155 !important;
          }

          .stAlert {
            border-radius: 12px;
            border: 1px solid var(--border);
          }

          [data-testid="stDataFrame"] {
            border: 1px solid var(--border);
            border-radius: 10px;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str) -> None:
    st.markdown(
        f"""
        <div class="dg-card">
          <div class="dg-card-label">{label}</div>
          <div class="dg-card-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def badge(label: str, kind: str) -> str:
    css_class = {
        "critical": "dg-badge-critical",
        "warning": "dg-badge-warning",
        "good": "dg-badge-good",
    }.get(kind, "dg-badge-good")
    return f"<span class='dg-badge {css_class}'>{label}</span>"


def render_header() -> None:
    st.markdown("<h1 class='dg-title'>Data Guardian</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='dg-subtitle'>Plataforma de analise e tratamento de qualidade de dados.</p>",
        unsafe_allow_html=True,
    )
