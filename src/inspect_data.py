"""Print a first profile of the local retail dataset."""

from pathlib import Path

from ecommerce_analysis.analysis import build_quality_summary
from ecommerce_analysis.data_loader import load_transactions

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = PROJECT_ROOT / "data" / "raw" / "Online Retail.xlsx"


def main() -> int:
    """Inspect the local workbook and return a shell-friendly exit code."""
    if not DEFAULT_DATASET.is_file():
        print("Dataset not found.")
        print(f"Expected location: {DEFAULT_DATASET}")
        print("Download the UCI Online Retail workbook and save it at that path.")
        return 1

    data = load_transactions(DEFAULT_DATASET)
    summary = build_quality_summary(data)

    print("SOURCE DATA PROFILE")
    print("===================")
    print(f"File: {DEFAULT_DATASET}")
    print(f"Rows: {len(data):,}")
    print(f"Columns: {len(data.columns):,}")

    print("\nCOLUMN NAMES AND DATA TYPES")
    print("===========================")
    print(data.dtypes.to_string())

    print("\nFIRST FIVE RECORDS")
    print("===================")
    print(data.head().to_string(index=False))

    print("\nMISSING VALUES BY COLUMN")
    print("========================")
    print(data.isna().sum().to_string())

    print("\nQUALITY SUMMARY")
    print("================")
    for name, value in summary.items():
        print(f"{name.replace('_', ' ').title()}: {value:,}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
