from __future__ import annotations

import io

import pandas as pd
import streamlit as st


@st.cache_data(show_spinner=False)
def read_uploaded_csv(file_bytes: bytes, file_name: str) -> pd.DataFrame:
    del file_name
    return pd.read_csv(io.BytesIO(file_bytes))
