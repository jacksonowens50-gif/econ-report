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

# ---------- commentary thresholds ----------
# Every number a reasonable person could argue with lives here.
# When a client says "3% isn't elevated in this environment," that's a
# one-line change, not a hunt through prose.
COMMENTARY = {
    # how many consecutive same-direction prints before we call it a trend
    "trend_run_length": 3,

    # a move smaller than this is noise, not news (% for index/level, pp for rate)
    "material_mom": {
        "index": 0.25,
        "rate": 0.2,
        "level": 0.5,
    },

    # series-specific reference points the narrative can lean on
    "context": {
        "CPIAUCSL": {"target_yoy": 2.0, "elevated_yoy": 3.0},
        "UNRATE": {"elevated": 4.5, "healthy": 4.0},
        "PAYEMS": {"weak_mom_pct": 0.05},
        "RSAFS": {"strong_yoy": 4.0},
    },

}
# ---------- validation ----------
VALID_KINDS = {"index", "rate", "level"}
REQUIRED_KEYS = {"name", "label", "kind", "units"}


def validate():
    """Fail before the first network call, not after the last one."""
    problems = []

    for series_id, meta in SERIES.items():
        missing = REQUIRED_KEYS - meta.keys()
        if missing:
            problems.append(f"{series_id}: missing key(s) {sorted(missing)}")

        kind = meta.get("kind")
        if kind is not None and kind not in VALID_KINDS:
            problems.append(f"{series_id}: kind '{kind}' is not one of {sorted(VALID_KINDS)}")

    names = [m["name"] for m in SERIES.values() if "name" in m]
    dupes = {n for n in names if names.count(n) > 1}
    if dupes:
        problems.append(f"duplicate series name(s): {sorted(dupes)}")

    if problems:
        raise SystemExit(
            "config.py is invalid:\n  " + "\n  ".join(problems)
        )