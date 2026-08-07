"""Narrative layer: turn computed facts into analyst commentary."""

import os

import pandas as pd

import config

from datetime import datetime


def _trailing_run(values):
    """How many consecutive periods at the end share a direction, and which way."""
    run = 0
    direction = None

    for v in reversed(values):
        if pd.isna(v) or v == 0:
            break
        rising = v > 0
        if direction is None:
            direction = rising
        if rising != direction:
            break
        run += 1

    return run, direction


def build_facts(df, series_id):
    """Everything true about one series, with no opinions attached."""
    meta = config.SERIES[series_id]
    g = df[df["series_id"] == series_id].sort_values("date")
    actual = g.dropna(subset=["value"])
    if actual.empty:
        return None

    last = actual.iloc[-1]
    run, rising = _trailing_run(actual["mom_change"].tolist())
    threshold = config.COMMENTARY["material_mom"][meta["kind"]]

    return {
        "series_id": series_id,
        "label": meta["label"],
        "kind": meta["kind"],
        "unit": last["change_unit"],
        "as_of": last["date"],
        "value": last["value"],
        "mom": last["mom_change"],
        "yoy": last["yoy_change"],
        "mom_3m": last["mom_change_3m_avg"],
        "run": run,
        "rising": rising,
        "material": bool(pd.notna(last["mom_change"]) and abs(last["mom_change"]) >= threshold),
        "missing": int(g["value"].isna().sum()),
        "context": config.COMMENTARY["context"].get(series_id, {}),
    }

_ORDINALS = {2: "second", 3: "third", 4: "fourth", 5: "fifth", 6: "sixth"}


def _move(v, unit, digits=2):
    """Phrase a change with direction and magnitude, or say we don't know."""
    if pd.isna(v):
        return "is not available"
    suffix = "%" if unit == "%" else " pp"
    if v > 0:
        return f"rose {abs(v):.{digits}f}{suffix}"
    if v < 0:
        return f"fell {abs(v):.{digits}f}{suffix}"
    return "was unchanged"


def narrate_series(f):
    """One short paragraph: where it is, where it's going, whether that matters."""
    as_of = f"{f['as_of']:%B %Y}"
    unit = f["unit"]
    ctx = f["context"]
    lines = []

    # --- level: what the headline number actually is for this kind of series ---
    if f["kind"] == "index":
        lines.append(
            f"**{f['label']}** {_move(f['yoy'], '%', 1)} over the year to {as_of}; "
            f"on the month it {_move(f['mom'], unit)}."
        )
    elif f["kind"] == "rate":
        lines.append(
            f"**{f['label']}** stood at {f['value']:.1f}% in {as_of}, "
            f"{_move(f['mom'], unit, 1)} from the prior month and "
            f"{_move(f['yoy'], unit, 1)} from a year earlier."
        )
    else:
        lines.append(
            f"**{f['label']}** reached {f['value']:,.0f} in {as_of}, "
            f"{_move(f['mom'], unit)} on the month and {_move(f['yoy'], unit, 1)} on the year."
        )

    # --- trend: one print is an event, three is a direction ---
    if f["run"] >= config.COMMENTARY["trend_run_length"]:
        word = _ORDINALS.get(f["run"], f"{f['run']}th")
        lines.append(
            f"That is the {word} consecutive month moving the same way, "
            f"averaging {f['mom_3m']:+.2f}{'%' if unit == '%' else ' pp'} over three months."
        )
    elif not f["material"]:
        lines.append("The move is within normal month-to-month variation.")

    # --- context: measured against an assumption stated in config ---
    sid = f["series_id"]
    if sid == "CPIAUCSL" and pd.notna(f["yoy"]):
        if f["yoy"] >= ctx["elevated_yoy"]:
            lines.append(
                f"At {f['yoy']:.1f}%, inflation remains above the Fed's {ctx['target_yoy']:.0f}% "
                f"target by a margin that historically keeps policy restrictive."
            )
        elif f["yoy"] <= ctx["target_yoy"]:
            lines.append(f"That is at or below the Fed's {ctx['target_yoy']:.0f}% target.")
    elif sid == "UNRATE":
        if f["value"] >= ctx["elevated"]:
            lines.append("That is elevated relative to the post-2015 range and worth watching.")
        elif f["value"] <= ctx["healthy"]:
            lines.append("That remains consistent with a tight labour market.")
    elif sid == "PAYEMS" and pd.notna(f["mom"]) and f["mom"] < ctx["weak_mom_pct"]:
        lines.append("Job growth at this pace is close to flat once population growth is accounted for.")
    elif sid == "RSAFS" and pd.notna(f["yoy"]) and f["yoy"] >= ctx["strong_yoy"]:
        lines.append("Consumer demand is still growing faster than prices, which supports real spending.")

    # --- honesty about gaps ---
    if f["missing"]:
        lines.append(
            f"_Note: {f['missing']} observation(s) missing from this series; "
            f"changes spanning the gap are not computed._"
        )

    return " ".join(lines)

def cross_series_note(facts):
    """Observations that only exist in the relationships between series."""
    notes = []
    cpi = facts.get("CPIAUCSL")
    retail = facts.get("RSAFS")
    unrate = facts.get("UNRATE")
    payems = facts.get("PAYEMS")

    # nominal spending vs. prices — the real-demand question
    if cpi and retail and pd.notna(cpi["yoy"]) and pd.notna(retail["yoy"]):
        real = retail["yoy"] - cpi["yoy"]
        if real > 0:
            notes.append(
                f"Retail sales are growing {retail['yoy']:.1f}% year over year against "
                f"{cpi['yoy']:.1f}% inflation, implying roughly {real:.1f}% real demand growth — "
                f"consumers are buying more, not just paying more."
            )
        else:
            notes.append(
                f"Retail sales growth of {retail['yoy']:.1f}% trails {cpi['yoy']:.1f}% inflation, "
                f"implying real spending is contracting by about {abs(real):.1f}%. "
                f"Nominal sales growth here is a price effect, not a demand story."
            )

    # the two labour surveys disagreeing is itself the signal —
    # but only when both moves are big enough to mean anything
    if unrate and payems and pd.notna(unrate["mom"]) and pd.notna(payems["mom"]):
        both_material = unrate["material"] and payems["material"]

        if not both_material:
            notes.append(
                f"Labor market indicators were broadly stable: unemployment "
                f"{_move(unrate['mom'], 'pp', 1)} and payrolls {_move(payems['mom'], '%')}, "
                f"both within the range where month-to-month movement is noise."
            )
        elif unrate["mom"] > 0 and payems["mom"] > 0:
            notes.append(
                "Unemployment and payrolls both rose materially in the same month. These come "
                "from two different surveys — households and employers — and they diverge when "
                "labor force participation is climbing. Read it as more people looking, "
                "not fewer people working."
            )
        elif unrate["mom"] < 0 and payems["mom"] < 0:
            notes.append(
                "Unemployment fell while payrolls also fell, both by material margins — a "
                "combination that usually means people leaving the labor force rather than "
                "finding jobs. A falling unemployment rate is not good news in this configuration."
            )

    return notes

def what_to_watch(facts):
    """Explicit falsifiers: what would change the read above."""
    items = []
    cpi = facts.get("CPIAUCSL")
    unrate = facts.get("UNRATE")
    payems = facts.get("PAYEMS")

    if cpi and pd.notna(cpi["mom_3m"]):
        items.append(
            f"CPI three-month average is {cpi['mom_3m']:+.2f}%. Two consecutive prints "
            f"below zero would break the current trend read and argue the annual rate "
            f"is about to fall faster than the year-over-year figure suggests."
        )

    if unrate and payems:
        items.append(
            "A month where unemployment rises and payrolls fall together would resolve "
            "the survey divergence in the worse direction and change the labour read materially."
        )

    items.append(
        "All figures are subject to revision. Payrolls in particular are revised twice, "
        "and the first print is the least reliable one in this report."
    )

    return items

def write_markdown(df):
    """Assemble the full narrative and write it to disk. Returns the path."""
    facts = {sid: build_facts(df, sid) for sid in config.SERIES}
    facts = {sid: f for sid, f in facts.items() if f is not None}

    lines = [
        "# Economic Conditions Summary",
        "",
        f"_Generated {datetime.now():%Y-%m-%d %H:%M}. "
        f"Source: FRED, Federal Reserve Bank of St. Louis._",
        "",
        "## At a glance",
        "",
        "| Series | As Of | Latest | MoM | YoY |",
        "|---|---|---|---|---|",
    ]

    for f in facts.values():
        u = "%" if f["unit"] == "%" else " pp"
        mom = "n/a" if pd.isna(f["mom"]) else f"{f['mom']:+.2f}{u}"
        yoy = "n/a" if pd.isna(f["yoy"]) else f"{f['yoy']:+.2f}{u}"
        lines.append(
            f"| {f['label']} | {f['as_of']:%b %Y} | {f['value']:,.2f} | {mom} | {yoy} |"
        )

    lines += ["", "## Analyst commentary", ""]
    for f in facts.values():
        lines += [narrate_series(f), ""]

    cross = cross_series_note(facts)
    if cross:
        lines += ["## Cross-series read", ""]
        lines += [f"- {note}" for note in cross]
        lines.append("")

    lines += ["## What to watch", ""]
    lines += [f"- {item}" for item in what_to_watch(facts)]
    lines.append("")

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    path = os.path.join(config.OUTPUT_DIR, config.MARKDOWN_NAME)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    return path