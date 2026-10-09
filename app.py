"""Streamlit dashboard for the e-commerce analysis project."""

from pathlib import Path

import plotly.express as px
import streamlit as st

from ecommerce_analysis.analysis import build_quality_summary, prepare_transactions
from ecommerce_analysis.data_loader import load_transactions

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_DATASET = PROJECT_ROOT / "data" / "raw" / "Online Retail.xlsx"

st.set_page_config(
    page_title="E-commerce Analytics",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("E-commerce Customer Behaviour and Sales Analysis")
st.caption(
    "Transaction overview, product performance, sales patterns, and data-quality indicators."
)

with st.sidebar:
    st.header("Data source")
    uploaded_file = st.file_uploader(
        "Load a transaction file",
        type=["xlsx", "csv"],
        help="Upload a CSV or Excel file. For repeated use, keep the workbook in data/raw/.",
    )
    if uploaded_file is not None:
        data_source = uploaded_file
        source_label = uploaded_file.name
    elif DEFAULT_DATASET.is_file():
        data_source = DEFAULT_DATASET
        source_label = str(DEFAULT_DATASET.relative_to(PROJECT_ROOT))
    else:
        data_source = None
        source_label = ""

if data_source is None:
    st.info("The source dataset has not been added yet.")
    st.markdown(
        "Download the [UCI Online Retail dataset]"
        "(https://archive.ics.uci.edu/dataset/352/online+retail) and save the Excel "
        "workbook as **data/raw/Online Retail.xlsx**, or upload a CSV/XLSX file in the sidebar."
    )
    st.stop()

try:
    source_data = load_transactions(data_source)
    transactions = prepare_transactions(source_data)
except (OSError, ValueError, ImportError) as error:
    st.error(f"Could not load the selected transaction file: {error}")
    st.stop()

if transactions.empty:
    st.warning("The selected file contains no transaction rows.")
    st.stop()

st.caption(f"Data source: {source_label}")

with st.sidebar:
    if "Country" in transactions.columns:
        country_values = (
            transactions["Country"].dropna().astype(str).sort_values().unique().tolist()
        )
        selected_countries = st.multiselect(
            "Countries",
            options=country_values,
            default=[],
            help="Leave empty to include all countries.",
        )
    else:
        selected_countries = []

filtered = transactions.copy()
if selected_countries:
    filtered = filtered[filtered["Country"].astype(str).isin(selected_countries)]

sales = filtered.loc[filtered["IsSaleLine"]].copy()
quality = build_quality_summary(filtered)

total_sales = float(sales["SalesValue"].sum())
invoice_count = int(sales["InvoiceNo"].nunique())
if "CustomerID" in sales.columns:
    customer_count = int(sales["CustomerID"].nunique(dropna=True))
else:
    customer_count = 0

cancelled_invoices = int(quality.get("cancellation_invoices", 0))
return_lines = int(quality.get("negative_quantity_rows", 0))

metric_columns = st.columns(4)
metric_columns[0].metric("Qualifying sales line value", f"£{total_sales:,.2f}")
metric_columns[1].metric("Sales invoices", f"{invoice_count:,}")
metric_columns[2].metric("Identified customers", f"{customer_count:,}")
metric_columns[3].metric("Cancelled invoices", f"{cancelled_invoices:,}")

st.caption(
    "Sales line value includes non-cancellation rows with positive quantities, "
    "non-negative unit prices, and valid invoice dates. Returns are reported separately "
    "and are not yet deducted to calculate net revenue."
)

left_column, right_column = st.columns(2)

with left_column:
    st.subheader("Sales line value over time")
    if not sales.empty:
        monthly = (
            sales.assign(Month=sales["InvoiceDate"].dt.to_period("M").dt.to_timestamp())
            .groupby("Month", as_index=False)["SalesValue"]
            .sum()
            .sort_values("Month")
        )
        figure = px.line(
            monthly,
            x="Month",
            y="SalesValue",
            markers=True,
            labels={"Month": "Month", "SalesValue": "Sales line value (£)"},
        )
        figure.update_layout(margin={"l": 10, "r": 10, "t": 20, "b": 10})
        st.plotly_chart(figure, use_container_width=True)
    else:
        st.info("No qualifying sales lines are available under the selected filters.")

with right_column:
    st.subheader("Top products by sales line value")
    if not sales.empty and "Description" in sales.columns:
        top_products = (
            sales.dropna(subset=["Description"])
            .groupby("Description", as_index=False)["SalesValue"]
            .sum()
            .sort_values("SalesValue", ascending=False)
            .head(10)
            .sort_values("SalesValue")
        )
        figure = px.bar(
            top_products,
            x="SalesValue",
            y="Description",
            orientation="h",
            labels={"Description": "Product", "SalesValue": "Sales line value (£)"},
        )
        figure.update_layout(margin={"l": 10, "r": 10, "t": 20, "b": 10})
        st.plotly_chart(figure, use_container_width=True)
    else:
        st.info("Product descriptions are unavailable in this file.")

st.subheader("Data-quality overview")
quality_columns = st.columns(4)
quality_columns[0].metric("Source rows", f"{quality['rows']:,}")
quality_columns[1].metric("Duplicate rows", f"{quality['duplicate_rows']:,}")
missing_row_count = int(filtered.isna().any(axis=1).sum())
quality_columns[2].metric("Rows with missing values", f"{missing_row_count:,}")
quality_columns[3].metric("Negative-quantity rows", f"{return_lines:,}")

with st.expander("Missing values by column"):
    missing_values = (
        filtered.isna()
        .sum()
        .rename("Missing values")
        .rename_axis("Column")
        .reset_index()
        .sort_values("Missing values", ascending=False)
    )
    st.dataframe(missing_values, use_container_width=True, hide_index=True)

with st.expander("Preview transaction records"):
    st.dataframe(filtered.head(100), use_container_width=True, hide_index=True)

st.caption(
    "This dashboard is an initial analytical baseline. Interpret results alongside the "
    "documented data rules; the source is historical and does not update automatically."
)
