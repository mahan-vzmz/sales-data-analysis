"""Monthly customer retention from the Gold cohort mart."""

from dataclasses import dataclass
from datetime import date

import pandas as pd


@dataclass(frozen=True)
class CohortResult:
    """Retention rates in matrix and long-form layouts."""

    matrix: pd.DataFrame
    long_form: pd.DataFrame


def build_retention_matrix(
    purchases: pd.DataFrame, *, observation_end: date | None = None
) -> CohortResult:
    """Measure monthly repeat purchases from a complete mart_cohort_base snapshot."""
    activity = purchases.loc[
        purchases["retained_quantity"].gt(0),
        ["customer_id", "order_month", "acquisition_cohort_month"],
    ].rename(columns={"acquisition_cohort_month": "cohort_month"})
    for column in ("order_month", "cohort_month"):
        activity[column] = (
            pd.to_datetime(activity[column]).dt.to_period("M").dt.to_timestamp()
        )
    if activity.isna().any().any():
        raise ValueError(
            "Completed purchases require customer IDs and cohort/order months"
        )

    first_purchase = activity.groupby("customer_id")["order_month"].transform("min")
    if activity["cohort_month"].ne(first_purchase).any():
        raise ValueError(
            "Cohort month must match the first completed purchase in the snapshot"
        )

    order_month = (
        activity["order_month"].dt.year * 12 + activity["order_month"].dt.month
    )
    cohort_month = (
        activity["cohort_month"].dt.year * 12 + activity["cohort_month"].dt.month
    )
    activity["cohort_age"] = order_month - cohort_month
    keys = ["cohort_month", "cohort_age"]
    counts = activity.groupby(keys)["customer_id"].nunique().rename("active_customers")
    cohorts = (
        activity.groupby("cohort_month")["customer_id"]
        .nunique()
        .reset_index(name="cohort_size")
    )

    latest_month = int(order_month.max()) if not activity.empty else 0
    if observation_end is not None:
        end_month = observation_end.year * 12 + observation_end.month
        if end_month < latest_month:
            raise ValueError("observation_end cannot precede a completed purchase")
        latest_month = end_month
    age_count = latest_month - int(cohort_month.min()) + 1 if not activity.empty else 0
    ages = pd.DataFrame({"cohort_age": pd.RangeIndex(age_count)})
    grid = cohorts.merge(ages, how="cross")
    cohort_start = grid["cohort_month"].dt.year * 12 + grid["cohort_month"].dt.month
    long_form = grid.loc[cohort_start + grid["cohort_age"] <= latest_month].join(
        counts, on=keys
    )
    long_form["active_customers"] = (
        long_form["active_customers"].fillna(0).astype("int64")
    )
    long_form["retention_rate"] = (
        long_form["active_customers"] / long_form["cohort_size"]
    )
    long_form = long_form[
        [*keys, "cohort_size", "active_customers", "retention_rate"]
    ].reset_index(drop=True)
    matrix = long_form.pivot(
        index="cohort_month", columns="cohort_age", values="retention_rate"
    )
    return CohortResult(matrix=matrix, long_form=long_form)
