"""Preparation, quality checks, and baseline analysis for retail transactions."""

from collections.abc import Mapping

import pandas as pd

REQUIRED_COLUMNS = {"InvoiceNo", "InvoiceDate", "Quantity", "UnitPrice"}
PREPARED_COLUMNS = {
    "InvoiceNo",
    "InvoiceDate",
    "Quantity",
    "UnitPrice",
    "IsCancellation",
    "IsReturnLine",
    "IsSaleLine",
    "SalesValue",
}


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
        "rows": len(data),
        "columns": len(data.columns),
        "duplicate_rows": int(data.duplicated().sum()),
        "missing_cells": int(data.isna().sum().sum()),
    }

    if "CustomerID" in data.columns:
        summary["missing_customer_ids"] = int(data["CustomerID"].isna().sum())

    if "Description" in data.columns:
        description = data["Description"].astype("string").str.strip()
        summary["missing_descriptions"] = int(
            (description.isna() | description.eq("")).sum()
        )

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

    if "UnitPrice" in data.columns:
        unit_price = pd.to_numeric(data["UnitPrice"], errors="coerce")
        summary["negative_unit_price_rows"] = int(unit_price.lt(0).sum())
        summary["zero_unit_price_rows"] = int(unit_price.eq(0).sum())

    if "InvoiceDate" in data.columns:
        invoice_dates = pd.to_datetime(
            data["InvoiceDate"], errors="coerce", dayfirst=True
        )
        summary["invalid_invoice_dates"] = int(invoice_dates.isna().sum())

    return summary


def _require_prepared_transactions(data: pd.DataFrame) -> None:
    missing_columns = sorted(PREPARED_COLUMNS.difference(data.columns))
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(
            "Expected data prepared by prepare_transactions(); missing columns: "
            f"{missing}"
        )


def build_sales_summary(data: pd.DataFrame) -> Mapping[str, int | float | str]:
    """Summarise qualifying sales without treating returns as ordinary sales."""
    _require_prepared_transactions(data)
    sales = data.loc[data["IsSaleLine"]].copy()
    cancellations = data.loc[data["IsCancellation"]]
    returns = data.loc[data["IsReturnLine"]]

    summary: dict[str, int | float | str] = {
        "source_rows": len(data),
        "qualifying_sales_rows": len(sales),
        "qualifying_sales_line_value": float(sales["SalesValue"].sum()),
        "sales_invoices": int(sales["InvoiceNo"].nunique()),
        "cancellation_rows": len(cancellations),
        "cancellation_invoices": int(cancellations["InvoiceNo"].nunique()),
        "negative_quantity_rows": len(returns),
    }

    if not sales.empty:
        summary["first_sales_date"] = sales["InvoiceDate"].min().date().isoformat()
        summary["last_sales_date"] = sales["InvoiceDate"].max().date().isoformat()
    else:
        summary["first_sales_date"] = "Not available"
        summary["last_sales_date"] = "Not available"

    if "CustomerID" in sales.columns:
        summary["identified_customers"] = int(sales["CustomerID"].nunique(dropna=True))
    if "StockCode" in sales.columns:
        summary["distinct_products"] = int(sales["StockCode"].nunique(dropna=True))
    if "Country" in sales.columns:
        summary["countries"] = int(sales["Country"].nunique(dropna=True))

    return summary


def monthly_sales_summary(data: pd.DataFrame) -> pd.DataFrame:
    """Aggregate qualifying sales by calendar month."""
    _require_prepared_transactions(data)
    sales = data.loc[data["IsSaleLine"]].copy()
    columns = ["Month", "SalesValue", "InvoiceCount"]
    if "CustomerID" in sales.columns:
        columns.append("CustomerCount")
    if sales.empty:
        return pd.DataFrame(columns=columns)

    sales["Month"] = sales["InvoiceDate"].dt.to_period("M").dt.to_timestamp()
    aggregations = {
        "SalesValue": ("SalesValue", "sum"),
        "InvoiceCount": ("InvoiceNo", "nunique"),
    }
    if "CustomerID" in sales.columns:
        aggregations["CustomerCount"] = ("CustomerID", "nunique")

    monthly = (
        sales.groupby("Month", as_index=False)
        .agg(**aggregations)
        .sort_values("Month")
        .reset_index(drop=True)
    )
    return monthly


def top_products_summary(data: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    """Return products ranked by qualifying sales line value."""
    _require_prepared_transactions(data)
    if limit < 1:
        raise ValueError("limit must be at least 1")
    if "Description" not in data.columns:
        raise ValueError("Product analysis requires a Description column")

    sales = data.loc[data["IsSaleLine"]].dropna(subset=["Description"]).copy()
    sales["Description"] = sales["Description"].astype("string").str.strip()
    sales = sales.loc[sales["Description"].ne("")]
    group_columns = ["Description"]
    if "StockCode" in sales.columns:
        group_columns.insert(0, "StockCode")

    columns = [*group_columns, "QuantitySold", "SalesValue", "InvoiceCount"]
    if sales.empty:
        return pd.DataFrame(columns=columns)

    products = (
        sales.groupby(group_columns, as_index=False, dropna=False)
        .agg(
            QuantitySold=("Quantity", "sum"),
            SalesValue=("SalesValue", "sum"),
            InvoiceCount=("InvoiceNo", "nunique"),
        )
        .sort_values("SalesValue", ascending=False)
        .head(limit)
        .reset_index(drop=True)
    )
    return products
