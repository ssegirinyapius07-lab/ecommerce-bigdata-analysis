"""Reusable CSV and Excel transaction-data loading utilities."""

import re
from pathlib import Path
from typing import BinaryIO

import pandas as pd

SUPPORTED_SUFFIXES = {".csv", ".xlsx"}
PathLike = str | Path

# Map common names used by public transaction datasets to the app's standard schema.
_COLUMN_ALIASES = {
    "invoice": "InvoiceNo",
    "invoiceno": "InvoiceNo",
    "invoicenumber": "InvoiceNo",
    "stockcode": "StockCode",
    "description": "Description",
    "quantity": "Quantity",
    "invoicedate": "InvoiceDate",
    "price": "UnitPrice",
    "unitprice": "UnitPrice",
    "customerid": "CustomerID",
    "country": "Country",
}
_CORE_TRANSACTION_COLUMNS = {"InvoiceNo", "InvoiceDate", "Quantity", "UnitPrice"}


def _normalise_column_names(data: pd.DataFrame) -> pd.DataFrame:
    """Trim headers and standardise common transaction column aliases."""
    normalised = data.copy()
    columns: list[str] = []
    seen: set[str] = set()

    for column in data.columns:
        original = str(column).strip()
        key = re.sub(r"[^a-z0-9]+", "", original.casefold())
        canonical = _COLUMN_ALIASES.get(key, original)
        if canonical in seen:
            raise ValueError(
                f"More than one column maps to '{canonical}'. Keep only one version "
                "of each transaction field."
            )
        columns.append(canonical)
        seen.add(canonical)

    normalised.columns = columns
    return normalised


def load_transactions(source: PathLike | BinaryIO) -> pd.DataFrame:
    """Load CSV or Excel transaction data into a standard column schema.

    Excel workbooks may contain multiple transaction worksheets, which are
    combined when they all contain the required invoice, date, quantity, and
    price fields. Unrelated worksheets are ignored when transaction worksheets
    are found.
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
        return _normalise_column_names(data)

    workbook_sheets = pd.read_excel(
        input_source, sheet_name=None, engine="openpyxl"
    )
    sheets = [_normalise_column_names(sheet) for sheet in workbook_sheets.values()]
    transaction_sheets = [
        sheet for sheet in sheets if _CORE_TRANSACTION_COLUMNS.issubset(sheet.columns)
    ]

    if transaction_sheets:
        return pd.concat(transaction_sheets, ignore_index=True, sort=False)
    if sheets:
        return sheets[0]
    return pd.DataFrame()
