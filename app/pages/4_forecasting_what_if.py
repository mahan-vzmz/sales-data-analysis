"""Saved forecast backtest and a bounded price and discount scenario."""

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

st.title("Forecasting & What-If")
st.caption(
    "How did the forecast perform, and what revenue would the same units imply at another price or discount?"
)
settings = app_settings()
try:
    artifact = load_model_artifact(settings, "forecast")
    forecast = pd.DataFrame(artifact.get("predictions", []))
    if not {"category", "week_start", "prediction"} <= set(forecast.columns):
        raise DataUnavailable("Forecast artifact has no usable prediction rows.")
    forecast["week_start"] = pd.to_datetime(forecast["week_start"], errors="raise")
    cutoff_value = artifact.get("training_cutoff")
    if not isinstance(cutoff_value, str):
        raise DataUnavailable("Forecast artifact has no valid training cutoff.")
    cutoff = pd.Timestamp(cutoff_value)
    if pd.isna(cutoff):
        raise DataUnavailable("Forecast artifact has no valid training cutoff.")
except (DataUnavailable, ValueError) as exc:
    st.info(str(exc))
    st.stop()

st.caption(f"Model: {artifact['model']} · Last training week: {cutoff.date()}")
st.subheader("Backtest errors")
metrics = pd.DataFrame(artifact.get("fold_metrics", []))
if not metrics.empty:
    st.dataframe(
        metrics, hide_index=True, alt="MAE and sMAPE by backtest fold and model"
    )
else:
    st.info("No fold metrics are available in this artifact.")

dimensions = MART_DIMENSIONS["mart_forecasting_base"]
filters = sidebar_filters(forecast, dimensions)
selected = forecast.loc[
    forecast["week_start"].dt.date.between(filters.start, filters.end)
]
if filters.categories:
    selected = selected.loc[selected["category"].isin(filters.categories)]
if selected.empty:
    show_empty_result()
    st.stop()
st.subheader("Held-out forecast")
st.line_chart(
    selected,
    x="week_start",
    y="prediction",
    color="category",
    x_label="Week starting",
    y_label="Ordered units",
    alt="Held-out ordered-unit predictions by product category",
)
show_download(selected, "forecast.csv", alt="Filtered held-out forecast predictions")

st.subheader("Demand and revenue scenario")
st.caption("Scenario estimate — not causal impact")
category = st.selectbox("Scenario category", sorted(selected["category"].unique()))
try:
    history = read_mart(settings, "mart_forecasting_base")
except DataUnavailable as exc:
    st.info(str(exc))
    st.stop()
history = history.loc[
    history["category"].eq(category) & history["week_start"].le(cutoff)
].sort_values("week_start")
commercial_history = history[["average_unit_price", "effective_discount_rate"]].dropna()
if commercial_history.empty:
    st.info(
        "No observed prices and discounts are available before the training cutoff for this category."
    )
    st.stop()


def scenario_value(
    column: str, label: str, key: str, *, multiplier: float = 1
) -> float:
    observed = commercial_history[column] * multiplier
    minimum, maximum, baseline = (
        float(observed.min()),
        float(observed.max()),
        float(observed.iloc[-1]),
    )
    if minimum == maximum:
        st.write(f"{label}: {baseline:g} (fixed observed value)")
        return baseline / multiplier
    return st.slider(label, minimum, maximum, baseline, key=key) / multiplier


st.caption("Input ranges use observations through the training cutoff.")
price = scenario_value("average_unit_price", "Unit price (USD)", "scenario_price")
discount = scenario_value(
    "effective_discount_rate", "Discount (%)", "scenario_discount", multiplier=100
)
baseline = commercial_history.iloc[-1]
scenario = selected.loc[selected["category"].eq(category)].copy()
scenario["scenario_units"] = scenario["prediction"].astype(float)
if artifact["model"] == "seasonal_naive":
    st.caption(
        "Changing reference-week units changes the seasonal-naive forecast for the selected week."
    )
    target_week = st.selectbox(
        "Target week for demand scenario",
        sorted(scenario["week_start"].dt.strftime("%Y-%m-%d").unique()),
    )
    target = scenario["week_start"].eq(pd.Timestamp(target_week))
    reference_units = float(scenario.loc[target, "prediction"].iloc[0])
    observed_units = history["ordered_quantity"]
    minimum, maximum = float(observed_units.min()), float(observed_units.max())
    if not minimum <= reference_units <= maximum:
        st.info("The saved reference is outside the available warehouse history.")
    elif minimum < maximum:
        scenario_input = st.slider(
            "Seasonal reference units",
            minimum,
            maximum,
            reference_units,
            step=1.0,
            key="scenario_reference_units",
        )
        # Seasonal naive predicts the target by copying its reference observation.
        scenario.loc[target, "scenario_units"] = scenario_input
else:
    st.caption(
        "The saved forecast supplies the unit estimates for this price and discount comparison."
    )
scenario["baseline_revenue"] = (
    scenario["prediction"]
    * baseline["average_unit_price"]
    * (1 - baseline["effective_discount_rate"])
)
scenario["scenario_revenue"] = scenario["scenario_units"] * price * (1 - discount)
scenario["baseline_unit_price"] = baseline["average_unit_price"]
scenario["baseline_discount_rate"] = baseline["effective_discount_rate"]
scenario["scenario_unit_price"] = price
scenario["scenario_discount_rate"] = discount
scenario["interpretation"] = "Scenario estimate — not causal impact"
baseline_revenue = scenario["baseline_revenue"].sum()
scenario_revenue = scenario["scenario_revenue"].sum()
with st.container(horizontal=True):
    st.metric("Baseline revenue", f"${baseline_revenue:,.2f}")
    st.metric("Scenario revenue", f"${scenario_revenue:,.2f}")
    st.metric("Difference", f"${scenario_revenue - baseline_revenue:,.2f}")
show_download(
    scenario, "forecast-scenario.csv", alt="Baseline and scenario revenue by week"
)
