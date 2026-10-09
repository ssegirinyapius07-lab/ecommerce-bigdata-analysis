"""Streamlit dashboard for e-commerce transaction analysis."""

from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from ecommerce_analysis.analysis import (
    build_quality_summary,
    build_sales_summary,
    country_sales_summary,
    customer_rfm_summary,
    high_quantity_lines,
    monthly_sales_summary,
    prepare_transactions,
    top_products_summary,
)
from ecommerce_analysis.data_loader import load_transactions

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_DATASET = PROJECT_ROOT / "data" / "raw" / "Online Retail.xlsx"


@st.cache_data(show_spinner="Loading transaction data...")
def load_local_dataset(path: str, modified_time: float) -> pd.DataFrame:
    """Cache local data using its modification time to detect file updates."""
    del modified_time
    return load_transactions(path)


@st.cache_data(show_spinner="Reading uploaded transaction data...")
def load_uploaded_dataset(filename: str, content: bytes) -> pd.DataFrame:
    """Cache uploaded data by filename and content."""
    file_buffer = BytesIO(content)
    file_buffer.name = filename  # type: ignore[attr-defined]
    return load_transactions(file_buffer)


st.set_page_config(
    page_title="E-commerce Analytics",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("E-commerce Customer Behaviour and Sales Analysis")
st.caption(
    "Sales performance, customer purchasing patterns, product trends, "
    "and transaction data quality."
)

with st.sidebar:
    st.header("Data source")
    uploaded_file = st.file_uploader(
        "Upload transaction data",
        type=["xlsx", "csv"],
        help=(
            "Upload a CSV or Excel file. For repeated analysis, keep the standard workbook "
            "in data/raw/."
        ),
    )

if uploaded_file is not None:
    try:
        source_data = load_uploaded_dataset(
            uploaded_file.name, uploaded_file.getvalue()
        )
        source_label = uploaded_file.name
    except Exception as error:  # noqa: BLE001 - file parsers raise several exception types.
        st.error(f"Unable to read the uploaded file: {error}")
        st.stop()
elif DEFAULT_DATASET.is_file():
    try:
        source_data = load_local_dataset(
            str(DEFAULT_DATASET), DEFAULT_DATASET.stat().st_mtime
        )
        source_label = str(DEFAULT_DATASET.relative_to(PROJECT_ROOT))
    except Exception as error:  # noqa: BLE001 - file parsers raise several exception types.
        st.error(f"Unable to read the local dataset: {error}")
        st.stop()
else:
    st.info("No transaction dataset has been selected.")
    st.markdown(
        "Download the [UCI Online Retail dataset]"
        "(https://archive.ics.uci.edu/dataset/352/online+retail) and save the workbook as "
        "**data/raw/Online Retail.xlsx**, or upload a CSV/XLSX file using the sidebar."
    )
    st.stop()

if source_data.empty:
    st.warning("The selected file contains no transaction records.")
    st.stop()

try:
    transactions = prepare_transactions(source_data)
except (ValueError, TypeError) as error:
    st.error(f"The selected file does not contain the required transaction fields: {error}")
    st.stop()

valid_dates = transactions["InvoiceDate"].dropna()
if valid_dates.empty:
    st.error("The selected file does not contain any valid invoice dates.")
    st.stop()

min_date = valid_dates.min().date()
max_date = valid_dates.max().date()
dataset_quality = build_quality_summary(source_data)

with st.sidebar:
    st.divider()
    st.header("Analysis filters")
    selected_date_range = st.date_input(
        "Invoice date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        help="Choose the invoice-date interval included in the analysis.",
    )

    if "Country" in transactions.columns:
        country_options = sorted(
            transactions["Country"].dropna().astype(str).unique().tolist()
        )
        selected_countries = st.multiselect(
            "Countries",
            options=country_options,
            default=[],
            help="Leave empty to include all countries.",
        )
    else:
        selected_countries = []

filtered = transactions.copy()
if isinstance(selected_date_range, (tuple, list)) and len(selected_date_range) == 2:
    start_date, end_date = selected_date_range
    filtered = filtered.loc[
        filtered["InvoiceDate"].between(
            pd.Timestamp(start_date),
            pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(nanoseconds=1),
        )
    ]

if selected_countries and "Country" in filtered.columns:
    filtered = filtered.loc[filtered["Country"].astype(str).isin(selected_countries)]

st.caption(f"Data source: {source_label}")
st.caption(
    f"Selected period: {selected_date_range[0] if isinstance(selected_date_range, (tuple, list)) else selected_date_range} "
    f"to {selected_date_range[1] if isinstance(selected_date_range, (tuple, list)) and len(selected_date_range) == 2 else selected_date_range}"
)

sales_summary = build_sales_summary(filtered)
sales_line_value = float(sales_summary["qualifying_sales_line_value"])
invoice_count = int(sales_summary["sales_invoices"])
identified_customers = int(sales_summary.get("identified_customers", 0))
country_count = int(sales_summary.get("countries", 0))

metric_columns = st.columns(4)
metric_columns[0].metric("Qualifying sales line value", f"£{sales_line_value:,.2f}")
metric_columns[1].metric("Sales invoices", f"{invoice_count:,}")
metric_columns[2].metric("Identified customers", f"{identified_customers:,}")
metric_columns[3].metric("Countries with sales", f"{country_count:,}")

st.caption(
    "Sales line value is not net revenue. This view excludes cancellation-marked invoices, "
    "non-positive quantities, negative prices, and invalid dates. Returns and duplicate "
    "records are not automatically removed or netted against sales."
)

overview_tab, product_tab, customer_tab, quality_tab = st.tabs(
    ["Overview", "Products", "Customers", "Data quality"]
)

with overview_tab:
    st.subheader("Monthly sales performance")
    monthly = monthly_sales_summary(filtered)
    if monthly.empty:
        st.info("No qualifying sales lines exist for the selected filters.")
    else:
        monthly_figure = px.line(
            monthly,
            x="Month",
            y="SalesValue",
            markers=True,
            labels={"Month": "Month", "SalesValue": "Sales line value (GBP)"},
        )
        monthly_figure.update_layout(
            margin={"l": 10, "r": 10, "t": 25, "b": 10},
            hovermode="x unified",
        )
        st.plotly_chart(monthly_figure, use_container_width=True)

        st.subheader("Monthly activity")
        st.dataframe(
            monthly.rename(
                columns={
                    "Month": "Month",
                    "SalesValue": "Sales line value (GBP)",
                    "InvoiceCount": "Sales invoices",
                    "CustomerCount": "Identified customers",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("Country performance")
    countries = country_sales_summary(filtered)
    if countries.empty:
        st.info("Country data is unavailable for the selected records.")
    else:
        country_chart_data = countries.head(10).sort_values("SalesValue")
        country_figure = px.bar(
            country_chart_data,
            x="SalesValue",
            y="Country",
            orientation="h",
            labels={"SalesValue": "Sales line value (GBP)", "Country": "Country"},
        )
        country_figure.update_layout(margin={"l": 10, "r": 10, "t": 25, "b": 10})
        st.plotly_chart(country_figure, use_container_width=True)
        st.dataframe(countries.head(20), use_container_width=True, hide_index=True)

with product_tab:
    st.subheader("Top products by qualifying sales line value")
    products = top_products_summary(filtered, limit=10)
    if products.empty:
        st.info("No product sales are available under the selected filters.")
    else:
        product_chart_data = products.sort_values("SalesValue")
        product_figure = px.bar(
            product_chart_data,
            x="SalesValue",
            y="Description",
            orientation="h",
            hover_data=["StockCode", "QuantitySold", "InvoiceCount"],
            labels={
                "SalesValue": "Sales line value (GBP)",
                "Description": "Product",
                "QuantitySold": "Quantity sold",
                "InvoiceCount": "Sales invoices",
            },
        )
        product_figure.update_layout(margin={"l": 10, "r": 10, "t": 25, "b": 10})
        st.plotly_chart(product_figure, use_container_width=True)
        st.dataframe(products, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("High-quantity transaction review")
    st.write(
        "These records are flagged for investigation only. The threshold does not prove "
        "that an order is incorrect, and flagged records remain included in the analysis."
    )
    quantity_threshold = st.number_input(
        "Flag sale lines with quantity at or above",
        min_value=100,
        max_value=100000,
        value=1000,
        step=100,
    )
    exceptions = high_quantity_lines(
        filtered, minimum_quantity=int(quantity_threshold)
    )
    if exceptions.empty:
        st.info("No qualifying sales lines meet the selected quantity threshold.")
    else:
        st.dataframe(exceptions, use_container_width=True, hide_index=True)

with customer_tab:
    st.subheader("Customer purchasing behaviour")
    if "CustomerID" not in filtered.columns:
        st.info("The selected file does not contain customer identifiers.")
    else:
        customers = customer_rfm_summary(filtered)
        if customers.empty:
            st.info("No identified customers have qualifying sales in the selected period.")
        else:
            customer_metrics = st.columns(3)
            customer_metrics[0].metric("Identified customers", f"{len(customers):,}")
            customer_metrics[1].metric(
                "Repeat customers",
                f"{int(customers['Frequency'].gt(1).sum()):,}",
            )
            customer_metrics[2].metric(
                "Customer sales line value",
                f"£{customers['Monetary'].sum():,.2f}",
            )

            st.caption(
                "Recency is measured from one day after the latest qualifying sale date "
                "within the selected data. Frequency counts distinct invoices; monetary "
                "value sums qualifying sales line values for customers with an ID."
            )

            scatter_figure = px.scatter(
                customers,
                x="Frequency",
                y="Monetary",
                hover_data=["CustomerID", "RecencyDays", "AverageInvoiceValue"],
                labels={
                    "Frequency": "Distinct sales invoices",
                    "Monetary": "Sales line value (GBP)",
                    "RecencyDays": "Days since last purchase",
                    "AverageInvoiceValue": "Average invoice value (GBP)",
                },
                title="Customer frequency and monetary value",
            )
            scatter_figure.update_layout(margin={"l": 10, "r": 10, "t": 45, "b": 10})
            st.plotly_chart(scatter_figure, use_container_width=True)

            st.subheader("Customers ranked by sales line value")
            st.dataframe(customers.head(25), use_container_width=True, hide_index=True)

with quality_tab:
    st.subheader("Source dataset quality")
    st.caption(
        "These indicators describe the entire selected source file, independent of "
        "the date and country filters."
    )
    quality_metrics = st.columns(4)
    quality_metrics[0].metric("Source records", f"{dataset_quality['rows']:,}")
    quality_metrics[1].metric(
        "Exact duplicate rows", f"{dataset_quality['duplicate_rows']:,}"
    )
    quality_metrics[2].metric(
        "Missing customer IDs",
        f"{dataset_quality.get('missing_customer_ids', 0):,}",
    )
    quality_metrics[3].metric(
        "Missing descriptions",
        f"{dataset_quality.get('missing_descriptions', 0):,}",
    )

    missing_values = (
        source_data.isna()
        .sum()
        .rename("Missing values")
        .rename_axis("Column")
        .reset_index()
        .sort_values("Missing values", ascending=False)
    )
    st.subheader("Missing values by column")
    st.dataframe(missing_values, use_container_width=True, hide_index=True)

    issue_columns = st.columns(3)
    issue_columns[0].metric(
        "Cancellation rows", f"{dataset_quality.get('cancellation_rows', 0):,}"
    )
    issue_columns[1].metric(
        "Negative-quantity rows",
        f"{dataset_quality.get('negative_quantity_rows', 0):,}",
    )
    issue_columns[2].metric(
        "Zero-price rows", f"{dataset_quality.get('zero_unit_price_rows', 0):,}"
    )

    st.warning(
        "Exact duplicates, cancellation rows, and negative-quantity rows can overlap. "
        "Review the records and their business meaning before removing or adjusting them."
    )

    with st.expander("Preview source records"):
        st.dataframe(source_data.head(100), use_container_width=True, hide_index=True)

st.caption(
    "Source: UCI Online Retail historical transaction data. December 2011 is incomplete "
    "in this dataset (records end on 9 December 2011). Results describe this source "
    "dataset and should not be interpreted as current market conditions."
)
