# econ-report

An automated economic reporting pipeline. Pulls four macro series from the FRED API,
computes month-over-month and year-over-year changes, and delivers a formatted Excel
workbook plus a written analyst commentary.

Built as a working example of the pattern behind every reporting pipeline:
**source → extract → transform → deliver.**

## What it produces

| Output | Contents |
|---|---|
| `output/econ_report.xlsx` | Summary, full data, change history, and a provenance sheet |
| `output/econ_summary.md` | At-a-glance table plus written commentary and cross-series analysis |

Series tracked: CPI, unemployment rate, nonfarm payrolls, and advance retail sales.

## Setup

Requires Python 3.11+ and a free [FRED API key](https://fredaccount.stlouisfed.org/apikeys).

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
[Environment]::SetEnvironmentVariable("FRED_API_KEY", "your_key_here", "User")
```

The key is read from the environment and never written to disk.

## Run

```powershell
python main.py
```

## Design notes

**Rates and levels are not the same kind of number.** Unemployment moving 4.1% → 4.3%
is +0.2 percentage points, not +4.9%. Each series declares a `kind` in `config.py`,
which drives both the arithmetic and how changes are labeled.

**Year-over-year is matched on date, not row count.** Twelve rows back is only one year
back for monthly data. Date-matching means adding a quarterly or weekly series requires
no change to the calculation.

**Commentary is rules-driven and gated on materiality.** Thresholds live in `config.py`
so the assumptions behind every claim are visible and challengeable. Immaterial moves
are reported as immaterial rather than dressed up as news.

**Provenance travels with the deliverable.** The Metadata sheet records run time, source,
row counts, and missing observations, so the workbook can answer "is this current and
where did it come from" without its author present.

## Structure

```
config.py       every configurable value; nothing else
extract.py      FRED API -> raw observations
transform.py    raw observations -> tidy frame with MoM/YoY
report.py       frame -> formatted Excel workbook
commentary.py   frame -> written narrative
main.py         orchestration
```

## Future work

- Replace the rules-based commentary with a hybrid layer: rules compute the facts and
  flags, an LLM phrases what the rules have already established. Keeps the analysis
  auditable while improving the prose.
- Add quarterly GDP to exercise the mixed-frequency path.
- Schedule via Task Scheduler for a daily morning run.