"""Shared filters for dimensions exposed by a Gold mart."""

from dataclasses import dataclass
from datetime import date

import pandas as pd
import streamlit as st


@dataclass(frozen=True)
class Filters:
    """Inclusive dates and exact-match selections; empty tuples select all."""

    start: date | None = None
    end: date | None = None
    channels: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    geographies: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.start is not None and self.end is not None and self.start > self.end:
            raise ValueError("Filter start date must be on or before its end date")


def sidebar_filters(frame: pd.DataFrame, dimensions: dict[str, str]) -> Filters:
    """Render only the dimensions supported by the selected mart."""
    start, end = None, None
    with st.sidebar:
        st.subheader("Filters")
        if "date" in dimensions:
            dates = pd.to_datetime(frame[dimensions["date"]]).dropna()
            if not dates.empty:
                first, last = dates.min().date(), dates.max().date()
                selection = st.date_input(
                    "Date range",
                    (first, last),
                    min_value=first,
                    max_value=last,
                    key="gold_dates",
                )
                if len(selection) != 2:
                    st.info("Select both dates to apply the range.")
                    st.stop()
                start, end = selection

        selected = {}
        for name, label in (
            ("channel", "Sales channel"),
            ("category", "Product category"),
            ("geography", "Customer home city"),
        ):
            if name in dimensions:
                options = sorted(frame[dimensions[name]].dropna().unique().tolist())
                selected[name] = tuple(
                    st.multiselect(label, options, key=f"gold_{name}")
                )
        unavailable = [
            name
            for name in ("date", "channel", "category", "geography")
            if name not in dimensions
        ]
        if unavailable:
            st.caption("Unavailable in this mart: " + ", ".join(unavailable) + ".")

    return Filters(
        start=start,
        end=end,
        channels=selected.get("channel", ()),
        categories=selected.get("category", ()),
        geographies=selected.get("geography", ()),
    )
