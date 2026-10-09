"""Print the first exploratory sales summary from the local retail workbook."""

from pathlib import Path

from ecommerce_analysis.analysis import (
    build_quality_summary,
    build_sales_summary,
    monthly_sales_summary,
    prepare_transactions,
    top_products_summary,
)
from ecommerce_analysis.data_loader import load_transactions

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = PROJECT_ROOT / "data" / "raw" / "Online Retail.xlsx"


def main() -> int:
    """Load the source file and print a concise, repeatable analysis report."""
    if not DEFAULT_DATASET.is_file():
        print("Dataset not found.")
        print(f"Expected location: {DEFAULT_DATASET}")
        print("Download the UCI Online Retail workbook and save it at that path.")
        return 1

    source_data = load_transactions(DEFAULT_DATASET)
    prepared = prepare_transactions(source_data)
    quality = build_quality_summary(source_data)
    sales_summary = build_sales_summary(prepared)

    print("E-COMMERCE SALES ANALYSIS")
    print("=========================")
    print(f"Source file: {DEFAULT_DATASET}")
    print("\nSALES SUMMARY")
    print("-------------")
    for name, value in sales_summary.items():
        label = name.replace("_", " ").title()
        if name == "qualifying_sales_line_value":
            print(f"{label}: GBP {value:,.2f}")
        elif isinstance(value, int):
            print(f"{label}: {value:,}")
        else:
            print(f"{label}: {value}")

    print("\nDATA-QUALITY SUMMARY")
    print("--------------------")
    for name, value in quality.items():
        print(f"{name.replace('_', ' ').title()}: {value:,}")

    print("\nTOP 10 PRODUCTS BY QUALIFYING SALES LINE VALUE")
    print("----------------------------------------------")
    products = top_products_summary(prepared, limit=10)
    if products.empty:
        print("No qualifying product records were found.")
    else:
        print(products.to_string(index=False, formatters={"SalesValue": "{:,.2f}".format}))

    print("\nMONTHLY SALES SUMMARY")
    print("---------------------")
    monthly = monthly_sales_summary(prepared)
    if monthly.empty:
        print("No qualifying sales records were found.")
    else:
        print(
            monthly.to_string(
                index=False,
                formatters={"SalesValue": "{:,.2f}".format},
            )
        )

    print(
        "\nNote: qualifying sales line value is not net revenue. "
        "Returns and cancellations are reported separately."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
