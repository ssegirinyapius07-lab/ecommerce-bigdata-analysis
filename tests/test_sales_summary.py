import pandas as pd
import pytest

from ecommerce_analysis.analysis import (
    build_sales_summary,
    monthly_sales_summary,
    prepare_transactions,
    top_products_summary,
)


@pytest.fixture
def prepared_transactions() -> pd.DataFrame:
    source = pd.DataFrame(
        {
            "InvoiceNo": ["10001", "10001", "C10002", "10003", "10004"],
            "StockCode": ["A", "B", "C", "A", "D"],
            "Description": ["Product A", "Product B", "Product C", "Product A", None],
            "InvoiceDate": [
                "01/12/2010",
                "01/12/2010",
                "02/12/2010",
                "03/01/2011",
                "04/01/2011",
            ],
            "Quantity": [2, 1, 1, -1, 2],
            "UnitPrice": [10.0, 5.0, 12.0, 5.0, -1.0],
            "CustomerID": [100, 100, 101, 100, None],
            "Country": ["UK", "UK", "UK", "UK", "France"],
        }
    )
    return prepare_transactions(source)


def test_sales_summary_separates_sales_cancellations_and_returns(
    prepared_transactions: pd.DataFrame,
) -> None:
    summary = build_sales_summary(prepared_transactions)

    assert summary["source_rows"] == 5
    assert summary["qualifying_sales_rows"] == 2
    assert summary["qualifying_sales_line_value"] == pytest.approx(25.0)
    assert summary["sales_invoices"] == 1
    assert summary["cancellation_rows"] == 1
    assert summary["cancellation_invoices"] == 1
    assert summary["negative_quantity_rows"] == 1
    assert summary["identified_customers"] == 1
    assert summary["distinct_products"] == 2
    assert summary["countries"] == 1
    assert summary["first_sales_date"] == "2010-12-01"
    assert summary["last_sales_date"] == "2010-12-01"


def test_monthly_summary_groups_sales_by_month(
    prepared_transactions: pd.DataFrame,
) -> None:
    monthly = monthly_sales_summary(prepared_transactions)

    assert len(monthly) == 1
    assert monthly.loc[0, "Month"] == pd.Timestamp("2010-12-01")
    assert monthly.loc[0, "SalesValue"] == pytest.approx(25.0)
    assert monthly.loc[0, "InvoiceCount"] == 1
    assert monthly.loc[0, "CustomerCount"] == 1


def test_top_products_excludes_cancellations_returns_and_invalid_prices(
    prepared_transactions: pd.DataFrame,
) -> None:
    products = top_products_summary(prepared_transactions, limit=10)

    assert products["Description"].tolist() == ["Product A", "Product B"]
    assert products["SalesValue"].tolist() == [20.0, 5.0]
    assert products["QuantitySold"].tolist() == [2, 1]


def test_top_products_rejects_non_positive_limit(
    prepared_transactions: pd.DataFrame,
) -> None:
    with pytest.raises(ValueError, match="limit must be at least 1"):
        top_products_summary(prepared_transactions, limit=0)
