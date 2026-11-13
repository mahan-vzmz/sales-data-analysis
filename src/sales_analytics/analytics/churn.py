"""Historical customer features and inactivity labels."""

from collections.abc import Iterable
from datetime import date
from numbers import Integral

import pandas as pd

_FEATURE_COLUMNS = [
    "customer_id",
    "cutoff",
    "horizon_end",
    "last_feature_event_date",
    "last_purchase_date",
    "recency_days",
    "completed_order_count",
    "return_count",
    "inactive_label",
]


def build_customer_snapshots(
    events: pd.DataFrame,
    cutoffs: Iterable[date],
    horizon_days: int,
    *,
    observation_end: date | None = None,
) -> pd.DataFrame:
    """Build one row per eligible customer and fully observed cutoff."""
    if (
        not isinstance(horizon_days, Integral)
        or isinstance(horizon_days, bool)
        or horizon_days < 1
    ):
        raise ValueError("horizon_days must be a positive integer")

    history = events[["customer_id", "event_date", "event_type"]].copy()
    if (
        not history["event_date"]
        .map(lambda value: isinstance(value, (date, str)))
        .all()
    ):
        raise ValueError("event_date must contain calendar dates or date strings")
    history["event_date"] = (
        pd.to_datetime(history["event_date"]).dt.normalize().dt.as_unit("us")
    )
    if history.isna().any().any():
        raise ValueError("customer_id, event_date and event_type must be present")
    if not history["event_type"].isin(["completed_purchase", "return"]).all():
        raise ValueError("event_type must be completed_purchase or return")

    cutoff_dates = pd.DatetimeIndex(list(cutoffs)).normalize().unique().sort_values()
    if cutoff_dates.hasnans:
        raise ValueError("cutoffs must contain valid dates")
    horizon = pd.Timedelta(days=int(horizon_days))
    last_event_date = history["event_date"].max()
    observed_through = (
        pd.Timestamp(observation_end).normalize()
        if observation_end is not None
        else last_event_date
    )
    if observation_end is not None and (
        pd.isna(observed_through) or last_event_date > observed_through
    ):
        raise ValueError("observation_end must be on or after the last supplied event")
    if len(cutoff_dates) and (
        pd.isna(observed_through) or cutoff_dates[-1] + horizon > observed_through
    ):
        raise ValueError("observation_end must cover the full prediction horizon")

    purchases = history[history["event_type"].eq("completed_purchase")]
    returns = history[history["event_type"].eq("return")]
    snapshots = []
    for cutoff in cutoff_dates:
        horizon_end = cutoff + horizon
        past_purchases = purchases[purchases["event_date"].le(cutoff)]
        past_returns = returns[returns["event_date"].le(cutoff)]
        features = past_purchases.groupby("customer_id")["event_date"].agg(
            last_purchase_date="max", completed_order_count="size"
        )
        return_history = past_returns.groupby("customer_id")["event_date"].agg(
            last_return_date="max", return_count="size"
        )
        features = features.join(return_history)
        features["return_count"] = features["return_count"].fillna(0).astype("int64")
        features["last_feature_event_date"] = features[
            ["last_purchase_date", "last_return_date"]
        ].max(axis=1)
        features["recency_days"] = (cutoff - features["last_purchase_date"]).dt.days

        future_buyers = purchases.loc[
            purchases["event_date"].gt(cutoff)
            & purchases["event_date"].le(horizon_end),
            "customer_id",
        ]
        features["inactive_label"] = (~features.index.isin(future_buyers)).astype(
            "int64"
        )
        features["cutoff"] = cutoff
        features["horizon_end"] = horizon_end
        snapshots.append(features.reset_index()[_FEATURE_COLUMNS])

    if not snapshots:
        return pd.DataFrame(columns=_FEATURE_COLUMNS)
    return pd.concat(snapshots, ignore_index=True)
