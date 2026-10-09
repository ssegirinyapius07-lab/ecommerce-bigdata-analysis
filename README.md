# E-commerce Customer Behaviour and Sales Analysis

A reproducible Python analytics project for exploring retail transactions, understanding customer purchasing patterns, and presenting business findings through an interactive dashboard. A separate Apache Spark stage will demonstrate distributed processing and compare its results with the Pandas workflow.

## Project objectives

- Inspect source data and make data-quality issues visible.
- Document the treatment of cancelled invoices, returns, invalid prices, and missing customer identifiers.
- Analyse sales line value, monthly patterns, product performance, customer activity, and countries represented in the source data.
- Present metrics and charts in an interactive dashboard.
- Add a PySpark processing path as a separate, testable stage.
- Keep setup, tests, data handling, and Git history reproducible.

## Dataset

The first source is the [UCI Online Retail dataset](https://archive.ics.uci.edu/dataset/352/online+retail), containing 541,909 historical transaction records from a UK-based online retailer between 1 December 2010 and 9 December 2011.

Download the Excel workbook from UCI and save it locally as:

```text
data/raw/Online Retail.xlsx
```

**The dataset is historical, not a live feed.** The application can load the same local file repeatedly. Later, additional CSV or Excel extracts can be loaded through the same ingestion path to refresh the analysis. Data will not update automatically unless a new file or live data source is supplied.

Raw and generated data files are intentionally excluded from Git. This keeps the repository smaller and avoids committing source data or local analysis output.

## Technology

- Python 3.11 or newer
- Pandas for tabular analysis
- OpenPyXL for Excel workbook input
- Streamlit for the dashboard
- Plotly for interactive visualisations
- Pytest and Ruff for testing and code-quality checks
- Apache PySpark as an optional later stage; its local runtime needs a supported Java version

## Repository layout

```text
ecommerce-bigdata-analysis/
├── .github/workflows/ci.yml
├── data/
│   ├── raw/                    # Local source files; not committed
│   └── processed/              # Local generated files; not committed
├── src/ecommerce_analysis/
│   ├── __init__.py
│   ├── analysis.py
│   └── data_loader.py
├── tests/
│   ├── test_analysis.py
│   └── test_data_loader.py
├── app.py
├── src/inspect_data.py
├── src/analyze_data.py
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── requirements-bigdata.txt
└── README.md
```

## Windows setup

Run these commands from PowerShell in the cloned repository directory:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

Inspect data quality and then print a first sales summary after placing the workbook in `data/raw/`:

```powershell
.\.venv\Scripts\python.exe src\inspect_data.py
.\.venv\Scripts\python.exe src\analyze_data.py
```

Start the dashboard after placing the workbook in `data/raw/`:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

The dataset can also be selected through the dashboard's upload control. The local workbook is preferred for repeated analysis.

## Data interpretation

The first dashboard uses the term **qualifying sales line value** for the sum of line values on non-cancellation rows with a positive quantity, a non-negative unit price, and a valid invoice date. It is not presented as final net revenue: returns and cancelled invoices are identified separately so that their treatment can be reviewed explicitly. Any later data cleaning will be documented and tested rather than silently discarding records.

Customer identifiers can be missing in the source data. Customer counts and customer-based results therefore use available identifiers only and should not be treated as complete customer coverage.

## Development roadmap

1. Environment verification and source-data inspection.
2. Data-quality assessment and documented preparation rules.
3. Exploratory analysis of trends, products, customers, and geography.
4. Dashboard filters, charts, and explanatory insights.
5. PySpark implementation and comparison of key calculations with Pandas.
6. Automated tests, performance checks, and presentation documentation.

## Project status

Initial analysis stage: reusable CSV/Excel loading, explicit quality indicators, qualifying-sales summaries, monthly aggregation, ranked products, the dashboard baseline, automated tests, and CI checks. Analysis rules are being extended incrementally and the Spark stage remains planned.
