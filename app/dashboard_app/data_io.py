from __future__ import annotations

import csv
import io

import pandas as pd
import streamlit as st

_MAX_FILE_SIZE_MB = 200
_CHUNK_SIZE = 50_000
_LARGE_FILE_THRESHOLD = 10 * 1024 * 1024  # 10 MB


def _detect_encoding(file_bytes: bytes) -> str:
    try:
        import chardet  # type: ignore
        result = chardet.detect(file_bytes[:100_000])
        encoding = result.get("encoding") or "utf-8"
        if (result.get("confidence") or 0.0) < 0.5:
            return "utf-8"
        return encoding
    except ImportError:
        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                file_bytes[:2048].decode(enc)
                return enc
            except UnicodeDecodeError:
                continue
        return "utf-8"


def _detect_delimiter(file_bytes: bytes, encoding: str) -> str:
    try:
        sample = file_bytes[:8192].decode(encoding, errors="replace")
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        return dialect.delimiter
    except csv.Error:
        return ","


def _read_csv_chunked(file_bytes: bytes, encoding: str, sep: str) -> pd.DataFrame:
    chunks = [
        chunk
        for chunk in pd.read_csv(
            io.BytesIO(file_bytes),
            encoding=encoding,
            sep=sep,
            chunksize=_CHUNK_SIZE,
            low_memory=False,
        )
    ]
    if not chunks:
        return pd.DataFrame()
    return pd.concat(chunks, ignore_index=True)


@st.cache_data(show_spinner=False)
def read_uploaded_csv(
    file_bytes: bytes,
    file_name: str,
) -> tuple[pd.DataFrame | None, str | None, dict[str, str]]:
    """
    Returns (df, error_message, meta).
    meta contains 'encoding' and 'delimiter' detected automatically.
    """
    if len(file_bytes) > _MAX_FILE_SIZE_MB * 1024 * 1024:
        return None, f"Arquivo muito grande. Limite: {_MAX_FILE_SIZE_MB} MB.", {}

    encoding = _detect_encoding(file_bytes)
    delimiter = _detect_delimiter(file_bytes, encoding)
    meta: dict[str, str] = {
        "encoding": encoding,
        "delimiter": repr(delimiter),
    }

    is_large = len(file_bytes) > _LARGE_FILE_THRESHOLD

    try:
        if is_large:
            df = _read_csv_chunked(file_bytes, encoding, delimiter)
        else:
            df = pd.read_csv(
                io.BytesIO(file_bytes),
                encoding=encoding,
                sep=delimiter,
                low_memory=False,
            )
    except UnicodeDecodeError:
        for fallback in ("utf-8", "latin-1", "cp1252"):
            if fallback == encoding:
                continue
            try:
                df = pd.read_csv(
                    io.BytesIO(file_bytes),
                    encoding=fallback,
                    sep=delimiter,
                    low_memory=False,
                )
                meta["encoding"] = fallback
                break
            except UnicodeDecodeError:
                continue
        else:
            return None, "Nao foi possivel detectar a codificacao do arquivo.", meta
    except pd.errors.EmptyDataError:
        return None, "O arquivo CSV esta vazio.", meta
    except pd.errors.ParserError as e:
        return None, f"CSV malformado: {e}", meta
    except Exception as e:
        return None, f"Erro inesperado ao ler arquivo: {e}", meta

    if df.shape[1] == 0:
        return None, "O arquivo nao contem colunas validas.", meta
    if df.empty:
        return None, "O arquivo nao contem linhas de dados (apenas cabecalho).", meta

    return df, None, meta
