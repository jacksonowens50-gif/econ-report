"""Transform layer: raw observations -> tidy frame with derived change metrics."""

import pandas as pd
from dateutil.relativedelta import relativedelta
import config


def parse_observations(observations, series_id):
    """Turn raw FRED observation dicts into clean records for one series."""
    meta = config.SERIES[series_id]
    records = []
    missing = 0

    for obs in observations:
        raw_value = obs.get("value")
        raw_date = obs.get("date")

        if raw_date is None:
            continue

        if raw_value in (".", "", None):
            missing += 1
            value = None
        else:
            try:
                value = float(raw_value)
            except ValueError:
                missing += 1
                value = None

        records.append({
            "date": raw_date,
            "series_id": series_id,
            "series_name": meta["name"],
            "label": meta["label"],
            "kind": meta["kind"],
            "value": value,
        })

    if missing:
        print(f"  [{series_id}] {missing} missing value(s) kept as null")

    return records

def build_frame(raw_by_series):
    """Combine per-series records into one tidy long-format DataFrame."""
    records = []
    for series_id, observations in raw_by_series.items():
        records.extend(parse_observations(observations, series_id))

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["series_name", "date"]).reset_index(drop=True)
    return df

def _change(current, prior, kind):
    """Express a change the way its series type demands."""
    if kind == "rate":
        return current - prior          # percentage POINTS
    return (current / prior - 1) * 100  # percent


def add_changes(df):
    """Add prior-period and year-ago comparisons, per series."""
    frames = []

    for _, group in df.groupby("series_name", sort=False):
        g = group.sort_values("date").copy()
        kind = g["kind"].iloc[0]

        # prior period: the row above, within this series only
        g["prior_value"] = g["value"].shift(1)

        # year ago: matched on DATE, not on a row count
        lookup = g.set_index("date")["value"]
        g["value_year_ago"] = [
            lookup.get(d - relativedelta(years=1)) for d in g["date"]
        ]

        g["mom_change"] = _change(g["value"], g["prior_value"], kind)
        g["yoy_change"] = _change(g["value"], g["value_year_ago"], kind)
        g["mom_change_3m_avg"] = g["mom_change"].rolling(3).mean()
        g["change_unit"] = "pp" if kind == "rate" else "%"

        frames.append(g)

    return pd.concat(frames, ignore_index=True)

def to_wide(df):
    """Pivot to dates-down / series-across for the human-readable sheet."""
    wide = df.pivot(index="date", columns="series_name", values="value")
    return wide.sort_index()

def latest_snapshot(df):
    """One row per series: its most recent actual reading and how it changed."""
    rows = []

    for _, group in df.groupby("series_name", sort=False):
        actual = group.dropna(subset=["value"]).sort_values("date")
        if actual.empty:
            continue

        last = actual.iloc[-1]
        rows.append({
            "Series": last["label"],
            "As Of": last["date"],
            "Value": last["value"],
            "Units": config.SERIES[last["series_id"]]["units"],
            f"MoM": last["mom_change"],
            f"YoY": last["yoy_change"],
            "Change Unit": last["change_unit"],
        })

    return pd.DataFrame(rows)