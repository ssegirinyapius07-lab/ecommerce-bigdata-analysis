import pandas as pd
import pytest

from ecommerce_analysis.analysis import build_quality_summary, prepare_transactions


def test_preparation_separates_sales_cancellations_and_returns() -> None:
    source = pd.DataFrame(
        {
            "InvoiceNo": ["10001", "C10002", "10003", "10004"],
            "InvoiceDate": ["01/12/2010", "02/12/2010", "03/12/2010", "not-a-date"],
            "Quantity": [2, 1, -1, 2],
            "UnitPrice": [10.0, 12.0, 5.0, 7.0],
            "CustomerID": [100, 101, 100, None],
            "Description": ["Item A", "Item B", "Item A", "Item C"],
        }
    )

    prepared = prepare_transactions(source)

    assert len(prepared) == len(source)
    assert prepared["SalesValue"].tolist() == [20.0, 0.0, 0.0, 0.0]
    assert prepared["IsSaleLine"].tolist() == [True, False, False, False]
    assert prepared["IsCancellation"].tolist() == [False, True, False, False]
    assert prepared["IsReturnLine"].tolist() == [False, False, True, False]


def test_preparation_requires_core_columns() -> None:
    with pytest.raises(ValueError, match="Required transaction columns are missing"):
        prepare_transactions(pd.DataFrame({"InvoiceNo": ["10001"]}))


def test_quality_summary_reports_missing_ids_cancellations_and_duplicates() -> None:
    source = pd.DataFrame(
        {
            "InvoiceNo": ["10001", "10001", "C10002"],
            "CustomerID": [10, 10, None],
            "Quantity": [1, 1, -1],
        }
    )

    summary = build_quality_summary(source)

    assert summary["rows"] == 3
    assert summary["duplicate_rows"] == 1
    assert summary["missing_customer_ids"] == 1
    assert summary["cancellation_rows"] == 1
    assert summary["cancellation_invoices"] == 1
    assert summary["negative_quantity_rows"] == 1
