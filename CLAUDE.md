# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Install dependencies:**
```bash
pip install -r requirements.txt
```

**Run the application:**
```bash
python -m streamlit run app/dashboard.py
```

## Architecture

Data Guardian is a **Streamlit-based data quality platform** for CSV files, built for Portuguese-speaking users (PT-BR interface). It runs entirely in session state — no database, no persistence beyond file downloads.

### Layer structure

```
app/                        # UI layer (Streamlit)
│   dashboard.py            # Entry point — configures Streamlit page, adds src/ to sys.path
│   dashboard_app/
│       app_main.py         # run_dashboard() — main orchestrator, session state management
│       sections.py         # Render functions for each dashboard panel
│       scoring.py          # Quality scoring algorithm
│       styles.py           # Design system (CSS, metric_card(), badge(), render_header())
│       data_io.py          # CSV read with @st.cache_data

src/data/                   # Business logic (no Streamlit imports)
    quality.py              # analyze_dataset(df) — returns analysis dict
    cleaning.py             # clean_dataset(df, **options) — returns cleaned DataFrame
```

### Data flow

1. User uploads CSV → `data_io.py` caches the DataFrame in `st.session_state`
2. `quality.py.analyze_dataset(df)` produces an analysis dict (missing values, duplicates, outliers, type issues, constants, column profiles)
3. `scoring.py.compute_quality_score()` converts analysis dict into a 0–100 score and prioritized issue list
4. `sections.py` renders five panels: overview, quality issues, alerts, cleaning, and BI/visual insights
5. User configures treatment options → `cleaning.py.clean_dataset()` applies transformations → download cleaned CSV

### Key module contracts

| Module | Key function | Input → Output |
|--------|-------------|----------------|
| `quality.py` | `analyze_dataset(df)` | DataFrame → analysis dict |
| `cleaning.py` | `clean_dataset(df, **options)` | DataFrame + options → cleaned DataFrame |
| `scoring.py` | `compute_quality_score(analysis, df)` | analysis dict → score dict + issue list |
| `scoring.py` | `build_prioritized_issues(analysis, df)` | analysis dict → sorted issue list |
| `sections.py` | `render_*(...)` | analysis dict + df → Streamlit widgets (side effects only) |

### Quality score levels (PT-BR labels)
- **Excelente**: ≥ 90
- **Bom**: 75–89
- **Atenção**: 55–74
- **Crítico**: < 55

### Cleaning options (kwargs to `clean_dataset`)
- `trim_strings` — strip whitespace from string columns
- `fill_placeholders` — convert placeholder nulls (`NA`, `N/A`, `null`, `none`, `-`) to `NaN`
- `normalize_columns` — rename columns to `lowercase_snake_case`
- `remove_duplicates`
- `drop_high_missing` + `missing_threshold` — drop columns above a missing % threshold
- `fill_numeric` — strategy: `median | mean | zero`
- `fill_categorical` — strategy: `mode | unknown`

### Design system
`styles.py` owns all CSS via `apply_design_system()`. UI components (`metric_card()`, `badge()`, `render_header()`) return HTML strings rendered with `st.markdown(..., unsafe_allow_html=True)`. Colors and typography are defined as CSS variables; change them in `styles.py` to restyle the entire app.

### Streamlit-specific conventions
- All cross-section state lives in `st.session_state` (managed in `app_main.py`)
- `data_io.py` uses `@st.cache_data` — cached per uploaded file bytes
- `dashboard.py` manually inserts the repo root into `sys.path` so `src/` is importable without installing as a package
- There is no test framework or linter configured in the repo
