"""econ-report: pull FRED series, compute changes, deliver Excel + narrative."""

import commentary
import config
import extract
import report
import transform


def main():
    config.validate()

    print(f"econ-report | {len(config.SERIES)} series | "
          f"{config.START_DATE:%Y-%m-%d} to {config.END_DATE:%Y-%m-%d}")

    api_key = extract.get_api_key()

    try:
        raw = extract.fetch_all(api_key)
    except extract.ExtractError as e:
        raise SystemExit(f"Run aborted: {e}")

    df = transform.add_changes(transform.build_frame(raw))

    excel_path = report.write_excel(
        snapshot=transform.latest_snapshot(df),
        wide=transform.to_wide(df),
        changes=report.build_changes_table(df),
        metadata=report.build_metadata(df),
    )
    markdown_path = commentary.write_markdown(df)

    print(f"\nWrote {excel_path}")
    print(f"Wrote {markdown_path}")


if __name__ == "__main__":
    main()