"""Customer segmentation from the current Gold customer snapshot."""

from datetime import date

import pandas as pd


def build_rfm(customers: pd.DataFrame, analysis_date: date) -> pd.DataFrame:
    """Score customers from mart_customer_360 relative to analysis_date."""
    customers = customers.reset_index(drop=True)
    result = customers[
        ["customer_id", "completed_order_count", "return_adjusted_value"]
    ].rename(
        columns={
            "completed_order_count": "frequency_orders",
            "return_adjusted_value": "monetary_value",
        }
    )
    ids = result["customer_id"]
    if ids.isna().any() or not ids.is_unique:
        raise ValueError("mart_customer_360 requires one row per non-null customer_id")

    frequency = result["frequency_orders"].astype("Int64")
    last_purchase = pd.to_datetime(customers["last_purchase_date"])
    buyers = frequency.gt(0)
    if (
        frequency.isna().any()
        or frequency.lt(0).any()
        or (buyers != last_purchase.notna()).any()
    ):
        raise ValueError(
            "completed_order_count and last_purchase_date are inconsistent"
        )
    if result["monetary_value"].isna().any():
        raise ValueError("return_adjusted_value must be present for every customer")

    recency = (pd.Timestamp(analysis_date) - last_purchase).dt.days.astype("Int64")
    if recency.lt(0).any():
        raise ValueError("analysis_date cannot precede the latest completed purchase")
    result["frequency_orders"] = frequency
    result.insert(1, "recency_days", recency)

    for metric, score, ascending in (
        ("recency_days", "r_score", False),
        ("frequency_orders", "f_score", True),
        ("monetary_value", "m_score", True),
    ):
        values = result.loc[buyers, metric]
        ranks = values.rank(method="average", ascending=ascending)
        # Twice the midpoint rank is integral, so quintile boundaries stay exact.
        midpoint_rank_doubled = 2 * ranks - 1
        quintiles = (5 * midpoint_rank_doubled - 1) // (2 * len(values)) + 1
        result[score] = quintiles.reindex(result.index, fill_value=0).astype("int64")

    result["segment"] = "Active"
    result.loc[result["r_score"].le(2), "segment"] = "At risk"
    result.loc[
        result[["r_score", "f_score", "m_score"]].ge(4).all(axis=1), "segment"
    ] = "Champions"
    result.loc[~buyers, "segment"] = "No completed purchases"
    return result
