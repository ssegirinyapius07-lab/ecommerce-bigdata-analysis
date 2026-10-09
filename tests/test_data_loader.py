from pathlib import Path

import pandas as pd
import pytest

from ecommerce_analysis.data_loader import load_transactions


def test_loads_csv_and_trims_column_names(tmp_path: Path) -> None:
    csv_path = tmp_path / "transactions.csv"
    csv_path.write_text(" InvoiceNo ,Quantity\n1001,2\n", encoding="utf-8")

    data = load_transactions(csv_path)

    assert list(data.columns) == ["InvoiceNo", "Quantity"]
    assert data.loc[0, "InvoiceNo"] == 1001
    assert data.loc[0, "Quantity"] == 2


def test_loads_csv_with_common_retail_header_aliases(tmp_path: Path) -> None:
    csv_path = tmp_path / "online_retail_ii.csv"
    csv_path.write_text(
        "Invoice,StockCode,Description,Quantity,Invoice Date,Price,Customer ID,Country\n"
        "1001,A1,Item A,2,01/12/2010,1.5,123,United Kingdom\n",
        encoding="utf-8",
    )

    data = load_transactions(csv_path)

    assert list(data.columns) == [
        "InvoiceNo",
        "StockCode",
        "Description",
        "Quantity",
        "InvoiceDate",
        "UnitPrice",
        "CustomerID",
        "Country",
    ]
    assert data.loc[0, "InvoiceNo"] == 1001
    assert data.loc[0, "UnitPrice"] == 1.5
    assert data.loc[0, "CustomerID"] == 123


def test_loads_and_combines_transaction_worksheets(tmp_path: Path) -> None:
    excel_path = tmp_path / "online_retail_ii.xlsx"
    first_year = pd.DataFrame(
        {
            "Invoice": [1001],
            "StockCode": ["A1"],
            "Description": ["Item A"],
            "Quantity": [2],
            "InvoiceDate": ["01/12/2010"],
            "Price": [1.5],
            "Customer ID": [123],
            "Country": ["United Kingdom"],
        }
    )
    second_year = pd.DataFrame(
        {
            "Invoice": [1002],
            "StockCode": ["B2"],
            "Description": ["Item B"],
            "Quantity": [3],
            "InvoiceDate": ["01/01/2011"],
            "Price": [2.5],
            "Customer ID": [456],
            "Country": ["France"],
        }
    )

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        first_year.to_excel(writer, sheet_name="Year 2009-2010", index=False)
        second_year.to_excel(writer, sheet_name="Year 2010-2011", index=False)
        pd.DataFrame({"Notes": ["Not transaction data"]}).to_excel(
            writer, sheet_name="Notes", index=False
        )

    data = load_transactions(excel_path)

    assert len(data) == 2
    assert data["InvoiceNo"].tolist() == [1001, 1002]
    assert data["UnitPrice"].tolist() == [1.5, 2.5]
    assert data["CustomerID"].tolist() == [123, 456]


def test_missing_file_raises_clear_error(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError, match="was not found"):
        load_transactions(missing_path)


def test_unsupported_extension_is_rejected(tmp_path: Path) -> None:
    unsupported_path = tmp_path / "transactions.json"
    unsupported_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported file format"):
        load_transactions(unsupported_path)
