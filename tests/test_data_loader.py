from pathlib import Path

import pytest

from ecommerce_analysis.data_loader import load_transactions


def test_loads_csv_and_trims_column_names(tmp_path: Path) -> None:
    csv_path = tmp_path / "transactions.csv"
    csv_path.write_text(" InvoiceNo ,Quantity\n1001,2\n", encoding="utf-8")

    data = load_transactions(csv_path)

    assert list(data.columns) == ["InvoiceNo", "Quantity"]
    assert data.loc[0, "InvoiceNo"] == 1001
    assert data.loc[0, "Quantity"] == 2


def test_missing_file_raises_clear_error(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError, match="was not found"):
        load_transactions(missing_path)


def test_unsupported_extension_is_rejected(tmp_path: Path) -> None:
    unsupported_path = tmp_path / "transactions.json"
    unsupported_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported file format"):
        load_transactions(unsupported_path)
