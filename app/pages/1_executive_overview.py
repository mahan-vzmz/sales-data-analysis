"""Executive revenue, profit and returns for the selected sales population."""

import streamlit as st

from app.ui.charts import show_download, show_empty_result
from app.ui.data import MART_DIMENSIONS, DataUnavailable, app_settings, read_mart
from app.ui.filters import sidebar_filters

st.title("Executive overview")
st.caption("Where did revenue and profit come from after returns?")
settings = app_settings()
mart = "mart_sales_detail"
try:
    source = read_mart(settings, mart)
    filters = sidebar_filters(source, MART_DIMENSIONS[mart])
    rows = read_mart(settings, mart, filters)
except DataUnavailable as exc:
    st.info(str(exc))
    st.stop()
if rows.empty:
    show_empty_result()
    st.stop()

revenue = "return_adjusted_revenue"
with st.container(horizontal=True):
    st.metric("Revenue after returns", f"${rows[revenue].sum():,.2f}")
    st.metric("Profit after returns", f"${rows['return_adjusted_profit'].sum():,.2f}")
    st.metric("Returned revenue", f"${rows['returned_revenue'].sum():,.2f}")
st.caption("Returns are attributed to the original purchase date.")
trend = (
    rows.groupby(rows["order_date"].dt.to_period("M").dt.to_timestamp())[
        [revenue, "return_adjusted_profit"]
    ]
    .sum()
    .rename(
        columns={
            revenue: "Revenue after returns",
            "return_adjusted_profit": "Profit after returns",
        }
    )
)
st.subheader("Monthly performance")
st.line_chart(
    trend,
    y_label="USD",
    x_label="Purchase month",
    alt="Monthly revenue and profit after returns",
)
for field, label in (("channel", "Sales channel"), ("home_city", "Customer home city")):
    st.subheader(f"Revenue by {label.lower()}")
    breakdown = rows.groupby(field, as_index=False)[revenue].sum()
    st.bar_chart(
        breakdown,
        x=field,
        y=revenue,
        x_label=label,
        y_label="USD",
        alt=f"Revenue after returns by {label.lower()}",
    )
st.subheader("Sales detail")
show_download(
    rows, "sales-detail.csv", alt="Filtered sales lines and return-adjusted measures"
)
