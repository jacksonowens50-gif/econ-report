"""All configuration for the econ-report pipeline. Nothing else belongs here."""

from datetime import date
from dateutil.relativedelta import relativedelta

# ---------- source ----------
BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

# kind drives BOTH the math and the formatting downstream:
#   "index" -> level is meaningless alone; the YoY % change IS the metric
#   "rate"  -> already a percent; changes are percentage POINTS, not percent
#   "level" -> a count or a dollar amount; percent change is the right read
SERIES = {
    "CPIAUCSL": {
        "name": "cpi",
        "label": "CPI (All Urban Consumers)",
        "kind": "index",
        "units": "Index 1982-84=100",
    },
    "UNRATE": {
        "name": "unemployment_rate",
        "label": "Unemployment Rate",
        "kind": "rate",
        "units": "Percent",
    },
    "PAYEMS": {
        "name": "nonfarm_payrolls",
        "label": "Nonfarm Payroll Employment",
        "kind": "level",
        "units": "Thousands of Persons",
    },
    "RSAFS": {
        "name": "retail_sales",
        "label": "Retail Sales (Advance)",
        "kind": "level",
        "units": "Millions of Dollars",
    },
}

# ---------- reporting window ----------
# Relative, not hardcoded: this is meant to run every morning forever.
# A pinned END_DATE would quietly stop reporting new data the day it passed.
LOOKBACK_YEARS = 11          # 10 years of report + 1 year of runway for YoY
END_DATE = date.today()
START_DATE = END_DATE - relativedelta(years=LOOKBACK_YEARS)

# ---------- request behavior ----------
PAGE_LIMIT = 1000
REQUEST_TIMEOUT = 30
MAX_PAGES = 50

# ---------- output ----------
OUTPUT_DIR = "output"
EXCEL_NAME = "econ_report.xlsx"
MARKDOWN_NAME = "econ_summary.md"