import pandas as pd
import pytest

from ecommerce_analysis.analysis import (
    country_sales_summary,
    customer_rfm_summary,
    high_quantity_lines,
)


def _prepared_sample() -> pd.DataFrame:
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
    from ecommerce_analysis.analysis import prepare_transactions

    return prepare_transactions(source)


def test_country_summary_ranks_qualifying_sales_only() -> None:
    countries = country_sales_summary(_prepared_sample())

    assert countries["Country"].tolist() == ["UK"]
    assert countries.loc[0, "SalesValue"] == pytest.approx(25.0)
    assert countries.loc[0, "SalesLines"] == 2
    assert countries.loc[0, "InvoiceCount"] == 1
    assert countries.loc[0, "CustomerCount"] == 1


def test_customer_rfm_uses_distinct_invoices_and_identified_customers_only() -> None:
    customers = customer_rfm_summary(_prepared_sample())

    assert len(customers) == 1
    assert customers.loc[0, "CustomerID"] == 100
    assert customers.loc[0, "LastPurchase"] == pd.Timestamp("2010-12-01")
    assert customers.loc[0, "RecencyDays"] == 1
    assert customers.loc[0, "Frequency"] == 1
    assert customers.loc[0, "Monetary"] == pytest.approx(25.0)
    assert customers.loc[0, "AverageInvoiceValue"] == pytest.approx(25.0)


def test_high_quantity_analysis_flags_but_does_not_delete_source_rows() -> None:
    source = pd.DataFrame(
        {
            "InvoiceNo": ["10001", "10002"],
            "StockCode": ["A", "B"],
            "Description": ["Standard item", "Bulk item"],
            "InvoiceDate": ["01/12/2010", "02/12/2010"],
            "Quantity": [2, 80995],
            "UnitPrice": [2.0, 2.08],
            "CustomerID": [10, 20],
            "Country": ["UK", "UK"],
        }
    )
    from ecommerce_analysis.analysis import prepare_transactions

    prepared = prepare_transactions(source)
    flagged = high_quantity_lines(prepared, minimum_quantity=1000)

    assert len(prepared) == 2
    assert len(flagged) == 1
    assert flagged.loc[0, "InvoiceNo"] == "10002"
    assert flagged.loc[0, "Quantity"] == 80995


def test_high_quantity_analysis_rejects_non_positive_threshold() -> None:
    with pytest.raises(ValueError, match="minimum_quantity must be at least 1"):
        high_quantity_lines(_prepared_sample(), minimum_quantity=0)
