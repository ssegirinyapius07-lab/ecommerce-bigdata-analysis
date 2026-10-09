"""Baseline preparation and data-quality summaries for retail transactions."""

from collections.abc import Mapping

import pandas as pd

REQUIRED_COLUMNS = {"InvoiceNo", "InvoiceDate", "Quantity", "UnitPrice"}


def prepare_transactions(data: pd.DataFrame) -> pd.DataFrame:
    """Add analysis fields without removing or overwriting source rows.

    Qualifying sales lines exclude cancellation-marked invoices, non-positive
    quantities, negative unit prices, and invalid invoice dates. Returns and
    cancellations remain present in the prepared data for separate review.
    """
    missing_columns = sorted(REQUIRED_COLUMNS.difference(data.columns))
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Required transaction columns are missing: {missing}")

    prepared = data.copy()
    prepared["InvoiceNo"] = prepared["InvoiceNo"].astype("string").str.strip()
    prepared["InvoiceDate"] = pd.to_datetime(
        prepared["InvoiceDate"], errors="coerce", dayfirst=True
    )
    prepared["Quantity"] = pd.to_numeric(prepared["Quantity"], errors="coerce")
    prepared["UnitPrice"] = pd.to_numeric(prepared["UnitPrice"], errors="coerce")

    prepared["LineValue"] = prepared["Quantity"] * prepared["UnitPrice"]
    prepared["IsCancellation"] = prepared["InvoiceNo"].str.upper().str.startswith(
        "C", na=False
    )
    prepared["IsReturnLine"] = prepared["Quantity"].lt(0)
    prepared["IsSaleLine"] = (
        ~prepared["IsCancellation"]
        & prepared["Quantity"].gt(0)
        & prepared["UnitPrice"].ge(0)
        & prepared["InvoiceDate"].notna()
    )
    prepared["SalesValue"] = prepared["LineValue"].where(
        prepared["IsSaleLine"], 0.0
    ).fillna(0.0)
    return prepared


def build_quality_summary(data: pd.DataFrame) -> Mapping[str, int]:
    """Return basic quality indicators without silently changing the input."""
    summary = {
        "rows": int(len(data)),
        "columns": int(len(data.columns)),
        "duplicate_rows": int(data.duplicated().sum()),
        "missing_cells": int(data.isna().sum().sum()),
    }

    if "CustomerID" in data.columns:
        summary["missing_customer_ids"] = int(data["CustomerID"].isna().sum())

    if "InvoiceNo" in data.columns:
        invoice_numbers = data["InvoiceNo"].astype("string").str.strip()
        cancellation_mask = invoice_numbers.str.upper().str.startswith("C", na=False)
        summary["cancellation_rows"] = int(cancellation_mask.sum())
        summary["cancellation_invoices"] = int(
            invoice_numbers.loc[cancellation_mask].nunique()
        )

    if "Quantity" in data.columns:
        quantity = pd.to_numeric(data["Quantity"], errors="coerce")
        summary["negative_quantity_rows"] = int(quantity.lt(0).sum())

    return summary
