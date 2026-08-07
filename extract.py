"""Extract layer: pull raw observations from the FRED API. No interpretation here."""

import os
import requests

import config


class ExtractError(Exception):
    """Raised when FRED returns something we can't work with."""


def get_api_key():
    """Read FRED_API_KEY from the environment, or stop with a clear message."""
    key = os.getenv("FRED_API_KEY")
    if not key:
        raise SystemExit(
            "FRED_API_KEY is not set. Get a free key at "
            "https://fredaccount.stlouisfed.org/apikeys and set it with:\n"
            '  [Environment]::SetEnvironmentVariable("FRED_API_KEY", "your_key", "User")'
        )
    return key


def fetch_series(series_id, api_key):
    """Return all raw observation dicts for one series. Returns [] on failure."""
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": config.START_DATE.isoformat(),
        "observation_end": config.END_DATE.isoformat(),
        "limit": config.PAGE_LIMIT,
        "offset": 0,
    }

    observations = []
    page = 0

    while True:
        try:
            response = requests.get(
                config.BASE_URL, params=params, timeout=config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"  [{series_id}] request failed: {type(e).__name__}")
            return []

        try:
            payload = response.json()
        except ValueError:
            print(f"  [{series_id}] response was not JSON")
            return []

        batch = payload.get("observations")
        if batch is None:
            print(f"  [{series_id}] no 'observations' key in response — check the series ID")
            return []

        observations.extend(batch)
        params["offset"] += len(batch)
        page += 1

        if params["offset"] >= payload.get("count", 0):
            break
        if page >= config.MAX_PAGES:
            print(f"  [{series_id}] hit page cap — returning partial data")
            break

    print(f"  [{series_id}] {len(observations)} observations in {page} page(s)")
    return observations


def fetch_all(api_key):
    """Pull every configured series. Returns {series_id: [raw observations]}."""
    results = {}

    for series_id in config.SERIES:
        observations = fetch_series(series_id, api_key)
        if observations:
            results[series_id] = observations
        else:
            print(f"  [{series_id}] SKIPPED — no data returned")

    if not results:
        raise ExtractError("No data returned for any series. Nothing to report.")

    return results