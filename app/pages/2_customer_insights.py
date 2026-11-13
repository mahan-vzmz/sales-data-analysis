"""Customer value, repeat purchasing and saved inactivity probabilities."""

from datetime import date

import pandas as pd
import streamlit as st

from app.ui.charts import show_download, show_empty_result
from app.ui.data import (
    MART_DIMENSIONS,
    DataUnavailable,
    app_settings,
    load_model_artifact,
    read_mart,
)
from app.ui.filters import sidebar_filters
from sales_analytics.analytics.cohorts import build_retention_matrix
from sales_analytics.analytics.rfm import build_rfm

st.title("Customer insights")
st.caption("Which customers buy again, and where is inactivity concentrated?")
settings = app_settings()
mart = "mart_customer_360"
try:
    source = read_mart(settings, mart)
    filters = sidebar_filters(source, MART_DIMENSIONS[mart])
    customers = read_mart(settings, mart, filters)
except DataUnavailable as exc:
    st.info(str(exc))
    st.stop()
if customers.empty:
    show_empty_result()
    st.stop()

latest = source["last_purchase_date"].max()
analysis_date = latest.date() if pd.notna(latest) else date.today()
st.subheader("Customer value and inactivity")
st.caption(
    f"Recency reference: {analysis_date}. RFM scores are relative to the selected population."
)
rfm = build_rfm(customers, analysis_date)
segment_counts = rfm.groupby("segment").size().rename("customers")
st.bar_chart(
    segment_counts,
    x_label="RFM segment",
    y_label="Customers",
    alt="Customer counts by RFM segment",
)
st.subheader("Days since last purchase")
recency_bands = (
    pd.cut(
        rfm["recency_days"],
        bins=[-1, 29, 89, 179, float("inf")],
        labels=["0–29", "30–89", "90–179", "180+"],
    )
    .cat.add_categories(["No completed purchases"])
    .fillna("No completed purchases")
)
st.bar_chart(
    recency_bands.value_counts(sort=False).rename("customers"),
    x_label="Days since last purchase",
    y_label="Customers",
    alt="Customer counts by time since last completed purchase",
)
show_download(
    rfm, "customer-scores.csv", alt="Customer RFM scores and days since last purchase"
)

st.subheader("Cohort retention")
try:
    purchases = read_mart(settings, "mart_cohort_base")
except DataUnavailable as exc:
    st.info(str(exc))
else:
    last_observed = pd.to_datetime(purchases["order_month"]).max()
    cohort = build_retention_matrix(
        purchases.loc[purchases["customer_id"].isin(customers["customer_id"])],
        observation_end=last_observed.date() if pd.notna(last_observed) else None,
    )
    if cohort.matrix.empty:
        st.info("No completed purchases for this cohort selection.")
    else:
        st.dataframe(
            cohort.matrix, alt="Share of original cohort making a purchase by month age"
        )
        st.caption("Rates are fractions of the original cohort. Month zero is 1.00.")

st.subheader("Saved inactivity probabilities")
try:
    artifact = load_model_artifact(settings, "propensity")
    probabilities = pd.DataFrame(artifact.get("predictions", []))
    if not {"customer_id", "cutoff", "probability"} <= set(probabilities.columns):
        raise DataUnavailable("Propensity artifact has no usable probability rows.")
except DataUnavailable as exc:
    st.info(str(exc))
else:
    probabilities = probabilities.loc[
        probabilities["customer_id"].isin(customers["customer_id"])
    ]
    if probabilities.empty:
        show_empty_result()
    else:
        st.caption(
            f"Saved evaluation probabilities for {artifact.get('horizon_days', 'the model horizon')} days without a completed purchase."
        )
        show_download(
            probabilities,
            "inactivity-probabilities.csv",
            alt="Held-out inactivity probabilities",
        )
