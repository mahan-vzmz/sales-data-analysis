"""Shared chart and empty-result display."""

import pandas as pd
import streamlit as st


def show_empty_result() -> None:
    st.info("No rows match this selection.")


def show_weekly_units(frame: pd.DataFrame) -> None:
    """Plot ordered units by week and category with accessible labels."""
    if frame.empty:
        show_empty_result()
        return
    st.line_chart(
        frame,
        x="week_start",
        y="ordered_quantity",
        color="category",
        x_label="Week starting",
        y_label="Units ordered",
        alt="Weekly ordered units by product category",
    )
