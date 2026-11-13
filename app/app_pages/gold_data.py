"""Browse the data available to the analytical pages."""

import streamlit as st

from app.ui.charts import show_empty_result, show_weekly_units
from app.ui.data import MART_DIMENSIONS, DataUnavailable, app_settings, read_mart
from app.ui.filters import sidebar_filters

st.title("Gold data")
mart = st.selectbox(
    "Gold mart",
    list(MART_DIMENSIONS),
    index=list(MART_DIMENSIONS).index("mart_forecasting_base"),
    format_func=lambda name: name.removeprefix("mart_").replace("_", " ").capitalize(),
    key="gold_mart",
)
settings = app_settings()
try:
    source = read_mart(settings, mart)
    if source.empty:
        show_empty_result()
        st.stop()
    filters = sidebar_filters(source, MART_DIMENSIONS[mart])
    rows = read_mart(settings, mart, filters)
except DataUnavailable as exc:
    st.info(str(exc))
    st.stop()

if rows.empty:
    show_empty_result()
else:
    if mart == "mart_forecasting_base":
        st.subheader("Weekly ordered units")
        show_weekly_units(rows)
    st.dataframe(rows, hide_index=True, alt="Rows in the selected Gold mart")
