from __future__ import annotations

import io

import pandas as pd
import streamlit as st

_MAX_FILE_SIZE_MB = 50
_ENCODINGS = ("utf-8", "latin-1", "cp1252")


@st.cache_data(show_spinner=False)
def read_uploaded_csv(file_bytes: bytes, file_name: str) -> tuple[pd.DataFrame | None, str | None]:
    if len(file_bytes) > _MAX_FILE_SIZE_MB * 1024 * 1024:
        return None, f"Arquivo muito grande. Limite: {_MAX_FILE_SIZE_MB} MB."

    last_error: str = "Encoding desconhecido."
    for encoding in _ENCODINGS:
        try:
            df = pd.read_csv(io.BytesIO(file_bytes), encoding=encoding)
        except UnicodeDecodeError:
            last_error = "Nao foi possivel detectar a codificacao do arquivo."
            continue
        except pd.errors.EmptyDataError:
            return None, "O arquivo CSV esta vazio."
        except pd.errors.ParserError as e:
            return None, f"CSV malformado: {e}"
        except Exception as e:
            return None, f"Erro inesperado ao ler arquivo: {e}"

        if df.shape[1] == 0:
            return None, "O arquivo nao contem colunas validas."
        if df.empty:
            return None, "O arquivo nao contem linhas de dados (apenas cabecalho)."

        return df, None

    return None, last_error
