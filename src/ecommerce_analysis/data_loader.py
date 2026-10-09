"""Reusable CSV and Excel transaction-data loading utilities."""

from pathlib import Path
from typing import BinaryIO

import pandas as pd

SUPPORTED_SUFFIXES = {".csv", ".xlsx"}
PathLike = str | Path


def load_transactions(source: PathLike | BinaryIO) -> pd.DataFrame:
    """Load transaction data from a CSV or XLSX file.

    Args:
        source: A filesystem path or a binary file-like object with a filename.

    Returns:
        A DataFrame whose column names have surrounding whitespace removed.

    Raises:
        FileNotFoundError: The provided filesystem path does not exist.
        ValueError: The file format is not supported.
    """
    if isinstance(source, (str, Path)):
        path = Path(source)
        if not path.is_file():
            raise FileNotFoundError(f"Transaction data file was not found: {path}")
        suffix = path.suffix.lower()
        input_source: PathLike | BinaryIO = path
    else:
        source_name = getattr(source, "name", "")
        suffix = Path(str(source_name)).suffix.lower()
        input_source = source

    if suffix not in SUPPORTED_SUFFIXES:
        supported = ", ".join(sorted(SUPPORTED_SUFFIXES))
        raise ValueError(
            f"Unsupported file format '{suffix}'. Supported formats: {supported}"
        )

    if hasattr(input_source, "seek"):
        input_source.seek(0)  # type: ignore[union-attr]

    if suffix == ".csv":
        data = pd.read_csv(input_source, encoding="utf-8-sig", low_memory=False)
    else:
        data = pd.read_excel(input_source, engine="openpyxl")

    data.columns = [str(column).strip() for column in data.columns]
    return data
