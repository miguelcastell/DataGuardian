from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is importable when Streamlit executes from app/ context.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.dashboard_app import run_dashboard


if __name__ == "__main__":
    run_dashboard()
